"""Robust column mapper — prospect headers in any form to our canonical schema.

Four-layer cascade, cheapest and most certain first:

  1. Synonyms dictionary  (deterministic, hand-curated per field)
  2. Fuzzy match          (rapidfuzz token-set ratio on normalized headers)
  3. Local embeddings     (fastembed / BAAI bge-small, ONNX, CPU)
  4. Cloud LLM fallback   (header strings only — never row data; opt-in)

Layers 1-3 are fully local. Layer 4 is only invoked for headers that nothing
else resolved with confidence, and even then it sends only the unmatched
header strings, never any row data. See docs/design/richer-ingest.md.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import rapidfuzz

from pricing.schema import FIELDS

logger = logging.getLogger("pricekeel.mapping")
# The embedding layer fails the same way for every header, so warn once.
_EMBED_FAILURE_LOGGED = False

# Curated synonyms per canonical field. Lowercase, deterministic, easy to grow.
SYNONYMS: dict[str, list[str]] = {
    "opportunity_id": [
        "opportunity id", "opp id", "deal id", "opportunity",
        "opp", "oppid", "opp_id", "deal", "deal number", "deal #",
        "record id",  # HubSpot's per-deal key
    ],
    "account_id": [
        "account id", "customer id", "acct id", "client id", "company id",
    ],
    "account_name": [
        "account", "account name", "acct name", "customer", "customer name",
        "company", "company name", "client", "client name", "buyer",
    ],
    "outcome": [
        "outcome", "status", "stage", "deal status", "deal stage",
        "won/lost", "result", "disposition", "stage name",
    ],
    "created_date": [
        "created", "created date", "create date", "open date",
        "opp created", "opportunity created", "created at",
    ],
    "close_date": [
        "close date", "closed date", "closed", "won date", "lost date",
        "deal closed", "close", "closed at", "closedate",
    ],
    "segment": [
        # NOTE: "tier" deliberately removed — it collides with product_tier
        # (segment values are SMB/MidMarket/Enterprise; a "tier" column means
        # the product plan). "seg" added for abbreviated finance exports.
        "segment", "customer segment", "seg", "size", "company size",
        "account segment",
    ],
    "region": [
        "region", "geo", "territory", "country", "area",
    ],
    "industry": [
        "industry", "vertical", "sector",
    ],
    "business_unit": [
        "bu", "business unit", "business group", "division", "org", "unit",
    ],
    "product_line": [
        # "product family" removed — it collides with product_family and would
        # leave a real product_family column unmapped when both are present.
        "line", "product line", "line of business", "lob",
    ],
    "product_family": [
        "family", "product family", "category", "product category",
    ],
    "product_tier": [
        "tier", "plan", "package", "edition", "product tier", "subscription tier",
    ],
    "sku": [
        "sku", "part number", "part no", "part#", "product id",
        "product code", "item", "item code", "material",
    ],
    "value_metric": [
        "value metric", "pricing model", "billing model", "pricing",
        "monetization", "charge model",
    ],
    "list_acv": [
        "list acv", "list", "list price", "list value", "list amount",
        "list_acv", "total list", "annual list",
    ],
    "booked_acv": [
        "acv", "booked", "booked value", "booked amount", "amount",
        "annual contract value", "annual value", "annualized",
        "won amount", "booked acv", "subscription value", "deal value",
        # Real exports name the post-discount figure many ways:
        "deal amount", "net price", "contract value", "net acv", "net amount",
    ],
    "platform_fee_acv": [
        "platform fee", "platform fee acv", "platform", "base fee",
        "subscription fee", "fixed fee",
    ],
    "usage_acv": [
        "usage", "usage acv", "usage value", "consumption", "metered", "variable",
    ],
    "term_months": [
        "term", "contract term", "duration", "term months",
        "term (months)", "contract length", "length",
    ],
    "quantity": [
        "qty", "quantity", "seats", "units", "volume", "user count",
    ],
    "rep_id": [
        "rep", "rep id", "owner", "salesperson", "ae", "account executive",
        "owner id", "rep name", "deal owner",
        # "deal owner" claimed here in layer 1 so it can't fuzzy-grab
        # opportunity_id (it contains the token "deal").
    ],
    "approved_by": [
        "approver", "approved by", "approval", "approved",
    ],
    "competitor_present": [
        "competitor", "competitor present", "competitive",
        "competition", "has competitor",
    ],
    "lost_reason": [
        "lost reason", "loss reason", "reason", "loss code",
    ],
    "committed_acv": [
        "committed acv", "commit", "commitment", "committed spend",
        "minimum commitment", "min commit", "committed amount", "floor",
        "annual commitment",
    ],
    "overage_rate": [
        "overage rate", "overage", "on demand rate", "on-demand rate",
        "overage price", "unit overage", "burst rate", "rate per unit",
    ],
    "list_unit_rate": [
        "list unit price", "rate card price", "unit list price", "list rate",
    ],
    "credits_tcv": [
        "credits", "service credits", "free months value", "credit value",
    ],
    "ramp_year_1_acv": [
        "ramp year 1", "year 1 acv", "y1 acv", "ramp y1", "year one acv",
        "ramp_year_1", "yr1 acv",
    ],
    "ramp_year_2_acv": [
        "ramp year 2", "year 2 acv", "y2 acv", "ramp y2", "year two acv",
        "ramp_year_2", "yr2 acv",
    ],
    "is_renewal": [
        "renewal", "is renewal", "renewal flag", "is_renewal", "renewed",
        "contract type",
    ],
    "renewal_uplift": [
        "renewal uplift", "uplift", "renewal increase", "price uplift",
        "renewal rate increase", "escalator", "annual uplift",
    ],
    "cogs_acv": [
        "cogs", "cogs acv", "cost of goods", "cost of goods sold",
        "delivery cost", "infra cost", "cost", "service cost",
    ],
    "currency": [
        "currency", "ccy", "curr", "currency code", "currency iso",
        "iso currency", "transaction currency",
        # Salesforce's own multi-currency-org export header is the literal
        # field name CurrencyIsoCode (no separators, so it normalizes to
        # "currencyisocode" with nothing for the space-collapse regex to
        # split on); "currency iso code" covers a spaced-out variant of the
        # same header (2026-09-27 fix, PK-16/salesforce-readiness follow-up).
        "currencyisocode", "currency iso code",
    ],
}

_FIELDS_BY_NAME = {f.name: f for f in FIELDS}


def normalize(s: str) -> str:
    """Lowercase + collapse separators/whitespace; idempotent."""
    s = (s or "").lower().strip()
    s = re.sub(r"[\s_\-./()\[\]]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _normalized_synonyms() -> dict[str, list[str]]:
    return {f: [normalize(a) for a in alts] for f, alts in SYNONYMS.items()}


_NORM_SYN = _normalized_synonyms()


# --- Layer 1: deterministic synonyms ----------------------------------------

def synonyms_match(header: str) -> Optional[str]:
    n = normalize(header)
    for field, alts in _NORM_SYN.items():
        if n in alts:
            return field
    return None


# --- Layer 2: fuzzy ---------------------------------------------------------

def fuzzy_match(header: str, threshold: int = 88,
                sort_floor: int = 70) -> Optional[tuple[str, int]]:
    """Best field for a header by token-set ratio, guarded against subset
    coincidences.

    token_set_ratio gives a generic one-word synonym ("category") a perfect 100
    against an unrelated header that merely contains it ("forecast category"),
    which silently mis-maps an extra column. We additionally require a symmetric
    token_sort_ratio floor, which separates the real cases ("net acv usd" vs
    "net acv" sorts at ~78) from the coincidences ("forecast category" vs
    "category" sorts at ~64).
    """
    n = normalize(header)
    best_field, best_score = None, 0
    for field, alts in _NORM_SYN.items():
        for alt in alts:
            score = rapidfuzz.fuzz.token_set_ratio(n, alt)
            if score < threshold or score <= best_score:
                continue
            if rapidfuzz.fuzz.token_sort_ratio(n, alt) < sort_floor:
                continue
            best_score, best_field = score, field
    if best_field is not None:
        return (best_field, best_score)  # type: ignore[return-value]
    return None


# --- Layer 3: local embeddings (fastembed) ----------------------------------

_EMBED_MODEL = None
_FIELD_EMBEDS: Optional[tuple[list[str], "any"]] = None  # type: ignore[type-arg]


def _model():
    """Lazy-load the embedding model on first use (downloads ~80MB once)."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from fastembed import TextEmbedding
        _EMBED_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _EMBED_MODEL


