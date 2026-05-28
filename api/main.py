"""Pricekeel API. Thin FastAPI wrapper over the pricing/ engine.

The Next.js front end calls this; the analytics are NOT reimplemented here.
Run:  uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pricing import assist, mapping, model  # noqa: F401  (assist used below)
from pricing import docs as docs_mod
from pricing import rag as rag_mod
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
        # Optional hierarchy slices: dimension -> list of {dim, deals, list_acv,
        # booked_acv, avg_discount, price_realization}. Empty {} if none present.
        "hierarchy_slices": {
            dim: _records(rows) for dim, rows in res["hierarchy_slices"].items()
        },
        # Framework-grounded follow-on signals.
        "packaging_signals": res["packaging_signals"],
        "trade_or_give": res["trade_or_give"],
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


def _read_upload(file: UploadFile, content: bytes, *, nrows: int | None = None) -> pd.DataFrame:
    """Parse an uploaded CSV or XLSX into a string DataFrame."""
    name = (file.filename or "").lower()
    # .xlsx only: legacy .xls (xlrd) has had macro / CVE issues; skip it.
    if name.endswith(".xlsx"):
        return pd.read_excel(
            io.BytesIO(content), dtype=str, keep_default_na=False, nrows=nrows,
        )
    return pd.read_csv(
        io.BytesIO(content), dtype=str, keep_default_na=False, nrows=nrows,
    )


@app.post("/map-headers")
async def map_headers_endpoint(file: UploadFile = File(...)) -> dict:
    """Parse an uploaded file's headers and suggest a mapping to our schema.

    Sends nothing externally for layers 1-3 (synonyms / fuzzy / local
    embeddings). The cloud LLM fallback (layer 4) only ever receives header
    strings, never row data. We also peek at 3 sample rows for the review UI.
    """
    content = await file.read()
    try:
        df_peek = _read_upload(file, content, nrows=5)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")
    headers = [str(c) for c in df_peek.columns]
    result = mapping.map_headers(headers)
    sample_rows = json.loads(df_peek.head(3).to_json(orient="records"))
    return {**result, "headers": headers, "sample": sample_rows}


@app.post("/diagnostic")
async def diagnostic(
    file: UploadFile = File(...),
    policy: float = Form(0.15),
    mapping_json: str = Form(""),
) -> dict:
    """Run the diagnostic on an uploaded CSV or XLSX. Optionally apply a
    header mapping ({our_field: their_header}) before ingest. The file and
    any temp artifacts are deleted immediately — uploaded data is never
    retained on disk."""
    content = await file.read()
    try:
        df = _read_upload(file, content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    if mapping_json:
        try:
            m = json.loads(mapping_json) or {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="mapping_json is not valid JSON")
        rename = {h: f for f, h in m.items() if h and h in df.columns}
        df = df.rename(columns=rename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        df.to_csv(tmp.name, index=False)
        path = tmp.name
    try:
        return _diagnostic_payload(path, policy)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


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


# --- Ask-your-Pricekeel (Phase 3.0): docs + analysis + (optional) web RAG ------

# In-memory chunk store keyed by session id. Dev fallback; production should
# move to Supabase pgvector keyed to the customer.
_DOC_STORE: dict[str, list[docs_mod.Chunk]] = {}


@app.post("/docs/upload")
async def docs_upload(
    files: list[UploadFile] = File(...),
    session_id: str = Form(""),
) -> dict:
    """Parse + chunk + embed uploaded documents under a session id.

    Returns the session id (newly minted if the client did not send one) plus
    a per-file summary. Documents stay in memory; they are not retained on
    disk and only their chunks (which the customer themselves uploaded) ever
    reach the LLM during a later /ask call.
    """
    import uuid
    sid = session_id or uuid.uuid4().hex

    new_chunks: list[docs_mod.Chunk] = []
    file_info: list[dict] = []
    for f in files:
        data = await f.read()
        try:
            parsed = docs_mod.parse_and_chunk(f.filename or "doc", data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        doc_id = uuid.uuid4().hex
        for i, (page, text) in enumerate(parsed):
            new_chunks.append(docs_mod.Chunk(
                doc_id=doc_id,
                doc_name=f.filename or "doc",
                chunk_idx=i,
                text=text,
                page=page,
            ))
        file_info.append({"name": f.filename, "chunks": len(parsed)})

    if new_chunks:
        embs = docs_mod.embed_texts([c.text for c in new_chunks])
        for c, e in zip(new_chunks, embs):
            c.embedding = e

    _DOC_STORE.setdefault(sid, []).extend(new_chunks)
    return {
        "session_id": sid,
        "files": file_info,
        "total_chunks": len(_DOC_STORE[sid]),
    }


class AskReq(BaseModel):
    question: str
    session_id: str | None = None
    use_web: bool = False
    # Optional client-supplied analysis snapshot (e.g. the JSON for an
    # uploaded-CSV result). Defaults to the demo diagnostic on the sample.
    analysis: dict | None = None


@app.post("/ask")
def ask_endpoint(req: AskReq) -> dict:
    """RAG over analysis + uploaded docs + (optional) web search."""
    chunks = _DOC_STORE.get(req.session_id or "", []) if req.session_id else []
    analysis = req.analysis if req.analysis is not None else _diagnostic_payload(
        str(DEMO_CSV), 0.15,
    )
    ans = rag_mod.ask(req.question, analysis, chunks, use_web=req.use_web)
    return {
        "text": ans.text,
        "used_web": ans.used_web,
        "session_id": req.session_id,
        "citations": [
            {
                "kind": c.kind,
                "title": c.title,
                "snippet": c.snippet,
                "detail": c.detail,
            }
            for c in ans.citations
        ],
    }


# --- Win-probability model + discount guidance (Phase 2 / web M2) -----------

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
