"""Numeric-fidelity evals (PK-29).

Property under test: every figure in narrated or templated text traces to a
numeric leaf of the source dict it was built from, at the stated precision.
"The LLM never computes a number": a figure in text that is not in the source
is a failing test, not a warning.

Everything here is offline. The provider is patched at its lowest call site
(anthropic.Anthropic, inside pricing.assist._complete), the patch is asserted
to have been hit, and socket connects are blocked so a stray network call
fails loudly.

Known limits of the checker (documented, not hidden):
  * Small integers (counts under ~50) can match an unrelated numeric leaf by
    coincidence. Money and percent figures, the ones a finance reader checks,
    are the strongly protected class.
  * Percent tokens match a leaf either as a fraction (x100) or as an
    already-percent value, because the digest and the opportunities use both.
"""
from __future__ import annotations

import json
import math
import re
import socket
from pathlib import Path
from types import SimpleNamespace

import anthropic
import numpy as np
import pandas as pd
import pytest

from pricing import assist, copilot, diagnostic, governance
from pricing.copilot import _money, _pct

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "data" / "synthetic" / "deals.csv"

# Template constants the code writes into prose on purpose (not data). Each is
# an explicit, reviewed exception with its source line.
TEMPLATE_CONSTANTS = (
    r"\b2 pt\b",   # copilot._opp_raise_prices: "Test a 2 pt list price increase"
)

_SUFFIX = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6,
           "b": 1e9, "billion": 1e9}
_TOKEN = re.compile(
    r"""
    (?P<money>\$(?P<m>\d[\d,]*(?:\.\d+)?)(?:\s?(?P<suf>million|thousand|billion|[MKBmkb])\b)?)
  | (?P<pct>(?P<p>\d+(?:\.\d+)?)\s?(?:%|percent))
  | (?P<num>(?<![\w.\-])\d[\d,]*(?:\.\d+)?)
    """, re.X)


# --- the helper: numeric leaves of a source structure -----------------------

def numeric_leaves(obj, *, skip_keys=("data",)) -> list[float]:
    """Every numeric value reachable in `obj`: scalars, DataFrame/array cells,
    container lengths, and numbers embedded in string leaves (e.g. a band
    label "5-10%"). Booleans and NaN are not figures."""
    out: list[float] = []

    def add(x):
        x = float(x)
        if math.isfinite(x):
            out.append(x)

    def walk(o):
        if o is None or isinstance(o, (bool, np.bool_)):
            return
        if isinstance(o, (int, float, np.integer, np.floating)):
            add(o)
        elif isinstance(o, str):
            for m in re.finditer(r"\d+(?:\.\d+)?", o.replace(",", "")):
                add(m.group())
        elif isinstance(o, dict):
            for k, v in o.items():
                if k in skip_keys:
                    continue
                walk(v)
        elif isinstance(o, pd.DataFrame):
            add(len(o))
            num = o.select_dtypes("number")
            for v in np.unique(num.to_numpy(dtype=float).ravel()):
                add(v)
            # Column sums: the code legitimately totals a surfaced frame.
            for v in num.sum().to_numpy(dtype=float):
                add(v)
            for col in o.columns.difference(num.columns):
                for s in o[col].dropna().astype(str).unique()[:200]:
                    walk(s)
        elif isinstance(o, pd.Series):
            walk(o.to_frame())
        elif isinstance(o, np.ndarray):
            for v in np.unique(o.astype(float).ravel()):
                add(v)
        elif isinstance(o, (list, tuple, set)):
            add(len(o))
            for v in o:
                walk(v)

    walk(obj)
    return out


class _Index:
    """Lazily built sets of leaf renderings per (kind, precision)."""

    def __init__(self, source):
        self.leaves = numeric_leaves(source)
        self._cache: dict = {}

    def _set(self, key, fn):
        if key not in self._cache:
            self._cache[key] = {fn(x) for x in self.leaves}
        return self._cache[key]

    def has_money(self, text: str, d: int, scale: float) -> bool:
        return text in self._set(("$", d, scale), lambda x: f"{x / scale:.{d}f}")

    def has_pct(self, text: str, d: int) -> bool:
        return (text in self._set(("%x", d), lambda x: f"{x * 100:.{d}f}")
                or text in self._set(("%", d), lambda x: f"{x:.{d}f}"))

    def has_num(self, text: str, d: int) -> bool:
        return text in self._set(("n", d), lambda x: f"{x:.{d}f}")


def _decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def figures_in(text: str) -> list[str]:
    """The figure tokens parsed out of text (money, percent, plain numbers)."""
    for pat in TEMPLATE_CONSTANTS:
        text = re.sub(pat, " ", text)
    return [m.group(0) for m in _TOKEN.finditer(text)]


