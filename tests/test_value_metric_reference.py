"""Value-metric reference partition: seats, consumption, and hybrid discounts
are different levers, so each earns its own win point (basis disclosed), while
the pooled reference stays unchanged."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pricing import diagnostic, metrics
from pricing.ingest import ingest

ROOT = Path(__file__).resolve().parents[1]

_KNOWN_BASES = {metrics._BASIS_OWN, metrics._BASIS_FALLBACK, metrics._BASIS_NO_SEGMENT,
               metrics._BASIS_BAND_FLOOR}


def _book() -> pd.DataFrame:
    return ingest(ROOT / "data" / "synthetic" / "deals.csv")


def test_table_covers_each_value_metric_with_disclosed_basis():
    df = _book()
    table = metrics.value_metric_reference_table(df)
    metrics_seen = {row["value_metric"] for row in table}
    # The synthetic book carries all three value metrics.
    assert {"seats", "consumption", "hybrid"} <= metrics_seen
    for row in table:
        assert 0.0 <= row["reference_threshold"] <= 1.0
        assert row["basis"] in _KNOWN_BASES
        assert row["deals"] > 0


def test_well_populated_metrics_earn_their_own_win_point():
    df = _book()
    table = {row["value_metric"]: row for row in metrics.value_metric_reference_table(df)}
    # Each metric clears the 100-deal floor in the demo book, so it should not
    # be silently pooled; it earns its own win point, discloses a fallback, or
    # (2026-09-27 fix) discloses a band-floor fallthrough when its own
    # win-point search degenerates to the cheapest real band (consumption on
    # the current demo book: its search lands on 0-5% by a hair, so it falls
    # through to the global reference rather than outranking a coarser one).
    for name in ("seats", "consumption", "hybrid"):
        assert table[name]["deals"] >= 100
        assert table[name]["basis"] in (metrics._BASIS_OWN, metrics._BASIS_BAND_FLOOR)
    assert table["seats"]["basis"] == metrics._BASIS_OWN
    assert table["hybrid"]["basis"] == metrics._BASIS_OWN
    assert table["consumption"]["basis"] == metrics._BASIS_BAND_FLOOR


def test_pooled_reference_is_unchanged_and_surfaced_alongside():
    df = _book()
    # The partition is additive: the pooled reference is still computed and the
    # diagnostic now surfaces both.
    res = diagnostic.analyze(df)
    assert "reference_discount" in res
    assert "value_metric_reference" in res
    assert res["value_metric_reference"]  # non-empty on a real book
    pooled = res["reference_discount"]["reference_threshold"]
    assert 0.0 <= pooled <= 1.0


def test_empty_or_missing_column_returns_empty():
    assert metrics.value_metric_reference_table(pd.DataFrame()) == []
    df = _book().drop(columns=["value_metric"])
    assert metrics.value_metric_reference_table(df) == []
