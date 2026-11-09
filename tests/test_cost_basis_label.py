"""Cost-basis label evals (PK-29, ADR-006).

Part 1: the response builder in pricing/cost_basis.py (table tests).
Part 2: the eval against existing narration: with the book's cost_basis at its
default (crm_proxy), the word "margin" may appear in generated text only inside
the negated phrases "not bookable margin", "not cost-based margin" and
"not cost-based/bookable margin". Every occurrence is inventoried and
classified; an affirmative use is a finding, not an edit (this task does not
own the narration modules).

No live provider call: the provider is patched at anthropic.Anthropic and the
patch is asserted to have been hit; socket connects are blocked.
"""
from __future__ import annotations

import re
import socket
from pathlib import Path

import pandas as pd
import pytest

from pricing import assist, copilot, cost_basis, diagnostic, governance
from pricing.cost_basis import (
    MarginLabelError, MarginRefusedError, assert_no_margin_for_proxy,
    label_for, refuse_margin_for_proxy,
)
from pricing.schema import CostBasis
from tests.test_numeric_fidelity import _install_provider, opp_texts

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
    assert "margin" in PROXY and PROXY.count("margin") == 1  # only "not margin"
    for basis in ("declared_cost", "erp_verified"):
        assert "margin" in label_for(basis).label


def test_guard_passes_the_proxy_label_and_fails_an_affirmative_margin():
    assert_no_margin_for_proxy(PROXY, "crm_proxy")
    assert_no_margin_for_proxy("Realization is never labeled margin.", "crm_proxy")
    assert_no_margin_for_proxy("no figure here", "crm_proxy")
    for bad in ("gross margin 40 percent", "Margin", "MARGIN is 12%",
                "not bookable margin", "net margin", "contribution margin"):
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


def test_refuse_helper_raises_for_proxy_and_not_for_others():
    for basis in ("crm_proxy", None, "unknown", CostBasis.CRM_PROXY):
        with pytest.raises(MarginRefusedError):
            refuse_margin_for_proxy(basis)
    assert refuse_margin_for_proxy("declared_cost") is None
    assert refuse_margin_for_proxy(CostBasis.ERP_VERIFIED) is None


# --- Part 2: the eval against existing narration -----------------------------

# Negated phrasings the existing caveats use. The lead's brief allows these;
# ADR-006's strict wording ("no output may contain the word margin") does not,
# see test_strict_adr_006_reading below.
_ALLOWED_NEGATED = re.compile(
    r"\bnot (?:cost-based/bookable|bookable|cost-based) margin\b", re.I)


def margin_occurrences(text: str) -> list[tuple[str, bool]]:
    """(context snippet, allowed) for every 'margin' substring in text."""
    out = []
    for m in re.finditer("margin", text, flags=re.I):
        lo = max(0, m.start() - 30)
        window = text[lo:m.end() + 5]
        allowed = any(a.start() + lo <= m.start() < a.end() + lo
                      for a in _ALLOWED_NEGATED.finditer(window))
        out.append((text[lo:m.end() + 5].replace("\n", " "), allowed))
    return out


@pytest.fixture(scope="module")
def analysis():
    return diagnostic.run(BOOK)


def test_book_cost_basis_defaults_to_crm_proxy(analysis):
    assert set(analysis["data"]["cost_basis"].unique()) == {"crm_proxy"}


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

    # Recorded provider narrations, shaped the way the system prompts ask.
    narrations = {
        "copilot.answer_canonical[recorded]": (
            "Where are the opportunities? The engine found several. Impacts "
            "are correlational estimates at an assumed recoverable share, "
            "not bookable margin, and are not additive [A]."),
        "assist.executive_summary[recorded]": (
            "Upside to pursue deal by deal. The figure is correlational and "
            "based on price realization, not cost-based margin [A]."),
    }
    for name, recorded in narrations.items():
        calls = _install_provider(monkeypatch, recorded)
        if "copilot" in name:
            text = copilot.answer_canonical("opportunities_over", analysis).text
        else:
            text = assist.executive_summary(analysis)
        assert len(calls) == 1, f"provider patch not hit for {name}"
        out[name] = text
    return out


def test_margin_appears_only_in_negated_phrases_for_proxy_data(
        monkeypatch, analysis):
    outputs = _collect_outputs(monkeypatch, analysis)
    findings, allowed = [], []
    for source, text in outputs.items():
        for snippet, ok in margin_occurrences(text):
            (allowed if ok else findings).append((source, snippet))
    # The inventory is asserted, so a new occurrence is a visible change.
    assert findings == [], f"affirmative 'margin' for crm_proxy data: {findings}"
    sources = {s for s, _ in allowed}
    assert "prompt:copilot._COPILOT_SYSTEM" in sources
    assert "prompt:assist._SUMMARY_SYSTEM" in sources
    assert "copilot._NON_ADDITIVE_CAVEAT" not in sources
    assert any(s.startswith("opportunity[") for s in sources)


@pytest.mark.xfail(
    strict=True,
    reason="STRICT ADR-006 READING: pricing/copilot.py:153 (_RECOVERABLE_CAVEAT, "
           "'not bookable margin'), pricing/copilot.py:638-639 (_COPILOT_SYSTEM, "
           "same phrase), pricing/assist.py:247 (_SUMMARY_SYSTEM, 'not "
           "cost-based margin') carry the word margin on crm_proxy output. "
           "They are negated, so the brief allows them, but ADR-006 says no "
           "output may contain the word. Decision needed: reword to 'not "
           "bookable revenue' or amend the ADR to allow negation.")
def test_strict_adr_006_reading_no_margin_word_at_all(monkeypatch, analysis):
    for source, text in _collect_outputs(monkeypatch, analysis).items():
        if source.startswith("prompt:"):
            continue  # prompts instruct the model; the strict read is outputs
        assert_no_margin_for_proxy(text, "crm_proxy")


def test_source_scan_every_margin_in_pricing_is_negated_or_reviewed():
    """Static scan so a new affirmative use in any module trips CI, including
    surfaces that cannot run offline."""
    skip = {"cost_basis.py", "schema.py", "model.py"}  # builder, enum docs,
    # and 'marginal win gain' in model.py (not the word margin as a label).
    bad = []
    for path in sorted((ROOT / "pricing").glob("*.py")):
        if path.name in skip:
            continue
        # Join adjacent string-literal fragments so a phrase split across
        # lines ("not " / "bookable margin") is read whole.
        src = re.sub(r'"\s*\n\s*"', "", path.read_text(encoding="utf-8"))
        for snippet, ok in margin_occurrences(src):
            if not ok and "not cost-based/bookable margin" not in snippet:
                bad.append((path.name, snippet))
    assert bad == [], bad
