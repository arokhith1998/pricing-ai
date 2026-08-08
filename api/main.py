"""Pricekeel API. Thin FastAPI wrapper over the pricing/ engine.

The Next.js front end calls this; the analytics are NOT reimplemented here.
Run:  uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import dataclasses
import hmac
import io
import json
import logging
import os
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from pricing import assist, mapping, model  # noqa: F401  (assist used below)
from pricing import copilot as copilot_mod
from pricing import crm as crm_mod
from pricing import docs as docs_mod
from pricing import governance as governance_mod
from pricing import matching as matching_mod
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

logger = logging.getLogger("pricekeel.api")

app = FastAPI(title="Pricekeel API", version="0.1.0")

# --- API perimeter (CTO security review, 2026-06-11) -------------------------
#
# api.pricekeel.com is publicly reachable; the Next.js tier proxies to it
# server-side and attaches `X-Pricekeel-Key: $PRICEKEEL_API_KEY`. One
# middleware enforces, in order: shared-secret auth (401), upload size cap
# (413), and per-IP rate limiting (429). All checks read state at request
# time so tests (and Render env changes) take effect without re-import.

AUTH_HEADER = "x-pricekeel-key"
AUTH_EXEMPT_PATHS = {"/", "/health"}

# Tenant scope (Finding 3). The web proxy sets X-Pricekeel-Customer per signed-in
# customer; absent => "default" so single-tenant behavior is unchanged. Every
# decision-log write and read is scoped by this value so one customer's log is
# invisible to another.
CUSTOMER_HEADER = "x-pricekeel-customer"


def _customer_ref(request: Request) -> str:
    """Tenant key from X-Pricekeel-Customer; 'default' when absent/blank."""
    return (request.headers.get(CUSTOMER_HEADER, "") or "").strip() or "default"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
UPLOAD_PATHS = {"/map-headers", "/diagnostic", "/docs/upload"}

# Per-request caps for the multi-file docs upload (Finding 4). The single-file
# byte cap (_read_capped) and the chunk-count cap (_doc_store_append) do not
# bound how MANY files or how many TOTAL bytes one request carries.
MAX_DOCS_FILES_PER_REQUEST = 10
MAX_DOCS_TOTAL_BYTES = 25 * 1024 * 1024  # 25 MB across all files in one request

# Sliding-window per-IP limits: path (exact, or prefix when ending in "/")
# -> (max requests, window seconds). LLM-backed endpoints are the expensive
# ones (provider cost + worker time); the rest are CPU-bound but heavy.
RATE_LIMITS: dict[str, tuple[int, float]] = {
    "/ask": (10, 60.0),
    "/summary": (10, 60.0),
    "/matching/": (10, 60.0),
    "/diagnostic": (30, 60.0),
    "/map-headers": (30, 60.0),
    "/docs/upload": (30, 60.0),
    # Guidance-tier endpoint: CPU-bound model sweep plus a decision-log write.
    # (POST only — the middleware never limits GET, so reads stay unmetered,
    # same as /recommend.)
    "/exceptions": (30, 60.0),
    "/crm/": (20, 60.0),
}
# (rule, client_ip) -> deque of request timestamps inside the window.
_RATE_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)

def _is_prod() -> bool:
    """Production unless PRICEKEEL_ENV is explicitly 'dev' (same rule CORS
    uses to fail closed on an unset env). Read at call time so Render env
    changes and tests take effect without re-import."""
    return os.environ.get("PRICEKEEL_ENV", "").lower() != "dev"


if not os.environ.get("PRICEKEEL_API_KEY"):
    logger.warning("API perimeter OPEN — set PRICEKEEL_API_KEY")


def _rate_state_reset() -> None:
    """Test hook: forget all rate-limit history."""
    _RATE_BUCKETS.clear()


def _client_ip(request: Request) -> str:
    """Caller IP. Render sits behind a proxy, so trust the first
    X-Forwarded-For value; fall back to the socket peer."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff.strip():
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_rule_for(path: str) -> tuple[str, int, float] | None:
    """Match a request path to a rate-limit rule (exact or prefix)."""
    for rule, (limit, window) in RATE_LIMITS.items():
        if path == rule or (rule.endswith("/") and path.startswith(rule)):
            return rule, limit, window
    return None


def _rate_limit_retry_after(rule: str, limit: int, window: float,
                            ip: str) -> int | None:
    """Record this request; return Retry-After seconds if over the limit."""
    now = time.monotonic()
    bucket = _RATE_BUCKETS[(rule, ip)]
    while bucket and bucket[0] <= now - window:
        bucket.popleft()
    if len(bucket) >= limit:
        return max(1, int(bucket[0] + window - now) + 1)
    bucket.append(now)
    return None


