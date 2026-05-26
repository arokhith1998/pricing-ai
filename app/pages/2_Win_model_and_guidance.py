"""Win model and guidance. Win probability and the best discount per deal."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from _app_lib import (  # noqa: E402
    BRAND, field_label, get_diagnostic, get_model, get_model_leakage, model,
    money, page, pct, pretty_factors, require_csv, sidebar_inputs,
)

page("Win model and guidance")
csv, policy = sidebar_inputs()
require_csv(csv)
res = get_diagnostic(csv, policy)

st.caption("Predict the next deal. We estimate the chance of winning from what "
           "is known when the quote goes out, then find the discount that makes "
           "the most expected revenue. This is decision support, with a person "
           "always in the loop.")

try:
    tm = get_model(csv)
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not train the model: {exc}")
    st.stop()

m = tm.metrics
st.success("The model is well calibrated: the win rates it predicts line up "
           f"with what actually happened ({pct(m['mean_pred'])} predicted versus "
           f"{pct(m['base_rate'])} actual). That makes the guidance below dependable.")
with st.expander("Model quality (advanced)"):
    a1, a2, a3 = st.columns(3)
    a1.metric("Ranking accuracy (AUC)", f"{m['auc']:.3f}",
              help="1.0 is perfect, 0.5 is a coin flip.")
    a2.metric("Calibration error (Brier)", f"{m['brier']:.3f}", help="Lower is better.")
    a3.metric("Average precision", f"{m['avg_precision']:.3f}")

# --- what the model says you could keep --------------------------------------
ml = get_model_leakage(csv)
st.info(
    f"**Judged deal by deal:** these wins needed about "
    f"**{pct(ml['mean_justified_discount'])}** discount on average to win, versus "
    f"**{pct(ml['mean_actual_discount'])}** actually given. That gap is "
    f"**{money(ml['model_excess_won'])}** ({pct(ml['model_excess_pct_of_booked'])} "
    f"of booked value) across {ml['deals_over_justified']:,} deals. Because it is "
    "judged per deal, it is more dependable than the single companywide number "
    "on the Diagnostic page."
)

gl, gr = st.columns([2, 3])
with gl:
    with st.container(border=True):
        st.markdown("##### What drives wins")
        fi = model.feature_importance(tm).copy()
        fi["feature"] = fi["feature"].map(field_label)
        st.altair_chart(
            alt.Chart(fi).mark_bar(color=BRAND["teal"], cornerRadiusEnd=3).encode(
                x=alt.X("gain:Q", title="Influence"),
                y=alt.Y("feature:N", sort="-x", title=None),
                tooltip=[alt.Tooltip("feature:N", title="Factor"),
                         alt.Tooltip("gain:Q", title="Influence", format=",.0f")]),
            use_container_width=True)
        st.caption("How much each factor moves the win prediction, across all deals.")

with gr:
    with st.container(border=True):
        st.markdown("##### Discount guidance for one deal")
        opp_choices = list(res["top_leak_deals"]["opportunity_id"])
        if not opp_choices:
            st.caption("No deals to guide on in this dataset.")
            st.stop()
        opp = st.selectbox("Opportunity", opp_choices)
        didx = res["data"].index[res["data"]["opportunity_id"] == opp][0]
        deal = res["data"].loc[didx]
        rec = model.recommend_discount(tm, tm.X_all.loc[[didx]], float(deal["list_acv"]))

        d1, d2, d3 = st.columns(3)
        d1.metric("Discount given", pct(rec["current_discount"]))
        d2.metric("Recommended discount", pct(rec["recommended_discount"]),
                  f"{rec['recommended_discount'] - rec['current_discount']:+.0%}",
                  delta_color="off")
        d3.metric("Extra value expected", money(rec["uplift"]),
                  help="Expected annual value at the recommended discount versus "
                       "the one given.")

        curve = rec["curve"]
        base = alt.Chart(curve).encode(
            x=alt.X("discount:Q", axis=alt.Axis(format="%"), title="Discount"))
        ev = base.mark_line(color=BRAND["navy"], strokeWidth=3).encode(
            y=alt.Y("expected_acv:Q", title="Expected value ($)"),
            tooltip=[alt.Tooltip("discount:Q", title="Discount", format=".0%"),
                     alt.Tooltip("expected_acv:Q", title="Expected value", format="$,.0f"),
                     alt.Tooltip("win_prob:Q", title="Win probability", format=".0%")])
        wp = base.mark_line(color=BRAND["coral"], strokeDash=[4, 3]).encode(
            y=alt.Y("win_prob:Q", title="Win probability", axis=alt.Axis(format="%")))
        rule = alt.Chart(pd.DataFrame({"d": [rec["recommended_discount"]]})).mark_rule(
            color=BRAND["teal"], strokeDash=[2, 2]).encode(x="d:Q")
        st.altair_chart(alt.layer(ev, wp, rule).resolve_scale(y="independent"),
                        use_container_width=True)
        st.caption("The solid line is expected value at each discount. The dashed "
                   "line is win probability. The vertical line marks the "
                   "recommended discount, where expected value peaks.")

        st.markdown("**What drove this prediction**")
        st.dataframe(pretty_factors(model.explain(tm, tm.X_all.loc[[didx]])).head(6),
                     hide_index=True, use_container_width=True)
