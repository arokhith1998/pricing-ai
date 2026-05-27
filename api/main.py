"""Pricekeel API. Thin FastAPI wrapper over the pricing/ engine.

The Next.js front end calls this; the analytics are NOT reimplemented here.
Run:  uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pricing import assist, model  # noqa: F401  (assist used below)
from pricing.diagnostic import run
from pricing.ingest import ingest

ROOT = Path(__file__).resolve().parents[1]
DEMO_CSV = ROOT / "data" / "synthetic" / "deals.csv"

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

app = FastAPI(title="Pricekeel API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _records(df) -> list[dict]:
    """DataFrame to JSON-safe records (handles numpy types via to_json)."""
    return json.loads(df.to_json(orient="records"))


def _diagnostic_payload(csv_path: str, policy: float) -> dict:
    res = run(csv_path, policy_threshold=policy)
    return {
        "overview": res["overview"],
        "leakage": res["leakage"],
        "reference_discount": res["reference_discount"],
        "quarter_end": res["quarter_end"],
        "governance": res["governance"],
        "win_rate_by_band": _records(res["win_rate_by_band"]),
        "realization_by_segment": _records(res["realization_by_segment"]),
        "top_leak_deals": _records(res["top_leak_deals"]),
    }


@app.get("/")
def root() -> dict:
    """Friendly landing so visiting the API root is not a bare 404."""
    return {
        "service": "Pricekeel API",
        "note": "This is the data service, not the app. Open the web UI at "
                "http://localhost:3000.",
        "endpoints": ["/health", "/demo", "/docs"],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm": assist.has_llm()}


@app.get("/demo")
def demo(policy: float = 0.15) -> dict:
    """Diagnostic on the bundled synthetic dataset (for the demo UI)."""
    return _diagnostic_payload(str(DEMO_CSV), policy)


@app.post("/diagnostic")
async def diagnostic(file: UploadFile = File(...), policy: float = Form(0.15)) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(await file.read())
        path = tmp.name
    return _diagnostic_payload(path, policy)


class SummaryReq(BaseModel):
    policy: float = 0.15


@app.post("/summary")
def summary(req: SummaryReq) -> dict:
    """AI executive summary of the demo diagnostic. Demo data only for now."""
    if not assist.has_llm():
        return {"enabled": False, "summary": None}
    res = run(str(DEMO_CSV), policy_threshold=req.policy)
    return {"enabled": True, "summary": assist.executive_summary(res)}


class MapReq(BaseModel):
    headers: list[str]


@app.post("/map-columns")
def map_columns(req: MapReq) -> dict:
    """Map a prospect's CSV headers to our schema (header names only)."""
    if not assist.has_llm():
        return {"enabled": False, "mapping": {}}
    return {"enabled": True, "mapping": assist.map_columns(req.headers)}


# --- Win-probability model + discount guidance (Phase 2 / web M2) ------------
#
# Training the LightGBM model takes ~1s on the demo data, so we train once and
# cache it (keyed on the CSV's mtime). The analytics live in pricing/model.py;
# this layer only adapts shapes and applies plain-language labels for the UI.

_ENGINE: dict = {"mtime": None, "df": None, "tm": None}


def _engine() -> tuple[pd.DataFrame, "model.TrainedModel"]:
    """Return (ingested df, trained model), rebuilding if the CSV changed."""
    mtime = DEMO_CSV.stat().st_mtime
    if _ENGINE["mtime"] != mtime:
        df = ingest(str(DEMO_CSV))
        _ENGINE.update(mtime=mtime, df=df, tm=model.train(df))
    return _ENGINE["df"], _ENGINE["tm"]


@app.get("/model")
def model_info() -> dict:
    """Win-probability model quality + what drives it (plain labels)."""
    _df, tm = _engine()
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


@app.get("/deals")
def deals(limit: int = 40) -> dict:
    """Candidate deals for the guidance picker (largest won deals first)."""
    df, _tm = _engine()
    won = df[df["is_won"]].sort_values("list_acv", ascending=False).head(limit)
    cols = ["opportunity_id", "resolved_account_name", "segment", "industry",
            "product_tier", "list_acv", "discount_pct", "competitor_present",
            "is_quarter_end"]
    return {"deals": _records(won[cols])}


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


@app.post("/recommend")
def recommend(req: RecommendReq) -> dict:
    """Per-deal discount guidance: recommended discount, expected value, why."""
    df, tm = _engine()
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
        "list_acv": list_acv,
        "current_discount": rec["current_discount"],
        "recommended_discount": rec["recommended_discount"],
        "win_prob_at_current": float(cur_row["win_prob"]),
        "win_prob_at_rec": rec["win_prob_at_rec"],
        "expected_acv_at_current": rec["expected_acv_at_current"],
        "expected_acv_at_rec": rec["expected_acv_at_rec"],
        "uplift": rec["uplift"],
        "top_factors": _explain_factors(tm, df, idx),
        "curve": _records(curve),
    }
