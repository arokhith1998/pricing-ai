---
title: 'Outreach personas: who we email, who we never cold-email, who we avoid'
created: 2026-06-11
updated: 2026-09-26
tags: [gtm, personas, icp, outreach, sales]
status: active
---

# Outreach personas

Four personas, in priority order, plus the anti-personas. Build the target list (120-150
contacts) against personas 1 and 2; persona 3 is reached only through referrers and
forwarded artifacts; persona 4 is taken opportunistically. Companion docs:
[[outreach-sequence]] (the touches), [[design-partner-targets]] (sourcing queries),
[[objection-inventory]] (the answers).

## The ICP every persona below sits inside

Do not re-derive this per persona. Sources:
`vault/Competitive/2026-08-01-salesforce-market-need-assessment.md` (lines 61-74) and
`vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md`.

| Filter | Current value |
|---|---|
| ARR band (screening proxy only) | **$10M to $100M**, sweet spot $20M to $60M |
| The actual gate | **500+ closed opportunities a year** (or the equivalent across a 2-3 year lookback) |
| Pricing model | Usage-based or hybrid, platform fee plus a consumption metric |
| CRM | **Salesforce-primary for the live workflow.** The CSV diagnostic is CRM-agnostic, so HubSpot accounts are diagnostic-only, never quoted the in-CRM loop |
| Data readiness | Reliable list and booked values, a documented discount policy, recurring exception volume |
| Champion | Deal Desk / RevOps / Pricing owner |
| Economic buyer | CFO, VP Finance, or VP Pricing |

Never state the ARR band without the deal-volume gate. A high-velocity $12M ARR company
with 600 closed opportunities is servable; a $30M ARR company selling twelve enterprise
deals a year is not. The band alone overstates who can be served.

Standing rules across all personas: CFO never cold. CRO only after the champion is in,
because the diagnostic names their reps. Free diagnostic requires closed-lost rows.

---

## Persona 1: The RevOps Owner (primary; email first)

**Title variants:** VP Revenue Operations · Director of Revenue Operations · Head of
RevOps · Director, GTM Operations · Deal Desk Lead / Manager · Director, Sales Operations
(where RevOps does not exist as a title).

**Firmographics:** $10-100M ARR B2B SaaS (densest at $20-60M), hybrid or usage-based
pricing, 500+ closed opportunities a year, 40-120 sales/CS heads, Series B-C,
Salesforce-primary. No dedicated pricing team: RevOps inherited discount governance and
never asked for it.

**Pains:**
- Discount approvals happen ad hoc in Slack; nothing is logged, nothing is auditable.
- Quarter-end fire drills: every Q-close week is exception-request triage.
- CFO asks "why is realization down" and no answer survives scrutiny.
- Comp plans reward bookings over price quality, and RevOps gets blamed for the result.
- A CPQ rollout is looming and nobody can state what the discount policy actually is.

**Trigger events:** new CFO arrives · board asks about NRR or gross margin · annual comp
and policy planning · a big renewal that re-priced badly · CPQ implementation being scoped.

**Watering holes:** LinkedIn RevOps voices · RevOps Co-op · Pavilion · Wizards of Ops.

**Opening hook:** "Your deal desk already knows which reps over-discount. This shows what
it costs, from one CSV, with the receipts." Lead with the rep league table and the policy
simulation (which 3 policy levers would have contained the excess, with simulated impact).

**First objection and answer:** "We can pivot-table this in Excel." Answer: you can pivot
the won deals; the win-rate-by-band analysis needs the lost deals next to the wins, which
is what separates discounts that buy wins from margin giveaways. The diagnostic is free,
so Excel confirming it costs 30 minutes. Full track in [[objection-inventory]] #1.

**Qualify on the call, not after:** how many opportunities closed last year, and is
Salesforce the system of record. Those two answers decide whether this is a Tier A
diagnostic conversation or a Tier B live-workflow one.

---

## Persona 2: The First Pricing Hire (primary; co-equal with 1)

**Title variants:** Head of Pricing · Director of Pricing & Packaging · Head of
Monetization · Director, Pricing Strategy · Principal, Pricing (often literally the only
pricing person in the building).

**Firmographics:** $30-100M ARR, usage-based or hybrid, often PLG-plus-sales-led motion.
0-2 staff, 6-18 months into the role, frequently ex-Simon-Kucher or OpenView-orbit. Note:
below roughly $30M ARR this title barely exists, so target persona 1 instead. The
deal-volume gate still applies: a $60M ARR enterprise seller with 80 deals a year is not
a fit regardless of title.

**Pains:**
- Needs a defensible quick win to justify a role the org is still skeptical of.
- No data engineering support; every analysis is a personal SQL-and-spreadsheet grind.
- CRO pushes back on every policy proposal; needs evidence that is not "my judgment."
- Wants named-methodology air cover for recommendations the sales org will hate.

**Trigger events:** just hired (90-day plan needs a deliverable) · pricing-model migration
(seats to usage) · pricing council being formed · repricing project on the H2 roadmap.

