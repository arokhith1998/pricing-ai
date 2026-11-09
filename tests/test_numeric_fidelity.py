"""Numeric-fidelity evals (PK-29).

Property under test: every figure in templated or narrated text traces to a
signed numeric leaf of the source dict it was built from, at the stated
precision. "The LLM never computes a number": a figure in text that is not in
the source is a failing test, not a warning.

NO REAL MODEL OUTPUT IS EVALUATED HERE. The "synthetic replies" are hand-built
mimics of what the system prompts ask a model to write, returned through a
patched provider (anthropic.Anthropic, the lowest call site in
assist._complete; the patch is asserted hit and socket connects are blocked).
They prove the plumbing and the checker, not what a model says. Capturing one
real provider response with its model id and date is a follow-up.

What is traced against what:
  * Copilot opportunities: each opportunity's sentences are traced to THAT
    opportunity's own source (its evidence paths plus the analysis section it
    reads, narrowed to its own row for per-segment and per-slice items). This
    is the real protection.
  * Digest, summary_facts and the synthetic narrations: no per-item source
    exists, so these are traced to the WHOLE analysis dict, which is much
    weaker (see the measured classes below).

Signs: a leading minus, the word "minus", and accounting parentheses around a
money or percent figure make the figure negative, and the sign is compared, so
"-18%" cannot trace to a positive 0.18 and "-5.2%" traces to -0.052.

Measured strength against the whole synthetic-book index (see
test_measured_coincidence_rates_stay_in_the_documented_bands; fabricated
figures drawn at random, the share that still "traces" by coincidence):
  - whole-dollar money ($8,946,770): 0.0%, strong. A fabricated figure does not
    trace.
  - one-decimal percent (13.3%): about 20%, weak.
  - $X.XM style money ($8.9M): about 9%, weak.
  - integer percent (13%): about 76%, near meaningless.
  - small counts (1 to 40 deals): about 33%, weak to near meaningless.
This is why the opportunity test traces to a per-item source and why the digest
and summary checks, which have only the whole dict, should be read as
"no figure is wildly off", not as proof of each figure.

Formats the parser does not understand fail closed (the bare number is compared
unscaled and almost never matches): "1.2M" without "$", "$1.2 bn", "18 pct",
"12 bps", and "Q4 2026". A reply that uses them is reported untraceable and
needs the parser extended, never a silent pass.

Percent tokens match a leaf either as a fraction (x100) or as an already-percent
value, because the digest and the opportunities use both.
"""
from __future__ import annotations

import json
import math
import random
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
    (?P<money>\$(?P<ms>[-−])?(?P<m>\d[\d,]*(?:\.\d+)?)
        (?:\s?(?P<suf>million|thousand|billion|[MKBmkb])\b)?)
  | (?P<pct>(?P<p>\d+(?:\.\d+)?)\s?(?:%|percent))
  | (?P<num>(?<![\w.])\d[\d,]*(?:\.\d+)?)
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


def _strip_constants(text: str) -> str:
    for pat in TEMPLATE_CONSTANTS:
        text = re.sub(pat, " ", text)
    return text


def _scan(text: str):
    """Yield (match, kind, negative) for each figure; identifiers and ranges
    such as "D-22" or "OPP-00280" are skipped, not parsed as figures."""
    for m in _TOKEN.finditer(text):
        kind = m.lastgroup if m.lastgroup in ("money", "pct", "num") else (
            "money" if m.group("money") else "pct" if m.group("pct") else "num")
        pre = text[:m.start()]
        neg = bool(m.group("ms"))
        if pre and pre[-1] in "-−":
            glued = len(pre) > 1 and (pre[-2].isalnum() or pre[-2] in "._")
            if not glued:
                neg = True
            elif kind == "num":
                continue          # identifier or range tail, not a figure
        elif re.search(r"\bminus\s+$", pre, flags=re.I):
            neg = True
        elif (kind in ("money", "pct") and pre.endswith("(")
              and text[m.end():m.end() + 1] == ")"):
            neg = True            # accounting parentheses
        yield m, kind, neg


def figures_in(text: str) -> list[str]:
    """The figure tokens parsed out of text (money, percent, plain numbers),
    with a leading "-" when the figure is negative."""
    return [("-" if neg and not m.group(0).startswith("$-") else "") + m.group(0)
            for m, _, neg in _scan(_strip_constants(text))]


