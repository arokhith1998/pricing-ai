"""Business panel review — four AI personas roleplay as domain experts.

Pricing strategist · Sales leader (CRO) · Business / GTM operator ·
B2B SaaS website marketer. Each gets the Pricekeel product brief + key copy
excerpts and is asked for a blunt, focused critique ending in BIGGEST RISK
and BIGGEST OPPORTUNITY.

Run:

  $env:PYTHONPATH = "C:\\pricing-ai"
  python tools/oai_panel.py

Requires OPENAI_API_KEY (or ANTHROPIC_API_KEY + LLM_PROVIDER=anthropic) in
C:/Pricing-AI/.env. Never sends customer data.
"""
from __future__ import annotations

from pricing import assist

# ---- the product brief ----------------------------------------------------

BRIEF = """
# Pricekeel — product brief (state: 2026-05-28)

Pricekeel is a pricing-intelligence platform for $10-100M ARR B2B SaaS
companies on usage-based or hybrid pricing models.

WEDGE: A free retrospective discount-leakage diagnostic built from a CSV
export of closed deals. Reframed in copy as "pricing upside to pursue".

ICP (validated against vault notes):
- Series B / early C, $15-60M ARR.
- Hybrid pricing (platform fee + usage metric). Avoid pure-seat / pure-outcome.
- Sales-led or hybrid PLG-to-sales with a deal desk that runs on spreadsheets.
- Champion: Head of Pricing or VP RevOps.
- Economic buyer: CFO.
- Unlocker: VP Sales / CRO.

WEDGE GTM (founder script):
"Send me a CSV of your last 4 quarters of closed deals; I'll show you your
discount leakage % and win rate by discount band — free, under NDA."

PRODUCT SURFACE (live on main):
- Landing pitch · ROI calculator widget · "Built for your stack" strip
  (Salesforce / HubSpot / Stripe / Zuora / Snowflake / Google Sheets, with
  'via CSV today' / 'Phase 3 connector' labels) · Founder bio strip
  (placeholder for Adhithya) · "Final phase: Margin Enhancement" teaser.
- /sample — diagnostic on bundled synthetic data; lead-gated for full view
  (lead form: name + company + title + role function + ARR range + pricing
  model + company email + consent checkbox + silent UTM capture).
- /diagnostic — win rate vs discount with confidence band and "win point"
  marker; price realization by segment + BU + product line; packaging signal
  (Rivera); trade-or-give (Simon-Kucher); three leakage lenses (gross,
  off-policy, beyond-win-point); quarter-end effect; governance gaps; top
  deals to investigate.
- /guidance — pick a deal -> recommended discount + expected-value uplift +
  win probability + top factors (LightGBM SHAP) + EV curve. AUC ~0.64,
  calibrated.
- /upload — CSV / Excel upload with mapping review UI. Four-layer column
  mapper: synonyms dict -> rapidfuzz -> local fastembed embeddings -> cloud
  LLM fallback. Hierarchy fields (BU / line / family / SKU) auto-slice
  the diagnostic when populated.
- Ask your Pricekeel — RAG slide-out chat panel: docs (PDF/DOCX/XLSX/PPTX/
  MD/TXT) + analysis JSON + optional Perplexity Sonar web search. Local
  embeddings; cloud LLM generation. Citations [A]/[D#]/[W#] enforced.
- /pricing — three tiers, all "Talk to us": Diagnostic / Pricekeel Operate /
  Margin Enhancement. No Stripe checkout.
- /blog — founder-bylined posts (Adhithya Bhaskar), Tue/Thu cadence.
- /privacy — DRAFT (needs counsel). Lead form has required consent checkbox.

ARCHITECTURE: Next.js 16 (Tailwind 4) + FastAPI + LightGBM win-prob model +
fastembed (BAAI bge-small ONNX, CPU) embeddings. Supabase provisioned (not
yet wired). Cloud LLM = OpenAI gpt-4o by default, swappable to Anthropic.
Row-level customer data NEVER leaves; only aggregates + header strings +
RAG chunks + user questions reach the cloud LLM.

CURRENT STATE:
- NOT yet deployed (Render + Vercel pending founder action).
- NO design partner yet, NO real customer data.
- NO LinkedIn page yet.
- /privacy is a draft pending counsel.
- Solo founder Adhithya Bhaskar (CEO); Claude playing CTO/CMO/CFO.

PHASE 3 ROADMAP ("Margin Enhancement"): Active-contract layer (special pricing
agreements, fixed discounts, renewal uplift gaps), NRR/expansion/contraction
metrics, native CRM + billing connectors, peer benchmarks, EVC inputs
(competitor + value), competitor-by-features intelligence. All deferred to
their own design docs.
"""

# ---- key copy excerpts (rendered text, not JSX) ---------------------------

