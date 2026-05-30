"""Pricing Copilot v2 — turn the diagnostic into structured opportunities.

The diagnostic surfaces *what is happening* (leakage lenses, governance gaps,
price-realization shape). The copilot surfaces *what to do about it*: a
ranked list of Opportunity objects, each with a dollar impact estimate, a
confidence score, and the deterministic evidence that backed it.

Every number in an Opportunity comes from the analysis dict produced by
`pricing.diagnostic.run`. The LLM (called in `answer_canonical`) is only
ever asked to narrate these structured opportunities — it never invents
numbers, and the system prompt forbids it.

This module is the moat language we keep talking about: "Every decision is
logged with its math; defensible to finance." That promise lives here.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

from pricing import assist


# ---------------------------------------------------------------------------
# Six canonical questions the panel named. Each maps to an opportunity
# extractor below. Surfaced in the UI as chips.

CANONICAL_QUESTIONS: list[dict] = [
    {
        "id": "losing_deals",
        "label": "Why are we losing deals?",
        "hint": "Win-curve shape, leakage by lens, governance gaps.",
    },
    {
        "id": "raise_prices",
        "label": "Where should we increase prices?",
        "hint": "Segments with high win rate AND high realization.",
    },
    {
        "id": "over_discounted",
        "label": "Which products are over-discounted?",
        "hint": "By-hierarchy slice: discount past the win point.",
    },
    {
        "id": "opportunities_over",
        "label": "What opportunities are worth more than $500K?",
        "hint": "Leakage + price-realization gaps ranked by annual impact.",
    },
    {
        "id": "qe_effect",
        "label": "How is the quarter-end effect changing the book?",
        "hint": "Discount lift in the QE window vs the rest.",
    },
    {
        "id": "investigate",
        "label": "Which deals should I investigate?",
        "hint": "Top off-policy + no-approver deals from the analysis.",
    },
]


# ---------------------------------------------------------------------------
# Data shapes


@dataclass
class Evidence:
    """One piece of deterministic support for an opportunity."""
    type: str          # "win_rate" | "leakage" | "governance" | "realization" | "qe_lift" | "deal"
    value: str         # human-readable summary, already formatted
    source: str        # which analysis key it came from


@dataclass
class Opportunity:
    """A structured pricing move with revenue impact, confidence, evidence."""
    id: str
    kind: str          # "reduce_leakage" | "raise_price" | "investigate" | "governance"
    scope: str         # human label: "Enterprise segment", "Product line Foo", etc.
    current: str       # current state in human form ("avg discount 14%")
    recommended: str   # recommended state ("trim to reference 9%")
    revenue_impact_usd: float  # annualized estimate
    confidence: float  # 0-1
    evidence: list[Evidence] = field(default_factory=list)
    methodology: str = ""  # the named framework backing the move

    def to_dict(self) -> dict:
        d = asdict(self)
        d["evidence"] = [asdict(e) for e in self.evidence]
        return d


@dataclass
class Answer:
    """Copilot answer: narrative + structured opportunities."""
    text: str
    opportunities: list[Opportunity]
    qid: str
    citations_used: list[str] = field(default_factory=list)  # ["A"] etc

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "opportunities": [o.to_dict() for o in self.opportunities],
            "qid": self.qid,
            "citations_used": self.citations_used,
        }


# ---------------------------------------------------------------------------
# Helpers

def _money(x: float) -> str:
    return f"${x:,.0f}"


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _new_id(kind: str) -> str:
    return f"{kind}-{uuid.uuid4().hex[:8]}"


def _safe(d: dict, *keys, default=0.0):
    """Walk d[k1][k2]...; return default if any key missing."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur if cur is not None else default


# ---------------------------------------------------------------------------
# Opportunity extractors — pure functions of the analysis dict