def untraceable_figures(text: str, source) -> list[str]:
    """Figures in `text` with no signed numeric leaf in `source` at the same
    precision. Reference formatting is copilot._money (whole dollars) and
    copilot._pct (one decimal percent); other precisions are compared at the
    precision the text states. Sign is compared. An empty list means every
    figure traces."""
    idx = source if isinstance(source, _Index) else _Index(source)
    bad = []
    for m, kind, neg in _scan(_strip_constants(text)):
        sign = "-" if neg else ""
        if kind == "money":
            raw = m.group("m").replace(",", "")
            scale = _SUFFIX.get((m.group("suf") or "").lower(), 1.0)
            ok = idx.has_money(sign + raw, _decimals(raw), scale)
        elif kind == "pct":
            p = m.group("p")
            ok = idx.has_pct(sign + p, _decimals(p))
        else:
            raw = m.group("num").replace(",", "")
            ok = idx.has_num(sign + raw, _decimals(raw))
        if not ok:
            bad.append(("-" if neg and not m.group(0).startswith("$-") else "")
                       + m.group(0))
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


def install_synthetic_provider(monkeypatch, reply: str):
    """Patch anthropic.Anthropic (the lowest call site in assist._complete) to
    return `reply`, a hand-written synthetic reply, never real model output.
    Returns a list recording each call's kwargs, so tests can assert the patch
    was hit and inspect the prompt."""
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


def _dig(a: dict, path: str):
    cur = a
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


# The analysis leaves each extractor in pricing/copilot.py actually reads
# (dotted paths). A per-item source is built from these and nothing broader.
_READS = {
    "defended": ["defended_vs_investigate.defended_value",
                 "defended_vs_investigate.defended_deals",
                 "defended_vs_investigate.investigate_value",
                 "defended_vs_investigate.investigate_deals",
                 "defended_vs_investigate.reference_threshold",
                 "defended_vs_investigate.defended_pct_of_booked"],
    "excess": ["leakage.excess_vs_segment_reference_won",
               "leakage.excess_segment_pct_of_booked",
               "leakage.reference_threshold", "leakage.reference_band",
               "leakage.deals_above_segment_reference",
               "overview.booked_acv_won"],
    "offpolicy": ["leakage.off_policy_leakage_won", "leakage.policy_threshold",
                  "governance.off_policy_unapproved_won"],
    "qe": ["quarter_end.attributable_discount_won", "quarter_end.lift",
           "quarter_end.qe_deals", "quarter_end.rest_avg_discount"],
    "invest": ["top_leak_deals"],
}


def opp_source(o: copilot.Opportunity, analysis: dict) -> dict:
    """The opportunity's OWN source: only the analysis leaves its extractor
    reads (_READS), narrowed to its own row for per-segment and per-slice
    items. Not the whole analysis."""
    kind = o.id.split("-")[0]
    if kind == "od":
        dim = o.scope.split(":")[0].lower()
        name = o.scope.split(": ", 1)[1]
        frame = analysis["hierarchy_slices"][dim]
        return {"row": frame[frame[dim].astype(str) == name],
                "reference_threshold":
                    analysis["leakage"]["reference_threshold"]}
    if kind == "raise":
        seg = o.scope.split(": ", 1)[1]
        frame = analysis["realization_by_segment"]
        return {"row": frame[frame["segment"].astype(str) == seg]}
    src = {}
    for path in _READS[kind]:
        v = _dig(analysis, path)
        if v is not None:
            src[path] = v
    return src


# Constants the code writes into methodology prose (not data). Each is an
# explicit reviewed exception; see copilot.py recoverable_share assignments.
TEMPLATE_CONSTANTS += (
    r"\b\d+% recoverable assumption",
)


def assert_opportunity_traces(o: copilot.Opportunity, analysis: dict) -> None:
    src = _Index(opp_source(o, analysis))
    for t in opp_texts(o):
        assert untraceable_figures(t, src) == [], (o.id, o.scope, t)


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


def test_helper_skips_identifiers_and_ranges_but_checks_range_percents():
    assert untraceable_figures("deal D-22 and OPP-00280", {"x": 1}) == []
    assert untraceable_figures("the 5-10% band", {"x": 0.10, "y": 5}) == []
    assert untraceable_figures("the 5-12% band", {"x": 0.10, "y": 5}) == ["12%"]


def test_helper_compares_signed_values():
    pos18, neg52 = {"a": 0.18}, {"a": -0.052}
    # A negative figure cannot trace to a positive leaf, in every notation.
    for text in ("-18%", "−18%", "minus 18%", "(18%)"):
        assert untraceable_figures(text, pos18) != [], text
    assert untraceable_figures("18%", pos18) == []
    assert untraceable_figures("+18%", pos18) == []
    # A correct negative traces to the negative leaf, and not to a positive.
    for text in ("-5.2%", "−5.2%", "minus 5.2%", "(5.2%)"):
        assert untraceable_figures(text, neg52) == [], text
        assert untraceable_figures(text, {"a": 0.052}) != [], text
    assert untraceable_figures("5.2%", neg52) != []
    # Money, including accounting parentheses and "$-".
    assert untraceable_figures("($1,234)", {"a": -1234}) == []
    assert untraceable_figures("($1,234)", {"a": 1234}) != []
    assert untraceable_figures("$-1,234", {"a": -1234}) == []
    assert untraceable_figures("-$1,234", {"a": 1234}) != []
    # Parentheses around a count are prose, not a negative.
    assert untraceable_figures("$64,647,544 (1,087 deals)",
                               {"a": 64647544, "b": 1087}) == []


