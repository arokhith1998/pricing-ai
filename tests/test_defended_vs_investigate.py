"""Tests for pricing.metrics.defended_vs_investigate.

Splits won deals into 'defended' (discount sat at/below reference) vs
'investigate' (above reference). No 'recovery rate' assumption — pure
reportage. Tests pin the boundary behavior, the empty case, and that the
two buckets cover the booked total exactly.
"""
from __future__ import annotations

import pandas as pd

from pricing import metrics


def _df(rows):
    """Build a minimal DataFrame with the columns the leakage path needs."""
    return pd.DataFrame([
        {
            "opportunity_id": f"OPP-{i}",
            "is_won": r["won"],
            "discount_pct": r["disc"],
            "list_acv": r["list"],
            "booked_acv": r["list"] * (1 - r["disc"]) if r["won"] else 0.0,
            "discount_amount": r["list"] * r["disc"] if r["won"] else 0.0,
            "segment": "Enterprise",
            "is_quarter_end": False,
        }
        for i, r in enumerate(rows)
    ])


def test_defended_vs_investigate_splits_at_reference_threshold(monkeypatch):
    # Pin reference_threshold to 0.10 so the split is deterministic.
    monkeypatch.setattr(metrics, "reference_discount",
                        lambda df, **kw: {"reference_threshold": 0.10, "reference_band": "5-10%",
                                          "peak_band": "10-15%", "peak_win_rate": 0.7})
    df = _df([
        {"won": True, "disc": 0.05, "list": 100_000},  # defended (5% < 10%)
        {"won": True, "disc": 0.10, "list": 100_000},  # defended (= threshold)
        {"won": True, "disc": 0.15, "list": 100_000},  # investigate
        {"won": True, "disc": 0.25, "list": 100_000},  # investigate
        {"won": False, "disc": 0.30, "list": 100_000},  # lost — ignored
    ])
    out = metrics.defended_vs_investigate(df, policy_threshold=0.15)
    assert out["reference_threshold"] == 0.10
    assert out["defended_deals"] == 2
    assert out["investigate_deals"] == 2
    # defended_value = 100K*0.95 + 100K*0.90 = 95K + 90K = 185K
    assert abs(out["defended_value"] - 185_000) < 1.0
    # investigate_value = 100K*0.85 + 100K*0.75 = 85K + 75K = 160K
    assert abs(out["investigate_value"] - 160_000) < 1.0
    # totals reconcile with booked
    assert abs(out["defended_value"] + out["investigate_value"] - 345_000) < 1.0
    # share
    assert abs(out["defended_pct_of_booked"] - 185_000 / 345_000) < 0.001


def test_defended_vs_investigate_empty_data():
    df = pd.DataFrame(columns=["opportunity_id", "is_won", "discount_pct",
                               "list_acv", "booked_acv", "discount_amount",
                               "segment", "is_quarter_end"])
    out = metrics.defended_vs_investigate(df, policy_threshold=0.15)
    assert out["defended_value"] == 0.0
    assert out["investigate_value"] == 0.0
    assert out["defended_deals"] == 0
    assert out["defended_pct_of_booked"] == 0.0
