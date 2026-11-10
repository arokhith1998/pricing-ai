"""PK-54: realization, contracted versus billed and usage actuals from billing.

Recovers the PK-53 planted answer key exactly. Money is Decimal rounded half-up
to the cent (ratios to four places), so every assertion is equality, never a
tolerance."""
from __future__ import annotations

import json
from datetime import date, timedelta
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
    assert v["invoiced_total"] == D("73500.00")
    assert v["shortfall_total"] == D("0.00")
    assert v["overage_total"] == D("64500.00")
    assert v["net_vs_commit"] == D("64500.00")
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


# --- PK-54 rework: review findings pinned -------------------------------------

def _row(acct="A", start="2025-01-01", end="2025-01-31", inv=100.0, **extra):
    r = {"source_system": "stripe", "source_record_id": acct, "period_start": start,
         "period_end": end, "currency": "USD", "invoiced_amount": inv}
    r.update(extra)
    return r


def test_finding1_shortfall_and_overage_are_per_period_never_netted():
    rows = [_row(start="2025-01-01", end="2025-01-31", inv=1500.0, committed_amount=1000.0),
            _row(start="2025-02-01", end="2025-02-28", inv=600.0, committed_amount=1000.0),
            _row(start="2025-03-01", end="2025-03-31", inv=800.0, committed_amount=1000.0)]
    v = billing.contracted_vs_billed(rows)["accounts"]["A"]["values"]
    assert v["overage_total"] == D("500.00")
    assert v["shortfall_total"] == D("600.00")
    assert v["net_vs_commit"] == D("-100.00")
    assert v["periods_below_commit"] == 2
    book = billing.contracted_vs_billed(rows)["book"]["by_currency"]["USD"]
    assert book["shortfall_total"] == D("600.00") and book["overage_total"] == D("500.00")


def test_finding2_weekly_periods_are_not_rounded_up_to_a_month():
    rows = [_row(start=f"2025-01-{1 + 7 * i:02d}", end=f"2025-01-{7 + 7 * i:02d}",
                 inv=100.0, usage_amount=100.0) for i in range(4)]
    rows += [_row(start="2025-01-29", end="2025-02-04", inv=100.0, usage_amount=100.0),
             _row(start="2025-02-05", end="2025-02-11", inv=100.0, usage_amount=100.0)]
    lv = billing.usage_actuals(rows)["accounts"]["A"]
    assert lv["status"] == "not_provided"
    assert lv["values"]["usage_acv"] is None
    assert "not whole calendar months" in lv["reasons"][0]
    assert "1200" not in json.dumps(lv, default=str)


def test_finding2_prorated_stub_is_left_out_not_rounded_to_a_month():
    rows = []
    for i in range(6):
        rows.append(_row(start=f"2025-{i + 1:02d}-01",
                         end=pd.Timestamp(f"2025-{i + 1:02d}-01").to_period("M")
                         .end_time.date().isoformat(), inv=100.0, usage_amount=100.0))
    rows.append(_row(start="2025-07-01", end="2025-07-10", inv=50.0, usage_amount=50.0))
    lv = billing.usage_actuals(rows)["accounts"]["A"]
    assert lv["status"] == "scored"
    assert lv["values"]["window_months"] == 6
    assert lv["values"]["usage_total"] == D("600.00")
    assert lv["values"]["usage_acv"] == D("1200.00")
    assert "1 period(s) are not whole calendar months" in lv["reasons"][0]


def test_finding2_mid_month_anchored_months_still_annualise():
    rows = [_row(start=f"2025-{i:02d}-15", end=f"2025-{i + 1:02d}-14", inv=10.0,
                 usage_amount=10.0) for i in range(1, 7)]
    v = billing.usage_actuals(rows)["accounts"]["A"]["values"]
    assert v["window_months"] == 6 and v["usage_acv"] == D("120.00")


def test_finding3_identical_duplicates_collapse():
    r = _row(list_amount=200.0, discount_amount=0.0, credit_amount=0.0)
    out = billing.billing_realization([r, dict(r), dict(r)])
    assert out["skipped"]["duplicate_periods_dropped"] == 2
    assert out["skipped"]["conflicting_period_rows"] == 0
    assert _v(out, "A")["list_total"] == D("200.00")