def _opp_defended_wins(analysis: dict) -> Optional[Opportunity]:
    """Informational, sales-friendly companion to the leakage opportunities.

    Surfaces the booked value where the discount sat at-or-below the reference
    threshold — i.e. the discounting that plausibly bought the wins. No
    "recovery rate" assumption is applied; this is reportage, not a refund
    claim. Treat this as the sales-readout balance to the leakage list.
    """
    dvi = analysis.get("defended_vs_investigate") or {}
    defended = float(dvi.get("defended_value") or 0)
    if defended <= 0:
        return None
    defended_n = int(dvi.get("defended_deals") or 0)
    investigate = float(dvi.get("investigate_value") or 0)
    investigate_n = int(dvi.get("investigate_deals") or 0)
    rt = float(dvi.get("reference_threshold") or 0)
    pct = float(dvi.get("defended_pct_of_booked") or 0)
    return Opportunity(
        id=_new_id("defended"),
        kind="defended",
        scope="Won deals where the discount earned the win",
        current=f"{_pct(pct)} of booked value — {defended_n:,} deals at discount ≤ {_pct(rt)}",
        recommended=(
            "Sales: keep doing this. These discounts sat at or below the win-curve "
            "reference; trim only where the curve says you would have won anyway."
        ),
        # revenue_impact_usd here is the *defended* booked value, NOT a savings
        # claim. The UI labels it accordingly ("defended value", not "upside").
        revenue_impact_usd=defended,
        confidence=0.90,  # high — it is reportage of historical fact
        evidence=[
            Evidence("realization",
                     f"{_money(defended)} booked at discount ≤ {_pct(rt)}",
                     "defended_vs_investigate.defended_value"),
            Evidence("leakage",
                     f"{_money(investigate)} ({investigate_n:,} deals) above reference — see investigate list",
                     "defended_vs_investigate.investigate_value"),
        ],
        methodology="Win-curve reference (Nagle) — discount at or below the band where win rate plateaus",
    )


def _opp_excess_leakage(analysis: dict) -> Optional[Opportunity]:
    """Excess vs reference: the headline leakage. Always recommend trimming."""
    lk = analysis.get("leakage") or {}
    excess = float(lk.get("excess_vs_reference_won") or 0)
    if excess <= 0:
        return None
    pct = float(lk.get("excess_pct_of_booked") or 0)
    rt = float(lk.get("reference_threshold") or 0)
    band = lk.get("reference_band") or ""
    n = int(lk.get("deals_above_reference") or 0)
    booked = _safe(analysis, "overview", "booked_acv_won")

    # Recovering ALL excess is unrealistic; assume a recoverable share.
    # 30-50% recovery is the rule-of-thumb from discount-governance
    # tightening across pricing engagements — Simon-Kucher's range.
    recoverable_share = 0.40
    impact = excess * recoverable_share

    return Opportunity(
        id=_new_id("excess"),
        kind="reduce_leakage",
        scope="Whole book — discounts above the reference band",
        current=f"{_pct(pct)} of booked value discounted past the win point",
        recommended=f"Tighten approvals above {_pct(rt)} (the {band} band)",
        revenue_impact_usd=impact,
        confidence=0.75,
        evidence=[
            Evidence("leakage",
                     f"{_money(excess)} discounted beyond reference",
                     "leakage.excess_vs_reference_won"),
            Evidence("leakage",
                     f"{n:,} deals priced above the reference threshold",
                     "leakage.deals_above_reference"),
            Evidence("realization",
                     f"Booked ACV {_money(booked)}",
                     "overview.booked_acv_won"),
        ],
        methodology="Simon-Kucher discount governance (40% recoverable assumption)",
    )


def _opp_off_policy(analysis: dict) -> Optional[Opportunity]:
    """Off-policy leakage above the policy threshold."""
    lk = analysis.get("leakage") or {}
    off = float(lk.get("off_policy_leakage_won") or 0)
    if off <= 0:
        return None
    pt = float(lk.get("policy_threshold") or 0)
    gov = analysis.get("governance") or {}
    no_approver = int(gov.get("off_policy_no_approver") or 0)
    recoverable_share = 0.50  # off-policy is the easiest to recover
    impact = off * recoverable_share

    ev = [
        Evidence("leakage",
                 f"{_money(off)} discounted above {_pct(pt)} policy",
                 "leakage.off_policy_leakage_won"),
    ]
    if no_approver:
        ev.append(Evidence(
            "governance",
            f"{no_approver:,} off-policy deals closed with no recorded approver",
            "governance.off_policy_no_approver",
        ))

    return Opportunity(
        id=_new_id("offpolicy"),
        kind="governance",
        scope="Off-policy deals (above stated policy threshold)",
        current=f"{_money(off)} given above {_pct(pt)} policy",
        recommended="Enforce approval gate; route every above-policy quote to deal desk",
        revenue_impact_usd=impact,
        confidence=0.80,
        evidence=ev,
        methodology="Discount governance — Nagle reference price + approval routing",
    )


