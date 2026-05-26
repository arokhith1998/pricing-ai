"""Win model & guidance — P(win) and the EV-optimal discount per deal."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from _app_lib import (  # noqa: E402
    BRAND, get_diagnostic, get_model, model, money, page, pct,
    require_csv, sidebar_inputs,
)

page("Win model & guidance")
csv, policy = sidebar_inputs()
require_csv(csv)
res = get_diagnostic(csv, policy)
tm = get_model(csv)
m = tm.metrics

st.caption("Predict the next deal: P(win) from quote-time features, and the "
           "discount that maximizes expected booked ACV. Decision support — "
           "humans in the loop, not an autopilot.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("ROC AUC", f"{m['auc']:.3f}", help="Discrimination on a 25% holdout.")
c2.metric("Avg precision", f"{m['avg_precision']:.3f}", help=f"Base win rate {pct(m['base_rate'])}.")
c3.metric("Brier score", f"{m['brier']:.3f}", help="Calibration error (lower is better).")
c4.metric("Calibration", f"{pct(m['mean_pred'])} / {pct(m['base_rate'])}",
          help="Mean predicted vs actual win rate on holdout.")

# --- model-conditioned leakage (Phase 1 + 2 unified) -------------------------
ml = model.leakage_vs_model(tm, res["data"])
st.info(
    f"**Model-conditioned leakage:** mean justified discount "
    f"**{pct(ml['mean_justified_discount'])}** vs actual {pct(ml['mean_actual_discount'])}. "
    f"**{money(ml['model_excess_won'])}** ({pct(ml['model_excess_pct_of_booked'])} of booked ACV) "
    f"was given above each deal's *own* EV-optimal discount, across "
    f"{ml['deals_over_justified']:,} deals. This conditions on deal attributes, "
    "so it's more defensible than the single global reference on the Diagnostic page."
)

gl, gr = st.columns([2, 3])
with gl:
    st.subheader("Feature importance")
    fi = model.feature_importance(tm)
    st.altair_chart(
        alt.Chart(fi).mark_bar(color="#6baed6").encode(
            x=alt.X("gain:Q", title="Gain"),
            y=alt.Y("feature:N", sort="-x", title=None)),
        use_container_width=True)
with gr:
    st.subheader("Per-deal discount guidance")
    opp_choices = list(res["top_leak_deals"]["opportunity_id"])
    opp = st.selectbox("Opportunity (defaults to top leak deals)", opp_choices)
    didx = res["data"].index[res["data"]["opportunity_id"] == opp][0]
    deal = res["data"].loc[didx]
    rec = model.recommend_discount(tm, tm.X_all.loc[[didx]], float(deal["list_acv"]))

    d1, d2, d3 = st.columns(3)
    d1.metric("Discount given", pct(rec["current_discount"]))
    d2.metric("Recommended", pct(rec["recommended_discount"]),
              f"{rec['recommended_discount'] - rec['current_discount']:+.0%}",
              delta_color="off")
    d3.metric("Expected ACV uplift", money(rec["uplift"]),
              help="Expected booked ACV at the recommended vs the given discount.")

    curve = rec["curve"]
    base = alt.Chart(curve).encode(
        x=alt.X("discount:Q", axis=alt.Axis(format="%"), title="Discount"))
    ev = base.mark_line(color=BRAND["navy"], strokeWidth=3).encode(
        y=alt.Y("expected_acv:Q", title="Expected ACV ($)"))
    wp = base.mark_line(color=BRAND["coral"], strokeDash=[4, 3]).encode(
        y=alt.Y("win_prob:Q", title="P(win)", axis=alt.Axis(format="%")))
    rule = alt.Chart(pd.DataFrame({"d": [rec["recommended_discount"]]})).mark_rule(
        color=BRAND["teal"], strokeDash=[2, 2]).encode(x="d:Q")
    st.altair_chart(alt.layer(ev, wp, rule).resolve_scale(y="independent"),
                    use_container_width=True)
    st.caption("Solid = expected ACV, dashed = P(win), vertical = recommended "
               "discount (peak of expected ACV).")

    st.markdown("**Why this prediction** (top SHAP contributions, log-odds):")
    st.dataframe(model.explain(tm, tm.X_all.loc[[didx]]).head(6),
                 hide_index=True, use_container_width=True)
