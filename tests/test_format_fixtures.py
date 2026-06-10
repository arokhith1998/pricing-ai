"""Ingestion stress test — the same 300 deals, exported six real-world ways.

Each fixture in data/synthetic/format-fixtures/ is the SAME underlying deals
(data/synthetic/format-base.csv) re-serialized the way a different system
exports it (Salesforce, HubSpot, an EU ERP, a warehouse dump, Finance's Excel,
a hand-maintained CRM). A correct pipeline produces identical metrics from
every one.

This replaces the exploratory tools/check_format_fixtures.py (item 6 of the fix
list in that directory's README). Done = every fixture ingests and reproduces
the canonical booked-ACV total within 0.5%.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pricing.ingest import ingest

ROOT = Path(__file__).resolve().parents[1]
FIXDIR = ROOT / "data" / "synthetic" / "format-fixtures"
BASE = ROOT / "data" / "synthetic" / "format-base.csv"
TOLERANCE = 0.005  # 0.5%

FIXTURES = [
    "salesforce_export.csv",   # Title Case headers, "Closed Won", MM/DD/YYYY, "$1,234.56", CRLF
    "hubspot_export.csv",      # "Record ID"/"Deal Stage", "closedwon", ISO datetimes
    "eu_export.csv",           # semicolon delimiter, DD.MM.YYYY, decimal commas, ja/nein
    "warehouse_export.csv",    # UPPER_SNAKE abbreviations, 1/0 booleans
    "finance_export.xlsx",     # title+blank rows above header, currency strings, TOTAL row
    "messy_export.csv",        # BOM, padded/mixed-case headers, no account_id, blank rows
]


@pytest.fixture(scope="module")
def canonical() -> dict:
    df = pd.read_csv(BASE)
    return {
        "n": len(df),
        "total": float(df["booked_acv"].sum()),
        "won": int((df["outcome"] == "closed_won").sum()),
    }


def test_all_fixtures_present():
    have = {p.name for p in FIXDIR.iterdir()} if FIXDIR.exists() else set()
    missing = [f for f in FIXTURES if f not in have]
    assert not missing, (
        f"missing fixtures {missing}; regenerate with "
        "`PYTHONPATH=. python tools/make_format_fixtures.py`"
    )


@pytest.mark.parametrize("fixture", FIXTURES)
def test_fixture_ingests_and_matches_canonical(fixture, canonical):
    df = ingest(FIXDIR / fixture)  # must not raise on any real-world format

    # 1. Every deal survives — blank separators and the Excel TOTAL row are
    #    dropped, but no real deal is lost.
    assert len(df) == canonical["n"], (
        f"{fixture}: ingested {len(df)} rows, expected {canonical['n']}"
    )

    # 2. The booked-ACV total matches the canonical within tolerance. A comma
    #    misread as a decimal (the worst, silent failure) would blow this up.
    total = float(df["booked_acv"].sum())
    drift = abs(total - canonical["total"]) / canonical["total"]
    assert drift < TOLERANCE, (
        f"{fixture}: booked-ACV total {total:,.2f} drifts {drift:.2%} from "
        f"canonical {canonical['total']:,.2f}"
    )

    # 3. Outcomes mapped exactly — every "Closed Won"/"closedwon"/"W"/"WON"
    #    variant resolves, so the won count matches deal-for-deal.
    assert int(df["is_won"].sum()) == canonical["won"], (
        f"{fixture}: {int(df['is_won'].sum())} won, expected {canonical['won']} "
        "(outcome alias unmapped?)"
    )

    # 4. Dates parsed — a swapped day/month format or a delimiter miss would
    #    NaT-out the column and silently break quarter-end analysis.
    parsed = df["close_date"].notna().mean()
    assert parsed > 0.99, f"{fixture}: only {parsed:.0%} of close_dates parsed"
