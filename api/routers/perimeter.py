"""Perimeter component: `/` and `/health`, plus the caller-identity helpers
the http middleware and the tenant-scoped routers both need.

The rate-limit state, the upload-size cap, and the `perimeter` http
middleware itself stay in api/main.py rather than here. That is a deliberate
exception to the "one component -> one router file" rule (see the note at
the top of api/main.py): tests/test_api_perimeter.py (a frozen contract,
task PK-1 acceptance criterion 2) monkeypatches attributes such as
`main.RATE_LIMITS` and `main.MAX_UPLOAD_BYTES` and expects that to change
live behavior. A function only sees a monkeypatched module attribute when
the function itself was *defined* in that module (Python binds a function's
free variables to its defining module's globals, not to wherever it is
later imported) — so anything the tests patch on `main` has to actually
live in main.py, not be re-exported from here.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from pricing import assist

router = APIRouter()

# Tenant scope (Finding 3). The web proxy sets X-Pricekeel-Customer per signed-in
# customer; absent => "default" so single-tenant behavior is unchanged. Every
# decision-log write and read is scoped by this value so one customer's log is
# invisible to another.
CUSTOMER_HEADER = "x-pricekeel-customer"


def _customer_ref(request: Request) -> str:
    """Tenant key from X-Pricekeel-Customer; 'default' when absent/blank."""
    return (request.headers.get(CUSTOMER_HEADER, "") or "").strip() or "default"


def _client_ip(request: Request) -> str:
    """Caller IP. Render sits behind a proxy, so trust the first
    X-Forwarded-For value; fall back to the socket peer."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff.strip():
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/")
def root() -> dict:
    """Friendly landing so visiting the API root is not a bare 404."""
    return {
        "service": "Pricekeel API",
        "note": "This is the data service, not the app. Open the web UI at "
                "http://localhost:3000.",
        "endpoints": ["/health", "/demo", "/docs"],
    }


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "llm": assist.has_llm()}