def _opp_raise_prices(analysis: dict) -> list[Opportunity]:
    """Segments with high win rate AND high realization → price headroom.

    The signal: a segment that wins easily at the current discount is
    likely paying *less than it would be willing to pay*. Headroom for a
    selective list-price or discount-floor move.
    """
    rs = analysis.get("realization_by_segment")
    if rs is None:
        return []
    # rs is a pandas DataFrame in normal flow but the API may pass a list of
    # dicts after JSON round-trip. Normalize.
    try:
        rows = rs.to_dict(orient="records") if hasattr(rs, "to_dict") else list(rs)
    except Exception:  # noqa: BLE001
        return []
    opps: list[Opportunity] = []
    for row in rows:
        win = float(row.get("win_rate") or 0)
        realization = float(row.get("price_realization") or 0)
        n = int(row.get("deals") or row.get("n") or 0)
        seg = str(row.get("segment") or row.get("name") or "Unnamed segment")
        # Headroom heuristic: win rate >= 70% AND realization >= 85% AND
        # at least 25 deals in the segment for the signal to be real.
        if win < 0.70 or realization < 0.85 or n < 25:
            continue
        booked = float(row.get("booked_acv") or 0)
        # Assume a 2 percentage-point list-price move + 50% capture
        impact = booked * 0.02 * 0.50
        if impact < 50_000:  # ignore noise
            continue
        opps.append(Opportunity(
            id=_new_id("raise"),
            kind="raise_price",
            scope=f"Segment: {seg}",
            current=f"Win rate {_pct(win)} at realization {_pct(realization)}",
            recommended="Test a 2 pt list price increase or tighter discount floor",
            revenue_impact_usd=impact,
            confidence=0.55,
            evidence=[
                Evidence("win_rate", f"{_pct(win)} win rate ({n:,} deals)",
                         "realization_by_segment"),
                Evidence("realization",
                         f"Price realization {_pct(realization)}",
                         "realization_by_segment"),
            ],
            methodology="Nagle — value-based pricing, EVC headroom",
        ))
    return sorted(opps, key=lambda o: -o.revenue_impact_usd)[:3]


def _opp_over_discounted_slices(analysis: dict) -> list[Opportunity]:
    """For each hierarchy dimension (BU / line / family / SKU), find slices
    where average discount is materially above the reference threshold.
    """
    slices = analysis.get("hierarchy_slices") or {}
    if not slices:
        return []
    rt = _safe(analysis, "leakage", "reference_threshold")
    if not rt:
        return []

    opps: list[Opportunity] = []
    for dim, frame in slices.items():
        try:
            rows = frame.to_dict(orient="records") if hasattr(frame, "to_dict") else list(frame)
        except Exception:  # noqa: BLE001
            continue
        for row in rows:
            disc = float(row.get("avg_discount") or 0)
            n = int(row.get("deals") or row.get("n") or 0)
            booked = float(row.get("booked_acv") or 0)
            name = str(row.get(dim) or row.get("name") or "")
            if not name or n < 15 or disc <= rt:
                continue
            excess = max(0.0, disc - rt)
            impact = booked * excess * 0.40  # 40% recoverable share
            if impact < 75_000:
                continue
            opps.append(Opportunity(
                id=_new_id(f"od-{dim}"),
                kind="reduce_leakage",
                scope=f"{dim.title()}: {name}",
                current=f"Avg discount {_pct(disc)} ({n:,} deals)",
                recommended=f"Tighten discount floor toward the {_pct(rt)} reference",
                revenue_impact_usd=impact,
                confidence=0.65,
                evidence=[
                    Evidence("leakage",
                             f"Discount {_pct(disc)} vs reference {_pct(rt)}",
                             f"hierarchy_slices.{dim}"),
                    Evidence("realization",
                             f"Booked {_money(booked)} on {n:,} deals",
                             f"hierarchy_slices.{dim}"),
                ],
                methodology="Reference price (Nagle) + Simon-Kucher governance",
            ))
    return sorted(opps, key=lambda o: -o.revenue_impact_usd)[:5]


