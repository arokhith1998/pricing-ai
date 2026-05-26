"""Methodology. How the numbers are worked out, in plain terms."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from _app_lib import (  # noqa: E402
    get_diagnostic, pct, page, require_csv, sidebar_inputs,
)

page("Methodology")
csv, policy = sidebar_inputs()
require_csv(csv)
res = get_diagnostic(csv, policy)
rd = res["reference_discount"]

st.subheader("How we measure the leak")
st.markdown(
    "Everything here comes from your own closed deals. The math is fixed and "
    "repeatable, and the key numbers are tested. We show three views, from the "
    "plainest to the most useful:"
)
st.markdown(
    f"1. **Total discount given.** Everything given away from list price on won "
    f"deals. This is the full picture, not a problem by itself.\n"
    f"2. **Above your policy.** Discount given above your policy line "
    f"(currently {pct(policy)}, which you can change in the sidebar). This is a "
    f"governance view.\n"
    f"3. **Beyond the win point.** Discount given past the level where extra "
    f"discount stops winning more deals."
)

st.subheader("Finding the win point")
ci = rd.get("peak_win_rate_ci")
st.markdown(
    f"Win rates bounce around, so we do not trust a single number. We build a "
    f"confidence range for each discount band, then pick the cheapest discount "
    f"that still wins about as often as the best one. Here the win rate is "
    f"highest in the {rd['peak_band']} band at {pct(rd['peak_win_rate'])}"
    + (f" (likely between {pct(ci[0])} and {pct(ci[1])})" if ci else "")
    + f", and the {rd['reference_band']} band already gets there. So the win "
    f"point is {pct(rd['reference_threshold'])}. Discount beyond that is the "
    f"third view above."
)
band_ci = rd.get("band_win_rate_ci") or {}
if band_ci:
    st.caption("Win rate by discount band, with the likely range:")
    st.dataframe(
        {"Discount band": list(band_ci.keys()),
         "Win rate": [pct(v[0]) for v in band_ci.values()],
         "Low estimate": [pct(v[1]) for v in band_ci.values()],
         "High estimate": [pct(v[2]) for v in band_ci.values()]},
        hide_index=True, use_container_width=True)

st.warning(
    "Important honesty note. The third view is a correlation, not proof of "
    "cause. Bigger, harder, and more competitive deals tend to get bigger "
    "discounts, so some of that discount was justified. Treat it as a list of "
    "deals to look at, not a refund you are owed. The deal-by-deal number on "
    "the guidance page is the more dependable one. Have a pricing advisor "
    "sanity-check the method before you quote a figure to a customer."
)

st.subheader("The prediction model")
st.markdown(
    "- It only uses what is known when the quote goes out (segment, region, "
    "industry, plan, pricing model, list value, the proposed discount, whether "
    "a competitor is in the deal, the term, and timing). It never sees the "
    "result, so it cannot cheat.\n"
    "- Every prediction shows the top factors that pushed it up or down, so a "
    "buyer can see why, not just what.\n"
    "- For guidance we test each possible discount and recommend the one that "
    "makes the most expected revenue. A person always makes the final call."
)

st.caption("Definitions. Price realization is booked value divided by list "
           "value on won deals. Discount is one minus price realization. Win "
           "rate in a band is wins divided by total deals in that band.")
