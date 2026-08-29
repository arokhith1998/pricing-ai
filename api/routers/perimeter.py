"""Perimeter component: `/` and `/health`.

The caller-identity helpers (`_customer_ref`, `_client_ip`), the rate-limit
state, the upload-size cap, and the `perimeter` http middleware itself all
stay in api/main.py rather than here. That is a deliberate exception to the
"one component -> one router file" rule (see the note at the top of
api/main.py): tests/test_api_perimeter.py (a frozen contract, task PK-1
acceptance criterion 2) monkeypatches attributes such as `main.RATE_LIMITS`
and `main.MAX_UPLOAD_BYTES` and expects that to change live behavior. A
function only sees a monkeypatched module attribute when the function
itself was *defined* in that module (Python binds a function's free
variables to its defining module's globals, not to wherever it is later
imported), and a caller in a different module only sees a patch if it looks
the name up as `main.<name>` at call time rather than importing the object
by reference. So `_customer_ref` and `_client_ip` live in main.py too, even
though nothing patches them today: they sit on the security perimeter
(tenant scoping, rate-limit bucketing) and a silently-inert future patch
there is the exact failure mode this split exists to avoid. Callers in
other routers reach `_customer_ref` via a deferred `from api import main`
inside the endpoint function (see api/routers/crm.py, governance.py,
copilot.py), the same pattern api/routers/diagnostic.py already uses for
`_read_capped`.
"""

from __future__ import annotations

from fastapi import APIRouter

from pricing import assist

router = APIRouter()


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
