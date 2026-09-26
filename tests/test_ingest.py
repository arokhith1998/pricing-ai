"""Tests for ingestion + identity resolution."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pricing.ingest import (
    CurrencyBlockedError,
    LoadReport,
    SchemaError,
    _deal_type_of,
    apply_header_mapping,
    enrich,
    ingest_verbose,
    normalize_account_name,
    resolve_identity,
    validate,
)


def test_normalize_strips_form_punctuation_and_case():
    assert normalize_account_name("  ACME, Inc. ") == "acme"
    assert normalize_account_name("Acme Inc") == "acme"
    assert normalize_account_name("Lumen Data LLC") == "lumen data"
    assert normalize_account_name("lumen   data") == "lumen data"
    # a descriptive qualifier is part of identity, not stripped
    assert normalize_account_name("Lumen Data") == normalize_account_name("LUMEN DATA, Corp.")


def test_resolve_identity_collapses_messy_variants():
    df = pd.DataFrame({
        "opportunity_id": ["O1", "O2", "O3", "O4"],
        "account_id": ["ACC-1", "", "", "ACC-9"],
        "account_name": ["Acme, Inc.", "ACME inc", "  acme ", "Zephyr LLC"],
    })
    out = resolve_identity(df)
    ids = out.set_index("opportunity_id")["resolved_account_id"]
    # first three are the same account (Acme), backfilled to the explicit id
    assert ids["O1"] == ids["O2"] == ids["O3"] == "ACC-1"
    # the fourth is a different account
    assert ids["O4"] != ids["O1"]
    assert out["resolved_account_id"].nunique() == 2


def test_validate_raises_on_missing_required_columns():
    df = pd.DataFrame({"opportunity_id": ["O1"], "account_name": ["Acme"]})
    with pytest.raises(SchemaError):
        validate(df)


def test_enrich_derives_discount_and_policy_flags():
    df = pd.DataFrame({
        "opportunity_id": ["O1", "O2"],
        "account_id": ["ACC-1", "ACC-2"],
        "account_name": ["Acme", "Zephyr"],
        "outcome": ["closed_won", "closed_lost"],
        "list_acv": [100_000.0, 50_000.0],
        "booked_acv": [80_000.0, 47_500.0],
        "approved_by": ["", ""],
    })
    out = enrich(resolve_identity(df), policy_threshold=0.15)
    row1 = out.set_index("opportunity_id").loc["O1"]
    assert row1["discount_pct"] == pytest.approx(0.20)
    assert row1["price_realization"] == pytest.approx(0.80)
    assert row1["discount_amount"] == pytest.approx(20_000.0)
    assert bool(row1["is_won"]) is True
    assert row1["discount_band"] == "20-25%"
    assert bool(row1["off_policy"]) is True
    # off-policy with no recorded approver → governance gap
    assert bool(row1["off_policy_unapproved"]) is True
    # O2 is a 5% discount → on policy
    row2 = out.set_index("opportunity_id").loc["O2"]
    assert row2["discount_pct"] == pytest.approx(0.05)
    assert bool(row2["off_policy"]) is False


# --- Deal-type (New vs Renewal) ingestion (2026-06-10 dry-run, wishlist 4) ---


def test_deal_type_classifier_three_state():
    # boolean renewal flags
    assert _deal_type_of("true") == "renewal"
    assert _deal_type_of("false") == "new"
    # CRM Type values
    assert _deal_type_of("Renewal") == "renewal"
    assert _deal_type_of("Existing Business - Upgrade") == "renewal"
    assert _deal_type_of("New Business") == "new"
    # unknowns stay unknown: never guessed, never fillna'd
    assert _deal_type_of("") == ""
    assert _deal_type_of("nan") == ""
    assert _deal_type_of("Closed") == ""


def test_type_column_rescued_only_when_values_look_like_deal_types():
    df = pd.DataFrame({
        "Opportunity ID": ["O1", "O2", "O3"],
        "Account": ["A", "B", "C"],
        "Stage": ["Closed Won", "Closed Won", "Closed Lost"],
        "Amount": ["90000", "80000", "70000"],
        "List Price": ["100000", "100000", "100000"],
        "Type": ["New Business", "Renewal", "New Business"],
    })
    report = LoadReport()
    out = apply_header_mapping(df, report)
    # claimed by value scan, with provenance disclosed
    assert "is_renewal" in out.columns
    assert report.field_sources["is_renewal"] == "Type (value-scan, high)"
    assert "Type" not in report.unmapped_columns


def test_generic_type_column_stays_unmapped_when_values_dont_check_out():
    # The "Forecast Category" lesson: a generic header whose values do not
    # look like deal types must stay unmapped, never fuzzy-claimed.
    df = pd.DataFrame({
        "Opportunity ID": ["O1", "O2"],
        "Account": ["A", "B"],
        "Stage": ["Closed Won", "Closed Lost"],
        "Amount": ["90000", "80000"],
        "List Price": ["100000", "100000"],
        "Type": ["Closed", "Closed"],
    })
    report = LoadReport()
    out = apply_header_mapping(df, report)
    assert "is_renewal" not in out.columns
    assert "Type" in report.unmapped_columns


def test_ingest_derives_canonical_deal_type_from_type_column(tmp_path):
    """End to end: a Salesforce-style Type column becomes the canonical
    three-state deal_type ('new' / 'renewal' / '') plus the is_renewal bool."""
    n = 36
    types = (["New Business"] * 18 + ["Renewal"] * 14
             + ["Add-On Services"] * 2 + [""] * 2)
    rows = ["opportunity_id,account_name,outcome,created_date,close_date,"
            "segment,product_tier,value_metric,list_acv,booked_acv,Type"]
    for i in range(n):
        rows.append(
            f"OPP-{i:03d},Acct {i},closed_won,2025-01-01,2025-02-15,"
            f"SMB,Pro,hybrid,100000,90000,{types[i]}"
        )
    p = tmp_path / "deals-with-type.csv"
    p.write_text("\n".join(rows), encoding="utf-8")

    df, report = ingest_verbose(p)
    assert "deal_type" in df.columns
    counts = df["deal_type"].value_counts()
    assert counts["new"] == 18
    assert counts["renewal"] == 14
    # unknown values stay '' (never guessed into a bucket)
    assert (df["deal_type"] == "").sum() == 4
    assert df["is_renewal"].sum() == 14
    assert report.field_sources["is_renewal"] == "Type (value-scan, high)"


# --- Currency (2026-09-26 data-layer fix) ------------------------------------


def _mixed_currency_csv(tmp_path, n_usd: int = 20, n_eur: int = 15):
    rows = ["opportunity_id,account_name,outcome,created_date,close_date,"
            "segment,product_tier,value_metric,list_acv,booked_acv"]
    for i in range(n_usd):
        rows.append(f"OPP-U{i:03d},Acct {i},closed_won,2025-01-01,2025-02-15,"
                    f"SMB,Pro,hybrid,$100000,$90000")
    for i in range(n_eur):
        rows.append(f"OPP-E{i:03d},Acct {100 + i},closed_won,2025-01-01,"
                    f"2025-02-15,SMB,Pro,hybrid,€100000,€90000")
    p = tmp_path / "mixed.csv"
    p.write_text("\n".join(rows), encoding="utf-8")
    return p


def test_mixed_currency_blocks_by_default(tmp_path):
    """Summing EUR and USD as one number silently corrupts every dollar total;
    ingestion must refuse rather than warn-and-sum."""
    p = _mixed_currency_csv(tmp_path)
    with pytest.raises(CurrencyBlockedError) as exc_info:
        ingest_verbose(p)
    err = exc_info.value
    assert "USD" in str(err) and "EUR" in str(err)
    # the report is attached to the exception even though ingestion refused
    assert err.report.blockers
    assert "USD" in err.report.blockers[0] and "EUR" in err.report.blockers[0]


def test_mixed_currency_normalizes_when_fx_rates_supplied(tmp_path):
    p = _mixed_currency_csv(tmp_path)
    df, report = ingest_verbose(
        p, fx_rates={"EUR": 1.10}, fx_rates_date="2026-09-01",
    )
    assert report.fx_normalized is True
    assert report.fx_rate_date == "2026-09-01"
    assert any("normalized" in n.lower() for n in report.notes)
    eur_rows = df[df["opportunity_id"].str.startswith("OPP-E")]
    assert np.allclose(eur_rows["booked_acv"].to_numpy(), 90_000 * 1.10)
    usd_rows = df[df["opportunity_id"].str.startswith("OPP-U")]
    assert np.allclose(usd_rows["booked_acv"].to_numpy(), 90_000)
    assert (df["currency"] == "USD").all()


def test_mixed_currency_missing_rate_still_blocks(tmp_path):
    """fx_rates that don't cover every currency present must still block, not
    silently leave the uncovered currency un-normalized."""
    p = _mixed_currency_csv(tmp_path)
    with pytest.raises(CurrencyBlockedError):
        ingest_verbose(p, fx_rates={"GBP": 1.27})  # no EUR rate supplied


def test_single_currency_file_defaults_to_usd(tmp_path):
    rows = ["opportunity_id,account_name,outcome,created_date,close_date,"
            "segment,product_tier,value_metric,list_acv,booked_acv"]
    for i in range(30):
        rows.append(f"OPP-{i:03d},Acct {i},closed_won,2025-01-01,2025-02-15,"
                    f"SMB,Pro,hybrid,100000,90000")
    p = tmp_path / "single.csv"
    p.write_text("\n".join(rows), encoding="utf-8")
    df, report = ingest_verbose(p)
    assert report.fx_normalized is False
    assert not report.blockers
    assert (df["currency"] == "USD").all()