def test_finding3_differing_duplicate_is_a_conflict_not_first_row_wins():
    rows = [_row(inv=100.0, list_amount=200.0, discount_amount=0.0, credit_amount=0.0),
            _row(inv=150.0, list_amount=200.0, discount_amount=0.0, credit_amount=0.0),
            _row(start="2025-02-01", end="2025-02-28", inv=100.0, list_amount=200.0,
                 discount_amount=0.0, credit_amount=0.0)]
    out = billing.billing_realization(rows)
    lv = out["accounts"]["A"]
    assert lv["values"]["periods"] == 1  # only February survives
    assert lv["values"]["invoiced_total"] == D("100.00")
    assert lv["data_quality"]["conflict_rows_excluded"] == 2
    assert "disagree on amounts" in lv["data_quality"]["conflict_reasons"][0]
    assert any("2 period row(s) in conflict" in r for r in lv["reasons"])
    assert out["skipped"]["conflicting_period_rows"] == 2
    assert out["skipped"]["accounts_with_conflicts"] == 1


def test_finding3_overlapping_periods_are_conflicts_not_double_counted():
    rows = [_row(start="2025-03-01", end="2025-03-15", inv=50.0, usage_amount=50.0,
                 committed_amount=100.0),
            _row(start="2025-03-01", end="2025-03-31", inv=100.0, usage_amount=100.0,
                 committed_amount=100.0)]
    out = billing.contracted_vs_billed(rows)
    lv = out["accounts"]["A"]
    assert lv["status"] == "not_provided"  # nothing left after the conflict
    assert lv["data_quality"]["conflict_rows_excluded"] == 2
    assert "overlap" in lv["data_quality"]["conflict_reasons"][0]
    assert out["skipped"]["conflicting_period_rows"] == 2


def test_finding3_adjacent_periods_are_not_overlaps():
    rows = [_row(start="2025-01-01", end="2025-01-31"),
            _row(start="2025-02-01", end="2025-02-28")]
    out = billing.billing_realization(rows)
    assert out["skipped"]["conflicting_period_rows"] == 0


def test_finding4_absent_discount_and_credit_columns_are_not_in_the_file():
    rows = [_row(inv=80.0, list_amount=100.0)]
    lv = billing.billing_realization(rows)["accounts"]["A"]
    v = lv["values"]
    assert v["discount_total"] is None and v["credit_total"] is None
    assert v["other_gap_total"] is None
    assert v["realization"] == D("0.8000") and v["gap_total"] == D("20.00")
    assert any("discount_amount column is not in the file" in r for r in lv["reasons"])
    assert any("credit_amount column is not in the file" in r for r in lv["reasons"])
    book = billing.billing_realization(rows)["book"]["by_currency"]["USD"]
    assert book["other_gap_total"] is None
    assert book["other_gap_total_accounts_missing"] == 1


def test_finding4_blank_cells_in_a_present_column_are_excluded_per_row_with_a_count():
    rows = [_row(start="2025-01-01", end="2025-01-31", inv=80.0, list_amount=100.0,
                 discount_amount=20.0, credit_amount=0.0),
            _row(start="2025-02-01", end="2025-02-28", inv=80.0, list_amount=100.0,
                 discount_amount=None, credit_amount=0.0)]
    lv = billing.billing_realization(rows)["accounts"]["A"]
    v = lv["values"]
    assert v["discount_total"] == D("20.00") and v["discount_blank_rows"] == 1
    assert v["credit_total"] == D("0.00") and v["credit_blank_rows"] == 0
    assert v["other_gap_total"] == D("0.00")  # only January is explained, and fully
    assert v["realization"] == D("0.8000")
    assert any("1 period(s) have a blank discount_amount" in r for r in lv["reasons"])


def test_finding5_refund_row_is_invalid_and_never_scored_negative():
    rows = [_row(start="2025-01-01", end="2025-01-31", inv=-20.0, list_amount=100.0,
                 discount_amount=0.0, credit_amount=0.0),
            _row(start="2025-02-01", end="2025-02-28", inv=90.0, list_amount=100.0,
                 discount_amount=0.0, credit_amount=0.0)]
    out = billing.billing_realization(rows)
    v = _v(out, "A")
    assert v["realization"] == D("0.9000")
    assert v["invalid_money_value_rows"] == 1
    assert out["skipped"]["invalid_money_value_rows"] == 1
    assert any("invalid_money_value" in r for r in out["accounts"]["A"]["reasons"])


def test_finding5_list_below_invoiced_plus_discount_plus_credit_is_invalid():
    rows = [_row(inv=90.0, list_amount=100.0, discount_amount=10.0, credit_amount=5.0)]
    lv = billing.billing_realization(rows)["accounts"]["A"]
    assert lv["status"] == "not_provided"
    assert lv["values"] == {"invalid_money_value_rows": 1}
    assert "invalid_money_value" in lv["reasons"][0]


def test_finding5_boundary_list_equal_to_the_sum_is_valid():
    rows = [_row(inv=85.0, list_amount=100.0, discount_amount=10.0, credit_amount=5.0)]
    v = billing.billing_realization(rows)["accounts"]["A"]["values"]
    assert v["invalid_money_value_rows"] == 0 and v["realization"] == D("0.8500")