def test_unparsed_formats_fail_closed():
    src = {"a": 1_200_000.0, "b": 0.18, "c": 0.0012, "d": 4}
    for text in ("1.2M", "$1.2 bn", "18 pct", "12 bps", "Q4 2026"):
        assert untraceable_figures(text, src) != [], text


def test_measured_coincidence_rates_stay_in_the_documented_bands(analysis, index):
    """How strong is each figure class against the WHOLE-dict index? Draw
    random fabricated figures and count how many trace by coincidence. This is
    why the opportunity test uses per-item sources."""
    rng = random.Random(29)

    def rate(make, n=400):
        return sum(not untraceable_figures(make(), index)
                   for _ in range(n)) / n

    whole_dollar = rate(lambda: f"${rng.randint(1_000_000, 90_000_000):,}")
    millions_1dp = rate(lambda: f"${rng.uniform(1, 90):.1f}M")
    pct_1dp = rate(lambda: f"{rng.uniform(1, 60):.1f}%")
    pct_int = rate(lambda: f"{rng.randint(1, 60)}%")
    small_count = rate(lambda: f"{rng.randint(1, 40)} deals")
    assert whole_dollar < 0.02          # strong
    assert millions_1dp > 0.05          # weak
    assert pct_1dp > 0.10               # weak
    assert pct_int > 0.60               # near meaningless
    assert small_count > 0.20           # weak, roughly one in three
    print(f"MEASURED whole_dollar={whole_dollar:.3f} millions_1dp="
          f"{millions_1dp:.3f} pct_1dp={pct_1dp:.3f} pct_int={pct_int:.3f} "
          f"small_count={small_count:.3f}")


# --- opportunities over the synthetic book -----------------------------------

def test_each_opportunity_traces_to_its_own_source(analysis):
    opps = copilot.opportunities(analysis)
    assert opps, "synthetic book produced no opportunities"
    for o in opps:
        assert_opportunity_traces(o, analysis)


def test_a_figure_from_another_opportunity_does_not_trace(analysis):
    """The per-item source is what protects: a real figure from a different
    opportunity is rejected, though it is in the whole analysis dict."""
    opps = {o.id.split("-")[0]: o for o in copilot.opportunities(analysis)}
    other = opps["offpolicy"].evidence[0].value      # "$X discounted above ..."
    swapped = opps["excess"].evidence[0].value.replace(
        re.search(r"\$[\d,]+", opps["excess"].evidence[0].value).group(0),
        re.search(r"\$[\d,]+", other).group(0))
    assert untraceable_figures(swapped, _Index(analysis)) == []   # whole dict: passes
    assert untraceable_figures(
        swapped, _Index(opp_source(opps["excess"], analysis))) != []


def test_synthetic_book_covers_five_of_seven_opportunity_types(analysis):
    prefixes = {o.id.split("-")[0] for o in copilot.opportunities(analysis)}
    assert {"defended", "excess", "offpolicy", "qe", "od"} <= prefixes


@pytest.mark.xfail(
    strict=True,
    reason="PK-74, pricing/copilot.py:530: _opp_investigate sums the "
           "'discount_amount' column but the real top_leak_deals frame "
           "(metrics.top_leak_deals, via diagnostic.analyze) carries "
           "'excess_discount_dollars', so the investigate opportunity never "
           "fires on a real book. Existing unit tests pass only because their "
           "fixture invents a discount_amount column. This tripwire flips to a "
           "failure when PK-74 lands: remove the marker then.")
def test_synthetic_book_fires_the_investigate_opportunity(analysis):
    prefixes = {o.id.split("-")[0] for o in copilot.opportunities(analysis)}
    assert "invest" in prefixes


def test_raise_price_fires_when_a_segment_reaches_the_thresholds():
    """raise_price needs win >= 70%, realization >= 85%, >= 25 deals. The
    synthetic book has no such segment (a property of its data, not a bug), so
    a fixture that reaches the thresholds proves the extractor and its text."""
    a = {
        "realization_by_segment": pd.DataFrame([
            {"segment": "Enterprise", "win_rate": 0.72,
             "price_realization": 0.88, "deals": 120,
             "booked_acv": 22_000_000.0},
            {"segment": "SMB", "win_rate": 0.40, "price_realization": 0.75,
             "deals": 600, "booked_acv": 13_000_000.0},
        ]),
    }
    opps = copilot._opp_raise_prices(a)
    assert [o.scope for o in opps] == ["Segment: Enterprise"]
    assert_opportunity_traces(opps[0], a)


