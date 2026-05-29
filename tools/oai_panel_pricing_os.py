"""Blind panel review — does the multi-vertical AI Pricing-OS vision make sense?

Four AI personas evaluate a product vision cold, with NO knowledge of:
  - the founder's existing product (Pricekeel)
  - the prior business panel review (2026-05-28, 4/4 said "stay narrow")
  - the founder's path-dependence
  - the current code state

The brief describes the multi-vertical Pricing-OS as if a pre-seed founder
walked in with a deck and pitched it for the first time. The panel evaluates
it on its merits: category, moat, fundability, technical feasibility.

Round 1 = each persona reviews cold.
Round 2 = each persona reads the other three and reconsiders.

Run:
  $env:PYTHONPATH = "C:\\pricing-ai"
  python tools/oai_panel_pricing_os.py --round 2

Requires OPENAI_API_KEY (or ANTHROPIC_API_KEY + LLM_PROVIDER=anthropic).
"""
from __future__ import annotations

from pricing import assist

# ---- the blind brief ------------------------------------------------------

BRIEF = """
# Product vision — AI Pricing Operating System & Competitive Intelligence Platform

## What it is

An AI-powered Pricing OS that delivers competitive intelligence, dynamic
pricing recommendations, and explainable monetization decisions across
multiple verticals from a single platform.

NOT another web scraper. NOT another price monitoring dashboard. The pitch
is: the system of record for pricing decisions across any industry where
price is contested.

## Verticals targeted at launch

The vision is one platform serving SEVEN verticals from day one with shared
infrastructure and vertical-specific modules:

1. B2B SaaS — pricing page monitoring, plan comparison, packaging analysis,
   feature-level benchmarking, launch detection, pricing experiments,
   monetization recommendations.
2. Ecommerce — Amazon, Walmart, eBay, Shopify stores, D2C site monitoring,
   marketplace intelligence, promotion tracking.
3. Retail — competitor shelf-price monitoring, MAP compliance, marketplace
   intelligence.
4. Manufacturing / Industrial — distributor catalogs, OEM pricing,
   regional pricing analysis, channel pricing comparison, margin leakage.
5. Automotive — dealer networks, aftermarket parts pricing, OEM pricing,
   regional comparisons.
6. Distributor / Channel — distributor pricing intelligence across
   multi-tier channel.
7. Cross-vertical — executive pricing dashboards.

## Core capability set

**AI Product Matching Engine.** Match equivalent products, plans, SKUs,
components, parts, and services across competitors using embeddings,
feature extraction, structured attribute parsing, and semantic similarity.

**AI Pricing Copilot.** Natural-language Q&A grounded in customer's own
pricing data + competitor data + market signals. Sample questions the
copilot must answer:
  - Why are we losing deals?
  - Which competitors are undercutting us?
  - Where should we increase prices?
  - Which products are over-discounted?
  - What pricing opportunities exist worth more than $500K?
  - How has competitor behavior changed in the last 90 days?

**Recommendation engine.** Uses competitor pricing + historical trends +
demand signals + promotions + inventory signals + channel pricing + market
conditions to generate explainable pricing recommendations with:
  - estimated revenue impact
  - estimated margin impact
  - confidence score
  - supporting evidence

**Other modules** the brief calls out: competitor price monitoring,
historical pricing, promotion tracking, marketplace intelligence, MAP
compliance, dynamic pricing recommendations, predictive pricing analytics,
inventory-aware pricing signals, distributor pricing intelligence, dealer
pricing intelligence, executive dashboards.

## Stated competitive landscape

The founder names the following as competitors to evaluate against:
PriceIntel.ai, PriceIntelGuru, Competera, Pricefx, Vendavo, PROS, Prisync,
Wiser, Intelligence Node.

## Founder + capital state

Solo founder. Pre-seed. Pre-revenue. No design partner signed. No
customer data yet. Founder has domain background in pricing strategy.
Currently bootstrap, planning to raise on the basis of this vision.

## What the founder explicitly asks the panel

1. Is this vision a category, a feature, or a service? What is the actual
   moat over time?
2. Which features create the strongest defensible moat? Which are
   commodity? Which are unnecessary complexity at this stage?
3. Which verticals (if any) should launch first? Which should be cut?
4. What is the fastest path to revenue and product-market fit?
5. What is the realistic phasing — Phase 1 / 2 / 3?
6. Can this become a venture-scale ($100M+ ARR) business? If not, what
   would?
7. Where will this fail? What would a better, more focused alternative
   look like?

Be brutally honest. Founder explicitly asked for it.
"""

