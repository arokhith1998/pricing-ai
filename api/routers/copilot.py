"""Copilot v2 component: /copilot/canonical (GET+POST), /copilot/log,
/copilot/decisions.

The copilot turns the analysis into a ranked list of Opportunity objects
(revenue impact + confidence + evidence) and asks the LLM to narrate them.
Every dollar figure is deterministic; the LLM never invents numbers.

`_customer_ref` (tenant scoping) is owned by the perimeter component and
stays defined in api/main.py (see api/main.py's docstring). It is reached
here via a deferred `from api import main` inside each endpoint, the same
pattern api/routers/diagnostic.py uses for `_read_capped`, because a
module-level import would try to import api.main while it is still
mid-import (main.py imports this router).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from pricing import copilot as copilot_mod
from pricing import governance as governance_mod
from api.shared import DEMO_CSV, diagnostic_payload

router = APIRouter()


class CanonicalReq(BaseModel):
    qid: str
    session_id: str | None = None
    analysis: dict | None = None
    min_impact_usd: float = 0.0


@router.get("/copilot/canonical")
def copilot_canonical_list() -> dict:
    """The six canonical questions the UI surfaces as chips."""
    return {"questions": copilot_mod.CANONICAL_QUESTIONS}


@router.post("/copilot/canonical")
def copilot_canonical(req: CanonicalReq, request: Request) -> dict:
    """Deterministic opportunities + LLM narrative for one canonical question."""
    from api import main  # deferred: see module docstring
    analysis = req.analysis if req.analysis is not None else diagnostic_payload(
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
            customer_ref=main._customer_ref(request),
        )
    return ans.to_dict()


class DecisionLogReq(BaseModel):
    session_id: str = Field(..., max_length=120)
    qid: str
    # No canonical question ever surfaces more than 5 opportunities (see
    # pricing/copilot.py's per-kind slices), so an accept/reject list past a
    # couple dozen is already suspect; 50 is a generous cap that still bounds
    # an unauthenticated caller's write into Neon (same class of gap fixed on
    # /exceptions' justification/requested_by).
    accepted: list[str] = Field(default_factory=list, max_length=50)
    rejected: list[str] = Field(default_factory=list, max_length=50)
    note: str = Field("", max_length=2000)


@router.post("/copilot/log")
def copilot_log(req: DecisionLogReq, request: Request) -> dict:
    """Log a copilot decision. Same response contract as before; storage now
    goes through pricing/governance.py (Neon when configured, memory
    fallback) instead of a process-lifetime dict. Scoped to the tenant."""
    from api import main  # deferred: see module docstring
    d = governance_mod.log_copilot_decision(
        req.session_id, req.qid,
        accepted=req.accepted, rejected=req.rejected, note=req.note,
        customer_ref=main._customer_ref(request),
    )
    return {"logged": True, "decision": d}


@router.get("/copilot/decisions")
def copilot_decisions(session_id: str, request: Request) -> dict:
    from api import main  # deferred: see module docstring
    return {
        "session_id": session_id,
        "decisions": governance_mod.copilot_decisions(
            session_id, customer_ref=main._customer_ref(request)),
    }
