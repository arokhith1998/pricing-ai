"""Pricekeel home and overview (run: streamlit run app/dashboard.py).

Multipage app. This page sets the frame: the headline numbers and how the data
flows. Detail lives in the sidebar pages: Diagnostic, Win model and guidance,
Data and identity, Methodology.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

from _app_lib import (  # noqa: E402
    BRAND, assist, get_ai_summary, get_diagnostic, money, page, pct,
    require_csv, sidebar_inputs,
)

page("Overview")
csv, policy = sidebar_inputs()
require_csv(csv)
res = get_diagnostic(csv, policy)
ov, lk = res["overview"], res["leakage"]

st.subheader("Where the money goes, and what to do about it")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Booked value (annual)", money(ov["booked_acv_won"]))
c2.metric("Price realization", pct(ov["price_realization_won"]),
          help=f"Share of list price you actually keep on won deals. "
               f"Average discount is {pct(ov['avg_discount_won'])}.")
c3.metric("Money beyond the win point", money(lk["excess_vs_reference_won"]),
          f"{pct(lk['excess_pct_of_booked'])} of booked value", delta_color="inverse")
c4.metric("Win rate", pct(ov["win_rate"]),
          f"{ov['won']:,} won, {ov['lost']:,} lost")

st.info(
    f"**The short version.** Win rate stops improving past about a "
    f"**{pct(lk['reference_threshold'])}** discount, yet "
    f"**{money(lk['excess_vs_reference_won'])}** "
    f"({pct(lk['excess_pct_of_booked'])} of booked value) was discounted beyond "
    "that. This is a list to investigate, not a refund. The Methodology page "
    "explains how it is worked out, and the Diagnostic page breaks it down."
)

# --- AI executive summary ----------------------------------------------------
with st.container(border=True):
    st.markdown("##### Executive summary")
    if assist.has_llm():
        try:
            st.markdown(get_ai_summary(assist.summary_facts(res)))
            st.caption("Written by AI from the verified figures above. It "
                       "explains the numbers, it does not calculate them.")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Summary unavailable right now: {exc}")
    else:
        st.caption("Add an API key to .env to turn on a written summary of this "
                   "diagnostic.")

# --- how the system works ----------------------------------------------------
st.subheader("How it works")
st.caption("Each page below is one step in this flow. The figures are fixed and "
           "repeatable. The model adds the forward-looking guidance.")
dot = f"""
digraph {{
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="{BRAND['mist']}",
        color="{BRAND['navy']}", fontname="Inter", fontsize=11, margin="0.18,0.10"];
  edge [color="{BRAND['slate']}", penwidth=1.4];
  csv  [label="Your closed deals\\n(won and lost)"];
  ing  [label="Clean up\\nand match accounts"];
  met  [label="Measure\\nrealization and win rate"];
  diag [label="Diagnostic\\n(where the money goes)", fillcolor="{BRAND['navy']}", fontcolor="white"];
  mdl  [label="Predict\\nwin probability"];
  gui  [label="Recommend\\nthe best discount", fillcolor="{BRAND['teal']}", fontcolor="white"];
  csv -> ing -> met -> diag;
  ing -> mdl -> gui;
  met -> mdl;
}}
"""
st.graphviz_chart(dot, use_container_width=True)

g1, g2 = st.columns(2)
with g1:
    st.markdown(
        "- **Diagnostic.** Price realization, win rate by discount, quarter-end "
        "pressure, approval gaps, and the deals to look at first.\n"
        "- **Win model and guidance.** The chance of winning and the discount "
        "that makes the most expected revenue, deal by deal."
    )
with g2:
    st.markdown(
        "- **Data and identity.** How messy names and missing IDs become clean "
        "accounts, plus bring-your-own-CSV matching.\n"
        "- **Methodology.** Exactly how the numbers are worked out, and where "
        "they are a signal rather than proof."
    )
