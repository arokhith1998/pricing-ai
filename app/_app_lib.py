"""Shared helpers for the Pricekeel multipage dashboard.

Each page imports this; it puts the repo root on sys.path (so `pricing` imports
work under `streamlit run`), holds the brand kit, and caches the expensive
diagnostic/model work so navigating between pages is instant.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pricing import assist, metrics, model  # noqa: E402  (re-exported for pages)
from pricing.diagnostic import run  # noqa: E402
from pricing.ingest import ingest  # noqa: E402
from pricing.schema import DEFAULT_POLICY_THRESHOLD  # noqa: E402

BRAND = {
    "name": "Pricekeel",
    "tagline": "Keep your pricing on an even keel.",
    "navy": "#0C2D48", "ink": "#0B1727", "teal": "#17B8A6", "green": "#2BB673",
    "coral": "#F0654E", "amber": "#E8A33D", "slate": "#5B6B7B",
    "mist": "#E6EDF3", "paper": "#F7FAFC",
}
DEFAULT_CSV = ROOT / "data" / "synthetic" / "deals.csv"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {{ --pk-navy:{BRAND['navy']}; --pk-teal:{BRAND['teal']}; --pk-mist:{BRAND['mist']};
         --pk-slate:{BRAND['slate']}; }}
html, body, [class*="css"], .stMarkdown, input, textarea, button, select {{
    font-family:'Inter',sans-serif; }}
h1,h2,h3,h4 {{ color:var(--pk-navy); letter-spacing:-0.3px; }}
@keyframes pkFade {{ from {{opacity:0; transform:translateY(10px);}} to {{opacity:1; transform:none;}} }}
.main .block-container {{ animation:pkFade .45s ease-out; padding-top:1.1rem; max-width:1200px; }}
/* metric cards */
[data-testid="stMetric"] {{ background:#fff; border:1px solid var(--pk-mist); border-radius:12px;
    padding:14px 16px; box-shadow:0 1px 2px rgba(12,45,72,.05);
    transition:transform .15s ease, box-shadow .15s ease; }}
[data-testid="stMetric"]:hover {{ transform:translateY(-2px); box-shadow:0 6px 18px rgba(12,45,72,.10); }}
[data-testid="stMetricValue"] {{ font-variant-numeric:tabular-nums; font-weight:700; color:var(--pk-navy); }}
/* bordered containers behave like cards */
[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:14px !important;
    border-color:var(--pk-mist) !important; background:#fff;
    box-shadow:0 1px 3px rgba(12,45,72,.05); transition:box-shadow .2s ease; }}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{ box-shadow:0 8px 24px rgba(12,45,72,.09); }}
.stButton>button {{ border-radius:10px; font-weight:600; }}
.stTabs [aria-selected="true"] {{ color:var(--pk-teal); }}
.pk-word {{ font-weight:800; font-size:1.55rem; letter-spacing:-0.6px; }}
.pk-word .a {{ color:var(--pk-navy); }} .pk-word .b {{ color:var(--pk-teal); }}
.pk-tag {{ color:var(--pk-slate); font-size:.9rem; margin-top:-4px; margin-bottom:.5rem; }}
.pk-mark {{ vertical-align:middle; margin-right:10px; }}
hr {{ border-color:var(--pk-mist); }}
@media (max-width:640px) {{ .main .block-container {{ padding:1rem .8rem; }} }}
</style>
"""

# Inline keel mark (matches brand/logo-mark.svg) so the header has no file dep.
_MARK = (
    f'<svg class="pk-mark" width="30" height="30" viewBox="0 0 48 48" '
    f'xmlns="http://www.w3.org/2000/svg">'
    f'<line x1="9" y1="19" x2="39" y2="19" stroke="{BRAND["navy"]}" '
    f'stroke-width="3" stroke-linecap="round"/>'
    f'<path d="M13 19 Q24 43 35 19" fill="none" stroke="{BRAND["teal"]}" '
    f'stroke-width="4" stroke-linecap="round"/></svg>'
)


def page(title: str, icon: str = "⚓") -> None:
    """Standard page setup: config, fonts, and the Pricekeel header."""
    st.set_page_config(page_title=f"{title} · Pricekeel", page_icon=icon,
                       layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div>{_MARK}<span class="pk-word"><span class="a">Price</span>'
        f'<span class="b">keel</span></span></div>'
        f'<div class="pk-tag">{BRAND["tagline"]}</div>',
        unsafe_allow_html=True,
    )
    st.write("")


