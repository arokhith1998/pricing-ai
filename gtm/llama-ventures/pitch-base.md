---
title: Llama Ventures pitch base — the canonical, evidence-bounded Pricekeel story
created: 2026-09-11
updated: 2026-09-11
type: gtm
tags: [gtm, fundraising, investor, llama-ventures, pitch, agent]
status: active
related: ["[[seed-deck-outline]]", "[[defensibility-rebuttal]]", "[[2026-08-09-metering-landgrab-why-now]]", "[[2026-06-10-panel-review-tam-sam-som]]", "[[2026-08-01-progress-reset]]"]
confidence: high
sources:
  - "Vault synthesis 2026-09-11: seed-deck-outline, defensibility-rebuttal, metering-landgrab-why-now, phase3-distribution sizing, progress-reset, crm-honesty decision"
  - "Llama Ventures CLI @llamaventures/cli v2.5.0, `llama pitch` external founder intake"
ai-first: true
---

## For future Claude

This is the single source of truth the `llama-pitch` agent speaks from when it
talks to the Llama Ventures intake agent. It is deliberately written as answers,
not as a deck. Every claim carries a tier: VERIFIED, HYPOTHESIS, or UNKNOWN. The
agent may never promote a claim up a tier. If the intake agent asks something not
covered here, the answer is "I do not know yet, and here is how I would find out."

The honesty posture is not modesty, it is strategy. Llama's intake returns a
structured 12-dimension verdict. Overclaiming traction is the fastest way to lose
the dimensions that actually score well (product, founder-market fit, why-now).

---

# 0. The claim boundary (read this before every answer)

**VERIFIED, provable today**
- The product is built, live, and installable. `pricekeel.com` is a working
  product, not a landing page. `/sample` runs the real engine on a synthetic
  2,000-deal book.
- A Salesforce External Client App exists and passed live-org acceptance in a
  dedicated Developer Edition org: production OAuth consent and callback, expected
  org identity, encrypted access/refresh token storage, Opportunity metadata
  discovery, mapping persistence, and bounded sync. The org returned 18 closed and
  13 open Opportunities, and the 30-usable-outcome guardrail correctly refused to
  produce guidance on a book that thin.
- Engineering rigor: 195 Python tests plus TypeScript connector tests, CI green on
  `main` and gating every push and pull request, PRs #44 through #47 merged and
  deployed to production.
- The engine labels its own evidence. Every verdict carries a `method` and
  `evidence_source`, and the deal-desk UI states which engine produced the number,
  so an approver is never shown demo-grade math implicitly.
- The engine refuses to lie by omission. If no pre-discount list field is mapped
  and the book collapses to a near-zero discount, onboarding blocks with a remedy
  instead of reporting a confident zero.
- A CRM proxy is never called margin. That boundary is enforced in the schema.

**HYPOTHESIS, labeled as such every time**
- ACV of $30K to $60K for the wedge. Pre-pilot, no customer has paid this.
- The $15K paid pilot with 50% credited to the annual contract.
- Wedge SAM of $120M to $215M US.
- The Phase 3 distribution and manufacturing adjacency at $350M to $850M US SAM.
- NRR, LTV/CAC, CAC payback, and every expansion number. Zero customers means
  zero observed retention.

**UNKNOWN, say so plainly**
- Real willingness to pay. No one has paid Pricekeel anything.
- Whether a mid-market CFO will grant CRM access to a pre-seed company.
- Whether cross-customer benchmarking consent is obtainable at scale. This is the
  moat and it is also the hardest data-governance sell.

**Never do**
- Never present the synthetic funnel rows as traction. They live in
  `docs/ops/funnel-tracker-example.csv` with `EXAMPLE-` prefixes for exactly this
  reason, and the operating tracker is header-only because that is the honest count.
- Never say "customers" when the truth is "conversations."
- Never quote a benchmark drawn from the synthetic book as if it came from a market.

---

# 1. The one-liner

Pricekeel is the decision system of record for pricing. V1 prices every discount
exception in Salesforce before approval: it reads the live Opportunity, recommends
an explainable guardrail built from the company's own closed won and lost history,
records the human decision with evidence Finance can audit, and reconciles the
outcome when the deal closes.

Not a CRM. Not a CPQ. Not an autonomous price setter. The category noun is the
decision record.

# 2. The problem

Mid-market B2B SaaS companies between $20M and $100M ARR approve discount
exceptions blind. There is no defensible reference price, pricing discipline lives
in spreadsheets and tribal memory, and points of price realization leak deal by
deal. The buyer, a CFO or Head of Pricing, cannot defend a discount in a committee
with math. They can defend it with a story, and the story loses to the rep who
wants the deal closed this quarter.

