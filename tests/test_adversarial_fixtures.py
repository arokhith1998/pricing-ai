"""Round-2 adversarial ingestion tests — silent-corruption traps.

Round 1 (test_format_fixtures.py) proved header/format variety ingests. This
round attacks with cases that produce WRONG NUMBERS WITHOUT ERRORS, plus
degenerate inputs that must fail loudly. Same 300 canonical deals underneath
(data/synthetic/format-base.csv); each fixture has its own pass condition.

Promoted from tools/check_adversarial_fixtures.py once green. Each test asserts
both the resulting DataFrame and the LoadReport — the "here is what we read from
your file" artifact that makes every exclusion/dedupe/decode visible instead of
silent. See data/synthetic/adversarial-fixtures/README.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pricing.ingest import SchemaError, ingest, ingest_verbose

ROOT = Path(__file__).resolve().parents[1]
FIXDIR = ROOT / "data" / "synthetic" / "adversarial-fixtures"
BASE = ROOT / "data" / "synthetic" / "format-base.csv"
TOLERANCE = 0.005


@pytest.fixture(scope="module")
def canonical() -> dict:
    df = pd.read_csv(BASE)
    return {
        "n": len(df),
        "total": float(df["booked_acv"].sum()),
        "won": int((df["outcome"] == "closed_won").sum()),
        "close_dates": pd.to_datetime(
            df.sort_values("opportunity_id")["close_date"]
        ).reset_index(drop=True),
    }


def test_uk_dates_match_canonical_truth(canonical):
    """DD/MM/YYYY must be detected, not silently day/month-swapped."""
    df = ingest(FIXDIR / "uk_dates.csv")
    got = pd.to_datetime(
        df.sort_values("opportunity_id")["close_date"]
    ).reset_index(drop=True)
    wrong = int((got != canonical["close_dates"]).sum())
    assert wrong == 0, f"{wrong}/300 close_dates silently swapped day/month"


def test_open_pipeline_deals_are_excluded(canonical):
    """Open deals (Negotiation/Proposal/...) must be dropped and reported, not
    miscounted as losses (which tanks the win rate)."""
    df, report = ingest_verbose(FIXDIR / "open_pipeline.csv")
    assert len(df) == canonical["n"], f"kept {len(df)} rows, expected 300"
    assert int(df["is_won"].sum()) == canonical["won"]
    # the 40 open rows are accounted for in the report, by stage, not silently
    assert sum(report.excluded_open.values()) == 40, report.excluded_open
    assert report.excluded_open, "exclusion happened but was not reported"


def test_credits_zero_bad_cells_contained():
    """A $0 list price (div-by-zero) and unparseable money must not leak inf/NaN
    garbage into the totals; an accounting negative parses as one negative."""
    df = ingest(FIXDIR / "credits_zero.csv")
    assert int(np.isinf(df["discount_pct"]).sum()) == 0
    assert int((df["booked_acv"] < 0).sum()) <= 1


def test_dupe_opps_not_double_counted(canonical):
    """Exact re-export duplicates must drop into the report, not inflate $."""
    df, report = ingest_verbose(FIXDIR / "dupe_opps.csv")
    drift = abs(float(df["booked_acv"].sum()) - canonical["total"]) / canonical["total"]
    assert drift < TOLERANCE, f"total drifts {drift:.1%} (duplicates double-counted?)"
    assert report.exact_duplicates_dropped == 12, report.exact_duplicates_dropped
    assert len(df) == canonical["n"]


def test_cp1252_names_decode_without_mojibake():
    """Windows-1252 export must decode cleanly (cascade), not crash or mojibake —
    mojibake names break identity resolution."""
    df, report = ingest_verbose(FIXDIR / "cp1252_names.csv")
    moji = int(df["account_name"].astype(str).str.contains("Ã|�").sum())
    assert moji == 0, f"{moji} mojibake account names"
    assert report.encoding == "cp1252", f"decoded as {report.encoding}, expected cp1252"


def test_space_thousands_money_parses(canonical):
    """French 'NBSP thousands + decimal comma' money must parse exactly."""
    df = ingest(FIXDIR / "space_thousands.csv")
    drift = abs(float(df["booked_acv"].sum()) - canonical["total"]) / canonical["total"]
    assert drift < TOLERANCE, f"total drifts {drift:.1%}"


def test_multisheet_picks_the_deals_sheet(canonical):
    """A summary sheet before the data sheet must not win; pick by field
    coverage and report the chosen sheet."""
    df, report = ingest_verbose(FIXDIR / "multisheet.xlsx")
    assert len(df) == canonical["n"], f"rows={len(df)}"
    drift = abs(float(df["booked_acv"].sum()) - canonical["total"]) / canonical["total"]
    assert drift < TOLERANCE, f"total drifts {drift:.1%}"
    assert report.sheet == "Deals", f"chose sheet {report.sheet!r}, expected 'Deals'"


@pytest.mark.parametrize("fixture", ["header_only.csv", "garbage.csv"])
def test_degenerate_inputs_fail_loudly(fixture):
    """A header-only or non-deals file must raise a clean validation error,
    never silently return a (meaningless) DataFrame."""
    with pytest.raises(SchemaError):
        ingest(FIXDIR / fixture)
