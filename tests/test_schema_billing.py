"""PK-53: the contract_period_actuals grain, stripe and chargebee source values,
the billing-only outcome marker and the planted billing answer key."""

from __future__ import annotations

import csv
import hashlib
import io
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from pricing import guardrail
from pricing.generate import generate
from pricing.generate_billing import generate_billing
from pricing.ingest import ingest, ingest_frame_verbose
from pricing.schema import (
    ALL_COLUMNS, ALL_FIELD_NAMES, BILLING_ONLY_OUTCOME, BILLING_SOURCES,
    CONTRACT_PERIOD_COLUMNS, CONTRACT_PERIOD_FIELDS, CONTRACT_PERIOD_KEY_FIELDS,
    CONTRACT_PERIOD_MONEY_FIELDS, FIELDS, GENERATOR_COLUMNS, PROVENANCE_ENUMS,
    REQUIRED_FIELDS, CostBasis, Outcome, SourceSystem, win_rate_eligible,
)

ROOT = Path(__file__).resolve().parents[1]
PINNED_SHA256 = "ecfa1b6b25bd69d8258ced8d88ded57d21e31e87fc45166cdc8a2c306143ea48"


# --- source values -----------------------------------------------------------

def test_source_system_gains_stripe_and_chargebee_and_keeps_billing():
    values = {m.value for m in SourceSystem}
    assert {"stripe", "chargebee", "billing"} <= values
    assert {"csv", "salesforce", "hubspot", "cpq", "manual"} <= values
    assert PROVENANCE_ENUMS["source_system"] == frozenset(values)
    assert BILLING_SOURCES == {"billing", "stripe", "chargebee"}


def test_generator_output_is_byte_identical():
    df = generate(n=2000, seed=7)[GENERATOR_COLUMNS]
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\r\n")
    assert hashlib.sha256(buf.getvalue().encode("utf-8")).hexdigest() == PINNED_SHA256


GRAIN_ONLY = ["period_index", "period_start", "period_end", "list_amount",
              "invoiced_amount", "discount_amount", "credit_amount", "usage_units",
              "usage_amount", "committed_amount"]


def test_deal_schema_is_unchanged_by_the_grain():
    assert not set(GRAIN_ONLY) & set(ALL_FIELD_NAMES)
    assert ALL_COLUMNS == ALL_FIELD_NAMES
    assert not set(GRAIN_ONLY) & set(GENERATOR_COLUMNS)
    assert len(REQUIRED_FIELDS) == 10


def test_existing_file_loads_unchanged(tmp_path):
    p = tmp_path / "deals.csv"
    generate(n=60, seed=7)[GENERATOR_COLUMNS].to_csv(p, index=False)
    out = ingest(p)
    # ingest.enrich already derives a deal-level discount_amount; not new.
    assert not (set(GRAIN_ONLY) - {"discount_amount"}) & set(out.columns)
    assert (out["source_system"] == "csv").all()
    assert (out["cost_basis"] == "crm_proxy").all()


def test_stripe_and_chargebee_source_values_survive_ingest():
    base = generate(n=80, seed=7)[GENERATOR_COLUMNS].copy()
    base["source_system"] = ["stripe", "Chargebee"] * 40
    df, report = ingest_frame_verbose(base, source="t")
    assert set(df["source_system"]) == {"stripe", "chargebee"}
    assert "unrecognized" not in str(report.summary())


# --- the grain ---------------------------------------------------------------

def test_grain_fields_are_the_design_section_4_list():
    assert CONTRACT_PERIOD_COLUMNS == [
        "source_system", "source_record_id", "period_index", "period_start",
        "period_end", "currency", "list_amount", "invoiced_amount",
        "discount_amount", "credit_amount", "usage_units", "usage_amount",
        "committed_amount",
    ]
    assert {"period_start", "period_end", "currency", "list_amount",
            "invoiced_amount", "discount_amount", "credit_amount", "usage_units",
            "usage_amount", "committed_amount"} <= set(CONTRACT_PERIOD_COLUMNS)
    assert all(not f.required for f in CONTRACT_PERIOD_FIELDS)
    assert set(CONTRACT_PERIOD_KEY_FIELDS) <= set(CONTRACT_PERIOD_COLUMNS)
    assert set(CONTRACT_PERIOD_MONEY_FIELDS) <= set(CONTRACT_PERIOD_COLUMNS)


