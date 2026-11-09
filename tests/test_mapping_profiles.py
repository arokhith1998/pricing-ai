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


def test_profile_reads_headers_only(crm):
    """Same headers, wildly different values: identical profile."""
    other = crm.copy()
    other["Stage"] = "zzz"
    assert profile_source(list(crm.columns)) == profile_source(list(other.columns))


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
    assert deals.loc["Q-2002", "outcome"] == "closed_lost"
    assert deals.loc["Q-2004", "outcome"] == "open"
    assert set(deals["outcome"]) <= set(OUTCOME_VALUES)


def test_rollup_expired_quote_is_ask_user_not_lost(cpq):
    deals = rollup_quote_lines(cpq).set_index("source_quote_id")
    assert deals.loc["Q-2006", "outcome"] == "ask_user"
    assert deals.attrs["ask_user"] == {"Q-2006": ["Expired"]}


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
    ("Closed Lost", "closed_lost"), ("Declined", "closed_lost"),
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
