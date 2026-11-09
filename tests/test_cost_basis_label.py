"""Cost-basis label evals (PK-29, ADR-006 as amended 2026-11-09).

Part 1: the response builder in pricing/cost_basis.py (table tests).
Part 2: the eval against existing narration: with the book's cost_basis at its
default (crm_proxy), the word "margin" may appear in generated text only inside
the four whole-phrase negations in cost_basis.allowed_phrases(): "not margin",
"never labeled margin", "not bookable margin", "not cost-based margin". That
tuple is the only allowlist; this file keeps none and classifies every
occurrence through cost_basis.margin_violations.

IMPORTANT: no real model output is evaluated here. The "synthetic reply" texts
are hand-written mimics of what the system prompts ask for, returned through a
patched provider (anthropic.Anthropic, hit asserted, sockets blocked). They
prove the plumbing and the guard, not what a model actually says. Capturing one
real provider response (model id and date) is a follow-up.
"""
from __future__ import annotations

import re
import socket
from pathlib import Path

import pytest

from pricing import assist, copilot, cost_basis, diagnostic, governance
from pricing.cost_basis import (
    MarginLabelError, MarginRefusedError, allowed_phrases,
    assert_no_margin_for_proxy, label_for, margin_violations,
    refuse_margin_for_proxy, weakest_basis,
)
from pricing.schema import CostBasis
from tests.test_numeric_fidelity import install_synthetic_provider, opp_texts

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "data" / "synthetic" / "deals.csv"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _blocked(self, *a, **k):
        raise AssertionError("network call attempted in an offline eval")
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.delenv("DATABASE_URL", raising=False)


# --- Part 1: the builder ------------------------------------------------------

PROXY = "cost proxy, not margin"
DECLARED = "contribution margin, customer-supplied cost basis"
ERP = "gross margin, ERP-verified cost"


@pytest.mark.parametrize("value, label, may", [
    ("crm_proxy", PROXY, False),
    ("declared_cost", DECLARED, True),
    ("erp_verified", ERP, True),
    (CostBasis.CRM_PROXY, PROXY, False),
    (CostBasis.DECLARED_COST, DECLARED, True),
    (CostBasis.ERP_VERIFIED, ERP, True),
    ("  ERP_Verified ", ERP, True),          # trimmed, case-insensitive
    ("unknown", PROXY, False),
    ("net_margin", PROXY, False),
    ("", PROXY, False),
    (None, PROXY, False),
    (42, PROXY, False),
])
def test_label_table(value, label, may):
    got = label_for(value)
    assert got.label == label
    assert got.may_say_margin is may
    assert got.labeled == label


def test_label_attaches_to_a_caller_formatted_figure():
    assert label_for("crm_proxy", "$1,200").labeled == f"$1,200, {PROXY}"
    assert label_for("erp_verified", "41.0%").labeled == f"41.0%, {ERP}"


def test_builder_values_match_the_schema_enum():
    assert {m.value for m in CostBasis} == set(cost_basis.LABELS)


def test_no_label_says_net_margin_and_only_proxy_forbids_margin():
    for text in cost_basis.LABELS.values():
        assert "net margin" not in text.lower()
    for basis in ("declared_cost", "erp_verified"):
        assert "margin" in label_for(basis).label
    # The proxy label passes its own guard.
    assert margin_violations(PROXY, "crm_proxy") == []


def test_allowlist_is_pinned_to_the_four_adr_006_phrases():
    assert allowed_phrases() == (
        "not margin",
        "never labeled margin",
        "not bookable margin",
        "not cost-based margin",
    )


def test_guard_passes_the_four_allowed_phrases_and_the_proxy_label():
    for phrase in allowed_phrases():
        for text in (phrase, f"The figure is {phrase}.", f"{phrase}, and more",
                     f"It is {phrase.upper()}", f"so  {phrase.replace(' ', '  ')} ;"):
            assert_no_margin_for_proxy(text, "crm_proxy")
    assert_no_margin_for_proxy(PROXY, "crm_proxy")
    assert_no_margin_for_proxy("no figure here", "crm_proxy")


