"""Discount-leakage diagnostic dashboard (Streamlit).

Run:  streamlit run app/dashboard.py
Then point it at a deals CSV (defaults to the synthetic dataset).

This is the demo surface for the wedge: paste in a CSV, see the leak. Streamlit
is the deliberate week-1 choice over Next.js — local-first, fast to a working
demo. A customer-facing UI comes later.
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# allow running via `streamlit run app/dashboard.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pricing import metrics, model  # noqa: E402
from pricing.diagnostic import run  # noqa: E402
from pricing.ingest import ingest  # noqa: E402
from pricing.schema import DEFAULT_POLICY_THRESHOLD  # noqa: E402


@st.cache_resource(show_spinner="Training win-probability model…")
def _train_model(path: str):
    """Train once per CSV (cached). Policy threshold doesn't affect the model."""
    return model.train(ingest(path))

st.set_page_config(page_title="Discount-Leakage Diagnostic", layout="wide")


def _money(x: float) -> str:
    return f"${x:,.0f}"


st.sidebar.title("Diagnostic input")
default_csv = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "deals.csv"
csv_path = st.sidebar.text_input("Deals CSV path", value=str(default_csv))
policy = st.sidebar.slider("Discount policy threshold", 0.0, 0.40,
                           DEFAULT_POLICY_THRESHOLD, 0.01,
                           help="Discount above this is 'off-policy'.")
st.sidebar.caption(
    "One row per closed opportunity (won + lost). See gtm/data-request.md for "
    "the exact columns. Synthetic data is for demo only."
)

if not Path(csv_path).exists():
    st.error(f"CSV not found: {csv_path}\n\nGenerate one with "
             "`python -m pricing.generate`.")
    st.stop()

try:
    res = run(csv_path, policy_threshold=policy)
except Exception as exc:  # surface schema/parse errors plainly
    st.error(f"Could not run diagnostic: {exc}")
    st.stop()

ov, lk, qe, gv = res["overview"], res["leakage"], res["quarter_end"], res["governance"]

st.title("Discount-Leakage Diagnostic")
st.caption("Retrospective analysis of closed deals — where margin leaks, and "
           "which deals to investigate first.")

# --- headline KPIs -----------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Booked ACV (won)", _money(ov["booked_acv_won"]))
c2.metric("Price realization", f"{ov['price_realization_won']:.1%}",
          help="Booked ÷ list on won deals (avg discount "
               f"{ov['avg_discount_won']:.1%}).")
c3.metric("Excess discount", _money(lk["excess_vs_reference_won"]),
          f"{lk['excess_pct_of_booked']:.1%} of booked ACV", delta_color="inverse")
c4.metric("Win rate", f"{ov['win_rate']:.1%}",
          f"{ov['won']:,} won / {ov['lost']:,} lost")

st.info(
    f"**Headline:** win rate stops improving past a **{lk['reference_threshold']:.0%}** "
    f"discount, yet **{_money(lk['excess_vs_reference_won'])}** "
    f"({lk['excess_pct_of_booked']:.1%} of booked ACV) was discounted beyond "
    f"that across **{lk['deals_above_reference']:,}** won deals. "
    "Correlational — a prioritized list to investigate, not a refund figure."
)

# --- win rate by band --------------------------------------------------------
left, right = st.columns([3, 2])
with left:
    st.subheader("Win rate vs discount")
    wb = res["win_rate_by_band"]
    base = alt.Chart(wb).encode(x=alt.X("discount_band:N", sort=list(wb["discount_band"]),
                                        title="Discount band"))
    bars = base.mark_bar(color="#9ecae1").encode(
        y=alt.Y("deals:Q", title="Deals"))
    line = base.mark_line(point=True, color="#d62728", strokeWidth=3).encode(
        y=alt.Y("win_rate:Q", title="Win rate", axis=alt.Axis(format="%")))
    st.altair_chart(alt.layer(bars, line).resolve_scale(y="independent"),
                    use_container_width=True)
    st.caption("Bars = deal volume; red line = win rate. A flat line over higher "
               "bands means extra discount isn't buying wins.")

with right:
    st.subheader("Price realization by segment")
    seg = res["realization_by_segment"][
        ["segment", "deals", "booked_acv", "avg_discount", "price_realization"]
    ].copy()
    seg["booked_acv"] = seg["booked_acv"].map(_money)
    seg["avg_discount"] = seg["avg_discount"].map(lambda x: f"{x:.1%}")
    seg["price_realization"] = seg["price_realization"].map(lambda x: f"{x:.1%}")
    st.dataframe(seg, hide_index=True, use_container_width=True)

# --- leakage lenses ----------------------------------------------------------
st.subheader("Leakage lenses (won deals)")
l1, l2, l3 = st.columns(3)
l1.metric("Gross discount given", _money(lk["gross_discount_won"]),
          help="Total list-to-booked giveback. Descriptive, not a problem by itself.")
l2.metric(f"Off-policy (> {lk['policy_threshold']:.0%})",
          _money(lk["off_policy_leakage_won"]),
          help="Discount above the policy line.")
