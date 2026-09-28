"""LLM assist layer — narrative + CSV column mapping.

Thin, guard-railed layer on top of the deterministic analytics. The LLM NEVER
computes a number: it narrates figures we already verified, and it maps column
*names* (not data). Only aggregates and header names are sent to the provider,
never row-level customer data: this module never forwards a row, and the
callers that build a fuller prompt (pricing.rag.ask) strip every named-deal
array out of the analysis dict before it reaches `_complete` (see
pricing/rag.py's module docstring). Real-customer use needs the provider's
zero-retention / DPA terms (aligns with the NDA's no-training clause).

Anthropic only. The product runtime no longer talks to OpenAI (PK-5); the old
LLM_PROVIDER switch is gone. tools/oai_review.py is a separate, deliberately
OpenAI adversarial-review script that does not import this module — its
purpose is a second opinion from a *different* vendor, so it stays put.
Configure ANTHROPIC_API_KEY (+ optionally ANTHROPIC_SUMMARY_MODEL /
ANTHROPIC_MAP_MODEL) in .env.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pricing.schema import FIELDS

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Hard ceiling on any single LLM call. Without it a stalled provider call can
# hang a Render worker indefinitely (the CTO-review finding). Overridable for
# ops, never unbounded.
LLM_TIMEOUT_SECONDS = float(os.environ.get("PRICEKEEL_LLM_TIMEOUT", "60"))

# Two-tier model selection, preserving the old gpt-4o / gpt-4o-mini cost split
# (pricing/matching.py:390, tests/test_matching.py:366). Neither tier does the
# job of the "large" reasoning model on purpose: this module only narrates
# figures the deterministic layer already computed and maps column *names* —
# not the kind of task that needs the top tier (claude-opus-5). Sonnet 5 is
# the default for board-facing narrative prose quality; Haiku 4.5 is the
# small tier for cheap, structured tasks (CSV column mapping, and the
# JSON-extraction calls in matching.py that share this provider boundary).
_DEFAULT_SUMMARY_MODEL = "claude-sonnet-5"
_DEFAULT_MAP_MODEL = "claude-haiku-4-5"


class LLMError(RuntimeError):
    """Base class for assist-layer LLM failures."""


class LLMUnavailableError(LLMError):
    """The provider timed out or could not be reached. The API layer maps
    this to a 503 instead of letting a worker hang or 500."""


class LLMConfigError(LLMError):
    """A caller of this module got the call contract wrong (e.g. json_mode
    without a json_schema) — a code bug here, not a provider failure and
    not a client's fault. Deliberately NOT a ValueError: api/main.py catches
    (ValueError, requests.RequestException) and turns it into a 422 with
    str(exc) as the client-visible detail, which would misattribute an
    internal programming error to the caller's input."""


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