def _field_embeds():
    """One embedding per canonical field, built from its description + synonyms."""
    global _FIELD_EMBEDS
    if _FIELD_EMBEDS is None:
        import numpy as np
        m = _model()
        names, texts = [], []
        for name, f in _FIELDS_BY_NAME.items():
            syn = ", ".join(SYNONYMS.get(name, []))
            texts.append(f"{name}: {f.description}. Aliases: {syn}")
            names.append(name)
        embs = np.array(list(m.embed(texts)))
        embs = embs / np.linalg.norm(embs, axis=1, keepdims=True)
        _FIELD_EMBEDS = (names, embs)
    return _FIELD_EMBEDS


def embedding_match(header: str, threshold: float = 0.55,
                    notes: Optional[list[str]] = None) -> Optional[tuple[str, float]]:
    """Cosine match of the header against every field's description+synonyms.

    `notes` collects a reason string when the layer is unavailable, so the
    caller can tell "no semantic match" from "the semantic layer never ran".
    """
    global _EMBED_FAILURE_LOGGED
    try:
        import numpy as np
        m = _model()
        names, field_embs = _field_embeds()
        h_emb = next(iter(m.embed([header])))
        h_emb = h_emb / np.linalg.norm(h_emb)
        sims = field_embs @ h_emb
        idx = int(np.argmax(sims))
        score = float(sims[idx])
        if score >= threshold:
            return (names[idx], score)
    except Exception as exc:
        # If fastembed isn't available at runtime, this layer just no-ops.
        # The mapper still works on the other layers, but an operator needs
        # to know the semantic layer is off.
        if not _EMBED_FAILURE_LOGGED:
            logger.warning("mapping: embedding layer unavailable, skipping: %s",
                           type(exc).__name__)
            _EMBED_FAILURE_LOGGED = True
        # The log fires once per process; this rides with every result, so the
        # tenth upload of the day discloses the degradation as loudly as the
        # first one did.
        if notes is not None:
            notes.append(f"embedding layer unavailable ({type(exc).__name__}), "
                         "semantic header matching was skipped")
        return None
    return None