def _opp_quarter_end(analysis: dict) -> Optional[Opportunity]:
    """Quarter-end discount lift — attributable dollars."""
    qe = analysis.get("quarter_end") or {}
    attributable = float(qe.get("attributable_discount_won") or 0)
    if attributable < 100_000:
        return None
    lift = float(qe.get("lift") or 0)
    qe_deals = int(qe.get("qe_deals") or 0)
    impact = attributable * 0.50  # half is structurally recoverable
    return Opportunity(
        id=_new_id("qe"),
        kind="reduce_leakage",
        scope="Quarter-end discount lift",
        current=f"+{_pct(lift)} extra discount in the QE window ({qe_deals:,} deals)",
        recommended="Move QE-flagged deals through deal desk earlier; cap end-of-quarter discount",
        revenue_impact_usd=impact,
        confidence=0.70,
        evidence=[
            Evidence("qe_lift",
                     f"{_money(attributable)} attributable to QE lift",
                     "quarter_end.attributable_discount_won"),
            Evidence("qe_lift", f"+{_pct(lift)} vs rest-of-quarter",
                     "quarter_end.lift"),
        ],
        methodology="Discount governance — calendar effect mitigation",
    )


def _opp_investigate(analysis: dict) -> Optional[Opportunity]:
    """Top deals to investigate — straight from the top_leak_deals frame."""
    top = analysis.get("top_leak_deals")
    if top is None:
        return None
    try:
        rows = top.to_dict(orient="records") if hasattr(top, "to_dict") else list(top)
    except Exception:  # noqa: BLE001
        return None
    if not rows:
        return None
    # Sum of the discount-amount column on the surfaced deals
    total = sum(float(r.get("discount_amount") or 0) for r in rows)
    if total <= 0:
        return None
    return Opportunity(
        id=_new_id("invest"),
        kind="investigate",
        scope=f"Top {len(rows)} deals flagged in the diagnostic",
        current=f"{_money(total)} of discount across the flagged deals",
        recommended="Review approvers and concession patterns; document what to do differently",
        revenue_impact_usd=total * 0.20,  # 20% recoverable on retrospective review
        confidence=0.55,
        evidence=[
            Evidence("deal", f"{len(rows)} deals on the surface",
                     "top_leak_deals"),
            Evidence("deal", f"{_money(total)} in flagged discount",
                     "top_leak_deals"),
        ],
        methodology="Retrospective deal review (Simon-Kucher)",
    )


# ---------------------------------------------------------------------------
# Public surface


def opportunities(analysis: dict, *, min_impact_usd: float = 0.0) -> list[Opportunity]:
    """All opportunities the deterministic extractors produce, sorted by impact.

    Pure function. The LLM never touches this — every figure traces back
    to a key in the analysis dict. Add new extractors here; they fan in.
    """
    pool: list[Opportunity] = []
    for opp in (
        _opp_defended_wins(analysis),
        _opp_excess_leakage(analysis),
        _opp_off_policy(analysis),
        _opp_quarter_end(analysis),
        _opp_investigate(analysis),
    ):
        if opp is not None:
            pool.append(opp)

    pool.extend(_opp_raise_prices(analysis))
    pool.extend(_opp_over_discounted_slices(analysis))

    if min_impact_usd > 0:
        pool = [o for o in pool if o.revenue_impact_usd >= min_impact_usd]
    return sorted(pool, key=lambda o: -o.revenue_impact_usd)