@app.middleware("http")
async def perimeter(request: Request, call_next):
    path = request.url.path

    # 1) Shared-secret auth. CORS preflights (OPTIONS) carry no custom
    # headers by design, and they execute nothing — let them through.
    expected = os.environ.get("PRICEKEEL_API_KEY", "")
    exempt = path in AUTH_EXEMPT_PATHS or request.method == "OPTIONS"
    # Fail closed in production: a prod deploy with no API key is fully public,
    # so reject every non-exempt request rather than silently serve it. /health
    # and / stay exempt so Render's probe and a bare landing still work. In dev
    # (PRICEKEEL_ENV=dev) we keep the warn-and-allow behavior for local work.
    if not expected and not exempt and _is_prod():
        return JSONResponse(
            status_code=503,
            content={"detail": (
                "Server misconfigured: API key not set. "
                "Set PRICEKEEL_API_KEY."
            )},
        )
    if expected and not exempt:
        supplied = request.headers.get(AUTH_HEADER, "")
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid X-Pricekeel-Key."},
            )

    # 2) Upload size cap (declared size; the read path re-checks actual bytes).
    if path in UPLOAD_PATHS and request.method == "POST":
        try:
            declared = int(request.headers.get("content-length", "0") or "0")
        except ValueError:
            declared = 0
        if declared > MAX_UPLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": (
                    f"Upload too large: {declared} bytes "
                    f"(limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)."
                )},
            )

    # 3) Per-IP sliding-window rate limit on the expensive endpoints.
    rule = _rate_rule_for(path)
    if rule is not None and request.method == "POST":
        name, limit, window = rule
        retry_after = _rate_limit_retry_after(name, limit, window,
                                              _client_ip(request))
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": (
                    f"Rate limit exceeded ({limit} requests / "
                    f"{int(window)}s for {name}). Try again shortly."
                )},
                headers={"Retry-After": str(retry_after)},
            )

    return await call_next(request)

# CORS: lock to known origins by default. Wildcard "*" only when
# PRICEKEEL_ENV is EXPLICITLY "dev" — an unset env var (e.g. a fresh Render
# service) must fail closed, not open (CTO review). Set
# PRICEKEEL_CORS_ORIGINS as a comma-separated list to override.
_DEFAULT_ORIGINS = [
    "https://www.pricekeel.com",
    "https://pricekeel.com",
    "https://pricekeel.vercel.app",
]
_dev_mode = os.environ.get("PRICEKEEL_ENV", "").lower() == "dev"
_origin_env = os.environ.get("PRICEKEEL_CORS_ORIGINS", "").strip()
if _origin_env:
    _origins = [o.strip() for o in _origin_env.split(",") if o.strip()]
    _origin_regex = None
elif _dev_mode:
    _origins = ["*"]
    _origin_regex = None
else:
    _origins = _DEFAULT_ORIGINS
    # Vercel preview deployments — match `pricekeel-*-arokhith1998s-projects.vercel.app`.
    _origin_regex = r"^https://pricekeel-[a-z0-9]+-arokhith1998s-projects\.vercel\.app$"
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=_origin_regex,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type", "Authorization", "X-Pricekeel-Key",
        "X-Pricekeel-Customer",
    ],
    allow_credentials=False,
)


@app.exception_handler(assist.LLMUnavailableError)
async def _llm_unavailable_handler(request: Request,
                                   exc: assist.LLMUnavailableError):
    """A stalled/unreachable LLM provider is a 503, not a hung worker."""
    return JSONResponse(
        status_code=503,
        content={"detail": f"LLM provider unavailable: {exc}"},
    )


def _records(df) -> list[dict]:
    """DataFrame to JSON-safe records (handles numpy types via to_json)."""
    return json.loads(df.to_json(orient="records"))


def _load_report_dict(rep) -> dict:
    """LoadReport dataclass -> JSON-safe dict, plus its human summary block."""
    d = dataclasses.asdict(rep)
    d["summary"] = rep.summary()
    # Round-trip to flush any stray numpy scalars to plain JSON types.
    return json.loads(json.dumps(d, default=str))