The pain is not "we discount too much." The pain is "I cannot prove what the right
discount was, before or after."

# 3. Why now

The usage-data layer is being locked inside payments and CRM platforms, and the
decision layer on top of it is still unclaimed. In a single seven-month window:

- Stripe acquired Metronome, roughly $1B, announced Dec 2025, completed late
  Jan 2026.
- Thoma Bravo completed its roughly $1.4B acquisition of PROS Holdings on
  Dec 9 2025, combining the B2B pricing business with Conga.
- Adyen agreed to acquire Orb, roughly $335M, June 2026.
- Salesforce agreed to acquire m3ter on June 8 2026, folding usage-based billing
  into Agentforce Revenue Management.

(All figures verified 2026-08-09 and stale-fast. Re-verify before quoting.)

The window to establish the decision-integrity wedge and start accumulating the
benchmark corpus is roughly 12 to 18 months from mid-2026, before a data-owning
platform ships a worse-but-free version.

**State the double-edge yourself, do not wait to be asked.** Salesforce buying
m3ter is both the strongest tailwind (it validates usage-based pricing on
Salesforce as the battlefield and pulls usage data into the exact CRM Pricekeel
already reads) and the sharpest platform risk (Revenue Cloud already ships
discount matrices, approvals, and price waterfall).

# 4. The wedge, and why it is narrow on purpose

Decision integrity for Salesforce discount exceptions, for usage-based and hybrid
B2B SaaS. Four verbs: read the live Opportunity, recommend an explainable
guardrail from the org's own history, record the human decision with auditable
evidence, reconcile the outcome.

Narrow because the incumbents (Vendavo, PROS, Zilliant, Pricefx) live in
manufacturing and distribution with twenty-year head starts and $500M+ raised, and
they ignore mid-market SaaS usage-based pricing. The wedge exists precisely in
their blind spot. Widening now would trade the one market where Pricekeel is
uniquely positioned for the one where it is weakest.

# 5. Defensibility (the hardest question, answered without flinching)

**Concede first, it earns the rest.** The scorecard, the "hold at 16%"
recommendation, and the leakage dashboard are copyable. Salesforce Revenue Cloud
already ships discount matrices and approval routing. Metronome, Orb, and m3ter own
the usage substrate and are one release from a recommended-discount panel. If the
pitch is "our UI is nicer," it loses.

**The real moat is three structural things:**

1. **Neutrality.** A billing platform that benchmarks your prices is conflicted: it
   profits from higher usage and higher prices, and its benchmark can only see its
   own billed base. A CRM benchmarks nothing. A neutral third party can benchmark
   decisions across billing systems and CRMs. This is the Bloomberg argument, and
   it is structural, not a toggle Stripe can flip without cannibalizing itself.
2. **Decision system of record by accumulation.** The durable asset is the
   compounding corpus of recommendation, evidence, human decision, and reconciled
   outcome, plus the cross-customer benchmark built on it. A billing player is
   structurally disinclined to build it (different buyer, different muscle) and a
   CRM is structurally uninterested (workflow and config DNA, not
   committee-defensible pricing science).
3. **Explainability as the category.** The product exists so a Head of Pricing can
   defend a decision in a committee. Billing platforms optimize for billing
   correctness, which is a different muscle from a defensible narrative.

**The honest synthesis, say it out loud:** that moat is a thesis today, not an
asset, because there are zero paying customers. Defensibility in the next 12 to 18
months is speed, explainability, and usage-native depth. The compounding moat turns
on only once N consenting customers exist. So the whole game is the race to
accumulation, and the clock is the acquisition window above.

# 6. Market (bottoms-up only, never a share of a top-down TAM)

The ICP funnel: roughly 17,000 US SaaS companies, 15 to 20 percent in the $20M to
$100M ARR band, roughly 48 percent on usage-based or hybrid pricing, minus the
Salesforce gate, the 500-closed-outcomes data bar, a policy owner, a champion, and
a CFO buyer. That nets to roughly 3,000 to 3,600 qualified accounts.

Wedge SAM: roughly $120M to $215M at a $40K to $60K ACV. The ACV is a
**hypothesis, pre-pilot**.

The wedge SAM is small by construction. That is intentional and should be said
before it is discovered. The bridge to a fund-returner runs on four labeled
assumptions, never merged with the wedge:
1. 2 to 3x ACV from capability pillars 2 through 6.
2. Rising usage-based pricing adoption.
3. A widening ARR band.
4. Largest: a Phase 3 port into mid-market distribution and manufacturing
   negotiated pricing, a **labeled-hypothesis** $350M to $850M US SAM ($0.8B to
   $2B global) at a higher $60K to $120K ACV.

