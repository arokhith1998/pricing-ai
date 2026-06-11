"""Tests for ingestion + identity resolution."""

from __future__ import annotations

import pandas as pd
import pytest

from pricing.ingest import (
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