def _analysis_payload(res: dict) -> dict:
    """JSON-safe dashboard payload for CSV and live-CRM analyses."""
    return {
        # "What we read from your file" — ingest disclosures (duplicates
        # dropped, open deals excluded, encoding, unmapped columns, ...).
        "load_report": _load_report_dict(res["load_report"]),
        "overview": res["overview"],
        "leakage": res["leakage"],
        "reference_discount": res["reference_discount"],
        "quarter_end": res["quarter_end"],
        "governance": res["governance"],
        "trend_by_quarter": _records(res["trend_by_quarter"]),
        "segment_win_points": res["segment_win_points"],
        "policy_simulations": res["policy_simulations"],
        "new_vs_renewal": _records(res["new_vs_renewal"]),
        "rep_discipline": _records(res["rep_discipline"]),
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
        "trade_or_give_deals": _records(res["trade_or_give_deals"]),
        "quarter_end_deals": _records(res["quarter_end_deals"]),
        "packaging_signal_deals": _records(res["packaging_signal_deals"]),
        "defended_vs_investigate": res["defended_vs_investigate"],
    }


def _diagnostic_payload(csv_path: str, policy: float) -> dict:
    return _analysis_payload(run(csv_path, policy_threshold=policy))


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


async def _read_capped(file: UploadFile) -> bytes:
    """Read an upload, hard-capped at MAX_UPLOAD_BYTES.

    Backstop behind the Content-Length middleware check — a client can lie
    about (or omit) Content-Length, so we also bound the actual bytes read
    before any parsing happens.
    """
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(f"Upload too large "
                    f"(limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)."),
        )
    return content


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
    content = await _read_capped(file)
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
    content = await _read_capped(file)
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
# move to Neon pgvector keyed to the customer.
#
# This dict is the single piece of process-lifetime state in the API. Without
# any cap it grows on every upload until OOM. Hardening (per the 2026-05-30
# launch-readiness review): per-session chunk cap, total-session cap, TTL,
# and lazy expiry on every read/write. None of this is a substitute for
# moving to Neon pgvector, but it removes the foot-gun for soft launch.

import time as _time

_DOC_STORE: dict[str, tuple[float, list[docs_mod.Chunk]]] = {}
_DOC_STORE_MAX_SESSIONS = int(os.environ.get("PRICEKEEL_DOC_MAX_SESSIONS", "500"))
_DOC_STORE_MAX_CHUNKS_PER_SESSION = int(
    os.environ.get("PRICEKEEL_DOC_MAX_CHUNKS_PER_SESSION", "2000"),
)
_DOC_STORE_TTL_SECONDS = int(
    os.environ.get("PRICEKEEL_DOC_TTL_SECONDS", str(60 * 60 * 4)),  # 4h
)


def _doc_store_expire_old(now: float | None = None) -> None:
    """Drop sessions older than TTL. O(n) — fine at the cap of 500 sessions."""
    now = now if now is not None else _time.time()
    cutoff = now - _DOC_STORE_TTL_SECONDS
    for sid in [s for s, (ts, _) in _DOC_STORE.items() if ts < cutoff]:
        del _DOC_STORE[sid]


def _doc_store_get(sid: str) -> list[docs_mod.Chunk]:
    _doc_store_expire_old()
    entry = _DOC_STORE.get(sid)
    return entry[1] if entry else []


