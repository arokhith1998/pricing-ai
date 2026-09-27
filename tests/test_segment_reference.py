"""Known-answer tests for segment-aware reference discounts.

2026-06-10 dry-run methodology fix: the headline excess must be the sum of
per-segment excess, each segment measured against its OWN win point where it
has sufficient data, with the global reference kept as a disclosed fallback
for thin segments and as a transparent secondary lens.
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


def _seg_block(prefix: str, segment: str, n: int, discount: float,
               win_rate: float) -> list[dict]:
    """n deals in one segment at a fixed discount, `win_rate` of them won."""
    list_acv, booked = 100_000.0, 100_000.0 * (1 - discount)
    n_won = round(n * win_rate)
    return [
        dict(opportunity_id=f"{prefix}-{i}", account_id=f"{prefix}-{i}",
             account_name=f"{prefix}-{i}",
             outcome="closed_won" if i < n_won else "closed_lost",
             list_acv=list_acv, booked_acv=booked, segment=segment)
        for i in range(n)
    ]


def _three_segment_book() -> pd.DataFrame:
    """ENT's win point is 10-15% while the global reference lands at 5% —
    exactly the dry-run scenario where a global reference overstates ENT.

    ENT (100 deals, 5 populated bands): sufficient, own reference = 10%.
    MM  (160 deals, 3 populated bands): sufficient, own reference = 5%.
    SMB (30 deals, 1 band): thin, must fall back to the global reference.
    """
    rows: list[dict] = []
    rows += _seg_block("e00", "ENT", 20, 0.02, 0.30)
    rows += _seg_block("e05", "ENT", 20, 0.07, 0.40)
    rows += _seg_block("e10", "ENT", 20, 0.12, 0.80)  # ENT win point
    rows += _seg_block("e15", "ENT", 20, 0.17, 0.80)
    rows += _seg_block("e20", "ENT", 20, 0.22, 0.80)
    rows += _seg_block("m00", "MM", 40, 0.02, 0.40)
    rows += _seg_block("m05", "MM", 80, 0.07, 0.85)   # MM win point
    rows += _seg_block("m10", "MM", 40, 0.12, 0.80)
    rows += _seg_block("s10", "SMB", 30, 0.12, 0.60)  # thin segment
    return _build(rows)


def test_sufficient_segments_get_own_reference_thin_falls_back():
    df = _three_segment_book()
    table = {r["segment"]: r for r in metrics.segment_reference_table(df)}
    g_rt = metrics.reference_discount(df)["reference_threshold"]
    assert g_rt == pytest.approx(0.05)  # the dry-run setup: global ref is low

    # ENT: 100 deals / 5 bands -> earns its own (higher) win point.
    assert table["ENT"]["basis"] == "own win point"
    assert table["ENT"]["reference_threshold"] == pytest.approx(0.10)
    assert table["ENT"]["deals"] == 100
    assert table["ENT"]["bands_populated"] == 5

    # MM: sufficient, own win point happens to equal the global one.
    assert table["MM"]["basis"] == "own win point"
    assert table["MM"]["reference_threshold"] == pytest.approx(0.05)
    assert table["MM"]["bands_populated"] == 3

    # SMB: 30 deals / 1 band -> global fallback, explicitly disclosed.
    assert table["SMB"]["basis"] == "global fallback (insufficient data)"
    assert table["SMB"]["reference_threshold"] == pytest.approx(g_rt)
    assert table["SMB"]["deals"] == 30
    assert table["SMB"]["bands_populated"] == 1


def test_headline_is_sum_of_per_segment_excess():
    df = _three_segment_book()
    lk = metrics.leakage(df)

    # Manual per-segment excess against each segment's own reference:
    # ENT (ref .10): won 16@.12 + 16@.17 + 16@.22 -> 16*(.02+.07+.12)*100k
    # MM  (ref .05): won 68@.07 + 32@.12          -> (68*.02 + 32*.07)*100k
    # SMB (ref .05 global fallback): won 18@.12   -> 18*.07*100k
    ent = 16 * (0.02 + 0.07 + 0.12) * 100_000
    mm = (68 * 0.02 + 32 * 0.07) * 100_000
    smb = 18 * 0.07 * 100_000
    assert lk["excess_vs_segment_reference_won"] == pytest.approx(ent + mm + smb)

    # And generically: headline == sum of per-segment excess computed
    # independently from the disclosed reference table.
    won = df[df["is_won"]]
    total = 0.0
    for r in lk["segment_references"]:
        sub = won[won["segment"] == r["segment"]]
        total += float(((sub["discount_pct"] - r["reference_threshold"])
                        .clip(lower=0.0) * sub["list_acv"]).sum())
    assert lk["excess_vs_segment_reference_won"] == pytest.approx(total)

    # The corrected headline is LOWER than the single-global-reference number
    # (ENT discounts up to its own win point no longer count as excess).
    assert (lk["excess_vs_segment_reference_won"]
            < lk["excess_vs_reference_won"])


def test_global_secondary_lens_is_still_computed_unchanged():
    """The methodology change must be transparent, not silent: the old global
    number stays in the dict, computed exactly as before."""
    df = _three_segment_book()
    lk = metrics.leakage(df)
    assert lk["reference_threshold"] == pytest.approx(0.05)
    # vs global .05: ENT won 8@.07+16@.12+16@.17+16@.22, MM 68@.07+32@.12,
    # SMB 18@.12 — every won deal contributes (discount - .05).
    expected = (
        (8 * 0.02 + 16 * 0.07 + 16 * 0.12 + 16 * 0.17) * 100_000   # ENT
        + (68 * 0.02 + 32 * 0.07) * 100_000                        # MM
        + 18 * 0.07 * 100_000                                      # SMB
    )
    assert lk["excess_vs_reference_won"] == pytest.approx(expected)


def test_blank_segment_deals_use_global_with_disclosure_row():
    df = _three_segment_book()
    extra = _build(_seg_block("x", "", 4, 0.22, 1.0))
    df = pd.concat([df, extra], ignore_index=True)
    table = {r["segment"]: r for r in metrics.segment_reference_table(df)}
    assert "(blank)" in table
    assert table["(blank)"]["deals"] == 4
    assert table["(blank)"]["basis"] == "global fallback (no segment value)"
    # Blank-segment won deals are measured against the global reference.
    lk = metrics.leakage(df)
    base = metrics.leakage(_three_segment_book())
    blank_excess = 4 * (0.22 - lk["reference_threshold"]) * 100_000
    assert (lk["excess_vs_segment_reference_won"]
            == pytest.approx(base["excess_vs_segment_reference_won"]
                             + blank_excess))


def test_without_segment_column_headline_degrades_to_global():
    rows = _three_segment_book().drop(columns=["segment"])
    assert metrics.segment_reference_table(rows) == []
    lk = metrics.leakage(rows)
    assert (lk["excess_vs_segment_reference_won"]
            == pytest.approx(lk["excess_vs_reference_won"]))
    assert lk["deals_above_segment_reference"] == lk["deals_above_reference"]
    assert lk["segment_references"] == []


def test_readout_discloses_references_and_secondary_lens(capsys):
    """The printed deliverable must show the per-segment reference table
    (with basis) and keep the global number as a labeled secondary lens."""
    res = diagnostic.analyze(_three_segment_book())
    diagnostic.print_report(res)
    out = capsys.readouterr().out
    assert "Excess vs segment references" in out
    assert "secondary lens, single global reference" in out
    assert "Reference discount by segment" in out
    assert "own win point" in out
    assert "global fallback (insufficient data)" in out
    # correlational caveat must survive the methodology change
    assert "correlational" in out


# --- PK-16: business_unit / product_line reference tables --------------------

def _bu_block(prefix: str, business_unit: str, n: int, discount: float,
             win_rate: float, segment: str = "ENT") -> list[dict]:
    """n deals in one business_unit (fixed segment) at a fixed discount."""
    list_acv, booked = 100_000.0, 100_000.0 * (1 - discount)
    n_won = round(n * win_rate)
    return [
        dict(opportunity_id=f"{prefix}-{i}", account_id=f"{prefix}-{i}",
             account_name=f"{prefix}-{i}",
             outcome="closed_won" if i < n_won else "closed_lost",
             list_acv=list_acv, booked_acv=booked, segment=segment,
             business_unit=business_unit)
        for i in range(n)
    ]


def _bu_book() -> pd.DataFrame:
    """One segment (ENT) split across two business units. BU-A repeats the
    exact win-curve shape the ENT block uses elsewhere in this file, so its
    own reference is known to land at 10% (10-15% band); BU-B is thin (one
    band) and must fall back."""
    rows: list[dict] = []
    rows += _bu_block("ba00", "BU-A", 20, 0.02, 0.30)
    rows += _bu_block("ba05", "BU-A", 20, 0.07, 0.40)
    rows += _bu_block("ba10", "BU-A", 20, 0.12, 0.80)  # BU-A win point
    rows += _bu_block("ba15", "BU-A", 20, 0.17, 0.80)
    rows += _bu_block("ba20", "BU-A", 20, 0.22, 0.80)
    rows += _bu_block("bb10", "BU-B", 30, 0.12, 0.60)  # thin
    return _build(rows)


def test_business_unit_table_mirrors_segment_sufficiency_bar():
    df = _bu_book()
    table = {r["business_unit"]: r for r in metrics.business_unit_reference_table(df)}
    g_rt = metrics.reference_discount(df)["reference_threshold"]

    assert table["BU-A"]["basis"] == "own win point"
    assert table["BU-A"]["reference_threshold"] == pytest.approx(0.10)
    assert table["BU-A"]["deals"] == 100
    assert table["BU-A"]["bands_populated"] == 5

    assert table["BU-B"]["basis"] == "global fallback (insufficient data)"
    assert table["BU-B"]["reference_threshold"] == pytest.approx(g_rt)
    assert table["BU-B"]["deals"] == 30


def test_product_line_table_mirrors_segment_sufficiency_bar():
    df = _bu_book().rename(columns={"business_unit": "product_line"})
    table = {r["product_line"]: r for r in metrics.product_line_reference_table(df)}
    assert table["BU-A"]["basis"] == "own win point"
    assert table["BU-A"]["reference_threshold"] == pytest.approx(0.10)


def test_per_deal_reference_prefers_business_unit_over_segment():
    """A deal's own BU reference (when earned) wins over its segment
    reference, which wins over global, even though every deal here shares
    the same segment (ENT)."""
    df = _bu_book()
    won = df[df["is_won"]]
    seg_rt = metrics.reference_discount(df)["reference_threshold"]
    seg_refs = metrics.segment_reference_table(df)
    ent_seg_threshold = {r["segment"]: r["reference_threshold"]
                        for r in seg_refs}["ENT"]

    thr = metrics._per_deal_reference(won, df, seg_rt, seg_refs)
    bu_a_thr = thr[won["business_unit"] == "BU-A"].to_numpy()
    bu_b_thr = thr[won["business_unit"] == "BU-B"].to_numpy()

    # BU-A earned its own (higher) reference -- every BU-A deal uses 10%,
    # not the blended ENT segment threshold.
    assert bu_a_thr == pytest.approx(0.10)
    # BU-B is thin: it falls back through to the segment's own reference
    # (ENT earned one from the combined 130-deal book), not straight to global.
    assert bu_b_thr == pytest.approx(ent_seg_threshold)


def test_hierarchy_slice_reference_reports_own_reference_and_excess():
    df = _bu_book()
    rows = {r["business_unit"]: r
           for r in metrics.hierarchy_slice_reference(df, "business_unit")
           .to_dict(orient="records")}
    assert rows["BU-A"]["reference_basis"] == metrics._BASIS_OWN
    assert rows["BU-A"]["reference_threshold"] == pytest.approx(0.10)
    # BU-A won deals: 16@.12(excess .02) + 16@.17(.07) + 16@.22(.12), *100k
    expected = (16 * 0.02 + 16 * 0.07 + 16 * 0.12) * 100_000
    assert rows["BU-A"]["excess_won"] == pytest.approx(expected)
    # BU-B did not earn its own BU reference; the fallback basis is disclosed.
    assert rows["BU-B"]["reference_basis"] != metrics._BASIS_OWN


def test_hierarchy_slice_reference_labels_dimensions_with_no_dedicated_table():
    """product_family has no dedicated reference table (PK-16 scoped BU and
    product_line only), so its slices always disclose the generic fallback
    label rather than silently reusing another dimension's basis string."""
    df = _bu_book().rename(columns={"business_unit": "product_family"})
    rows = metrics.hierarchy_slice_reference(df, "product_family")
    assert (rows["reference_basis"] == metrics._NO_DEDICATED_TABLE_BASIS).all()


def test_diagnostic_prints_hierarchy_slice_with_basis(capsys):
    df = _bu_book()
    diagnostic.print_report(diagnostic.analyze(df))
    out = capsys.readouterr().out
    assert "Hierarchy slice: business_unit" in out
    assert "did not" in out and "earn their own reference" in out
