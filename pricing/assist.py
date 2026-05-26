"""LLM assist layer — narrative + CSV column mapping.

Thin, guard-railed layer on top of the deterministic analytics. The LLM NEVER
computes a number: it narrates figures we already verified, and it maps column
*names* (not data). Only aggregates and header names are sent to the provider —
never row-level customer data. Real-customer use needs the provider's
zero-retention / DPA terms (aligns with the NDA's no-training clause).

Provider-swappable: defaults to OpenAI (set in .env). Set LLM_PROVIDER=anthropic
(+ ANTHROPIC_API_KEY) to switch to Claude — no other code change.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pricing.schema import FIELDS

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _provider() -> str:
    p = os.environ.get("LLM_PROVIDER", "openai").lower()
    if p == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "openai"


def has_llm() -> bool:
    """True if a usable provider key is configured."""
    if _provider() == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    return bool(os.environ.get("OPENAI_API_KEY"))


def _complete(system: str, user: str, *, json_mode: bool = False,
              max_tokens: int = 800, small: bool = False) -> str:
    """One completion, provider-agnostic. `small` picks the cheaper model."""
    if _provider() == "anthropic":
        from anthropic import Anthropic
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        msg = Anthropic().messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}])
        return msg.content[0].text

    from openai import OpenAI
    model = (os.environ.get("OPENAI_MAP_MODEL", "gpt-4o-mini") if small
             else os.environ.get("OPENAI_SUMMARY_MODEL", "gpt-4o"))
    kwargs: dict = {"model": model, "temperature": 0.3,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}]}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return OpenAI().chat.completions.create(**kwargs).choices[0].message.content


# --- executive summary -------------------------------------------------------

def summary_facts(res: dict) -> str:
    """Deterministic facts block from a diagnostic result (the only inputs the
    model may use). Pure function — safe to cache/test offline."""
    ov, lk = res["overview"], res["leakage"]
    qe, gv = res.get("quarter_end") or {}, res["governance"]
    lines = [
        f"booked_acv_won={ov['booked_acv_won']:.0f}",
        f"price_realization_won={ov['price_realization_won']:.3f}",
        f"avg_discount_won={ov['avg_discount_won']:.3f}",
        f"win_rate={ov['win_rate']:.3f} (won={ov['won']}, lost={ov['lost']})",
        f"reference_discount={lk['reference_threshold']:.3f}",
        f"excess_vs_reference_won={lk['excess_vs_reference_won']:.0f} "
        f"({lk['excess_pct_of_booked']:.3f} of booked ACV, correlational)",
        f"off_policy_leakage_won={lk['off_policy_leakage_won']:.0f}",
        f"gross_discount_won={lk['gross_discount_won']:.0f}",
    ]
    if qe:
        lines.append(f"quarter_end_discount_lift={qe['lift']:.3f} "
                     f"(attributable={qe['attributable_discount_won']:.0f})")
    lines.append(f"off_policy_unapproved_deals={gv['off_policy_unapproved_won']} "
                 f"(${gv['unapproved_discount_dollars']:.0f} unapproved)")
    return "\n".join(lines)


_SUMMARY_SYSTEM = (
    "You are a B2B SaaS pricing analyst writing a board-ready briefing for a "
    "Head of Pricing and CFO. Use ONLY the figures provided — never invent or "
    "recompute numbers. 120–170 words, direct, no hype, no emoji. Lead with the "
    "headline leak in dollars and % of ACV, then the 2–3 biggest drivers "
    "(reference discount, quarter-end, unapproved off-policy deals). State once "
    "that the excess figure is correlational (a list to investigate, not a "
    "refund). End with one concrete recommended next step."
)


def executive_summary(res: dict) -> str:
    """Board-ready narrative of a diagnostic result (sends only aggregates)."""
    return _complete(_SUMMARY_SYSTEM, summary_facts(res), max_tokens=500).strip()


# --- CSV column mapping ------------------------------------------------------

def mapping_targets() -> list[dict]:
    """Our schema fields the mapper tries to fill (pure)."""
    return [{"field": f.name, "required": f.required, "description": f.description}
            for f in FIELDS]


def map_columns(headers: list[str]) -> dict:
    """Map a prospect's CSV headers to our schema. Returns {our_field: header|None}.

    Sends only the header strings — no data rows.
    """
    targets = mapping_targets()
    system = (
        "Map a customer's CSV column headers to our canonical schema. Return a "
        "JSON object whose keys are our field names and whose values are the "
        "single best-matching customer header (verbatim) or null if there is no "
        "confident match. Map only confident matches; prefer null over guessing."
    )
    user = json.dumps({"our_fields": targets, "their_headers": headers})
    raw = _complete(system, user, json_mode=True, small=True, max_tokens=600)
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        out = json.loads(raw)
    valid = {h for h in headers}
    return {f["field"]: (out.get(f["field"]) if out.get(f["field"]) in valid else None)
            for f in targets}
