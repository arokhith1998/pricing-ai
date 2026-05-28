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

import re
from typing import Optional

import rapidfuzz

from pricing.schema import FIELDS

# Curated synonyms per canonical field. Lowercase, deterministic, easy to grow.
SYNONYMS: dict[str, list[str]] = {
    "opportunity_id": [
        "opportunity id", "opp id", "deal id", "opportunity",
        "opp", "oppid", "opp_id", "deal", "deal number", "deal #",
    ],
    "account_id": [
        "account id", "customer id", "acct id", "client id", "company id",
    ],
    "account_name": [
        "account", "account name", "customer", "customer name",
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
        "segment", "customer segment", "tier", "size", "company size",
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
        "line", "product line", "line of business", "lob", "product family",
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
    ],
    "platform_fee_acv": [
        "platform fee", "platform", "base fee", "subscription fee",
        "fixed fee", "commit",
    ],
    "usage_acv": [
        "usage", "usage value", "consumption", "metered", "variable",
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
        "owner id", "rep name",
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

def fuzzy_match(header: str, threshold: int = 88) -> Optional[tuple[str, int]]:
    n = normalize(header)
    best_field, best_score = None, 0
    for field, alts in _NORM_SYN.items():
        for alt in alts:
            score = rapidfuzz.fuzz.token_set_ratio(n, alt)
            if score > best_score:
                best_score, best_field = score, field
    if best_score >= threshold:
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


def embedding_match(header: str, threshold: float = 0.55) -> Optional[tuple[str, float]]:
    """Cosine match of the header against every field's description+synonyms."""
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
    except Exception:
        # If fastembed isn't available at runtime, this layer just no-ops.
        return None
    return None


# --- Orchestrator -----------------------------------------------------------

Confidence = str  # "high" | "medium" | "low" | "none"


def map_headers(headers: list[str], llm_fallback: bool = True) -> dict:
    """Return {mapping, confidence, used} for our schema fields.

    `mapping[field]` is the matched prospect header (or None).
    `confidence[field]` is one of high/medium/low/none.
    `used[header]` records which layer matched it (audit trail).
    """
    field_to_header: dict[str, str] = {}
    confidence: dict[str, Confidence] = {}
    used: dict[str, str] = {}
    claimed: set[str] = set()

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
    for h in headers:
        if h in claimed:
            continue
        r = embedding_match(h)
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
                        if h and h not in claimed and f in unmatched_fields:
                            _claim(f, h, "llm", "low")
            except Exception:
                pass

    # Always include every field key.
    out_mapping: dict[str, Optional[str]] = {
        f: field_to_header.get(f) for f in _FIELDS_BY_NAME
    }
    for f in _FIELDS_BY_NAME:
        confidence.setdefault(f, "none")

    return {"mapping": out_mapping, "confidence": confidence, "used": used}