def untraceable_figures(text: str, source) -> list[str]:
    """Figures in `text` with no numeric leaf in `source` at the same precision.

    Reference formatting is copilot._money (whole dollars) and copilot._pct
    (one decimal percent); other precisions are compared at the precision the
    text states. An empty list means every figure traces.
    """
    idx = source if isinstance(source, _Index) else _Index(source)
    for pat in TEMPLATE_CONSTANTS:
        text = re.sub(pat, " ", text)
    bad = []
    for m in _TOKEN.finditer(text):
        if m.group("money"):
            raw = m.group("m").replace(",", "")
            scale = _SUFFIX.get((m.group("suf") or "").lower(), 1.0)
            ok = idx.has_money(raw, _decimals(raw), scale)
        elif m.group("pct"):
            p = m.group("p")
            ok = idx.has_pct(p, _decimals(p))
        else:
            raw = m.group("num").replace(",", "")
            ok = idx.has_num(raw, _decimals(raw))
        if not ok:
            bad.append(m.group(0))
    return bad


# --- shared fixtures ---------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _blocked(self, *a, **k):
        raise AssertionError("network call attempted in an offline eval")
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.delenv("DATABASE_URL", raising=False)


@pytest.fixture(scope="module")
def analysis() -> dict:
    return diagnostic.run(BOOK)


@pytest.fixture(scope="module")
def index(analysis) -> _Index:
    return _Index(analysis)


def _install_provider(monkeypatch, reply: str):
    """Patch anthropic.Anthropic (the lowest call site in assist._complete).
    Returns a list recording each call's kwargs, so tests can assert the
    patch was hit and inspect the prompt."""
    calls: list[dict] = []

    class _Messages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=reply)])

    class _Fake:
        def __init__(self, **kwargs):
            self.init = kwargs
            self.messages = _Messages()

    monkeypatch.setattr(anthropic, "Anthropic", _Fake)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-offline-test")
    return calls


def opp_texts(o: copilot.Opportunity) -> list[str]:
    d = o.to_dict()
    return ([d["scope"], d["current"], d["recommended"], d["methodology"],
             d["caveat"]] + [e["value"] for e in d["evidence"]])


# --- helper self-tests -------------------------------------------------------

def test_helper_parses_money_percent_and_counts():
    got = figures_in("$1,234 at 5.0% across 612 deals, ~$4.8M, 9.2 percent")
    assert got == ["$1,234", "5.0%", "612", "$4.8M", "9.2 percent"]


def test_helper_compares_at_the_stated_precision():
    src = {"a": 4_812_345.6, "b": 0.0512, "c": 612}
    assert untraceable_figures("$4,812,346 and 5.1% and 612 deals", src) == []
    assert untraceable_figures("$4.8M", src) == []
    # Right digits, wrong precision, is a different figure.
    assert untraceable_figures("$4,812,345", src) == ["$4,812,345"]
    assert untraceable_figures("5.2%", src) == ["5.2%"]


# --- opportunities over the synthetic book -----------------------------------

def test_opportunity_text_traces_to_the_analysis_dict(analysis, index):
    opps = copilot.opportunities(analysis)
    assert opps, "synthetic book produced no opportunities"
    for o in opps:
        for t in opp_texts(o):
            assert untraceable_figures(t, index) == [], (o.scope, t)


def test_synthetic_book_covers_five_of_seven_opportunity_types(analysis):
    prefixes = {o.id.split("-")[0] for o in copilot.opportunities(analysis)}
    assert {"defended", "excess", "offpolicy", "qe", "od"} <= prefixes


@pytest.mark.xfail(
    strict=True,
    reason="PK-74, pricing/copilot.py:530: _opp_investigate sums the "
           "'discount_amount' column but the real top_leak_deals frame "
           "(metrics.top_leak_deals, via diagnostic.analyze) carries "
           "'excess_discount_dollars'. The investigate opportunity never fires "
           "on a real book; existing unit tests pass only because their "
           "fixture invents a discount_amount column. raise_price does not "
           "fire either, which is a data property of the synthetic book "
           "(no segment reaches win>=70% and realization>=85%), not a bug.")
def test_synthetic_book_produces_all_seven_types(analysis):
    prefixes = {o.id.split("-")[0] for o in copilot.opportunities(analysis)}
    assert {"defended", "excess", "offpolicy", "qe", "od", "invest",
            "raise"} <= prefixes


def test_all_seven_types_trace_on_the_fixture_dict():
    """Fixture dict that fires every extractor, so the seven-type coverage is
    real even though the synthetic book fires five."""
    from tests.test_copilot import _base_analysis
    a = _base_analysis()
    opps = copilot.opportunities(a)
    prefixes = {o.id.split("-")[0] for o in opps}
    assert {"defended", "excess", "offpolicy", "qe", "od", "invest",
            "raise"} <= prefixes
    idx = _Index(a)
    for o in opps:
        for t in opp_texts(o):
            assert untraceable_figures(t, idx) == [], (o.scope, t)


# --- digest text -------------------------------------------------------------

