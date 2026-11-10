"""HubSpot adapter and source registry: known answers, outcome safety, purity,
and the per-request source resolution in /crm/*.

Every record here is synthetic (invented companies, invented ids). The vendor
object shapes are from general HubSpot knowledge and are confirmed against the
live API by PK-47; the mapping logic is what these tests pin.
"""
from __future__ import annotations

import copy
import itertools
import json
import socket
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main
from api.routers import crm as crm_router
from pricing import crm, governance, guardrail
from pricing.adapters import (
    REGISTRY, UnknownSourceSystemError, get_adapter,
)
from pricing.adapters.hubspot import ASK_USER, HubSpotAdapter, HubSpotConfigError
from pricing.csv_adapter import CsvAdapter

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "hubspot"


def _load(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


CONFIG = _load("config.json")
EXPECTED = _load("expected.json")
LINE_DEALS = _load("deals_line_items.json")
PLAIN_DEALS = _load("deals_no_line_items.json")
ALL_DEALS = LINE_DEALS + PLAIN_DEALS


@pytest.fixture()
def adapter() -> HubSpotAdapter:
    return get_adapter("hubspot").configured(CONFIG)


# --- known-answer recovery ---------------------------------------------------

@pytest.mark.parametrize("deal", ALL_DEALS, ids=[d["id"] for d in ALL_DEALS])
def test_known_answer_recovery(adapter, deal):
    row = adapter.to_canonical(deal)
    want = EXPECTED[deal["id"]]
    for key, value in want.items():
        got = row[key]
        if isinstance(value, float):
            assert got == pytest.approx(value, abs=1e-9), key
        else:
            assert got == value, key
    assert row["source_system"] == "hubspot"
    assert row["source_record_id"] == deal["id"]
    assert row["opportunity_id"] == deal["id"]
    assert row["source_url"] == f"https://app.hubspot.com/contacts/4412345/record/0-3/{deal['id']}"


def test_line_item_sums_are_exact_decimals(adapter):
    # 0.12 * 500000 + 33.33 * 3 would drift as binary floats; Decimal sums it.
    row = adapter.to_canonical(next(d for d in ALL_DEALS if d["id"] == "601"))
    assert row["list_acv"] == 60099.99
    assert row["booked_acv"] == 45099.99


def test_pipelines_resolve_separately_with_custom_labels(adapter):
    rows = {r["opportunity_id"]: r for r in map(adapter.to_canonical, ALL_DEALS)}
    assert rows["501"]["stage_label"] == "Signed, kickoff booked"
    assert rows["601"]["stage_label"] == "Live in production"
    # The same stage id string in another pipeline is a different stage.
    other = copy.deepcopy(next(d for d in ALL_DEALS if d["id"] == "501"))
    other["properties"]["pipeline"] = "p_plat"
    assert adapter.to_canonical(other)["outcome"] == ASK_USER


def test_no_line_item_pipeline_has_no_list_and_hits_the_blocker(adapter):
    rows = [adapter.to_canonical(d) for d in PLAIN_DEALS]
    assert {r["list_source"] for r in rows} == {"none"}
    assert all(r["list_acv"] is None for r in rows)
    # No declared-list fallback (F6): booked is carried, list is never invented.
    assert rows[0]["booked_acv"] == 12000.0

    # A whole book with no line items runs the engine's existing missing-list
    # refusal: no closed deal is usable, so it names the 30-deal floor.
    book = [adapter.to_canonical(_synthetic_record(i, won=i % 2 == 0, with_lines=False))
            for i in range(60)]
    with pytest.raises(guardrail.DealDataError, match="at least 30"):
        guardrail.analyze_deals(book, labels=adapter.labels)


def test_ask_user_deals_are_disclosed_by_stage_and_never_counted(adapter):
    rows = [adapter.to_canonical(d) for d in ALL_DEALS]
    extras = adapter.readiness_extras(rows)
    assert extras["ask_user"]["deals"] == 3
    reasons = {(s["stage_id"], s["reason"]) for s in extras["ask_user"]["by_stage"]}
    assert reasons == {("9100004", "stage_unconfirmed"), ("9100099", "stage_not_in_map"),
                       ("8000001", "stage_missing")}
    assert extras["list_source_counts"] == {"line_items": 7, "none": 4}


def test_open_stage_with_past_close_date_stays_open(adapter):
    row = adapter.to_canonical(next(d for d in ALL_DEALS if d["id"] == "503"))
    assert row["close_date"] == "2025-01-15"
    assert row["outcome"] == "open"


# --- outcome safety ----------------------------------------------------------

def _deal(stage: str, pipeline: str = "p") -> dict:
    return {"id": "1", "properties": {
        "pipeline": pipeline, "dealstage": stage, "amount": "100",
        "closedate": "2020-01-01T00:00:00Z", "hs_is_closed_lost": "true",
        "hs_is_closed_won": "false", "dealname": "Lostlike Co"}}


def test_closed_lost_only_from_a_confirmed_lost_stage():
    """Exhaustive over stage-map shapes: closed_lost appears exactly when the
    deal's stage is mapped once, confirmed with the literal True, and lost."""
    outcomes = ["won", "lost", "open", "LOST", "closed_lost", "", None, "unknown", 1]
    confirmations = [True, False, "true", "false", 1, 0, None, "yes"]
    stage_ids = ["s1", "s2", "absent", ""]
    checked = 0
    for outcome, confirmed, stage in itertools.product(outcomes, confirmations, stage_ids):
        entry = {"pipeline_id": "p", "stage_id": "s1", "label": "x",
                 "outcome": outcome, "confirmed": confirmed}
        decoy = {"pipeline_id": "p", "stage_id": "s2", "label": "y",
                 "outcome": "lost", "confirmed": False}
        row = HubSpotAdapter({"portal_id": "1", "stage_map": [entry, decoy]}).to_canonical(
            _deal(stage))
        lost_confirmed = (stage == "s1" and confirmed is True
                          and str(outcome).lower() == "lost")
        assert (row["outcome"] == "closed_lost") == lost_confirmed, (outcome, confirmed, stage)
        if stage in {"absent", ""} or confirmed is not True:
            assert row["outcome"] == ASK_USER
        checked += 1
    assert checked == len(outcomes) * len(confirmations) * len(stage_ids)


def test_unmapped_unconfirmed_and_ambiguous_stages_are_ask_user():
    base = {"pipeline_id": "p", "stage_id": "s1", "label": "x"}
    cases = {
        "no map": [],
        "unconfirmed": [{**base, "outcome": "lost", "confirmed": False}],
        "ambiguous": [{**base, "outcome": "lost", "confirmed": True},
                      {**base, "outcome": "won", "confirmed": True}],
    }
    for name, stage_map in cases.items():
        row = HubSpotAdapter({"portal_id": "1", "stage_map": stage_map}).to_canonical(_deal("s1"))
        assert row["outcome"] == ASK_USER, name
    # Missing pipeline or stage on the deal is ask_user, never open or lost.
    adapter = HubSpotAdapter({"portal_id": "1", "stage_map": [
        {**base, "outcome": "lost", "confirmed": True}]})
    assert adapter.to_canonical(_deal("s1", pipeline=""))["outcome"] == ASK_USER
    assert adapter.to_canonical(_deal("s1"))["outcome"] == "closed_lost"


def test_unconfigured_adapter_maps_everything_to_ask_user():
    assert HubSpotAdapter().to_canonical(_deal("s1"))["outcome"] == ASK_USER


def test_bad_config_is_a_named_error():
    for bad in ({}, {"portal_id": "abc"}, {"portal_id": "1", "stage_map": "x"},
                {"portal_id": "1", "stage_map": [{"stage_id": "s"}]},
                {"portal_id": "1", "app_host": "evil.example.com"},
                {"portal_id": "1", "default_value_metric": "tokens"}):
        with pytest.raises(HubSpotConfigError):
            HubSpotAdapter().configured(bad)


def test_home_currency_mode_states_the_currency_and_scales_by_hubspot_rate():
    cfg = {**CONFIG, "use_home_currency": True, "home_currency": "usd"}
    deal = copy.deepcopy(next(d for d in ALL_DEALS if d["id"] == "502"))  # EUR 85000
    deal["properties"]["amount_in_home_currency"] = "93500"  # rate 1.10
    row = HubSpotAdapter().configured(cfg).to_canonical(deal)
    assert row["currency_iso"] == "USD"
    assert row["booked_acv"] == pytest.approx(93500.0)
    assert row["list_acv"] == pytest.approx(110000.0)
    # No derivable rate: list is left unresolved, never mixed across currencies.
    del deal["properties"]["amount_in_home_currency"]
    row = HubSpotAdapter().configured(cfg).to_canonical(deal)
    assert row["list_acv"] is None and row["list_source"] == "none"
    with pytest.raises(HubSpotConfigError):
        HubSpotAdapter().configured({**cfg, "property_mapping": {"booked_acv": "hs_acv"}})


def test_mapped_list_and_acv_properties_take_precedence():
    cfg = {**CONFIG, "property_mapping": {"list_acv": "list_price_annual", "booked_acv": "hs_acv"}}
    deal = copy.deepcopy(next(d for d in ALL_DEALS if d["id"] == "501"))
    deal["properties"].update({"list_price_annual": "150000", "hs_acv": "99000"})
    row = HubSpotAdapter().configured(cfg).to_canonical(deal)
    assert (row["list_acv"], row["list_source"]) == (150000.0, "mapped_field")
    assert (row["booked_acv"], row["booked_source"]) == (99000.0, "deal_property")


def test_amount_disagreeing_with_line_items_is_flagged_not_hidden(adapter):
    deal = copy.deepcopy(next(d for d in ALL_DEALS if d["id"] == "501"))
    deal["properties"]["amount"] = "70000"
    row = adapter.to_canonical(deal)
    # Booked is the deal amount; the line net only feeds the mismatch, and the
    # list on the disagreeing line basis is dropped with its reason.
    assert row["booked_acv"] == 70000.0 and row["booked_source"] == "deal_property"
    assert row["amount_mismatch"] is True
    assert row["list_acv"] is None and row["list_reason"] == "list_dropped_basis_mismatch"


def test_company_association_shapes(adapter):
    deal = copy.deepcopy(next(d for d in ALL_DEALS if d["id"] == "501"))
    deal["associations"] = {"companies": [
        {"toObjectId": 111, "associationTypes": [{"typeId": 341}]},
        {"toObjectId": 222, "associationTypes": [{"typeId": 5}]}]}
    assert adapter.to_canonical(deal)["source_account_id"] == "222"
    deal["associations"] = {}
    assert adapter.to_canonical(deal)["source_account_id"] == "9001"  # expanded company


def test_no_margin_cost_or_salesforce_wording():
    row = HubSpotAdapter().configured(CONFIG).to_canonical(ALL_DEALS[0])
    assert "cogs_acv" not in row and "cost_basis" not in row
    source = (ROOT / "pricing" / "adapters" / "hubspot.py").read_text(encoding="utf-8").lower()
    assert "salesforce" not in source
    assert "margin" not in source


# --- purity ------------------------------------------------------------------

def test_to_canonical_does_not_mutate_input_and_is_repeatable(adapter):
    before = copy.deepcopy(ALL_DEALS)
    first = [adapter.to_canonical(d) for d in ALL_DEALS]
    assert ALL_DEALS == before
    assert [adapter.to_canonical(d) for d in ALL_DEALS] == first


def test_to_canonical_opens_no_socket(adapter, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    assert [adapter.to_canonical(d)["opportunity_id"] for d in ALL_DEALS]


# --- registry ----------------------------------------------------------------

def test_registry_default_and_membership():
    assert get_adapter(None) is crm.ADAPTER
    assert get_adapter("") is crm.ADAPTER
    assert get_adapter("  Salesforce ") is crm.ADAPTER
    assert isinstance(get_adapter("csv"), CsvAdapter)
    assert get_adapter("hubspot").system == "hubspot"
    assert set(REGISTRY) == {"salesforce", "csv", "hubspot"}
    for system, registered in REGISTRY.items():
        assert registered.system == system


def test_registry_unknown_system_raises_named_error():
    with pytest.raises(UnknownSourceSystemError, match="registered: csv, hubspot, salesforce") as err:
        get_adapter("stripe")
    assert "stripe" not in str(err.value)  # the caller's value is not echoed
    with pytest.raises(UnknownSourceSystemError):
        get_adapter("billing")  # a SourceSystem value with no adapter yet


# --- API: per-request source resolution --------------------------------------

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


def _synthetic_record(i: int, *, won: bool, with_lines: bool = True,
                      list_acv: float = 100_000.0, booked_acv: float = 90_000.0,
                      stage: str | None = None) -> dict:
    stage = stage or ("won" if won else "lost")
    record = {
        "id": str(1000 + i),
        "properties": {
            "dealname": f"Acct {i}", "amount": str(booked_acv), "dealstage": stage,
            "pipeline": "p_book", "closedate": "2026-03-01T00:00:00Z",
            "createdate": "2025-12-01T00:00:00Z", "deal_currency_code": "USD",
        },
        "associations": {"companies": {"results": [{"id": str(5000 + i)}]}},
        "company": {"id": str(5000 + i), "properties": {"name": f"Acct {i}"}},
    }
    if with_lines:
        record["line_items"] = [{"id": f"li{i}", "properties": {
            "price": str(list_acv), "quantity": "1", "amount": str(booked_acv)}}]
    return record


BOOK_CONFIG = {
    "portal_id": "4412345",
    "stage_map": [
        {"pipeline_id": "p_book", "stage_id": "won", "label": "Won", "outcome": "won", "confirmed": True},
        {"pipeline_id": "p_book", "stage_id": "lost", "label": "Lost", "outcome": "lost", "confirmed": True},
        {"pipeline_id": "p_book", "stage_id": "open", "label": "Open", "outcome": "open", "confirmed": True},
        {"pipeline_id": "p_book", "stage_id": "review", "label": "Review", "outcome": "won", "confirmed": False},
    ],
}


def _book() -> list[dict]:
    closed = pd.read_csv(ROOT / "data" / "synthetic" / "deals.csv").head(240)
    records = [
        _synthetic_record(i, won=row.outcome == "closed_won", list_acv=float(row.list_acv),
                          booked_acv=float(row.booked_acv))
        for i, row in enumerate(closed.itertuples())
    ]
    records.append(_synthetic_record(9001, won=False, stage="open",
                                     list_acv=100_000.0, booked_acv=70_000.0))
    records.append(_synthetic_record(9002, won=False, stage="review"))
    return records


def test_analyze_with_source_system_hubspot_uses_the_hubspot_adapter(client, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("the Salesforce path must not run for hubspot")
    monkeypatch.setattr(crm_router.crm_mod, "analyze_records", boom)
    resp = client.post("/crm/analyze", json={
        "records": _book(), "source_system": "hubspot", "source_config": BOOK_CONFIG})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["analysis"]["overview"]["opportunities"] == 240
    guide = body["guidance"][0]
    assert guide["deal_id"] == "10001"  # open deal index 9001 -> id 1000 + 9001
    assert guide["source_url"] == "https://app.hubspot.com/contacts/4412345/record/0-3/10001"
    assert guide["evidence_source"] == "band_guardrail"
    readiness = body["readiness"]
    assert readiness["ask_user"]["deals"] == 1
    assert readiness["ask_user"]["by_stage"][0]["reason"] == "stage_unconfirmed"
    assert readiness["list_source_counts"]["line_items"] == 242
    assert readiness["open_usable"] == 1


def test_analyze_without_source_system_stays_salesforce(client, monkeypatch):
    seen = {}

    def fake(records, policy_threshold_pct=15.0, *, list_field_mapped=False):
        seen["called"] = True
        return {"analysis": {"overview": {}}, "guidance": [], "readiness": {"marker": 1}}
    monkeypatch.setattr(crm_router.crm_mod, "analyze_records", fake)
    monkeypatch.setattr(crm_router, "analysis_payload", lambda a: a)
    for body in ({"records": []}, {"records": [], "source_system": ""},
                 {"records": [], "source_system": "salesforce",
                  "source_config": {"ignored": True}}):
        seen.clear()
        resp = client.post("/crm/analyze", json=body)
        assert resp.status_code == 200 and seen == {"called": True}, body


def test_analyze_unknown_source_and_bad_config_are_422(client):
    resp = client.post("/crm/analyze", json={"records": [], "source_system": "stripe"})
    assert resp.status_code == 422 and "stripe" not in resp.json()["detail"]
    resp = client.post("/crm/analyze", json={"records": [], "source_system": "x" * 33})
    assert resp.status_code == 422
    resp = client.post("/crm/analyze", json={
        "records": [], "source_system": "hubspot", "source_config": {"portal_id": "x"}})
    assert resp.status_code == 422
    resp = client.post("/crm/analyze", json={"records": [], "source_system": "hubspot"})
    assert resp.status_code == 422 and "portal_id" in resp.json()["detail"]


def test_hubspot_without_list_prices_names_the_blocker(client):
    records = [_synthetic_record(i, won=i % 2 == 0, with_lines=False) for i in range(60)]
    resp = client.post("/crm/analyze", json={
        "records": records, "source_system": "hubspot", "source_config": BOOK_CONFIG})
    assert resp.status_code == 422
    assert "at least 30" in resp.json()["detail"]


def test_only_analyze_is_hubspot_enabled(client):
    """Workflow, reconcile and write-back refuse any non-Salesforce source, and
    nothing is logged: a request body is never a source of HubSpot outcomes."""
    wf = client.post("/crm/workflow", json={
        "records": _book(), "source_system": "hubspot", "source_config": BOOK_CONFIG,
        "deal_id": "10001", "event": "flagged", "actor": "A. Rep"})
    assert wf.status_code == 422 and "/crm/workflow" in wf.json()["detail"]
    rec = client.post("/crm/reconcile", json={
        "outcomes": [{"deal_id": "10001", "outcome": "closed_won"}],
        "source_system": "hubspot"})
    assert rec.status_code == 422 and "/crm/reconcile" in rec.json()["detail"]
    wb = client.post("/crm/writeback", json={
        "deal_id": "10001", "actor": "x", "action_event": "flagged", "success": True,
        "source_system": "hubspot"})
    assert wb.status_code == 422
    assert governance.STORE.list(kind="exception", limit=10) == []
    # The log read is per-source and empty for HubSpot.
    assert client.get("/crm/workflow", params={"source_system": "hubspot"}).json()["items"] == []
    assert client.get("/crm/workflow", params={"source_system": "x" * 33}).status_code == 422


def test_salesforce_analyze_adds_neutral_keys_beside_legacy_ones(client, monkeypatch):
    legacy = {"opportunity_id": "O1", "salesforce_url": "/lightning/r/Opportunity/O1/view",
              "comparables": [{"opportunity_id": "O2"}]}
    monkeypatch.setattr(crm_router.crm_mod, "analyze_records",
                        lambda *a, **k: {"analysis": {}, "guidance": [legacy], "readiness": {}})
    monkeypatch.setattr(crm_router, "analysis_payload", lambda a: a)
    row = client.post("/crm/analyze", json={"records": []}).json()["guidance"][0]
    assert row["deal_id"] == "O1" and row["opportunity_id"] == "O1"
    assert row["source_url"] == row["salesforce_url"] == "/lightning/r/Opportunity/O1/view"
    assert row["comparables"] == [{"opportunity_id": "O2", "deal_id": "O2"}]
    assert "deal_id" not in legacy  # the wrapper's own output is not mutated


def test_floor_refusal_explains_ask_user_and_list_sources(client):
    records = [_synthetic_record(i, won=True, stage="review") for i in range(40)]
    resp = client.post("/crm/analyze", json={
        "records": records, "source_system": "hubspot", "source_config": BOOK_CONFIG})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "at least 30" in detail and "40 deals" in detail and '"line_items": 40' in detail
    assert "Acct" not in detail  # counts only


def test_readiness_surfaces_booked_sources_and_mismatch_counts(client):
    book = _book()
    book[0]["properties"]["amount"] = "1"  # typed amount far from its line items
    resp = client.post("/crm/analyze", json={
        "records": book, "source_system": "hubspot", "source_config": BOOK_CONFIG})
    readiness = resp.json()["readiness"]
    assert readiness["booked_source_counts"] == {"deal_property": 242}
    assert readiness["amount_mismatch"] == 1


# --- money safety and shared basis -------------------------------------------

def _line(price=None, qty=None, amount=None) -> dict:
    props = {k: v for k, v in {"price": price, "quantity": qty, "amount": amount}.items()
             if v is not None}
    return {"id": "li", "properties": props}


def _basis_deal(lines, amount) -> dict:
    deal = _synthetic_record(1, won=True, with_lines=False)
    deal["properties"].update({"amount": amount, "pipeline": "p_book", "dealstage": "won"})
    deal["line_items"] = lines
    return deal


def _book_adapter() -> HubSpotAdapter:
    return HubSpotAdapter().configured(BOOK_CONFIG)


def test_crafted_numbers_are_dropped_not_fatal():
    adapter = _book_adapter()
    huge = "1E+600000"
    row = adapter.to_canonical(_basis_deal([_line(huge, huge, huge)], "5000"))
    assert row["list_acv"] is None and row["list_source"] == "none"
    assert row["list_reason"] in {"line_unpriced", "no_list_source"}
    assert row["booked_acv"] == 5000.0
    # A deal whose own amount is out of range has no booked value.
    row = adapter.to_canonical(_basis_deal([], huge))
    assert row["booked_acv"] is None
    # Products of in-range values that exceed the bound are skipped too.
    row = adapter.to_canonical(_basis_deal([_line("1E+15", "1E+15", "1")], "5000"))
    assert row["list_acv"] is None


def test_term_months_is_capped_and_prompt():
    import time
    cfg = {**BOOK_CONFIG, "property_mapping": {"term_months": "term"}}
    adapter = HubSpotAdapter().configured(cfg)
    started = time.monotonic()
    for value, want in (("1E+50000000", None), ("601", None), ("600", 600),
                        ("0", 0), ("36", 36), ("-3", None), ("abc", None)):
        deal = _basis_deal([], "5000")
        deal["properties"]["term"] = value
        assert adapter.to_canonical(deal)["term_months"] == want, value
    assert time.monotonic() - started < 2


def test_partial_line_pricing_drops_the_list():
    # One priced line without an amount plus one amount-only line, deal amount
    # 5900: the priced line alone (5000) is not the basis of the 5900 sold.
    deal = _basis_deal([_line("5000", "1"), _line(amount="900")], "5900")
    row = _book_adapter().to_canonical(deal)
    assert row["list_acv"] is None and row["list_source"] == "none"
    assert row["list_reason"] == "line_unpriced"
    assert row["booked_acv"] == 5900.0 and row["booked_source"] == "deal_property"


def test_recurring_line_below_the_deal_total_drops_the_list():
    # Monthly price 1000 x 10 against a 108000 term total: list under booked.
    deal = _basis_deal([_line("1000", "10")], "108000")
    row = _book_adapter().to_canonical(deal)
    assert row["list_acv"] is None and row["list_reason"] == "list_below_booked"
    assert row["booked_acv"] == 108000.0
    # With a line amount that disagrees, booked stays the deal amount, the
    # mismatch is flagged and the list is dropped with the basis reason.
    deal = _basis_deal([_line("1000", "10", "10000")], "108000")
    row = _book_adapter().to_canonical(deal)
    assert (row["list_acv"], row["booked_acv"]) == (None, 108000.0)
    assert row["booked_source"] == "deal_property"
    assert row["list_reason"] == "list_dropped_basis_mismatch"
    assert row["amount_mismatch"] is True


def test_consistent_line_basis_keeps_the_list_and_flags_nothing():
    deal = _basis_deal([_line("1000", "10", "9000")], "9000")
    row = _book_adapter().to_canonical(deal)
    assert (row["list_acv"], row["list_reason"], row["amount_mismatch"]) == (10000.0, "", False)


# --- PK-46 second rework: booked basis, money bound, disclosure, nits -------


def test_line_net_never_replaces_the_deal_amount_probe():
    # Reviewer's probe: annual deal amount 120000, one monthly line priced
    # 12000 with a net of 10000. Booked is the deal amount, never the line net.
    row = _book_adapter().to_canonical(_basis_deal([_line("12000", "1", "10000")], "120000"))
    assert row["booked_acv"] == 120000.0 and row["booked_source"] == "deal_property"
    assert row["list_acv"] is None and row["list_source"] == "none"
    assert row["list_reason"] == "list_dropped_basis_mismatch"
    assert row["amount_mismatch"] is True


@pytest.mark.parametrize("value,kept", [("1000000000000000", True), ("1000000000000001", False),
                                        ("9000000000000000", False), ("9E+15", False)])
def test_money_bound_is_exactly_1e15(value, kept):
    row = _book_adapter().to_canonical(_basis_deal([], value))
    assert (row["booked_acv"] is not None) is kept
    if not kept:
        assert row["booked_source"] == "unparseable"


def test_ask_user_disclosure_does_not_depend_on_error_text(client, monkeypatch):
    from pricing import guardrail
    from pricing.adapters import ClosedFloorError
    original = guardrail.analyze_deals

    def reworded(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except guardrail.DealDataError:
            raise guardrail.DealDataError("Too few closed deals to proceed.") from None

    monkeypatch.setattr(guardrail, "analyze_deals", reworded)
    records = [_synthetic_record(i, won=True, stage="review") for i in range(40)]
    resp = client.post("/crm/analyze", json={
        "records": records, "source_system": "hubspot", "source_config": BOOK_CONFIG})
    assert resp.status_code == 422
    assert "40 deals" in resp.json()["detail"]
    assert ClosedFloorError.code == "closed_floor"
    assert issubclass(ClosedFloorError, guardrail.DealDataError)


def test_mapped_list_without_a_derivable_rate_is_labelled():
    cfg = {**BOOK_CONFIG, "use_home_currency": True, "home_currency": "USD",
           "property_mapping": {"list_acv": "list_price"}}
    adapter = HubSpotAdapter().configured(cfg)
    deal = _basis_deal([], "5000")
    deal["properties"].update({"list_price": "6000", "amount_in_home_currency": "",
                               "deal_currency_code": "EUR"})
    row = adapter.to_canonical(deal)
    assert row["list_acv"] is None
    assert row["list_source"] == "rate_not_derivable" and row["list_reason"] == "rate_not_derivable"


def test_fractional_term_months_is_refused_with_a_reason():
    adapter = HubSpotAdapter().configured({**BOOK_CONFIG, "property_mapping": {"term_months": "term"}})
    deal = _basis_deal([], "5000")
    deal["properties"]["term"] = "12.9"
    row = adapter.to_canonical(deal)
    assert row["term_months"] is None and row["term_reason"] == "term_months_fractional"
    deal["properties"]["term"] = "12.0"
    row = adapter.to_canonical(deal)
    assert row["term_months"] == 12 and row["term_reason"] == ""


def test_non_numeric_amount_is_unparseable_not_deal_property():
    row = _book_adapter().to_canonical(_basis_deal([], "98,000"))
    assert row["booked_acv"] is None
    assert row["booked_source"] == "unparseable" and row["booked_reason"] == "amount_unparseable"
    extras = HubSpotAdapter.readiness_extras([row])
    assert extras["booked_source_counts"] == {"unparseable": 1}


def test_records_hash_is_order_independent_for_raw_hubspot_records():
    from api.routers.crm import _records_hash
    records = [_synthetic_record(i, won=True) for i in range(5)]
    assert _records_hash(records) == _records_hash(list(reversed(records)))