@pytest.mark.parametrize("bad", [
    "gross margin 40 percent", "Margin", "MARGIN is 12%", "net margin",
    "contribution margin", "This is bookable margin.", "cost-based margin of 12%",
    # Near-misses of an allowed phrase: the phrase must be whole.
    "not margin compression",
    "not margin-dilutive",
    "not margins of 40%",
    "we cannot margin this",
    "not marginal",
    # Whitespace and unicode folding cannot smuggle one through.
    "not margin compression",
    "ＭＡＲＧＩＮ is 40%",   # fullwidth MARGIN
    "mar​gin is 40%",                            # zero width space
])
def test_guard_fails_affirmative_or_near_miss_margin(bad):
    with pytest.raises(MarginLabelError):
        assert_no_margin_for_proxy(bad, "crm_proxy")
    assert margin_violations(bad, "crm_proxy")


def test_bookable_margin_without_not_still_fails_the_guard():
    for bad in ("This is bookable margin.", "cost-based margin of 12%"):
        with pytest.raises(MarginLabelError):
            assert_no_margin_for_proxy(bad, "crm_proxy")


def test_guard_treats_missing_or_unknown_basis_as_proxy():
    for basis in (None, "", "garbage"):
        with pytest.raises(MarginLabelError):
            assert_no_margin_for_proxy("gross margin 40 percent", basis)


def test_guard_passes_for_declared_and_erp():
    for basis in ("declared_cost", "erp_verified"):
        assert_no_margin_for_proxy("gross margin 40 percent", basis)
        assert_no_margin_for_proxy(label_for(basis, "40%").labeled, basis)
        assert margin_violations("gross margin 40 percent", basis) == []


def test_homoglyph_limit_is_real_and_documented():
    """Cross-script lookalikes are NOT folded (see _normalize_text docstring)."""
    assert margin_violations("mаrgin is 40%", "crm_proxy") == []
    assert "homoglyph" in cost_basis._normalize_text.__doc__


def test_refuse_helper_raises_for_proxy_and_not_for_others():
    for basis in ("crm_proxy", None, "unknown", CostBasis.CRM_PROXY):
        with pytest.raises(MarginRefusedError):
            refuse_margin_for_proxy(basis)
    assert refuse_margin_for_proxy("declared_cost") is None
    assert refuse_margin_for_proxy(CostBasis.ERP_VERIFIED) is None


@pytest.mark.parametrize("bases, want", [
    (["erp_verified", "erp_verified"], "erp_verified"),
    (["erp_verified", "declared_cost"], "declared_cost"),
    (["erp_verified", "declared_cost", "crm_proxy"], "crm_proxy"),
    (["declared_cost", "declared_cost"], "declared_cost"),
    (["crm_proxy"], "crm_proxy"),
    (["erp_verified", None], "crm_proxy"),
    (["erp_verified", "garbage"], "crm_proxy"),
    ([], "crm_proxy"),
    ((b for b in ["erp_verified"]), "erp_verified"),   # any iterable
    ([CostBasis.ERP_VERIFIED, CostBasis.DECLARED_COST], "declared_cost"),
])
def test_weakest_basis(bases, want):
    assert weakest_basis(bases) == want


# --- Part 2: the eval against existing narration -----------------------------

def count_margin(text: str) -> int:
    return len(re.findall("margin", text, flags=re.I))


def classify(text: str) -> tuple[int, list[str]]:
    """(allowed occurrences, violation snippets) for crm_proxy output, with
    classification done only by cost_basis.margin_violations."""
    bad = margin_violations(text, "crm_proxy")
    return count_margin(text) - len(bad), bad


@pytest.fixture(scope="module")
def analysis():
    return diagnostic.run(BOOK)


def test_book_cost_basis_defaults_to_crm_proxy(analysis):
    assert set(analysis["data"]["cost_basis"].unique()) == {"crm_proxy"}
    assert weakest_basis(analysis["data"]["cost_basis"]) == "crm_proxy"


