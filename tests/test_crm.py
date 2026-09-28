"""CRM-native analysis tests: live-record boundary and open-deal guardrails."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main
from api.routers import crm as crm_router
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


def test_degenerate_list_guard_skipped_when_field_explicitly_mapped():
    # Same degenerate (list == booked) book as above, but the customer has
    # told us they mapped a real pre-discount list field: an honest
    # near-zero-discount book is not a mapping error, so the guard must be a
    # no-op (CONTRACT A). No open deal here on purpose: a book where every
    # closed deal discounts 0% has exactly one populated band, so it can
    # never clear the 3-band reference-sufficiency bar either -- a separate,
    # correct refusal (see test_guidance_raises_instead_of_a_zero_percent_
    # guardrail_on_thin_book) this test is not about.
    records = [r for r in _records() if r.get("outcome") != "open"]
    for row in records:
        row["list_acv"] = row["booked_acv"]
    with pytest.raises(crm.CRMDataError, match="near-identical"):
        crm.analyze_records(records, list_field_mapped=False)

    result = crm.analyze_records(records, list_field_mapped=True)
    assert result["analysis"]["overview"]["opportunities"] == 240
    assert result["guidance"] == []


# --- insufficient-reference blocker (2026-09-26 fix) -------------------------
# A thin book (reference_discount sufficient=False) must never turn into a
# live 0% guardrail: guidance_for_open_deal must refuse rather than recommend
# clawing back the whole discount.

def _insufficient_records() -> list[dict]:
    """42 closed deals across 5 real discount bands, none clearing the
    15-deal floor: reference_discount() returns sufficient=False. One open
    deal in the same (only) segment, so nothing can fall back to a segment
    that earned its own reference either."""
    discounts = [0.02, 0.07, 0.12, 0.17, 0.22]
    win_rates = [0.40, 0.50, 0.60, 0.60, 0.60]
    counts = [8, 8, 8, 9, 9]
    records: list[dict] = []
    idx = 0
    for disc, wr, n in zip(discounts, win_rates, counts):
        n_won = round(n * wr)
        for i in range(n):
            list_acv = 100_000.0
            records.append({
                "opportunity_id": f"OPP-{idx}",
                "account_name": f"Acct {idx}",
                "outcome": "closed_won" if i < n_won else "closed_lost",
                "created_date": "2025-01-01",
                "close_date": "2025-02-15",
                "product_tier": "Pro",
                "value_metric": "hybrid",
                "list_acv": list_acv,
                "booked_acv": list_acv * (1 - disc),
                "segment": "SMB",
            })
            idx += 1
    assert len(records) == 42
    records.append({
        "opportunity_id": "SF-OPEN-THIN",
        "account_name": "Thin Book Co",
        "outcome": "open",
        "created_date": "2026-08-01",
        "close_date": "",
        "product_tier": "Pro",
        "value_metric": "hybrid",
        "list_acv": 100_000.0,
        "booked_acv": 85_000.0,
        "segment": "SMB",
    })
    return records


def test_analyze_records_readiness_blocker_instead_of_raising_on_thin_book():
    """2026-09-27 fix (silent-failure-hunter): readiness passes at 30 usable
    closed deals while the engine needs 3 real discount bands at 15 deals
    each. Before this fix, analyze_records raised CRMDataError on the FIRST
    open deal, discarding the whole analysis; a caller like /crm/analyze
    wants the book-level analysis and readiness counts even when open-deal
    guidance cannot be computed. Now it returns 200-shaped output: empty
    guidance, and readiness names the blocker."""
    records = _insufficient_records()
    result = crm.analyze_records(records, policy_threshold_pct=15.0)
    assert result["guidance"] == []
    assert "analysis" in result and result["analysis"]
    blocker = result["readiness"]["reference_blocker"]
    assert "Insufficient closed-deal data" in blocker
    assert result["readiness"]["closed_usable"] == 42


def test_crm_workflow_422_not_zero_guardrail_on_thin_book(client):
    """The live path: /crm/workflow (a single selected deal) must still
    return 422 with the insufficient-data reason, never a 200 with
    guardrail_pct 0 / recommended_discount 0.0 manufactured off the
    insufficient-data sentinel, and never the generic 'not usable' message
    that would otherwise mask the real reason (see selected_guidance)."""
    response = client.post("/crm/workflow", json={
        "records": _insufficient_records(),
        "deal_id": "SF-OPEN-THIN",
        "event": "accepted",
        "actor": "Account Executive",
    })
    assert response.status_code == 422
    assert "insufficient" in response.json()["detail"].lower()


def test_crm_analyze_200_with_readiness_blocker_on_thin_book(client):
    """The book-level /crm/analyze must degrade to a 200 with the analysis
    and readiness counts intact, disclosing the blocker instead of losing the
    whole response to a raised exception (2026-09-27 fix)."""
    response = client.post("/crm/analyze", json={"records": _insufficient_records()})
    assert response.status_code == 200
    body = response.json()
    assert body["guidance"] == []
    assert "insufficient" in body["readiness"]["reference_blocker"].lower()


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


# --- fail-closed audit writes for CRM workflow events (CTO finding 3) --------

def test_crm_workflow_degrades_to_memory_with_200_in_dev(client, monkeypatch):
    # Dev (no DATABASE_URL, PRICEKEEL_ENV=dev from the fixture): the memory
    # fallback still returns 200 with persisted: False, same as before.
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *a, **k: _guidance())
    r = client.post("/crm/workflow", json={
        "records": [{}], "deal_id": "SF-OPEN-001", "event": "accepted",
        "actor": "Account Executive",
    })
    assert r.status_code == 200
    assert r.json()["persisted"] is False


_PROD_KEY = "prod-secret-key"
_PROD_AUTH = {"X-Pricekeel-Key": _PROD_KEY}


def test_crm_workflow_fails_closed_in_production_when_not_persisted(
    client, monkeypatch,
):
    # In production, a workflow write that only reached the memory fallback
    # must not be reported as a success: 503, not 200.
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *a, **k: _guidance())
    monkeypatch.setenv("PRICEKEEL_ENV", "production")
    monkeypatch.setenv("PRICEKEEL_API_KEY", _PROD_KEY)
    r = client.post("/crm/workflow", json={
        "records": [{}], "deal_id": "SF-OPEN-001", "event": "accepted",
        "actor": "Account Executive",
    }, headers=_PROD_AUTH)
    assert r.status_code == 503
    assert "not recorded" in r.json()["detail"].lower()


def test_crm_reconcile_fails_closed_in_production_when_not_persisted(
    client, monkeypatch,
):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *a, **k: _guidance())
    accepted = client.post("/crm/workflow", json={
        "records": [{}], "deal_id": "SF-OPEN-001", "event": "accepted",
        "actor": "Account Executive",
    })
    assert accepted.status_code == 200
    monkeypatch.setenv("PRICEKEEL_ENV", "production")
    monkeypatch.setenv("PRICEKEEL_API_KEY", _PROD_KEY)
    r = client.post("/crm/reconcile", json={
        "outcomes": [{"deal_id": "SF-OPEN-001", "outcome": "closed_won"}],
    }, headers=_PROD_AUTH)
    assert r.status_code == 503


def test_crm_writeback_fails_closed_in_production_when_not_persisted(
    client, monkeypatch,
):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *a, **k: _guidance())
    accepted = client.post("/crm/workflow", json={
        "records": [{}], "deal_id": "SF-OPEN-001", "event": "accepted",
        "actor": "Account Executive",
    })
    assert accepted.status_code == 200
    monkeypatch.setenv("PRICEKEEL_ENV", "production")
    monkeypatch.setenv("PRICEKEEL_API_KEY", _PROD_KEY)
    r = client.post("/crm/writeback", json={
        "deal_id": "SF-OPEN-001", "actor": "Account Executive",
        "action_event": "accepted", "success": True, "task_id": "T-1",
    }, headers=_PROD_AUTH)
    assert r.status_code == 503


def test_crm_workflow_logs_a_warning_naming_the_event_on_fallback(
    client, monkeypatch, caplog,
):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *a, **k: _guidance())
    with caplog.at_level(logging.WARNING, logger="pricekeel.api.crm"):
        client.post("/crm/workflow", json={
            "records": [{}], "deal_id": "SF-OPEN-001", "event": "accepted",
            "actor": "Account Executive",
        })
    assert "accepted" in caplog.text
    assert "fell back to the in-memory decision log" in caplog.text


# --- reference_discount memoized across one analyze_records call -----------
# (backend-engineer perf finding, scoped to the open-deal guidance loop:
# metrics.py's own internal repeats inside a single diagnostic run are a
# separate, larger fix that needs pricing/metrics.py, out of scope here.)

def test_reference_for_segment_uses_supplied_values_without_recomputing():
    def _boom(*_a, **_k):
        raise AssertionError("must not recompute when values are supplied")

    fake_global = {"reference_threshold": 0.11, "reference_band": "5-10%"}
    fake_table = [{"segment": "Enterprise", "reference_threshold": 0.20,
                   "reference_band": "15-25%", "basis": "segment"}]

    hit = crm._reference_for_segment(
        pd.DataFrame(), "Enterprise", global_ref=fake_global,
        segment_table=fake_table,
    )
    assert hit == (0.20, "15-25%", "segment")

    miss = crm._reference_for_segment(
        pd.DataFrame(), "Unknown", global_ref=fake_global,
        segment_table=fake_table,
    )
    assert miss == (0.11, "5-10%", "global fallback (segment not found)")


def test_analyze_records_reference_calls_do_not_scale_with_open_deal_count(
    monkeypatch,
):
    calls = {"ref": 0, "table": 0}
    original_ref = crm.metrics.reference_discount
    original_table = crm.metrics.segment_reference_table

    def counted_ref(df, *a, **kw):
        calls["ref"] += 1
        return original_ref(df, *a, **kw)

    def counted_table(df, *a, **kw):
        calls["table"] += 1
        return original_table(df, *a, **kw)

    monkeypatch.setattr(crm.metrics, "reference_discount", counted_ref)
    monkeypatch.setattr(crm.metrics, "segment_reference_table", counted_table)

    crm.analyze_records(_records(), policy_threshold_pct=15.0)
    calls_with_one_open_deal = dict(calls)
    assert calls_with_one_open_deal["ref"] >= 1

    calls["ref"] = calls["table"] = 0
    records = _records()
    for i in range(4):
        extra = dict(records[-1])
        extra["opportunity_id"] = f"SF-OPEN-EXTRA-{i}"
        records.append(extra)
    crm.analyze_records(records, policy_threshold_pct=15.0)

    # Five open deals instead of one: reference_discount and
    # segment_reference_table must still run the same fixed number of times,
    # not once more per extra open deal.
    assert calls == calls_with_one_open_deal


# --- evidence_version on every CRM verdict (CTO finding 4) ------------------

def test_evidence_version_is_stable_for_identical_books():
    records = _records()
    a = crm_router.evidence_version(records, 15.0, "band_guardrail")
    b = crm_router.evidence_version(list(records), 15.0, "band_guardrail")
    assert a == b


def test_evidence_version_changes_with_the_policy_threshold():
    records = _records()
    a = crm_router.evidence_version(records, 15.0, "band_guardrail")
    b = crm_router.evidence_version(records, 20.0, "band_guardrail")
    assert a != b


def test_evidence_version_changes_with_record_count_and_method():
    records = _records()
    baseline = crm_router.evidence_version(records, 15.0, "band_guardrail")
    assert crm_router.evidence_version(records[:-1], 15.0, "band_guardrail") != baseline
    assert crm_router.evidence_version(records, 15.0, "modeled_ev_curve") != baseline


def test_evidence_version_fingerprints_the_book_content():
    """2026-09-26 fix: the old fingerprint hashed len(records) and a sync
    timestamp that reads 'none' on every real adapter, so two DIFFERENT
    books of the SAME size hashed identically. Two two-deal books that differ
    only in booked_acv must now hash differently."""
    book_a = [
        {"opportunity_id": "OPP-1", "booked_acv": 90_000.0, "outcome": "closed_won"},
        {"opportunity_id": "OPP-2", "booked_acv": 80_000.0, "outcome": "closed_won"},
    ]
    book_b = [
        {"opportunity_id": "OPP-1", "booked_acv": 90_000.0, "outcome": "closed_won"},
        {"opportunity_id": "OPP-2", "booked_acv": 70_000.0, "outcome": "closed_won"},
    ]
    a_digest, a_inputs = crm_router.evidence_version(book_a, 15.0, "band_guardrail")
    b_digest, b_inputs = crm_router.evidence_version(book_b, 15.0, "band_guardrail")
    assert a_digest != b_digest
    assert a_inputs["records_hash"] != b_inputs["records_hash"]
    assert a_inputs["records"] == b_inputs["records"] == 2

    # Row order must not matter: the hash is stable under reordering.
    reordered_digest, reordered_inputs = crm_router.evidence_version(
        list(reversed(book_a)), 15.0, "band_guardrail",
    )
    assert reordered_digest == a_digest
    assert reordered_inputs["records_hash"] == a_inputs["records_hash"]


def test_evidence_version_returns_fingerprint_inputs_alongside_the_hash():
    digest, inputs = crm_router.evidence_version(_records(), 15.0, "band_guardrail")
    assert isinstance(digest, str) and digest
    for key in ("records", "records_hash", "max_sync", "policy_threshold_pct",
               "method", "git_sha"):
        assert key in inputs


def test_evidence_version_warns_when_git_sha_is_unknown(monkeypatch, caplog):
    monkeypatch.delenv("PRICEKEEL_GIT_SHA", raising=False)
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.setattr(crm_router.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    with caplog.at_level(logging.WARNING, logger="pricekeel.api.crm"):
        _digest, inputs = crm_router.evidence_version(
            [{"opportunity_id": "OPP-1"}], 15.0, "band_guardrail",
        )
    assert inputs["git_sha"] == "unknown"
    assert "git sha could not be resolved" in caplog.text.lower()


def test_crm_workflow_verdict_carries_evidence_version(client, monkeypatch):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *a, **k: _guidance())
    r = client.post("/crm/workflow", json={
        "records": [{}], "deal_id": "SF-OPEN-001", "event": "accepted",
        "actor": "Account Executive",
    })
    assert r.status_code == 200
    version = r.json()["verdict"]["evidence_version"]
    assert isinstance(version, str) and version

    # An approval on the same override inherits the request's evidence
    # version rather than recomputing one against whatever it happens to
    # submit as `records` (it need not resubmit the book at all).
    override = client.post("/crm/workflow", json={
        "records": [{}], "deal_id": "SF-OPEN-002", "event": "override_requested",
        "actor": "Account Executive", "justification": "x",
        "requested_discount_pct": 22.0,
    })
    monkeypatch.setattr(main.crm_mod, "selected_guidance",
                        lambda *a, **k: {**_guidance(), "opportunity_id": "SF-OPEN-002"})
    assert override.status_code == 200
    requested_version = override.json()["verdict"]["evidence_version"]
    approved = client.post("/crm/workflow", json={
        "records": [], "deal_id": "SF-OPEN-002", "event": "approved",
        "actor": "Deal Desk",
    })
    assert approved.status_code == 200
    assert approved.json()["verdict"]["evidence_version"] == requested_version


# --- length caps on justification / actor (code-reviewer finding 2) --------

def test_crm_workflow_actor_and_justification_length_caps_422(client, monkeypatch):
    monkeypatch.setattr(main.crm_mod, "selected_guidance", lambda *a, **k: _guidance())
    over_actor = client.post("/crm/workflow", json={
        "records": [{}], "deal_id": "SF-OPEN-001", "event": "accepted",
        "actor": "a" * 121,
    })
    assert over_actor.status_code == 422

    over_justification = client.post("/crm/workflow", json={
        "records": [{}], "deal_id": "SF-OPEN-001", "event": "override_requested",
        "actor": "Account Executive", "justification": "x" * 2001,
        "requested_discount_pct": 22.0,
    })
    assert over_justification.status_code == 422


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