Phase 3 is a proven-engine port, not a hand-wave, and not a plan for now. It
transfers the spine (win probability, price realization, explainability, the
decision log) but flips the objective to pocket margin and re-grains to the SKU
line, which needs true COGS and ERP connectors. Five prerequisites gate it, and
the first is a paying SaaS pilot.

Blended TAM of $5.5B to $6B (price optimization plus CPQ) is gravity only. It is
never "our market."

# 7. Business model

$30K to $60K wedge ACV. A $15K paid 90-day pilot with 50 percent credited to the
annual contract. A 3 to 6 month cycle. Every number is **assumed, zero customers**.

The six-pillar expansion is the financial model, driven by NRR. The margin risk is
named and planned for: LLM inference and onboarding drag are priced separately or
automated, to protect blended gross margin above roughly 60 percent.

# 8. Traction (the honest slide)

See `gtm/llama-ventures/traction-update.md`. That file is the only place traction
claims live, so there is exactly one thing to keep current and one thing to get
wrong. The agent reads it at session start and speaks only what is in it.

Standing rules for this section, regardless of what the update file says:
- Conversations are conversations. A pilot is a pilot only when money or a signed
  agreement exists.
- If the strongest true statement is "two design-partner conversations in
  progress, no signed agreement," that is the statement.
- Feasibility risk is retired. Demand risk is not. Say which risk the round buys
  down.

# 9. Team and founder-market fit

Adhithya Bhaskar, founder. M.S. in Pricing from Simon Business School, building a
pricing product. This is unusually coherent domain credibility: the founder reasons
in the same frameworks (Nagle on reference price and EVC, Simon-Kucher on discount
governance, Ramanujam, Bertini and Koenigsberg, Campbell on the value metric,
Poyar on usage-based benchmarks) that the buyer uses to defend decisions in
committee. The founder is the human embodiment of the explainability thesis.

The distribution plan matches: a LinkedIn credibility engine turning framework
fluency into an audience of the exact CFO and Head of Pricing buyer.

**Name the gaps without being asked:** no operator scar story from inside a
mid-market RevOps org, and a solo founder. Say how each is being closed.

# 10. The ask

To be set by the founder before the session. The structure: amount, use of funds,
and the 12 to 18 month milestones the round buys, tied explicitly to retiring
demand risk and turning the moat from thesis into asset. Concrete milestones:
N paid pilots, first validated ACV, first cross-customer benchmark, and
commit/ramp/overage depth built.

# 11. Risks, stated before they are asked

1. **Demand risk is the whole risk.** Product is built; nobody has paid. This is
   the honest headline.
2. **Data access.** Will a mid-market CFO grant CRM access to a pre-seed vendor?
   Unknown. The 30-usable-outcome guardrail and the 500-closed-outcomes data bar
   mean thin books cannot be served at all, which shrinks the qualified set.
3. **Platform risk.** Salesforce and m3ter. Answered in section 3 and 5.
4. **Cold start.** The moat requires N consenting customers. Customer 1 gets no
   benchmark, only their own history. The product is designed so a single
   customer's own book is already enough to be useful, which is why the wedge is
   the org's own closed won and lost history rather than a market benchmark.
5. **Governance gap, currently open.** The approver is operator-typed free text and
   a tenant shares one access code, so approval separation rests on a self-approval
   string check and the audit payload records `actor_assertion: self_asserted`.
   Real governance evidence needs per-user identity (WorkOS or SSO). This is a
   known, filed, honest gap. Do not describe the audit trail as identity-bound.
6. **Solo founder, pre-revenue, no institutional capital.**

# 12. What Pricekeel is not

Not a CPQ. Not a billing or metering platform. Not an autonomous pricing agent.
Not a consultancy. Not a retail or e-commerce price optimizer (shelf pricing does
not transfer, and that was explicitly rejected).

---

# Answer patterns for the intake agent

**If asked for a metric that does not exist:** "That number does not exist yet
because we have zero paying customers. Our working hypothesis is X, and here is
what would validate or kill it."

**If asked about competition:** concede the copyable feature first, then the three
structural moats, then the admission that the moat is prospective.

**If asked why this founder:** M.S. in Pricing plus a shipped, tested, live product
with a Salesforce package that passed live-org acceptance. Feasibility retired
solo. Then name the operator gap.

**If pushed on market size:** bottoms-up funnel, never a slice of the $6B TAM.
Volunteer that the wedge SAM is small by construction and that the expansion bridge
is four labeled assumptions.

**If asked for the deck:** `decks/Pricekeel-Investor-Deck.pdf` (verify it matches
this evidence boundary before uploading; if it does not, fix the deck, not the
answer).