def test_weekly_digest_text_traces_to_analysis_and_log(analysis):
    store = governance.DecisionStore()
    store.insert(kind="exception", deal_id="D-22", requested_by="rep@x.com",
                 payload={"deal_id": "D-22", "requested_discount_pct": 22.0,
                          "requested_by": "rep@x.com",
                          "verdict": {"below_floor": True}})
    store.insert(kind="copilot", payload={"session_id": "s1"})
    d = governance.build_digest(analysis=analysis, store=store)
    entries = store.list(limit=100)
    source = {"analysis": analysis, "log": [e["payload"] for e in entries],
              "window_days": d["window_days"],
              "floor_pct": governance.FLOOR_PCT_DEFAULT,
              "counts": {k: d["stats"][k] for k in
                         ("exceptions_total", "exceptions_below_floor",
                          "copilot_decisions")}}
    idx = _Index(source)
    texts = [d["headline"]] + d["lines"]
    assert any("percent" in t for t in texts)
    for t in texts:
        assert untraceable_figures(t, idx) == [], t


# --- offline narration through the real provider seam ------------------------

def test_summary_facts_text_traces_to_the_result(analysis, index):
    assert untraceable_figures(assist.summary_facts(analysis), index) == []


def test_recorded_executive_summary_traces_and_prompt_is_aggregates(
        monkeypatch, analysis, index):
    ov, lk = analysis["overview"], analysis["leakage"]
    recorded = (
        f"The headline upside is {_money(lk['excess_vs_reference_won'])}, "
        f"{_pct(lk['excess_pct_of_booked'])} of booked ACV of "
        f"{_money(ov['booked_acv_won'])}. Price realization is "
        f"{_pct(ov['price_realization_won'])}. About "
        f"${lk['off_policy_leakage_won'] / 1e6:.1f}M sat above policy. This "
        "is correlational and based on price realization, not cost-based "
        "margin. Next step: review deals above the reference one by one."
    )
    calls = _install_provider(monkeypatch, recorded)
    text = assist.executive_summary(analysis)
    assert len(calls) == 1, "the provider patch was not hit"
    assert text == recorded
    # Data minimization: the prompt is the aggregate facts block, not rows.
    assert calls[0]["messages"][0]["content"] == assist.summary_facts(analysis)
    assert untraceable_figures(text, index) == []


def test_recorded_copilot_narration_traces_to_the_opportunity_json(
        monkeypatch, analysis):
    opps = copilot.opportunities(analysis)[:3]
    parts = [f"{o.scope}: {_money(o.revenue_impact_usd)} at "
             f"{o.confidence:.0%} confidence [A]." for o in opps]
    recorded = ("Why are we losing deals? " + " ".join(parts)
                + " These are correlational estimates at an assumed "
                  "recoverable share, not bookable margin, and are not "
                  "additive.")
    calls = _install_provider(monkeypatch, recorded)
    ans = copilot.answer_canonical("opportunities_over", analysis)
    assert len(calls) == 1, "the provider patch was not hit"
    assert ans.narrated and ans.text == recorded
    # The model's input is the deterministic opportunity JSON, nothing else.
    user = calls[0]["messages"][0]["content"]
    payload = json.loads(user.split("OPPORTUNITIES (JSON, deterministic):\n")[1])
    assert [p["revenue_impact_usd"] for p in payload] == [
        o.revenue_impact_usd for o in ans.opportunities]
    idx = _Index({"analysis": analysis, "opps": payload})
    for p in payload:
        for t in (p["scope"], p["current"], p["recommended"]):
            assert untraceable_figures(t, idx) == []
    assert untraceable_figures(ans.text, idx) == []


# --- the checker must fail when it should ------------------------------------

def test_corrupted_figure_in_opportunity_text_is_caught(analysis, index):
    o = next(o for o in copilot.opportunities(analysis)
             if o.id.startswith("excess"))
    good = o.evidence[0].value
    assert untraceable_figures(good, index) == []
    money = re.search(r"\$[\d,]+", good).group(0)
    bumped = f"${int(money[1:].replace(',', '')) + 1:,}"
    bad = good.replace(money, bumped)
    assert untraceable_figures(bad, index) == [bumped]
    # A percentage moved by 40 points also fails. (A one-tenth nudge can land
    # on an unrelated leaf by coincidence: the documented limit of the checker.)
    pct = re.search(r"\d+\.\d%", o.current).group(0)
    nudged = f"{float(pct[:-1]) + 40.0:.1f}%"
    assert nudged in untraceable_figures(o.current.replace(pct, nudged), index)


def test_invented_number_in_recorded_narration_is_caught(
        monkeypatch, analysis, index):
    _install_provider(monkeypatch, "Upside is $9,999,999 or 77.7% of ACV.")
    text = assist.executive_summary(analysis)
    assert untraceable_figures(text, index) == ["$9,999,999", "77.7%"]
