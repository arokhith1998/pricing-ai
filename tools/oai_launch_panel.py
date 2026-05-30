"""Launch-readiness panel — eight personas review Pricekeel as it stands today.

CTO · COO · CMO · VP Pricing (buyer-side) · CRO · Business expert · Startup
expert · Website / conversion expert.

Each gets the same brief: what is shipped, what is pending, what the founder
explicitly cares about for launch. Round 1 = cold reviews. Round 2 = each
reads the other seven and reacts.

Run:
  $env:PYTHONPATH = "C:\\pricing-ai"
  python tools/oai_launch_panel.py --round 2
"""
from __future__ import annotations

from pricing import assist

# ---- the brief ------------------------------------------------------------

BRIEF = """
# Pricekeel — launch-readiness brief (state: 2026-05-29)

## Product, live URLs

- **pricekeel.com** — Next.js 16 on Vercel, custom domain wired today
  (apex + www + api.pricekeel.com). Server: Vercel iad1. SSL clean.
- **api.pricekeel.com** — FastAPI in a Docker container on Render Starter
  ($7/mo, Virginia us-east-1). /health returns ok.
- **Supabase** project pricekeel-prod (us-east-1, Free tier). Tables: leads,
  access_codes. Service-role only; no anon key in browser. Lead-gated routes
  go through the captured-lead cookie; access-code routes require an NDA-
  issued code.
- Total live burn: ~$8.50/mo. Pre-revenue.

## What is shipped (live in product)

1. Landing page (`/`) — narrow positioning ("Pricing-leakage diagnostic and
   deal guidance for usage-based B2B SaaS"), ROI calculator, stack strip,
   founder strip (placeholder bio), Margin-Enhancement Phase-3 teaser.
2. `/sample` — diagnostic on bundled synthetic data; lead-gated for the
   full read-out. Form captures: name, company, title, role function, ARR,
   pricing model, company email, consent. UTM silent capture.
3. `/diagnostic` — full diagnostic on the active dataset. Three leakage
   lenses (gross / off-policy / beyond-win-point), win-curve + win point,
   price realization by segment + hierarchy slice, packaging signal
   (Rivera), trade-or-give (Simon-Kucher), quarter-end effect, governance
   gaps, top deals to investigate.
4. `/guidance` — LightGBM win-probability model + SHAP factors. Per-deal
   recommended discount, expected-value uplift, calibrated win probability.
   AUC ~0.64, calibration is the highlighted card.
5. `/upload` — CSV / XLSX upload with the four-layer mapper (synonyms →
   rapidfuzz → fastembed → cloud LLM fallback). Hierarchy fields (BU /
   line / family / SKU) auto-slice the diagnostic when populated.
6. **Pricing Copilot v2** (just shipped today) — six canonical questions
   as UI chips: "why are we losing deals?", "where should we raise
   prices?", "which products are over-discounted?", "what opportunities
   are worth more than $X?", "how is the quarter-end effect changing the
   book?", "which deals to investigate?". Each routes through a
   deterministic opportunity extractor that turns the analysis into
   structured Opportunity objects (scope, current→move, ANNUALIZED $
   IMPACT, confidence, evidence, methodology). The LLM only narrates;
   never invents numbers. OpportunityCards have Accept / Dismiss; every
   decision is logged to a per-session decision log. Tagline visible
   in product: "Decisions are logged with their math. Defensible to
   finance."
7. **AI Product Matching v1** (just shipped today) — /competitor-watch
   page. Customer enters their own pricing-page URL + up to 8 named
   competitor URLs. Server fetches each (1h cache, 250KB cap), LLM
   extracts structured plans, fastembed + rapidfuzz match yours vs
   theirs, surface pricing position (above/at/below market) +
   feature deltas. NOT a market-wide scraper.
8. /pricing — three tiers, all "Talk to us": Diagnostic / Pricekeel
   Operate / Margin Enhancement. No Stripe checkout. CFO-question FAQ
   ("proven ROI?", "integrations?", "security?"). "Why we are not a
   feature" section. Anchor line: "Engagements typically start in the
   low five figures."
9. /blog — MDX, founder-bylined (Adhithya Bhaskar). Two posts live, plus
   a calendar for Tue/Thu posts.
10. /privacy — DRAFT (counsel review pending).
11. LinkedIn company page exists at linkedin.com/company/pricekeel.
    Name + tagline saved earlier today; **Details tab + logo + cover
    image + first launch post still pending** (LinkedIn lock conflicts
    blocked the automated path; manual paste in vault).
12. Twelve unit tests on the copilot opportunity extractors (dollar math)
    and twelve on the matching algorithm (scoring, deltas, caching).

## What is NOT yet done — explicit gating

- **Zero design partners. Zero customer conversations. Zero LinkedIn
  posts. Zero followers on the company page.**
- LinkedIn personal profile (Adhithya's) not yet set up per the strategy
  doc (`vault/GTM/linkedin-strategy.md` exists but not applied).
- LinkedIn company page Details copy, logo, cover image, launch post —
  ready in vault for manual paste.
- Microsoft 365 email DNS in GoDaddy still propagating; `adhithya@
  pricekeel.com` is targeted as the public contact but not yet wired
  into `NEXT_PUBLIC_CONTACT_EMAIL`.
- Counsel review of /privacy.
- Founder headshot, real bio at `/founder.jpg` and About section.
- No paid acquisition. No tracking pixels beyond first-party UTM
  capture.

## Founder + capital

Solo founder (Adhithya Bhaskar). Pre-seed. Pre-revenue. Pricing strategy
background. Currently bootstrap. The vault has decisions explicitly
rejecting both (a) a multi-vertical Pricing-OS Phase-1 expansion, and
(b) the e-commerce / retail / manufacturing pivot. Phase 1 stays SaaS-
only — but with the Pricing-OS narrative kept as the long-term fundraising
north star (per the 2026-05-29 blind panel).

## Explicit questions for THIS panel

1. **Is this ready to put in front of a paying VP Pricing / CFO?**
   Where will it fall over at first contact with a real buyer?
2. **What is the single most important launch-blocking thing missing?**
3. **What is the right launch sequence — soft (1-1 founder DMs), loud
   (Product Hunt / Hacker News), or vertical (Pavilion / Pricing Society
   community)?**
4. **Is the product priced wrong on the /pricing page?** ("Low five
   figures" anchor — too high, too low, or about right for the ICP?)
5. **Is there enough product here to ASK for money, or should the
   diagnostic stay free for the first N customers regardless?**
6. **What is the right design-partner ask?** What do we offer them, what
   do we ask in return, and what does the first 30 minutes of that
   conversation actually look like?
7. **Where would a hostile reviewer (skeptical CFO, jaded pricing analyst,
   former PROS sales engineer) destroy this on a 30-minute call?**
8. **In your seat specifically, what should the founder do this week?**
   Three concrete actions, no theory.

Be brutally honest. Founder explicitly asked for it. The 2026-05-28 panel
(four personas) and the 2026-05-29 blind panel (four personas) have
already established that scope discipline is good — the founder is not
debating expansion. This panel is about LAUNCH.
"""


