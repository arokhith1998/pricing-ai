---
title: Llama Ventures rehearsal script — ready-to-send answers
created: 2026-09-11
updated: 2026-09-11
type: gtm
tags: [gtm, fundraising, investor, llama-ventures, pitch, rehearsal]
status: draft
related: ["[[pitch-base]]", "[[traction-update]]"]
confidence: high
ai-first: true
---

## For future Claude

Ready-to-send answers for the Llama Ventures `llama pitch` intake session. Every
answer is pre-checked against the claim boundary in [[pitch-base]] and the traction
facts in [[traction-update]]. The intake is rate-limited by email and IP, so the
session is rehearsed here before a single real message is sent.

Answers are written to be spoken as-is. They are short on purpose: the intake agent
scores signal density, and a one-sentence answer with a real number beats a
paragraph of positioning.

---

# The commands

```bash
npx -y -p @llamaventures/cli llama pitch start --name "Adhithya Bhaskar" --email "adhithya@pricekeel.com"
```

Then one `say` per answer, `upload` for the deck, `status` to check state, and
`finalize` only when the founder approves.

```bash
npx -y -p @llamaventures/cli llama pitch say '<answer>'
npx -y -p @llamaventures/cli llama pitch upload ./decks/Pricekeel-Investor-Deck.pdf
npx -y -p @llamaventures/cli llama pitch status
npx -y -p @llamaventures/cli llama pitch finalize
```

**Gate before `upload`:** the deck was last touched before the 2026-08-09 evidence
boundary was written. Read it against [[pitch-base]] and [[traction-update]] first.
If the deck claims more than this script does, fix the deck. Do not let an uploaded
PDF overclaim what the conversation carefully did not.

---

# 0. What the 11 Sep session changed

Four corrections from [[verdict-2026-09-11]], to apply before the next intake.

1. **Lead with the wedge-reselection story.** It was the only thing scored green
   on founder-market fit and it did not appear until message five. It belongs in
   the opener: the retrospective diagnostic was built, worked, and was unsellable
   because nothing in the buyer's week depended on it, so the wedge was reselected
   against four criteria (weekly cadence, an existing ritual and owner, data
   already in the CRM, useful to one customer with no network).
2. **Never concede the domain, only the operating experience.** One sentence, both
   halves together. See section 8.
3. **Competitive positioning and moat get their own short message.** Buried in a
   long multi-topic message, they were scored as never discussed.
4. **Send the deck early**, not at the end. Product signal came back blank because
   the artifact never arrived.

# 1. Opening message

> Pricekeel is the decision system of record for pricing. V1 prices every discount
> exception in Salesforce before approval: it reads the live Opportunity,
> recommends an explainable guardrail built from that company's own closed won and
> lost history, records the human decision with evidence Finance can audit, and
> reconciles the outcome when the deal closes.
>
> The buyer is a CFO or Head of Pricing at a $20M to $100M ARR B2B SaaS company on
> usage-based or hybrid pricing. Today they approve discount exceptions blind:
> no defensible reference price, discipline living in spreadsheets, and points of
> price realization leaking deal by deal. They cannot defend a discount in
> committee with math.
>
> Where we are, stated plainly: the product is built, live at pricekeel.com, and
> the Salesforce package passed live-org acceptance in a real org. Feasibility risk
> is retired. We have zero paying customers and two design-partner conversations at
> the intro-call stage. The risk we are raising to retire is demand, not
> feasibility. Raising a $500K to $1M pre-seed.

# 2. Product, and what "built" actually means

> Built and verifiable, not a prototype. pricekeel.com is a working product;
> `/sample` runs the real engine on a synthetic 2,000-deal book. The Salesforce
> External Client App passed live-org acceptance in a dedicated Developer Edition
> org: production OAuth consent and callback, expected org identity, encrypted
> access and refresh token storage, Opportunity metadata discovery, mapping
> persistence, and bounded sync. That org returned 18 closed and 13 open
> Opportunities, and the 30-usable-outcome guardrail correctly refused to produce
> guidance on a book that thin. The product declining to answer is the feature.
>
> 195 Python tests plus TypeScript connector tests, CI green on main and gating
> every push and pull request.
>
> Two honesty mechanisms are worth more than any feature. First, every verdict
> carries a method and evidence_source label, and the deal desk UI states which
> engine produced the number, so an approver is never shown demo-grade math
> implicitly. Second, if no pre-discount list field is mapped and the book
> collapses to a near-zero discount, onboarding blocks with a specific remedy
> instead of reporting a confident zero. We also never call a CRM proxy margin.
> That boundary is enforced in the schema, not in a doc.

