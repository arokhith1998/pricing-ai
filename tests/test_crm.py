"""CRM-native analysis tests: live-record boundary and open-deal guardrails."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main
from pricing import crm
from pricing import governance

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clean_crm_state(monkeypatch):
    for var in ("PRICEKEEL_API_KEY", "DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("PRICEKEEL_ENV", "dev")
    governance.STORE.reset_memory()
    main._rate_state_reset()
    yield
    governance.STORE.reset_memory()
    main._rate_state_reset()


@pytest.fixture()
def client():
    return TestClient(main.app)


def _guidance() -> dict:
    return {
        "opportunity_id": "SF-OPEN-001",
        "account": "Northstar Labs",
        "current_discount": 0.30,
        "recommended_discount": 0.15,
        "reference_discount": 0.15,
        "list_acv": 100_000.0,
        "reference_basis": "segment median",
        "current_band": "25-35%",
        "recommended_band": "10-20%",
        "win_rate_at_current_band": 0.4,
        "win_rate_at_recommended_band": 0.6,
        "caveat": "Historical evidence is correlational.",
    }


def _records() -> list[dict]:
    closed = pd.read_csv(ROOT / "data" / "synthetic" / "deals.csv").head(240)
    records = closed.to_dict(orient="records")
    for row in records:
        row["currency_iso"] = "USD"
        row["salesforce_url"] = f"/lightning/r/Opportunity/{row['opportunity_id']}/view"
    open_deal = dict(records[0])
    open_deal.update({
        "opportunity_id": "SF-OPEN-001",
        "account_name": "Northstar Labs",
        "outcome": "open",
        "list_acv": 100_000.0,
        "booked_acv": 70_000.0,
        "close_date": "2026-09-30",
        "salesforce_url": "/lightning/r/Opportunity/SF-OPEN-001/view",
    })
    records.append(open_deal)
    return records


def test_live_records_reuse_diagnostic_and_guide_open_deal():
    result = crm.analyze_records(_records(), policy_threshold_pct=15.0)

    assert result["analysis"]["overview"]["opportunities"] == 240
    assert result["readiness"]["open_usable"] == 1
    guide = result["guidance"][0]
    assert guide["opportunity_id"] == "SF-OPEN-001"
    assert guide["current_discount"] == pytest.approx(0.30)
    assert guide["recommended_discount"] <= guide["current_discount"]
    assert guide["price_to_retain"] >= 0
    assert guide["comparables"]
    assert "correlational" in guide["caveat"].lower()


def test_crm_refuses_mixed_currency_totals():
    records = _records()
    records[0]["currency_iso"] = "EUR"

    with pytest.raises(crm.CRMDataError, match="multiple Salesforce currencies"):
        crm.analyze_records(records)


def test_crm_refuses_thin_history():
    with pytest.raises(crm.CRMDataError, match="at least 30"):
        crm.analyze_records(_records()[:20])


def test_crm_refuses_degenerate_list():
    # Simulate the default-mapping failure: list value resolves to the booked
    # amount, so every closed deal shows zero discount. The engine must refuse
    # rather than report leakage as invisible.
    records = _records()
    for row in records:
        if row.get("outcome") in {"closed_won", "closed_lost"}:
            row["list_acv"] = row["booked_acv"]
    with pytest.raises(crm.CRMDataError, match="near-identical"):
        crm.analyze_records(records)


def test_selected_guidance_rejects_unknown_or_unusable_open_deal():
    with pytest.raises(crm.CRMDataError, match="selected open Salesforce"):
        crm.selected_guidance(_records(), "NOT-THERE")


def test_workflow_requires_override_before_approval(client, monkeypatch):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *args, **kwargs: _guidance())
    body = {
        "records": [{}],
        "deal_id": "SF-OPEN-001",
        "event": "approved",
        "actor": "Deal Desk",
    }

    response = client.post("/crm/workflow", json=body)

    assert response.status_code == 409
    assert "override request" in response.json()["detail"].lower()


def test_approval_inherits_override_terms(client, monkeypatch):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *args, **kwargs: _guidance())
    common = {
        "records": [{}],
        "deal_id": "SF-OPEN-001",
        "actor": "Account Executive",
    }
    requested = client.post("/crm/workflow", json={
        **common,
        "event": "override_requested",
        "justification": "Multi-year strategic logo",
        "requested_discount_pct": 22.0,
    })
    assert requested.status_code == 200

    approved = client.post("/crm/workflow", json={
        **common,
        "event": "approved",
        "actor": "Deal Desk",
    })

    assert approved.status_code == 200
    assert approved.json()["verdict"]["requested_pct"] == pytest.approx(22.0)
    log = client.get("/crm/workflow").json()["items"]
    assert log[0]["justification"] == "Multi-year strategic logo"


def _guidance_then_unavailable(monkeypatch) -> dict:
    """Live guidance for the first call only, unavailable after that.

    Mirrors the real sequence: the rep requests an override while the deal is
    open, the opportunity then closes in Salesforce (or the org drops below the
    evidence floor), and the approver acts once it has left the open-deal set.
    """
    calls = {"n": 0}

    def _stub(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _guidance()
        raise crm.CRMDataError(
            "The selected open Salesforce opportunity is not usable."
        )

    monkeypatch.setattr(main.crm_mod, "selected_guidance", _stub)
    return calls


def _request_override(client, actor: str = "Account Executive") -> None:
    response = client.post("/crm/workflow", json={
        "records": [{}],
        "deal_id": "SF-OPEN-001",
        "actor": actor,
        "event": "override_requested",
        "justification": "Multi-year strategic logo",
        "requested_discount_pct": 22.0,
    })
    assert response.status_code == 200


def test_decision_uses_recorded_terms_after_the_deal_leaves_the_open_set(
    client, monkeypatch,
):
    calls = _guidance_then_unavailable(monkeypatch)
    _request_override(client)

    approved = client.post("/crm/workflow", json={
        "records": [],
        "deal_id": "SF-OPEN-001",
        "actor": "Deal Desk",
        "event": "approved",
    })

    assert approved.status_code == 200
    assert approved.json()["verdict"]["requested_pct"] == pytest.approx(22.0)
    assert calls["n"] == 1, "a decision must not re-derive live guidance"
    log = client.get("/crm/workflow").json()["items"]
    assert log[0]["event"] == "approved"
    assert log[0]["verdict"]["requested_pct"] == pytest.approx(22.0)


def test_rejection_preserves_the_requested_terms(client, monkeypatch):
    _guidance_then_unavailable(monkeypatch)
    _request_override(client)

    rejected = client.post("/crm/workflow", json={
        "records": [],
        "deal_id": "SF-OPEN-001",
        "actor": "VP Pricing",
        "event": "rejected",
    })

    assert rejected.status_code == 200
    assert rejected.json()["verdict"]["requested_pct"] == pytest.approx(22.0)


def test_approval_cannot_restate_the_requested_discount(client, monkeypatch):
    _guidance_then_unavailable(monkeypatch)
    _request_override(client)

    approved = client.post("/crm/workflow", json={
        "records": [{}],
        "deal_id": "SF-OPEN-001",
        "actor": "Deal Desk",
        "event": "approved",
        "requested_discount_pct": 8.0,
    })

    assert approved.status_code == 422
    assert "cannot be restated" in approved.json()["detail"]
    log = client.get("/crm/workflow").json()["items"]
    assert log[0]["event"] == "override_requested"


def test_actor_cannot_approve_their_own_override(client, monkeypatch):
    _guidance_then_unavailable(monkeypatch)
    _request_override(client, actor="J. Rivera")

    approved = client.post("/crm/workflow", json={
        "records": [{}],
        "deal_id": "SF-OPEN-001",
        "actor": "  j.   rivera  ",
        "event": "approved",
    })

    assert approved.status_code == 409
    assert "different person" in approved.json()["detail"]
    log = client.get("/crm/workflow").json()["items"]
    assert log[0]["event"] == "override_requested"


def test_salesforce_sync_reconciles_outcome_once(client, monkeypatch):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *args, **kwargs: _guidance())
    accepted = client.post("/crm/workflow", json={
        "records": [{}],
        "deal_id": "SF-OPEN-001",
        "event": "accepted",
        "actor": "Account Executive",
    })
    assert accepted.status_code == 200
    outcome = {
        "outcomes": [{
            "deal_id": "SF-OPEN-001",
            "account": "Northstar Labs",
            "outcome": "closed_won",
        }],
    }

    first = client.post("/crm/reconcile", json=outcome)
    second = client.post("/crm/reconcile", json=outcome)

    assert first.json()["count"] == 1
    assert second.json()["count"] == 0
    log = client.get("/crm/workflow").json()["items"]
    assert log[0]["event"] == "outcome_recorded"
    assert log[0]["outcome"] == "closed_won"


def test_pending_override_is_not_dropped_when_salesforce_closes_the_deal(
    client, monkeypatch,
):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *args, **kwargs: _guidance())
    _request_override(client)

    reconciled = client.post("/crm/reconcile", json={
        "outcomes": [{
            "deal_id": "SF-OPEN-001",
            "account": "Northstar Labs",
            "outcome": "closed_lost",
        }],
    })

    assert reconciled.status_code == 200
    assert reconciled.json()["count"] == 1
    log = client.get("/crm/workflow").json()["items"]
    assert log[0]["event"] == "outcome_recorded"
    assert log[0]["outcome"] == "closed_lost"


def test_reconcile_batches_latest_history_lookup(client, monkeypatch):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *args, **kwargs: _guidance())
    for deal_id in ("SF-OPEN-001", "SF-OPEN-002"):
        response = client.post("/crm/workflow", json={
            "records": [{}],
            "deal_id": deal_id,
            "event": "accepted",
            "actor": "Account Executive",
        })
        assert response.status_code == 200
    original = governance.STORE.latest_by_deal
    calls = {"n": 0}

    def _counted(**kwargs):
        calls["n"] += 1
        return original(**kwargs)

    monkeypatch.setattr(governance.STORE, "latest_by_deal", _counted)
    reconciled = client.post("/crm/reconcile", json={
        "outcomes": [
            {"deal_id": "SF-OPEN-001", "outcome": "closed_won"},
            {"deal_id": "SF-OPEN-002", "outcome": "closed_lost"},
        ],
    })

    assert reconciled.status_code == 200
    assert reconciled.json()["count"] == 2
    assert calls["n"] == 1


def test_salesforce_writeback_result_is_append_only_and_visible(client, monkeypatch):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *args, **kwargs: _guidance())
    accepted = client.post("/crm/workflow", json={
        "records": [{}],
        "deal_id": "SF-OPEN-001",
        "event": "accepted",
        "actor": "Account Executive",
    })
    assert accepted.status_code == 200

    audited = client.post("/crm/writeback", json={
        "deal_id": "SF-OPEN-001",
        "actor": "Account Executive",
        "action_event": "accepted",
        "success": False,
        "error": "INSUFFICIENT_ACCESS: Task create denied",
    })

    assert audited.status_code == 200
    assert audited.json()["event"] == "salesforce_writeback_failed"
    log = client.get("/crm/workflow").json()["items"]
    assert log[0]["event"] == "salesforce_writeback_failed"
    assert log[0]["writeback"]["success"] is False
    assert "INSUFFICIENT_ACCESS" in log[0]["writeback"]["error"]


def test_deal_history_is_scoped_before_the_limit(client, monkeypatch):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *args, **kwargs: _guidance())
    _request_override(client)
    for index in range(550):
        governance.STORE.insert(
            kind="exception",
            deal_id=f"NOISE-{index}",
            payload={"source": "salesforce_crm", "event": "accepted"},
            decision="accepted",
            customer_ref="default",
        )

    approved = client.post("/crm/workflow", json={
        "records": [],
        "deal_id": "SF-OPEN-001",
        "actor": "Deal Desk",
        "event": "approved",
    })

    assert approved.status_code == 200
    assert approved.json()["verdict"]["requested_pct"] == pytest.approx(22.0)
