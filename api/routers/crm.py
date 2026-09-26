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

`_customer_ref` (tenant scoping) is owned by the perimeter component and
stays defined in api/main.py (see api/main.py's docstring). It is reached
here via a deferred `from api import main` inside each endpoint, the same
pattern api/routers/diagnostic.py uses for `_read_capped`, because a
module-level import would try to import api.main while it is still
mid-import (main.py imports this router).
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from pricing import crm as crm_mod
from pricing import governance as governance_mod
from api.shared import analysis_payload

logger = logging.getLogger("pricekeel.api.crm")

router = APIRouter()


# --- evidence_version (CTO finding 4) ----------------------------------------
#
# The acceptance criteria for the CRM workflow promise a persisted evidence
# version on every verdict so a past recommendation is checkable against the
# exact book, policy, engine, and code that produced it. None existed. This
# fingerprints what produced the number, not the number itself: two runs over
# the same book, threshold, and code land on the same hash, and changing any
# one input changes it.

_SYNC_TIMESTAMP_KEYS = ("synced_at", "last_modified_date", "systemmodstamp")


def _git_sha() -> str:
    """The deployed commit, for the evidence fingerprint. PRICEKEEL_GIT_SHA
    or Render's own RENDER_GIT_COMMIT win when set (cheap, no subprocess in
    the request path on a real deploy); `git rev-parse` is the local-dev
    fallback; "unknown" means neither was available."""
    for var in ("PRICEKEEL_GIT_SHA", "RENDER_GIT_COMMIT"):
        sha = os.environ.get(var, "").strip()
        if sha:
            return sha
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2, check=True,
        )
        sha = out.stdout.strip()
        if sha:
            return sha
    except Exception:  # noqa: BLE001, evidence_version must degrade, not 500
        pass
    return "unknown"


def _max_sync_timestamp(records: list[dict]) -> str:
    """Latest per-record sync/modification timestamp across the supplied
    book, when the caller provides one. The current Salesforce adapter sends
    no such field per record, so this reads "none" today; it activates the
    moment one of these keys appears on a record, and that presence is
    itself part of the fingerprint (a book with real sync timestamps hashes
    differently from one without)."""
    values = [
        str(row[key])
        for row in records
        for key in _SYNC_TIMESTAMP_KEYS
        if row.get(key)
    ]
    return max(values) if values else "none"


def evidence_version(records: list[dict], policy_threshold_pct: float,
                     method: str) -> str:
    """Reproducibility fingerprint for a CRM verdict: record count, max sync
    timestamp, policy threshold, engine label, and git SHA, hashed together."""
    fingerprint = "|".join([
        f"records={len(records)}",
        f"max_sync={_max_sync_timestamp(records)}",
        f"policy_threshold_pct={float(policy_threshold_pct):g}",
        f"method={method}",
        f"git_sha={_git_sha()}",
    ])
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]


def _insert_or_fail_closed(*, kind: str, deal_id: str, payload: dict,
                           decision: str, justification: str,
                           requested_by: str, customer_ref: str) -> dict:
    """Append a CRM workflow decision-log row; fail closed in production
    instead of quietly degrading (CTO finding 3, code-reviewer finding 1).

    A CRM workflow event (override request, approval, rejection, outcome
    reconciliation, writeback receipt) IS the audit trail this product sells;
    a write that lands in the in-memory fallback there is not durable and
    must not be reported as a 200. The demo /exceptions path and copilot
    logging keep the memory fallback with a 200 (Finding 5's original
    behavior) since those are not price-affecting workflow decisions.

    Always logs a warning naming the event on a fallback, in dev too, so a
    local operator sees the same signal production would alert on; only
    raises 503 when `main._is_prod()`.
    """
    row = governance_mod.STORE.insert(
        kind=kind, deal_id=deal_id, payload=payload, decision=decision,
        justification=justification, requested_by=requested_by,
        customer_ref=customer_ref,
    )
    if not row.get("persisted", False):
        logger.warning(
            "CRM workflow event %r for deal %s fell back to the in-memory "
            "decision log (DATABASE_URL unset or unreachable); this write "
            "is not durable.", payload.get("event", decision), deal_id,
        )
        from api import main  # deferred: see module docstring
        if main._is_prod():
            raise HTTPException(
                status_code=503,
                detail=(
                    "The decision log could not be durably written, so this "
                    "CRM workflow action was not recorded. Try again shortly."
                ),
            )
    return row


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
        "analysis": analysis_payload(result["analysis"]),
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
    # Operator-typed free text, unbounded before this cap (code-reviewer
    # finding 2): an unauthenticated caller could write arbitrarily large
    # strings into the decision log on every request.
    actor: str = Field("", max_length=120)
    justification: str = Field("", max_length=2000)
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
    from api import main  # deferred: see module docstring
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
    customer = main._customer_ref(request)
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
        # Fingerprints the book, threshold, and code that produced this
        # verdict (CTO finding 4). The approval/rejection branch above copies
        # the override request's stored verdict rather than recomputing one,
        # so it carries this same evidence_version through unchanged; that is
        # correct; a decision is made on the evidence that was captured at
        # request time, not on a fresh fetch the approver happens to submit.
        verdict["evidence_version"] = evidence_version(
            req.records, req.policy_threshold_pct, verdict["method"],
        )
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
    row = _insert_or_fail_closed(
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
    from api import main  # deferred: see module docstring
    customer = main._customer_ref(request)
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
        row = _insert_or_fail_closed(
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
    from api import main  # deferred: see module docstring
    if req.action_event not in {"flagged", "accepted", "override_requested", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Unsupported writeback action event.")
    customer = main._customer_ref(request)
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
    row = _insert_or_fail_closed(
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
    from api import main  # deferred: see module docstring
    rows = governance_mod.STORE.list(
        kind="exception",
        limit=max(1, min(int(limit), 200)),
        customer_ref=main._customer_ref(request),
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
