---
title: Deck audit — Pricekeel-Investor-Deck.pdf against the evidence boundary
created: 2026-09-11
updated: 2026-09-11
type: gtm
tags: [gtm, fundraising, deck, audit, evidence-boundary, investor]
status: active
related: ["[[pitch-base]]", "[[traction-update]]", "[[seed-deck-outline]]", "[[defensibility-rebuttal]]", "[[2026-08-09-metering-landgrab-why-now]]"]
confidence: high
sources:
  - "Full text extraction of decks/Pricekeel-Investor-Deck.pdf (15 pages, built 30 May 2026), audited 2026-09-11 against repo state and vault evidence boundary"
ai-first: true
---

## For future Claude

Audit of the 30 May 2026 investor deck against the evidence boundary written in
August 2026. Verdict: do not patch, rebuild. The deck is not wrong because it was
sloppy, it is wrong because the company moved. It was an honest document in May.

Source of truth for the rebuild: [[pitch-base]], [[traction-update]],
[[seed-deck-outline]], [[defensibility-rebuttal]].

---

# Verdict

**Do not send. Do not upload to the Llama Ventures intake. Rebuild.**

Three independent reasons, any one of which is disqualifying:

1. **Wrong document type.** The ask on slide 15 is "5 to 10 design partner intros."
   It is a design-partner recruitment deck. The ask is now a $500K to $1M pre-seed.
   An investor intake agent scores the ask as its own dimension, and this deck does
   not make one.
2. **Materially stale.** Built 30 May 2026. It predates the Neon migration
   (26 Jun), the Salesforce workflow shipping (1 Aug), the progress reset (1 Aug),
   the CRM honesty decision (8 Aug), and the entire why-now and defensibility work
   (9 Aug). Several slides now state things that are simply false.
3. **Four claims breach the evidence boundary**, and one of them, the headline on
   slide 1, is the first sentence an investor reads.

---

# A. Claims that breach the evidence boundary

## A1. Slide 1, headline. "B2B SaaS companies leak 4 to 8% of ARR to discount drift."

Unsourced market statistic, stated as fact, in the most load-bearing position in
the document. No citation exists in the repo or the vault. Either attribute it to
a named, checkable source or cut it. An investor who asks "where is that from" and
gets a pause has learned something about every other number in the deck.

**Fix:** replace with the mechanism, which is defensible without a citation: buyers
cannot defend a discount in committee with math. Or cite Simon-Kucher or Nagle
directly if a real figure can be sourced.

## A2. Slide 1. "a read-out that nobody else builds."

Absolute negative claim. Unprovable and unnecessary.

**Fix:** cut. The positioning argument on the rebuilt defensibility slide does this
job properly.

## A3. Slide 13. "NO CATEGORY COMPETITOR."

This is the most dangerous slide in the deck and it directly contradicts
[[defensibility-rebuttal]], which is the vault's considered position: concede the
copyable feature first, because pretending otherwise costs credibility. The slide
also predates the entire metering land-grab. Stripe/Metronome, Thoma Bravo/PROS,
Adyen/Orb, and Salesforce/m3ter all closed or were announced after this deck was
built. Salesforce Revenue Cloud already ships discount matrices, approval routing,
and price waterfall.

**Fix:** replace with the concede-then-claim structure. Concede the scorecard and
the recommendation are copyable, then argue neutrality, accumulation, and
explainability, then admit the moat is prospective at zero customers.

## A4. Slide 13. "the customer owns an audit-grade record."

"Audit-grade" overclaims against a known, filed gap. The approver is
operator-typed free text, a tenant shares one access code, and the audit payload
records `actor_assertion: self_asserted`. Until per-user identity ships (WorkOS or
SSO), the trail is not identity-bound.

**Fix:** "an append-only decision record with the supporting math," plus the
identity gap named on the risks slide.

## A5. Slide 2. "15 to 25% lift in discount given" at quarter end.

Unsourced. If this comes from the synthetic book, it is a property of the
generator, not of the market, and must be labeled as such.

**Fix:** attribute, or restate as what the engine measures
(`quarter_end_effect(df)`) rather than as a market fact.

## A6. Slide 5. The drilldown numbers do not survive scrutiny.

$64.8M of $67.1M booked value flagged as "investigate" is 97 percent of the book.
A CFO reads that as "your tool flags everything," which is the same as flagging
nothing. The $2.3M defended versus $64.8M investigate split makes the diagnostic
look uncalibrated even though the underlying math is sound.

**Fix:** lead the drilldown with the off-policy-no-approver figure ($2.7M), which
is specific, actionable, and the lowest-friction guardrail. Show the defended
split as a proportion of deals, not as a dollar contrast that reads as absurd.

---

# B. Factual errors introduced by time

| Slide | Deck says | Truth as of 2026-09-11 |
|---|---|---|
| 11, 14 | "77 Python tests" | 195 Python tests plus TypeScript connector tests, CI green on `main` and gating every push and PR |
| 11, 12 | "Supabase, Postgres" as the data layer | Migrated to Neon on 2026-06-26, verified in production. Supabase retained only as a rollback path, pending decommission |
| 13 | "INTEGRATION-LIGHT WEDGE. CSV in, read-out out. No 6-month Salesforce integration." | The wedge **is** the Salesforce connector now. This slide argues against the current product |
| 14 | "Phase 2, 2027: Copilot and recommendation engine" | Shipped Aug 2026. The live Salesforce decision lifecycle is roughly 15 months ahead of this roadmap |
| 14 | "What is not here yet. No design partner." | Two design-partner conversations in progress, intro calls only. See [[traction-update]] |
| 12 | "CSV uploads processed in memory and deleted" | Still true for the CSV path, but incomplete: the Salesforce path persists encrypted OAuth tokens and sync metadata. The privacy slide must describe both paths or it is misleading by omission |
| 4, 5 | Sample figures | These are regenerated live from the engine by `tools/build_deck.py`, so they self-heal on rebuild. No action needed |

