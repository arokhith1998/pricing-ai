"""Governance loop component: /exceptions (GET+POST), /digest.

The subscription use case: a deal-desk rep requests a below-floor discount,
Pricekeel returns the priced verdict (same EV-curve math as /recommend, no
LLM) and logs the decision; /digest re-surfaces the week's activity. Every
number is deterministic; storage via pricing/governance.py (Neon when
configured, in-memory fallback).

Percent convention (documented contract): requested_discount_pct and every
*_pct field in the verdict and digest are percent 0-100: 22.5 means a
22.5 percent discount, the default floor_pct is 15.0. Win probabilities are
0-1 fractions; ev_delta_vs_recommended is dollars.

`_customer_ref` (tenant scoping) is owned by the perimeter component and
stays defined in api/main.py (see api/main.py's docstring). It is reached
here via a deferred `from api import main` inside each endpoint, the same
pattern api/routers/diagnostic.py uses for `_read_capped`, because a
module-level import would try to import api.main while it is still
mid-import (main.py imports this router).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from pricing import governance as governance_mod
from pricing.diagnostic import run
from api.shared import DEMO_CSV, engine

logger = logging.getLogger("pricekeel.api")

router = APIRouter()


class ExceptionReq(BaseModel):
    deal_id: str
    # Percent 0-100 (22.5 = a 22.5 percent discount). Valid range 0-40, the
    # discount grid the win model sweeps.
    requested_discount_pct: float
    justification: str = ""
    requested_by: str = ""


@router.post("/exceptions")
def create_exception(req: ExceptionReq, request: Request) -> dict:
    """Score a discount-exception request against the deal's own EV curve,
    log it, and return the verdict. requested_discount_pct is percent 0-100.

    Response shape: {id, verdict, created_at, persisted}. `persisted` is True
    when the decision was written durably to the database, False when it landed
    in the in-memory fallback (database unset or unreachable) — the response
    never claims durability it does not have (Finding 5). The write is scoped to the
    caller's tenant via X-Pricekeel-Customer (Finding 3)."""
    from api import main  # deferred: see module docstring
    if not (0.0 <= req.requested_discount_pct
            <= governance_mod.EXCEPTION_MAX_PCT):
        raise HTTPException(
            status_code=422,
            detail=(f"requested_discount_pct must be between 0 and "
                    f"{governance_mod.EXCEPTION_MAX_PCT:g} (percent of list "
                    f"price; the modeled discount range)."),
        )
    df, tm = engine()
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
        customer_ref=main._customer_ref(request),
    )
    return {"id": str(row["id"]), "verdict": verdict,
            "created_at": str(row["created_at"]),
            "persisted": bool(row.get("persisted", False))}


@router.get("/exceptions")
def list_exceptions(request: Request, limit: int = 50) -> dict:
    """Recent exception requests, newest first, with their logged verdicts.
    Scoped to the caller's tenant via X-Pricekeel-Customer (Finding 3)."""
    from api import main  # deferred: see module docstring
    rows = governance_mod.STORE.list(kind="exception",
                                     limit=max(1, min(int(limit), 200)),
                                     customer_ref=main._customer_ref(request))
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
# keyed on the CSV's mtime (same pattern as api.shared.engine) so an
# unmetered GET is not a full ingest+diagnostic every time.
_DIGEST_BOOK: dict = {"mtime": None, "analysis": None}


@router.get("/digest")
def digest(request: Request) -> dict:
    """Weekly governance digest: decision-log activity over the last 7 days
    plus the loaded book's diagnostic aggregates. Deterministic, no LLM.
    Discount/realization figures are percent 0-100, matching /exceptions.
    Scoped to the caller's tenant via X-Pricekeel-Customer (Finding 3)."""
    from api import main  # deferred: see module docstring
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
    except Exception:  # noqa: BLE001  (digest must degrade, not 500)
        logger.warning("digest: book diagnostics unavailable", exc_info=True)
    result = governance_mod.build_digest(analysis=analysis, window_days=7,
                                         customer=main._customer_ref(request))
    # CONTRACT B: no per-tenant book is persisted yet, so the book-diagnostics
    # half above is always computed from the bundled demo CSV regardless of
    # tenant. Disclose that explicitly so a caller never mistakes these
    # realization/excess figures for this tenant's own book.
    result["book_source"] = "demo"
    return result
