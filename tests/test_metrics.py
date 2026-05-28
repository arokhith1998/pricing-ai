"""Known-answer tests for the leakage metrics (the trust-critical logic)."""

from __future__ import annotations

import pandas as pd
import pytest

from pricing import metrics
from pricing.ingest import enrich, resolve_identity


def _build(rows: list[dict]) -> pd.DataFrame:
    """Raw rows -> resolved + enriched frame (skips CSV/string coercion)."""
    df = pd.DataFrame(rows)
    if "approved_by" not in df.columns:
        df["approved_by"] = ""
    return enrich(resolve_identity(df))


def _won(opp, acct, list_acv, booked):
    return dict(opportunity_id=opp, account_id=acct, account_name=acct,
                outcome="closed_won", list_acv=float(list_acv),
                booked_acv=float(booked))


def test_gross_and_off_policy_leakage_known_values():
    df = _build([
        _won("O1", "A1", 100_000, 95_000),   # 5%  discount -> on policy
        _won("O2", "A2", 100_000, 80_000),   # 20% discount -> 5k over policy
        _won("O3", "A3", 200_000, 140_000),  # 30% discount -> 30k over policy
    ])
    lk = metrics.leakage(df, policy_threshold=0.15)
    # gross giveback = 5k + 20k + 60k
    assert lk["gross_discount_won"] == pytest.approx(85_000.0)
    # off-policy = (0) + (0.05*100k) + (0.15*200k)
    assert lk["off_policy_leakage_won"] == pytest.approx(35_000.0)


def _band_block(prefix, n, discount, win_rate):
    """n deals at a fixed discount, `win_rate` fraction of them won."""
    list_acv, booked = 100_000.0, 100_000.0 * (1 - discount)
    n_won = round(n * win_rate)
    rows = []
    for i in range(n):
        rows.append(dict(
            opportunity_id=f"{prefix}-{i}",
            account_id=f"{prefix}-{i}",
            account_name=f"{prefix}-{i}",
            outcome="closed_won" if i < n_won else "closed_lost",
            list_acv=list_acv, booked_acv=booked,
        ))
    return rows


def test_reference_discount_finds_the_plateau():
    # win rate climbs then plateaus at the 10-15% band (0.80) and stays flat.
    rows = []
    rows += _band_block("b00", 20, 0.02, 0.40)  # 0-5%
    rows += _band_block("b05", 20, 0.07, 0.50)  # 5-10%
    rows += _band_block("b10", 20, 0.12, 0.80)  # 10-15%  <- cheapest peak
    rows += _band_block("b15", 20, 0.17, 0.80)  # 15-20%
    rows += _band_block("b20", 20, 0.22, 0.80)  # 20-25%
    df = _build(rows)

    ref = metrics.reference_discount(df, seed=0)
    assert ref["peak_win_rate"] == pytest.approx(0.80)
    # the 10-15% band already reaches peak, so reference threshold is its lower edge
    assert ref["reference_threshold"] == pytest.approx(0.10)
    assert ref["reference_band"] == "10-15%"
    # bootstrap CIs are reported and bracket the point estimate
    lo, hi = ref["peak_win_rate_ci"]
    assert lo <= ref["peak_win_rate"] <= hi


def test_excess_vs_reference_only_counts_discount_above_reference():
    rows = []
    rows += _band_block("b00", 20, 0.02, 0.40)
    rows += _band_block("b05", 20, 0.07, 0.50)
    rows += _band_block("b10", 20, 0.12, 0.80)
    rows += _band_block("b15", 20, 0.17, 0.80)
    rows += _band_block("b20", 20, 0.22, 0.80)
    df = _build(rows)
    lk = metrics.leakage(df)
    assert lk["reference_threshold"] == pytest.approx(0.10)
    # every won deal above the 10% reference contributes its excess, including
    # the reference band itself (12% discount -> 0.02 excess). list_acv = 100k.
    # won deals: 16 @0.12 (excess .02) + 16 @0.17 (.07) + 16 @0.22 (.12)
    expected = 16 * 0.02 * 100_000 + 16 * 0.07 * 100_000 + 16 * 0.12 * 100_000
    assert lk["excess_vs_reference_won"] == pytest.approx(expected)
    assert lk["deals_above_reference"] == 48


