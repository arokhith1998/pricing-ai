"""Governance-loop tests: decision store, /exceptions verdicts, /digest.

Covers the subscription use case end to end, offline and deterministic:
  1. DecisionStore memory mode (no DATABASE_URL) and database-failure
     degradation (mocked psycopg — no network ever).
  2. Exception verdicts pinned on the demo book: below_floor on both sides
     of the 15 percent floor, EV-delta sign, 404/422, percent 0-100 surface.
  3. Digest aggregation from seeded decision-log entries, including the
     exact headline format.
  4. The perimeter (shared-secret auth + rate-limit rules) on the new
     endpoints.

LLM keys are stripped so nothing calls a provider; DATABASE_URL is stripped
so the store runs in memory; the store and limiter are reset around every
test.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from api import main
from pricing import governance

KEY = "test-secret-key"
AUTH = {"X-Pricekeel-Key": KEY}

FLOOR = 15.0  # DEFAULT_POLICY_THRESHOLD on the percent 0-100 API surface


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    """No API key, no LLM keys, no DATABASE_URL, empty store + limiter."""
    for var in ("PRICEKEEL_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                "DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)
    # Dev path: the no-key endpoint tests below run open (warn-and-allow);
    # prod fail-closed is covered in test_api_perimeter.py.
    monkeypatch.setenv("PRICEKEEL_ENV", "dev")
    governance.STORE.reset_memory()
    main._rate_state_reset()
    yield
    governance.STORE.reset_memory()
    main._rate_state_reset()


@pytest.fixture()
def client():
    return TestClient(main.app)


@pytest.fixture()
def deal_id(client) -> str:
    """A real opportunity id from the demo book (largest won deal)."""
    return client.get("/deals").json()["deals"][0]["opportunity_id"]


# --- 1. DecisionStore: memory mode -------------------------------------------

def test_insert_returns_row_with_id_and_created_at():
    row = governance.STORE.insert(kind="exception", deal_id="D-1",
                                  payload={"a": 1}, decision="below_floor",
                                  justification="why", requested_by="rep")
    assert row["id"] and row["created_at"]
    assert row["kind"] == "exception"
    assert row["payload"] == {"a": 1}


def test_insert_rejects_unknown_kind():
    with pytest.raises(ValueError):
        governance.STORE.insert(kind="mystery")


def test_list_filters_by_kind_and_orders_newest_first():
    governance.STORE.insert(kind="copilot", payload={"session_id": "s1"})
    governance.STORE.insert(kind="exception", deal_id="D-1")
    governance.STORE.insert(kind="exception", deal_id="D-2")

    exc = governance.STORE.list(kind="exception")
    assert [r["deal_id"] for r in exc] == ["D-2", "D-1"]  # newest first
    assert governance.STORE.list(kind="copilot")[0]["payload"] == {
        "session_id": "s1"}
    assert len(governance.STORE.list()) == 3


def test_list_filters_by_session_and_since():
    governance.STORE.insert(kind="copilot", payload={"session_id": "s1"})
    governance.STORE.insert(kind="copilot", payload={"session_id": "s2"})
    old = governance.STORE.insert(kind="exception", deal_id="OLD")
    # Memory-mode insert returns the stored dict itself; age it 9 days.
    old["created_at"] = (governance._now_utc()
                         - timedelta(days=9)).isoformat()

    s1 = governance.STORE.list(kind="copilot", session_id="s1")
    assert len(s1) == 1 and s1[0]["payload"]["session_id"] == "s1"

    recent = governance.STORE.list(
        since=governance._now_utc() - timedelta(days=7))
    assert all(r["deal_id"] != "OLD" for r in recent)
    assert len(recent) == 2


# Fake psycopg connection so the DB-backed paths run with no network. The
# cursor ignores the SQL it is handed and returns the rows it was seeded with;
# context-manager protocol is honored because the store uses `with` on both
# the connection and the cursor.
class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def execute(self, *_a, **_k):
        pass

    def fetchone(self):
        return dict(self._rows[0]) if self._rows else None

    def fetchall(self):
        return [dict(r) for r in self._rows]


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def cursor(self, *_a, **_k):
        return _FakeCursor(self._rows)


def _fake_connect_returning(rows):
    def _connect(*_a, **_k):
        return _FakeConn(rows)
    return _connect


def test_db_failure_degrades_to_memory(monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid/db")

    def boom(*_a, **_k):
        raise RuntimeError("network down")

    monkeypatch.setattr(governance.psycopg, "connect", boom)

    with caplog.at_level(logging.WARNING, logger="pricekeel.governance"):
        row = governance.STORE.insert(kind="exception", deal_id="D-1")
        rows = governance.STORE.list(kind="exception")
    assert row["id"] and row["created_at"]  # the caller's request succeeded
    assert [r["deal_id"] for r in rows] == ["D-1"]
    assert "fell back to memory" in caplog.text


def test_memory_insert_reports_not_persisted():
    # Finding 5: a memory-fallback write must not claim durability.
    row = governance.STORE.insert(kind="exception", deal_id="D-1")
    assert row["persisted"] is False


def test_db_success_reports_persisted(monkeypatch):
    # Finding 5: a durable DB write reports persisted=True.
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    fixture = {"id": "u-1", "created_at": "2026-06-11T00:00:00+00:00",
               "kind": "exception", "deal_id": "D-1"}
    monkeypatch.setattr(governance.psycopg, "connect",
                        _fake_connect_returning([fixture]))
    row = governance.STORE.insert(kind="exception", deal_id="D-1")
    assert row["id"] == "u-1"
    assert row["persisted"] is True


def test_db_list_returns_rows_from_db(monkeypatch):
    # The new SQL read path returns DB rows, newest first.
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    fixture = [
        {"id": "u-2", "created_at": "2026-06-11T00:00:02+00:00",
         "kind": "exception", "deal_id": "D-2", "customer_ref": "default",
         "payload": {}},
        {"id": "u-1", "created_at": "2026-06-11T00:00:01+00:00",
         "kind": "exception", "deal_id": "D-1", "customer_ref": "default",
         "payload": {}},
    ]
    monkeypatch.setattr(governance.psycopg, "connect",
                        _fake_connect_returning(fixture))
    out = governance.STORE.list(kind="exception")
    assert [r["deal_id"] for r in out] == ["D-2", "D-1"]


# --- 1c. tenant scoping (Finding 3) ------------------------------------------

def test_store_list_scoped_by_customer_ref():
    governance.STORE.insert(kind="exception", deal_id="A-1", customer_ref="A")
    governance.STORE.insert(kind="exception", deal_id="B-1", customer_ref="B")
    a = governance.STORE.list(kind="exception", customer_ref="A")
    b = governance.STORE.list(kind="exception", customer_ref="B")
    assert [r["deal_id"] for r in a] == ["A-1"]
    assert [r["deal_id"] for r in b] == ["B-1"]
    # Default scope sees neither A nor B.
    assert governance.STORE.list(kind="exception", customer_ref="default") == []


def test_exceptions_isolated_across_customers_via_header(client, deal_id):
    # Write as customer A; a read as customer B must not see it.
    client.post("/exceptions",
                json={"deal_id": deal_id, "requested_discount_pct": 25.0,
                      "justification": "A's deal", "requested_by": "a@x.com"},
                headers={"X-Pricekeel-Customer": "A"})
    a_items = client.get("/exceptions",
                         headers={"X-Pricekeel-Customer": "A"}).json()["items"]
    b_items = client.get("/exceptions",
                         headers={"X-Pricekeel-Customer": "B"}).json()["items"]
    assert len(a_items) == 1
    assert b_items == []
    # No header => "default", also isolated from A.
    assert client.get("/exceptions").json()["items"] == []


def test_exceptions_response_includes_persisted_flag(client, deal_id):
    # Memory mode (no DATABASE_URL): persisted must be False, never claimed.
    r = client.post("/exceptions",
                    json={"deal_id": deal_id, "requested_discount_pct": 20.0,
                          "justification": "x", "requested_by": "rep@x.com"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"id", "verdict", "created_at", "persisted"}
    assert body["persisted"] is False


def test_copilot_decisions_isolated_across_customers(client):
    client.post("/copilot/log",
                json={"session_id": "s1", "qid": "losing_deals", "note": "A"},
                headers={"X-Pricekeel-Customer": "A"})
    a = client.get("/copilot/decisions", params={"session_id": "s1"},
                   headers={"X-Pricekeel-Customer": "A"}).json()
    b = client.get("/copilot/decisions", params={"session_id": "s1"},
                   headers={"X-Pricekeel-Customer": "B"}).json()
    assert len(a["decisions"]) == 1
    assert b["decisions"] == []


def test_digest_scoped_by_customer(client, deal_id):
    client.post("/exceptions",
                json={"deal_id": deal_id, "requested_discount_pct": 30.0,
                      "justification": "x", "requested_by": "rep@x.com"},
                headers={"X-Pricekeel-Customer": "A"})
    a = client.get("/digest", headers={"X-Pricekeel-Customer": "A"}).json()
    b = client.get("/digest", headers={"X-Pricekeel-Customer": "B"}).json()
    assert a["customer"] == "A"
    assert a["stats"]["exceptions_total"] == 1
    assert b["customer"] == "B"
    assert b["stats"]["exceptions_total"] == 0


def test_digest_all_returns_one_digest_per_active_tenant_excluding_demo(client):
    """2026-09-27 fix: after the per-visitor demo:<uuid> tenant fix, nobody
    writes to the 'default' tenant GET /digest defaults to, so the cron email
    reported zero activity forever. GET /digest/all walks every tenant with
    decision-log activity in the window instead, excluding demo:* tenants
    (each anonymous sample-page visitor mints its own)."""
    governance.STORE.insert(
        kind="exception", deal_id="A-1",
        payload={"deal_id": "A-1", "requested_discount_pct": 22.0,
                 "requested_by": "a@customer-a.com",
                 "verdict": {"below_floor": True}},
        decision="below_floor", requested_by="a@customer-a.com",
        customer_ref="ACME-CODE",
    )
    governance.STORE.insert(
        kind="exception", deal_id="B-1",
        payload={"deal_id": "B-1", "requested_discount_pct": 5.0,
                 "requested_by": "b@customer-b.com",
                 "verdict": {"below_floor": False}},
        decision="within_floor", requested_by="b@customer-b.com",
        customer_ref="BRAVO-CODE",
    )
    # An anonymous demo visitor's activity must never appear here.
    governance.STORE.insert(
        kind="copilot", payload={"session_id": "s1"},
        customer_ref="demo:11111111-1111-1111-1111-111111111111",
    )

    r = client.get("/digest/all")
    assert r.status_code == 200
    body = r.json()
    assert set(body["customers"]) == {"ACME-CODE", "BRAVO-CODE"}
    assert not any(c.startswith("demo:") for c in body["customers"])

    by_customer = {d["customer"]: d for d in body["digests"]}
    assert by_customer["ACME-CODE"]["stats"]["exceptions_total"] == 1
    assert by_customer["ACME-CODE"]["stats"]["exceptions_below_floor"] == 1
    assert by_customer["BRAVO-CODE"]["stats"]["exceptions_total"] == 1
    assert by_customer["BRAVO-CODE"]["stats"]["exceptions_below_floor"] == 0
    assert all(d["book_source"] == "demo" for d in body["digests"])


def test_digest_all_is_empty_when_no_tenant_has_activity(client):
    r = client.get("/digest/all")
    assert r.status_code == 200
    assert r.json() == {"digests": [], "customers": []}


# --- 2. /exceptions verdicts pinned on the demo book --------------------------

def test_exception_below_floor_flag_on_both_sides_of_floor(client, deal_id):
    over = client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": 25.0,
        "justification": "competitor pressure", "requested_by": "rep@x.com"})
    assert over.status_code == 200
    v = over.json()["verdict"]
    assert v["below_floor"] is True
    assert v["floor_pct"] == FLOOR
    assert v["requested_pct"] == 25.0

    under = client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": 10.0,
        "justification": "renewal goodwill", "requested_by": "rep@x.com"})
    assert under.json()["verdict"]["below_floor"] is False

    # Exactly at the floor does not exceed it.
    at = client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": FLOOR,
        "justification": "at floor", "requested_by": "rep@x.com"})
    assert at.json()["verdict"]["below_floor"] is False


def test_exception_verdict_contract_and_ev_delta_sign(client, deal_id):
    r = client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": 25.0,
        "justification": "competitor pressure", "requested_by": "rep@x.com"})
    body = r.json()
    # Contract gained a `persisted` field (Finding 5).
    assert set(body) == {"id", "verdict", "created_at", "persisted"}
    assert body["persisted"] is False  # memory mode in tests
    assert isinstance(body["id"], str) and body["id"]
    v = body["verdict"]
    assert set(v) == {"requested_pct", "recommended_pct", "floor_pct",
                      "below_floor", "ev_delta_vs_recommended",
                      "win_prob_at_requested", "win_prob_at_recommended",
                      "rationale", "method"}
    # The demo path sweeps the deal's cohort-clipped EV curve; the verdict
    # carries the engine's own label (an interior peak, or the support floor
    # when the peak sits on the edge of the cohort's support), so it is never
    # mistaken for the live band guardrail.
    assert v["method"] in ("modeled_ev_curve", "support_floor")
    # Percent 0-100 surface; the model grid tops out at 40.
    assert 0.0 <= v["recommended_pct"] <= 40.0
    # Win probabilities stay 0-1 fractions.
    assert 0.0 <= v["win_prob_at_requested"] <= 1.0
    assert 0.0 <= v["win_prob_at_recommended"] <= 1.0
    # EV(requested) - EV(recommended) can never be positive: the recommended
    # discount maximizes expected ACV on the same sweep.
    assert v["ev_delta_vs_recommended"] <= 0.0
    # 25 percent on the largest demo deal sits past the EV optimum, so the
    # delta is strictly negative and the recommendation is below the request.
    assert v["ev_delta_vs_recommended"] < 0.0
    assert v["recommended_pct"] < 25.0
    # One plain sentence from the numbers (no sentence boundary inside;
    # periods inside decimals do not count); house style bans em dashes.
    assert v["rationale"].endswith(".") and ". " not in v["rationale"]
    assert "percent" in v["rationale"]
    assert "—" not in v["rationale"]
    print("\nPINNED demo-book verdict (deal", deal_id, "at 25.0):",
          {k: v[k] for k in ("recommended_pct", "ev_delta_vs_recommended",
                             "win_prob_at_requested",
                             "win_prob_at_recommended")})


def test_exceptions_and_recommend_agree_on_one_deal(client):
    """code-reviewer major (2026-09-26): exception_verdict used to call
    recommend_discount without the cohort, so /exceptions swept 0-40% while
    /recommend swept the clipped cohort grid and the two disagreed on the
    same deal. Requesting exactly the deal's own discount must now reproduce
    /recommend's recommendation, win probabilities and method, on a deal
    from every segment."""
    deals = client.get("/deals", params={"limit": 200}).json()["deals"]
    by_segment = {}
    for d in deals:
        by_segment.setdefault(d["segment"], d)
    assert len(by_segment) >= 2
    for seg, d in by_segment.items():
        rec = client.post("/recommend", json={
            "opportunity_id": d["opportunity_id"]}).json()
        exc = client.post("/exceptions", json={
            "deal_id": d["opportunity_id"],
            "requested_discount_pct": rec["current_discount"] * 100.0,
            "justification": "parity check", "requested_by": "test"}).json()
        v = exc["verdict"]
        assert v["method"] == rec["method"], seg
        assert v["recommended_pct"] == pytest.approx(
            rec["recommended_discount"] * 100.0, abs=1e-6), seg
        assert v["win_prob_at_recommended"] == pytest.approx(
            rec["win_prob_at_rec"], abs=1e-9), seg
        assert v["win_prob_at_requested"] == pytest.approx(
            rec["win_prob_at_current"], abs=1e-9), seg
        assert v["ev_delta_vs_recommended"] == pytest.approx(
            -rec["uplift"], abs=1e-6), seg


def test_exception_unknown_deal_404(client):
    r = client.post("/exceptions", json={
        "deal_id": "OPP-DOES-NOT-EXIST", "requested_discount_pct": 20.0,
        "justification": "x", "requested_by": "rep@x.com"})
    assert r.status_code == 404


def test_exception_justification_and_requested_by_length_caps_422(client, deal_id):
    over_justification = client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": 20.0,
        "justification": "x" * 2001, "requested_by": "rep@x.com"})
    assert over_justification.status_code == 422

    over_requested_by = client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": 20.0,
        "justification": "x", "requested_by": "y" * 121})
    assert over_requested_by.status_code == 422

    at_cap = client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": 20.0,
        "justification": "x" * 2000, "requested_by": "y" * 120})
    assert at_cap.status_code == 200


def test_exception_out_of_range_422(client, deal_id):
    for bad in (-1.0, 40.5, 100.0):
        r = client.post("/exceptions", json={
            "deal_id": deal_id, "requested_discount_pct": bad,
            "justification": "x", "requested_by": "rep@x.com"})
        assert r.status_code == 422, bad
    # 40.0 is the inclusive top of the modeled grid.
    ok = client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": 40.0,
        "justification": "x", "requested_by": "rep@x.com"})
    assert ok.status_code == 200


def test_exception_persists_and_lists_newest_first(client, deal_id):
    for pct in (12.0, 30.0):
        client.post("/exceptions", json={
            "deal_id": deal_id, "requested_discount_pct": pct,
            "justification": f"j-{pct}", "requested_by": "rep@x.com"})
    r = client.get("/exceptions", params={"limit": 50})
    assert r.status_code == 200
    items = r.json()["items"]
    assert [i["requested_discount_pct"] for i in items] == [30.0, 12.0]
    top = items[0]
    assert set(top) == {"id", "deal_id", "requested_discount_pct",
                        "justification", "requested_by", "verdict",
                        "created_at"}
    assert top["deal_id"] == deal_id
    assert top["justification"] == "j-30.0"
    assert top["verdict"]["below_floor"] is True
    # Persisted with kind='exception' through the governance store.
    assert len(governance.STORE.list(kind="exception")) == 2
    # limit=1 truncates.
    assert len(client.get("/exceptions", params={"limit": 1}).json()["items"]) == 1


# --- 3. /copilot/log + /copilot/decisions persist through the store -----------

def test_copilot_log_keeps_contract_and_persists(client):
    r = client.post("/copilot/log", json={
        "session_id": "s1", "qid": "losing_deals",
        "accepted": ["o1"], "rejected": ["o2"], "note": "took the first"})
    assert r.status_code == 200
    body = r.json()
    assert body["logged"] is True
    d = body["decision"]
    assert d["qid"] == "losing_deals"
    assert d["opportunities_accepted"] == ["o1"]
    assert d["opportunities_rejected"] == ["o2"]

    out = client.get("/copilot/decisions",
                     params={"session_id": "s1"}).json()
    assert out["session_id"] == "s1"
    assert len(out["decisions"]) == 1
    assert out["decisions"][0]["note"] == "took the first"
    # Sessions are isolated; rows land in the store with kind='copilot'.
    assert client.get("/copilot/decisions",
                      params={"session_id": "s2"}).json()["decisions"] == []
    assert len(governance.STORE.list(kind="copilot")) == 1


# --- 4. digest aggregation -----------------------------------------------------

def _seed_exception(pct: float, below: bool, deal: str = "D-1",
                    who: str = "rep@x.com") -> dict:
    return governance.STORE.insert(
        kind="exception", deal_id=deal,
        payload={"deal_id": deal, "requested_discount_pct": pct,
                 "justification": "j", "requested_by": who,
                 "verdict": {"below_floor": below}},
        decision="below_floor" if below else "within_floor",
        requested_by=who,
    )


def test_digest_aggregates_seeded_entries_with_exact_headline():
    _seed_exception(22.0, True, deal="D-22")
    _seed_exception(18.0, True, deal="D-18")
    _seed_exception(10.0, False, deal="D-10")
    governance.STORE.insert(kind="copilot", payload={"session_id": "s1"})
    governance.STORE.insert(kind="copilot", payload={"session_id": "s1"})
    # An 8-day-old below-floor exception must fall outside the window.
    stale = _seed_exception(39.0, True, deal="D-OLD")
    stale["created_at"] = (governance._now_utc()
                           - timedelta(days=8)).isoformat()

    analysis = {
        "overview": {"price_realization_won": 0.814},
        "leakage": {"excess_vs_segment_reference_won": 1_234_567.0,
                    "reference_threshold": 0.09},
    }
    d = governance.build_digest(analysis=analysis)

    assert d["headline"] == ("3 exception requests this week, 2 below the "
                             "15 percent floor; realization 81.4 percent.")
    assert d["window_days"] == 7
    assert d["customer"] == "default"
    assert d["stats"] == {
        "exceptions_total": 3,
        "exceptions_below_floor": 2,
        "copilot_decisions": 2,
        "realization_pct": pytest.approx(81.4),
        "excess_vs_segment_reference": 1_234_567.0,
    }
    assert 3 <= len(d["lines"]) <= 6
    joined = " ".join(d["lines"]) + d["headline"]
    assert "—" not in joined  # no em dashes in generated text
    # The largest below-floor request (22.0, not the stale 39.0) is named.
    assert any("22.0 percent" in ln and "D-22" in ln for ln in d["lines"])
    assert not any("D-OLD" in ln for ln in d["lines"])


def test_digest_counts_one_crm_override_not_the_approval_or_writeback():
    """Known-answer test for the digest miscount (code-reviewer finding,
    reproduced): one CRM override request, its approval, and one writeback
    receipt must render as 1 exception request, 1 outside the floor, not 3
    requests / 0 below floor."""
    override_verdict = {"requested_pct": 32.0, "outside_guardrail": True}
    governance.STORE.insert(
        kind="exception", deal_id="SF-1",
        payload={"source": "salesforce_crm", "event": "override_requested",
                 "actor": "rep@x.com", "verdict": override_verdict},
        decision="override_requested", requested_by="rep@x.com",
    )
    governance.STORE.insert(
        kind="exception", deal_id="SF-1",
        payload={"source": "salesforce_crm", "event": "approved",
                 "actor": "desk@x.com", "verdict": override_verdict},
        decision="approved", requested_by="desk@x.com",
    )
    governance.STORE.insert(
        kind="exception", deal_id="SF-1",
        payload={"source": "salesforce_crm_writeback",
                 "event": "salesforce_writeback_succeeded",
                 "actor": "desk@x.com", "verdict": override_verdict},
        decision="salesforce_writeback_succeeded", requested_by="desk@x.com",
    )

    d = governance.build_digest(analysis=None)

    assert d["headline"] == ("1 exception request this week, 1 below the "
                             "15 percent floor.")
    assert d["stats"]["exceptions_total"] == 1
    assert d["stats"]["exceptions_below_floor"] == 1


def test_digest_without_book_has_null_stats():
    d = governance.build_digest(analysis=None)
    assert d["headline"] == ("0 exception requests this week, 0 below the "
                             "15 percent floor.")
    assert d["stats"]["realization_pct"] is None
    assert d["stats"]["excess_vs_segment_reference"] is None
    assert any("No deal book is loaded" in ln for ln in d["lines"])
    assert 3 <= len(d["lines"]) <= 6


def test_digest_endpoint_reflects_logged_exception(client, deal_id):
    client.post("/exceptions", json={
        "deal_id": deal_id, "requested_discount_pct": 30.0,
        "justification": "big logo", "requested_by": "rep@x.com"})
    r = client.get("/digest")
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"customer", "generated_at", "window_days", "headline",
                      "lines", "stats", "book_source"}
    # The book half is demo-derived regardless of tenant until a per-tenant
    # book is persisted (CONTRACT B).
    assert d["book_source"] == "demo"
    assert d["window_days"] == 7
    assert d["stats"]["exceptions_total"] == 1
    assert d["stats"]["exceptions_below_floor"] == 1
    # The demo book is loaded, so realization is a percent 0-100.
    assert d["stats"]["realization_pct"] is not None
    assert 0.0 < d["stats"]["realization_pct"] <= 100.0
    assert d["headline"].startswith("1 exception request this week, 1 below "
                                    "the 15 percent floor; realization ")
    print("\nPINNED demo-book digest stats:", d["stats"])


# --- 5. perimeter on the new endpoints ----------------------------------------

def test_governance_endpoints_require_api_key(client, monkeypatch):
    monkeypatch.setenv("PRICEKEEL_API_KEY", KEY)
    assert client.get("/exceptions").status_code == 401
    assert client.get("/digest").status_code == 401
    body = {"deal_id": "nope", "requested_discount_pct": 20.0,
            "justification": "x", "requested_by": "rep@x.com"}
    assert client.post("/exceptions", json=body).status_code == 401
    # With the key, requests pass the perimeter and hit the handlers.
    assert client.get("/exceptions", headers=AUTH).status_code == 200
    assert client.get("/digest", headers=AUTH).status_code == 200
    assert client.post("/exceptions", json=body,
                       headers=AUTH).status_code == 404  # auth ok, bad deal


def test_exceptions_post_is_rate_limited(client, monkeypatch):
    assert main._rate_rule_for("/exceptions") is not None
    monkeypatch.setitem(main.RATE_LIMITS, "/exceptions", (2, 60.0))
    body = {"deal_id": "nope", "requested_discount_pct": 20.0,
            "justification": "x", "requested_by": "rep@x.com"}
    for _ in range(2):
        assert client.post("/exceptions", json=body).status_code == 404
    r = client.post("/exceptions", json=body)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1
    # GETs stay unmetered, same as the other guidance-tier reads.
    for _ in range(5):
        assert client.get("/exceptions").status_code == 200