# 3. Why now

> The usage-data layer is being locked inside payments and CRM platforms, and the
> decision layer on top of it is still unclaimed. In roughly seven months: Stripe
> acquired Metronome for about $1B, completed January 2026. Thoma Bravo completed
> a roughly $1.4B acquisition of PROS in December 2025. Adyen agreed to acquire Orb
> for about $335M in June 2026. Salesforce agreed to acquire m3ter on June 8 2026,
> folding usage-based billing into Agentforce Revenue Management.
>
> I will state the double-edge before you ask. Salesforce buying m3ter is my
> strongest tailwind, because it validates usage-based pricing on Salesforce as the
> battlefield and pulls usage data into the exact CRM we already read. It is also
> my sharpest platform risk, because Revenue Cloud already ships discount matrices,
> approvals, and price waterfall. My read on the window is 12 to 18 months from
> mid-2026 to establish the wedge and start accumulating the corpus.

# 4. Defensibility (concede first)

> The copyable part first, because pretending otherwise costs me credibility. The
> scorecard, the "hold at 16 percent" recommendation, and the leakage dashboard are
> all copyable. Revenue Cloud already ships discount matrices and approval routing.
> Metronome, Orb, and m3ter own the usage substrate and are one release from a
> recommended-discount panel. If my pitch is that my UI is nicer, I lose.
>
> Three things are structural. One, neutrality: a billing platform that benchmarks
> your prices is conflicted, because it profits from higher usage and higher prices,
> and it can only see its own billed base. A CRM benchmarks nothing. A neutral third
> party can benchmark decisions across billing systems and CRMs. That is the
> Bloomberg argument and Stripe cannot flip it without cannibalizing its own
> incentive. Two, decision system of record by accumulation: the durable asset is
> the compounding corpus of recommendation, evidence, human decision, and reconciled
> outcome, plus the cross-customer benchmark on top. Three, explainability as the
> category: the product exists so a Head of Pricing can win a committee argument,
> which is a different muscle from billing correctness.
>
> The honest synthesis: that moat is a thesis today, not an asset, because I have
> zero customers. My defensibility over the next 12 to 18 months is speed,
> explainability, and usage-native depth. The compounding moat turns on only once N
> consenting customers exist. So the whole game is the race to accumulation, and
> the clock is the acquisition window I just described.

# 5. Market (bottoms-up, volunteer the small SAM)

> Bottoms-up only. Roughly 17,000 US SaaS companies, 15 to 20 percent in the $20M
> to $100M ARR band, roughly 48 percent on usage-based or hybrid pricing, then the
> Salesforce gate, a 500-closed-outcomes data bar, a policy owner, a champion, and
> a CFO buyer. That nets to roughly 3,000 to 3,600 qualified accounts. At a $40K to
> $60K ACV, which is a pre-pilot hypothesis, wedge SAM is roughly $120M to $215M.
>
> I will volunteer the problem: that wedge SAM is small by construction. The bridge
> to a fund-returner is four labeled assumptions, never merged with the wedge.
> Two to three times ACV from capability pillars two through six. Rising
> usage-based-pricing adoption. A widening ARR band. And the largest, a Phase 3
> port into mid-market distribution and manufacturing negotiated pricing, a
> hypothesis $350M to $850M US SAM at a $60K to $120K ACV. That port transfers the
> spine, win probability, price realization, explainability, the decision log, but
> it flips the objective to pocket margin and re-grains to the SKU line, so it is a
> second engine gated behind a paying SaaS pilot. The blended $5.5B to $6B price
> optimization and CPQ TAM is gravity, not my market.

# 6. Traction (read [[traction-update]], say exactly this)

