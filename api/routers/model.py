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


def _explain_factors(tm: "model.TrainedModel", df: pd.DataFrame, idx, *,
                     discount_override: float | None = None,
                     top: int = 5) -> list[dict]:
    """Top SHAP drivers for one deal, as plain 'pushed win chance up/down'.

    `discount_override`, when given, explains the row at that discount
    instead of the deal's current one (mle-reviewer F4: the headline shows
    the recommended discount, and SHAP at the current discount can name a
    different top factor, or flip discount_pct's own sign, 14-36% of the
    time). Callers that need both must call this twice, once per row, and
    label which is which; `/recommend` below does exactly that.
    """
    X_row = tm.X_all.loc[[idx]].copy()
    if discount_override is not None:
        X_row["discount_pct"] = discount_override
    contrib = model.explain(tm, X_row)
    out = []
    for r in contrib.itertuples():
        if r.feature == "<base>":
            continue
        raw = (discount_override if (r.feature == "discount_pct"
                                     and discount_override is not None)
              else df.loc[idx, r.feature])
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


# Worded like crm.guidance_for_open_deal's correlational caveat (code-reviewer
# F3): the strongest dollar claim in the product, /recommend's EV uplift, must
# not be the one surface that ships without it.
_RECOMMEND_CAVEAT = (
    "This discount is the argmax of a model trained on observational deals, "
    "not a causal experiment: it is correlational decision support, not a "
    "guaranteed outcome. Validate against the comparables and band context "
    "below before treating it as committed guidance."
)


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
    # The cohort this recommendation is conditioned on (same one band_context
    # and comparable_deals use): fewer than ~50 deals here means the sweep
    # would extrapolate past this segment's real support, so recommend_discount
    # falls back to a band guardrail instead of a curve optimum (mle-reviewer
    # F3).
    cohort_discounts = df.loc[
        df["segment"] == df.loc[idx, "segment"], "discount_pct",
    ].to_numpy()
    rec = model.recommend_discount(tm, tm.X_all.loc[[idx]], list_acv,
                                   cohort_discounts=cohort_discounts)

    curve = rec["curve"]
    # Win probability at the deal's actual discount, read off the same curve.
    cur_row = curve.iloc[(curve["discount"] - rec["current_discount"]).abs().argmin()]
    return {
        "opportunity_id": req.opportunity_id,
        "account": str(df.loc[idx, "resolved_account_name"]),
        "segment": str(df.loc[idx, "segment"]),
        # "modeled_ev_curve" on enough cohort support, "band_guardrail" when
        # there is not. Labeled so the live Salesforce path (always
        # band_guardrail) is never confused with the stronger engine, and so
        # a thin-cohort demo deal is never shown a curve it did not earn.
        "method": rec["method"],
        "caveat": _RECOMMEND_CAVEAT,
        "list_acv": list_acv,
        "current_discount": rec["current_discount"],
        "recommended_discount": rec["recommended_discount"],
        "win_prob_at_current": float(cur_row["win_prob"]),
        "win_prob_at_rec": rec["win_prob_at_rec"],
        "expected_acv_at_current": rec["expected_acv_at_current"],
        "expected_acv_at_rec": rec["expected_acv_at_rec"],
        "uplift": rec["uplift"],
        # "top_factors" stays the current-discount explanation (unchanged
        # shape for existing callers); "top_factors_at_recommended" is the
        # new, separately labeled explanation at the row the headline
        # actually recommends (mle-reviewer F4).
        "top_factors": _explain_factors(tm, df, idx),
        "top_factors_at_recommended": _explain_factors(
            tm, df, idx, discount_override=rec["recommended_discount"]),
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
            # Which holdout produced those numbers. A time-ordered AUC and the
            # random-split fallback's AUC are not the same claim, and the panel
            # cites this one in a pricing committee.
            "split": tm.metrics["split"],
            "test_from": tm.metrics["test_from"],
            "brier_skill": tm.metrics.get("brier_skill"),
            "cohort_deals": rec.get("cohort_deals"),
        },
        "curve": records(curve),
    }
