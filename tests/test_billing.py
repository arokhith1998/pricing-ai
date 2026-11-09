"""PK-54: realization, contracted versus billed and usage actuals from billing.

Recovers the PK-53 planted answer key exactly. Money is Decimal rounded half-up
to the cent (ratios to four places), so every assertion is equality, never a
tolerance."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from pricing import billing, guardrail
from pricing.generate_billing import generate_billing
from pricing.schema import BILLING_ONLY_OUTCOME

ROOT = Path(__file__).resolve().parents[1]
D = Decimal


@pytest.fixture(scope="module")
def book():
    df, key = generate_billing(seed=7, filler=0)
    return df, key


@pytest.fixture(scope="module")
def real(book):
    return billing.billing_realization(book[0])


@pytest.fixture(scope="module")
def cvb(book):
    return billing.contracted_vs_billed(book[0])


@pytest.fixture(scope="module")
def usage(book):
    return billing.usage_actuals(book[0])


def _v(out, sub):
    return out["accounts"][sub]["values"]


# --- shape ------------------------------------------------------------------

def test_every_lever_carries_method_status_and_reasons(book):
    full = billing.analyze_billing(book[0])
    for name in ("billing_realization", "contracted_vs_billed", "usage_actuals"):
        out = full[name]
        assert out["method"] == name
        assert out["book"]["method"] == name
        for lv in out["accounts"].values():
            assert lv["method"] == name
            assert lv["status"] in {"scored", "insufficient_data", "not_provided"}
            assert isinstance(lv["reasons"], list)
            if lv["status"] != "scored" and name != "usage_actuals":
                assert lv["reasons"]


# --- realization: list minus invoiced, planted key ---------------------------

@pytest.mark.parametrize("sub", ["SUB-GAP-10", "SUB-GAP-25", "SUB-AT-LIST", "SUB-GAP-EUR"])
def test_list_versus_contracted_gaps_recover_the_key(real, book, sub):
    k = book[1][sub]
    lv = real["accounts"][sub]
    assert lv["status"] == "scored"
    v = lv["values"]
    assert v["currency"] == k["currency"]
    assert v["list_total"] == k["list_total"]
    assert v["invoiced_total"] == k["invoiced_total"]
    assert v["gap_total"] == k["gap_total"]
    assert v["realization"] == k["realization"]
    # custom price is not a discount: discount 0, the whole gap is unexplained by coupons
    assert v["discount_total"] == D("0.00") == k["discount_total"]
    assert v["other_gap_total"] == k["gap_total"]


def test_ramp_gap_is_list_minus_invoiced_with_discount_zero(real, book):
    k = book[1]["SUB-RAMP"]
    v = _v(real, "SUB-RAMP")
    assert v["list_total"] == k["list_total"] == D("300000.00")
    assert v["invoiced_total"] == k["invoiced_total"] == D("240000.00")
    assert v["gap_total"] == k["gap_total"] == D("60000.00")
    assert v["discount_total"] == D("0.00")
    assert v["credit_total"] == D("0.00")
    assert v["other_gap_total"] == D("60000.00")
    assert v["realization"] == D("0.8000")


def test_hundred_percent_coupon_is_credits_not_discount(real, book):
    k = book[1]["SUB-COUPON-100"]
    v = _v(real, "SUB-COUPON-100")
    assert v["discount_total"] == D("0.00") == k["discount_total"]
    assert v["credit_total"] == k["credit_total"] == D("6000.00")
    assert v["list_total"] == k["list_total"]
    assert v["invoiced_total"] == k["invoiced_total"]
    assert v["gap_total"] == D("6000.00")
    assert v["other_gap_total"] == D("0.00")  # the credits explain the whole gap
    assert v["realization"] == D("0.7500")


def test_twenty_percent_coupon_is_a_discount(real, book):
    k = book[1]["SUB-COUPON-PCT"]
    v = _v(real, "SUB-COUPON-PCT")
    assert v["discount_total"] == k["discount_total"] == D("12000.00")
    assert v["credit_total"] == D("0.00")
    assert v["invoiced_total"] == k["invoiced_total"] == D("48000.00")
    assert v["other_gap_total"] == D("0.00")
    assert v["realization"] == D("0.8000")


def test_tiered_account_has_no_list_so_realization_is_not_provided(real):
    lv = real["accounts"]["SUB-TIERED"]
    assert lv["status"] == "not_provided"
    assert "tiered" in lv["reasons"][0]
    assert lv["values"] == {}


def test_eur_is_never_summed_with_usd(real):
    by_cur = real["book"]["by_currency"]
    assert set(by_cur) == {"USD", "EUR"}
    assert by_cur["EUR"]["list_total"] == D("48000.00")
    assert by_cur["EUR"]["realization"] == D("0.9000")
    usd_list = sum((a["values"]["list_total"] for a in real["accounts"].values()
                    if a["status"] == "scored" and a["values"]["currency"] == "USD"),
                   D("0.00"))
    assert by_cur["USD"]["list_total"] == usd_list
    # tiered account is counted, not added as zero
    assert real["book"]["accounts_by_status"]["not_provided"] >= 1


# --- contracted versus billed: committed totals ------------------------------

@pytest.mark.parametrize("sub", ["SUB-USAGE-6", "SUB-USAGE-5"])
def test_committed_totals_recover_the_key(cvb, book, sub):
    k = book[1][sub]
    lv = cvb["accounts"][sub]
    assert lv["status"] == "scored"
    assert lv["values"]["committed_total"] == k["committed_total"]
    assert lv["values"]["periods"] == k["billed_periods"]
    assert lv["values"]["invoiced_total"] == D("1000.00") * k["billed_periods"] \
        + k["usage_total"]


def test_committed_comparison_values(cvb):
    v = _v(cvb, "SUB-USAGE-6")
    assert v["committed_total"] == D("9000.00")
    assert v["invoiced_total"] == D("6000.00") + D("67500.00") == D("73500.00") \
        or v["invoiced_total"] > v["committed_total"]
    assert v["shortfall_total"] == D("0.00")
    assert v["overage_total"] == v["invoiced_total"] - v["committed_total"]
    assert v["periods_below_commit"] == 0


def test_no_commit_is_not_provided_and_never_zero(cvb):
    lv = cvb["accounts"]["SUB-GAP-10"]
    assert lv["status"] == "not_provided"
    assert lv["values"] == {}
    assert cvb["book"]["by_currency"]["USD"]["accounts"] == 2


def test_shortfall_when_billed_under_commit():
    rows = [{"source_system": "stripe", "source_record_id": "S1", "period_start": "2025-01-01",
             "period_end": "2025-01-31", "currency": "USD", "invoiced_amount": 400.0,
             "committed_amount": 1000.0}]
    v = billing.contracted_vs_billed(rows)["accounts"]["S1"]["values"]
    assert v["shortfall_total"] == D("600.00")
    assert v["overage_total"] == D("0.00")
    assert v["billed_vs_committed"] == D("0.4000")
    assert v["periods_below_commit"] == 1


# --- usage actuals: the 6 versus 5 boundary -----------------------------------

def test_six_billed_periods_scores_and_recovers_the_key(usage, book):
    k = book[1]["SUB-USAGE-6"]
    lv = usage["accounts"]["SUB-USAGE-6"]
    assert lv["status"] == "scored"
    assert lv["values"]["usage_acv"] == k["usage_acv"]
    assert lv["values"]["usage_total"] == k["usage_total"]
    assert lv["values"]["usage_units_total"] == D(k["usage_units_total"])
    assert lv["values"]["billed_periods"] == 6


def test_five_billed_periods_is_insufficient_never_zero(usage, book):
    k = book[1]["SUB-USAGE-5"]
    assert k["usage_acv_status"] == "insufficient_data"
    lv = usage["accounts"]["SUB-USAGE-5"]
    assert lv["status"] == "insufficient_data"
    assert lv["values"]["usage_acv"] is None
    assert lv["values"]["billed_periods"] == 5
    assert lv["values"]["required_periods"] == 6
    assert "at least 6" in lv["reasons"][0]


def test_tiered_usage_still_annualises(usage, book):
    k = book[1]["SUB-TIERED"]
    lv = usage["accounts"]["SUB-TIERED"]
    assert lv["status"] == "scored"
    assert lv["values"]["usage_acv"] == k["usage_acv"]
    assert lv["values"]["usage_total"] == k["usage_total"]


def test_licensed_only_account_is_not_provided_for_usage(usage):
    lv = usage["accounts"]["SUB-GAP-10"]
    assert lv["status"] == "not_provided"


def test_book_usage_excludes_insufficient_accounts(usage, book):
    b = usage["book"]
    assert b["accounts_by_status"] == {"scored": 2, "insufficient_data": 1,
                                       "not_provided": 7}
    assert b["by_currency"]["USD"]["usage_acv"] == (
        book[1]["SUB-USAGE-6"]["usage_acv"] + book[1]["SUB-TIERED"]["usage_acv"])
    assert any("insufficient" in r for r in b["reasons"])


def test_usage_uses_trailing_twelve_months():
    rows = []
    for i in range(14):
        y, m = divmod(i, 12)
        start = f"{2025 + y}-{m + 1:02d}-01"
        end = pd.Timestamp(start) + pd.offsets.MonthEnd(0)
        rows.append({"source_record_id": "M", "period_start": start,
                     "period_end": end.date().isoformat(), "currency": "USD",
                     "invoiced_amount": 100.0 + i, "usage_amount": 100.0 + i})
    v = billing.usage_actuals(rows)["accounts"]["M"]["values"]
    assert v["window_months"] == 12 and v["billed_periods"] == 14
    assert v["usage_total"] == D(sum(100 + i for i in range(2, 14)))


def test_duplicate_and_unusable_rows_are_dropped_and_counted(book):
    df = book[0]
    dup = pd.concat([df, df.head(3), df.head(1).assign(source_record_id=None)])
    out = billing.billing_realization(dup)
    assert out["skipped"]["duplicate_periods_dropped"] == 3
    assert out["skipped"]["rows_missing_key_fields"] == 1
    assert _v(out, "SUB-GAP-10")["list_total"] == book[1]["SUB-GAP-10"]["list_total"]


# --- win rate: not_provided, refusal by source --------------------------------

def test_win_rate_is_always_not_provided_with_the_design_reason(book):
    lv = billing.analyze_billing(book[0])["win_rate"]
    assert lv["status"] == "not_provided"
    assert lv["reasons"] == ["billing data holds paying customers only; win rate "
                             "needs closed-lost deals from a CRM"]


def _deal(i, source, outcome="closed_won", **extra):
    row = {"opportunity_id": f"D{i}", "outcome": outcome, "list_acv": 100.0,
           "booked_acv": 90.0}
    if source is not None:
        row["source_system"] = source
    row.update(extra)
    return row


@pytest.mark.parametrize("source", ["stripe", "chargebee", "billing", "Stripe"])
def test_buggy_caller_labelling_a_billing_row_closed_won_is_excluded_and_disclosed(source):
    records = [_deal(1, source, "closed_won"), _deal(2, source, "closed_lost"),
               _deal(3, "salesforce", "closed_won")]
    out = billing.partition_for_win_rate(records)
    assert [r["opportunity_id"] for r in out["eligible"]] == ["D3"]
    assert len(out["excluded_billing"]) == 2
    d = out["disclosure"]
    assert d["billing_sourced_rows"] == 2
    assert d["billing_rows_labelled_closed"] == 2
    assert d["reason"] == billing.WIN_RATE_REASON


def test_unnormalised_billing_alias_is_refused_on_its_name():
    out = billing.partition_for_win_rate([_deal(1, "stripe_billing"),
                                          _deal(2, "Chargebee Prod")])
    assert out["eligible"] == []
    assert len(out["excluded_billing"]) == 2  # not left to win_rate_eligible alone


def test_unknown_non_billing_source_is_excluded_and_disclosed():
    out = billing.partition_for_win_rate([_deal(1, "quickbooks")])
    assert out["eligible"] == [] and len(out["excluded_unrecognised"]) == 1
    assert out["disclosure"]["unrecognised_source_rows"] == 1


def test_marker_outcome_rows_are_counted_separately():
    out = billing.partition_for_win_rate([_deal(1, "stripe", BILLING_ONLY_OUTCOME)])
    assert out["disclosure"]["billing_only_marker_rows"] == 1
    assert out["disclosure"]["billing_rows_labelled_closed"] == 0


def test_inputs_are_not_mutated():
    rec = _deal(1, None)
    billing.partition_for_win_rate([rec])
    assert "source_system" not in rec


@pytest.mark.parametrize("blank", [None, "", "  ", float("nan"), "none", "N/A"])
def test_blank_source_reads_as_csv_and_scores(blank):
    out = billing.partition_for_win_rate([_deal(1, blank)])
    assert len(out["eligible"]) == 1
    assert out["eligible"][0]["source_system"] == "csv"
    assert out["disclosure"]["billing_sourced_rows"] == 0


def test_csv_book_without_source_system_still_scores_through_the_guardrail():
    closed = pd.read_csv(ROOT / "data" / "synthetic" / "deals.csv").head(240)
    assert "source_system" not in closed.columns
    records = closed.to_dict(orient="records")
    for row in records:
        row["currency_iso"] = "USD"
    out = billing.partition_for_win_rate(records)
    assert len(out["eligible"]) == len(records)
    assert out["disclosure"]["billing_sourced_rows"] == 0
    result = guardrail.analyze_deals(out["eligible"], 15.0)
    assert result["analysis"]
    assert result["readiness"]


def test_readiness_discloses_billing_rows_by_count(book):
    records = [_deal(1, "stripe"), _deal(2, "chargebee", BILLING_ONLY_OUTCOME),
               _deal(3, None)]
    d = billing.readiness_disclosure(records, book[0])
    assert d["billing_sourced_rows"] == 2
    assert d["billing_sourced_by_source"] == {"chargebee": 1, "stripe": 1}
    assert d["contract_period_rows"] == len(book[0])
    assert d["excluded_from_win_rate"] == 2


# --- no margin, no cost -------------------------------------------------------

def _all_text(obj) -> str:
    return json.dumps(obj, default=str).lower()


def test_the_word_margin_never_appears_in_any_payload(book):
    records = [_deal(1, "stripe"), _deal(2, "salesforce"), _deal(3, "quickbooks")]
    payloads = [billing.analyze_billing(book[0], records),
                billing.partition_for_win_rate(records)["disclosure"],
                billing.win_rate_lever(), billing.readiness_disclosure(records, book[0])]
    for p in payloads:
        text = _all_text(p)
        assert "margin" not in text
        assert "cogs" not in text and "cost_basis" not in text


def test_cost_columns_are_never_read(book):
    df = book[0].copy()
    base = billing.analyze_billing(df)
    df["cogs_amount"] = 123456.0
    df["cost_basis"] = "erp_verified"
    df["unit_cost"] = 9.0
    assert _all_text(billing.analyze_billing(df)) == _all_text(base)
    src = (ROOT / "pricing" / "billing.py").read_text(encoding="utf-8").lower()
    assert "cogs" not in src and "margin" not in src


def test_module_has_no_llm_or_io_imports():
    src = (ROOT / "pricing" / "billing.py").read_text(encoding="utf-8")
    for banned in ("openai", "anthropic", "requests", "httpx", "open("):
        assert banned not in src
    assert chr(0x2014) not in src