def _doc_store_append(sid: str, new_chunks: list[docs_mod.Chunk]) -> int:
    """Append chunks to a session; enforce per-session and global caps.

    Returns the post-append chunk count. Raises HTTPException(429) if the
    cap is exceeded; raises HTTPException(503) if we are at session capacity
    and this is a *new* session id.
    """
    _doc_store_expire_old()
    existing = _DOC_STORE.get(sid)
    if existing is None and len(_DOC_STORE) >= _DOC_STORE_MAX_SESSIONS:
        raise HTTPException(
            status_code=503,
            detail="Document store is at session capacity; please retry later.",
        )
    existing_chunks = existing[1] if existing else []
    if len(existing_chunks) + len(new_chunks) > _DOC_STORE_MAX_CHUNKS_PER_SESSION:
        raise HTTPException(
            status_code=413,
            detail=(
                f"This session would exceed the chunk cap "
                f"({_DOC_STORE_MAX_CHUNKS_PER_SESSION}). Start a new session "
                "or drop fewer files."
            ),
        )
    merged = existing_chunks + new_chunks
    _DOC_STORE[sid] = (_time.time(), merged)
    return len(merged)


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

    # Per-request caps (Finding 4): bound file count and total bytes before we
    # parse anything, so a single request cannot exhaust memory by sending many
    # files each just under the single-file cap.
    if len(files) > MAX_DOCS_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=413,
            detail=(f"Too many files in one request "
                    f"(limit {MAX_DOCS_FILES_PER_REQUEST}). Upload fewer files "
                    "or split the request."),
        )

    new_chunks: list[docs_mod.Chunk] = []
    file_info: list[dict] = []
    total_bytes = 0
    for f in files:
        data = await _read_capped(f)
        total_bytes += len(data)
        if total_bytes > MAX_DOCS_TOTAL_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(f"Upload too large: total across files exceeds "
                        f"{MAX_DOCS_TOTAL_BYTES // (1024 * 1024)} MB. Upload "
                        "fewer or smaller files."),
            )
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

    total = _doc_store_append(sid, new_chunks)
    return {
        "session_id": sid,
        "files": file_info,
        "total_chunks": total,
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
    chunks = _doc_store_get(req.session_id) if req.session_id else []
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


# --- Copilot v2: canonical questions + structured opportunities -------------
# The copilot turns the analysis into a ranked list of Opportunity objects
# (revenue impact + confidence + evidence) and asks the LLM to narrate them.
# Every dollar figure is deterministic; the LLM never invents numbers.

class CanonicalReq(BaseModel):
    qid: str
    session_id: str | None = None
    analysis: dict | None = None
    min_impact_usd: float = 0.0


@app.get("/copilot/canonical")
def copilot_canonical_list() -> dict:
    """The six canonical questions the UI surfaces as chips."""
    return {"questions": copilot_mod.CANONICAL_QUESTIONS}


@app.post("/copilot/canonical")
def copilot_canonical(req: CanonicalReq, request: Request) -> dict:
    """Deterministic opportunities + LLM narrative for one canonical question."""
    analysis = req.analysis if req.analysis is not None else _diagnostic_payload(
        str(DEMO_CSV), 0.15,
    )
    ans = copilot_mod.answer_canonical(
        req.qid, analysis, min_impact_usd=req.min_impact_usd,
    )
    # Auto-log every surfaced set so the decision log always reflects what
    # the user actually saw (accept / reject can come later via /copilot/log).
    # Persisted via the governance store (Neon when configured), scoped
    # to the caller's tenant.
    if req.session_id:
        governance_mod.log_copilot_decision(
            req.session_id, req.qid,
            surfaced=[o.id for o in ans.opportunities],
            customer_ref=_customer_ref(request),
        )
    return ans.to_dict()


class DecisionLogReq(BaseModel):
    session_id: str
    qid: str
    accepted: list[str] = []
    rejected: list[str] = []
    note: str = ""


@app.post("/copilot/log")
def copilot_log(req: DecisionLogReq, request: Request) -> dict:
    """Log a copilot decision. Same response contract as before; storage now
    goes through pricing/governance.py (Neon when configured, memory
    fallback) instead of a process-lifetime dict. Scoped to the tenant."""
    d = governance_mod.log_copilot_decision(
        req.session_id, req.qid,
        accepted=req.accepted, rejected=req.rejected, note=req.note,
        customer_ref=_customer_ref(request),
    )
    return {"logged": True, "decision": d}


@app.get("/copilot/decisions")
def copilot_decisions(session_id: str, request: Request) -> dict:
    return {
        "session_id": session_id,
        "decisions": governance_mod.copilot_decisions(
            session_id, customer_ref=_customer_ref(request)),
    }


# --- Governance loop: discount exceptions + weekly digest --------------------
# The subscription use case: a deal-desk rep requests a below-floor discount,
# Pricekeel returns the priced verdict (same EV-curve math as /recommend, no
# LLM) and logs the decision; /digest re-surfaces the week's activity. Every
# number is deterministic; storage via pricing/governance.py (Neon when
# configured, in-memory fallback).
#
# Percent convention (documented contract): requested_discount_pct and every
# *_pct field in the verdict and digest are percent 0-100 — 22.5 means a
# 22.5 percent discount, the default floor_pct is 15.0. Win probabilities are
# 0-1 fractions; ev_delta_vs_recommended is dollars.


class ExceptionReq(BaseModel):
    deal_id: str
    # Percent 0-100 (22.5 = a 22.5 percent discount). Valid range 0-40, the
    # discount grid the win model sweeps.
    requested_discount_pct: float
    justification: str = ""
    requested_by: str = ""


@app.post("/exceptions")
def create_exception(req: ExceptionReq, request: Request) -> dict:
    """Score a discount-exception request against the deal's own EV curve,
    log it, and return the verdict. requested_discount_pct is percent 0-100.

    Response shape: {id, verdict, created_at, persisted}. `persisted` is True
    when the decision was written durably to the database, False when it landed
    in the in-memory fallback (database unset or unreachable) — the response
    never claims durability it does not have (Finding 5). The write is scoped to the
    caller's tenant via X-Pricekeel-Customer (Finding 3)."""
    if not (0.0 <= req.requested_discount_pct
            <= governance_mod.EXCEPTION_MAX_PCT):
        raise HTTPException(
            status_code=422,
            detail=(f"requested_discount_pct must be between 0 and "
                    f"{governance_mod.EXCEPTION_MAX_PCT:g} (percent of list "
                    f"price; the modeled discount range)."),
        )
    df, tm = _engine()
    matches = df.index[df["opportunity_id"] == req.deal_id]
    if len(matches) == 0:
        raise HTTPException(status_code=404, detail="Unknown deal_id")
    idx = matches[0]

    verdict = governance_mod.exception_verdict(
        tm, tm.X_all.loc[[idx]], float(df.loc[idx, "list_acv"]),
        req.requested_discount_pct,
    )
    row = governance_mod.STORE.insert(
        kind="exception",
        deal_id=req.deal_id,
        payload={
            "deal_id": req.deal_id,
            "requested_discount_pct": req.requested_discount_pct,
            "justification": req.justification,
            "requested_by": req.requested_by,
            "verdict": verdict,
        },
        decision="below_floor" if verdict["below_floor"] else "within_floor",
        justification=req.justification,
        requested_by=req.requested_by,
        customer_ref=_customer_ref(request),
    )
    return {"id": str(row["id"]), "verdict": verdict,
            "created_at": str(row["created_at"]),
            "persisted": bool(row.get("persisted", False))}


@app.get("/exceptions")
def list_exceptions(request: Request, limit: int = 50) -> dict:
    """Recent exception requests, newest first, with their logged verdicts.
    Scoped to the caller's tenant via X-Pricekeel-Customer (Finding 3)."""
    rows = governance_mod.STORE.list(kind="exception",
                                     limit=max(1, min(int(limit), 200)),
                                     customer_ref=_customer_ref(request))
    items = []
    for r in rows:
        p = r.get("payload") or {}
        items.append({
            "id": str(r.get("id", "")),
            "deal_id": str(p.get("deal_id", r.get("deal_id", ""))),
            "requested_discount_pct": p.get("requested_discount_pct"),
            "justification": str(p.get("justification", "")),
            "requested_by": str(p.get("requested_by", "")),
            "verdict": p.get("verdict") or {},
            "created_at": str(r.get("created_at", "")),
        })
    return {"items": items}


# The digest needs the loaded book's diagnostic aggregates; cache the run
# keyed on the CSV's mtime (same pattern as _ENGINE) so an unmetered GET is
# not a full ingest+diagnostic every time.
_DIGEST_BOOK: dict = {"mtime": None, "analysis": None}


@app.get("/digest")
def digest(request: Request) -> dict:
    """Weekly governance digest: decision-log activity over the last 7 days
    plus the loaded book's diagnostic aggregates. Deterministic, no LLM.
    Discount/realization figures are percent 0-100, matching /exceptions.
    Scoped to the caller's tenant via X-Pricekeel-Customer (Finding 3)."""
    analysis = None
    try:
        if DEMO_CSV.exists():
            mtime = DEMO_CSV.stat().st_mtime
            if _DIGEST_BOOK["mtime"] != mtime:
                _DIGEST_BOOK.update(
                    mtime=mtime,
                    analysis=run(str(DEMO_CSV), policy_threshold=0.15),
                )
            analysis = _DIGEST_BOOK["analysis"]
    except Exception:  # noqa: BLE001 — digest must degrade, not 500
        logger.warning("digest: book diagnostics unavailable", exc_info=True)
    return governance_mod.build_digest(analysis=analysis, window_days=7,
                                       customer=_customer_ref(request))


# --- Salesforce / CRM-native workflow -------------------------------------
# OAuth, token refresh, SOQL, and field-level access stay in the Next.js
# server tier. This API receives canonical rows over the existing shared-secret
# perimeter, computes deterministic analytics, discards the rows, and persists
# only workflow events in the append-only decision log.


class CRMAnalyzeReq(BaseModel):
    records: list[dict]
    policy_threshold_pct: float = 15.0


@app.post("/crm/analyze")
def crm_analyze(req: CRMAnalyzeReq) -> dict:
    try:
        result = crm_mod.analyze_records(
            req.records, policy_threshold_pct=req.policy_threshold_pct,
        )
    except crm_mod.CRMDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "analysis": _analysis_payload(result["analysis"]),
        "guidance": result["guidance"],
        "readiness": result["readiness"],
    }