def test_win_rate_by_band_is_ordered_and_complete():
    rows = _band_block("b10", 20, 0.12, 0.80) + _band_block("b00", 20, 0.02, 0.40)
    df = _build(rows)
    wb = metrics.win_rate_by_band(df)
    assert list(wb["discount_band"]) == ["0-5%", "10-15%"]
    assert wb.set_index("discount_band").loc["0-5%", "win_rate"] == pytest.approx(0.40)


def test_overview_counts_and_realization():
    df = _build([
        _won("O1", "A1", 100_000, 80_000),
        dict(opportunity_id="O2", account_id="A2", account_name="A2",
             outcome="closed_lost", list_acv=100_000.0, booked_acv=70_000.0),
    ])
    ov = metrics.overview(df)
    assert ov["opportunities"] == 2
    assert ov["won"] == 1
    assert ov["lost"] == 1
    assert ov["win_rate"] == pytest.approx(0.5)
    # realization is computed on WON business only
    assert ov["price_realization_won"] == pytest.approx(0.80)


def test_packaging_signal_flags_lagging_segment():
    """Rivera lens: a segment whose realization sits materially below the
    cross-segment median should be flagged as a packaging signal."""
    rows = []
    # Three segments of 4 won deals each, with realizations ~90, ~85, ~70%
    for i, (seg, real) in enumerate([("A", 0.90), ("B", 0.85), ("C", 0.70)]):
        for j in range(4):
            rows.append(dict(
                opportunity_id=f"O{seg}-{j}", account_id=f"AC-{seg}-{j}",
                account_name=f"AC-{seg}-{j}", outcome="closed_won",
                list_acv=100_000.0, booked_acv=100_000.0 * real,
                segment=seg,
            ))
    df = _build(rows)
    sigs = metrics.packaging_signals(df, min_deals=3, gap_pp=5.0)
    # C is the laggard — must be flagged. A is above the median, must NOT be.
    flagged_values = {s["value"] for s in sigs if s["dimension"] == "segment"}
    assert "C" in flagged_values
    assert "A" not in flagged_values


def test_trade_or_give_counts_off_policy_with_no_concession():
    """Simon-Kucher lens: off-policy won deals lacking BOTH a longer-than-
    median term AND a recorded approver are 'gave it away' deals."""
    rows = [
        # Reference deals to set the median term at 12.
        dict(opportunity_id="R1", account_id="R", account_name="R",
             outcome="closed_won", list_acv=100_000.0, booked_acv=95_000.0,
             term_months=12, approved_by=""),
        dict(opportunity_id="R2", account_id="R", account_name="R",
             outcome="closed_won", list_acv=100_000.0, booked_acv=95_000.0,
             term_months=12, approved_by=""),
        # Off-policy (25% discount):
        # 1) long term, no approver -> traded
        dict(opportunity_id="X1", account_id="X1", account_name="X1",
             outcome="closed_won", list_acv=100_000.0, booked_acv=75_000.0,
             term_months=36, approved_by=""),
        # 2) short term, approver -> traded
        dict(opportunity_id="X2", account_id="X2", account_name="X2",
             outcome="closed_won", list_acv=100_000.0, booked_acv=75_000.0,
             term_months=12, approved_by="MGR-01"),
        # 3 & 4) short term, no approver -> NOT traded (these are the "gave it away" ones)
        dict(opportunity_id="X3", account_id="X3", account_name="X3",
             outcome="closed_won", list_acv=100_000.0, booked_acv=75_000.0,
             term_months=12, approved_by=""),
        dict(opportunity_id="X4", account_id="X4", account_name="X4",
             outcome="closed_won", list_acv=100_000.0, booked_acv=70_000.0,
             term_months=12, approved_by=""),
    ]
    df = _build(rows)
    res = metrics.trade_or_give(df)
    assert res["deals"] == 2
    # Dollars discounted on the no-trade deals = 25k + 30k = 55k
    assert res["dollars"] == pytest.approx(55_000.0)
    assert res["off_policy_total"] == 4
