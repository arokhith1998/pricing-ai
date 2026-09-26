"""Pricing diagnostic metrics — the business logic.

This module is the one that earns or loses trust, so every metric here is
defined explicitly and is unit-tested. Inputs are the enriched frame from
`ingest.ingest()`.

Leakage is viewed through three complementary lenses, weakest-claim to
strongest-claim:

  1. Gross discount $ (won)        — total list-to-booked giveback on won deals.
                                      Descriptive, not a problem by itself.
  2. Off-policy leakage $ (won)    — discount given *above the policy line* on
                                      won deals. A governance lens.
  3. Excess-vs-reference $ (won)   — discount given above the point where win
                                      rate stops improving. The analytically
                                      interesting lens: this discount bought no
                                      incremental win probability.

IMPORTANT — lens 3 is CORRELATIONAL, not causal. Bigger, harder, or more
competitive deals attract bigger discounts, so some "excess" is justified.
Treat it as a prioritized list of deals to investigate, not a refund figure.
This is the methodology to sanity-check with a pricing advisor before showing a
customer (see vault/Decisions/2026-05-26-kickoff-decisions.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pricing.schema import DEFAULT_POLICY_THRESHOLD, DISCOUNT_BANDS

_BAND_ORDER = [label for _, _, label in DISCOUNT_BANDS]
_BAND_EDGES = {label: lo for lo, _hi, label in DISCOUNT_BANDS}

# Optional hierarchy columns the diagnostic auto-slices by when present.
HIERARCHY_DIMENSIONS: tuple[str, ...] = (
    "business_unit", "product_line", "product_family", "sku",
)

# --- Segment-aware reference sufficiency (2026-06-10 dry-run follow-up) ------
# A segment earns its OWN reference discount (win point) only when its win-rate
# curve is actually estimable from its data:
#   * >= SEGMENT_REF_MIN_DEALS closed deals — the reference search bootstraps a
#     CI per band with a 15-deal floor; ~100 deals spread over the discount
#     bands is roughly the volume at which several bands clear that floor and
#     the per-band CIs stop being vacuously wide.
#   * >= SEGMENT_REF_MIN_BANDS populated real (>= 0%) bands, each at or above
#     the 15-deal floor — a "win point" needs a curve: a peak band plus cheaper
#     bands to walk down. One or two populated bands is a lump, not a curve.
# Segments below either bar fall back to the GLOBAL reference, and the readout
# discloses the fallback explicitly (basis column) rather than hiding it.
SEGMENT_REF_MIN_DEALS: int = 100
SEGMENT_REF_MIN_BANDS: int = 3
_BASIS_OWN = "own win point"
_BASIS_FALLBACK = "global fallback (insufficient data)"
_BASIS_NO_SEGMENT = "global fallback (no segment value)"


def _won(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["is_won"]]


def overview(df: pd.DataFrame) -> dict:
    """Headline numbers for the diagnostic."""
    won = _won(df)
    n = len(df)
    n_won = len(won)
    booked = float(won["booked_acv"].sum())
    list_won = float(won["list_acv"].sum())
    return {
        "opportunities": n,
        "won": n_won,
        "lost": n - n_won,
        "win_rate": (n_won / n) if n else 0.0,
        "resolved_accounts": int(df["resolved_account_id"].nunique()),
        "booked_acv_won": booked,
        "list_acv_won": list_won,
        # blended price realization on won business, $-weighted
        "price_realization_won": (booked / list_won) if list_won else 0.0,
        "avg_discount_won": float(won["discount_pct"].mean()) if n_won else 0.0,
    }


def realization_by(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    """$-weighted price realization and avg discount by any dimension (won deals).

    Empty / NaN values in the dimension are filtered out before grouping.
    """
    won = _won(df).copy()
    if dim not in won.columns:
        return pd.DataFrame(columns=[dim, "deals", "list_acv", "booked_acv",
                                     "avg_discount", "price_realization"])
    won[dim] = won[dim].astype(str).str.strip()
    won = won[~won[dim].str.lower().isin(("", "nan", "none", "null", "na"))]
    if won.empty:
        return pd.DataFrame(columns=[dim, "deals", "list_acv", "booked_acv",
                                     "avg_discount", "price_realization"])
    g = won.groupby(dim).agg(
        deals=("opportunity_id", "count"),
        list_acv=("list_acv", "sum"),
        booked_acv=("booked_acv", "sum"),
        avg_discount=("discount_pct", "mean"),
    )
    g["price_realization"] = g["booked_acv"] / g["list_acv"]
    return g.reset_index().sort_values("booked_acv", ascending=False)


def realization_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    """$-weighted price realization and discount by segment (won deals)."""
    return realization_by(df, "segment")


def present_hierarchy_dimensions(df: pd.DataFrame) -> list[str]:
    """Optional hierarchy columns populated with ≥2 distinct non-empty values."""
    out = []
    for d in HIERARCHY_DIMENSIONS:
        if d not in df.columns:
            continue
        vals = df[d].astype(str).str.strip().str.lower()
        non_missing = vals[~vals.isin(("", "nan", "none", "null", "na"))]
        if non_missing.nunique() >= 2:
            out.append(d)
    return out


def packaging_signals(df: pd.DataFrame, min_deals: int = 15,
                      gap_pp: float = 5.0) -> list[dict]:
    """Rivera's 'packaging-fence' lens.

    For each segment or hierarchy dimension, flag values whose price
    realization is materially BELOW that dimension's median. Deep discounting
    concentrated in one value of a structural dimension often signals a
    packaging / fence problem, not just a rep-discipline problem.
    """
    out: list[dict] = []
    dims = ["segment"] + present_hierarchy_dimensions(df)
    for dim in dims:
        rows = realization_by(df, dim)
        if rows.empty or len(rows) < 2:
            continue
        rows = rows[rows["deals"] >= min_deals]
        if len(rows) < 2:
            continue
        median = float(rows["price_realization"].median())
        for r in rows.itertuples():
            gap = median - float(r.price_realization)
            if gap >= gap_pp / 100.0:
                out.append({
                    "dimension": dim,
                    "value": str(getattr(r, dim)),
                    "price_realization": float(r.price_realization),
                    "median_realization": median,
                    "gap_pp": gap * 100.0,
                    "deals": int(r.deals),
                    "booked_acv": float(r.booked_acv),
                })
    out.sort(key=lambda x: x["gap_pp"], reverse=True)
    return out


def trade_or_give(df: pd.DataFrame) -> dict:
    """Simon-Kucher 'trade, don't give' lens.

    Among off-policy WON deals, how many had no trade-back recorded — i.e.
    neither a longer-than-median contract term nor a recorded approver. A
    policy-busting discount with neither commitment nor sign-off is the
    quintessential 'gave it away' deal.
    """
    won = _won(df)
    if won.empty or "off_policy" not in won.columns:
        return {"deals": 0, "dollars": 0.0, "median_term_months": 0,
                "off_policy_total": 0}
    off = won[won["off_policy"]]
    if off.empty:
        return {"deals": 0, "dollars": 0.0, "median_term_months": 0,
                "off_policy_total": 0}
    median_term = (float(won["term_months"].median())
                   if "term_months" in won.columns else 12.0)
    term = (off.get("term_months", pd.Series([0] * len(off), index=off.index))
            .fillna(0))
    long_term = term > median_term
    approver = (off.get("approved_by",
                        pd.Series([""] * len(off), index=off.index))
                .fillna("").astype(str).str.strip())
    has_approver = approver != ""
    no_trade = ~long_term & ~has_approver
    no_trade_rows = off[no_trade]
    return {
        "deals": int(len(no_trade_rows)),
        "dollars": float(no_trade_rows["discount_amount"].sum()),
        "median_term_months": float(median_term),
        "off_policy_total": int(len(off)),
    }


def trade_or_give_deals(df: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    """The actual off-policy won deals that traded nothing for the discount.

    The receipts behind `trade_or_give()`: identical mask (off-policy won deals
    with neither a longer-than-median term nor a recorded approver), ranked by
    the discount $ given away. Showing these makes the aggregate claim auditable
    deal by deal rather than asked to be taken on trust.
    """
    cols = ["opportunity_id", "resolved_account_name", "segment", "list_acv",
            "booked_acv", "discount_pct", "discount_amount", "term_months"]
    won = _won(df)
    if won.empty or "off_policy" not in won.columns:
        return pd.DataFrame(columns=cols)
    off = won[won["off_policy"]]
    if off.empty:
        return pd.DataFrame(columns=cols)
    median_term = (float(won["term_months"].median())
                   if "term_months" in won.columns else 12.0)
    term = (off.get("term_months", pd.Series([0] * len(off), index=off.index))
            .fillna(0))
    long_term = term > median_term
    approver = (off.get("approved_by",
                        pd.Series([""] * len(off), index=off.index))
                .fillna("").astype(str).str.strip())
    no_trade = ~long_term & (approver == "")
    rows = off[no_trade]
    if rows.empty:
        return pd.DataFrame(columns=cols)
    keep = [c for c in cols if c in rows.columns]
    return rows.sort_values("discount_amount", ascending=False).head(n)[keep]


_FINDING_DEAL_COLS = ["opportunity_id", "resolved_account_name", "segment",
                      "list_acv", "booked_acv", "discount_pct", "discount_amount"]


def quarter_end_deals(df: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    """The quarter-end won deals with the deepest discounts — the receipts
    behind the quarter-end effect, ranked by discount $ given."""
    won = _won(df)
    if won.empty or "is_quarter_end" not in won.columns:
        return pd.DataFrame(columns=_FINDING_DEAL_COLS)
    qe = won[won["is_quarter_end"]]
    if qe.empty:
        return pd.DataFrame(columns=_FINDING_DEAL_COLS)
    keep = [c for c in _FINDING_DEAL_COLS if c in qe.columns]
    return qe.sort_values("discount_amount", ascending=False).head(n)[keep]


def packaging_signal_deals(df: pd.DataFrame, dimension: str, value: str,
                           n: int = 6) -> pd.DataFrame:
    """Won deals behind one packaging signal: those in the flagged dimension
    value, ranked by discount $ given. The receipts for a fence/packaging flag."""
    won = _won(df)
    if dimension not in won.columns:
        return pd.DataFrame(columns=_FINDING_DEAL_COLS)
    sub = won[won[dimension].astype(str).str.strip() == str(value)]
    if sub.empty:
        return pd.DataFrame(columns=_FINDING_DEAL_COLS)
    keep = [c for c in _FINDING_DEAL_COLS if c in sub.columns]
    return sub.sort_values("discount_amount", ascending=False).head(n)[keep]


def win_rate_by_band(df: pd.DataFrame) -> pd.DataFrame:
    """Win rate, deal counts, and avg discount per discount band (all deals)."""
    g = df.groupby("discount_band").agg(
        deals=("opportunity_id", "count"),
        won=("is_won", "sum"),
        avg_discount=("discount_pct", "mean"),
    )
    g["win_rate"] = g["won"] / g["deals"]
    g = g.reindex(_BAND_ORDER).dropna(subset=["deals"])
    return g.reset_index().rename(columns={"index": "discount_band"})


def reference_discount(df: pd.DataFrame, ci: float = 0.90, n_boot: int = 500,
                       seed: int = 0, min_deals: int = 15) -> dict:
    """Cheapest discount level that is statistically as good as the best band.

    Win rate per band is noisy, so we bootstrap a confidence interval on each
    band's win rate, then pick the *cheapest* band whose win rate is not
    significantly below the peak band — its bootstrap mean clears the peak
    band's lower CI bound. Discount above that level is candidate excess: it did
    not buy a statistically distinguishable win-rate gain. (Replaces the earlier
    point-estimate rule flagged by cross-model review as statistically naive.)

    Sufficiency (2026-09-26 fix): a reference is only estimable when at least
    SEGMENT_REF_MIN_BANDS real (non-negative) discount bands each clear
    `min_deals` closed deals — the same bar segment_reference_table already
    uses to decide whether a slice earns its own reference. Below that bar this
    used to silently relax the floor to 1 deal per band, which let a sparse
    book manufacture a 0% reference and read all of its discount as leakage.
    Now it returns an explicit insufficient-data state instead: `sufficient`
    is False, `basis` is "insufficient data", `reference_threshold` is 0.0, and
    `band_counts` carries every band's deal count so the caller can disclose
    why. Callers (leakage(), defended_vs_investigate()) must not headline a
    dollar figure off that 0.0 threshold.
    """
    work = df[["discount_band", "is_won"]]
    rng = np.random.default_rng(seed)
    lo_q, hi_q = (1 - ci) / 2, 1 - (1 - ci) / 2
    band_counts = {str(k): int(v) for k, v in work["discount_band"].value_counts().items()}

    def _band_stats(threshold: int) -> dict:
        out = {}
        for label in _BAND_ORDER:
            arr = work.loc[work["discount_band"] == label, "is_won"].to_numpy()
            if len(arr) < threshold:
                continue
            boot = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
            out[label] = (float(arr.mean()), float(np.quantile(boot, lo_q)),
                          float(np.quantile(boot, hi_q)), int(len(arr)))
        return out

    stats = _band_stats(min_deals)
    edges = {label: lo for lo, _hi, label in DISCOUNT_BANDS}
    # The reference discount is a discount POLICY level, so only real (>=0) bands
    # are candidates. Above-list deals (negative discount) are a pricing-power
    # signal — they still appear in band_win_rate_ci for the chart, but must
    # never be chosen as the reference (its threshold would be negative).
    pos_order = [lbl for lbl in _BAND_ORDER if edges.get(lbl, 0.0) >= 0.0]
    candidates = {k: v for k, v in stats.items() if edges.get(k, 0.0) >= 0.0}

    if len(candidates) < SEGMENT_REF_MIN_BANDS:
        return {
            "reference_threshold": 0.0,
            "reference_band": None,
            "peak_win_rate": 0.0,
            "peak_band": None,
            "peak_win_rate_ci": (0.0, 0.0),
            "band_win_rate_ci": {k: (v[0], v[1], v[2]) for k, v in stats.items()},
            "basis": "insufficient data",
            "sufficient": False,
            "band_counts": band_counts,
            "reference_band_median_discount": 0.0,
        }

    peak_band = max(candidates, key=lambda k: candidates[k][0])
    peak_mean, peak_lo, peak_hi, _ = candidates[peak_band]
    reference_band = peak_band
    for label in pos_order:            # cheapest real band not significantly < peak
        if label in candidates and candidates[label][0] >= peak_lo:
            reference_band = label
            break
    # Alternative threshold a founder could choose instead of the band floor
    # (pricing-strategist F3): the observed median discount of ALL deals inside
    # the reference band, rather than the band's lower edge. Not applied as the
    # threshold here — that is a founder call, not an engineering one — but
    # disclosed so the alternative can be shown alongside the shipped number.
    band_discounts = df.loc[df["discount_band"] == reference_band, "discount_pct"]
    median_discount = float(band_discounts.median()) if len(band_discounts) else 0.0
    return {
        "reference_threshold": float(edges[reference_band]),
        "reference_band": reference_band,
        "peak_win_rate": peak_mean,
        "peak_band": peak_band,
        "peak_win_rate_ci": (peak_lo, peak_hi),
        "band_win_rate_ci": {k: (v[0], v[1], v[2]) for k, v in stats.items()},
        "basis": _BASIS_OWN,
        "sufficient": True,
        "band_counts": band_counts,
        "reference_band_median_discount": median_discount,
    }


def _populated_real_bands(df: pd.DataFrame, floor: int = 15) -> int:
    """Number of non-negative discount bands holding at least `floor` deals.

    Negative ("above list") bands are excluded: they can never be a reference
    candidate (see reference_discount), so they contribute nothing to whether a
    win point is estimable.
    """
    if "discount_band" not in df.columns:
        return 0
    counts = df.groupby("discount_band").size()
    return int(sum(
        1 for label, c in counts.items()
        if c >= floor and _BAND_EDGES.get(label, -1.0) >= 0.0
    ))


def segment_reference_table(df: pd.DataFrame,
                            min_deals: int = SEGMENT_REF_MIN_DEALS,
                            min_bands: int = SEGMENT_REF_MIN_BANDS) -> list[dict]:
    """Per-segment reference discounts, with the basis of each disclosed.

    The 2026-06-10 dry-run exposed the methodology gap: Enterprise's win point
    sits at 10-15% while the global reference is 5%, so measuring Enterprise
    excess against the global 5% overstates it (those discounts DO buy wins up
    to the segment's own win point). Each segment with sufficient data (see
    SEGMENT_REF_MIN_DEALS / SEGMENT_REF_MIN_BANDS) gets its own reference from
    the same win-point logic; thin segments fall back to the global reference
    WITH an explicit basis disclosure, never silently.

    Returns one row per segment value (plus a "(blank)" row when deals carry no
    segment): segment, deals, bands_populated, reference_threshold,
    reference_band, basis.
    """
    out: list[dict] = []
    if "segment" not in df.columns or df.empty:
        return out
    g_ref = reference_discount(df)
    seg = df["segment"].astype(str).str.strip()
    blank = seg.str.lower().isin(("", "nan", "none", "null", "na"))
    for value in sorted(seg[~blank].unique()):
        sub = df[seg == value]
        bands = _populated_real_bands(sub)
        if len(sub) >= min_deals and bands >= min_bands:
            ref, basis = reference_discount(sub), _BASIS_OWN
        else:
            ref, basis = g_ref, _BASIS_FALLBACK
        out.append({
            "segment": value,
            "deals": int(len(sub)),
            "bands_populated": bands,
            "reference_threshold": float(ref["reference_threshold"]),
            "reference_band": ref["reference_band"],
            "basis": basis,
        })
    n_blank = int(blank.sum())
    if n_blank:
        out.append({
            "segment": "(blank)",
            "deals": n_blank,
            "bands_populated": 0,
            "reference_threshold": float(g_ref["reference_threshold"]),
            "reference_band": g_ref["reference_band"],
            "basis": _BASIS_NO_SEGMENT,
        })
    return out


def value_metric_reference_table(df: pd.DataFrame,
                                 min_deals: int = SEGMENT_REF_MIN_DEALS,
                                 min_bands: int = SEGMENT_REF_MIN_BANDS) -> list[dict]:
    """Per-value-metric reference discounts, with the basis of each disclosed.

    A discount percent does not mean the same thing across value metrics: a seat
    discount is a straight price concession, while a consumption or hybrid
    discount blends rate and contract structure. Pooling seats, consumption, and
    hybrid into one win point mixes incommensurable quantities, so the pooled
    reference is a weighted average of curves that should be read apart (Campbell:
    the value metric is the whole game). Each value_metric with sufficient data
    (SEGMENT_REF_MIN_DEALS / SEGMENT_REF_MIN_BANDS) earns its own win point from
    the same logic as reference_discount; thin metrics fall back to the global
    reference WITH an explicit basis disclosure, never silently.

    Additive: the pooled reference_discount and segment table are unchanged; this
    is a parallel cut a deal desk can read alongside them. Returns one row per
    value_metric value (plus a "(blank)" row when deals carry no value metric):
    value_metric, deals, bands_populated, reference_threshold, reference_band,
    basis.
    """
    out: list[dict] = []
    if "value_metric" not in df.columns or df.empty:
        return out
    g_ref = reference_discount(df)
    vm = df["value_metric"].astype(str).str.strip()
    blank = vm.str.lower().isin(("", "nan", "none", "null", "na"))
    for value in sorted(vm[~blank].unique()):
        sub = df[vm == value]
        bands = _populated_real_bands(sub)
        if len(sub) >= min_deals and bands >= min_bands:
            ref, basis = reference_discount(sub), _BASIS_OWN
        else:
            ref, basis = g_ref, _BASIS_FALLBACK
        out.append({
            "value_metric": value,
            "deals": int(len(sub)),
            "bands_populated": bands,
            "reference_threshold": float(ref["reference_threshold"]),
            "reference_band": ref["reference_band"],
            "basis": basis,
        })
    n_blank = int(blank.sum())
    if n_blank:
        out.append({
            "value_metric": "(blank)",
            "deals": n_blank,
            "bands_populated": 0,
            "reference_threshold": float(g_ref["reference_threshold"]),
            "reference_band": g_ref["reference_band"],
            "basis": _BASIS_NO_SEGMENT,
        })
    return out


def _per_deal_reference(rows: pd.DataFrame, df: pd.DataFrame,
                        global_rt: float,
                        seg_refs: list[dict] | None = None) -> pd.Series:
    """Reference threshold per deal: the deal's segment reference where the
    segment earned one, the global reference otherwise (incl. blank segments)."""
    if seg_refs is None:
        seg_refs = segment_reference_table(df)
    if seg_refs and "segment" in rows.columns:
        thr_map = {r["segment"]: r["reference_threshold"] for r in seg_refs}
        thr = rows["segment"].astype(str).str.strip().map(thr_map)
        return thr.fillna(global_rt)
    return pd.Series(global_rt, index=rows.index, dtype="float64")


def leakage(df: pd.DataFrame,
            policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> dict:
    """The three leakage lenses, in dollars, on won deals.

    Since the 2026-06-10 dry-run, lens 3 comes in two flavors:
      * segment-aware (THE headline): sum of per-segment excess, each segment
        measured against its own reference where it earned one (see
        segment_reference_table). Lower and more defensible.
      * single global reference (secondary lens, kept so the methodology
        change is transparent, not silent — and because downstream consumers
        read these keys). Overstates segments whose win point sits above the
        global reference.

    2026-09-26 fix: when the book is too sparse for reference_discount() to
    estimate a reference at all (`sufficient` is False), this no longer lets a
    0.0 threshold masquerade as "all discount is excess". Both dollar lenses
    are returned as 0.0, `excess_basis` is "insufficient data", and
    `excess_disclosure` carries a human-readable reason plus band counts.
    """
    won = _won(df)
    gross = float(won["discount_amount"].sum())

    over_policy = (won["discount_pct"] - policy_threshold).clip(lower=0.0)
    off_policy = float((over_policy * won["list_acv"]).sum())

    ref = reference_discount(df)
    rt = ref["reference_threshold"]
    booked = float(won["booked_acv"].sum())

    if not ref.get("sufficient", True):
        band_counts = ref.get("band_counts", {})
        disclosure = (
            "Insufficient data for a reference discount: no "
            f"{SEGMENT_REF_MIN_BANDS} real discount bands each clear 15 closed "
            "deals. Band counts: "
            + ", ".join(f"{k}={v}" for k, v in sorted(band_counts.items()))
            + ". Collect more closed deals before quoting an excess-discount "
              "figure."
        )
        return {
            "policy_threshold": policy_threshold,
            "gross_discount_won": gross,
            "off_policy_leakage_won": off_policy,
            "reference_threshold": 0.0,
            "reference_band": None,
            "excess_vs_reference_won": 0.0,
            "deals_above_reference": 0,
            "excess_pct_of_booked": 0.0,
            "segment_references": [],
            "excess_vs_segment_reference_won": 0.0,
            "deals_above_segment_reference": 0,
            "excess_segment_pct_of_booked": 0.0,
            "excess_basis": "insufficient data",
            "excess_disclosure": disclosure,
            "band_counts": band_counts,
        }

    over_ref = (won["discount_pct"] - rt).clip(lower=0.0)
    excess = float((over_ref * won["list_acv"]).sum())
    n_excess = int((won["discount_pct"] > rt).sum())

    # Segment-aware headline: each won deal measured against its own segment's
    # reference. Degrades to the global numbers when there is no segment column.
    seg_refs = segment_reference_table(df)
    thr = _per_deal_reference(won, df, rt, seg_refs)
    over_seg = (won["discount_pct"] - thr).clip(lower=0.0)
    excess_seg = float((over_seg * won["list_acv"]).sum())
    n_excess_seg = int((won["discount_pct"] > thr).sum())

    return {
        "policy_threshold": policy_threshold,
        "gross_discount_won": gross,
        "off_policy_leakage_won": off_policy,
        # Single-global-reference lens. Key names unchanged on purpose:
        # copilot/assist/app/web extractors read them.
        "reference_threshold": rt,
        "reference_band": ref["reference_band"],
        "excess_vs_reference_won": excess,
        "deals_above_reference": n_excess,
        "excess_pct_of_booked": (excess / booked) if booked else 0.0,
        # Segment-aware lens — the headline excess (sum of per-segment excess,
        # each against its own reference) + the disclosure table behind it.
        "segment_references": seg_refs,
        "excess_vs_segment_reference_won": excess_seg,
        "deals_above_segment_reference": n_excess_seg,
        "excess_segment_pct_of_booked": (excess_seg / booked) if booked else 0.0,
        "excess_basis": ref.get("basis", _BASIS_OWN),
        "excess_disclosure": "",
        "band_counts": ref.get("band_counts", {}),
    }


def defended_vs_investigate(df: pd.DataFrame,
                            policy_threshold: float = DEFAULT_POLICY_THRESHOLD,
                            ) -> dict:
    """Sales-friendly split of won deals: discount earned vs discount worth investigating.

    The expert-review framing (2026-05-30): "We help reps stop giving discount
    where it does not change win probability, AND defend the discounts that do."
    The leakage lenses tell only the second half of that story. This function
    surfaces both sides so sales sees the work the discounting actually earned.

    Split rule (deliberately conservative), evaluated per deal against
    `_per_deal_reference` (2026-09-26 fix — this used to use the single global
    reference while leakage() and top_leak_deals used the per-deal one, so a
    CFO reconciling this section against the headline found they disagreed;
    `investigate_deals` now equals `deals_above_segment_reference` exactly):
      - DEFENDED  : won deals where discount_pct <= the deal's own reference
                    (sat in or below the band where win rate had room to
                    move; the discount plausibly bought the win)
      - INVESTIGATE: won deals where discount_pct > the deal's own reference
                    (gave more discount than the win curve required — these
                    are the deals worth a retrospective review)

    The single global reference is kept as a labeled secondary lens
    (defended_value_global / investigate_value_global), the same transparency
    discipline as leakage()'s excess_vs_reference_won. `reference_basis`
    discloses whether the split used a per-deal (segment-aware) reference or
    fell back to a single global one (no segment column, or insufficient data).

    Returns booked-value totals + deal counts for each bucket. Pure function,
    no LLM, no assumed "recovery rate" — just the split.
    """
    empty = {
        "reference_threshold": 0.0, "reference_basis": "insufficient data",
        "defended_value": 0.0, "defended_deals": 0,
        "investigate_value": 0.0, "investigate_deals": 0,
        "defended_pct_of_booked": 0.0,
        "defended_value_global": 0.0, "investigate_value_global": 0.0,
    }
    won = _won(df)
    if won.empty:
        return empty
    ref = reference_discount(df)
    rt = float(ref["reference_threshold"])

    if not ref.get("sufficient", True):
        out = dict(empty)
        out["reference_threshold"] = rt
        return out

    seg_refs = segment_reference_table(df)
    thr = _per_deal_reference(won, df, rt, seg_refs)
    defended_mask = won["discount_pct"] <= thr
    defended_value = float(won.loc[defended_mask, "booked_acv"].sum())
    investigate_value = float(won.loc[~defended_mask, "booked_acv"].sum())
    booked_total = defended_value + investigate_value

    # Secondary: single global reference, same transparency discipline as
    # leakage()'s excess_vs_reference_won.
    global_defended_mask = won["discount_pct"] <= rt
    defended_value_global = float(won.loc[global_defended_mask, "booked_acv"].sum())
    investigate_value_global = float(won.loc[~global_defended_mask, "booked_acv"].sum())

    basis = "segment-aware (per deal)" if seg_refs else ref.get("basis", _BASIS_OWN)
    return {
        "reference_threshold": rt,
        "reference_basis": basis,
        "defended_value": defended_value,
        "defended_deals": int(defended_mask.sum()),
        "investigate_value": investigate_value,
        "investigate_deals": int((~defended_mask).sum()),
        "defended_pct_of_booked": (defended_value / booked_total) if booked_total else 0.0,
        "defended_value_global": defended_value_global,
        "investigate_value_global": investigate_value_global,
    }


def quarter_end_effect(df: pd.DataFrame) -> dict:
    """Compare discounting in the quarter-end window vs the rest (won deals)."""
    won = _won(df)
    if "is_quarter_end" not in won.columns or won.empty:
        return {}
    qe = won[won["is_quarter_end"]]
    rest = won[~won["is_quarter_end"]]
    qe_disc = float(qe["discount_pct"].mean()) if len(qe) else 0.0
    rest_disc = float(rest["discount_pct"].mean()) if len(rest) else 0.0
    # extra discount $ attributable to the quarter-end lift on QE deals
    attributable = float(((qe["discount_pct"] - rest_disc).clip(lower=0.0)
                          * qe["list_acv"]).sum())
    return {
        "qe_deals": len(qe),
        "qe_avg_discount": qe_disc,
        "rest_avg_discount": rest_disc,
        "lift": qe_disc - rest_disc,
        "attributable_discount_won": attributable,
    }


def rep_discipline(df: pd.DataFrame, min_deals: int = 10) -> pd.DataFrame:
    """Avg discount and win rate by rep (won deals for discount), flag outliers.

    A high discount with no win-rate premium is the rep-level leakage signal.
    """
    if "rep_id" not in df.columns:
        return pd.DataFrame()
    won = _won(df)
    disc = won.groupby("rep_id").agg(
        won_deals=("opportunity_id", "count"),
        avg_discount=("discount_pct", "mean"),
        booked_acv=("booked_acv", "sum"),
    )
    wr = df.groupby("rep_id").agg(
        total_deals=("opportunity_id", "count"),
        win_rate=("is_won", "mean"),
    )
    out = disc.join(wr, how="outer")
    out = out[out["won_deals"].fillna(0) >= min_deals]
    if out.empty:
        return out.reset_index()
    median = out["avg_discount"].median()
    out["discount_vs_median"] = out["avg_discount"] - median
    return out.reset_index().sort_values("avg_discount", ascending=False)


def governance_gaps(df: pd.DataFrame) -> dict:
    """Off-policy discounts with no recorded approver (won deals)."""
    won = _won(df)
    gaps = won[won.get("off_policy_unapproved", False)]
    return {
        "off_policy_won": int(won["off_policy"].sum()) if "off_policy" in won else 0,
        "off_policy_unapproved_won": int(len(gaps)),
        "unapproved_discount_dollars": float(gaps["discount_amount"].sum()) if len(gaps) else 0.0,
    }


def top_leak_deals(df: pd.DataFrame, n: int = 15,
                   policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> pd.DataFrame:
    """The won deals with the most excess discount $ — the investigate-first
    list. Excess is segment-aware (each deal vs its segment's own reference)
    so the receipts agree with the headline; without a segment column it falls
    back to the global reference."""
    won = _won(df).copy()
    rt = reference_discount(df)["reference_threshold"]
    thr = _per_deal_reference(won, df, rt)
    won["excess_discount_dollars"] = (
        (won["discount_pct"] - thr).clip(lower=0.0) * won["list_acv"]
    )
    cols = ["opportunity_id", "resolved_account_name", "segment",
            "business_unit", "product_line", "product_family", "sku",
            "rep_id", "list_acv", "booked_acv", "discount_pct",
            "competitor_present", "is_quarter_end", "off_policy_unapproved",
            "excess_discount_dollars"]
    cols = [c for c in cols if c in won.columns]
    return won.sort_values("excess_discount_dollars", ascending=False).head(n)[cols]


# --- Customer wishlist (2026-06-10 dry-run): trend, cuts, so-what ------------

def trend_by_quarter(df: pd.DataFrame, min_deals: int = 10) -> pd.DataFrame:
    """Realization, win rate, and excess-vs-reference leakage by close quarter.

    The first question a CFO asks: is leakage getting better or worse? Since
    2026-09-26, excess is measured against each deal's own per-deal reference
    (`_per_deal_reference`: segment, else the deal's BU or product line where
    one earned its own reference, else global) — the same reference leakage()
    and top_leak_deals use, so this section reconciles with the headline
    instead of quoting a third basis. The single global reference is kept as
    `excess_won_global` (a property of the whole book, comparable quarter to
    quarter on its own terms) so the methodology change is transparent, not
    silent. Sparse quarters (< min_deals) are dropped rather than shown as
    noise. When the book overall is too sparse for ANY reference
    (`reference_discount` returns `sufficient=False`), every quarter's excess
    is reported as 0 with `excess_basis` disclosing why rather than charging
    the full discount as excess off a collapsed 0% threshold.
    """
    cols = ["quarter", "deals", "won", "win_rate", "booked_acv",
            "price_realization", "excess_won", "excess_pct_of_booked",
            "excess_won_global", "excess_basis"]
    if "quarter" not in df.columns:
        return pd.DataFrame(columns=cols)
    ref = reference_discount(df)
    rt = ref["reference_threshold"]
    sufficient = ref.get("sufficient", True)
    excess_basis = ref.get("basis", _BASIS_OWN)
    seg_refs = segment_reference_table(df)
    q = df["quarter"].astype(str).str.strip()
    work = df[q.ne("") & ~q.str.lower().isin(("nan", "none", "nat"))]
    out = []
    for quarter in sorted(work["quarter"].dropna().unique()):
        g = work[work["quarter"] == quarter]
        if len(g) < min_deals:
            continue
        won = _won(g)
        booked = float(won["booked_acv"].sum())
        list_won = float(won["list_acv"].sum())
        if not sufficient:
            excess, excess_global = 0.0, 0.0
        else:
            thr = _per_deal_reference(won, df, rt, seg_refs)
            excess = float(((won["discount_pct"] - thr).clip(lower=0.0)
                            * won["list_acv"]).sum())
            excess_global = float(((won["discount_pct"] - rt).clip(lower=0.0)
                                  * won["list_acv"]).sum())
        out.append({
            "quarter": str(quarter),
            "deals": int(len(g)),
            "won": int(len(won)),
            "win_rate": (len(won) / len(g)) if len(g) else 0.0,
            "booked_acv": booked,
            "price_realization": (booked / list_won) if list_won else 0.0,
            "excess_won": excess,
            "excess_pct_of_booked": (excess / booked) if booked else 0.0,
            "excess_won_global": excess_global,
            "excess_basis": excess_basis,
        })
    return pd.DataFrame(out, columns=cols)


def segment_win_points(df: pd.DataFrame, min_deals: int = 30) -> list[dict]:
    """Each segment's own win point. Enterprise and SMB curves differ, so a
    single global reference hides where the real saturation is per segment."""
    out: list[dict] = []
    if "segment" not in df.columns:
        return out
    for seg in sorted(df["segment"].dropna().astype(str).unique()):
        if not seg or seg.lower() in ("nan", "none", ""):
            continue
        g = df[df["segment"] == seg]
        if len(g) < min_deals:
            continue
        rd = reference_discount(g)
        out.append({
            "segment": seg,
            "deals": int(len(g)),
            "reference_band": rd["reference_band"],
            "peak_band": rd["peak_band"],
            "peak_win_rate": float(rd["peak_win_rate"]),
        })
    return out


def policy_simulations(df: pd.DataFrame,
                       policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> list[dict]:
    """Three concrete policies and the discount $ each would have held back on
    won deals, so '$X excess' arrives with a next action attached.

    Correlational, not a guarantee: some discount was needed to win, so each
    figure is an UPPER BOUND on what the policy could have retained, not a
    promised saving. Every dollar here reuses an existing leakage lens.
    """
    won = _won(df)
    if won.empty:
        return []
    rt = reference_discount(df)["reference_threshold"]
    qe = quarter_end_effect(df)

    def held(threshold) -> tuple[float, int]:
        over = (won["discount_pct"] - threshold).clip(lower=0.0)
        return float((over * won["list_acv"]).sum()), int((won["discount_pct"] > threshold).sum())

    # Lever 1 mirrors the (segment-aware) headline: hold each segment at its
    # own reference win point. Without a segment column this equals the global.
    ref_held, ref_n = held(_per_deal_reference(won, df, rt))
    pol_held, pol_n = held(policy_threshold)
    return [
        {"policy": "Hold each segment at its reference win point",
         "held_back": ref_held, "deals_affected": ref_n},
        {"policy": f"Require approval above the policy line ({policy_threshold:.0%})",
         "held_back": pol_held, "deals_affected": pol_n},
        {"policy": "Freeze extra discounting in the quarter-end window",
         "held_back": float(qe.get("attributable_discount_won", 0.0)) if qe else 0.0,
         "deals_affected": int(qe.get("qe_deals", 0)) if qe else 0},
    ]


# --- New vs Renewal split (2026-06-10 dry-run, wishlist 4) -------------------

_NVR_COLS = ["deal_type", "deals", "won", "win_rate", "avg_discount_won",
             "price_realization_won", "booked_acv_won",
             "reference_threshold", "reference_band", "reference_basis"]


def new_vs_renewal(df: pd.DataFrame, min_deals: int = 10,
                   ref_min_deals: int = SEGMENT_REF_MIN_DEALS,
                   ref_min_bands: int = SEGMENT_REF_MIN_BANDS) -> pd.DataFrame:
    """Realization, average discount, win rate, and win point by deal type.

    Renewal discounting is a different disease from new-business discounting:
    a renewal discount rarely buys incremental win probability (the customer is
    already on the product), so renewal giveback is a governance / escalator
    problem, while new-business giveback is a win-rate investment question.
    Splitting the two stops one from hiding inside the other's average.

    Uses the canonical `deal_type` column ingest derives from the renewal flag
    or a recognized Type column ("new" / "renewal" / "" for unknown). Rows
    group into New / Renewal / Other-unknown; groups thinner than `min_deals`
    are dropped, and a missing column returns an empty frame so the readout
    degrades gracefully. Each group gets its own win point only when it passes
    the same sufficiency bar as segments (ref_min_deals + ref_min_bands);
    otherwise the global reference is shown with the fallback disclosed.
    """
    if "deal_type" not in df.columns or df.empty:
        return pd.DataFrame(columns=_NVR_COLS)
    dt = df["deal_type"].astype(str).str.strip().str.lower()
    groups = [
        ("New", dt == "new"),
        ("Renewal", dt == "renewal"),
        ("Other/unknown", ~dt.isin(("new", "renewal"))),
    ]
    g_ref = reference_discount(df)
    out: list[dict] = []
    for label, mask in groups:
        sub = df[mask]
        if len(sub) < min_deals:
            continue
        won = _won(sub)
        booked = float(won["booked_acv"].sum())
        list_won = float(won["list_acv"].sum())
        if (len(sub) >= ref_min_deals
                and _populated_real_bands(sub) >= ref_min_bands):
            ref, basis = reference_discount(sub), _BASIS_OWN
        else:
            ref, basis = g_ref, _BASIS_FALLBACK
        out.append({
            "deal_type": label,
            "deals": int(len(sub)),
            "won": int(len(won)),
            "win_rate": (len(won) / len(sub)) if len(sub) else 0.0,
            "avg_discount_won": (float(won["discount_pct"].mean())
                                 if len(won) else 0.0),
            "price_realization_won": (booked / list_won) if list_won else 0.0,
            "booked_acv_won": booked,
            "reference_threshold": float(ref["reference_threshold"]),
            "reference_band": ref["reference_band"],
            "reference_basis": basis,
        })
    return pd.DataFrame(out, columns=_NVR_COLS)
