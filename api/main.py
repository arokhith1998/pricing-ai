"""Pricekeel API. Thin FastAPI wrapper over the pricing/ engine.

The Next.js front end calls this; the analytics are NOT reimplemented here.
Run:  uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pricing import assist, model  # noqa: F401  (assist used below)
from pricing.diagnostic import run
from pricing.ingest import ingest

ROOT = Path(__file__).resolve().parents[1]
DEMO_CSV = ROOT / "data" / "synthetic" / "deals.csv"

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
