"""Diagnostic component: /demo, /diagnostic, /map-headers, /map-columns,
/summary: the CSV/XLSX upload + AI-assisted mapping path.

`_read_capped` (the upload byte-cap backstop) is owned by the perimeter
component and stays defined in api/main.py; see the note there. The import
below is deferred to inside each endpoint (rather than at module load time)
because api/main.py imports this router, so a module-level `from api import
main` here would try to import a module that is still mid-import (main.py
has not finished executing yet). By request time main.py has always fully
loaded, so the deferred import is safe.
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from pricing import assist, mapping
from pricing.diagnostic import run
from api.shared import DEMO_CSV, diagnostic_payload

logger = logging.getLogger("pricekeel.api.diagnostic")

router = APIRouter()

_BAD_FILE_DETAIL = (
    "Could not read that file. Confirm it is a valid CSV or .xlsx export."
)


@router.get("/demo")
def demo(policy: float = 0.15) -> dict:
    """Diagnostic on the bundled synthetic dataset (for the demo UI)."""
    return diagnostic_payload(str(DEMO_CSV), policy)


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


@router.post("/map-headers")
async def map_headers_endpoint(file: UploadFile = File(...)) -> dict:
    """Parse an uploaded file's headers and suggest a mapping to our schema.

    Sends nothing externally for layers 1-3 (synonyms / fuzzy / local
    embeddings). The cloud LLM fallback (layer 4) only ever receives header
    strings, never row data. We also peek at 3 sample rows for the review UI.
    """
    from api import main  # deferred: see module docstring
    content = await main._read_capped(file)
    try:
        df_peek = _read_upload(file, content, nrows=5)
    except Exception as exc:  # noqa: BLE001
        logger.warning("map-headers: could not parse upload %r: %s",
                       file.filename, exc)
        raise HTTPException(status_code=400, detail=_BAD_FILE_DETAIL)
    headers = [str(c) for c in df_peek.columns]
    result = mapping.map_headers(headers)
    sample_rows = json.loads(df_peek.head(3).to_json(orient="records"))
    return {**result, "headers": headers, "sample": sample_rows}


@router.post("/diagnostic")
async def diagnostic(
    file: UploadFile = File(...),
    policy: float = Form(0.15),
    mapping_json: str = Form(""),
) -> dict:
    """Run the diagnostic on an uploaded CSV or XLSX. Optionally apply a
    header mapping ({our_field: their_header}) before ingest. The file and
    any temp artifacts are deleted immediately — uploaded data is never
    retained on disk."""
    from api import main  # deferred: see module docstring
    content = await main._read_capped(file)
    try:
        df = _read_upload(file, content)
    except Exception as exc:  # noqa: BLE001
        logger.warning("diagnostic: could not parse upload %r: %s",
                       file.filename, exc)
        raise HTTPException(status_code=400, detail=_BAD_FILE_DETAIL)

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
        return diagnostic_payload(path, policy)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


class SummaryReq(BaseModel):
    policy: float = 0.15


@router.post("/summary")
def summary(req: SummaryReq) -> dict:
    """AI executive summary of the demo diagnostic. Demo data only for now."""
    if not assist.has_llm():
        return {"enabled": False, "summary": None}
    res = run(str(DEMO_CSV), policy_threshold=req.policy)
    return {"enabled": True, "summary": assist.executive_summary(res)}


class MapReq(BaseModel):
    headers: list[str]


@router.post("/map-columns")
def map_columns(req: MapReq) -> dict:
    """Map a prospect's CSV headers to our schema (header names only)."""
    if not assist.has_llm():
        return {"enabled": False, "mapping": {}}
    return {"enabled": True, "mapping": assist.map_columns(req.headers)}