def sidebar_inputs() -> tuple[str, float]:
    """Shared CSV path + policy-threshold controls, persisted across pages."""
    st.sidebar.markdown("**Diagnostic input**")
    csv = st.sidebar.text_input(
        "Deals CSV path", value=str(st.session_state.get("csv", DEFAULT_CSV)))
    policy = st.sidebar.slider(
        "Discount policy threshold", 0.0, 0.40,
        float(st.session_state.get("policy", DEFAULT_POLICY_THRESHOLD)), 0.01,
        help="Discount above this is 'off-policy'.")
    st.session_state["csv"], st.session_state["policy"] = csv, policy
    st.sidebar.caption("One row per closed opportunity (won + lost). "
                       "Synthetic data is for demo only.")
    return csv, policy


def require_csv(csv: str) -> None:
    if not Path(csv).exists():
        st.error(f"CSV not found: {csv}\n\nGenerate one with "
                 "`python -m pricing.generate`.")
        st.stop()


@st.cache_data(show_spinner="Running diagnostic…")
def get_diagnostic(csv: str, policy: float) -> dict:
    return run(csv, policy_threshold=policy)


@st.cache_resource(show_spinner="Training win-probability model…")
def get_model(csv: str):
    return model.train(ingest(csv))


@st.cache_data(show_spinner=False)
def get_model_leakage(csv: str) -> dict:
    """Model-conditioned leakage, cached per CSV so the page never recomputes."""
    return model.leakage_vs_model(get_model(csv), ingest(csv))


@st.cache_data(show_spinner="Writing executive summary…")
def get_ai_summary(facts: str) -> str:
    """Cached per unique diagnostic (facts string) so we call the LLM once."""
    return assist._complete(assist._SUMMARY_SYSTEM, facts, max_tokens=500).strip()


@st.cache_data(show_spinner="Mapping columns…")
def get_column_map(headers: tuple[str, ...]) -> dict:
    return assist.map_columns(list(headers))


def money(x: float) -> str:
    return f"${x:,.0f}"


def pct(x: float) -> str:
    return f"{x:.1%}"


# Human-readable labels for every field we might show. No raw snake_case in UI.
LABELS = {
    "opportunity_id": "Opportunity ID", "account_name": "Account",
    "resolved_account_name": "Account", "resolved_account_id": "Account ID",
    "outcome": "Outcome", "created_date": "Created", "close_date": "Close date",
    "segment": "Segment", "region": "Region", "industry": "Industry",
    "product_tier": "Plan", "value_metric": "Pricing model",
    "list_acv": "List value (annual)", "booked_acv": "Booked value (annual)",
    "platform_fee_acv": "Platform fee (annual)", "usage_acv": "Usage value (annual)",
    "term_months": "Term (months)", "quantity": "Quantity", "rep_id": "Rep",
    "approved_by": "Approved by", "competitor_present": "Competitor in deal",
    "lost_reason": "Lost reason", "discount_pct": "Discount %",
    "price_realization": "Price realization", "discount_amount": "Discount given",
    "win_rate": "Win rate", "discount_band": "Discount band", "deals": "Deals",
    "won": "Won", "avg_discount": "Avg discount",
    "excess_discount_dollars": "Excess discount", "off_policy": "Above policy",
    "off_policy_unapproved": "Above policy, no approval",
    "is_quarter_end": "Closed near quarter end", "is_won": "Won",
    "quarter": "Quarter", "cycle_days": "Cycle (days)",
    "days_to_quarter_end": "Days to quarter end",
}


def relabel(df):
    """Rename a frame's columns to human-readable labels for display."""
    return df.rename(columns={c: LABELS.get(c, c) for c in df.columns})


def field_label(name: str) -> str:
    return LABELS.get(name, name)


def pretty_factors(expl_df):
    """Turn raw SHAP contributions into a plain 'what drove this' table."""
    d = expl_df[expl_df["feature"] != "<base>"].copy()
    d["Factor"] = d["feature"].map(field_label)
    d["Effect on win chance"] = d["contribution"].map(
        lambda c: "Raises win odds" if c > 0 else "Lowers win odds")
    return d[["Factor", "Effect on win chance"]]
