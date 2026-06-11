"""Diagnostic orchestration — run the full retrospective leakage analysis.

CLI:  python -m pricing.diagnostic data/synthetic/deals.csv
Also importable: `run(path)` returns a dict of result sections the dashboard
renders.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pricing import metrics
from pricing.ingest import ingest_verbose
from pricing.schema import DEFAULT_POLICY_THRESHOLD


def run(path: str | Path,
        policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> dict:
    """Run the full pipeline and return all diagnostic sections."""
    df, load_report = ingest_verbose(path, policy_threshold=policy_threshold)
    return analyze(df, load_report, policy_threshold=policy_threshold)


def analyze(df, load_report=None,
            policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> dict:
    """All diagnostic sections for an already-ingested (enriched) frame."""
    pkg = metrics.packaging_signals(df)
    return {
        "data": df,
        # "What we read from your file" — section #1 of every readout.
        "load_report": load_report,
        "overview": metrics.overview(df),
        # Customer wishlist (2026-06-10 dry-run): time trend, segment/rep cuts,
        # and a so-what (policy simulation) for the headline excess figure.
        "trend_by_quarter": metrics.trend_by_quarter(df),
        "segment_win_points": metrics.segment_win_points(df),
        "policy_simulations": metrics.policy_simulations(df, policy_threshold),
        # New vs Renewal split (dry-run wishlist 4): renewal discounting is a
        # different disease from new-business discounting. Empty frame when
        # the deal-type column is missing, so the readout degrades gracefully.
        "new_vs_renewal": metrics.new_vs_renewal(df),
        "realization_by_segment": metrics.realization_by_segment(df),
        "win_rate_by_band": metrics.win_rate_by_band(df),
        "reference_discount": metrics.reference_discount(df),
        "leakage": metrics.leakage(df, policy_threshold),
        "quarter_end": metrics.quarter_end_effect(df),
        "rep_discipline": metrics.rep_discipline(df),
        "governance": metrics.governance_gaps(df),
        "top_leak_deals": metrics.top_leak_deals(df, policy_threshold=policy_threshold),
        # Optional hierarchy slicing: one frame per populated dimension.
        "hierarchy_slices": {
            d: metrics.realization_by(df, d)
            for d in metrics.present_hierarchy_dimensions(df)
        },
        # Framework signals (Rivera packaging, Simon-Kucher trade-or-give).
        "packaging_signals": pkg,
        "trade_or_give": metrics.trade_or_give(df),
        # Per-finding receipts — the actual deals behind each aggregate claim,
        # so a reviewer can audit it deal by deal instead of on trust.
        "trade_or_give_deals": metrics.trade_or_give_deals(df),
        "quarter_end_deals": metrics.quarter_end_deals(df),
        # Receipts for the top (worst-gap) packaging signal, if any.
        "packaging_signal_deals": (
            metrics.packaging_signal_deals(df, pkg[0]["dimension"], pkg[0]["value"])
            if pkg else pd.DataFrame(columns=metrics._FINDING_DEAL_COLS)
        ),
        # Sales-friendly split: discount earned vs discount worth investigating.
        # Pure function of (won deals, reference_threshold) — no recovery
        # assumption. Surfaced so reps see what their discounting defended,
        # not only what it leaked.
        "defended_vs_investigate": metrics.defended_vs_investigate(df, policy_threshold),
    }


def _money(x: float) -> str:
    return f"${x:,.0f}"


def _pct(x: float) -> str:
    return f"{x:.1%}"


def print_report(res: dict) -> None:
    ov = res["overview"]
    lk = res["leakage"]
    qe = res["quarter_end"]
    gv = res["governance"]

    # Section #1: what we read from the file. Trust before conclusions — the
    # deliverable must not start with a number the prospect cannot vet.
    rep = res.get("load_report")
    if rep is not None:
        print("-" * 64)
        print("  WHAT WE READ FROM YOUR FILE")
        print("-" * 64)
        print(rep.summary())
        fuzzy_maps = {f: s for f, s in rep.field_sources.items() if "fuzzy" in s}
        if fuzzy_maps:
            print("  columns mapped by fuzzy match (please verify):")
            for fld, src in sorted(fuzzy_maps.items()):
                print(f"    {fld} <- {src}")
        print()

    print("=" * 64)
    print("  DISCOUNT-LEAKAGE DIAGNOSTIC")
    print("=" * 64)
    print(f"Opportunities analyzed : {ov['opportunities']:,} "
          f"({ov['won']:,} won / {ov['lost']:,} lost, win rate {_pct(ov['win_rate'])})")
    print(f"Resolved accounts      : {ov['resolved_accounts']:,}")
    print(f"Booked ACV (won)       : {_money(ov['booked_acv_won'])}")
    print(f"Price realization (won): {_pct(ov['price_realization_won'])} "
          f"(avg discount {_pct(ov['avg_discount_won'])})")

    print("\n-- Win rate by discount band " + "-" * 35)
    wb = res["win_rate_by_band"].copy()
    wb["win_rate"] = wb["win_rate"].map(_pct)
    wb["avg_discount"] = wb["avg_discount"].map(_pct)
    print(wb.to_string(index=False))

    rd = res["reference_discount"]
    print(f"\nWin rate peaks at {_pct(rd['peak_win_rate'])} (band {rd['peak_band']}); "
          f"that win rate is already reached by the {rd['reference_band']} band.")
    print(f"=> Reference discount = {_pct(rd['reference_threshold'])}. "
          f"Discount above this bought ~no incremental win rate.")

    print("\n-- Leakage (won deals) " + "-" * 41)
    print(f"Gross discount given        : {_money(lk['gross_discount_won'])}")
    print(f"Off-policy (> {_pct(lk['policy_threshold'])})         : {_money(lk['off_policy_leakage_won'])}")
    seg_refs = lk.get("segment_references") or []
    if seg_refs and "excess_vs_segment_reference_won" in lk:
        # Headline: per-segment excess, each segment vs its OWN reference.
        print(f"Excess vs segment references: "
              f"{_money(lk['excess_vs_segment_reference_won'])} "
              f"across {lk['deals_above_segment_reference']:,} deals "
              f"= {_pct(lk['excess_segment_pct_of_booked'])} of booked ACV")
        print(f"  (secondary lens, single global reference at "
              f"{_pct(lk['reference_threshold'])}: "
              f"{_money(lk['excess_vs_reference_won'])} across "
              f"{lk['deals_above_reference']:,} deals = "
              f"{_pct(lk['excess_pct_of_booked'])} of booked ACV. The global "
              f"lens overstates segments")
        print("   whose win point sits above the global reference; the "
              "segment-aware figure is the one to use.)")

        # Disclosure: exactly which reference each segment was measured
        # against, and why. The headline is only defensible if this is shown.
        print("\n-- Reference discount by segment (basis of the headline) "
              + "-" * 6)
        print(f"   {'segment':<14}{'reference':>10}  {'basis':<38}"
              f"{'deals':>7}{'bands':>7}")
        for r in seg_refs:
            print(f"   {r['segment']:<14}"
                  f"{_pct(r['reference_threshold']):>10}  "
                  f"{r['basis']:<38}{r['deals']:>7,}{r['bands_populated']:>7}")
        print(f"   (A segment earns its own reference with >= "
              f"{metrics.SEGMENT_REF_MIN_DEALS} deals and >= "
              f"{metrics.SEGMENT_REF_MIN_BANDS} populated bands;")
        print("    thinner segments are measured against the global "
              "reference, disclosed above.)")
    else:
        print(f"Excess vs reference ({_pct(lk['reference_threshold'])})  : "
              f"{_money(lk['excess_vs_reference_won'])} "
              f"across {lk['deals_above_reference']:,} deals "
              f"= {_pct(lk['excess_pct_of_booked'])} of booked ACV")

    # Wishlist 1: is leakage getting better or worse, by quarter?
    trend = res.get("trend_by_quarter")
    if trend is not None and not trend.empty:
        print("\n-- Trend by quarter " + "-" * 44)
        t = trend.copy()
        t["win_rate"] = t["win_rate"].map(_pct)
        t["price_realization"] = t["price_realization"].map(_pct)
        t["excess_pct_of_booked"] = t["excess_pct_of_booked"].map(_pct)
        for c in ("booked_acv", "excess_won"):
            t[c] = t[c].map(_money)
        print(t.to_string(index=False))
        print("   (trend excess uses the single global reference so quarters "
              "stay comparable)")

    # Wishlist 2a: realization by segment + each segment's own win point.
    seg = res.get("realization_by_segment")
    if seg is not None and not seg.empty:
        print("\n-- Price realization by segment " + "-" * 32)
        s = seg.copy()
        s["price_realization"] = s["price_realization"].map(_pct)
        s["avg_discount"] = s["avg_discount"].map(_pct)
        for c in ("list_acv", "booked_acv"):
            s[c] = s[c].map(_money)
        print(s.to_string(index=False))
    for r in res.get("segment_win_points") or []:
        print(f"   {r['segment']:<12} peak {_pct(r['peak_win_rate'])} at "
              f"{r['peak_band']}, win point {r['reference_band']} ({r['deals']:,} deals)")

    # Wishlist 4 (dry-run 2026-06-10): New vs Renewal. Renewal discounting is
    # a different disease from new-business discounting, so the two must not
    # hide inside one blended average. Section degrades gracefully: absent
    # without a deal-type column, marked insufficient when it is too sparse.
    nvr = res.get("new_vs_renewal")
    data = res.get("data")
    has_type_col = data is not None and "deal_type" in getattr(data, "columns", ())
    typed = (nvr[nvr["deal_type"].isin(("New", "Renewal"))]
             if nvr is not None and not nvr.empty else None)
    if typed is not None and not typed.empty:
        print("\n-- New vs Renewal " + "-" * 46)
        v = nvr.copy()
        for c in ("win_rate", "avg_discount_won", "price_realization_won",
                  "reference_threshold"):
            v[c] = v[c].map(_pct)
        v["booked_acv_won"] = v["booked_acv_won"].map(_money)
        v = v.drop(columns=["reference_band"])
        v = v.rename(columns={"avg_discount_won": "avg_discount",
                              "price_realization_won": "realization",
                              "booked_acv_won": "booked_acv",
                              "reference_threshold": "win_point",
                              "reference_basis": "win_point_basis"})
        print(v.to_string(index=False))
        by_type = typed.set_index("deal_type")
        if {"New", "Renewal"} <= set(by_type.index):
            nd = by_type.loc["New", "avg_discount_won"]
            rd_ = by_type.loc["Renewal", "avg_discount_won"]
            print(f"   Renewal deals average {_pct(rd_)} discount vs "
                  f"{_pct(nd)} on new business. Renewal discounting is a")
            print("   different disease: a renewal discount rarely buys a win "
                  "(the customer is already on the")
            print("   product), so treat renewal giveback as governance and "
                  "escalator slippage, while new-business")
            print("   giveback is a win-rate investment question.")
    elif has_type_col:
        print("\n-- New vs Renewal " + "-" * 46)
        print("   Deal-type column present but too sparse to split "
              "(insufficient data).")

    if qe:
        print("\n-- Quarter-end effect " + "-" * 42)
        print(f"Avg discount: quarter-end {_pct(qe['qe_avg_discount'])} "
              f"vs rest {_pct(qe['rest_avg_discount'])} "
              f"(lift {_pct(qe['lift'])}, {_money(qe['attributable_discount_won'])} attributable)")

    print("\n-- Governance " + "-" * 50)
    print(f"Off-policy won deals        : {gv['off_policy_won']:,}")
    print(f"  ...with NO recorded approver: {gv['off_policy_unapproved_won']:,} "
          f"({_money(gv['unapproved_discount_dollars'])} discounted, unapproved)")

    # Wishlist 2b: rep league table — surface the over-discounters by name.
    reps = res.get("rep_discipline")
    if reps is not None and not reps.empty:
        print("\n-- Rep league table " + "-" * 44)
        r = reps.copy()
        for c in ("avg_discount", "win_rate", "discount_vs_median"):
            if c in r:
                r[c] = r[c].map(_pct)
        if "booked_acv" in r:
            r["booked_acv"] = r["booked_acv"].map(_money)
        print(r.to_string(index=False))

    print("\n-- Top deals to investigate (excess discount $) " + "-" * 16)
    tld = res["top_leak_deals"].head(8).copy()
    for c in ("list_acv", "booked_acv", "excess_discount_dollars"):
        if c in tld:
            tld[c] = tld[c].map(_money)
    if "discount_pct" in tld:
        tld["discount_pct"] = tld["discount_pct"].map(_pct)
    print(tld.to_string(index=False))

    # Wishlist 3: so-what. What would each policy have held back on won deals?
    sims = res.get("policy_simulations") or []
    if sims:
        print("\n-- What would have prevented it (policy simulation) " + "-" * 12)
        for s in sims:
            print(f"   {s['policy']:<46} up to {_money(s['held_back'])} "
                  f"({s['deals_affected']:,} won deals)")
        print("   (Upper bound: correlational, some discount was needed to win.)")

    print("\n(Note: excess-vs-reference is correlational — a prioritized list to")
    print(" investigate, not a refund figure. Validate with a pricing advisor.)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the leakage diagnostic.")
    ap.add_argument("path", type=Path, help="path to a deals CSV")
    ap.add_argument("--policy", type=float, default=DEFAULT_POLICY_THRESHOLD,
                    help="discount policy threshold (fraction, default 0.15)")
    args = ap.parse_args()
    pd.set_option("display.width", 140)
    res = run(args.path, policy_threshold=args.policy)
    print_report(res)


if __name__ == "__main__":
    main()