def test_grain_has_no_contact_or_customer_identifier_fields():
    banned = ("email", "phone", "contact", "address", "name", "customer",
              "account", "user", "person", "tax")
    for col in CONTRACT_PERIOD_COLUMNS:
        assert not any(b in col for b in banned), col
    by_name = {f.name: f for f in CONTRACT_PERIOD_FIELDS}
    assert "not a customer id" in by_name["source_record_id"].description
    assert "tax excluded" in by_name["invoiced_amount"].description
    assert "tax excluded" in by_name["list_amount"].description


def test_one_currency_per_row_and_money_fields_are_floats():
    by_name = {f.name: f for f in CONTRACT_PERIOD_FIELDS}
    assert by_name["currency"].dtype == "str"
    for m in CONTRACT_PERIOD_MONEY_FIELDS:
        assert by_name[m].dtype == "float"
        assert by_name[m].description.rstrip().endswith("Money.")


def test_nothing_in_the_grain_is_called_margin_and_cost_basis_is_absent():
    for f in CONTRACT_PERIOD_FIELDS:
        text = f"{f.name} {f.description} {f.example}".lower()
        assert "margin" not in text
        assert "cost" not in text
    assert "cost_basis" not in CONTRACT_PERIOD_COLUMNS
    assert "cogs_acv" not in CONTRACT_PERIOD_COLUMNS
    # cost_basis still defaults to crm_proxy; erp_verified stays connector-only.
    assert CostBasis.ERP_VERIFIED.value == "erp_verified"


def test_generated_billing_rows_never_carry_cost_or_erp_verified():
    df, _ = generate_billing(seed=7, filler=5)
    assert list(df.columns) == CONTRACT_PERIOD_COLUMNS
    assert "cost_basis" not in df.columns and "cogs_acv" not in df.columns


# --- the closed-lost gap -----------------------------------------------------

def test_win_rate_eligibility_refuses_billing_sources():
    assert win_rate_eligible("salesforce", "closed_won")
    assert win_rate_eligible(SourceSystem.SALESFORCE, Outcome.WON)
    assert win_rate_eligible("salesforce", Outcome.WON)
    assert win_rate_eligible(" CSV ", "Closed_Lost")
    assert not win_rate_eligible(SourceSystem.STRIPE, "closed_won")
    assert not win_rate_eligible(SourceSystem.CHARGEBEE, Outcome.WON)
    for missing in (None, float("nan"), ""):
        assert not win_rate_eligible(missing, "closed_won")
    assert not win_rate_eligible("csv", BILLING_ONLY_OUTCOME)
    for source in ("stripe", "chargebee", "billing", "Stripe"):
        assert not win_rate_eligible(source, "closed_won")
        assert not win_rate_eligible(source, "closed_lost")
        assert not win_rate_eligible(source, BILLING_ONLY_OUTCOME)
    assert BILLING_ONLY_OUTCOME not in {m.value for m in Outcome}


def _crm_records(n=240) -> list[dict]:
    rows = pd.read_csv(ROOT / "data" / "synthetic" / "deals.csv").head(n).to_dict("records")
    for r in rows:
        r["currency_iso"] = "USD"
    return rows


def _billing_deals(n, source="stripe") -> list[dict]:
    out = []
    for i, r in enumerate(_crm_records(n)):
        r = dict(r)
        r.update(opportunity_id=f"BILL-{i}", outcome=BILLING_ONLY_OUTCOME,
                 source_system=source)
        out.append(r)
    return out


@pytest.mark.parametrize("source", ["stripe", "chargebee", "billing"])
def test_guardrail_refuses_a_billing_only_book(source):
    with pytest.raises(guardrail.DealDataError, match="Only 0 usable closed"):
        guardrail.analyze_deals(_billing_deals(240, source))


def test_billing_rows_do_not_move_win_rate_in_a_mixed_book():
    crm = _crm_records()
    alone = guardrail.analyze_deals(crm)
    mixed = guardrail.analyze_deals(crm + _billing_deals(200))
    assert mixed["readiness"]["closed_received"] == alone["readiness"]["closed_received"]
    assert mixed["analysis"]["reference_discount"] == alone["analysis"]["reference_discount"]
    assert mixed["analysis"]["leakage"]["segment_references"] == \
        alone["analysis"]["leakage"]["segment_references"]


