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


def realization_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    """$-weighted price realization and discount by segment (won deals)."""
    won = _won(df)
    g = won.groupby("segment").agg(
        deals=("opportunity_id", "count"),
        list_acv=("list_acv", "sum"),
        booked_acv=("booked_acv", "sum"),
        avg_discount=("discount_pct", "mean"),
    )
    g["price_realization"] = g["booked_acv"] / g["list_acv"]
    return g.reset_index().sort_values("booked_acv", ascending=False)


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
    """
    work = df[["discount_band", "is_won"]]
    rng = np.random.default_rng(seed)
    lo_q, hi_q = (1 - ci) / 2, 1 - (1 - ci) / 2

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

    stats = _band_stats(min_deals) or _band_stats(1)  # relax floor if too sparse
    edges = {label: lo for lo, _hi, label in DISCOUNT_BANDS}
    if not stats:
        return {"reference_threshold": 0.0, "reference_band": _BAND_ORDER[0],
                "peak_win_rate": 0.0, "peak_band": _BAND_ORDER[0],
                "peak_win_rate_ci": (0.0, 0.0), "band_win_rate_ci": {}}

    peak_band = max(stats, key=lambda k: stats[k][0])
    peak_mean, peak_lo, peak_hi, _ = stats[peak_band]
    reference_band = peak_band
    for label in _BAND_ORDER:          # cheapest band not significantly < peak
        if label in stats and stats[label][0] >= peak_lo:
            reference_band = label
            break
    return {
        "reference_threshold": float(edges[reference_band]),
        "reference_band": reference_band,
        "peak_win_rate": peak_mean,
        "peak_band": peak_band,
        "peak_win_rate_ci": (peak_lo, peak_hi),
        "band_win_rate_ci": {k: (v[0], v[1], v[2]) for k, v in stats.items()},
    }


def leakage(df: pd.DataFrame,
            policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> dict:
    """The three leakage lenses, in dollars, on won deals."""
    won = _won(df)
    gross = float(won["discount_amount"].sum())

    over_policy = (won["discount_pct"] - policy_threshold).clip(lower=0.0)
    off_policy = float((over_policy * won["list_acv"]).sum())

    ref = reference_discount(df)
    rt = ref["reference_threshold"]
    over_ref = (won["discount_pct"] - rt).clip(lower=0.0)
    excess = float((over_ref * won["list_acv"]).sum())
    n_excess = int((won["discount_pct"] > rt).sum())

    booked = float(won["booked_acv"].sum())
    return {
        "policy_threshold": policy_threshold,
        "gross_discount_won": gross,
        "off_policy_leakage_won": off_policy,
        "reference_threshold": rt,
        "reference_band": ref["reference_band"],
        "excess_vs_reference_won": excess,
        "deals_above_reference": n_excess,
        # excess as a share of booked ACV — the headline "leakage %"
        "excess_pct_of_booked": (excess / booked) if booked else 0.0,
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
    """The won deals with the most excess-vs-reference discount $ — the
    investigate-first list."""
    won = _won(df).copy()
    rt = reference_discount(df)["reference_threshold"]
    won["excess_discount_dollars"] = (
        (won["discount_pct"] - rt).clip(lower=0.0) * won["list_acv"]
    )
    cols = ["opportunity_id", "resolved_account_name", "segment", "rep_id",
            "list_acv", "booked_acv", "discount_pct", "competitor_present",
            "is_quarter_end", "off_policy_unapproved", "excess_discount_dollars"]
    cols = [c for c in cols if c in won.columns]
    return won.sort_values("excess_discount_dollars", ascending=False).head(n)[cols]
