"""Round-3 judgment-trap tests.

Rounds 1–2 covered format variety and silent corruption. Round 3 tests cases
where correctness needs a judgment call: pass = a defensible call made OR the
assumption disclosed in the LoadReport. A right number with hidden judgment
fails. Same 300 canonical deals underneath (data/synthetic/format-base.csv).

Promoted from tools/check_round3_fixtures.py once green. Each test asserts the
DataFrame AND the LoadReport disclosure that makes the judgment visible. See
data/synthetic/round3-fixtures/README.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pricing.ingest import ingest_verbose

ROOT = Path(__file__).resolve().parents[1]
FIXDIR = ROOT / "data" / "synthetic" / "round3-fixtures"
BASE = ROOT / "data" / "synthetic" / "format-base.csv"
TOLERANCE = 0.005


@pytest.fixture(scope="module")
def canonical() -> dict:
    df = pd.read_csv(BASE)
    return {
        "n": len(df),
        "won_total": float(df.loc[df["outcome"] == "closed_won", "booked_acv"].sum()),
    }


def test_conflicting_dupes_are_flagged_not_silently_merged(canonical):
    """Same opportunity_id with different values is a data-quality error: keep
    one, flag it — never silently pick a side."""
    df, report = ingest_verbose(FIXDIR / "conflicting_dupes.csv")
    assert len(df) == canonical["n"]
    assert len(report.conflicting_ids) == 12, report.conflicting_ids


def test_ambiguous_dates_assumption_is_disclosed():
    """When every day <= 12 the day/month order can't be inferred; the
    month-first assumption must be stated in the report, not silently made."""
    _df, report = ingest_verbose(FIXDIR / "ambiguous_dates.csv")
    disclosed = any(
        "ambiguous" in n.lower() and "month-first" in n.lower()
        for n in report.notes
    )
    assert disclosed, f"date assumption not disclosed; notes={report.notes}"


def test_mixed_currency_is_flagged():
    """Stripping symbols would sum EUR + USD into one meaningless total; the
    mixed currency must be flagged."""
    _df, report = ingest_verbose(FIXDIR / "mixed_currency.csv")
    assert "€" in report.currencies and "$" in report.currencies
    assert len(report.currencies) > 1


def test_uplift_deals_kept_as_pricing_power():
    """Deals booked above list (negative discount) are a pricing-power signal,
    not leakage — they must survive (not be clamped to 0) and be reported."""
    df, report = ingest_verbose(FIXDIR / "uplift_deals.csv")
    assert len(df) == 300
    n_neg = int((df["discount_pct"] < -1e-9).sum())
    assert n_neg == 15, f"{n_neg} above-list deals survived, expected 15"
    assert report.above_list_deals == 15
    # labeled into their own band, never mislabeled into "0-5%"
    assert "above list" in set(df.loc[df["discount_pct"] < 0, "discount_band"])
    assert not np.isinf(df["discount_pct"]).any()


def test_blank_booked_lost_preserves_won_total_and_reports(canonical):
    """Blank booked values on lost deals must not corrupt the won total, and the
    blanks must be reported (not silently summed as zero)."""
    df, report = ingest_verbose(FIXDIR / "blank_booked_lost.csv")
    won_total = float(df.loc[df["outcome"] == "closed_won", "booked_acv"].sum())
    drift = abs(won_total - canonical["won_total"]) / canonical["won_total"]
    assert drift < TOLERANCE, f"won total drifts {drift:.2%}"
    assert report.blank_booked == 20, report.blank_booked


def test_big_injection_scales_and_keeps_formulas_as_text():
    """A 30k-row export with formula-injection account names must ingest at scale
    and keep '=HYPERLINK(...)' as inert text, never evaluated."""
    df, _report = ingest_verbose(FIXDIR / "big_injection.csv")
    assert len(df) == 30000
    names = df["account_name"].astype(str)
    assert names.str.startswith("=HYPERLINK").any(), "formula text not preserved"
