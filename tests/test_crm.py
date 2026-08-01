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