# ---- personas — calibrated for THIS vision, not for a SaaS wedge -----------

PERSONAS = [
    (
        "1. Principal Product Manager — Multi-Vertical SaaS Platforms",
        "You are a Principal PM who has shipped multi-vertical platform "
        "products at Salesforce, Workday, and a vertical SaaS scale-up "
        "(say Toast or Procore). You have built single-platform / "
        "vertical-config products and you have seen them fail. You think "
        "in terms of: platform abstractions that actually transfer vs "
        "configurations that masquerade as platforms; the cost of being "
        "a horizontal-platform play; sequencing of vertical modules; the "
        "0-to-1 vs 1-to-N problem; when 'one platform serves seven "
        "verticals' is real and when it is fiction. Evaluate this vision "
        "as the PM would in a portfolio-review meeting. Be specific about "
        "which features genuinely share infrastructure and which would "
        "require fundamentally different products. Cite real comparable "
        "product successes and failures. End with two bold lines: "
        "'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. ~400 words max. Blunt."
    ),
    (
        "2. Cross-Vertical Pricing Strategy Consultant",
        "You are a senior partner at a global pricing consultancy "
        "(Simon-Kucher / McKinsey pricing practice tier) with 20+ years "
        "spanning B2B SaaS pricing, CPG / retail pricing, industrial / B2B "
        "manufacturing pricing, and automotive. You think in EVC, value-"
        "metric architecture, discount governance, MAP enforcement, "
        "channel pricing dynamics, dealer-incentive economics, contract "
        "leakage in B2B, and what each industry's pricing buyer actually "
        "wakes up worrying about. Honest read on most multi-vertical "
        "pricing-intelligence products: they collapse into either retail "
        "competitive-scraping tools or enterprise B2B optimization tools — "
        "and the cross-vertical methodology rarely actually transfers. "
        "Evaluate: does the methodology transfer across these 7 verticals, "
        "or are these actually 7 different products that happen to share "
        "a name? Name where the methodology genuinely transfers and where "
        "it does not. End with two bold lines: 'BIGGEST RISK:' and "
        "'BIGGEST OPPORTUNITY:'. ~400 words max. Blunt."
    ),
    (
        "3. Data Platform Architect / Senior Engineer",
        "You are a senior staff engineer / data platform architect who has "
        "built large-scale data acquisition systems at Wiser, Bright Data, "
        "or Prisync. You think in terms of: scraping infrastructure cost "
        "at scale, anti-bot evasion, proxy rotation, legal exposure under "
        "DMCA / CFAA / TOS, the unit economics of price coverage, the "
        "compute and storage cost of historical pricing across millions "
        "of SKUs, the engineering team size required to maintain each "
        "vertical's data pipeline, partnerships required for closed-data "
        "verticals (dealer feeds, distributor catalogs). Evaluate this "
        "vision from a build-feasibility standpoint. What is the realistic "
        "engineering cost (FTEs + infrastructure $) to deliver each of "
        "the 7 verticals at parity with the named competitors? Where are "
        "the data acquisition cliffs that a solo founder cannot cross? "
        "What is buildable in 6 months, 18 months, never? End with two "
        "bold lines: 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. ~400 "
        "words max. Blunt."
    ),
    (
        "4. Vertical Software Investor (Series A partner)",
        "You are a Series A partner at a top vertical-software fund "
        "(Bessemer / Insight / Battery / OpenView tier). You have led "
        "investments in pricing software (Pricefx-like, Vendavo-like) and "
        "in vertical SaaS. You think in: category dynamics, ACV ladders, "
        "GTM motion fit, capital efficiency from seed to A, defensibility "
        "(data moats vs methodology moats vs distribution moats), exit "
        "comparables, and what a fundable founder narrative looks like in "
        "the current pricing-software category. Evaluate this vision as "
        "you would in a partner meeting. Is this fundable as pitched? If "
        "not, what is the minimum reframing that makes it fundable? What "
        "comparable companies should the founder study, and where do they "
        "diverge from this plan? What would you fund, what would you cut, "
        "and what would you postpone? Be honest about whether this is "
        "venture-scale or a $5–20M ARR lifestyle business. End with two "
        "bold lines: 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. ~400 "
        "words max. Blunt."
    ),
]

