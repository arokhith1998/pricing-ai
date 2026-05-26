"""Tests for ingestion + identity resolution."""

from __future__ import annotations

import pandas as pd
import pytest

from pricing.ingest import (
    SchemaError,
    enrich,
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