# --- Orchestrator -----------------------------------------------------------

Confidence = str  # "high" | "medium" | "low" | "none"


def map_headers(headers: list[str], llm_fallback: bool = True,
                use_embeddings: bool = True) -> dict:
    """Return {mapping, confidence, used} for our schema fields.

    `mapping[field]` is the matched prospect header (or None).
    `confidence[field]` is one of high/medium/low/none.
    `used[header]` records which layer matched it (audit trail).

    `use_embeddings=False` restricts to the deterministic layers 1-2 (synonyms
    + fuzzy); the core ingest path uses this so it stays offline and
    reproducible (no 80MB model download, no network).
    """
    field_to_header: dict[str, str] = {}
    confidence: dict[str, Confidence] = {}
    used: dict[str, str] = {}
    claimed: set[str] = set()
    # Layers that did not run. Returned to the caller: an unmapped field looks
    # the same whether nothing matched or the layer that would have matched it
    # never ran, and only one of those is the customer's data being unusual.
    notes: list[str] = []
    # True only when Layer 4 was invoked and raised (silent-failure-hunter
    # F5): lets onboarding support tell "the LLM ran and found nothing" or
    # "it was never invoked" apart from "it was invoked and broke", which an
    # unmapped-column list alone cannot distinguish.
    llm_fallback_failed = False

    def _claim(field: str, header: str, layer: str, conf: Confidence) -> None:
        field_to_header[field] = header
        confidence[field] = conf
        used[header] = layer
        claimed.add(header)

    # Layer 1: synonyms (high)
    for h in headers:
        if h in claimed:
            continue
        f = synonyms_match(h)
        if f and f not in field_to_header:
            _claim(f, h, "synonyms", "high")

    # Layer 2: fuzzy
    for h in headers:
        if h in claimed:
            continue
        r = fuzzy_match(h)
        if r and r[0] not in field_to_header:
            conf: Confidence = "high" if r[1] >= 95 else "medium"
            _claim(r[0], h, "fuzzy", conf)

    # Layer 3: embeddings (semantic, the catch for unusual phrasing)
    for h in (headers if use_embeddings else []):
        if h in claimed:
            continue
        r = embedding_match(h, notes=notes)
        if r and r[0] not in field_to_header:
            conf = "medium" if r[1] >= 0.65 else "low"
            _claim(r[0], h, "embedding", conf)

    # Layer 4: cloud LLM (header strings only, opt-in)
    if llm_fallback:
        unmatched_headers = [h for h in headers if h not in claimed]
        unmatched_fields = [f for f in _FIELDS_BY_NAME if f not in field_to_header]
        if unmatched_headers and unmatched_fields:
            try:
                from pricing import assist
                if assist.has_llm():
                    llm_map = assist.map_columns(unmatched_headers)
                    for f, h in (llm_map or {}).items():
                        # `h in unmatched_headers` is a defense-in-depth check
                        # (assist.map_columns already enforces this): a header
                        # this layer did not actually receive must never be
                        # claimed, regardless of what the LLM returned.
                        if (h and h in unmatched_headers and h not in claimed
                                and f in unmatched_fields):
                            _claim(f, h, "llm", "low")
            except Exception as exc:
                # Unmatched fields already show confidence "none" to the user;
                # the operator still needs to know the LLM layer failed.
                llm_fallback_failed = True
                logger.warning("mapping: LLM fallback failed for %d headers: %s",
                               len(unmatched_headers), type(exc).__name__)
                notes.append(
                    f"LLM header fallback failed ({type(exc).__name__}); "
                    f"{len(unmatched_headers)} unrecognized column(s) were left "
                    "unmapped without it")

    # Always include every field key.
    out_mapping: dict[str, Optional[str]] = {
        f: field_to_header.get(f) for f in _FIELDS_BY_NAME
    }
    for f in _FIELDS_BY_NAME:
        confidence.setdefault(f, "none")

    return {"mapping": out_mapping, "confidence": confidence, "used": used,
            "notes": notes, "llm_fallback_failed": llm_fallback_failed}