USER_PROMPT = f"""Here is a product vision a pre-seed founder has put in
front of you. Evaluate it cold from your seat. You have no prior knowledge
of this founder, no prior pitch from them, and no prior product context.
Treat the brief at face value. Be brutally honest — they asked.

============================== PRODUCT VISION ==============================
{BRIEF}
============================================================================

Reminder: end with 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:' bold lines.
"""


def run_round_one() -> dict[str, str]:
    out: dict[str, str] = {}
    for name, system in PERSONAS:
        bar = "=" * 78
        print(f"\n{bar}\n  ROUND 1 — {name}\n{bar}\n")
        try:
            text = assist._complete(system, USER_PROMPT, max_tokens=1300).strip()
        except Exception as exc:  # noqa: BLE001
            text = f"[error calling LLM: {exc}]"
        print(text)
        out[name] = text
    return out


def _round_two_system(original_system: str) -> str:
    return (
        original_system
        + "\n\nThis is ROUND 2 of the panel review. In ROUND 1 you and three "
        "other experts each reviewed this vision cold. Below are the OTHER "
        "THREE reviews. Read them honestly. Stay in your seat (you are still "
        "the same expert as in ROUND 1). Identify what you most disagree "
        "with on reflection, what you agree with, and — taking the panel's "
        "collective signal — what you would actually advise the founder to "
        "build vs cut. Be specific. End with two bold lines: 'BIGGEST "
        "DISAGREEMENT WITH THE PANEL:' and 'TOP 3 ACTIONS THIS QUARTER:'."
    )


def run_round_two(round_one: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    names = [n for n, _ in PERSONAS]
    for name, system in PERSONAS:
        others = "\n\n".join(
            f"--- ROUND 1 from {other} ---\n{round_one[other]}"
            for other in names if other != name
        )
        user = (
            f"{USER_PROMPT}\n\n========= ROUND 1 — OTHER THREE REVIEWS =========\n"
            f"{others}\n\n=================================================\n"
        )
        bar = "=" * 78
        print(f"\n{bar}\n  ROUND 2 — {name}\n{bar}\n")
        try:
            text = assist._complete(
                _round_two_system(system), user, max_tokens=1300,
            ).strip()
        except Exception as exc:  # noqa: BLE001
            text = f"[error calling LLM: {exc}]"
        print(text)
        out[name] = text
    return out


def main() -> None:
    if not assist.has_llm():
        raise SystemExit(
            "No LLM provider configured. Put OPENAI_API_KEY (or "
            "ANTHROPIC_API_KEY + LLM_PROVIDER=anthropic) in C:/Pricing-AI/.env."
        )
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--round", type=int, choices=[1, 2], default=2,
        help="1 = cold reviews, 2 = cold + adversarial cross-pollination",
    )
    args = ap.parse_args()
    r1 = run_round_one()
    if args.round == 2:
        run_round_two(r1)


if __name__ == "__main__":
    main()