_CRM_EVENTS = {
    "flagged", "accepted", "override_requested", "approved", "rejected",
    "outcome_recorded",
}


class CRMWorkflowReq(CRMAnalyzeReq):
    deal_id: str
    event: str
    actor: str = ""
    justification: str = ""
    requested_discount_pct: float | None = None
    outcome: str = ""


def _crm_deal_history(customer: str, deal_id: str) -> list[dict]:
    rows = governance_mod.STORE.list(
        kind="exception", deal_id=deal_id, source="salesforce_crm",
        limit=500, customer_ref=customer,
    )
    return rows


def _normalized_actor(value: str) -> str:
    """Compare self-asserted actor names ignoring case and inner whitespace.

    Actor is free text until an authenticated identity exists, so this makes
    the self-approval guard hold for "J. Rivera" vs "j.  rivera". It cannot
    stop deliberate impersonation; that needs real identity, not a string.
    """
    return " ".join(str(value).split()).casefold()


@app.post("/crm/workflow")
def crm_workflow(req: CRMWorkflowReq, request: Request) -> dict:
    event = req.event.strip().lower()
    if event not in _CRM_EVENTS:
        raise HTTPException(status_code=422, detail="Unsupported CRM workflow event.")
    actor = req.actor.strip()
    if not actor:
        raise HTTPException(status_code=422, detail="actor is required.")
    if event == "override_requested" and not req.justification.strip():
        raise HTTPException(
            status_code=422,
            detail="An override request requires a justification.",
        )
    if event == "outcome_recorded" and req.outcome not in {"closed_won", "closed_lost"}:
        raise HTTPException(
            status_code=422,
            detail="outcome_recorded requires closed_won or closed_lost.",
        )
    customer = _customer_ref(request)
    history = _crm_deal_history(customer, req.deal_id)
    previous_payload = (history[0].get("payload") or {}) if history else {}
    previous_event = str(previous_payload.get("event") or "")
    decides_override = event in {"approved", "rejected"}
    if decides_override and previous_event != "override_requested":
        raise HTTPException(
            status_code=409,
            detail="Approve or reject only after an override request.",
        )
    if event == "outcome_recorded":
        raise HTTPException(
            status_code=409,
            detail="Outcomes are reconciled from Salesforce on the next sync.",
        )
    if decides_override:
        # A decision resolves the terms that were actually requested, so the
        # recorded override request is authoritative and live guidance is not
        # consulted at all. Recomputing it here would strand a pending approval
        # whenever the opportunity leaves the open set (it closed, or the org
        # dropped below the evidence floor), and a percentage posted at
        # approval time would silently replace what the rep asked for.
        if req.requested_discount_pct is not None:
            raise HTTPException(
                status_code=422,
                detail=("Approve or reject decides the recorded override terms; "
                        "requested_discount_pct cannot be restated at approval."),
            )
        if _normalized_actor(actor) == _normalized_actor(
            previous_payload.get("actor") or ""
        ):
            raise HTTPException(
                status_code=409,
                detail=("This actor requested the override; approving or "
                        "rejecting it requires a different person."),
            )
        verdict = dict(previous_payload.get("verdict") or {})
        if not verdict:
            raise HTTPException(
                status_code=409,
                detail="The pending override request has no recorded terms to decide.",
            )
        guidance: dict = {
            "opportunity_id": req.deal_id,
            "account": str(previous_payload.get("account") or ""),
            "evidence_source": "persisted_override_request",
        }
    else:
        try:
            guidance = crm_mod.selected_guidance(
                req.records, req.deal_id,
                policy_threshold_pct=req.policy_threshold_pct,
            )
        except crm_mod.CRMDataError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        recommended_pct = float(guidance["recommended_discount"]) * 100.0
        current_pct = float(guidance["current_discount"]) * 100.0
        if event == "accepted":
            requested_pct = recommended_pct
        elif req.requested_discount_pct is not None:
            requested_pct = float(req.requested_discount_pct)
        else:
            requested_pct = current_pct
        if not (0.0 <= requested_pct <= governance_mod.EXCEPTION_MAX_PCT):
            raise HTTPException(
                status_code=422,
                detail=("requested_discount_pct must be between 0 and "
                        f"{governance_mod.EXCEPTION_MAX_PCT:g}."),
            )
        guardrail_pct = float(guidance["reference_discount"]) * 100.0
        verdict = {
            "requested_pct": requested_pct,
            "recommended_pct": recommended_pct,
            "guardrail_pct": guardrail_pct,
            "outside_guardrail": requested_pct > guardrail_pct,
            "price_to_retain": max(
                0.0,
                (requested_pct - recommended_pct) / 100.0
                * float(guidance["list_acv"]),
            ),
            "reference_basis": guidance["reference_basis"],
            "current_band": guidance["current_band"],
            "recommended_band": guidance["recommended_band"],
            "historical_win_rate_at_requested_band": guidance[
                "win_rate_at_current_band"
            ],
            "historical_win_rate_at_recommended_band": guidance[
                "win_rate_at_recommended_band"
            ],
            "caveat": guidance["caveat"],
            # The live path scores against historical band win rates, not the
            # modeled EV curve. Labeled so an approver is never shown demo-grade
            # math implicitly (Gap 2 honesty).
            "method": "band_guardrail",
        }
    effective_justification = (
        req.justification.strip()
        or str(previous_payload.get("justification") or "")
    )
    payload = {
        "source": "salesforce_crm",
        "event": event,
        "deal_id": req.deal_id,
        "account": guidance["account"],
        "actor": actor,
        # Actor is typed by the operator, not proven by an authenticated
        # session. The audit record says so rather than implying otherwise.
        "actor_assertion": "self_asserted",
        "justification": effective_justification,
        "outcome": req.outcome,
        "verdict": verdict,
    }
    row = governance_mod.STORE.insert(
        kind="exception",
        deal_id=req.deal_id,
        payload=payload,
        decision=event,
        justification=effective_justification,
        requested_by=req.actor.strip(),
        customer_ref=customer,
    )
    return {
        "id": str(row["id"]),
        "event": event,
        "guidance": guidance,
        "verdict": verdict,
        "created_at": str(row["created_at"]),
        "persisted": bool(row.get("persisted", False)),
    }