LANDING_COPY = """
EYEBROW: PRICING INTELLIGENCE FOR USAGE-BASED B2B SAAS
H1: Stop giving away price that wins you nothing.
SUBHEAD: Pricekeel reads your closed deals and shows where discounting buys
wins, where it just gives money away, and the discount that earns the most
on the next deal. No warehouse, no integration. One CSV.
PRIMARY CTAs: "Try it on sample data" (-> /sample) · "Run it on your data" (-> /upload)

PROOF STRIP: "The pricing upside hiding in a typical book of deals"
- 10-20% of list price given up to discounting
- ~17% of booked value discounted past the point that wins anything
- 1 in 4 off-policy deals closed with no recorded approver
- Footnote: "Figures from the bundled sample. Your numbers come from your own data."

ROI CALCULATOR (new): two sliders (ARR + avg discount) -> live estimated
upside in dollars + % of ARR. Math: ARR * (avg_disc - 5%) * 0.6.

WHAT IT DOES (three cards):
- Find the leakage
- Find the win point
- Guide the next discount

BUILT FOR YOUR STACK (logo strip):
Salesforce · HubSpot · Stripe · Zuora · Google Sheets [via CSV today]
Snowflake [Phase 3 connector]

FINAL PHASE TEASER: "Margin Enhancement — coming soon. Connects to contracts
and CRM to find margin across the whole book: SPAs, fixed discounts,
renewal uplift left on the table, price-floor breaches."

FOUNDER STRIP: "Built by Adhithya Bhaskar" + bio one-liner placeholder.

CLOSING CTA: "See it on your own deals" — Start with the sample / Upload your CSV.
"""

PRICING_COPY = """
H1: Built for the conversation, not the credit card.
SUB: "We sell into pricing teams at $10-100M ARR B2B SaaS — that means an
actual scoping call, not a self-serve checkout. Pick the closest fit and we
will reply within one business day."

TIER 1 - Diagnostic (one-time):
"A one-time retrospective on your closed deals. The full diagnostic +
per-deal Guidance on the dataset you send. Under NDA if you need one."
Features: CSV/Excel upload, mapping reviewed locally · Win point + leakage
lenses + packaging signal + trade-or-give · Per-deal Guidance · Executive
summary written from the figures.
CTA: Talk to us

TIER 2 - Pricekeel Operate (recurring) [HIGHLIGHTED]:
"Diagnostic + Guidance, refreshed on every new quarter of deals. Ask-your-
Pricekeel on your team's actual policy and playbook docs."
Features: Quarterly refresh · Guidance on deals being quoted now · RAG chat
on your policy docs · Email digests of new signals.
CTA: Talk to us

TIER 3 - Margin Enhancement (final phase):
"The Phase 3 contract / margin layer. Connect Salesforce or HubSpot + Stripe
or Zuora; we read active contracts, special pricing agreements, and renewal
terms."
Features: Native connectors · Active-contract analysis · Renewal / expansion
/ contraction metrics · Peer benchmarks once base supports.
CTA: Talk to us

HOW WE SCOPE IT: Diagnostic = one-time engagement. Operate = annual contract,
ACV scales with deal volume + doc count. Margin Enhancement = custom.
"""

LEAD_FORM_FIELDS = """
Lead form (required to unlock the full /sample read-out):
1. Full name
2. Company
3. Title (e.g. VP Pricing)
4. Role function: Pricing / Finance / Sales-Revenue / RevOps-Deal Desk /
   Product / Founder-Exec / Other
5. Annual revenue: <$10M / $10M-$50M / $50M-$200M / $200M+
6. Pricing model: Seats per-user / Usage consumption / Hybrid (platform +
   usage) / Other
7. Company email (free-domain regex rejects gmail/outlook/yahoo/etc.)
8. Required consent checkbox: "I agree to the Privacy Policy and to being
   contacted about my results."

Silent UTM capture: utm_source / medium / campaign / term / content from URL.

Access-code gate (separate, for /upload of own data): user enters a code
issued after NDA conversation.
"""

# ---- personas -------------------------------------------------------------

