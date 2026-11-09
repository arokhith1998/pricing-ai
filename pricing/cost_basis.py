"""Cost-basis label builder (ADR-006): the one place label text is written.

ADR-006 (docs/agents/DECISIONS.md, accepted 2026-11-07) fixes three cost-basis
values and says the label a reader sees is produced by one response builder in
code, never written freehand in copy or prompts:

    crm_proxy      -> "cost proxy, not margin"
    declared_cost  -> "contribution margin, customer-supplied cost basis"
    erp_verified   -> "gross margin, ERP-verified cost"

Rules enforced here:
  * The word "margin" is never emitted for a crm_proxy basis, and any unknown,
    missing or malformed basis is treated as crm_proxy (fail toward honesty).
  * Net margin is not a label for any basis; none exists below.
  * A function that computes a margin figure must refuse crm_proxy input
    rather than compute and caveat: call `refuse_margin_for_proxy` first.

Pure functions. No I/O, no LLM, no imports from the rest of the package (the
string values mirror pricing.schema.CostBasis; a test pins the parity).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

CRM_PROXY = "crm_proxy"
DECLARED_COST = "declared_cost"
ERP_VERIFIED = "erp_verified"

# ADR-006 label text. Edit here and nowhere else.
LABELS: dict[str, str] = {
    CRM_PROXY: "cost proxy, not margin",
    DECLARED_COST: "contribution margin, customer-supplied cost basis",
    ERP_VERIFIED: "gross margin, ERP-verified cost",
}

# The only phrases that may carry the word "margin" next to a crm_proxy basis.
_ALLOWED_PROXY_PHRASES = ("not margin", "never labeled margin")


class MarginLabelError(ValueError):
    """Text for a crm_proxy basis contains the word margin (ADR-006)."""


class MarginRefusedError(ValueError):
    """A margin figure was requested from crm_proxy input (ADR-006)."""


@dataclass(frozen=True)
class CostBasisLabel:
    basis: str            # normalized: one of the three ADR-006 values
    label: str            # the ADR-006 label text
    may_say_margin: bool  # False only for crm_proxy
    labeled: str          # `figure` followed by the label, or the label alone


def normalize_basis(cost_basis: Any) -> str:
    """Map an enum member, string, None or garbage to one of the three values.

    Anything that is not exactly declared_cost or erp_verified (after trim and
    lowercase) is crm_proxy, so a missing or corrupt value can never earn a
    stronger label.
    """
    raw = getattr(cost_basis, "value", cost_basis)
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in (DECLARED_COST, ERP_VERIFIED):
            return v
    return CRM_PROXY


def label_for(cost_basis: Any, figure: Any = None) -> CostBasisLabel:
    """Build the ADR-006 label for `cost_basis`, optionally attached to a figure.

    `figure` is a caller-formatted string (or number) the label qualifies; it is
    rendered as "<figure>, <label>". This function never computes a number.
    """
    basis = normalize_basis(cost_basis)
    label = LABELS[basis]
    labeled = label if figure is None else f"{figure}, {label}"
    return CostBasisLabel(basis=basis, label=label,
                          may_say_margin=basis != CRM_PROXY, labeled=labeled)


def assert_no_margin_for_proxy(text: str, basis: Any) -> None:
    """Raise MarginLabelError if `text` says margin about a crm_proxy basis.

    Case-insensitive substring check for "margin". Only the exact phrases "not
    margin" and "never labeled margin" are removed before the check. Other
    bases pass untouched. Unknown or missing bases count as crm_proxy.
    """
    if normalize_basis(basis) != CRM_PROXY:
        return
    remainder = text
    for phrase in _ALLOWED_PROXY_PHRASES:
        remainder = re.sub(re.escape(phrase), " ", remainder, flags=re.IGNORECASE)
    if re.search("margin", remainder, flags=re.IGNORECASE):
        raise MarginLabelError(
            "the word 'margin' may not appear for a crm_proxy cost basis "
            f"(ADR-006): {text!r}")


def refuse_margin_for_proxy(basis: Any) -> None:
    """Call at the top of any margin computation; raises for crm_proxy input.

    ADR-006: a margin computation refuses crm_proxy input rather than computing
    and caveating. Returns None for declared_cost and erp_verified.
    """
    if not label_for(basis).may_say_margin:
        raise MarginRefusedError(
            "margin cannot be computed from a crm_proxy cost basis (ADR-006); "
            "declared_cost or erp_verified input is required")