class CRMOutcome(BaseModel):
    deal_id: str
    account: str = ""
    outcome: str


class CRMReconcileReq(BaseModel):
    outcomes: list[CRMOutcome]


@app.post("/crm/reconcile")
def crm_reconcile(req: CRMReconcileReq, request: Request) -> dict:
    """Close the loop from Salesforce truth on each live sync.

    Only deals already present in the Pricekeel CRM workflow are eligible; a
    closed Opportunity that never had a decision is not silently added.
    """
    customer = _customer_ref(request)
    added = []
    outcomes = [
        item for item in req.outcomes[:5000]
        if item.outcome in {"closed_won", "closed_lost"}
    ]
    latest_by_deal = governance_mod.STORE.latest_by_deal(
        kind="exception",
        deal_ids=[item.deal_id for item in outcomes],
        source="salesforce_crm",
        customer_ref=customer,
    )
    for item in outcomes:
        latest = latest_by_deal.get(item.deal_id)
        if not latest:
            continue
        latest_payload = latest.get("payload") or {}
        if latest_payload.get("event") == "outcome_recorded":
            continue
        prior_event = str(latest_payload.get("event") or "")
        if prior_event not in {
            "flagged", "accepted", "override_requested", "approved", "rejected",
        }:
            continue
        payload = {
            "source": "salesforce_crm",
            "event": "outcome_recorded",
            "deal_id": item.deal_id,
            "account": item.account,
            "actor": "Salesforce sync",
            "justification": "Outcome reconciled from Salesforce IsWon/IsClosed.",
            "outcome": item.outcome,
            "prior_event": prior_event,
            "verdict": latest_payload.get("verdict") or {},
        }
        row = governance_mod.STORE.insert(
            kind="exception",
            deal_id=item.deal_id,
            payload=payload,
            decision="outcome_recorded",
            justification=payload["justification"],
            requested_by="Salesforce sync",
            customer_ref=customer,
        )
        added.append({
            "id": str(row["id"]),
            "deal_id": item.deal_id,
            "outcome": item.outcome,
        })
    return {"added": added, "count": len(added)}