def _collect_outputs(monkeypatch, analysis) -> dict[str, str]:
    """Every generated text surface that can run offline, keyed by source."""
    from tests.test_copilot import _base_analysis
    out: dict[str, str] = {}
    for label, a in (("book", analysis), ("fixture", _base_analysis())):
        for i, o in enumerate(copilot.opportunities(a)):
            out[f"opportunity[{label}:{o.id.split('-')[0]}:{i}]"] = \
                "\n".join(opp_texts(o))
    out["copilot._NON_ADDITIVE_CAVEAT"] = copilot._NON_ADDITIVE_CAVEAT
    out["assist.summary_facts"] = assist.summary_facts(analysis)
    d = governance.build_digest(analysis=analysis,
                                store=governance.DecisionStore())
    out["governance.build_digest"] = "\n".join([d["headline"]] + d["lines"])

    # Prompts that shape provider output.
    out["prompt:copilot._COPILOT_SYSTEM"] = copilot._COPILOT_SYSTEM
    out["prompt:assist._SUMMARY_SYSTEM"] = assist._SUMMARY_SYSTEM

    # No-provider fallback text of the copilot.
    with monkeypatch.context() as mp:
        mp.setattr(assist, "has_llm", lambda: False)
        out["copilot.answer_canonical[no provider]"] = (
            copilot.answer_canonical("opportunities_over", analysis).text)

    # Synthetic replies (hand-written mimics, NOT model output) through the
    # patched provider seam.
    replies = {
        "copilot.answer_canonical[synthetic_reply]": (
            "Where are the opportunities? The engine found several. Impacts "
            "are correlational estimates at an assumed recoverable share, "
            "not bookable margin, and are not additive [A]."),
        "assist.executive_summary[synthetic_reply]": (
            "Upside to pursue deal by deal. The figure is correlational and "
            "based on price realization, not cost-based margin [A]."),
    }
    for name, reply in replies.items():
        calls = install_synthetic_provider(monkeypatch, reply)
        if "copilot" in name:
            text = copilot.answer_canonical("opportunities_over", analysis).text
        else:
            text = assist.executive_summary(analysis)
        assert len(calls) == 1, f"provider patch not hit for {name}"
        out[name] = text
    return out


def test_margin_appears_only_in_allowed_negations_for_proxy_data(
        monkeypatch, analysis):
    outputs = _collect_outputs(monkeypatch, analysis)
    findings, allowed_by_source = [], {}
    for source, text in outputs.items():
        ok, bad = classify(text)
        findings += [(source, b) for b in bad]
        if ok:
            allowed_by_source[source] = ok
    assert findings == [], f"affirmative 'margin' for crm_proxy data: {findings}"
    sources = set(allowed_by_source)
    # Inventory: these surfaces carry an allowed negation today.
    assert "prompt:copilot._COPILOT_SYSTEM" in sources
    assert "prompt:assist._SUMMARY_SYSTEM" in sources
    assert any(s.startswith("opportunity[") for s in sources)
    # And these must stay free of the word entirely.
    for clean in ("assist.summary_facts", "governance.build_digest",
                  "copilot.answer_canonical[no provider]",
                  "copilot._NON_ADDITIVE_CAVEAT"):
        assert count_margin(outputs[clean]) == 0, clean


def test_strict_adr_006_reading_no_affirmative_margin_in_any_output(
        monkeypatch, analysis):
    for source, text in _collect_outputs(monkeypatch, analysis).items():
        assert_no_margin_for_proxy(text, "crm_proxy")


def _code_without_comments(path: Path) -> str:
    """Source text with comment-only lines dropped (first non-space char is #)
    and adjacent string literals joined, so "not " / "bookable margin" split
    across lines reads as one phrase."""
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
             if not ln.lstrip().startswith("#")]
    return re.sub(r"""(["'])\s*\n\s*\1""", "", "\n".join(lines))


def test_source_scan_every_margin_word_in_code_is_an_allowed_negation():
    """Static scan so a new affirmative use anywhere in the Python tier trips
    CI, including surfaces that cannot run offline. Comment lines are exempt,
    files are not, except pricing/cost_basis.py itself, which defines the
    label strings and so must contain the word (and has its own tests)."""
    paths = (sorted((ROOT / "pricing").glob("*.py"))
             + sorted((ROOT / "api").glob("*.py"))
             + sorted((ROOT / "api" / "routers").glob("*.py")))
    assert paths, "scan found no files"
    owner = ROOT / "pricing" / "cost_basis.py"
    bad = []
    for path in paths:
        if path == owner:
            continue
        for snippet in margin_violations(_code_without_comments(path),
                                         "crm_proxy", whole_word=True):
            bad.append((path.relative_to(ROOT).as_posix(), snippet))
    assert bad == [], bad
