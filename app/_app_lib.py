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

from pricing import metrics, model  # noqa: E402  (re-exported for pages)
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown {{ font-family: 'Inter', sans-serif; }}
.pk-word {{ font-weight: 700; font-size: 1.5rem; letter-spacing: -0.5px; }}
.pk-word .a {{ color: {BRAND['navy']}; }}
.pk-word .b {{ color: {BRAND['teal']}; }}
.pk-tag {{ color: {BRAND['slate']}; font-size: 0.9rem; margin-top: -4px; }}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
.pk-mark {{ vertical-align: middle; margin-right: 10px; }}
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


def money(x: float) -> str:
    return f"${x:,.0f}"


def pct(x: float) -> str:
    return f"{x:.1%}"
