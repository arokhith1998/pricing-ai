"""Known-answer tests for the leakage metrics (the trust-critical logic)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pricing import diagnostic, metrics
from pricing.ingest import enrich, ingest_frame_verbose, ingest_verbose, resolve_identity

ROOT = Path(__file__).resolve().parents[1]


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


def test_reference_band_median_discount_is_disclosed_not_applied():
    """Pricing-strategist F3: the band floor is a founder call, not an
    engineering one, so this fix does not move reference_threshold off the
    band floor -- it only discloses the alternative (the band's own observed
    median discount) alongside it, so it CAN be shown without shipping it."""
    rows = []
    rows += _band_block("b00", 20, 0.02, 0.40)
    rows += _band_block("b05", 20, 0.07, 0.50)
    rows += _band_block("b10", 20, 0.12, 0.80)  # every deal here discounts 12%
    rows += _band_block("b15", 20, 0.17, 0.80)
    rows += _band_block("b20", 20, 0.22, 0.80)
    df = _build(rows)

    ref = metrics.reference_discount(df, seed=0)
    # The shipped threshold is still the band FLOOR (10%), unchanged...
    assert ref["reference_threshold"] == pytest.approx(0.10)
    # ...while the alternative -- the band's own median discount (12%, since
    # every deal in the 10-15% band sits at exactly 12%) -- is disclosed
    # alongside it, not substituted in.
    assert ref["reference_band_median_discount"] == pytest.approx(0.12)


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


def test_reference_discount_insufficient_data_does_not_relax_floor():
    """2026-09-26 fix: a sparse book (no band clears the 15-deal floor) must
    return an explicit insufficient-data state, not silently relax the floor
    to 1 deal per band and manufacture a 0% reference."""
    rows = []
    # 40 deals spread across all 6 real discount bands, 6-7 deals each -- none
    # clears the 15-deal floor, even though 6 distinct bands have data.
    rows += _band_block("b00", 7, 0.02, 0.40)   # 0-5%
    rows += _band_block("b05", 7, 0.07, 0.50)   # 5-10%
    rows += _band_block("b10", 7, 0.12, 0.60)   # 10-15%
    rows += _band_block("b15", 7, 0.17, 0.60)   # 15-20%
    rows += _band_block("b20", 6, 0.22, 0.60)   # 20-25%
    rows += _band_block("b25", 6, 0.30, 0.60)   # 25%+
    df = _build(rows)
    assert len(df) == 40

    ref = metrics.reference_discount(df)
    assert ref["sufficient"] is False
    assert ref["basis"] == "insufficient data"
    assert ref["reference_threshold"] == 0.0
    assert ref["reference_band"] is None
    assert ref["reference_band_median_discount"] == 0.0
    # every band's raw count is disclosed, even though none clears the floor
    assert sum(ref["band_counts"].values()) == 40

    lk = metrics.leakage(df)
    # no headline dollar figure is manufactured off the collapsed 0% reference
    assert lk["excess_vs_reference_won"] == 0.0
    assert lk["deals_above_reference"] == 0
    assert lk["excess_vs_segment_reference_won"] == 0.0
    assert lk["deals_above_segment_reference"] == 0
    assert lk["excess_basis"] == "insufficient data"
    assert "Insufficient data" in lk["excess_disclosure"]
    assert lk["band_counts"]


def _insufficient_hierarchy_rows(prefix, n, discount, win_rate, segment="SMB",
                                 business_unit="BU-A", product_line="PL-A"):
    """Like _band_block, but carries segment/business_unit/product_line so the
    hierarchy-table and per-deal-reference paths have something to look up."""
    list_acv, booked = 100_000.0, 100_000.0 * (1 - discount)
    n_won = round(n * win_rate)
    rows = []
    for i in range(n):
        rows.append(dict(
            opportunity_id=f"{prefix}-{i}", account_id=f"{prefix}-{i}",
            account_name=f"{prefix}-{i}",
            outcome="closed_won" if i < n_won else "closed_lost",
            list_acv=list_acv, booked_acv=booked,
            segment=segment, business_unit=business_unit, product_line=product_line,
        ))
    return rows


def _42_deal_insufficient_book() -> pd.DataFrame:
    """42 deals across 5 real bands, none clearing the 15-deal floor (2026-09-26
    blocker fix reproduction case). Every deal shares one segment/BU/product
    line, so none of those slices can earn its own reference either."""
    rows = []
    rows += _insufficient_hierarchy_rows("b00", 8, 0.02, 0.40)
    rows += _insufficient_hierarchy_rows("b05", 8, 0.07, 0.50)
    rows += _insufficient_hierarchy_rows("b10", 8, 0.12, 0.60)
    rows += _insufficient_hierarchy_rows("b15", 9, 0.17, 0.60)
    rows += _insufficient_hierarchy_rows("b20", 9, 0.22, 0.60)
    df = _build(rows)
    assert len(df) == 42
    return df


def test_insufficient_book_propagates_through_every_downstream_consumer():
    """2026-09-26 blocker fix: a thin (42-deal) book must not manufacture a
    0% reference anywhere downstream of reference_discount(). Every consumer
    must disclose 'insufficient data' with a NaN threshold and 0 excess,
    never a confident number built off the sentinel 0.0 threshold."""
    df = _42_deal_insufficient_book()
    ref = metrics.reference_discount(df)
    assert ref["sufficient"] is False

    # _per_deal_reference: NaN thresholds when nothing (segment, BU, product
    # line) earned its own and the global fallback is itself NaN.
    won = df[df["is_won"]]
    thr = metrics._per_deal_reference(won, df, float("nan"))
    assert thr.isna().all()

    # top_leak_deals: an EMPTY frame with a basis column, not an investigate
    # list scored against a 0% threshold.
    tld = metrics.top_leak_deals(df)
    assert tld.empty
    assert "reference_basis" in tld.columns

    # Every hierarchy reference table: NaN threshold, "insufficient data" basis.
    for table in (metrics.segment_reference_table(df),
                 metrics.business_unit_reference_table(df),
                 metrics.product_line_reference_table(df)):
        assert table, "expected at least one row (the shared segment/BU/PL value)"
        row = table[0]
        assert row["basis"] == "insufficient data"
        assert pd.isna(row["reference_threshold"])
        assert row["reference_band"] is None

    # hierarchy_slice_reference: NaN threshold, 0 excess, disclosed basis.
    hs = metrics.hierarchy_slice_reference(df, "business_unit")
    row = hs.iloc[0]
    assert row["reference_basis"] == "insufficient data"
    assert row["excess_won"] == 0.0
    assert pd.isna(row["reference_threshold"])

    # policy_simulations: lever 1 marked non-computable with a disclosure,
    # not a silent $0 "nothing to hold back".
    sims = metrics.policy_simulations(df)
    lever1 = sims[0]
    assert lever1["held_back"] == 0.0
    assert lever1.get("non_computable") is True
    assert "disclosure" in lever1 and "insufficient" in lever1["disclosure"].lower()


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


def test_trade_or_give_deals_are_the_receipts():
    """trade_or_give_deals returns exactly the no-trade set behind the count,
    ranked by discount $ given away."""
    rows = [
        # Reference deal to set the median term at 12.
        dict(opportunity_id="R1", account_id="R", account_name="R",
             outcome="closed_won", list_acv=100_000.0, booked_acv=95_000.0,
             term_months=12, approved_by=""),
        # Off-policy (25-30%), short term, no approver -> the receipts.
        dict(opportunity_id="G1", account_id="G1", account_name="G1",
             outcome="closed_won", list_acv=100_000.0, booked_acv=75_000.0,
             term_months=12, approved_by=""),   # 25k given away
        dict(opportunity_id="G2", account_id="G2", account_name="G2",
             outcome="closed_won", list_acv=100_000.0, booked_acv=70_000.0,
             term_months=12, approved_by=""),   # 30k given away
        # Traded (approver) -> excluded.
        dict(opportunity_id="T1", account_id="T1", account_name="T1",
             outcome="closed_won", list_acv=100_000.0, booked_acv=75_000.0,
             term_months=12, approved_by="MGR-01"),
        # Traded (long term) -> excluded.
        dict(opportunity_id="T2", account_id="T2", account_name="T2",
             outcome="closed_won", list_acv=100_000.0, booked_acv=75_000.0,
             term_months=36, approved_by=""),
    ]
    df = _build(rows)
    deals = metrics.trade_or_give_deals(df)
    # only the no-trade deals, ranked by discount $ (G2 30k before G1 25k)
    assert list(deals["opportunity_id"]) == ["G2", "G1"]
    assert deals.iloc[0]["discount_amount"] == pytest.approx(30_000.0)
    # exactly the set the aggregate counts
    assert len(deals) == metrics.trade_or_give(df)["deals"]


def test_quarter_end_deals_are_the_qe_set():
    """quarter_end_deals returns only quarter-end won deals, by discount $."""
    rows = [
        dict(opportunity_id="Q1", account_id="Q1", account_name="Q1",
             outcome="closed_won", list_acv=100_000.0, booked_acv=70_000.0,
             segment="SMB", approved_by="",
             created_date=pd.Timestamp("2025-03-01"),
             close_date=pd.Timestamp("2025-03-31")),   # quarter end, 30k given
        dict(opportunity_id="Q2", account_id="Q2", account_name="Q2",
             outcome="closed_won", list_acv=100_000.0, booked_acv=80_000.0,
             segment="SMB", approved_by="",
             created_date=pd.Timestamp("2025-03-01"),
             close_date=pd.Timestamp("2025-03-29")),   # quarter end, 20k given
        dict(opportunity_id="N1", account_id="N1", account_name="N1",
             outcome="closed_won", list_acv=100_000.0, booked_acv=75_000.0,
             segment="SMB", approved_by="",
             created_date=pd.Timestamp("2025-02-01"),
             close_date=pd.Timestamp("2025-02-15")),   # mid-quarter, excluded
    ]
    df = _build(rows)
    deals = metrics.quarter_end_deals(df)
    assert list(deals["opportunity_id"]) == ["Q1", "Q2"]
    assert deals.iloc[0]["discount_amount"] == pytest.approx(30_000.0)


def test_policy_simulations_union_is_not_a_sum(monkeypatch):
    """2026-09-26 fix: a deal can be above its reference, off-policy, AND in
    the quarter-end window at once, so stacking (summing) the three levers
    double-counts it. policy_simulations must add a non-additive union entry
    whose held_back is strictly less than the sum of the three, computed as
    each overlapping deal's single largest lever figure, never the sum of its
    levers."""
    monkeypatch.setattr(
        metrics, "reference_discount",
        lambda df, **kw: {"reference_threshold": 0.10, "reference_band": "10-15%",
                          "peak_band": "10-15%", "peak_win_rate": 0.7,
                          "sufficient": True, "basis": "own win point",
                          "band_counts": {}})
    rows = [
        # D1 trips all three levers: over reference (.30 > .10), off-policy
        # (> .15), and quarter-end.
        dict(opportunity_id="D1", is_won=True, discount_pct=0.30, list_acv=100_000.0,
             booked_acv=70_000.0, discount_amount=30_000.0, segment="SMB",
             is_quarter_end=True),
        # D2: over reference and off-policy, not quarter-end.
        dict(opportunity_id="D2", is_won=True, discount_pct=0.20, list_acv=100_000.0,
             booked_acv=80_000.0, discount_amount=20_000.0, segment="SMB",
             is_quarter_end=False),
        # D3: quarter-end, but below reference and on-policy.
        dict(opportunity_id="D3", is_won=True, discount_pct=0.08, list_acv=100_000.0,
             booked_acv=92_000.0, discount_amount=8_000.0, segment="SMB",
             is_quarter_end=True),
        # D4: rest-of-quarter baseline deal.
        dict(opportunity_id="D4", is_won=True, discount_pct=0.02, list_acv=100_000.0,
             booked_acv=98_000.0, discount_amount=2_000.0, segment="SMB",
             is_quarter_end=False),
    ]
    df = pd.DataFrame(rows)
    sims = metrics.policy_simulations(df, policy_threshold=0.15)
    stacked = [s for s in sims if not s.get("non_additive")]
    union = next(s for s in sims if s.get("non_additive"))

    assert len(stacked) == 3
    assert union["non_additive"] is True
    assert union["union_value"] == pytest.approx(union["held_back"])
    stacked_sum = sum(s["held_back"] for s in stacked)
    assert stacked_sum == pytest.approx(30_000 + 20_000 + 19_000)
    # D1's single largest lever (reference, $20k) is counted once, not summed
    # across all three ($20k + $15k + $19k) -> union < the naive stacked sum.
    assert union["held_back"] == pytest.approx(30_000.0)
    assert union["held_back"] < stacked_sum
    assert union["deals_affected"] == 3  # D1, D2, D3 each trip >= one lever


# --- bootstrap repetition (2026-09-26 perf fix) ------------------------------

def test_diagnostic_analyze_bounds_reference_discount_calls(monkeypatch):
    """reference_discount() runs a 500-sample bootstrap; before this fix,
    diagnostic.analyze on the demo book called it ~153 times because
    hierarchy_slice_reference, defended_vs_investigate, trend_by_quarter, and
    policy_simulations each rebuilt the segment/BU/product-line reference
    tables independently instead of sharing the ones diagnostic.analyze
    already computes once."""
    df, report = ingest_verbose(ROOT / "data" / "synthetic" / "deals.csv")
    calls = {"n": 0}
    original = metrics.reference_discount

    def counted(df_arg, *a, **kw):
        calls["n"] += 1
        return original(df_arg, *a, **kw)

    monkeypatch.setattr(metrics, "reference_discount", counted)
    diagnostic.analyze(df, report)
    # Measured 19 on the current demo book (1 global + one bootstrap per
    # segment/business_unit/product_line/value_metric value that clears its
    # own sufficiency bar, plus segment_win_points' independent per-segment
    # pass): bounded by the number of distinct hierarchy values, not by deal
    # count or open-deal count, unlike the ~153 this replaces. 30 leaves
    # headroom for a slightly richer book without flaking.
    assert calls["n"] < 30, (
        f"reference_discount called {calls['n']} times in one diagnostic.analyze "
        "run; the shared global/segment/BU/product-line tables should bound "
        "this to a small, roughly constant number regardless of book size."
    )


def test_diagnostic_analyze_bounds_reference_discount_calls_with_deal_type(monkeypatch):
    """2026-09-27 fix (item 2): the demo CSV above has no deal_type/is_renewal
    column, so new_vs_renewal's old bug -- calling reference_discount(df)
    unconditionally instead of taking the caller's already-computed
    global_ref -- was invisible to the count test above. Add is_renewal here
    so new_vs_renewal actually runs, and pin that it reuses the shared global
    reference rather than recomputing it a second time."""
    raw = pd.read_csv(ROOT / "data" / "synthetic" / "deals.csv",
                      dtype=str, keep_default_na=False)
    raw["is_renewal"] = [i % 2 == 0 for i in range(len(raw))]
    df, report = ingest_frame_verbose(raw)
    calls = {"n": 0}
    original = metrics.reference_discount

    def counted(df_arg, *a, **kw):
        calls["n"] += 1
        return original(df_arg, *a, **kw)

    monkeypatch.setattr(metrics, "reference_discount", counted)
    diagnostic.analyze(df, report)
    # A book with deal_type adds at most a couple more own-reference
    # bootstraps (New / Renewal groups), never a second independent global
    # recompute; still bounded, not doubled.
    assert calls["n"] < 35, (
        f"reference_discount called {calls['n']} times in one diagnostic.analyze "
        "run on a book with deal_type; new_vs_renewal must reuse the shared "
        "global reference (threaded via global_ref), not recompute it."
    )


def test_packaging_signal_deals_returns_the_value_deals():
    """packaging_signal_deals returns only the won deals in the flagged value."""
    rows = [
        dict(opportunity_id="P1", account_id="P1", account_name="P1",
             outcome="closed_won", list_acv=100_000.0, booked_acv=70_000.0,
             segment="SMB", approved_by=""),          # SMB, 30k
        dict(opportunity_id="P2", account_id="P2", account_name="P2",
             outcome="closed_won", list_acv=100_000.0, booked_acv=80_000.0,
             segment="SMB", approved_by=""),          # SMB, 20k
        dict(opportunity_id="E1", account_id="E1", account_name="E1",
             outcome="closed_won", list_acv=100_000.0, booked_acv=90_000.0,
             segment="Enterprise", approved_by=""),   # other value, excluded
    ]
    df = _build(rows)
    deals = metrics.packaging_signal_deals(df, "segment", "SMB")
    assert list(deals["opportunity_id"]) == ["P1", "P2"]
    assert (deals["segment"] == "SMB").all()


# --- BU/product-line-over-segment precedence blocker (2026-09-27 fix) -------

def test_demo_book_segment_aware_headline_is_pinned():
    """Known-answer test for the demo book's headline number: sum of per-deal
    excess measured against each deal's own reference, segment applied first.

    Before this fix, business_unit and product_line references (applied over
    segment) outranked the Enterprise segment's real ~10% reference with a
    degenerate 0% reference earned by BU "Data" and three product lines, so
    56 of 180 Enterprise won deals were measured at 0% instead of 10% and the
    headline read $12.48M -- ABOVE the $11.22M global lens the sample page
    labels as overstating by design. Pinned to the last known-good value
    (also the bundled sample-fallback.json figure) within 1%."""
    df, report = ingest_verbose(ROOT / "data" / "synthetic" / "deals.csv")
    lk = metrics.leakage(df)
    headline = lk["excess_vs_segment_reference_won"]
    global_lens = lk["excess_vs_reference_won"]
    assert headline == pytest.approx(8_946_770.48, rel=0.01)
    # The methodology point the sample page makes must hold: the segment-aware
    # headline is LOWER than the global lens it is shown beside as overstating.
    assert headline < global_lens


def test_sample_fallback_json_headline_matches_the_live_demo_book():
    """web/src/data/sample-fallback.json is a bundled snapshot of GET /demo
    (api.shared.diagnostic_payload on the demo CSV), served when the FastAPI
    backend is unreachable. It must not silently drift from what the live
    engine actually computes -- that was exactly this blocker's second bug:
    the bundled file held the last-known-good $8.95M while the live,
    precedence-broken API answered $12.48M."""
    import json

    path = ROOT / "web" / "src" / "data" / "sample-fallback.json"
    bundled = json.loads(path.read_text(encoding="utf-8"))
    df, report = ingest_verbose(ROOT / "data" / "synthetic" / "deals.csv")
    live = metrics.leakage(df)
    assert (bundled["leakage"]["excess_vs_segment_reference_won"]
            == pytest.approx(live["excess_vs_segment_reference_won"], rel=0.01))
    assert (bundled["leakage"]["excess_vs_reference_won"]
            == pytest.approx(live["excess_vs_reference_won"], rel=0.01))


def test_no_slice_reference_of_zero_ever_outranks_a_sufficient_segment():
    """Direct precedence test: even if a business_unit or product_line table
    reports a 0.0 'own win point' (the degenerate case the band-floor fix
    prevents upstream, see test_band_floor_slice_falls_through_on_demo_book),
    _per_deal_reference must apply the segment's own sufficient reference
    LAST, so it always wins over a coarser 0.0."""
    rows = pd.DataFrame({
        "segment": ["Enterprise", "Enterprise", "SMB"],
        "business_unit": ["Data", "Data", "Data"],
        "product_line": ["Compute", "Compute", "Compute"],
    })
    seg_refs = [{"segment": "Enterprise", "reference_threshold": 0.10,
                "reference_band": "10-15%", "basis": metrics._BASIS_OWN,
                "deals": 300, "bands_populated": 4}]
    bu_refs = [{"business_unit": "Data", "reference_threshold": 0.0,
               "reference_band": "0-5%", "basis": metrics._BASIS_OWN,
               "deals": 600, "bands_populated": 6}]
    pl_refs = [{"product_line": "Compute", "reference_threshold": 0.0,
               "reference_band": "0-5%", "basis": metrics._BASIS_OWN,
               "deals": 300, "bands_populated": 6}]
    thr = metrics._per_deal_reference(rows, rows, 0.05, seg_refs, bu_refs, pl_refs)
    # Rows 0/1 (Enterprise) get the segment's 10%, not BU/product-line's 0%.
    assert thr.iloc[0] == pytest.approx(0.10)
    assert thr.iloc[1] == pytest.approx(0.10)
    # Row 2 (SMB, no segment reference earned) falls through to BU's 0.0,
    # since BU is still preferred over product_line and over the global 5%.
    assert thr.iloc[2] == pytest.approx(0.0)


def test_band_floor_slice_falls_through_on_demo_book():
    """On the real demo book, BU 'Data' and product lines 'Compute',
    'Streaming', 'Warehouse' each clear the sufficiency bar but their own
    win-point search lands on the cheapest real band (0-5%, threshold 0.0).
    They must be labeled 'band floor, not applied' and fall through to the
    global reference, never 'own win point' at a manufactured 0%."""
    df = ingest_verbose(ROOT / "data" / "synthetic" / "deals.csv")[0]
    g_ref = metrics.reference_discount(df)
    bu_table = metrics.business_unit_reference_table(df, global_ref=g_ref)
    pl_table = metrics.product_line_reference_table(df, global_ref=g_ref)
    for table in (bu_table, pl_table):
        for row in table:
            if row["basis"] == metrics._BASIS_OWN:
                assert row["reference_threshold"] > metrics._MIN_POSITIVE_BAND_EDGE
    bu_basis = {r["business_unit"]: r["basis"] for r in bu_table}
    pl_basis = {r["product_line"]: r["basis"] for r in pl_table}
    assert bu_basis["Data"] == metrics._BASIS_BAND_FLOOR
    for pl in ("Compute", "Streaming", "Warehouse"):
        assert pl_basis[pl] == metrics._BASIS_BAND_FLOOR