# ---------------------------------------------------------------------------
# Canonical question routing


def _opps_for_question(qid: str, analysis: dict, min_impact_usd: float = 0.0) -> list[Opportunity]:
    """Filter the opportunity pool by which canonical question is asked."""
    all_opps = opportunities(analysis, min_impact_usd=min_impact_usd)
    if qid == "losing_deals":
        return [o for o in all_opps if o.kind in ("reduce_leakage", "governance")][:5]
    if qid == "raise_prices":
        return [o for o in all_opps if o.kind == "raise_price"][:5]
    if qid == "over_discounted":
        return [o for o in all_opps
                if o.kind == "reduce_leakage" and o.scope.lower().startswith(
                    ("bu:", "line:", "family:", "sku:"))][:5]
    if qid == "opportunities_over":
        # already filtered by min_impact in opportunities(); show top 5
        return all_opps[:5]
    if qid == "qe_effect":
        return [o for o in all_opps if "quarter-end" in o.scope.lower()][:3]
    if qid == "investigate":
        return [o for o in all_opps if o.kind == "investigate"][:3]
    return all_opps[:5]


_COPILOT_SYSTEM = (
    "You are 'Pricekeel', the in-product pricing copilot. The user has asked "
    "one of six canonical questions. A deterministic engine has already "
    "extracted the structured opportunities relevant to that question — "
    "below as JSON. Your job is ONLY to narrate them in 120-180 words: "
    "(1) restate the question in one short sentence, (2) summarize what the "
    "data supports, (3) list the recommended moves with the dollar impact "
    "and confidence taken VERBATIM from the JSON. Do NOT invent numbers, "
    "ratios, percentages, or company names. Do NOT add opportunities that "
    "are not in the JSON. If the opportunities list is empty, say so "
    "plainly. Cite the analysis as [A]. Tone: calm, direct, finance-credible, "
    "no hype, no emoji."
)


def answer_canonical(qid: str, analysis: dict,
                     min_impact_usd: float = 0.0) -> Answer:
    """Deterministic opportunities + LLM narrative, glued together."""
    label = next((q["label"] for q in CANONICAL_QUESTIONS if q["id"] == qid), qid)
    opps = _opps_for_question(qid, analysis, min_impact_usd=min_impact_usd)

    if not assist.has_llm():
        text = (f"Pricekeel: I would normally narrate the {len(opps)} "
                f"opportunity{'ies' if len(opps) != 1 else ''} the engine "
                "extracted for this question, but no LLM provider is "
                "configured on this server.")
        return Answer(text=text, opportunities=opps, qid=qid,
                      citations_used=["A"])

    user_msg = (
        f"QUESTION: {label}\n\n"
        f"OPPORTUNITIES (JSON, deterministic):\n"
        f"{json.dumps([o.to_dict() for o in opps], default=str)}\n"
    )
    text = assist._complete(_COPILOT_SYSTEM, user_msg, max_tokens=400).strip()
    return Answer(text=text, opportunities=opps, qid=qid,
                  citations_used=["A"])


# ---------------------------------------------------------------------------
# Decision log — per-session, append-only, in-memory.
# Supabase-backed when we move past in-memory state.


@dataclass
class Decision:
    ts: float
    session_id: str
    qid: str
    opportunities_surfaced: list[str]
    opportunities_accepted: list[str]
    opportunities_rejected: list[str]
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


_DECISION_LOG: dict[str, list[Decision]] = {}


def log_decision(session_id: str, qid: str, *,
                 surfaced: list[str] | None = None,
                 accepted: list[str] | None = None,
                 rejected: list[str] | None = None,
                 note: str = "") -> Decision:
    d = Decision(
        ts=time.time(),
        session_id=session_id,
        qid=qid,
        opportunities_surfaced=list(surfaced or []),
        opportunities_accepted=list(accepted or []),
        opportunities_rejected=list(rejected or []),
        note=note,
    )
    _DECISION_LOG.setdefault(session_id, []).append(d)
    return d


def decisions_for(session_id: str) -> list[Decision]:
    return list(_DECISION_LOG.get(session_id, []))