l3.metric(f"Excess vs reference ({lk['reference_threshold']:.0%})",
          _money(lk["excess_vs_reference_won"]),
          help="Discount above the point where win rate stops improving.")

# --- quarter-end + governance ------------------------------------------------
q, g = st.columns(2)
with q:
    st.subheader("Quarter-end effect")
    if qe:
        st.metric("Discount lift in last 3 weeks of quarter",
                  f"{qe['lift']:+.1%}",
                  f"{_money(qe['attributable_discount_won'])} attributable")
        st.caption(f"Quarter-end avg discount {qe['qe_avg_discount']:.1%} vs "
                   f"{qe['rest_avg_discount']:.1%} the rest of the quarter.")
with g:
    st.subheader("Governance gaps")
    st.metric("Off-policy won deals with no approver",
              f"{gv['off_policy_unapproved_won']:,}",
              f"{_money(gv['unapproved_discount_dollars'])} discounted, unapproved",
              delta_color="inverse")

# --- investigate-first list --------------------------------------------------
st.subheader("Top deals to investigate")
st.caption("Won deals ranked by discount given above the reference level.")
tld = res["top_leak_deals"].copy()
for c in ("list_acv", "booked_acv", "excess_discount_dollars"):
    if c in tld:
        tld[c] = tld[c].map(_money)
if "discount_pct" in tld:
    tld["discount_pct"] = tld["discount_pct"].map(lambda x: f"{x:.1%}")
st.dataframe(tld, hide_index=True, use_container_width=True)

with st.expander("Resolved accounts & raw data"):
    st.caption(f"{ov['resolved_accounts']:,} accounts resolved from "
               f"{ov['opportunities']:,} opportunities (messy names + missing IDs).")
    st.dataframe(res["data"].head(200), hide_index=True, use_container_width=True)

# --- Phase 2: win-probability & deal guidance --------------------------------
st.divider()
st.header("Win-probability & deal guidance")
st.caption("Predict the next deal: P(win) from quote-time features, and the "
           "discount that maximizes expected booked ACV. Decision support — "
           "humans in the loop, not an autopilot.")

tm = _train_model(csv_path)
m = tm.metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("ROC AUC", f"{m['auc']:.3f}", help="Discrimination on a 25% holdout.")
m2.metric("Avg precision", f"{m['avg_precision']:.3f}",
          help=f"Base win rate {m['base_rate']:.1%}.")
m3.metric("Brier score", f"{m['brier']:.3f}", help="Calibration error (lower is better).")
m4.metric("Calibration", f"{m['mean_pred']:.1%} / {m['base_rate']:.1%}",
          help="Mean predicted vs actual win rate on holdout.")

gl, gr = st.columns([2, 3])
with gl:
    st.subheader("Feature importance")
    fi = model.feature_importance(tm)
    chart = (alt.Chart(fi).mark_bar(color="#6baed6")
             .encode(x=alt.X("gain:Q", title="Gain"),
                     y=alt.Y("feature:N", sort="-x", title=None)))
    st.altair_chart(chart, use_container_width=True)

with gr:
    st.subheader("Per-deal discount guidance")
    opp_choices = list(res["top_leak_deals"]["opportunity_id"])
    opp = st.selectbox("Opportunity (defaults to top leak deals)", opp_choices)
    didx = res["data"].index[res["data"]["opportunity_id"] == opp][0]
    deal = res["data"].loc[didx]
    rec = model.recommend_discount(tm, tm.X_all.loc[[didx]], float(deal["list_acv"]))

    d1, d2, d3 = st.columns(3)
    d1.metric("Discount given", f"{rec['current_discount']:.0%}")
    d2.metric("Recommended", f"{rec['recommended_discount']:.0%}",
              f"{rec['recommended_discount'] - rec['current_discount']:+.0%}",
              delta_color="off")
    d3.metric("Expected ACV uplift", _money(rec["uplift"]),
              help="Expected booked ACV at the recommended vs the given discount.")

    curve = rec["curve"]
    base = alt.Chart(curve).encode(x=alt.X("discount:Q", axis=alt.Axis(format="%"),
                                           title="Discount"))
    ev = base.mark_line(color="#2c7fb8", strokeWidth=3).encode(
        y=alt.Y("expected_acv:Q", title="Expected ACV ($)"))
    wp = base.mark_line(color="#d62728", strokeDash=[4, 3]).encode(
        y=alt.Y("win_prob:Q", title="P(win)", axis=alt.Axis(format="%")))
    rule = alt.Chart(pd.DataFrame({"d": [rec["recommended_discount"]]})).mark_rule(
        color="#2c7fb8", strokeDash=[2, 2]).encode(x="d:Q")
    st.altair_chart(alt.layer(ev, wp, rule).resolve_scale(y="independent"),
                    use_container_width=True)
    st.caption("Solid = expected ACV, dashed red = P(win), vertical line = "
               "recommended discount. The peak sits where extra discount stops "
               "paying for itself.")

    st.markdown("**Why this prediction** (top SHAP contributions, log-odds):")
    expl = model.explain(tm, tm.X_all.loc[[didx]]).head(6)
    st.dataframe(expl, hide_index=True, use_container_width=True)
