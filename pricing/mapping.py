"""Robust column mapper — prospect headers in any form to our canonical schema.

Layer 0 profiles the export from its header set alone (crm_opportunity,
cpq_line, unknown), normalises stage values into a closed outcome enum and
refuses, before any LLM call, an export that cannot supply outcome. Then a
four-layer cascade, cheapest and most certain first:

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

from pricing.schema import FIELDS, SourceSystem

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
        "opportunity stage",
    ],
    "created_date": [
        "created", "created date", "create date", "open date",
        "opp created", "opportunity created", "created at",
    ],
    "close_date": [
        "close date", "closed date", "closed", "won date", "lost date",
        "deal closed", "close", "closed at", "closedate",
        "opportunity close date",
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
        "opportunity amount",
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
        "list unit price", "unit list price", "rate card unit price",
        "list rate per unit",
    ],
    "credits_tcv": [
        "service credits value", "credits tcv", "free months value",
        "off-invoice credits",
    ],
    "source_system": ["source system"],
    "source_record_id": ["source record id"],
    "source_account_id": ["source account id"],
    "source_quote_id": ["source quote id"],
    "source_url": ["source url"],
    "value_metric_unit": ["value metric unit"],
    "cost_basis": ["cost basis"],
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
    s = re.sub(r"[\s_\-./:()\[\]]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _normalized_synonyms() -> dict[str, list[str]]:
    return {f: [normalize(a) for a in alts] for f, alts in SYNONYMS.items()}


_NORM_SYN = _normalized_synonyms()

# Fields claimed only by an exact normalized synonym or the exact field name,
# never by fuzzy, embedding or LLM matching. Bare words collide with real
# columns ("Credits" is a unit count in a credit-based book; Salesforce
# UnitPrice is the net sales price, not list). Same lesson as the Forecast
# Category guard in fuzzy_match. PR 73 review, 2026-11-07.
EXACT_ONLY_FIELDS = frozenset({
    "list_unit_rate", "credits_tcv",
    # Provenance fields: bare words like "Source" or "Account Source" are
    # ordinary CRM columns, so these claim only an exact synonym or name.
    "source_system", "source_record_id", "source_account_id", "source_quote_id",
    "source_url", "value_metric_unit", "cost_basis",
})
for _f in EXACT_ONLY_FIELDS:
    _NORM_SYN[_f].append(normalize(_f))


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
        if field in EXACT_ONLY_FIELDS:
            continue
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
            if name in EXACT_ONLY_FIELDS:
                continue
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


# --- Layer 0: source profile (header set only, deterministic) ---------------
#
# Profiles are generic export SHAPES, not vendor presets (founder decision D4,
# census 2026-11-07: no platform reaches the 30 percent threshold, and the
# quote tool is unknown for 45 of 47 accounts). The classifier reads header
# strings and nothing else; no row value is consulted, no LLM is involved.

PROFILE_CRM = "crm_opportunity"   # one row per deal
PROFILE_CPQ = "cpq_line"          # one row per quote line, many rows per quote
PROFILE_UNKNOWN = "unknown"

# Closed outcome enum. ask_user is an explicit bucket for anything we cannot
# place, because an unknown stage must never be guessed into closed_lost.
OUTCOME_WON, OUTCOME_LOST = "closed_won", "closed_lost"
OUTCOME_OPEN, OUTCOME_ASK_USER = "open", "ask_user"
OUTCOME_VALUES = (OUTCOME_WON, OUTCOME_LOST, OUTCOME_OPEN, OUTCOME_ASK_USER)

# Qualifiers that make a "status" column a billing or lifecycle state, not a
# sales outcome ("Subscription Status: canceled" is churn, not closed-lost).
_NON_OUTCOME_QUALIFIERS = frozenset({
    "subscription", "invoice", "payment", "billing", "renewal", "account",
    "customer", "contract", "license", "order", "shipping", "approval",
    "review", "delivery", "sync",
})
_STATUS_TOKENS = frozenset({"status", "stage", "state", "outcome"})
# Only a bare status or state header is ambiguous. A header naming a stage or
# an outcome is never blocked, whatever else the file contains.
_AMBIGUOUS_STATUS_TOKENS = frozenset({"status", "state"})
_QUOTE_ID_TAILS = frozenset({"id", "number", "no", "num", "ref", "key", "code"})
_QUOTE_WORDS = frozenset({"quote", "proposal"})

# Roll-up spec for cpq_line. Pure data so it can be shown, tested and audited.
CPQ_ROLLUP_SPEC: dict = {
    "join_key": "quote_id",            # role; the header is resolved per file
    "canonical_key_field": "source_quote_id",
    "sum": {"line_list": "list_acv", "line_booked": "booked_acv"},
    "outcome_from": "quote_status",
    "first_non_blank": ["account_name", "account_id", "opportunity_id",
                        "created_date", "close_date", "rep_id", "currency",
                        "segment", "region", "industry", "term_months"],
    "not_rolled_up": ["quantity"],     # units of different SKUs do not add
    "amounts": "summed as exported, never annualised or converted",
}


def _tokens(header: str) -> list[str]:
    return normalize(header).split()


def _field_of(header: str) -> Optional[str]:
    """Deterministic field guess for one header (layers 1 and 2 only)."""
    f = synonyms_match(header)
    if f:
        return f
    r = fuzzy_match(header)
    return r[0] if r else None


# Billing fingerprint: a subscription id column beside an interval, plan, MRR
# or period column, or an invoice number or amount-due column. In such a file a
# bare Status or State header is the billing state (active, canceled, paid,
# void), never a sales outcome. It never fires when CRM cues are present (an
# opportunity or deal id, a stage header): a CRM report with
# "Fiscal Period", "Plan" or "Customer ID" columns is still a CRM report.
_BILLING_PAIR_TOKENS = frozenset({"interval", "plan", "mrr", "period"})
_ID_TAILS = frozenset({"id", "number", "no", "num"})


def _billing_fingerprint(headers: list[str], roles: dict[str, str]) -> bool:
    toks = [set(_tokens(h)) for h in headers]
    # CRM vetoes: a deal id or a stage header. A close date alone is not one,
    # because billing exports carry close-like dates too.
    if roles.get("opportunity_id") or any("stage" in t for t in toks):
        return False
    has_sub_id = any("subscription" in t and (t & _ID_TAILS or len(t) == 1)
                     for t in toks)
    has_pair = any(t & _BILLING_PAIR_TOKENS for t in toks)
    invoice = any(("invoice" in t and t & _ID_TAILS) or t == {"amount", "due"}
                  for t in toks)
    return (has_sub_id and has_pair) or invoice


def _blocked_outcome_headers(headers: list[str], billing: bool) -> list[str]:
    """Bare status or state headers that must never be read as an outcome:
    qualified billing or lifecycle states ("Subscription Status", "Quote
    Approval Status") and, in a billing fingerprint, any bare status or state
    header. A header naming a stage or an outcome is never blocked."""
    out = []
    for h in headers:
        t = set(_tokens(h))
        if t & {"stage", "outcome"} or not t & _AMBIGUOUS_STATUS_TOKENS:
            continue
        if t & _NON_OUTCOME_QUALIFIERS or billing:
            out.append(str(h))
    return out


def _is_outcome_header(header: str) -> bool:
    toks = _tokens(header)
    if not toks or _NON_OUTCOME_QUALIFIERS & set(toks):
        return False
    return _field_of(header) == "outcome"


_EXACT_QUOTE_IDS = frozenset({"quote id", "quote number", "quote no", "quote num",
                              "quote", "proposal id", "proposal number"})


def _classify_roles(headers: list[str]) -> dict[str, str]:
    """Role -> header for the cues the profiles are built from. First header
    wins per role, in file order; a header serves one role only."""
    roles: dict[str, str] = {}
    used: set[str] = set()

    def put(role: str, h: str) -> None:
        if role not in roles and h not in used:
            roles[role] = h
            used.add(h)

    # Quote id: an exact "quote id" style header wins; otherwise any quote or
    # proposal id header, but never one naming the line ("Quote Line ID").
    for h in headers:
        if " ".join(_tokens(h)) in _EXACT_QUOTE_IDS:
            put("quote_id", h)
    for h in headers:
        toks = _tokens(h)
        tset = set(toks)
        if (toks and tset & _QUOTE_WORDS and "line" not in tset
                and toks[-1] in _QUOTE_ID_TAILS):
            put("quote_id", h)
    for h in headers:
        toks = _tokens(h)
        tset = set(toks)
        if not toks or h in used:
            continue
        n = " ".join(toks)
        if (tset & _QUOTE_WORDS and tset & {"status", "stage", "state"}
                and not tset & _NON_OUTCOME_QUALIFIERS):
            put("quote_status", h)
        elif "unit" in tset and tset & {"price", "rate", "amount"}:
            put("unit_list" if "list" in tset else "unit_net", h)
        elif "line" in tset and tset & {"total", "amount", "price", "value"}:
            put("line_list" if "list" in tset else "line_booked", h)
        elif "line" in tset and tset & {"id", "item", "number", "no", "num"}:
            put("line", h)
        elif n in ("line item", "line items"):
            put("line", h)
    for h in headers:
        if h in used:
            continue
        n = normalize(h)
        f = _field_of(h)
        if f == "sku" or n in ("product", "product name", "item name", "description"):
            put("line", h)
        elif f == "quantity":
            put("quantity", h)
        elif f == "list_acv":
            put("line_list", h)
        elif f == "booked_acv":
            put("line_booked", h)
        elif f == "close_date":
            put("close_date", h)
        elif f == "opportunity_id":
            put("opportunity_id", h)
        elif _is_outcome_header(h):
            put("outcome", h)
    # A quote status doubles as the outcome source; a plain outcome header does
    # too when the file is quote-shaped.
    if "quote_status" not in roles and "outcome" in roles:
        roles["quote_status"] = roles["outcome"]
    if "outcome" not in roles and "quote_status" in roles:
        roles["outcome"] = roles["quote_status"]
    return roles


def profile_source(headers: list[str]) -> dict:
    """Classify an export from its header set alone (no frame, no row values).

    Returns {profile, confidence, grain, evidence, missing, roles, rollup,
    billing_fingerprint}. `evidence` is the list of input headers that carried
    the decision; every entry is a header the caller passed in. `missing`
    names the cues the winning (or closest) profile lacks.
    """
    headers = [str(h).strip() for h in headers]
    roles = _classify_roles(headers)
    billing = _billing_fingerprint(headers, roles)
    # A blocked header never serves as quote status or outcome.
    blocked = set(_blocked_outcome_headers(headers, billing))
    for r in ("outcome", "quote_status"):
        if roles.get(r) in blocked:
            roles.pop(r)
    cpq_cues = ["quote_id", "line", "unit_net", "quantity", "quote_status"]
    unit_hdrs = {roles.get("unit_net"), roles.get("unit_list")}
    crm_amount = next((h for h in headers if h not in unit_hdrs
                       and _field_of(h) == "booked_acv"), None)
    crm_cues = {"outcome": roles.get("outcome"), "close_date": roles.get("close_date"),
                "amount": crm_amount or roles.get("line_booked")}

    has_unit_price = "unit_net" in roles or "unit_list" in roles
    cpq_hits = [c for c in cpq_cues
                if c in roles or (c == "unit_net" and has_unit_price)]
    is_cpq = ("quote_id" in roles and "line" in roles
              and (has_unit_price or "quantity" in roles))

    if is_cpq:
        profile = PROFILE_CPQ
        conf = "high" if len(cpq_hits) >= 5 else "medium"
        ev = [roles[r] for r in ("quote_id", "line", "unit_net", "unit_list",
                                 "quantity", "quote_status") if r in roles]
        missing = [c for c in cpq_cues if c not in cpq_hits]
        grain = "one row per quote line"
    elif crm_cues["outcome"] and (crm_cues["close_date"] or crm_cues["amount"]):
        profile = PROFILE_CRM
        conf = "high" if all(crm_cues.values()) else "medium"
        ev = [h for h in crm_cues.values() if h]
        missing = [k for k, v in crm_cues.items() if not v]
        grain = "one row per deal"
    else:
        profile, conf, grain = PROFILE_UNKNOWN, "none", "unknown"
        ev = [h for h in crm_cues.values() if h]
        missing = [k for k, v in crm_cues.items() if not v]
    return {"profile": profile, "confidence": conf, "grain": grain,
            "evidence": list(dict.fromkeys(ev)), "missing": missing,
            "roles": roles, "billing_fingerprint": billing,
            "rollup": CPQ_ROLLUP_SPEC if profile == PROFILE_CPQ else None}


def outcome_refusal(headers: list[str],
                    profile: Optional[dict] = None) -> Optional[dict]:
    """Structured refusal when no header can supply outcome, else None.

    Header-only and deterministic. A billing or quote export without a stage,
    status or outcome column cannot yield closed-won or closed-lost rows;
    guessing one would fabricate win rates.
    """
    p = profile or profile_source(headers)
    # Status-like headers we deliberately did not accept as an outcome
    # ("Subscription Status"): named so the caller can see why, and so the LLM
    # layer is not asked to promote one of them.
    blocked = _blocked_outcome_headers([str(h) for h in headers],
                                       bool(p.get("billing_fingerprint")))
    role = p["roles"].get("outcome")
    if role and role not in blocked:
        return None
    return {
        "refused": True,
        "blocked_headers": blocked,
        "decided_by": ("Deterministic layers decided this refusal. The LLM, "
                       "when enabled, was consulted only for non-outcome "
                       "headers and can never supply outcome."),
        "reason": "no_outcome_column",
        "profile": p["profile"],
        "missing": ["outcome"],
        "missing_detail": ("No stage, status or outcome column was found. A "
                           "subscription, invoice or payment status is a "
                           "billing state, not a sales outcome."),
        "message": ("This export cannot supply deal outcome (won or lost). "
                    "Add the CRM opportunity export, or a stage or status "
                    "column, and upload again."),
    }


# --- Stage normalisation (closed enum, explicit ask_user) -------------------

_STAGE_OPEN = {
    "open", "draft", "sent", "pending", "in review", "in progress",
    "prospecting", "qualification", "qualified", "needs analysis",
    "value proposition", "id decision makers", "perception analysis",
    "proposal price quote", "proposal", "negotiation review", "negotiation",
    "discovery", "demo", "contract sent", "presented", "viewed",
    "awaiting approval", "pending approval", "new", "working",
}
# CRM stage map: explicit won and lost words only. "Declined" or "Rejected"
# are quote-tool words and are not treated as a CRM closed-lost.
_CRM_WON = {"closed won", "won", "closedwon", "closed win", "win", "w",
            "accepted", "signed"}
_CRM_LOST = {"closed lost", "lost", "closedlost", "closed loss", "loss", "l"}
# cpq_line outcome map (PK-27 lead decision B): only an acceptance is a win.
# A declined, rejected, expired or cancelled quote is not a CRM closed-lost
# (gtm/data-readiness-checklists.md), so those and anything unrecognised go to
# ask_user. Explicit CRM-style "Closed Lost" or "Lost" words stay closed_lost.
_CPQ_WON = {"accepted", "signed", "won", "closed won", "closedwon", "booked"}
_CPQ_LOST = {"closed lost", "closedlost", "lost"}


STATUS_MAP_BILLING = "billing"


def _is_blank(v: object) -> bool:
    return v is None or (isinstance(v, float) and v != v)


def normalize_stage(value: object, value_map: str = PROFILE_CRM) -> str:
    """Map one stage or status value into closed_won | closed_lost | open |
    ask_user, with the named value map: PROFILE_CRM (default, crm_opportunity),
    PROFILE_CPQ (cpq_line quote status) or STATUS_MAP_BILLING (every value is
    ask_user). Exact lookup on the normalized string
    only, never a substring test, so "Closed - Lost to Competitor" is
    ask_user, not a guess. Blank, NaN, None and unrecognised values are
    ask_user, never closed_lost."""
    if _is_blank(value):
        return OUTCOME_ASK_USER
    if value_map == STATUS_MAP_BILLING:
        # Invoice and subscription states (paid, open, void, uncollectible,
        # draft, active, canceled) say nothing about a sales outcome. Every
        # value is ask_user: "open" here is an unpaid invoice, not an open deal.
        return OUTCOME_ASK_USER
    s = normalize(str(value))
    won, lost = ((_CPQ_WON, _CPQ_LOST) if value_map == PROFILE_CPQ
                 else (_CRM_WON, _CRM_LOST))
    if s in won:
        return OUTCOME_WON
    if s in lost:
        return OUTCOME_LOST
    if s in _STAGE_OPEN:
        return OUTCOME_OPEN
    return OUTCOME_ASK_USER


def normalize_stage_series(values, value_map: str = PROFILE_CRM
                           ) -> tuple[list[str], dict[str, int]]:
    """Normalise a column. Returns (outcomes, ask_user_counts) where
    ask_user_counts maps each unrecognised raw value ("" for blank or NaN) to
    its row count, so the user can resolve them. Stays in process; never sent
    to a provider."""
    out: list[str] = []
    ask: dict[str, int] = {}
    for v in values:
        o = normalize_stage(v, value_map)
        out.append(o)
        if o == OUTCOME_ASK_USER:
            key = "" if _is_blank(v) else str(v)
            ask[key] = ask.get(key, 0) + 1
    return out, ask


# --- cpq_line roll-up: quote lines to one canonical deal per quote ----------

_BLANK_IDS = {"", "nan", "none", "null", "<na>", "nat"}


def rollup_quote_lines(lines, roles: Optional[dict[str, str]] = None):
    """Roll a quote-line DataFrame up to one deal row per quote id.

    Join key: the quote id column (role `quote_id`), which becomes
    `source_quote_id` on the deal. list_acv and booked_acv are sums of the
    line list and booked amounts (a line total column when present, otherwise
    unit price times quantity), parsed with ingest.parse_money. Outcome comes
    from the quote status through normalize_stage with the cpq_line map; lines
    of one quote that disagree give ask_user. Pure deterministic arithmetic,
    no LLM. Raises ValueError when the file has no quote id column or no way
    to price a line. Amounts are summed as exported: multi-year quotes are
    not annualised here.

    Lines with a blank, NaN or None quote id are never grouped and never
    dropped silently: they are quarantined.

    Result attrs: join_key (header used), ask_user (quote id -> raw status
    values), quarantined_lines (DataFrame of the raw rows),
    quarantined_reason, opportunity_id_present, unpriced_lines (quote id ->
    count of lines with no computable booked amount).
    """
    import pandas as pd
    from pricing.ingest import parse_money  # lazy: ingest imports this module

    lines = lines.copy()
    lines.columns = [str(c).strip() for c in lines.columns]
    r = roles or profile_source(list(lines.columns))["roles"]
    key = r.get("quote_id")
    if not key or key not in lines.columns:
        raise ValueError("roll-up needs a quote id column; none was found")

    qid = lines[key].map(lambda v: "" if _is_blank(v) or pd.isna(v)
                         else str(v).strip())
    blank = qid.str.lower().isin(_BLANK_IDS)
    quarantined = lines[blank].copy()
    lines, qid = lines[~blank], qid[~blank]

    def _money(col: Optional[str]):
        if not col or col not in lines.columns:
            return None
        return parse_money(lines[col])

    def _qty(col: Optional[str]):
        # Thousands separators ("1,000") parse like money; never silently NaN.
        if not col or col not in lines.columns:
            return None
        return parse_money(lines[col])

    qty = _qty(r.get("quantity"))
    booked = _money(r.get("line_booked"))
    listed = _money(r.get("line_list"))
    if booked is None:
        unit = _money(r.get("unit_net"))
        if unit is None or qty is None:
            raise ValueError("roll-up cannot price lines: need a line total "
                             "column, or unit price and quantity")
        booked = unit * qty
    if listed is None:
        ulist = _money(r.get("unit_list"))
        listed = ulist * qty if (ulist is not None and qty is not None) else None

    work = pd.DataFrame({"_q": qid.values}, index=lines.index)
    work["booked_acv"] = booked
    if listed is not None:
        work["list_acv"] = listed
    status_col = r.get("quote_status")
    if status_col and status_col in lines.columns:
        work["_o"] = [normalize_stage(v, PROFILE_CPQ) for v in lines[status_col]]
        work["_raw"] = [("" if _is_blank(v) or pd.isna(v) else str(v))
                        for v in lines[status_col]]
    else:
        work["_o"] = OUTCOME_ASK_USER
        work["_raw"] = ""

    firsts: dict[str, str] = {}
    for role in CPQ_ROLLUP_SPEC["first_non_blank"]:
        h = r.get(role)
        if h and h in lines.columns:
            firsts[role] = h
    for h in lines.columns:
        f = _field_of(h)
        if (f in CPQ_ROLLUP_SPEC["first_non_blank"] and f not in firsts
                and h not in (key, status_col)):
            firsts[f] = h
    for field_name, h in firsts.items():
        work[field_name] = lines[h]

    rows, ask_user, unpriced = [], {}, {}
    for q, g in work.groupby("_q", sort=False):
        d: dict = {"source_quote_id": q}
        d["booked_acv"] = g["booked_acv"].sum(min_count=1)
        if "list_acv" in g:
            d["list_acv"] = g["list_acv"].sum(min_count=1)
        n_unpriced = int(g["booked_acv"].isna().sum())
        d["unpriced_lines"] = n_unpriced
        if n_unpriced:
            unpriced[q] = n_unpriced
        outs = set(g["_o"])
        d["outcome"] = outs.pop() if len(outs) == 1 else OUTCOME_ASK_USER
        if d["outcome"] == OUTCOME_ASK_USER:
            ask_user[q] = sorted(set(g["_raw"]))
        for f in firsts:
            s = g[f].dropna()
            s = s[s.astype(str).str.strip() != ""]
            d[f] = s.iloc[0] if len(s) else None
        # Never fill the CRM deal id with the quote id: they are different keys.
        d["opportunity_id"] = d.get("opportunity_id")
        d["line_count"] = len(g)
        d["source_system"] = SourceSystem.CPQ.value
        rows.append(d)
    cols = ["source_quote_id", "booked_acv"]
    if listed is not None:
        cols.append("list_acv")
    cols += ["unpriced_lines", "outcome", *firsts]
    cols += [c for c in ("opportunity_id", "line_count", "source_system")
             if c not in cols]
    deals = pd.DataFrame(rows, columns=cols)
    deals.attrs["join_key"] = key
    deals.attrs["ask_user"] = ask_user
    deals.attrs["unpriced_lines"] = unpriced
    deals.attrs["opportunity_id_present"] = "opportunity_id" in firsts
    deals.attrs["quarantined_lines"] = quarantined
    deals.attrs["quarantined_reason"] = (
        "blank, NaN or None quote id: line cannot be assigned to a quote"
        if len(quarantined) else "")
    return deals


# --- Orchestrator -----------------------------------------------------------

Confidence = str  # "high" | "medium" | "low" | "none"


def map_headers(headers: list[str], llm_fallback: bool = True,
                use_embeddings: bool = True) -> dict:
    """Return {mapping, confidence, used} for our schema fields.

    `mapping[field]` is the matched prospect header (or None).
    `confidence[field]` is one of high/medium/low/none.
    `used[header]` records which layer matched it (audit trail).

    Also returned:
      `profile`   layer-0 source profile (see profile_source): crm_opportunity,
                  cpq_line or unknown, with evidence headers and roles.
      `refusal`   None, or a structured refusal when no outcome source exists
                  after the deterministic layers (layers 1-3 and the profile
                  claim). Computed before layer 4, never alongside an outcome
                  claim. `refusal["decided_by"]` says the deterministic layers
                  decided and the LLM was consulted only for non-outcome headers.
      `llm_rejected`  [{field, header}] LLM suggestions dropped because they
                  named outcome (always) or a status-like header (when refused).
    The LLM never claims outcome. When layer 0 found an outcome role that
    layers 1-3 did not claim, it is claimed with layer label "profile".

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
    llm_rejected: list[dict] = []

    # Layer 0: deterministic source profile, header set only.
    profile = profile_source(headers)
    # Headers that must never be read as an outcome (billing states). Layers
    # 1-3 skip outcome claims on them.
    blocked_outcome = set(_blocked_outcome_headers(
        [str(h) for h in headers], bool(profile["billing_fingerprint"])))

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
        if f == "outcome" and h in blocked_outcome:
            continue
        if f and f not in field_to_header:
            _claim(f, h, "synonyms", "high")

    # Layer 2: fuzzy
    for h in headers:
        if h in claimed:
            continue
        r = fuzzy_match(h)
        if r and r[0] == "outcome" and h in blocked_outcome:
            continue
        if r and r[0] not in field_to_header:
            conf: Confidence = "high" if r[1] >= 95 else "medium"
            _claim(r[0], h, "fuzzy", conf)

    # Layer 3: embeddings (semantic, the catch for unusual phrasing)
    for h in (headers if use_embeddings else []):
        if h in claimed:
            continue
        r = embedding_match(h, notes=notes)
        if r and r[0] == "outcome" and h in blocked_outcome:
            continue
        if r and r[0] not in field_to_header:
            conf = "medium" if r[1] >= 0.65 else "low"
            _claim(r[0], h, "embedding", conf)

    # Profile claim: when layer 0 identified an outcome role (for example
    # Quote Status on cpq_line) that layers 1-3 did not claim, claim it
    # deterministically so the cascade and the profile never disagree.
    po = profile["roles"].get("outcome")
    if (po and "outcome" not in field_to_header and po not in claimed
            and po not in blocked_outcome):
        _claim("outcome", po, "profile", "high")

    # The refusal is computed after the deterministic cascade, so it is never
    # returned alongside a deterministic outcome claim.
    refusal = (None if "outcome" in field_to_header
               else outcome_refusal(headers, profile))

    # Layer 4: cloud LLM (header strings only, opt-in). Skipped when the
    # export carries a billing-state status column: the model must not be
    # offered a chance to promote it to outcome.
    llm_blocked = bool(refusal and refusal["blocked_headers"])
    if llm_fallback and not llm_blocked:
        unmatched_headers = [h for h in headers if h not in claimed]
        # outcome is never offered to the LLM; the rejection below stays as
        # the backstop for a reply that names it anyway.
        unmatched_fields = [f for f in _FIELDS_BY_NAME
                            if f not in field_to_header
                            and f not in EXACT_ONLY_FIELDS and f != "outcome"]
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
                        # The LLM never supplies outcome, on any file: reject
                        # and record every such claim before anything else.
                        if f == "outcome" and h:
                            llm_rejected.append({"field": f, "header": h})
                            continue
                        if not (h and h in unmatched_headers and h not in claimed
                                and f in unmatched_fields):
                            continue
                        # When layer 0 refused, a status-like header is not
                        # offered to any other field either.
                        if (refusal is not None
                                and set(_tokens(h)) & _AMBIGUOUS_STATUS_TOKENS):
                            llm_rejected.append({"field": f, "header": h})
                            continue
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
            "notes": notes, "llm_fallback_failed": llm_fallback_failed,
            "profile": profile, "refusal": refusal,
            "llm_rejected": llm_rejected}