def has_llm() -> bool:
    """True if a usable Anthropic key is configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _strip_code_fence(text: str) -> str:
    """Best-effort removal of a ```json ... ``` wrapper. Structured outputs
    (below) should make this unnecessary, but it's a cheap, harmless second
    layer against a model that still wraps its JSON in prose fencing."""
    text = text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```").strip()
    return text


def _json_output_config(json_schema: dict | None) -> dict:
    """Anthropic structured-outputs config for messages.create(). The older
    top-level `output_format` parameter is deprecated; this uses the current
    `output_config={"format": {...}}` shape.

    Callers MUST pass an explicit, real JSON Schema. There is no permissive
    "any JSON object" fallback: the API's structured-outputs subset uses
    constrained decoding against the schema you send, and an object schema
    with no declared properties constrains the model to producing nothing —
    it does not mean "any object", it is useless for getting real data back.
    A schema-less fallback would therefore not degrade loudly, it would
    quietly make the provider return {} (or equivalent) while `_complete`
    reports success — worse than a crash (PK-5 review round 2). Callers that
    don't have a real schema yet must not be handed one guessed by this
    module; give them a schema or don't use json_mode. (This module does not
    call anthropic.lib._parse._transform.transform_schema itself, and
    `output_config` is sent to the API as the raw dict you build — see the
    tests for how that function is used offline instead, as a pre-flight
    check against the SDK's own encoding of the documented schema subset.)
    """
    if json_schema is None:
        raise LLMConfigError(
            "json_mode=True requires an explicit json_schema keyword "
            "argument; there is no safe generic fallback under the API's "
            "structured-outputs subset (see _json_output_config's docstring)"
        )
    return {"format": {"type": "json_schema", "schema": json_schema}}


def _complete(system: str, user: str, *, json_mode: bool = False,
              max_tokens: int = 800, small: bool = False,
              json_schema: dict | None = None) -> str:
    """One completion against Anthropic. `small` picks the cheaper model.

    Every call carries an explicit timeout (LLM_TIMEOUT_SECONDS). Timeouts and
    connection failures raise LLMUnavailableError so callers can degrade
    cleanly (the API turns it into a 503) instead of hanging a worker.

    No sampling parameters (temperature / top_p / top_k) are sent: current
    Claude models reject them. `thinking` is deliberately not enabled either —
    this module only narrates numbers the deterministic layer already
    computed and maps column *names*, neither of which is a reasoning task,
    and adaptive thinking would add latency and cost against the same
    LLM_TIMEOUT_SECONDS ceiling for no narration-quality gain.
    """
    import anthropic
    from anthropic import Anthropic

    model = os.environ.get(
        "ANTHROPIC_MAP_MODEL" if small else "ANTHROPIC_SUMMARY_MODEL",
        _DEFAULT_MAP_MODEL if small else _DEFAULT_SUMMARY_MODEL,
    )
    kwargs: dict = {
        "model": model, "max_tokens": max_tokens, "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if json_mode:
        kwargs["output_config"] = _json_output_config(json_schema)
    try:
        msg = Anthropic(timeout=LLM_TIMEOUT_SECONDS).messages.create(**kwargs)
    # APITimeoutError subclasses APIConnectionError in the anthropic SDK.
    except anthropic.APIConnectionError as exc:
        raise LLMUnavailableError(
            f"LLM provider (anthropic) unreachable or timed out: {exc}"
        ) from exc
    # 429 (rate limit) and 5xx (server-side) are also "provider unavailable"
    # from a caller's point of view, not a request bug — degrade the same
    # way a connection failure does instead of leaking as a raw 500. Other
    # status errors (4xx request bugs, e.g. a malformed schema) are a real
    # bug in this module and must not be swallowed as a false "unavailable".
    except anthropic.APIStatusError as exc:
        if exc.status_code in (429, 500, 502, 503, 529):
            raise LLMUnavailableError(
                f"LLM provider (anthropic) returned {exc.status_code}: {exc}"
            ) from exc
        raise

    # Don't assume content[0] is text — filter for the text block instead.
    text_block = next(
        (b for b in msg.content if getattr(b, "type", None) == "text"), None)
    if text_block is None:
        raise LLMError("Anthropic response contained no text content block")
    text = text_block.text

    if json_mode:
        text = _strip_code_fence(text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            # Loud, not silent: a caller expecting JSON must never receive
            # unparseable prose back from this layer.
            raise LLMError(
                f"LLM returned non-JSON output despite json_mode=True: {exc}"
            ) from exc
        # json.loads also accepts a bare list/string/number/null, and every
        # json_mode caller here does `.get(...)` on the result — a valid but
        # non-object parse must fail loudly here, not with an AttributeError
        # three frames away in the caller.
        if not isinstance(parsed, dict):
            raise LLMError(
                "LLM returned valid JSON but not a JSON object under "
                f"json_mode=True (got {type(parsed).__name__})"
            )
    return text


# --- executive summary -------------------------------------------------------

def summary_facts(res: dict) -> str:
    """Deterministic facts block from a diagnostic result (the only inputs the
    model may use). Pure function — safe to cache/test offline."""
    ov, lk = res["overview"], res["leakage"]
    qe, gv = res.get("quarter_end") or {}, res["governance"]
    ref = res.get("reference_discount") or {}
    if ref.get("sufficient", True):
        reference_line = f"reference_discount={lk['reference_threshold']:.3f}"
    else:
        # A 0.0 threshold here would read as "the reference discount is
        # zero", not as "there is no reference": the book had too few real
        # discount bands with enough closed deals to estimate one
        # (metrics.reference_discount's own insufficient-data state, silent-
        # failure-hunter 2026-09-27). Narrate the reason, never the zero.
        band_counts = ref.get("band_counts", {})
        counts = ", ".join(f"{k}={v}" for k, v in sorted(band_counts.items()))
        reference_line = f"reference: insufficient data (band counts: {counts})"
    lines = [
        f"booked_acv_won={ov['booked_acv_won']:.0f}",
        f"price_realization_won={ov['price_realization_won']:.3f}",
        f"avg_discount_won={ov['avg_discount_won']:.3f}",
        f"win_rate={ov['win_rate']:.3f} (won={ov['won']}, lost={ov['lost']})",
        reference_line,
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
    "Head of Pricing and CFO. Use ONLY the figures provided, never invent or "
    "recompute numbers. 120-170 words, direct, no hype, no emoji. Frame this as "
    "pricing UPSIDE to pursue, not a loss to lament. Lead with the headline "
    "opportunity in dollars and % of ACV (revenue discounted past the win "
    "point), then the 2-3 biggest drivers (reference discount, quarter-end, "
    "unapproved off-policy deals). State once that this figure is correlational "
    "and based on price realization (booked vs list), not cost-based margin: it "
    "is upside to pursue deal by deal, not a refund you can book. End with one "
    "concrete recommended next step. Do not use em dashes; use commas, colons, "
    "or periods instead."
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
    # The API's structured-outputs subset does not accept a JSON Schema type
    # array (e.g. {"type": ["string", "null"]}) for constrained decoding.
    # anthropic.lib._parse._transform.transform_schema is not on this
    # runtime path (output_config is sent to the API as the raw dict below,
    # unmodified by the SDK) — but it's a static encoding of that documented
    # subset, and it raises on a type array, which is why the tests use it
    # offline as a pre-flight check on this exact schema. The portable
    # nullable form is anyOf over the two single types (PK-5 review round 2).
    def _nullable_string() -> dict:
        return {"anyOf": [{"type": "string"}, {"type": "null"}]}

    schema = {
        "type": "object",
        "properties": {t["field"]: _nullable_string() for t in targets},
        "required": [t["field"] for t in targets],
        "additionalProperties": False,
    }
    raw = _complete(system, user, json_mode=True, small=True, max_tokens=600,
                     json_schema=schema)
    out = json.loads(raw)  # _complete already guarantees this parses, or raises
    valid = {h for h in headers}
    return {f["field"]: (out.get(f["field"]) if out.get(f["field"]) in valid else None)
            for f in targets}