def test_all_seven_types_trace_on_the_fixture_dict():
    """Fixture dict that fires every extractor, so the seven-type coverage is
    real even though the synthetic book fires five."""
    from tests.test_copilot import _base_analysis
    a = _base_analysis()
    opps = copilot.opportunities(a)
    prefixes = {o.id.split("-")[0] for o in opps}
    assert {"defended", "excess", "offpolicy", "qe", "od", "invest",
            "raise"} <= prefixes
    for o in opps:
        assert_opportunity_traces(o, a)


# --- digest text (whole-dict source: no per-item dict exists) ----------------

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


# --- offline narration through the provider seam (synthetic replies) ---------

def test_summary_facts_text_traces_to_the_result(analysis, index):
    assert untraceable_figures(assist.summary_facts(analysis), index) == []


def test_synthetic_summary_reply_traces_and_prompt_is_aggregates(
        monkeypatch, analysis, index):
    ov, lk = analysis["overview"], analysis["leakage"]
    reply = (
        f"The headline upside is {_money(lk['excess_vs_reference_won'])}, "
        f"{_pct(lk['excess_pct_of_booked'])} of booked ACV of "
        f"{_money(ov['booked_acv_won'])}. Price realization is "
        f"{_pct(ov['price_realization_won'])}. About "
        f"${lk['off_policy_leakage_won'] / 1e6:.1f}M sat above policy. This "
        "is correlational and based on price realization, not cost-based "
        "margin. Next step: review deals above the reference one by one."
    )
    calls = install_synthetic_provider(monkeypatch, reply)
    text = assist.executive_summary(analysis)
    assert len(calls) == 1, "the provider patch was not hit"
    assert text == reply
    # Data minimization: the prompt is the aggregate facts block, not rows.
    assert calls[0]["messages"][0]["content"] == assist.summary_facts(analysis)
    assert untraceable_figures(text, index) == []


def test_synthetic_copilot_reply_traces_to_the_opportunity_json(
        monkeypatch, analysis):
    opps = copilot.opportunities(analysis)[:3]
    parts = [f"{o.scope}: {_money(o.revenue_impact_usd)} at "
             f"{o.confidence:.0%} confidence [A]." for o in opps]
    reply = ("Why are we losing deals? " + " ".join(parts)
             + " These are correlational estimates at an assumed "
               "recoverable share, not bookable margin, and are not "
               "additive.")
    calls = install_synthetic_provider(monkeypatch, reply)
    ans = copilot.answer_canonical("opportunities_over", analysis)
    assert len(calls) == 1, "the provider patch was not hit"
    assert ans.narrated and ans.text == reply
    # The model's input is the deterministic opportunity JSON, nothing else.
    user = calls[0]["messages"][0]["content"]
    payload = json.loads(user.split("OPPORTUNITIES (JSON, deterministic):\n")[1])
    assert [p["revenue_impact_usd"] for p in payload] == [
        o.revenue_impact_usd for o in ans.opportunities]
    # Whole-dict plus the opportunity JSON: the reply mixes items.
    idx = _Index({"analysis": analysis, "opps": payload})
    assert untraceable_figures(ans.text, idx) == []


# --- the checker must fail when it should ------------------------------------

def test_corrupted_figure_in_opportunity_text_is_caught(analysis):
    o = next(o for o in copilot.opportunities(analysis)
             if o.id.startswith("excess"))
    own = _Index(opp_source(o, analysis))
    good = o.evidence[0].value
    assert untraceable_figures(good, own) == []
    money = re.search(r"\$[\d,]+", good).group(0)
    bumped = f"${int(money[1:].replace(',', '')) + 1:,}"
    bad = good.replace(money, bumped)
    assert untraceable_figures(bad, own) == [bumped]
    # A percentage moved by one tenth fails against the per-item source.
    pct = re.search(r"\d+\.\d%", o.current).group(0)
    nudged = f"{float(pct[:-1]) + 0.1:.1f}%"
    assert nudged in untraceable_figures(o.current.replace(pct, nudged), own)


def test_invented_number_in_a_synthetic_reply_is_caught(
        monkeypatch, analysis, index):
    install_synthetic_provider(monkeypatch, "Upside is $9,999,999 or 77.7% of ACV.")
    text = assist.executive_summary(analysis)
    assert untraceable_figures(text, index) == ["$9,999,999", "77.7%"]