def test_ingest_excludes_billing_only_rows_from_closed_history():
    crm = pd.DataFrame(_crm_records(120)).drop(columns=["currency_iso"])
    bill = pd.DataFrame(_billing_deals(40)).drop(columns=["currency_iso"])
    df, report = ingest_frame_verbose(pd.concat([crm, bill], ignore_index=True), source="t")
    assert len(df) == 120
    assert not df["opportunity_id"].astype(str).str.startswith("BILL-").any()
    assert report.excluded_open.get(BILLING_ONLY_OUTCOME) == 40


# --- the planted answer key --------------------------------------------------

def _by_sub(df):
    return {k: g.sort_values("period_index") for k, g in df.groupby("source_record_id")}


def test_generation_is_deterministic_and_independent_of_filler_for_planted():
    a, key_a = generate_billing(seed=7, filler=10)
    b, key_b = generate_billing(seed=7, filler=10)
    pd.testing.assert_frame_equal(a, b)
    assert key_a == key_b
    planted_only, key_c = generate_billing(seed=99, filler=0)
    assert key_c == key_a
    planted_rows = a[~a["source_record_id"].str.startswith("SUB-F")]
    pd.testing.assert_frame_equal(planted_rows.reset_index(drop=True), planted_only)
    c, _ = generate_billing(seed=8, filler=10)
    assert not a.equals(c)


def test_generator_uses_its_own_stream_and_does_not_touch_the_deal_generator():
    before = generate(n=300, seed=7)
    generate_billing(seed=7, filler=50)
    after = generate(n=300, seed=7)
    pd.testing.assert_frame_equal(before, after)


def test_every_row_has_a_key_and_one_currency_and_identity_holds():
    df, _ = generate_billing(seed=7, filler=15)
    assert not df[CONTRACT_PERIOD_KEY_FIELDS].isna().any().any()
    assert df["currency"].isin(["USD", "EUR"]).all()
    assert set(df["source_system"]) <= {"stripe", "chargebee"}
    known = df.dropna(subset=["list_amount"])
    spent = known["invoiced_amount"] + known["discount_amount"] + known["credit_amount"]
    assert (known["list_amount"] + 0.005 >= spent).all()
    assert (pd.to_datetime(df["period_end"]) >= pd.to_datetime(df["period_start"])).all()


def test_list_versus_contracted_gaps():
    df, key = generate_billing()
    subs = _by_sub(df)
    assert len(subs["SUB-GAP-10"]) == 12
    assert key["SUB-GAP-10"]["list_total"] == Decimal("120000.00")
    assert key["SUB-GAP-10"]["invoiced_total"] == Decimal("108000.00")
    assert key["SUB-GAP-10"]["gap_total"] == Decimal("12000.00")
    assert key["SUB-GAP-10"]["realization"] == Decimal("0.9000")
    assert key["SUB-GAP-25"]["list_total"] == Decimal("96000.00")
    assert key["SUB-GAP-25"]["invoiced_total"] == Decimal("72000.00")
    assert key["SUB-GAP-25"]["realization"] == Decimal("0.7500")
    assert key["SUB-AT-LIST"]["realization"] == Decimal("1.0000")
    assert key["SUB-GAP-EUR"]["currency"] == "EUR"
    assert (subs["SUB-GAP-EUR"]["currency"] == "EUR").all()
    # Custom-price gaps are not discount objects: discount_amount is 0 and the
    # gap is list minus invoiced.
    for sub in ("SUB-GAP-10", "SUB-GAP-25", "SUB-AT-LIST", "SUB-GAP-EUR"):
        g = subs[sub]
        assert (g["discount_amount"] == 0).all() and (g["credit_amount"] == 0).all()
        assert key[sub]["discount_total"] == Decimal("0.00")
    assert round(subs["SUB-GAP-10"]["list_amount"].sum()
                 - subs["SUB-GAP-10"]["invoiced_amount"].sum(), 2) == 12000.00


def test_hundred_percent_off_coupon_maps_to_credits_only():
    df, key = generate_billing()
    g = _by_sub(df)["SUB-COUPON-100"]
    free = g.head(3)
    assert (free["invoiced_amount"] == 0).all()
    assert (free["credit_amount"] == free["list_amount"]).all()
    assert (g["discount_amount"] == 0).all()  # booked once, as credits
    assert (g.tail(9)["credit_amount"] == 0).all()
    k = key["SUB-COUPON-100"]
    assert k["zero_invoice_periods"] == 3
    assert k["credits_tcv"] == Decimal("6000.00") == k["credit_total"]
    assert k["discount_total"] == Decimal("0.00")
    assert round(g["credit_amount"].sum(), 2) == 6000.00


