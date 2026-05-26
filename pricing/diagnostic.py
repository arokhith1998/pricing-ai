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
from pricing.ingest import ingest
from pricing.schema import DEFAULT_POLICY_THRESHOLD


def run(path: str | Path,
        policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> dict:
    """Run the full pipeline and return all diagnostic sections."""
    df = ingest(path, policy_threshold=policy_threshold)
    return {
        "data": df,
        "overview": metrics.overview(df),
        "realization_by_segment": metrics.realization_by_segment(df),
        "win_rate_by_band": metrics.win_rate_by_band(df),
        "reference_discount": metrics.reference_discount(df),
        "leakage": metrics.leakage(df, policy_threshold),
        "quarter_end": metrics.quarter_end_effect(df),
        "rep_discipline": metrics.rep_discipline(df),
        "governance": metrics.governance_gaps(df),
        "top_leak_deals": metrics.top_leak_deals(df, policy_threshold=policy_threshold),
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
    print(f"Excess vs reference ({_pct(lk['reference_threshold'])})  : "
          f"{_money(lk['excess_vs_reference_won'])} "
          f"across {lk['deals_above_reference']:,} deals "
          f"= {_pct(lk['excess_pct_of_booked'])} of booked ACV")

    if qe:
        print("\n-- Quarter-end effect " + "-" * 42)
        print(f"Avg discount: quarter-end {_pct(qe['qe_avg_discount'])} "
              f"vs rest {_pct(qe['rest_avg_discount'])} "
              f"(lift {_pct(qe['lift'])}, {_money(qe['attributable_discount_won'])} attributable)")

    print("\n-- Governance " + "-" * 50)
    print(f"Off-policy won deals        : {gv['off_policy_won']:,}")
    print(f"  ...with NO recorded approver: {gv['off_policy_unapproved_won']:,} "
          f"({_money(gv['unapproved_discount_dollars'])} discounted, unapproved)")

    print("\n-- Top deals to investigate (excess discount $) " + "-" * 16)
    tld = res["top_leak_deals"].head(8).copy()
    for c in ("list_acv", "booked_acv", "excess_discount_dollars"):
        if c in tld:
            tld[c] = tld[c].map(_money)
    if "discount_pct" in tld:
        tld["discount_pct"] = tld["discount_pct"].map(_pct)
    print(tld.to_string(index=False))
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