**Watering holes:** LinkedIn pricing community · Professional Pricing Society · pricing
Slack groups · PeakSpan / OpenView content orbit.

**Opening hook:** methodology-forward. "Nagle reference pricing plus Simon-Kucher discount
governance, run on your own book, free, with the caveats printed on the page. You present
it; it makes your case to the CFO."

**Handle with care:** this person will spot methodology issues, including the
global-versus-segment reference question, in the first meeting. Say our limitations first:
correlational not causal, upper bound not a refund, segment-aware references, and the
minimum-outcomes threshold below which we suppress a section rather than render it.
Saying it first buys more trust than it costs.

**First objection and answer:** "ChatGPT can do this." Answer: a chatbot gives numbers
that look right and cannot be audited; here every figure comes from a deterministic,
tested engine and the LLM only narrates. Auditability is the point of hiring you, and of
this. Full track in [[objection-inventory]] #3.

---

## Persona 3: The Operator CFO (economic buyer; NEVER cold-emailed)

**Title variants:** CFO · VP Finance · Head of Finance (fractional CFOs are a channel, not
a target).

**Firmographics:** $10-100M ARR usage-based or hybrid SaaS. This persona is the
destination of the readout, not the target of the sequence.

**Reached via:** fractional CFO networks · pricing consultants · VC platform teams · and
above all, the CFO-forwardable readout a persona 1 or 2 champion sends internally. Every
artifact we make must survive this person's forward-and-skim.

**Pains:**
- Gross margin and NRR pressure from the board with no decomposition of the price side.
- Price realization unmeasured; "what is our effective discount" has no reliable answer.
- Deal desk reads as a cost center; no audit trail on who approved what.

**Trigger events (for the referrer to spot):** board meeting prep · fundraise diligence ·
budget season · a missed gross-margin target.

**Hook (delivered by the referrer, not us):** "The diagnostic produces the business case
in their own numbers; you present it." White-label-friendly for consultants.

**First objection and answer:** "Why should I trust a vendor's leakage number?" Answer:
the readout leads with what we read from the file (row counts, exclusions, blanks), every
finding decomposes to deal-level receipts, and the headline is labeled an upper bound, not
a recovery promise. It is built to be audited, not believed.

---

## Persona 4: The Pricing-Owner CEO (opportunistic; fastest close)

**Title variants:** Founder · CEO · Co-founder/CEO (the tell: they still personally
approve discounts).

**Firmographics:** $10-20M ARR usage-based SaaS, often API-first or dev-tools, no RevOps
function yet, 5-25 sales heads. Bottom of the band, so the deal-volume gate bites hardest
here: only worth pursuing when the motion is high-velocity enough to clear 500 closed
outcomes, which in practice means self-serve-plus-sales, not enterprise. One
decision-maker and no procurement: the fastest possible first logo when it qualifies.

**Pains:**
- Knows discounting is leaking and has zero time to analyze it.
- About to lose direct control of discounting (first VP Sales hire incoming).
- Needs a clean unit-economics story for the next round.

**Trigger events:** raising a round · first VP Sales hire · board pressure on burn
multiple.

**Watering holes:** founder communities · their investors (VC platform channel) ·
LinkedIn.

**Opening hook:** speed and self-serve. "Upload one CSV at pricekeel.com/upload: processed
in memory, never stored, I never see it. If the number is boring, delete the tab."

**First objection and answer:** "Is this just a one-time scan?" Answer: the free
diagnostic is one-time and that may genuinely be all you need pre-VP-Sales; the pilot
exists for when discount authority leaves your hands and you want the monthly readout and
decision log watching it. Full track in [[objection-inventory]] #7.

---

## Anti-personas (do not target; say no politely and say why)

| Anti-persona | Why not |
|---|---|
| CRO as first contact | The diagnostic names their reps. A CRO reached cold will kill it in self-defense; they enter after the champion, with the "what we would not change" section doing the diplomacy. |
| Under ~500 closed opportunities a year | The binding gate, and it is a data gate rather than a size one. Below it, band-level win rates are noise, so the honest answer is "your dataset is too small for this to be reliable." Offer the 2-3 year lookback first; if that does not clear it, say no. Talk track in [[objection-inventory]] #9. |
| Sub-$10M ARR | Outside the band, and almost never clears the deal-volume gate. Rare exception: a very high-velocity self-serve-plus-sales book. Verify the count before spending a touch. |
| Seat-only enterprise over $100M ARR | No usage line means no leakage story of our shape, and at that scale they should evaluate Pricefx or Vendavo. Telling them so costs us nothing and builds credibility. |
| Non-Salesforce for the live workflow | Not a disqualifier for the diagnostic, which is CRM-agnostic from CSV. It is a disqualifier for the in-CRM loop and therefore for a Tier B pilot today. Log the CRM; do not promise the workflow. Talk track in [[objection-inventory]] #10. |
| Retail / e-commerce | Different pricing physics entirely (per the 2026-05-29 scope decision). Out of scope, full stop. |

## Related

[[outreach-sequence]] · [[design-partner-targets]] · [[ideal-first-design-partner]] ·
[[objection-inventory]] · [[readout-close-script]]