def test_percentage_coupon_is_a_discount_object():
    df, key = generate_billing()
    g = _by_sub(df)["SUB-COUPON-PCT"]
    assert (g["discount_amount"] == 1000.0).all() and (g["credit_amount"] == 0).all()
    assert (g["list_amount"] == g["invoiced_amount"] + g["discount_amount"]).all()
    assert key["SUB-COUPON-PCT"]["discount_total"] == Decimal("12000.00")


def test_ramp_schedule():
    df, key = generate_billing()
    g = _by_sub(df)["SUB-RAMP"]
    assert list(g["invoiced_amount"]) == [60000.0, 80000.0, 100000.0]
    assert list(g["list_amount"]) == [100000.0] * 3
    assert (g["discount_amount"] == 0).all()  # ramp phases are not discounts
    k = key["SUB-RAMP"]
    assert k["discount_total"] == Decimal("0.00")
    assert k["gap_total"] == Decimal("60000.00")
    assert (k["ramp_year_1_acv"], k["ramp_year_2_acv"], k["booked_acv"]) == (
        Decimal("60000.00"), Decimal("80000.00"), Decimal("100000.00"))
    assert k["term_months"] == 36


def test_six_and_five_billed_period_accounts():
    df, key = generate_billing()
    subs = _by_sub(df)
    assert len(subs["SUB-USAGE-6"]) == 6 and len(subs["SUB-USAGE-5"]) == 5
    six, five = key["SUB-USAGE-6"], key["SUB-USAGE-5"]
    assert six["usage_acv_status"] == "scored"
    assert six["usage_total"] == Decimal("67500.00")  # 135,000 units at 0.50
    assert six["usage_acv"] == Decimal("135000.00")   # trailing 6 periods, annualised x2
    assert five["usage_acv_status"] == "insufficient_data"
    assert five["usage_acv"] is None
    assert five["usage_total"] == Decimal("56000.00")  # 112,000 units at 0.50
    assert six["list_unit_rate"] == Decimal("0.50")
    assert six["committed_amount_per_period"] == Decimal("1500.00")
    assert six["committed_total"] == Decimal("9000.00")
    assert five["committed_total"] == Decimal("7500.00")
    # usage amount is a part of the invoice, never more than it.
    for g in (subs["SUB-USAGE-6"], subs["SUB-USAGE-5"]):
        assert (g["usage_amount"] <= g["invoiced_amount"]).all()
        assert (g["committed_amount"] == 1500.0).all()


def test_tiered_price_has_no_unit_rates():
    df, key = generate_billing()
    g = _by_sub(df)["SUB-TIERED"]
    k = key["SUB-TIERED"]
    assert k["tiered"] is True
    assert k["list_unit_rate"] is None and k["overage_rate"] is None
    assert g["list_amount"].isna().all()
    # 8,000 -> 8,000.00; 30,000 -> 10,000 + 20,000*0.8 = 26,000.00; 60,000 -> 10,000
    # + 40,000*0.8 + 10,000*0.6 = 48,000.00; then 11,600 + 45,000 + 38,000.
    assert list(g["usage_amount"].head(3)) == [8000.0, 26000.0, 48000.0]
    assert k["usage_total"] == Decimal("176600.00")
    assert k["usage_acv"] == Decimal("353200.00")
    assert round(g["usage_amount"].sum(), 2) == 176600.00


def test_annualisation_uses_decimal_division_not_a_floor():
    from pricing.generate_billing import _annualise
    assert _annualise(100, 7) == Decimal("1.71")   # 1.7142 dollars, to the cent
    assert _annualise(5, 8) == Decimal("0.08")     # 0.075 rounds half up


def test_outcome_field_documents_the_billing_marker():
    by_name = {f.name: f for f in FIELDS}
    assert BILLING_ONLY_OUTCOME in by_name["outcome"].description


def test_csv_round_trip_keeps_columns(tmp_path):
    df, _ = generate_billing(seed=7, filler=3)
    p = tmp_path / "periods.csv"
    df.to_csv(p, index=False)
    with open(p, newline="", encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == CONTRACT_PERIOD_COLUMNS