> Two design-partner conversations in progress, intro calls only. No NDA, no data
> received, no commitment, no revenue. I am not going to dress that up.
>
> What is worth more than the stage is what the conversations already changed.
> Interest from those buyers pulled two things forward. First, CRM-agnostic
> ingestion: our column mapper already ingests a HubSpot deal export through the
> generic CSV path. To be precise, there is no native HubSpot connector yet, it is
> scoped; Salesforce is the only live connector and the only one that passed
> live-org acceptance. Second, margin recovery: the schema already carries an
> optional COGS field that anticipates a margin layer, and design-partner interest
> pulled it forward in the roadmap. The margin layer itself is scoped, not built,
> and I will not report a CRM proxy as margin.
>
> So the real signal is not the meeting count, it is that first contact with real
> buyers produced two concrete direction changes rather than validation theater.

# 7. Business model

> $30K to $60K wedge ACV, entered through a $15K paid 90-day pilot with 50 percent
> credited to the annual contract, on a 3 to 6 month cycle. Every one of those
> numbers is assumed, because zero customers means zero observed anything.
>
> The six-pillar expansion is the financial model and it is NRR-driven. The margin
> risk is named: LLM inference and onboarding are real gross-margin drag, so
> implementation is priced separately or automated, targeting blended gross margin
> above roughly 60 percent.

# 8. Team and founder-market fit (name the gaps)

> Adhithya Bhaskar, solo founder. I have the domain training and none of the
> operator scars, and I want both halves on the record in the same breath, because
> stated apart they get recorded apart.
>
> The training is an M.S. in Pricing from Simon Business School, so I reason in the
> frameworks the buyer uses to defend decisions in committee: Nagle on reference
> price and economic value, Simon-Kucher on discount governance, Campbell on the
> value metric, Poyar on usage-based benchmarks. That is why the engine maps every
> metric to a named framework and why an LLM is never allowed to produce a number
> in it.
>
> The scars I do not have: I have never run a deal desk or carried a quota, so
> every design-partner conversation is partly me buying that context. And I am
> solo, which is why feasibility got retired single-handed but demand will not. Distribution is founder-led: a LinkedIn
> credibility engine turning framework fluency into an audience of exactly the CFO
> and Head of Pricing buyer I sell to.

# 9. The ask

> Raising $500K to $1M pre-seed. It buys 12 to 18 months to retire demand risk,
> which is the only risk left that matters, and to turn the moat from thesis into
> asset.
>
> Milestones the round buys: complete the validation program of 15 problem
> interviews and 5 data-readiness reviews, convert 2 paid 90-day pilots, produce
> the first validated ACV rather than an assumed one, stand up the first
> cross-customer benchmark with consent, and build commit, ramp, and overage depth
> so the engine is usage-native rather than usage-adjacent. The use of funds is
> mostly my runway plus the first design-partner-facing hire and the data
> governance work that makes a CFO comfortable handing over a CRM export.

# 10. Risks (lead with them)

> Demand risk is the whole risk. The product is built and nobody has paid.
>
> Data access is second: whether a mid-market CFO grants CRM access to a pre-seed
> vendor is genuinely unknown, and my own guardrails make it harder, because a book
> thinner than 500 closed outcomes cannot be served at all. Platform risk is third,
> and it is Salesforce and m3ter. Cold start is fourth, and it is the reason the
> wedge is a company's own closed won and lost history rather than a market
> benchmark: customer one has to be useful with no network.
>
> One open product gap I will not hide: the approver today is operator-typed free
> text and a tenant shares one access code, so approval separation rests on a
> self-approval string check and the audit payload literally records
> actor_assertion self_asserted. Real governance evidence needs per-user identity,
> WorkOS or SSO. It is filed and it is honest, and until it ships I do not describe
> the audit trail as identity-bound.

# 11. What Pricekeel is not

> Not a CPQ. Not a billing or metering platform. Not an autonomous price setter,
> because a human decision is the thing being recorded. Not a consultancy. And not
> a retail or e-commerce price optimizer, which I rejected explicitly because shelf
> pricing has no deal to record.

# 12. If asked something not covered here

> I do not know that yet. Here is how I would find out.

Then say precisely what experiment or conversation would answer it. Never
improvise a number.

---

# Pre-send checklist

- [ ] Deck reviewed against [[pitch-base]] and [[traction-update]]; no claim in the
      PDF exceeds a claim in this script.
- [ ] [[traction-update]] still accurate on the day of the session.
- [ ] Market figures re-verified if the session is more than a quarter after
      2026-08-09.
- [ ] Founder has approved this script.
- [ ] `finalize` is run only on explicit founder approval.
