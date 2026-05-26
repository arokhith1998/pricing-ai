"""Methodology — how the numbers are computed and where they're only signals."""

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

st.subheader("How we measure leakage")
st.markdown(
    "Everything here is computed from your closed-deal data — deterministic, "
    "reproducible, and unit-tested. We show three lenses, weakest-claim first:"
)
st.markdown(
    "1. **Gross discount $** — total list-to-booked giveback on won deals. "
    "Descriptive; not a problem by itself.\n"
    "2. **Off-policy $** — discount given *above your policy threshold* "
    f"(currently **{pct(policy)}**, adjustable in the sidebar). A governance lens.\n"
    "3. **Excess vs reference $** — discount given above the level where win "
    "rate stops improving."
)

st.subheader("The reference discount (with a confidence interval)")
ci = rd.get("peak_win_rate_ci")
st.markdown(
    f"Win rate per band is noisy, so we **bootstrap a confidence interval** on "
    f"each band's win rate and pick the *cheapest* band that is not "
    f"statistically worse than the best band. Here the win rate peaks in the "
    f"**{rd['peak_band']}** band at **{pct(rd['peak_win_rate'])}**"
    + (f" (90% CI {pct(ci[0])}–{pct(ci[1])})" if ci else "")
    + f", and is already reached by **{rd['reference_band']}** — so the "
    f"reference discount is **{pct(rd['reference_threshold'])}**."
)
band_ci = rd.get("band_win_rate_ci") or {}
if band_ci:
    st.caption("Bootstrapped win rate by band (mean, 90% CI):")
    st.dataframe(
        {"band": list(band_ci.keys()),
         "win_rate": [pct(v[0]) for v in band_ci.values()],
         "ci_low": [pct(v[1]) for v in band_ci.values()],
         "ci_high": [pct(v[2]) for v in band_ci.values()]},
        hide_index=True, use_container_width=True)

st.warning(
    "**The excess-vs-reference lens is correlational, not causal.** Bigger, "
    "harder, and more competitive deals attract bigger discounts, so some "
    "'excess' is justified. Treat it as a prioritized list of deals to "
    "investigate — not a refund figure. The **model-conditioned** leakage on "
    "the *Win model & guidance* page conditions on each deal's attributes and "
    "is the more defensible number; validate the methodology with a pricing "
    "advisor before quoting a figure to a customer."
)

st.subheader("The win-probability model")
st.markdown(
    "- **Leakage-free features only:** the model trains on attributes known "
    "*at quote time* (segment, region, industry, tier, value metric, list ACV, "
    "proposed discount, competitor, term, quarter-end). It never sees the "
    "outcome or post-close fields — enforced by a test.\n"
    "- **Explainable:** per-deal attributions use LightGBM's native SHAP "
    "contributions (explainability > accuracy in enterprise).\n"
    "- **Guidance:** for each deal we sweep the discount and recommend the "
    "level that maximizes expected booked ACV = P(win) × list × (1 − discount). "
    "Humans stay in the loop."
)

st.caption("Definitions: price realization = booked ÷ list (won deals). "
           "Discount % = 1 − realization. Win rate by band = won ÷ (won + lost) "
           "within each discount band.")
