"""Diagnostic — the retrospective leakage breakdown."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import altair as alt  # noqa: E402
import streamlit as st  # noqa: E402

from _app_lib import (  # noqa: E402
    BRAND, get_diagnostic, money, page, pct, require_csv, sidebar_inputs,
)

page("Diagnostic")
csv, policy = sidebar_inputs()
require_csv(csv)
res = get_diagnostic(csv, policy)
lk, qe, gv = res["leakage"], res["quarter_end"], res["governance"]

# --- win rate vs discount ----------------------------------------------------
left, right = st.columns([3, 2])
with left:
    st.subheader("Win rate vs discount")
    wb = res["win_rate_by_band"]
    base = alt.Chart(wb).encode(
        x=alt.X("discount_band:N", sort=list(wb["discount_band"]), title="Discount band"))
    bars = base.mark_bar(color="#9ecae1").encode(y=alt.Y("deals:Q", title="Deals"))
    line = base.mark_line(point=True, color=BRAND["coral"], strokeWidth=3).encode(
        y=alt.Y("win_rate:Q", title="Win rate", axis=alt.Axis(format="%")))
    st.altair_chart(alt.layer(bars, line).resolve_scale(y="independent"),
                    use_container_width=True)
    st.caption("Bars = deal volume; line = win rate. A flat line over higher "
               "bands means extra discount isn't buying wins.")
with right:
    st.subheader("Realization by segment")
    seg = res["realization_by_segment"][
        ["segment", "deals", "booked_acv", "avg_discount", "price_realization"]].copy()
    seg["booked_acv"] = seg["booked_acv"].map(money)
    seg["avg_discount"] = seg["avg_discount"].map(pct)
    seg["price_realization"] = seg["price_realization"].map(pct)
    st.dataframe(seg, hide_index=True, use_container_width=True)

# --- leakage lenses ----------------------------------------------------------
st.subheader("Leakage lenses (won deals)")
l1, l2, l3 = st.columns(3)
l1.metric("Gross discount given", money(lk["gross_discount_won"]),
          help="Total list-to-booked giveback. Descriptive, not a problem by itself.")
l2.metric(f"Off-policy (> {pct(lk['policy_threshold'])})", money(lk["off_policy_leakage_won"]),
          help="Discount above the policy line.")
l3.metric(f"Excess vs reference ({pct(lk['reference_threshold'])})",
          money(lk["excess_vs_reference_won"]),
          help="Discount above where win rate stops improving (correlational).")

# --- quarter-end + governance ------------------------------------------------
q, g = st.columns(2)
with q:
    st.subheader("Quarter-end effect")
    if qe:
        st.metric("Discount lift in last 3 weeks of quarter", f"{qe['lift']:+.1%}",
                  f"{money(qe['attributable_discount_won'])} attributable")
        st.caption(f"Quarter-end avg discount {pct(qe['qe_avg_discount'])} vs "
                   f"{pct(qe['rest_avg_discount'])} the rest of the quarter.")
with g:
    st.subheader("Governance gaps")
    st.metric("Off-policy won deals with no approver",
              f"{gv['off_policy_unapproved_won']:,}",
              f"{money(gv['unapproved_discount_dollars'])} discounted, unapproved",
              delta_color="inverse")

# --- investigate-first list --------------------------------------------------
st.subheader("Top deals to investigate")
st.caption("Won deals ranked by discount given above the reference level.")
tld = res["top_leak_deals"].copy()
for c in ("list_acv", "booked_acv", "excess_discount_dollars"):
    if c in tld:
        tld[c] = tld[c].map(money)
if "discount_pct" in tld:
    tld["discount_pct"] = tld["discount_pct"].map(pct)
st.dataframe(tld, hide_index=True, use_container_width=True)
