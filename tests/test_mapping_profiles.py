"""PK-27: layer-0 source profiles, quote-line roll-up, stage normalisation,
the outcome refuse path, and the header-only LLM payload.

Profiles are generic export shapes, not vendor presets (founder decision D4).
Fixtures are synthetic: invented account names, no real company data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pricing import assist, mapping
from pricing.mapping import (
    CPQ_ROLLUP_SPEC, EXACT_ONLY_FIELDS, OUTCOME_ASK_USER, OUTCOME_VALUES,
    map_headers, normalize_stage, normalize_stage_series, outcome_refusal,
    profile_source, rollup_quote_lines,
)

FIX = Path(__file__).parent / "fixtures" / "mapping_profiles"


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIX / name, dtype=str, keep_default_na=False)


@pytest.fixture(scope="module")
def crm() -> pd.DataFrame:
    return _load("crm_opportunity.csv")


@pytest.fixture(scope="module")
def cpq() -> pd.DataFrame:
    return _load("cpq_quote_lines.csv")


@pytest.fixture(scope="module")
def billing() -> pd.DataFrame:
    return _load("billing_subscriptions.csv")


# --- profile detection -------------------------------------------------------

def test_crm_fixture_is_crm_opportunity_with_evidence(crm):
    p = profile_source(list(crm.columns))
    assert p["profile"] == "crm_opportunity"
    assert p["confidence"] == "high"
    assert set(p["evidence"]) == {"Stage", "Close Date", "Amount"}
    assert set(p["evidence"]) <= set(crm.columns)
    assert p["rollup"] is None


def test_cpq_fixture_is_cpq_line_with_evidence(cpq):
    p = profile_source(list(cpq.columns))
    assert p["profile"] == "cpq_line"
    assert p["confidence"] == "high"
    assert {"Quote ID", "Line ID", "Quantity", "Unit Price", "Quote Status"} <= set(p["evidence"])
    assert set(p["evidence"]) <= set(cpq.columns)
    assert p["rollup"] is CPQ_ROLLUP_SPEC
    assert p["roles"]["quote_id"] == "Quote ID"


def test_billing_fixture_is_unknown(billing):
    p = profile_source(list(billing.columns))
    assert p["profile"] == "unknown"
    assert "outcome" in p["missing"]


def test_no_vendor_named_profile_exists():
    names = {mapping.PROFILE_CRM, mapping.PROFILE_CPQ, mapping.PROFILE_UNKNOWN}
    for n in names:
        for vendor in ("hubspot", "dealhub", "pandadoc", "salesforce"):
            assert vendor not in n


def test_profile_source_takes_headers_only():
    import inspect
    assert list(inspect.signature(profile_source).parameters) == ["headers"]
    p = profile_source(["Opportunity ID", "Stage", "Close Date", "Amount"])
    assert p["profile"] == "crm_opportunity"


# --- roll-up -----------------------------------------------------------------

def test_rollup_one_deal_per_quote_with_summed_amounts(cpq):
    deals = rollup_quote_lines(cpq)
    assert deals["source_quote_id"].tolist() == sorted(cpq["Quote ID"].unique())
    assert len(deals) == cpq["Quote ID"].nunique() < len(cpq)
    assert deals.attrs["join_key"] == "Quote ID"
    qty = cpq["Quantity"].astype(float)
    net = (cpq["Unit Price"].astype(float) * qty).groupby(cpq["Quote ID"]).sum()
    lst = (cpq["List Unit Price"].astype(float) * qty).groupby(cpq["Quote ID"]).sum()
    for _, d in deals.iterrows():
        assert d["booked_acv"] == pytest.approx(net[d["source_quote_id"]])
        assert d["list_acv"] == pytest.approx(lst[d["source_quote_id"]])
        assert d["source_system"] == "cpq"
    assert deals["line_count"].sum() == len(cpq)


def test_rollup_outcome_comes_from_quote_status(cpq):
    deals = rollup_quote_lines(cpq).set_index("source_quote_id")
    assert deals.loc["Q-2001", "outcome"] == "closed_won"
    # A declined quote is not a CRM closed-lost: ask_user (decision B).
    assert deals.loc["Q-2002", "outcome"] == "ask_user"
    assert deals.loc["Q-2004", "outcome"] == "open"
    assert set(deals["outcome"]) <= set(OUTCOME_VALUES)


def test_rollup_expired_quote_is_ask_user_not_lost(cpq):
    deals = rollup_quote_lines(cpq).set_index("source_quote_id")
    assert deals.loc["Q-2006", "outcome"] == "ask_user"
    assert deals.attrs["ask_user"] == {"Q-2002": ["Declined"],
                                       "Q-2006": ["Expired"]}


def test_rollup_conflicting_line_statuses_go_to_ask_user():
    df = pd.DataFrame({
        "Quote ID": ["A", "A"], "Line ID": ["1", "2"], "Quantity": ["1", "1"],
        "Unit Price": ["10", "20"], "Quote Status": ["Accepted", "Declined"],
    })
    deals = rollup_quote_lines(df)
    assert deals.loc[0, "outcome"] == "ask_user"
    assert deals.loc[0, "booked_acv"] == 30


def test_rollup_prefers_line_total_columns_when_present():
    df = pd.DataFrame({
        "Quote ID": ["A", "A", "B"], "Line ID": ["1", "2", "3"],
        "Quantity": ["2", "3", "1"], "Unit Price": ["999", "999", "999"],
        "Line Total": ["$100", "$50", "$70"],
        "Line List Total": ["120", "60", "80"],
        "Quote Status": ["Accepted"] * 3,
    })
    d = rollup_quote_lines(df).set_index("source_quote_id")
    assert d.loc["A", "booked_acv"] == 150 and d.loc["A", "list_acv"] == 180
    assert d.loc["B", "booked_acv"] == 70


def test_rollup_without_quote_id_raises(crm):
    with pytest.raises(ValueError):
        rollup_quote_lines(crm)


# --- stage normalisation -----------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("Closed Won", "closed_won"), ("closed-won", "closed_won"),
    ("ClosedWon", "closed_won"), ("Accepted", "closed_won"),
    ("Closed Lost", "closed_lost"), ("Lost", "closed_lost"),
    ("Negotiation/Review", "open"), ("Prospecting", "open"), ("Draft", "open"),
])
def test_known_stages_map_into_the_closed_enum(raw, expected):
    assert normalize_stage(raw) == expected


@pytest.mark.parametrize("raw", [
    "Expired", "Closed", "Closed - Lost to Competitor", "On hold", "Churned",
    "Cancelled", "Pending Legal", "", "  ", None, float("nan"), "lost-ish",
])
def test_unknown_stage_goes_to_ask_user_never_closed_lost(raw):
    out = normalize_stage(raw)
    assert out == OUTCOME_ASK_USER
    assert out != "closed_lost"


def test_stage_series_reports_unrecognised_values_with_counts():
    outs, ask = normalize_stage_series(["Won", "Mystery", "Mystery", "Lost", "Hold"])
    assert outs == ["closed_won", "ask_user", "ask_user", "closed_lost", "ask_user"]
    assert ask == {"Mystery": 2, "Hold": 1}


# --- refuse path -------------------------------------------------------------

def test_refuse_path_fires_on_billing_fixture_naming_what_is_missing(billing):
    r = outcome_refusal(list(billing.columns))
    assert r is not None and r["refused"] is True
    assert r["missing"] == ["outcome"]
    assert r["reason"] == "no_outcome_column"
    assert "stage" in r["message"] or "status" in r["message"]


def test_subscription_status_is_not_an_outcome_column():
    assert outcome_refusal(["Customer", "Subscription Status", "Amount"]) is not None
    assert outcome_refusal(["Invoice Status", "Amount"]) is not None


def test_no_refusal_for_crm_or_cpq(crm, cpq):
    assert outcome_refusal(list(crm.columns)) is None
    assert outcome_refusal(list(cpq.columns)) is None


def test_map_headers_refuses_before_any_llm_call(billing, monkeypatch):
    calls: list = []
    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(assist, "map_columns", lambda h: calls.append(h) or {})
    res = map_headers(list(billing.columns), llm_fallback=True, use_embeddings=False)
    assert res["refusal"]["refused"] is True
    assert res["profile"]["profile"] == "unknown"
    assert calls == []


def test_map_headers_attaches_profile_and_no_refusal_for_crm(crm):
    res = map_headers(list(crm.columns), llm_fallback=False, use_embeddings=False)
    assert res["profile"]["profile"] == "crm_opportunity"
    assert res["refusal"] is None
    assert res["mapping"]["outcome"] == "Stage"


# --- LLM payload: headers and field descriptions only ------------------------

def test_llm_payload_contains_headers_only_no_row_values(cpq, monkeypatch):
    captured: dict = {}

    def fake_complete(system, user, **kw):
        captured["system"], captured["user"] = system, user
        return "{}"

    monkeypatch.setattr(assist, "_complete", fake_complete)
    monkeypatch.setattr(assist, "has_llm", lambda: True)
    # Extra unrecognised header forces layer 4 to run on a quote-shaped file.
    df = cpq.assign(**{"Mystery Column": "SECRETVALUE-xyz"})
    map_headers(list(df.columns), llm_fallback=True, use_embeddings=False)

    assert "user" in captured, "layer 4 never ran, the test proves nothing"
    payload = json.loads(captured["user"])
    assert set(payload) == {"our_fields", "their_headers"}
    assert set(payload["their_headers"]) <= set(df.columns)
    blob = captured["system"] + captured["user"]
    for col in df.columns:
        for v in df[col].unique():
            v = str(v)
            # Row values that are not themselves a header must never appear.
            # Skip short generic tokens that collide with field descriptions.
            if len(v) >= 6 and v not in df.columns:
                assert v not in blob, f"row value {v!r} from {col!r} leaked"
    assert "SECRETVALUE-xyz" not in blob


def test_map_columns_payload_keys_and_types(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(assist, "_complete",
                        lambda s, u, **kw: captured.update(user=u) or "{}")
    assist.map_columns(["A", "B"])
    p = json.loads(captured["user"])
    assert p["their_headers"] == ["A", "B"]
    assert all(set(t) == {"field", "required", "description"} for t in p["our_fields"])


def test_mapping_targets_excludes_every_exact_only_field():
    names = {t["field"] for t in assist.mapping_targets()}
    assert EXACT_ONLY_FIELDS, "guard set must not be empty"
    assert not (names & EXACT_ONLY_FIELDS)


def test_map_columns_schema_and_result_exclude_exact_only_fields(monkeypatch):
    captured: dict = {}
    reply = json.dumps({"list_unit_rate": "Credits", "source_system": "Source"})

    def fake_complete(system, user, **kw):
        captured["schema"] = kw.get("json_schema")
        return reply

    monkeypatch.setattr(assist, "_complete", fake_complete)
    out = assist.map_columns(["Credits", "Source"])
    assert not (set(out) & EXACT_ONLY_FIELDS)
    assert not (set(captured["schema"]["properties"]) & EXACT_ONLY_FIELDS)


# --- PK-23 header probes keep their behaviour --------------------------------

@pytest.mark.parametrize("header", ["Credits", "Credits Used", "Unit Price",
                                    "Source", "Account Source", "System Source"])
def test_pk23_probe_headers_stay_unmapped(header):
    res = map_headers([header], llm_fallback=False, use_embeddings=False)
    assert all(v is None for v in res["mapping"].values())


@pytest.mark.parametrize("header,field", [
    ("List Unit Price", "list_unit_rate"), ("Service Credits Value", "credits_tcv"),
    ("Source System", "source_system"), ("Cost Basis", "cost_basis"),
])
def test_pk23_probe_headers_map_exactly(header, field):
    res = map_headers([header], llm_fallback=False, use_embeddings=False)
    assert res["mapping"][field] == header


# --- the LLM can never supply outcome ----------------------------------------

def test_llm_outcome_claim_is_dropped_when_refusal_set(monkeypatch):
    headers = ["Weird Col A", "Account Name", "Mystery Phase"]
    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(assist, "map_columns",
                        lambda h: {"outcome": "Mystery Phase",
                                   "segment": "Weird Col A"})
    res = map_headers(headers, llm_fallback=True, use_embeddings=False)
    assert res["refusal"] is not None
    assert res["mapping"]["outcome"] is None
    assert {"field": "outcome", "header": "Mystery Phase"} in res["llm_rejected"]
    # Non-outcome headers were still matched by the LLM.
    assert res["mapping"]["segment"] == "Weird Col A"
    assert "LLM" in res["refusal"]["decided_by"]
    assert "Deterministic" in res["refusal"]["decided_by"]


def test_llm_status_like_header_claim_dropped_under_refusal(monkeypatch):
    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(assist, "map_columns",
                        lambda h: {"lost_reason": "Phase Status Note"})
    res = map_headers(["Phase Status Note", "Account Name"], llm_fallback=True,
                      use_embeddings=False)
    assert res["mapping"]["lost_reason"] is None
    assert res["refusal"] is not None


# --- review rework: decisions A and B, findings 1 to 13 ----------------------

@pytest.mark.parametrize("raw", ["Declined", "Rejected", "Expired", "Cancelled",
                                 "Canceled", "Whatever"])
def test_cpq_map_sends_declined_and_friends_to_ask_user(raw):
    assert normalize_stage(raw, "cpq_line") == "ask_user"


@pytest.mark.parametrize("raw", ["Accepted", "Signed", "Won"])
def test_cpq_map_wins(raw):
    assert normalize_stage(raw, "cpq_line") == "closed_won"


def test_crm_map_keeps_closed_lost_and_lost():
    assert normalize_stage("Closed Lost") == "closed_lost"
    assert normalize_stage("Lost") == "closed_lost"


def _lines(**over):
    base = {"Quote ID": ["A", "A", "B"], "Line ID": ["1", "2", "3"],
            "Quantity": ["1", "1", "1"], "Unit Price": ["10", "20", "30"],
            "Quote Status": ["Accepted", "Accepted", "Sent"]}
    base.update(over)
    return pd.DataFrame(base)


def test_blank_nan_none_quote_ids_are_quarantined_not_grouped(tmp_path):
    f = tmp_path / "q.csv"
    f.write_text("Quote ID,Line ID,Quantity,Unit Price,Quote Status\n"
                 "A,1,1,10,Accepted\n,2,1,99,Accepted\nB,3,1,30,Sent\n,4,1,5,\n")
    for kw in ({}, {"keep_default_na": False}):
        df = pd.read_csv(f, dtype=str, **kw)
        d = rollup_quote_lines(df)
        assert sorted(d["source_quote_id"]) == ["A", "B"]
        q = d.attrs["quarantined_lines"]
        assert len(q) == 2 and set(q["Line ID"]) == {"2", "4"}
        assert d.attrs["quarantined_reason"]
    df = _lines(**{"Quote ID": ["A", None, float("nan")]})
    d = rollup_quote_lines(df)
    assert list(d["source_quote_id"]) == ["A"]
    assert len(d.attrs["quarantined_lines"]) == 2


def test_nan_and_none_status_beside_a_real_one_is_ask_user_without_typeerror():
    df = _lines(**{"Quote Status": ["Accepted", None, float("nan")]})
    d = rollup_quote_lines(df).set_index("source_quote_id")
    assert d.loc["A", "outcome"] == "ask_user"
    assert d.loc["B", "outcome"] == "ask_user"
    assert d.attrs["ask_user"]["A"] == ["", "Accepted"]
    outs, ask = normalize_stage_series(["Won", float("nan"), None, "Won"])
    assert outs.count("ask_user") == 2 and ask == {"": 2}


def test_line_amounts_use_parse_money():
    df = pd.DataFrame({"Quote ID": ["A", "A", "B"], "Line ID": ["1", "2", "3"],
                       "Line Total": ["(100)", "$250", "1.234,50"],
                       "Quote Status": ["Accepted"] * 3})
    d = rollup_quote_lines(df).set_index("source_quote_id")
    assert d.loc["A", "booked_acv"] == 150          # -100 + 250
    assert d.loc["B", "booked_acv"] == pytest.approx(1234.50)


def test_quote_id_role_never_lands_on_a_line_header():
    h = ["Quote Line ID", "Quote ID", "Quantity", "Unit Price", "Quote Status"]
    p = profile_source(h)
    assert p["roles"]["quote_id"] == "Quote ID"
    assert p["roles"]["line"] == "Quote Line ID"
    assert profile_source(["Quote Line ID", "Quote Number", "Quantity",
                           "Unit Price"])["roles"]["quote_id"] == "Quote Number"
    only_line = profile_source(["Quote Line ID", "Quantity", "Unit Price"])
    assert "quote_id" not in only_line["roles"]


@pytest.mark.parametrize("headers", [
    ["id", "customer", "subscription", "status", "amount_due", "period_start",
     "period_end"],                                   # Stripe invoices
    ["Subscription ID", "Customer", "Status", "Plan", "Current Period Start",
     "Quantity", "Created"],                          # Stripe subscriptions
    ["Subscription Id", "Customer Id", "Plan Id", "Billing Period", "Status",
     "MRR", "Currency"],                              # Chargebee style
])
def test_billing_fingerprint_makes_bare_status_a_billing_state(headers):
    p = profile_source(headers)
    assert p["billing_fingerprint"] is True
    assert "outcome" not in p["roles"]
    r = outcome_refusal(headers)
    assert r is not None and r["missing"] == ["outcome"]
    res = map_headers(headers, llm_fallback=False, use_embeddings=False)
    assert res["mapping"]["outcome"] is None
    assert res["refusal"] is not None


def test_bare_status_still_outcome_without_billing_fingerprint():
    res = map_headers(["Opportunity ID", "Status", "Close Date", "Amount"],
                      llm_fallback=False, use_embeddings=False)
    assert res["mapping"]["outcome"] == "Status" and res["refusal"] is None


def test_colon_separated_headers_profile_correctly():
    p = profile_source(["Opportunity: Opportunity ID", "Opportunity: Stage",
                        "Opportunity: Close Date", "Opportunity: Amount"])
    assert p["profile"] == "crm_opportunity"
    q = profile_source(["Quote: Quote ID", "Quote: Line ID", "Quote: Quantity",
                        "Quote: Unit Price", "Quote: Status"])
    assert q["profile"] == "cpq_line"
    assert q["roles"]["quote_status"] == "Quote: Status"


def test_refusal_never_returned_beside_a_deterministic_outcome_claim(monkeypatch):
    monkeypatch.setattr(mapping, "embedding_match",
                        lambda h, notes=None: ("outcome", 0.9)
                        if h == "Phase Thing" else None)
    res = map_headers(["Account Name", "Phase Thing"], llm_fallback=False,
                      use_embeddings=True)
    assert res["mapping"]["outcome"] == "Phase Thing"
    assert res["refusal"] is None


def test_embedding_cannot_promote_a_billing_state_header(monkeypatch):
    monkeypatch.setattr(mapping, "embedding_match",
                        lambda h, notes=None: ("outcome", 0.9)
                        if h == "Subscription Status" else None)
    res = map_headers(["Subscription ID", "Plan", "Subscription Status"],
                      llm_fallback=False, use_embeddings=True)
    assert res["mapping"]["outcome"] is None and res["refusal"] is not None


def test_llm_outcome_claim_rejected_on_nonrefused_cpq_file(cpq, monkeypatch):
    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(assist, "map_columns",
                        lambda h: {"outcome": "Mystery Column"})
    df = cpq.assign(**{"Mystery Column": "x"})
    res = map_headers(list(df.columns), llm_fallback=True, use_embeddings=False)
    assert res["refusal"] is None
    assert res["mapping"]["outcome"] == "Quote Status"
    assert res["used"]["Quote Status"] == "profile"
    assert {"field": "outcome", "header": "Mystery Column"} in res["llm_rejected"]


def test_unpriced_lines_counted_and_opportunity_id_never_filled():
    df = _lines(**{"Unit Price": ["10", "n/a", "30"]})
    d = rollup_quote_lines(df).set_index("source_quote_id")
    assert d.loc["A", "unpriced_lines"] == 1 and d.loc["B", "unpriced_lines"] == 0
    assert d.attrs["unpriced_lines"] == {"A": 1}
    assert d.attrs["opportunity_id_present"] is False
    assert d["opportunity_id"].isna().all()
    assert (d["source_system"] == "cpq").all()
    with_opp = rollup_quote_lines(_lines(**{"Opportunity ID": ["O1", "O1", "O2"]}))
    assert with_opp.attrs["opportunity_id_present"] is True
    assert set(with_opp["opportunity_id"]) == {"O1", "O2"}


# --- second rework: billing fingerprint false positives, items 1 to 6 --------

_CRM_BASE = ["Opportunity ID", "Account Name", "Stage", "Amount", "Close Date",
             "Segment", "Value Metric"]


@pytest.mark.parametrize("extra", [
    ["Customer ID", "Fiscal Period"],
    ["Subscription Term", "Fiscal Period"],
    ["Subscription Value", "Plan"],
    ["Customer Number", "Billing Interval"],
    ["Subscription ID", "Plan", "Billing Interval", "Fiscal Period"],
])
def test_crm_headers_with_billing_looking_columns_keep_stage(extra):
    headers = _CRM_BASE + extra
    res = map_headers(headers, llm_fallback=False, use_embeddings=False)
    assert res["mapping"]["outcome"] == "Stage"
    assert res["refusal"] is None
    assert res["profile"]["profile"] == "crm_opportunity"
    assert res["profile"]["billing_fingerprint"] is False


def test_hubspot_style_deals_export_keeps_deal_stage():
    h = ["Record ID", "Deal Name", "Deal Stage", "Plan", "Customer ID",
         "Amount", "Close Date"]
    res = map_headers(h, llm_fallback=False, use_embeddings=False)
    assert res["mapping"]["outcome"] == "Deal Stage"
    assert res["refusal"] is None


def test_stage_or_outcome_header_is_never_blocked():
    from pricing.mapping import _blocked_outcome_headers
    assert _blocked_outcome_headers(["Subscription Stage", "Renewal Outcome"],
                                    True) == []
    assert _blocked_outcome_headers(["Subscription Status", "Status"],
                                    True) == ["Subscription Status", "Status"]


def test_crm_csv_with_fiscal_period_plan_customer_id_loads_every_row(tmp_path):
    from pricing.ingest import ingest_verbose
    n = 60
    df = pd.DataFrame({
        "Opportunity ID": [f"O{i}" for i in range(n)],
        "Account Name": [f"Acct {i % 20}" for i in range(n)],
        "Stage": ["Closed Won" if i % 3 else "Closed Lost" for i in range(n)],
        "Created Date": ["2025-01-05"] * n,
        "Close Date": ["2025-03-10"] * n,
        "Segment": ["SMB", "MidMarket", "Enterprise"] * 20,
        "Plan": ["Pro", "Team", "Enterprise"] * 20,
        "Value Metric": ["seats"] * n,
        "List ACV": [100000] * n,
        "Amount": [80000 + i * 100 for i in range(n)],
        "Fiscal Period": ["FY25 Q1"] * n,
        "Customer ID": [f"C{i % 20}" for i in range(n)],
    })
    f = tmp_path / "crm.csv"
    df.to_csv(f, index=False)
    out, report = ingest_verbose(str(f))
    assert len(out) == n
    assert report.rows_kept == n


def test_quote_export_with_only_approval_status_is_refused():
    h = ["Quote ID", "Line ID", "Quantity", "Unit Price", "Quote Approval Status"]
    p = profile_source(h)
    assert p["profile"] == "cpq_line"
    assert "quote_status" not in p["roles"] and "outcome" not in p["roles"]
    r = outcome_refusal(h)
    assert r is not None and "Quote Approval Status" in r["blocked_headers"]
    res = map_headers(h, llm_fallback=False, use_embeddings=False)
    assert res["mapping"]["outcome"] is None and res["refusal"] is not None


@pytest.mark.parametrize("h", ["Payment Status", "Delivery Status", "Sync Status",
                               "Review Status", "Quote Review Status"])
def test_non_outcome_qualified_status_never_gets_the_outcome_role(h):
    p = profile_source(["Quote ID", "Line ID", "Quantity", "Unit Price", h])
    assert "outcome" not in p["roles"] and "quote_status" not in p["roles"]


def test_all_quote_ids_quarantined_returns_full_column_set_zero_rows():
    df = _lines(**{"Quote ID": [None, "", float("nan")]})
    d = rollup_quote_lines(df)
    ok = rollup_quote_lines(_lines())
    assert len(d) == 0
    assert list(d.columns) == list(ok.columns)
    assert len(d.attrs["quarantined_lines"]) == 3
    assert d.attrs["quarantined_reason"]


def test_quantity_accepts_thousands_separators():
    df = pd.DataFrame({"Quote ID": ["A", "A"], "Line ID": ["1", "2"],
                       "Quantity": ["1,000", "2"], "Unit Price": ["2", "3"],
                       "Quote Status": ["Accepted", "Accepted"]})
    d = rollup_quote_lines(df)
    assert d.loc[0, "booked_acv"] == 1000 * 2 + 2 * 3
    assert d.loc[0, "unpriced_lines"] == 0


def test_outcome_is_not_offered_to_the_llm_and_a_reply_naming_it_is_rejected(
        monkeypatch):
    monkeypatch.setattr(assist, "has_llm", lambda: True)
    seen = {}

    def fake(h):
        seen["h"] = h
        return {"outcome": "Mystery Col", "segment": "Other Col"}

    monkeypatch.setattr(assist, "map_columns", fake)
    res = map_headers(["Account Name", "Mystery Col", "Other Col"],
                      llm_fallback=True, use_embeddings=False)
    assert res["mapping"]["outcome"] is None
    assert {"field": "outcome", "header": "Mystery Col"} in res["llm_rejected"]
    assert res["mapping"]["segment"] == "Other Col"


@pytest.mark.parametrize("value", ["paid", "open", "void", "uncollectible",
                                   "draft", "active", "canceled", "past_due"])
def test_billing_status_values_all_map_to_ask_user(value):
    assert normalize_stage(value, "billing") == "ask_user"


def test_invoice_header_set_is_refused_and_never_a_deal_outcome():
    h = ["Invoice Number", "Customer", "Amount Due", "Status"]
    p = profile_source(h)
    assert p["billing_fingerprint"] is True and p["profile"] == "unknown"
    res = map_headers(h, llm_fallback=False, use_embeddings=False)
    assert res["mapping"]["outcome"] is None
    assert res["refusal"]["blocked_headers"] == ["Status"]


@pytest.mark.parametrize("date_col", ["Close Date", "Closed At"])
def test_chargebee_with_a_close_date_is_still_billing(date_col):
    h = ["Subscription Id", "Customer Id", "Plan Id", "Plan Quantity", "Status",
         "Created At", date_col, "MRR"]
    p = profile_source(h)
    assert p["billing_fingerprint"] is True
    assert "outcome" not in p["roles"]
    res = map_headers(h, llm_fallback=False, use_embeddings=False)
    assert res["mapping"]["outcome"] is None
    assert res["refusal"]["blocked_headers"] == ["Status"]


def test_normalize_stage_takes_a_value_map_name():
    import inspect
    assert "value_map" in inspect.signature(normalize_stage).parameters
    assert normalize_stage("Accepted", value_map="cpq_line") == "closed_won"
    assert normalize_stage("paid", value_map="billing") == "ask_user"