# ---- personas -------------------------------------------------------------

PERSONAS = [
    (
        "1. CTO",
        "You are a CTO who has shipped two B2B SaaS products from 0 to $20M ARR "
        "and one that died at $2M because the architecture could not absorb the "
        "first 30 paying customers. You think in: where does this break at 30 "
        "logos, what is the on-call story, what is the time-to-first-byte for "
        "a new customer's CSV, what is the failure mode when a column mapping "
        "is wrong, what is the security posture from a CFO's first IT review. "
        "Evaluate this launch-readiness from your seat. Where are the seams "
        "that will tear at first paying customer scale? What technical risk is "
        "the founder overlooking? What would you ship or rip before opening "
        "the gate to a real customer? End with 'BIGGEST RISK:' and 'BIGGEST "
        "OPPORTUNITY:'. ~350 words. Be blunt."
    ),
    (
        "2. COO",
        "You are a COO who has built revenue-operations functions at three "
        "B2B SaaS companies from seed to series B. You think in: customer "
        "lifecycle, time-to-value, support cadence, billing readiness, "
        "renewal mechanics, SLA exposure, the actual paper trail from first "
        "call to PO. Evaluate the launch-readiness from your seat. Is there "
        "an operating model for the first 5 paying customers? Where is the "
        "first failure of operations going to come from (NDA churn, support, "
        "billing, contract storage, expectation mismatch)? What is the "
        "single operational scaffold you would put in place this week? End "
        "with 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. ~350 words. Blunt."
    ),
    (
        "3. CMO",
        "You are a B2B SaaS CMO who has launched two pricing / monetization "
        "products into the same buyer ICP this brief targets. You think in: "
        "positioning, narrative arc, hero-to-CTA latency, channel-vs-content "
        "fit, the launch-week 14-day sequence, founder-led vs brand-led "
        "voice, paid vs organic in the first 90 days. Evaluate the launch-"
        "readiness from your seat. What launch sequence beats every other? "
        "What story arc moves a Head of Pricing to forward this to their "
        "CFO? Where does the current narrative misfire? What single asset "
        "would you build that does not exist yet? End with 'BIGGEST RISK:' "
        "and 'BIGGEST OPPORTUNITY:'. ~350 words. Blunt."
    ),
    (
        "4. VP Pricing — the buyer",
        "You ARE the buyer. You are a VP Pricing at a $40M ARR B2B SaaS "
        "company on usage-based pricing. You report to the CFO, dotted line "
        "to the CRO. You have seen ProfitWell die, Vendr try to do everything, "
        "and three vendors pitch you something that did not survive a real "
        "discount conversation. You think in: would I forward this to my "
        "CFO, can the diagnostic survive a hostile counter-question from "
        "my Head of FP&A, is the methodology credible, are the numbers "
        "defensible, what would I lose if this vendor went away. Evaluate "
        "Pricekeel as if a peer at another company sent you the link and "
        "asked you to react. Would you take a 30-minute call? Would you "
        "let them touch your closed-deal CSV? What would you push back on "
        "hardest? End with 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. "
        "~350 words. Blunt."
    ),
    (
        "5. Sales Head (CRO)",
        "You are a CRO who has built two sales teams in the pricing / "
        "RevOps tools category. You think in: ICP fit, discovery questions, "
        "MEDDPICC, what unlocks the CFO conversation, when free wins vs "
        "when it dilutes value, what makes a champion turn into a buyer, "
        "where 'no decision' kills 60% of pipeline. Evaluate this launch "
        "from a sales-mechanics view. Is the pricing right? Is 'low five "
        "figures' the right anchor? Should the diagnostic stay free, or "
        "is that conditioning the market to never pay? What is the right "
        "design-partner ask, and what does the actual first 30 minutes of "
        "that conversation look like? Where does the deal die? End with "
        "'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. ~350 words. Blunt."
    ),
    (
        "6. Business Expert (operator / partner)",
        "You are a former vertical-SaaS CEO turned operator-investor. "
        "You think in: capital efficiency, time-to-revenue, defensibility, "
        "moat dynamics, category vs feature, sequencing — what creates "
        "leverage and what is just busy work. The founder is solo, "
        "pre-revenue, with two AI capabilities just shipped (Copilot + "
        "Product Matching) on top of a working diagnostic. Evaluate the "
        "business-model readiness. Is this venture-scale or a $5-20M "
        "lifestyle? What unit economics make sense for the first 10 "
        "customers? Where is real defensibility being built vs accumulated "
        "feature debt? End with 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. "
        "~350 words. Blunt."
    ),
    (
        "7. Startup Expert (pre-seed / seed)",
        "You are a former founder + current pre-seed accelerator partner "
        "(YC / Techstars / South Park Commons tier). You think in: "
        "founder energy, sequencing, time allocation, the 3-week sprint "
        "between intent and traction, what kills pre-seed founders, when "
        "to raise vs when to wait, when the product is too narrow vs "
        "when the founder is too broad. Evaluate the launch-readiness "
        "from a founder-execution lens. Where is the founder spending "
        "time that does not compound? What is the highest-leverage "
        "single move available this week? Are they ready to put this in "
        "front of a check-writing investor, or wait? End with 'BIGGEST "
        "RISK:' and 'BIGGEST OPPORTUNITY:'. ~350 words. Blunt."
    ),
    (
        "8. Website / Conversion Expert",
        "You are the product marketer / conversion strategist who built "
        "the websites for two YC-unicorn-tier B2B SaaS companies. You "
        "think in: 6-second hero comprehension, scan-vs-read density, "
        "social-proof gradient, intent-to-action latency, demo loop "
        "speed, the single line of copy that compresses the cycle, the "
        "info architecture for a buyer who has never heard of you. "
        "Look at pricekeel.com as a CFO buyer arriving from a LinkedIn "
        "post. Where does the funnel leak between hero and lead form? "
        "What single visible change would lift demo→lead conversion the "
        "most? What is undertuned on /pricing, /sample, /diagnostic? "
        "End with 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:'. ~350 "
        "words. Blunt."
    ),
]

USER_PROMPT = f"""Here is the launch-readiness brief. Review it from your seat.
Be blunt; the founder asked.

============================== BRIEF =======================================
{BRIEF}
============================================================================

Reminder: end with 'BIGGEST RISK:' and 'BIGGEST OPPORTUNITY:' on bold lines.
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
        + "\n\nThis is ROUND 2. In ROUND 1 you and seven other experts each "
        "reviewed Pricekeel cold. Below are the OTHER SEVEN reviews. Stay "
        "in your seat — you are still the same expert. Identify what you "
        "most disagree with on reflection, what you now agree with, and "
        "what the founder should DO this week given the collective signal. "
        "Be specific — name the moves. End with 'BIGGEST DISAGREEMENT WITH "
        "THE PANEL:' and 'TOP 3 ACTIONS THIS WEEK:'."
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
            f"{USER_PROMPT}\n\n========= ROUND 1 — OTHER SEVEN REVIEWS =========\n"
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
        raise SystemExit("No LLM provider configured.")
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--round", type=int, choices=[1, 2], default=2)
    args = ap.parse_args()
    r1 = run_round_one()
    if args.round == 2:
        run_round_two(r1)


if __name__ == "__main__":
    main()
