"""Salesforce / CRM-native workflow component: /crm/*.

OAuth, token refresh, SOQL, and field-level access stay in the Next.js
server tier. This API receives canonical rows over the existing shared-secret
perimeter, computes deterministic analytics, discards the rows, and persists
only workflow events in the append-only decision log.

`crm_mod` is re-exported as `api.main.crm_mod` (see api/main.py) purely so
tests/test_crm.py's `monkeypatch.setattr(main.crm_mod, "selected_guidance",
...)` keeps working: it patches the shared pricing.crm module object, which
is the same object this file calls through, so the patch is visible here
regardless of which file the route handler lives in.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from pricing import crm as crm_mod
from pricing import governance as governance_mod
from api.routers.perimeter import _customer_ref
from api.shared import _analysis_payload

router = APIRouter()


class CRMAnalyzeReq(BaseModel):
    records: list[dict]
    policy_threshold_pct: float = 15.0
    # CONTRACT A: the customer has explicitly mapped a real pre-discount
    # Salesforce list field (not left it defaulting to Amount), so a
    # near-zero-discount book is honest discounting, not a mapping error.
    # Skips _guard_degenerate_list when True; the hard block stays on by
    # default so a silent mapping failure never reads as zero leakage.
    list_field_mapped: bool = False


@router.post("/crm/analyze")
def crm_analyze(req: CRMAnalyzeReq) -> dict:
    try:
        result = crm_mod.analyze_records(
            req.records, policy_threshold_pct=req.policy_threshold_pct,
            list_field_mapped=req.list_field_mapped,
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


@router.post("/crm/workflow")
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
                list_field_mapped=req.list_field_mapped,
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


@router.post("/crm/reconcile")
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


@router.post("/crm/writeback")
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


@router.get("/crm/workflow")
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
