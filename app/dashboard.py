"""Pricekeel — home / overview page (run: `streamlit run app/dashboard.py`).

Multipage app. This page sets the frame: the headline numbers and how data
flows through the system. The detail lives in the pages in the sidebar:
Diagnostic, Win model & guidance, Data & identity, Methodology.
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

st.subheader("Where your margin is leaking — and what to do about it")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Booked ACV (won)", money(ov["booked_acv_won"]))
c2.metric("Price realization", pct(ov["price_realization_won"]),
          help=f"Booked ÷ list on won deals (avg discount {pct(ov['avg_discount_won'])}).")
c3.metric("Excess discount", money(lk["excess_vs_reference_won"]),
          f"{pct(lk['excess_pct_of_booked'])} of booked ACV", delta_color="inverse")
c4.metric("Win rate", pct(ov["win_rate"]),
          f"{ov['won']:,} won / {ov['lost']:,} lost")

st.info(
    f"**Headline:** win rate stops improving past a **{pct(lk['reference_threshold'])}** "
    f"discount, yet **{money(lk['excess_vs_reference_won'])}** "
    f"({pct(lk['excess_pct_of_booked'])} of booked ACV) was discounted beyond that. "
    "Correlational — a prioritized list to investigate, not a refund figure. "
    "See **Methodology** for how this is computed and **Diagnostic** for the breakdown."
)

# --- AI executive summary ----------------------------------------------------
with st.container(border=True):
    st.markdown("##### 🧠 AI executive summary")
    if assist.has_llm():
        try:
            st.markdown(get_ai_summary(assist.summary_facts(res)))
            st.caption("Generated from the verified figures above — the model "
                       "narrates, it does not compute.")
        except Exception as exc:  # surface API errors without crashing the page
            st.warning(f"AI summary unavailable: {exc}")
    else:
        st.caption("Add `OPENAI_API_KEY` (or a Claude key) to `.env` to enable a "
                   "board-ready narrative of this diagnostic.")

# --- How the system works (the flow) -----------------------------------------
st.subheader("How it works")
st.caption("Every page below is one step in this pipeline. The numbers are "
           "deterministic; the model adds the forward-looking guidance.")
dot = f"""
digraph {{
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="{BRAND['mist']}",
        color="{BRAND['navy']}", fontname="Inter", fontsize=11, margin="0.18,0.10"];
  edge [color="{BRAND['slate']}", penwidth=1.4];
  csv  [label="Deals CSV\\n(closed won + lost)"];
  ing  [label="Ingest +\\nidentity resolution"];
  met  [label="Metrics\\n(leakage, realization,\\nwin-rate-by-band)"];
  diag [label="Diagnostic\\n(the leak)", fillcolor="{BRAND['navy']}", fontcolor="white"];
  mdl  [label="Win-probability\\nmodel (LightGBM)"];
  gui  [label="Deal guidance\\n(EV-optimal discount)", fillcolor="{BRAND['teal']}", fontcolor="white"];
  csv -> ing -> met -> diag;
  ing -> mdl -> gui;
  met -> mdl;
}}
"""
st.graphviz_chart(dot, use_container_width=True)

g1, g2 = st.columns(2)
with g1:
    st.markdown(
        "- **Diagnostic** — price realization, win rate by discount band, "
        "quarter-end effect, governance gaps, and the deals to investigate first.\n"
        "- **Win model & guidance** — P(win) from quote-time features and the "
        "discount that maximizes expected ACV per deal."
    )
with g2:
    st.markdown(
        "- **Data & identity** — how messy account names + missing IDs resolve "
        "into accounts; raw data preview.\n"
        "- **Methodology** — exactly how leakage is defined and why the numbers "
        "are defensible (and where they are only correlational)."
    )
