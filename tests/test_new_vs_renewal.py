"""Known-answer tests for the New vs Renewal split (2026-06-10 dry-run,
wishlist 4): renewal discounting is a different disease from new-business
discounting, so the diagnostic splits realization, average discount, and the
win-point analysis by deal type, and degrades gracefully without the column.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pricing import diagnostic, metrics
from pricing.ingest import enrich, resolve_identity


def _build(rows: list[dict]) -> pd.DataFrame:
    """Raw rows -> resolved + enriched frame (skips CSV/string coercion)."""
    df = pd.DataFrame(rows)
    if "approved_by" not in df.columns:
        df["approved_by"] = ""
    return enrich(resolve_identity(df))


def _deal(opp, outcome, list_acv, booked, is_renewal, segment="SMB"):
    return dict(opportunity_id=opp, account_id=opp, account_name=opp,
                outcome=outcome, list_acv=float(list_acv),
                booked_acv=float(booked), is_renewal=is_renewal,
                segment=segment)


def test_split_math_known_answers():
    df = _build([
        # New business: 3 won at 10/20/30% discount + 1 lost.
        _deal("N1", "closed_won", 100_000, 90_000, False),
        _deal("N2", "closed_won", 100_000, 80_000, False),
        _deal("N3", "closed_won", 100_000, 70_000, False),
        _deal("N4", "closed_lost", 100_000, 90_000, False),
        # Renewals: 2 won at 5/15% discount.
        _deal("R1", "closed_won", 100_000, 95_000, True),
        _deal("R2", "closed_won", 100_000, 85_000, True),
    ])
    out = metrics.new_vs_renewal(df, min_deals=1).set_index("deal_type")

    new = out.loc["New"]
    assert new["deals"] == 4 and new["won"] == 3
    assert new["win_rate"] == pytest.approx(0.75)
    assert new["avg_discount_won"] == pytest.approx(0.20)
    # $-weighted realization on won deals: (90+80+70)/300
    assert new["price_realization_won"] == pytest.approx(0.80)
    assert new["booked_acv_won"] == pytest.approx(240_000.0)

    ren = out.loc["Renewal"]
    assert ren["deals"] == 2 and ren["won"] == 2
    assert ren["win_rate"] == pytest.approx(1.0)
    assert ren["avg_discount_won"] == pytest.approx(0.10)
    assert ren["price_realization_won"] == pytest.approx(0.90)

    # Groups this thin cannot earn their own win point: the global reference
    # is used and the fallback is disclosed, mirroring the segment rule.
    assert (out["reference_basis"]
            == "global fallback (insufficient data)").all()
    g_rt = metrics.reference_discount(df)["reference_threshold"]
    assert out["reference_threshold"].tolist() == pytest.approx([g_rt, g_rt])


def test_unrecognized_and_blank_types_land_in_other_bucket():
    # String-typed renewal flags (a recognized CRM Type column) route through
    # the same classifier: Renewal/New Business are typed, the rest is OTHER,
    # never silently guessed.
    df = _build([
        _deal("A", "closed_won", 100_000, 90_000, "Renewal"),
        _deal("B", "closed_won", 100_000, 90_000, "New Business"),
        _deal("C", "closed_won", 100_000, 90_000, "Upgrade"),
        _deal("D", "closed_won", 100_000, 90_000, ""),
    ])
    out = metrics.new_vs_renewal(df, min_deals=1).set_index("deal_type")
    assert out.loc["New", "deals"] == 1
    assert out.loc["Renewal", "deals"] == 1
    assert out.loc["Other/unknown", "deals"] == 2


def test_groups_thinner_than_min_deals_are_dropped():
    rows = [_deal(f"N{i}", "closed_won", 100_000, 90_000, False)
            for i in range(12)]
    rows.append(_deal("R1", "closed_won", 100_000, 95_000, True))
    out = metrics.new_vs_renewal(_build(rows), min_deals=10)
    assert list(out["deal_type"]) == ["New"]  # 1 renewal < min_deals


def test_degrades_gracefully_without_deal_type_column(capsys):
    df = _build([
        _deal("N1", "closed_won", 100_000, 90_000, False),
        _deal("N2", "closed_lost", 100_000, 90_000, False),
    ]).drop(columns=["deal_type", "is_renewal"])
    out = metrics.new_vs_renewal(df)
    assert out.empty
    assert list(out.columns) == metrics._NVR_COLS
    # ...and the printed readout simply omits the section.
    diagnostic.print_report(diagnostic.analyze(df))
    assert "New vs Renewal" not in capsys.readouterr().out


def test_sparse_deal_type_is_marked_insufficient_in_readout(capsys):
    # Column present, but no row classifies as New or Renewal.
    df = _build([
        _deal(f"U{i}", "closed_won", 100_000, 90_000, "Upgrade")
        for i in range(12)
    ])
    diagnostic.print_report(diagnostic.analyze(df))
    out = capsys.readouterr().out
    assert "New vs Renewal" in out
    assert "insufficient data" in out


def test_readout_prints_split_and_disease_framing(capsys):
    rows = []
    rows += [_deal(f"N{i}", "closed_won", 100_000, 80_000, False)
             for i in range(12)]
    rows += [_deal(f"R{i}", "closed_won", 100_000, 90_000, True)
             for i in range(12)]
    diagnostic.print_report(diagnostic.analyze(_build(rows)))
    out = capsys.readouterr().out
    assert "-- New vs Renewal" in out
    assert "Renewal discounting is a" in out
    assert "different disease" in out
