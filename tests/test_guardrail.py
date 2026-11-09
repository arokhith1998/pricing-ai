"""Source-neutral guardrail, adapters, and source-string aliases (PK-25)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main
from pricing import crm, csv_adapter, governance, guardrail
from pricing.ingest import ingest_frame_verbose

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
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


# --- the engine carries no source vocabulary ---------------------------------

_FORBIDDEN = ("salesforce", "sfdc", "opportunity", "opportunities", "sobject")


def test_guardrail_module_source_has_no_salesforce_vocabulary():
    text = Path(guardrail.__file__).read_text(encoding="utf-8").lower()
    for word in _FORBIDDEN:
        assert word not in text, f"{word!r} found in guardrail.py"


def test_deal_id_field_is_the_required_identifier():
    assert guardrail.DEAL_ID_FIELD == "opportunity_id"


# --- adapters ------------------------------------------------------------------

def test_both_adapters_satisfy_the_protocol():
    assert isinstance(crm.SalesforceAdapter(), guardrail.DealSourceAdapter)
    assert isinstance(csv_adapter.CsvAdapter(), guardrail.DealSourceAdapter)


def test_salesforce_adapter_stamps_provenance_and_does_not_mutate():
    raw = {"opportunity_id": "006X1", "account_id": "001A9",
           "salesforce_url": "/lightning/r/Opportunity/006X1/view",
           "list_acv": 10.0, "booked_acv": 9.0}
    before = dict(raw)
    out = crm.SalesforceAdapter().to_canonical(raw)
    assert raw == before
    assert out["source_system"] == "salesforce"
    assert out["source_record_id"] == "006X1"
    assert out["source_account_id"] == "001A9"
    assert out["source_url"] == "/lightning/r/Opportunity/006X1/view"
    assert out["list_acv"] == 10.0


def test_csv_adapter_stamps_only_when_absent():
    adapter = csv_adapter.CsvAdapter()
    assert adapter.to_canonical({"opportunity_id": "A"})["source_system"] == "csv"
    assert adapter.to_canonical(
        {"opportunity_id": "A", "source_system": " "})["source_system"] == "csv"
    assert adapter.to_canonical(
        {"opportunity_id": "A", "source_system": "hubspot"})["source_system"] == "hubspot"


@pytest.mark.parametrize("adapter,expected", [
    (crm.SalesforceAdapter(), "salesforce"),
    (csv_adapter.CsvAdapter(), "csv"),
])
def test_adapter_output_loads_through_ingest_with_the_right_source_system(
        adapter, expected):
    closed = [r for r in _records() if r["outcome"] != "open"]
    canonical = guardrail.canonical_records(adapter, closed)
    df, report = ingest_frame_verbose(pd.DataFrame(canonical), source="test")
    assert len(df) == len(closed)
    assert set(df["source_system"]) == {expected}


# --- behavior preserved across the split ---------------------------------------
# Expected values captured from pricing.crm on main at 0976558, before the split.

_BASELINE_COMPARABLES = [
    {'booked_acv': 76740.33, 'discount_pct': 0.124145, 'industry': 'MarTech', 'is_won': False, 'list_acv': 87617.61, 'deal_id': 'OPP-00058', 'resolved_account_name': 'Monarch Digital, Inc.', 'segment': 'MidMarket'},
    {'booked_acv': 100312.72, 'discount_pct': 0.125787, 'industry': 'MarTech', 'is_won': True, 'list_acv': 114746.27, 'deal_id': 'OPP-00222', 'resolved_account_name': 'Monarch Software', 'segment': 'MidMarket'},
    {'booked_acv': 67960.06, 'discount_pct': 0.216356, 'industry': 'MarTech', 'is_won': True, 'list_acv': 86723.09, 'deal_id': 'OPP-00103', 'resolved_account_name': 'Tessera Systems Corp.', 'segment': 'MidMarket'},
    {'booked_acv': 56403.44, 'discount_pct': 0.184781, 'industry': 'MarTech', 'is_won': False, 'list_acv': 69188.05, 'deal_id': 'OPP-00104', 'resolved_account_name': 'Juniper Systems, Inc.', 'segment': 'MidMarket'},
    {'booked_acv': 52007.09, 'discount_pct': 0.202431, 'industry': 'MarTech', 'is_won': True, 'list_acv': 65206.97, 'deal_id': 'OPP-00236', 'resolved_account_name': 'Aurora Cloud, Inc.', 'segment': 'MidMarket'},
]
_BASELINE = {
    "opportunity_id": "SF-OPEN-001",
    "account": "Northstar Labs",
    "evidence_source": "band_guardrail",
    "segment": "MidMarket",
    "product_tier": "Scale",
    "rep_id": "REP-09",
    "close_date": "2026-09-30",
    "currency_iso": "USD",
    "salesforce_url": "/lightning/r/Opportunity/SF-OPEN-001/view",
    "list_acv": 100000.0,
    "quoted_acv": 70000.0,
    "current_discount": 0.30000000000000004,
    "recommended_discount": 0.05,
    "policy_threshold": 0.15,
    "reference_discount": 0.05,
    "reference_band": "5-10%",
    "reference_basis": "global fallback (insufficient data)",
    "below_guardrail": False,
    "price_to_retain": 25000.000000000007,
    "win_rate_at_current_band": 0.375,
    "win_rate_at_recommended_band": 0.6304347826086957,
    "expected_acv_at_current": 26250.0,
    "expected_acv_at_recommended": 59891.30434782609,
    "expected_acv_delta": 33641.30434782609,
    "current_band": "25%+",
    "recommended_band": "5-10%",
    "current_band_deals": 16,
    "recommended_band_deals": 46,
    "competitor_present": True,
}
_BASELINE_READINESS = {
    "records_received": 241, "closed_received": 240, "closed_usable": 240,
    "closed_excluded_missing_value": 0, "open_received": 1, "open_usable": 1,
    "open_excluded_missing_value": 0, "currencies": ["USD"],
}


def _assert_matches_baseline(row: dict, *, id_key: str, url_key: str):
    renamed = {"opportunity_id": id_key, "salesforce_url": url_key}
    for key, expected in _BASELINE.items():
        mapped = renamed.get(key, key)
        if isinstance(expected, float):
            assert row[mapped] == pytest.approx(expected), key
        else:
            assert row[mapped] == expected, key
    assert row["caveat"].startswith("Historical discount-band outcomes are correlational")
    expected = [{(id_key if k == "deal_id" else k): v for k, v in c.items()}
                for c in _BASELINE_COMPARABLES]
    assert len(row["comparables"]) == len(expected)
    for got, want in zip(row["comparables"], expected):
        assert set(got) == set(want)
        for key, value in want.items():
            if isinstance(value, float):
                assert got[key] == pytest.approx(value), key
            else:
                assert got[key] == value, key


def test_crm_wrapper_output_equals_the_pre_split_output():
    result = crm.analyze_records(_records(), policy_threshold_pct=15.0)
    assert result["readiness"] == _BASELINE_READINESS
    assert len(result["guidance"]) == 1
    row = result["guidance"][0]
    _assert_matches_baseline(row, id_key="opportunity_id", url_key="salesforce_url")
    assert set(row) == set(_BASELINE) | {"caveat", "comparables"}
    picked = crm.selected_guidance(_records(), "SF-OPEN-001")
    _assert_matches_baseline(picked, id_key="opportunity_id", url_key="salesforce_url")


def test_guardrail_output_equals_the_pre_split_output_under_neutral_keys():
    canonical = guardrail.canonical_records(crm.SalesforceAdapter(), _records())
    result = guardrail.analyze_deals(canonical, 15.0, labels=crm.SalesforceAdapter.labels)
    assert result["readiness"] == _BASELINE_READINESS
    row = result["guidance"][0]
    _assert_matches_baseline(row, id_key="deal_id", url_key="source_url")
    assert "opportunity_id" not in row and "salesforce_url" not in row


def test_guardrail_runs_on_csv_adapter_rows_and_names_its_method():
    rows = [dict(r) for r in _records()]
    for row in rows:
        row["source_url"] = row.pop("salesforce_url")
    canonical = guardrail.canonical_records(csv_adapter.CsvAdapter(), rows)
    result = guardrail.analyze_deals(canonical, 15.0)
    row = result["guidance"][0]
    assert row["evidence_source"] == "band_guardrail"
    assert row["recommended_discount"] == pytest.approx(_BASELINE["recommended_discount"])
    assert row["deal_id"] == "SF-OPEN-001"


def test_thin_data_is_insufficient_not_a_number():
    canonical = guardrail.canonical_records(csv_adapter.CsvAdapter(), _records()[:20])
    with pytest.raises(guardrail.DealDataError, match="at least 30"):
        guardrail.analyze_deals(canonical, 15.0)
    # Same class the CRM wrapper raises, so API handlers keep catching it.
    assert crm.CRMDataError is guardrail.DealDataError
    with pytest.raises(crm.CRMDataError, match="at least 30"):
        crm.analyze_records(_records()[:20])


def test_error_wording_follows_the_adapter_labels():
    with pytest.raises(guardrail.DealDataError, match="No CSV deals were supplied"):
        guardrail.analyze_deals([], 15.0, labels=csv_adapter.CsvAdapter.labels)
    with pytest.raises(crm.CRMDataError, match="No Salesforce opportunities were supplied"):
        crm.analyze_records([])


def test_engine_imports_no_adapter():
    text = Path(guardrail.__file__).read_text(encoding="utf-8")
    assert "csv_adapter" not in text
    assert "from pricing import crm" not in text


def test_oversized_payload_message_uses_the_adapter_label():
    canonical = guardrail.canonical_records(csv_adapter.CsvAdapter(), _records()[:5])
    with pytest.raises(guardrail.DealDataError, match="Payload exceeds the 3 CSV record limit"):
        guardrail.analyze_deals(canonical, 15.0, labels=csv_adapter.CsvAdapter.labels,
                                max_records=3)


def test_no_guidance_output_calls_a_proxy_a_margin():
    result = crm.analyze_records(_records(), policy_threshold_pct=15.0)
    text = json.dumps(result["guidance"], default=str).lower()
    assert "margin" not in text


# --- source strings and aliases in the decision log -----------------------------

@pytest.mark.parametrize("legacy,system", [
    ("salesforce_crm", "salesforce"),
    ("salesforce_crm_writeback", "salesforce"),
    ("sfdc", "salesforce"),
    ("salesforce", "salesforce"),
    ("csv", "csv"),
    ("manual", "manual"),
])
def test_legacy_source_strings_resolve_to_the_source_system(legacy, system):
    assert governance.resolve_source(legacy) == system
    assert governance.resolve_source(legacy.upper()) == system


def test_salesforce_filter_finds_legacy_and_new_rows_and_hides_other_sources():
    store = governance.STORE
    for source, event in [
        ("salesforce_crm", "override_requested"),
        ("salesforce", "override_requested"),
        ("salesforce_crm_writeback", "salesforce_writeback_succeeded"),
        ("csv", "override_requested"),
    ]:
        store.insert(kind="exception", deal_id=f"D-{source}",
                     payload={"source": source, "event": event},
                     decision=event)
    by_system = {r["deal_id"] for r in store.list(kind="exception", source="salesforce")}
    assert by_system == {"D-salesforce_crm", "D-salesforce",
                         "D-salesforce_crm_writeback"}
    # Asking by a legacy spelling resolves to the same system.
    legacy_ask = {r["deal_id"] for r in store.list(kind="exception",
                                                   source="salesforce_crm")}
    assert legacy_ask == by_system
    no_receipts = {r["deal_id"] for r in store.list(
        kind="exception", source="salesforce", exclude_receipts=True)}
    assert no_receipts == {"D-salesforce_crm", "D-salesforce"}
    latest = store.latest_by_deal(
        kind="exception", deal_ids=["D-salesforce_crm_writeback", "D-salesforce"],
        source="salesforce_crm", exclude_receipts=True)
    assert set(latest) == {"D-salesforce"}


def test_csv_sourced_exception_shows_in_the_source_filter_next_to_salesforce():
    store = governance.STORE
    store.insert(kind="exception", deal_id="SF-1",
                 payload={"source": "salesforce", "event": "override_requested",
                          "verdict": {"requested_pct": 30.0, "outside_guardrail": True}},
                 decision="override_requested")
    store.insert(kind="exception", deal_id="CSV-1",
                 payload={"source": "csv", "source_system": "csv",
                          "event": "override_requested",
                          "verdict": {"requested_pct": 25.0, "outside_guardrail": True}},
                 decision="override_requested")
    both = {r["deal_id"] for r in store.list(kind="exception",
                                             source=["salesforce", "csv"])}
    assert both == {"SF-1", "CSV-1"}
    csv_rows = store.list(kind="exception", source="csv")
    assert {r["deal_id"] for r in csv_rows} == {"CSV-1"}
    assert governance.exception_source(csv_rows[0]["payload"]) == "csv"
    digest = governance.build_digest(analysis=None)
    assert digest["stats"]["exceptions_total"] == 2
    assert digest["stats"]["exceptions_below_floor"] == 2


def test_csv_row_that_is_not_a_request_stays_out_of_the_digest_headline():
    governance.STORE.insert(
        kind="exception", deal_id="CSV-2",
        payload={"source": "csv", "event": "approved", "verdict": {}},
        decision="approved")
    assert governance.build_digest(analysis=None)["stats"]["exceptions_total"] == 0


# --- the router keeps working over legacy rows and writes the new source --------

def _verdict() -> dict:
    return {"requested_pct": 22.0, "recommended_pct": 15.0, "guardrail_pct": 15.0,
            "outside_guardrail": True, "price_to_retain": 7000.0,
            "method": "band_guardrail"}


def test_approval_resolves_a_legacy_override_row_and_ignores_a_legacy_receipt(client):
    store = governance.STORE
    store.insert(kind="exception", deal_id="SF-OPEN-001",
                 payload={"source": "salesforce_crm", "event": "override_requested",
                          "actor": "rep", "account": "Northstar Labs",
                          "verdict": _verdict()},
                 decision="override_requested", requested_by="rep")
    store.insert(kind="exception", deal_id="SF-OPEN-001",
                 payload={"source": "salesforce_crm_writeback",
                          "event": "salesforce_writeback_succeeded",
                          "actor": "rep", "verdict": _verdict()},
                 decision="salesforce_writeback_succeeded", requested_by="rep")
    # The self-approval block holds on a legacy-sourced request.
    blocked = client.post("/crm/workflow", json={
        "records": [], "deal_id": "SF-OPEN-001", "actor": "Rep",
        "event": "approved"})
    assert blocked.status_code == 409, blocked.text
    resp = client.post("/crm/workflow", json={
        "records": [], "deal_id": "SF-OPEN-001", "actor": "Deal Desk",
        "event": "approved"})
    assert resp.status_code == 200, resp.text
    approved = [r for r in store.list(kind="exception", deal_id="SF-OPEN-001")
                if r["payload"].get("event") == "approved"]
    assert approved[0]["payload"]["source"] == "salesforce"


def test_writeback_receipt_is_logged_as_salesforce_and_listed(client):
    governance.STORE.insert(
        kind="exception", deal_id="SF-9",
        payload={"source": "salesforce", "event": "accepted", "verdict": _verdict()},
        decision="accepted")
    resp = client.post("/crm/writeback", json={
        "deal_id": "SF-9", "actor": "desk", "action_event": "accepted",
        "success": True, "task_id": "00T1"})
    assert resp.status_code == 200, resp.text
    receipts = [r for r in governance.STORE.list(kind="exception", deal_id="SF-9")
                if governance.is_writeback_receipt(r["payload"])]
    assert len(receipts) == 1
    assert receipts[0]["payload"]["source"] == "salesforce"
    log = client.get("/crm/workflow").json()["items"]
    assert {i["event"] for i in log} == {"accepted", "salesforce_writeback_succeeded"}


# --- receipts are detected structurally -----------------------------------------

def test_a_future_receipt_from_another_system_is_excluded_without_a_code_change():
    store = governance.STORE
    rows = {
        "H-DECISION": {"source": "hubspot", "event": "override_requested"},
        "H-RECEIPT-EVENT": {"source": "hubspot", "event": "hubspot_writeback_succeeded"},
        "H-RECEIPT-FAILED": {"source": "hubspot", "event": "hubspot_writeback_failed"},
        "H-RECEIPT-KEY": {"source": "hubspot", "event": "synced",
                          "writeback": {"success": True}},
    }
    for deal, payload in rows.items():
        store.insert(kind="exception", deal_id=deal, payload=payload,
                     decision=payload["event"])
    kept = {r["deal_id"] for r in store.list(kind="exception", source="hubspot",
                                             exclude_receipts=True)}
    assert kept == {"H-DECISION"}
    assert {r["deal_id"] for r in store.list(kind="exception", source="hubspot")} == set(rows)
    assert not governance._is_exception_request(rows["H-RECEIPT-EVENT"])
    assert not governance._is_exception_request(rows["H-RECEIPT-KEY"])


# --- source filter normalisation -------------------------------------------------

def _seed_two_sources():
    for deal, source in (("A", "salesforce_crm"), ("B", "csv")):
        governance.STORE.insert(kind="exception", deal_id=deal,
                                payload={"source": source, "event": "accepted"},
                                decision="accepted")


def test_generator_source_filter_is_read_once_not_per_row():
    _seed_two_sources()
    as_list = {r["deal_id"] for r in governance.STORE.list(
        kind="exception", source=["salesforce", "csv"])}
    as_gen = {r["deal_id"] for r in governance.STORE.list(
        kind="exception", source=(s for s in ["salesforce", "csv"]))}
    assert as_list == as_gen == {"A", "B"}
    latest = governance.STORE.latest_by_deal(
        kind="exception", deal_ids=["A", "B"],
        source=(s for s in ["salesforce", "csv"]))
    assert set(latest) == {"A", "B"}


def test_empty_source_sequence_matches_nothing_and_none_matches_everything():
    _seed_two_sources()
    assert governance.STORE.list(kind="exception", source=[]) == []
    assert governance.STORE.latest_by_deal(
        kind="exception", deal_ids=["A", "B"], source=[]) == {}
    assert len(governance.STORE.list(kind="exception", source=None)) == 2


def test_source_match_ignores_case_and_whitespace_like_the_sql_does():
    governance.STORE.insert(kind="exception", deal_id="C",
                            payload={"source": "  Salesforce_CRM ", "event": "accepted"},
                            decision="accepted")
    assert [r["deal_id"] for r in governance.STORE.list(
        kind="exception", source="salesforce")] == ["C"]


# --- the SQL the database path sends -----------------------------------------------

class _RecordingCursor:
    def __init__(self, log):
        self._log = log

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def execute(self, query, vals=None):
        self._log.append((query, list(vals or [])))

    def fetchall(self):
        return []


class _RecordingConn:
    def __init__(self, log):
        self._log = log

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def cursor(self, *_a, **_k):
        return _RecordingCursor(self._log)


def test_database_path_sends_the_alias_and_receipt_clauses(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    log: list = []
    monkeypatch.setattr(governance.psycopg, "connect",
                        lambda *_a, **_k: _RecordingConn(log))
    governance.STORE.list(kind="exception", source="salesforce_crm",
                          exclude_receipts=True)
    governance.STORE.latest_by_deal(kind="exception", deal_ids=["D1"],
                                    source=["salesforce", "csv"],
                                    exclude_receipts=True)
    assert len(log) == 2
    for query, vals in log:
        assert "lower(btrim(payload->>'source')) = any(%s)" in query
        assert "payload->'writeback' is null" in query
        assert query.count("not like %s") == 2
        assert "salesforce_crm_writeback" in vals
        assert any(isinstance(v, str) and v.startswith("%") and v.endswith("writeback\\_succeeded") for v in vals)
        assert any(isinstance(v, str) and v.startswith("%") and v.endswith("writeback\\_failed") for v in vals)
    list_vals = log[0][1]
    assert ["salesforce", "salesforce_crm", "salesforce_crm_writeback",
            "sfdc"] in list_vals
    assert ["csv", "salesforce", "salesforce_crm", "salesforce_crm_writeback",
            "sfdc"] in log[1][1]


def test_database_path_omits_the_clauses_when_not_asked(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    log: list = []
    monkeypatch.setattr(governance.psycopg, "connect",
                        lambda *_a, **_k: _RecordingConn(log))
    governance.STORE.list(kind="exception")
    query = log[0][0]
    assert "any(%s)" not in query and "writeback" not in query
