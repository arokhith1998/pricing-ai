"""Cost-basis label builder (ADR-006): the one place label text is written.

ADR-006 (docs/agents/DECISIONS.md, accepted 2026-11-07) fixes three cost-basis
values and says the label a reader sees is produced by one response builder in
code, never written freehand in copy or prompts:

    crm_proxy      -> "cost proxy, not margin"
    declared_cost  -> "contribution margin, customer-supplied cost basis"
    erp_verified   -> "gross margin, ERP-verified cost"

Rules enforced here:
  * The word "margin" is never used affirmatively for a crm_proxy basis, and
    any unknown, missing or malformed basis is treated as crm_proxy (fail
    toward honesty). Per the ADR-006 amendment of 2026-11-09 the ban is on
    affirmative use: the four negations in `allowed_phrases()` are the only
    permitted occurrences, and that tuple is the only allowlist in the repo.
  * Net margin is not a label for any basis; none exists below.
  * A function that computes a margin figure must refuse crm_proxy input
    rather than compute and caveat: call `refuse_margin_for_proxy` first.

Pure functions. No I/O, no LLM, no imports from the rest of the package (the
string values mirror pricing.schema.CostBasis; a test pins the parity).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

CRM_PROXY = "crm_proxy"
DECLARED_COST = "declared_cost"
ERP_VERIFIED = "erp_verified"

# ADR-006 label text. Edit here and nowhere else.
LABELS: dict[str, str] = {
    CRM_PROXY: "cost proxy, not margin",
    DECLARED_COST: "contribution margin, customer-supplied cost basis",
    ERP_VERIFIED: "gross margin, ERP-verified cost",
}

# ADR-006 amendment (lead decision 2026-11-09): the only phrases that may carry
# the word "margin" next to a crm_proxy basis. Exactly four; adding a fifth
# needs a superseding decision.
_ALLOWED_PROXY_PHRASES: tuple[str, ...] = (
    "not margin",
    "never labeled margin",
    "not bookable margin",
    "not cost-based margin",
)

# An allowed phrase counts only as a whole phrase: not glued to a preceding
# word character or hyphen ("cannot margin"), and followed by end of string or
# one punctuation mark, optionally after whitespace. "not margin compression",
# "not margin-dilutive", "not margins of 40%" and "not marginal" all fail. The
# punctuation must not be "?" (a question is not a negation) and must not lead
# into a figure ("not margin: 40%", "not margin (40%)" fail).
_ALLOWED_RE = re.compile(
    r"(?<![\w-])(?:%s)(?=\s*$|\s*[^\w\s\-?](?!\s*[\d$%%]))" % "|".join(
        re.escape(p) for p in _ALLOWED_PROXY_PHRASES),
    flags=re.IGNORECASE)

# Source-scan boundary: catches "margin", "margins" and snake_case such as
# gross_margin_pct (underscore is not a letter) but not "marginal".
_WHOLE_WORD_RE = r"(?<![A-Za-z])margins?(?![A-Za-z])"


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


def allowed_phrases() -> tuple[str, ...]:
    """The four negated phrases allowed next to a crm_proxy basis (ADR-006
    amendment). The single source of truth: callers and tests read it here."""
    return _ALLOWED_PROXY_PHRASES


def normalize_basis(cost_basis: Any) -> str:
    """Map an enum member, string, None or garbage to one of the three values.

    Anything that is not exactly declared_cost or erp_verified (after trim and
    lowercase) is crm_proxy, so a missing or corrupt value can never earn a
    stronger label.

    Trust boundary: this function trusts callers to pass values that were
    already validated upstream. It cannot tell a connector-set erp_verified from
    a typed one. Ingest reserves erp_verified for connector paths Pricekeel
    operates and rejects it from CSV and frame uploads (ADR-006, SchemaError).
    """
    raw = getattr(cost_basis, "value", cost_basis)
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in (DECLARED_COST, ERP_VERIFIED):
            return v
    return CRM_PROXY


def weakest_basis(bases: Iterable[Any]) -> str:
    """The basis a mixed set of rows may be labeled with: the weakest one.

    crm_proxy wins if any row is a proxy (or the set is empty, or a value is
    unknown), then declared_cost, and erp_verified only when every row is
    erp_verified. A book is never labeled stronger than its weakest row.
    """
    if isinstance(bases, (str, bytes)):
        raise TypeError("weakest_basis takes an iterable of bases, not a "
                        "single string (it would iterate characters)")
    normalized = {normalize_basis(b) for b in bases}
    if not normalized or CRM_PROXY in normalized:
        return CRM_PROXY
    if DECLARED_COST in normalized:
        return DECLARED_COST
    return ERP_VERIFIED


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


def _normalize_text(text: str) -> str:
    """NFKC-fold, drop invisible format characters, collapse whitespace.

    Limit: NFKC folds compatibility forms (fullwidth letters, ligatures) and
    format characters (zero width space, soft hyphen) are removed, but it does
    NOT map cross-script homoglyphs, so Cyrillic "mаrgin" (U+0430) is not seen
    as margin. The guard checks text our own code and prompts produce; it is not
    an adversarial-input filter.
    """
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return re.sub(r"\s+", " ", text)


def margin_violations(text: str, basis: Any, *,
                      whole_word: bool = False) -> list[str]:
    """Non-raising check: context snippets of every affirmative "margin".

    Returns [] for declared_cost and erp_verified. For crm_proxy (and unknown or
    missing bases) each case-insensitive "margin" substring not covered by a
    whole-phrase match of `allowed_phrases()` is returned with a little
    surrounding context. `whole_word=True` counts "margin" and "margins" as a
    word or inside snake_case (gross_margin_pct) but not "marginal" (used by
    the source scan); the guard itself leaves it False so "not marginal" fails.
    """
    if normalize_basis(basis) != CRM_PROXY:
        return []
    norm = _normalize_text(text)
    covered = [m.span() for m in _ALLOWED_RE.finditer(norm)]
    pattern = _WHOLE_WORD_RE if whole_word else "margin"
    out = []
    for m in re.finditer(pattern, norm, flags=re.IGNORECASE):
        if any(a <= m.start() < b for a, b in covered):
            continue
        out.append(norm[max(0, m.start() - 30):m.end() + 15])
    return out


def assert_no_margin_for_proxy(text: str, basis: Any) -> None:
    """Raise MarginLabelError if `text` uses "margin" affirmatively for crm_proxy.

    ADR-006 as amended 2026-11-09: only the whole-phrase negations in
    `allowed_phrases()` may carry the word. Other bases pass untouched. Unknown
    or missing bases count as crm_proxy. See `_normalize_text` for the
    homoglyph limit.
    """
    bad = margin_violations(text, basis)
    if bad:
        raise MarginLabelError(
            "the word 'margin' may not be used affirmatively for a crm_proxy "
            f"cost basis (ADR-006): {bad[0]!r}")


def refuse_margin_for_proxy(basis: Any) -> None:
    """Call at the top of any margin computation; raises for crm_proxy input.

    ADR-006: a margin computation refuses crm_proxy input rather than computing
    and caveating. Returns None for declared_cost and erp_verified.
    """
    if not label_for(basis).may_say_margin:
        raise MarginRefusedError(
            "margin cannot be computed from a crm_proxy cost basis (ADR-006); "
            "declared_cost or erp_verified input is required")