PERSONAS = [
    (
        "1. Pricing Strategist",
        "You are a senior pricing strategist with 20 years in B2B SaaS pricing "
        "transformation. You've consulted at Simon-Kucher, written for OpenView, "
        "and led pricing at three usage-based scale-ups. You think in terms of: "
        "value-based pricing, EVC, value-metric fit, packaging architecture, "
        "discount governance, NRR via expansion mechanics, and the leaky bucket. "
        "Your honest read on most pricing analytics products is they're "
        "descriptive not prescriptive, and they can't survive a CFO's first "
        "'so what do I DO?' question. Tell the founder what's defensible, what's "
        "missing, what would land with a real Head of Pricing on a first call. "
        "Cite specific moves they should make. End with two bold lines: "
        "'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. ~350 words max. Be blunt."
    ),
    (
        "2. Sales Leader (CRO)",
        "You are a CRO who has led sales for three B2B SaaS companies from $10M "
        "to $100M ARR, selling into CFOs and Heads of Pricing in usage-based "
        "SaaS. You think in MEDDIC, deal velocity, champion-economic-buyer "
        "dynamics, land-and-expand mechanics, and 'no decision' as the hardest "
        "competitor. Look at this product and tell me: where does the deal "
        "die? What questions does the CFO ask in the first 10 minutes that "
        "this product can't answer yet? Where's the friction in the funnel "
        "from landing to signed PO? What's the single most important change "
        "to compress the deal cycle? End with two bold lines: "
        "'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. ~350 words max. Be blunt."
    ),
    (
        "3. Business / GTM Operator",
        "You are a B2B SaaS general partner and former CEO of a $50M ARR "
        "vertical SaaS company. You think about category creation, defensibility, "
        "moats, capital efficiency, sequencing, and how a true category leader "
        "emerges vs becoming a feature. You're skeptical of products that "
        "overlap with adjacent categories (RevOps tools, sales intelligence, "
        "deal desk software, CPQ). Tell the founder: is Pricekeel a category, "
        "a feature, or a service? What's the actual moat over time? Where are "
        "the biggest strategic risks? What would you fund harder, what would "
        "you cut? End with two bold lines: 'BIGGEST RISK:' and 'BIGGEST "
        "OPPORTUNITY:'. ~350 words max. Be blunt."
    ),
    (
        "4. B2B SaaS Website Marketer (Linear / Stripe tier)",
        "You are a B2B SaaS product marketer who built the websites for two "
        "YC-unicorn-tier companies. You think in terms of: hero-second "
        "comprehension ('what is this?'), social proof gradient, trust signals, "
        "scan-vs-read density, mobile-first information architecture, CTA "
        "hierarchy, intent-to-action latency, and the live demo loop. You "
        "reward clarity over cleverness. Review Pricekeel's funnel as a CFO "
        "buyer who has never heard of it. Where does it fail the 6-second test? "
        "What copy is undertuned? Where's friction? What single visible change "
        "would lift conversion the most? End with two bold lines: 'BIGGEST "
        "RISK:' and 'BIGGEST OPPORTUNITY:'. ~350 words max. Be blunt."
    ),
]

USER_PROMPT = f"""Here is the product. Review it from your seat. Be blunt.

============================== PRODUCT BRIEF ===============================
{BRIEF}

============================== LANDING COPY ================================
{LANDING_COPY}

============================== /pricing COPY ===============================
{PRICING_COPY}

============================== LEAD-FORM SHAPE =============================
{LEAD_FORM_FIELDS}
============================================================================

Reminder: end with 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:' bold lines.
"""


def run_round_one() -> dict[str, str]:
    """Round 1: each persona reviews the product cold. Returns name -> text."""
    out: dict[str, str] = {}
    for name, system in PERSONAS:
        bar = "=" * 78
        print(f"\n{bar}\n  ROUND 1 — {name}\n{bar}\n")
        try:
            text = assist._complete(system, USER_PROMPT, max_tokens=1100).strip()
        except Exception as exc:  # noqa: BLE001
            text = f"[error calling LLM: {exc}]"
        print(text)
        out[name] = text
    return out


def _round_two_system(original_system: str) -> str:
    """Prepend an adversarial 'react to the others' framing to each persona."""
    return (
        original_system
        + "\n\nThis is ROUND 2 of the panel review. In ROUND 1 you and three "
        "other experts each reviewed Pricekeel cold. Below are the OTHER "
        "THREE reviews. Read them honestly. Stay in your seat (you are "
        "still the same expert as in ROUND 1). Identify what you most "
        "disagree with, what you agree with on reflection, and what the "
        "founder should DO this week given the panel's collective signal. "
        "Be specific — name the moves. End with two bold lines: 'BIGGEST "
        "DISAGREEMENT WITH THE PANEL:' and 'TOP 3 ACTIONS THIS WEEK:'."
    )


def run_round_two(round_one: dict[str, str]) -> dict[str, str]:
    """Round 2: each persona reads the other three's R1 reviews and reacts."""
    out: dict[str, str] = {}
    names = [n for n, _ in PERSONAS]
    for name, system in PERSONAS:
        others = "\n\n".join(
            f"--- ROUND 1 from {other} ---\n{round_one[other]}"
            for other in names
            if other != name
        )
        user = (
            f"{USER_PROMPT}\n\n========= ROUND 1 — OTHER THREE REVIEWS =========\n"
            f"{others}\n\n=================================================\n"
        )
        bar = "=" * 78
        print(f"\n{bar}\n  ROUND 2 — {name}\n{bar}\n")
        try:
            text = assist._complete(
                _round_two_system(system), user, max_tokens=1100,
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
        "--round", type=int, choices=[1, 2], default=1,
        help="1 = cold reviews, 2 = cold reviews + adversarial cross-pollination",
    )
    args = ap.parse_args()
    r1 = run_round_one()
    if args.round == 2:
        run_round_two(r1)


if __name__ == "__main__":
    main()