class CRMWritebackReq(BaseModel):
    deal_id: str
    actor: str
    action_event: str
    success: bool
    task_id: str = ""
    error: str = ""


@app.post("/crm/writeback")
def crm_writeback(req: CRMWritebackReq, request: Request) -> dict:
    """Append the Salesforce Task attempt/result without mutating the decision."""
    if req.action_event not in {"flagged", "accepted", "override_requested", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Unsupported writeback action event.")
    customer = _customer_ref(request)
    history = _crm_deal_history(customer, req.deal_id)
    if not history:
        raise HTTPException(status_code=409, detail="Writeback requires a recorded decision.")
    decision_payload = history[0].get("payload") or {}
    if decision_payload.get("event") != req.action_event:
        raise HTTPException(
            status_code=409,
            detail="Writeback result does not match the latest recorded decision.",
        )
    event = "salesforce_writeback_succeeded" if req.success else "salesforce_writeback_failed"
    payload = {
        "source": "salesforce_crm_writeback",
        "event": event,
        "deal_id": req.deal_id,
        "account": str(decision_payload.get("account") or ""),
        "actor": req.actor.strip(),
        "actor_assertion": "self_asserted",
        "justification": f"Salesforce Task writeback for {req.action_event}.",
        "outcome": "",
        "verdict": decision_payload.get("verdict") or {},
        "writeback": {
            "action_event": req.action_event,
            "success": req.success,
            "task_id": req.task_id.strip()[:200] if req.success else "",
            "error": req.error.strip()[:1000] if not req.success else "",
        },
    }
    row = governance_mod.STORE.insert(
        kind="exception",
        deal_id=req.deal_id,
        payload=payload,
        decision=event,
        justification=payload["justification"],
        requested_by=req.actor.strip(),
        customer_ref=customer,
    )
    return {
        "id": str(row["id"]),
        "event": event,
        "persisted": bool(row.get("persisted", False)),
    }


@app.get("/crm/workflow")
def crm_workflow_log(request: Request, limit: int = 100) -> dict:
    rows = governance_mod.STORE.list(
        kind="exception",
        limit=max(1, min(int(limit), 200)),
        customer_ref=_customer_ref(request),
    )
    items = []
    for row in rows:
        payload = row.get("payload") or {}
        if payload.get("source") not in {"salesforce_crm", "salesforce_crm_writeback"}:
            continue
        items.append({
            "id": str(row.get("id", "")),
            "deal_id": str(row.get("deal_id", "")),
            "event": str(payload.get("event", row.get("decision", ""))),
            "account": str(payload.get("account", "")),
            "actor": str(payload.get("actor", row.get("requested_by", ""))),
            "justification": str(payload.get("justification", "")),
            "outcome": str(payload.get("outcome", "")),
            "verdict": payload.get("verdict") or {},
            "writeback": payload.get("writeback") or {},
            "created_at": str(row.get("created_at", "")),
        })
    return {"items": items[:limit]}


# --- Product Matching v1: your pricing page vs your named competitors ------
# Customer enters their own pricing-page URL + up to ~8 competitor URLs.
# We fetch each page once (cached), extract structured plans via the LLM in
# JSON-mode, and match competitor plans to the customer's plans with an
# embedding+fuzzy scorer. NOT a market-wide scraper — only the customer's
# named competitors.

class CompareReq(BaseModel):
    my_url: str
    competitor_urls: list[str] = []


class CompetitorContextReq(BaseModel):
    url: str
    competitor_name: str = ""
    source_type: str = "other"


@app.post("/matching/competitor")
def matching_competitor(req: dict) -> dict:
    """Extract structured plans from a single competitor pricing URL.

    Useful as a one-shot probe so the UI can show 'we found 3 plans on
    this URL' before the user commits to a full comparison.
    """
    url = (req.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    vendor, plans = matching_mod.extract_plans_from_url(url)
    return {
        "url": url,
        "vendor": vendor,
        "plans": [p.to_dict() for p in plans],
    }


@app.post("/matching/compare")
def matching_compare(req: CompareReq) -> dict:
    """End-to-end comparison: customer's pricing page vs N competitor pages."""
    if not req.my_url.strip():
        raise HTTPException(status_code=400, detail="Missing my_url")
    competitor_urls = [u.strip() for u in req.competitor_urls if u and u.strip()]
    comp = matching_mod.compare(req.my_url.strip(), competitor_urls)
    return comp.to_dict()


@app.post("/matching/context")
def matching_context(req: CompetitorContextReq) -> dict:
    """Sourced qualitative context from one customer-named public URL.

    The result carries the source URL and never feeds numerical CRM guidance.
    """
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    allowed_types = {
        "pricing", "documentation", "release_notes", "case_study",
        "funding", "executive_interview", "investor_material", "other",
    }
    source_type = req.source_type.strip().lower()
    if source_type not in allowed_types:
        raise HTTPException(status_code=422, detail="Unsupported source_type")
    try:
        return matching_mod.extract_competitor_context(
            url,
            competitor_name=req.competitor_name,
            source_type=source_type,
        )
    except matching_mod.FetchBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except (ValueError, requests.RequestException) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


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
        "comparables": _records(model.comparable_deals(df, idx)),
        "band_context": model.band_context(df, idx, rec["recommended_discount"]),
        "confidence": {
            "auc": tm.metrics["auc"],
            "mean_pred": tm.metrics["mean_pred"],
            "base_rate": tm.metrics["base_rate"],
            "n_train": tm.metrics["n_train"],
        },
        "curve": _records(curve),
    }