def test_finding6_usage_column_absent_says_the_column_is_not_in_the_file():
    lv = billing.usage_actuals([_row()])["accounts"]["A"]
    assert lv["status"] == "not_provided"
    assert lv["reasons"] == ["usage_amount column is not in the file"]


def test_usage_column_present_but_blank_is_a_different_reason():
    lv = billing.usage_actuals([_row(usage_amount=None)])["accounts"]["A"]
    assert lv["status"] == "not_provided"
    assert "blank on every period" in lv["reasons"][0]


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


# --- PK-54 re-review ----------------------------------------------------------

def _billed_on(day, months, year=2025, first=1):
    """Monthly periods for a subscription billed on `day`, clamped to month length."""
    import calendar
    out = []
    for i in range(months):
        y, m = divmod(first - 1 + i, 12)
        y, m = year + y, m + 1
        y2, m2 = divmod(first + i, 12)
        y2, m2 = year + y2, m2 + 1
        s = date(y, m, min(day, calendar.monthrange(y, m)[1]))
        nxt = date(y2, m2, min(day, calendar.monthrange(y2, m2)[1]))
        out.append(_row(start=s.isoformat(), end=(nxt - timedelta(days=1)).isoformat(),
                        inv=100.0, usage_amount=100.0))
    return out


def test_whole_months_accepts_a_subscription_billed_on_the_31st():
    rows = _billed_on(31, 12)
    # Feb 28 to Mar 30, Apr 30 to May 30, Jun 30 to Jul 30, Sep 30 to Oct 30, Nov 30 to Dec 30
    assert any(r["period_start"] == "2025-02-28" and r["period_end"] == "2025-03-30"
               for r in rows)
    lv = billing.usage_actuals(rows)["accounts"]["A"]
    assert lv["status"] == "scored"
    assert lv["values"]["window_months"] == 12 and lv["values"]["billed_periods"] == 12
    assert lv["values"]["usage_acv"] == D("1200.00")
    assert lv["reasons"] == []


def test_whole_months_accepts_a_subscription_billed_on_the_30th_across_february():
    rows = _billed_on(30, 6)  # Jan 30 to Feb 27, Feb 28 to Mar 29, ...
    lv = billing.usage_actuals(rows)["accounts"]["A"]
    assert lv["status"] == "scored" and lv["values"]["window_months"] == 6
    assert lv["reasons"] == []


def test_whole_months_still_rejects_weekly_and_stubs():
    assert billing._whole_months(date(2025, 1, 1), date(2025, 1, 7)) is None
    assert billing._whole_months(date(2025, 1, 1), date(2025, 2, 7)) is None
    assert billing._whole_months(date(2025, 1, 10), date(2025, 1, 31)) is None
    assert billing._whole_months(date(2025, 1, 1), date(2025, 3, 31)) == 3


def test_refund_row_is_excluded_from_contracted_vs_billed():
    rows = [_row(inv=-50.0, committed_amount=100.0),
            _row(start="2025-02-01", end="2025-02-28", inv=80.0, committed_amount=100.0)]
    lv = billing.contracted_vs_billed(rows)["accounts"]["A"]
    v = lv["values"]
    assert v["periods"] == 1 and v["shortfall_total"] == D("20.00")
    assert v["billed_vs_committed"] == D("0.8000")
    assert any("invalid_money_value" in r for r in lv["reasons"])


def test_unparseable_amount_is_counted_under_its_own_name():
    rows = [_row(inv="1,200"), _row(start="2025-02-01", end="2025-02-28", inv=10.0,
                                    list_amount="$100"), _row(start="2025-03-01",
                                                              end="2025-03-31", inv=None)]
    out = billing.billing_realization(rows)
    assert out["skipped"]["rows_unparseable_amount"] == 2
    assert out["skipped"]["rows_missing_key_fields"] == 1
    assert out["accounts"] == {}


def test_usage_units_acv_is_rounded_to_the_cent():
    rows = [dict(r, usage_units=1) for r in _billed_on(1, 6)]
    v = billing.usage_actuals(rows)["accounts"]["A"]["values"]
    assert v["usage_units_acv"] == D("12.00")
    rows = [dict(r, usage_units=D("0.333")) for r in _billed_on(1, 7)]
    v = billing.usage_actuals(rows)["accounts"]["A"]["values"]
    assert v["usage_units_acv"] == (D("0.333") * 7 * 12 / 7).quantize(D("0.01"))
    assert v["usage_units_acv"].as_tuple().exponent == -2
