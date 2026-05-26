"""Diagnostic. The retrospective view of where discount money goes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import altair as alt  # noqa: E402
import streamlit as st  # noqa: E402

from _app_lib import (  # noqa: E402
    BRAND, get_diagnostic, money, page, pct, relabel, require_csv, sidebar_inputs,
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
        x=alt.X("discount_band:N", sort=list(wb["discount_band"]), title="Discount"))
    bars = base.mark_bar(color="#9ecae1").encode(y=alt.Y("deals:Q", title="Number of deals"))
    line = base.mark_line(point=True, color=BRAND["coral"], strokeWidth=3).encode(
        y=alt.Y("win_rate:Q", title="Win rate", axis=alt.Axis(format="%")))
    st.altair_chart(alt.layer(bars, line).resolve_scale(y="independent"),
                    use_container_width=True)
    st.caption("Bars show how many deals fell in each discount range. The line "
               "is the win rate. When the line stops climbing, extra discount is "
               "no longer winning more deals.")
with right:
    st.subheader("Price realization by segment")
    seg = res["realization_by_segment"][
        ["segment", "deals", "booked_acv", "avg_discount", "price_realization"]].copy()
    seg["booked_acv"] = seg["booked_acv"].map(money)
    seg["avg_discount"] = seg["avg_discount"].map(pct)
    seg["price_realization"] = seg["price_realization"].map(pct)
    st.dataframe(relabel(seg), hide_index=True, use_container_width=True)

# --- where the money goes ----------------------------------------------------
st.subheader("Where the money goes (won deals)")
l1, l2, l3 = st.columns(3)
l1.metric("Total discount given", money(lk["gross_discount_won"]),
          help="Everything given away from list price on won deals. This is the "
               "full picture, not a problem on its own.")
l2.metric(f"Above your policy ({pct(lk['policy_threshold'])})",
          money(lk["off_policy_leakage_won"]),
          help="Discount given above your policy line.")
l3.metric(f"Beyond the win point ({pct(lk['reference_threshold'])})",
          money(lk["excess_vs_reference_won"]),
          help="Discount given beyond the point where extra discount stops "
               "winning more deals. A list to investigate, not a refund.")

# --- quarter-end + governance ------------------------------------------------
q, g = st.columns(2)
with q:
    st.subheader("Quarter-end pressure")
    if qe:
        st.metric("Extra discount in the last 3 weeks of a quarter",
                  f"{qe['lift']:+.1%}",
                  f"{money(qe['attributable_discount_won'])} attributable")
        st.caption(f"Average discount near quarter-end is {pct(qe['qe_avg_discount'])}, "
                   f"versus {pct(qe['rest_avg_discount'])} the rest of the quarter.")
with g:
    st.subheader("Approval gaps")
    st.metric("Deals above policy with no recorded approval",
              f"{gv['off_policy_unapproved_won']:,}",
              f"{money(gv['unapproved_discount_dollars'])} discounted without sign-off",
              delta_color="inverse")

# --- investigate-first list --------------------------------------------------
st.subheader("Deals to look at first")
st.caption("Won deals ranked by how much discount was given beyond the win point.")
tld = res["top_leak_deals"].copy()
for c in ("list_acv", "booked_acv", "excess_discount_dollars"):
    if c in tld:
        tld[c] = tld[c].map(money)
if "discount_pct" in tld:
    tld["discount_pct"] = tld["discount_pct"].map(pct)
st.dataframe(relabel(tld), hide_index=True, use_container_width=True)
