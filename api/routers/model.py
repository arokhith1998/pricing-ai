"""Model component: /model, /deals, /recommend: win-probability model
quality, the guidance picker's deal list, and per-deal discount guidance.

The trained model + ingested demo book are cached in api/shared.py, not
here, because the governance router (/exceptions) scores a deal against the
same trained model and must never see a second, independently-trained copy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pricing import model
from api.shared import engine, records

router = APIRouter()

# Plain-language labels for model features (design doc appendix A). The UI never
# shows raw snake_case field names.
FEATURE_LABELS = {
    "segment": "Segment",
    "region": "Region",
    "industry": "Industry",
    "product_tier": "Plan",
    "value_metric": "Pricing model",
    "list_acv": "List value (annual)",
    "discount_pct": "Discount",
    "term_months": "Term (months)",
    "quantity": "Quantity",
    "is_quarter_end": "Closed near quarter end",
    "competitor_present": "Competitor in deal",
}


@router.get("/model")
def model_info() -> dict:
    """Win-probability model quality + what drives it (plain labels)."""
    _df, tm = engine()
    fi = model.feature_importance(tm)
    total = float(fi["gain"].sum()) or 1.0
    importance = [
        {
            "feature": r.feature,
            "label": FEATURE_LABELS.get(r.feature, r.feature),
            "share": float(r.gain) / total,
        }
        for r in fi.itertuples()
    ]
    return {
        "metrics": tm.metrics,
        "feature_importance": importance,
        "model_leakage": model.leakage_vs_model(tm, _df),
    }


@router.get("/deals")
def deals(limit: int = 40) -> dict:
    """Candidate deals for the guidance picker (largest won deals first)."""
    df, _tm = engine()
    won = df[df["is_won"]].sort_values("list_acv", ascending=False).head(limit)
    cols = ["opportunity_id", "resolved_account_name", "segment", "industry",
            "product_tier", "list_acv", "discount_pct", "competitor_present",
            "is_quarter_end"]
    return {"deals": records(won[cols])}


def _explain_factors(tm: "model.TrainedModel", df: pd.DataFrame, idx,
                     top: int = 5) -> list[dict]:
    """Top SHAP drivers for one deal, as plain 'pushed win chance up/down'."""
    contrib = model.explain(tm, tm.X_all.loc[[idx]])
    out = []
    for r in contrib.itertuples():
        if r.feature == "<base>":
            continue
        raw = df.loc[idx, r.feature]
        if isinstance(raw, (bool, np.bool_)):
            value = "Yes" if raw else "No"
        elif r.feature == "discount_pct":
            value = f"{float(raw):.0%}"
        elif r.feature == "list_acv":
            value = f"${float(raw):,.0f}"
        else:
            # Numeric (term, quantity) -> grouped integer; categories stay as-is.
            try:
                value = f"{float(raw):,.0f}"
            except (TypeError, ValueError):
                value = str(raw)
        out.append({
            "label": FEATURE_LABELS.get(r.feature, r.feature),
            "value": value,
            "direction": "up" if r.contribution >= 0 else "down",
            "contribution": float(r.contribution),
        })
        if len(out) >= top:
            break
    return out


class RecommendReq(BaseModel):
    opportunity_id: str


@router.post("/recommend")
def recommend(req: RecommendReq) -> dict:
    """Per-deal discount guidance: recommended discount, expected value, why."""
    df, tm = engine()
    matches = df.index[df["opportunity_id"] == req.opportunity_id]
    if len(matches) == 0:
        raise HTTPException(status_code=404, detail="Unknown opportunity_id")
    idx = matches[0]
    list_acv = float(df.loc[idx, "list_acv"])
    rec = model.recommend_discount(tm, tm.X_all.loc[[idx]], list_acv)

    curve = rec["curve"]
    # Win probability at the deal's actual discount, read off the same curve.
    cur_row = curve.iloc[(curve["discount"] - rec["current_discount"]).abs().argmin()]
    return {
        "opportunity_id": req.opportunity_id,
        "account": str(df.loc[idx, "resolved_account_name"]),
        "segment": str(df.loc[idx, "segment"]),
        # Modeled EV curve on the demo book. Labeled so the live Salesforce
        # path (band guardrail) is never confused with this stronger engine.
        "method": "modeled_ev_curve",
        "list_acv": list_acv,
        "current_discount": rec["current_discount"],
        "recommended_discount": rec["recommended_discount"],
        "win_prob_at_current": float(cur_row["win_prob"]),
        "win_prob_at_rec": rec["win_prob_at_rec"],
        "expected_acv_at_current": rec["expected_acv_at_current"],
        "expected_acv_at_rec": rec["expected_acv_at_rec"],
        "uplift": rec["uplift"],
        "top_factors": _explain_factors(tm, df, idx),
        # The evidence behind the recommendation (Phase 3 explainability):
        # similar deals, the segment's win-rate-by-band curve segment, and the
        # model-confidence numbers for the caveat. The panel must stand up in a
        # pricing committee, so every element is observed, not asserted.
        "comparables": records(model.comparable_deals(df, idx)),
        "band_context": model.band_context(df, idx, rec["recommended_discount"]),
        "confidence": {
            "auc": tm.metrics["auc"],
            "mean_pred": tm.metrics["mean_pred"],
            "base_rate": tm.metrics["base_rate"],
            "n_train": tm.metrics["n_train"],
        },
        "curve": records(curve),
    }
