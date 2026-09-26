"""Pricekeel API. Thin FastAPI wrapper over the pricing/ engine.

The Next.js front end calls this; the analytics are NOT reimplemented here.
Run:  uvicorn api.main:app --reload --port 8000

This module is the app entry point and owns the API perimeter: the CORS +
shared-secret + rate-limit middleware, the caller-identity helpers, the
upload-size cap, and the LLMUnavailableError handler. Everything else is
split into api/routers/*.py by component (perimeter, diagnostic, model,
rag, copilot, governance, crm, matching) so two unrelated backend changes
stop colliding on one 1400-line file. See api/routers/perimeter.py's
docstring and the PK-1 task notes for why.

Why the perimeter state stays HERE instead of moving to
api/routers/perimeter.py too: tests/test_api_perimeter.py (a frozen
contract) does things like `monkeypatch.setattr(main, "RATE_LIMITS", ...)`
and `monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", ...)` and expects that to
change live request handling. A Python function only ever reads a module's
CURRENT global value when the function itself was *defined* in that module
(its `__globals__` is fixed at def time, not at wherever it is later
imported), so anything the tests patch on `main` has to be both defined and
read from here. The same rule is why `_customer_ref` and `_client_ip` live
here too, not in api/routers/perimeter.py: nothing patches them today, but
they sit on the security perimeter (tenant scoping on every governance,
copilot and CRM write; X-Forwarded-For trust and rate-limit bucketing), and
a future `monkeypatch.setattr(main, "_client_ip", ...)` landing on a
re-exported copy elsewhere would be silently inert. Routers that need
main's state at request time (api/routers/diagnostic.py, rag.py, crm.py,
governance.py, copilot.py) do a deferred `from api import main` inside the
endpoint function itself, which is safe because by the time a real request
arrives this module has always finished importing.

`/matching/*` lives in api/routers/matching.py like every other component.
`main.matching_mod` (`from pricing import matching as matching_mod` below)
stays as a re-export purely so tests/test_api_perimeter.py's
`monkeypatch.setattr(main.matching_mod, "compare", ...)` keeps working: it
patches the shared pricing.matching module object, the same object
api/routers/matching.py calls through, so the patch is visible there
regardless of which file the route handler lives in. That attribute needs
only the module-level import, not the route handlers staying inline (see
api/routers/crm.py's docstring, which makes the identical point for
`crm_mod`).
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

from pricing import assist
from pricing import crm as crm_mod  # noqa: F401  (re-exported for tests/test_crm.py)
from pricing import matching as matching_mod  # noqa: F401  (re-exported for tests/test_api_perimeter.py)

from api.routers import (
    copilot,
    crm,
    diagnostic as diagnostic_router,
    governance,
    matching,
    model as model_router,
    perimeter as perimeter_router,
    rag,
)

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
# Exact paths, or path prefixes (trailing "/", matched the same way as
# RATE_LIMITS below). /crm/* JSON bodies were unguarded here (backend-engineer
# finding 3): CRMAnalyzeReq.records/CRMReconcileReq.outcomes had no
# perimeter-level cap, so Starlette and pydantic fully deserialized an
# oversized body into memory before pricing.crm.MAX_CRM_RECORDS ever saw it.
UPLOAD_PATHS = {"/map-headers", "/diagnostic", "/docs/upload", "/crm/"}


def _matches_prefixed_path(path: str, rules: set[str]) -> bool:
    """Exact match, or prefix match for a rule ending in '/' (same convention
    as _rate_rule_for)."""
    return any(path == rule or (rule.endswith("/") and path.startswith(rule))
              for rule in rules)

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
    # (POST only: the middleware never limits GET, so reads stay unmetered.)
    "/exceptions": (30, 60.0),
    # /recommend runs the same model sweep as /exceptions and was the one
    # uncapped model-cost endpoint (backend-engineer finding 4); same rate.
    "/recommend": (30, 60.0),
    "/crm/": (20, 60.0),
    # LLM-backed (audit P2 #2): same tier as /ask, /summary, /matching/.
    "/copilot/canonical": (10, 60.0),
    "/map-columns": (10, 60.0),
}
# (rule, key) -> deque of request timestamps inside the window. This is a
# plain in-process dict (backend-engineer finding 6, code-reviewer finding 5):
# on more than one worker or Render instance it is not shared, so the
# effective limit becomes limit * process_count. There is no cross-process
# rate-limit store today; disclosed here rather than silently assumed away.
_RATE_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def _is_prod() -> bool:
    """Production unless PRICEKEEL_ENV is explicitly 'dev' (same rule CORS
    uses to fail closed on an unset env). Read at call time so Render env
    changes and tests take effect without re-import."""
    return os.environ.get("PRICEKEEL_ENV", "").lower() != "dev"


if not os.environ.get("PRICEKEEL_API_KEY"):
    logger.warning("API perimeter OPEN: set PRICEKEEL_API_KEY")


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


# Tenant scope (Finding 3). The web proxy sets X-Pricekeel-Customer per
# signed-in customer; absent -> "default" so single-tenant behavior is
# unchanged. Every decision-log write and read is scoped by this value so
# one customer's log is invisible to another. Defined here, not in
# api/routers/perimeter.py, for the same reason as RATE_LIMITS above: see
# the module docstring.
CUSTOMER_HEADER = "x-pricekeel-customer"


def _customer_ref(request: Request) -> str:
    """Tenant key from X-Pricekeel-Customer; 'default' when absent/blank."""
    return (request.headers.get(CUSTOMER_HEADER, "") or "").strip() or "default"


def _client_ip(request: Request) -> str:
    """Caller IP for rate-limit bucketing.

    X-Forwarded-For is trusted only when PRICEKEEL_TRUST_PROXY is set
    (code-reviewer finding 5): any caller can set that header itself, so
    trusting it unconditionally lets a client pick its own bucket, or a
    proxy that never forwards it (the Next.js tier did not) collapses every
    caller onto one shared IP. Set PRICEKEEL_TRUST_PROXY on the one deploy
    that actually sits behind a trusted reverse proxy (Render); everywhere
    else this falls back to the socket peer."""
    if os.environ.get("PRICEKEEL_TRUST_PROXY", "").strip():
        xff = request.headers.get("x-forwarded-for", "")
        if xff.strip():
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit_key(request: Request) -> str:
    """Bucket key for the rate limiter: the caller's tenant header when
    present, else client IP (code-reviewer finding 5). Keying on the tenant
    first means one tenant behind a NAT or shared proxy IP shares a single
    bucket, and an unrelated tenant on the same IP is not starved by it."""
    customer = request.headers.get(CUSTOMER_HEADER, "").strip()
    if customer:
        return f"customer:{customer}"
    return f"ip:{_client_ip(request)}"


@app.middleware("http")
async def perimeter_middleware(request: Request, call_next):
    path = request.url.path

    # 1) Shared-secret auth. CORS preflights (OPTIONS) carry no custom
    # headers by design, and they execute nothing: let them through.
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
    if _matches_prefixed_path(path, UPLOAD_PATHS) and request.method == "POST":
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

    # 3) Sliding-window rate limit on the expensive endpoints, keyed on
    # tenant (X-Pricekeel-Customer) with an IP fallback.
    rule = _rate_rule_for(path)
    if rule is not None and request.method == "POST":
        name, limit, window = rule
        retry_after = _rate_limit_retry_after(name, limit, window,
                                              _rate_limit_key(request))
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
# PRICEKEEL_ENV is EXPLICITLY "dev": an unset env var (e.g. a fresh Render
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
    # Vercel preview deployments: match `pricekeel-*-arokhith1998s-projects.vercel.app`.
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

    Backstop behind the Content-Length middleware check: a client can lie
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


app.include_router(perimeter_router.router)
app.include_router(diagnostic_router.router)
app.include_router(model_router.router)
app.include_router(rag.router)
app.include_router(copilot.router)
app.include_router(governance.router)
app.include_router(crm.router)
app.include_router(matching.router)