---

# C. What is missing, and it is most of what now scores

The deck has no slide for any of the following. Each is a dimension an investor
intake will score, and each already exists as finished work in the vault.

1. **Why now.** The metering and billing land-grab, and the 12 to 18 month window.
   This is the single strongest new argument and it is entirely absent.
   [[2026-08-09-metering-landgrab-why-now]]
2. **Market sizing.** The bottoms-up ICP funnel, roughly 3,000 to 3,600 qualified
   accounts, wedge SAM, and the labeled expansion bridge. Absent.
3. **Business model.** ACV, the paid pilot structure, the cycle, the gross-margin
   plan. Absent. The deck never says how Pricekeel makes money.
4. **The Salesforce live-org acceptance proof.** The strongest verifiable asset the
   company has, and it postdates the deck entirely.
5. **Founder-market fit.** The M.S. in Pricing is never mentioned. This is the
   deck's most under-used asset.
6. **The ask in dollars**, with use of funds and the milestones it buys.
7. **Risks, owned rather than discovered.** Slide 14 gestures at this. It needs to
   be a real slide.

---

# D. What is genuinely good and must survive the rebuild

Do not throw these away. They are the reason the deck reads as credible.

1. **Slide 6, the pipeline, and slide 9, the copilot architecture.** "Every dollar
   figure is a deterministic Python calculation. The LLM writes the prose around
   the number, never the number itself." That is the explainability thesis made
   concrete, and it is unusually strong for a pre-seed deck.
2. **Slide 7, the methodology table.** Function, what it answers, and the named
   framework behind it. This is the founder-market-fit argument rendered as a
   table, and it is better than any bio slide.
3. **Slide 8, "AUC 0.640 ... accuracy is not the moat, the explanation chain is."**
   Publishing a modest AUC and defending why it is the right target is a
   credibility move most founders will not make. Keep it verbatim.
4. **Slide 3, the four artifacts.** Concrete, specific, forwardable.
5. **Slide 5's framing note**, that showing leakage alone reads as a witch-hunt and
   the defended split gives sales a fair seat. That is real customer empathy.
6. **The honest-disclosure line on slide 7**: "excess vs reference is
   correlational ... never recoverable revenue."
7. **The house style.** Light theme, no em dashes, one idea per slide, live
   engine numbers, all enforced by `tools/build_deck.py`. Rebuild in that builder.

---

# E. Positioning change to reflect (founder direction, 2026-09-11)

The ICP is stated as $10M to $100M ARR B2B SaaS. Once a margin recovery capability
exists, the same decision machinery becomes relevant to large manufacturers and
component suppliers with thousands of SKUs, hundreds of product lines, and large
negotiated account books.

**Two flags before this goes on a slide.**

1. **Scale mismatch with the standing decision.** [[2026-08-09-distribution-manufacturing-adjacency]]
   deliberately scoped the Phase 3 opening as *mid-market* distributors on Excel,
   below the incumbents' deployment-cost floor. Large semiconductor and industrial
   accounts are the core installed base of Vendavo, PROS, and Zilliant. Naming them
   as targets invites the question "so you plan to displace Vendavo at Intel with
   zero customers," which is a losing exchange. The underlying argument is good and
   should be kept: SKU count times product lines times negotiated accounts is a
   combinatorial decision volume, and that is exactly where a decision system of
   record compounds. Present it as the expansion thesis with prerequisites, name
   the segment rather than the logos, and keep the build gate at a paying SaaS pilot.
2. **The band was never actually $20M to $100M. Resolved 2026-09-11.** The sourced
   derivation in [[2026-06-10-panel-review-tam-sam-som]] always used $10M to $100M,
   so the narrower band in the old deck, on the site and in the agent definitions
   was drift with nothing computed behind it. Restored to $10M to $100M everywhere,
   with the gate that actually binds stated alongside it: servability is deal
   volume, not ARR.

3. **The bigger error, found while fixing the band.** The market slide quoted
   roughly 3,000 to 3,600 qualified accounts and a $120M to $215M SAM immediately
   after listing the operational gates. That is the figure from *before* those
   gates. [[2026-08-09-two-tier-sizing-crm-agnostic-and-india]] puts the post-funnel
   US wedge at ~350 to 480 accounts and $11M to $29M (any CRM), or ~130 to 190
   accounts and $4M to $11M Salesforce-native, and instructs reporting the
   post-funnel number with the expansion bridge shown separately. The deck now
   does. See [[2026-09-11-arr-band-and-post-funnel-sizing]].

---

# F. Recommendation

Rebuild as a fundraising deck in `tools/build_deck.py`, reusing the house style and
the live engine numbers. Target 14 slides. Keep section D verbatim where possible,
cut A1 through A5, correct table B, and add the seven missing slides in C.

Add product evidence as imagery: annotated screenshots of the real product, and a
short screen recording of a sample run hosted behind a link rather than embedded,
because an embedded video breaks the golden rule that a deck must read standalone
as a PDF.
