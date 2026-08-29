"""Pricekeel API. Thin FastAPI wrapper over the pricing/ engine.

The Next.js front end calls this; the analytics are NOT reimplemented here.
Run:  uvicorn api.main:app --reload --port 8000

This module is the app entry point and owns the API perimeter: the CORS +
shared-secret + rate-limit middleware, the upload-size cap, and the
LLMUnavailableError handler. Everything else is split into api/routers/*.py
by component (diagnostic, model, rag, copilot, governance, crm) so two
unrelated backend changes stop colliding on one 1400-line file — see
api/routers/perimeter.py's docstring and the PK-1 task notes for why.

Why the perimeter state stays HERE instead of moving to
api/routers/perimeter.py too: tests/test_api_perimeter.py (a frozen
contract) does things like `monkeypatch.setattr(main, "RATE_LIMITS", ...)`
and `monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", ...)` and expects that to
change live request handling. A Python function only ever reads a module's
CURRENT global value when the function itself was *defined* in that module
(its `__globals__` is fixed at def time, not at wherever it is later
imported) — so anything the tests patch on `main` has to be both defined
and read from here. Routers that need the same constants at request time
(api/routers/diagnostic.py, api/routers/rag.py) do a deferred
`from api import main` inside the endpoint function itself, which is safe
because by the time a real request arrives this module has always finished
importing.

`/matching/*` is intentionally NOT split into its own router: it is not one
of the seven components in the PK-1 task table (perimeter, diagnostic,
model, rag, copilot, governance, crm), and tests/test_crm.py /
tests/test_api_perimeter.py patch `main.matching_mod` / `main.crm_mod`
directly, which only works cleanly if those modules stay reachable as
attributes of `main` the way they already were.
"""

from __future__ import annotations

import hmac
import logging
import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import requests
from pricing import assist
from pricing import crm as crm_mod
from pricing import matching as matching_mod

from api.routers import copilot, crm, diagnostic, governance, model, perimeter, rag

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

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
UPLOAD_PATHS = {"/map-headers", "/diagnostic", "/docs/upload"}

# Per-request caps for the multi-file docs upload (Finding 4). The single-file
# byte cap (_read_capped) and the chunk-count cap (rag._doc_store_append) do
# not bound how MANY files or how many TOTAL bytes one request carries.
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
    # LLM-backed (audit P2 #2): same tier as /ask, /summary, /matching/.
    "/copilot/canonical": (10, 60.0),
    "/map-columns": (10, 60.0),
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
async def perimeter_middleware(request: Request, call_next):
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
                                              perimeter._client_ip(request))
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


async def _read_capped(file: UploadFile) -> bytes:
    """Read an upload, hard-capped at MAX_UPLOAD_BYTES.

    Backstop behind the Content-Length middleware check — a client can lie
    about (or omit) Content-Length, so we also bound the actual bytes read
    before any parsing happens. Called by api/routers/diagnostic.py and
    api/routers/rag.py via a deferred `from api import main` (see the module
    docstring above for why it lives here and not there).
    """
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(f"Upload too large "
                    f"(limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)."),
        )
    return content


app.include_router(perimeter.router)
app.include_router(diagnostic.router)
app.include_router(model.router)
app.include_router(rag.router)
app.include_router(copilot.router)
app.include_router(governance.router)
app.include_router(crm.router)


# --- Product Matching v1: your pricing page vs your named competitors ------
# Customer enters their own pricing-page URL + up to ~8 competitor URLs.
# We fetch each page once (cached), extract structured plans via the LLM in
# JSON-mode, and match competitor plans to the customer's plans with an
# embedding+fuzzy scorer. NOT a market-wide scraper — only the customer's
# named competitors.
#
# Left on the app directly (not split into a router): not one of the seven
# PK-1 components, and this keeps `main.matching_mod` a real attribute for
# tests/test_api_perimeter.py's monkeypatch.

# /matching/compare fans out one LLM call per URL (my_url + each competitor).
# Cap the total so a large list can't turn one request into an unbounded
# fetch+LLM bill; "usually 3-8" per the note above.
MAX_COMPARE_URLS = 8


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
    # Reject BEFORE any fetch/LLM call: my_url + competitor_urls together
    # drive N+1 page fetches and N+1 LLM extraction calls.
    total_urls = 1 + len(competitor_urls)
    if total_urls > MAX_COMPARE_URLS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Too many URLs ({total_urls}): my_url plus competitor_urls "
                f"must total at most {MAX_COMPARE_URLS}."
            ),
        )
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
