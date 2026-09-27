---
title: 'Pitch-base insert: how we report pilot revenue'
created: 2026-09-26
updated: 2026-09-26
tags: [gtm, investor, pricing, revenue-recognition, cfo, insert]
status: draft
---

# Pitch-base insert: how we report pilot revenue

**Why this is a separate file.** The target, `gtm/llama-ventures/pitch-base.md`, does not
exist in the `main` checkout. It lives on the unmerged agent-org branch
(`feat/agent-engineering-org`, PR #62). Paste the section below into `pitch-base.md`
immediately after the pricing and commercial-structure discussion (around line 183 in the
branch version, the `$30K to $60K` ACV paragraph), then delete this file.

Origin: fifteen-agent evaluation 2026-09-26, cfo finding F5
(`docs/reviews/2026-09-26-agent-reports/eval-cfo.md:78-89`).

---

## How we report pilot revenue

We report pilots as **bookings, never as ARR.** A 90-day paid pilot is a fixed-fee,
non-recurring engagement with no renewal obligation on either side. Counting it as annual
recurring revenue would overstate the run rate by roughly four times and would not survive
the first diligence call, so we do not do it. ARR starts at the annual agreement, not at
the pilot.

**The 50% pilot credit is a deferred material right, and we book it as one.** The pilot is
$15K, with 50% credited toward the annual agreement if the customer signs inside the pilot
window. Under ASC 606 that credit is a material right: $7,500 of the $15K is a separate
performance obligation and is deferred at signature rather than recognised with the pilot
fee. Recognised pilot revenue is therefore $7,500 unless and until the credit expires
unexercised.

**What that does to year-one economics, stated plainly:**

| Line | Low end | High end |
|---|---|---|
| Pilot fee | $15.0K | $15.0K |
| Annual list | $30.0K | $60.0K |
| Gross year-one list | $45.0K | $75.0K |
| Less the 50% pilot credit | ($7.5K) | ($7.5K) |
| **Year-one cash** | **$37.5K** | **$67.5K** |
| Effective year-one discount | 16.7% | 10.0% |
| **ARR entering year two** | **$30.0K** | **$60.0K** |

So the correct three numbers to quote are: **$15K pilot bookings, $7.5K recognised pilot
revenue, $30K to $60K ARR on conversion.** The year-one cash figure sits between them and
is not either of them.

**Two caveats that travel with this table.** First, the $30K to $60K ACV band is a
**hypothesis**: Pricekeel has no signed pilot, no observed ACV and no measured NRR, so
every figure above is a plan rather than an observation. Second, the effective 10% to 17%
year-one discount is deliberate, it is what a design partner is paid for in risk terms, and
it is priced in rather than negotiated away later.

**Gross margin, while we are here.** The software COGS is near zero: LLM calls in this
product are narration and column-mapping fallback at 350 to 1,500 max tokens, so cash COGS
per customer is trivial. We target **80%+ on the software line** and price onboarding as a
separate non-recurring line rather than blending it in. The honest drag on early margin is
founder hours per prospect and a free diagnostic, not inference cost. Defending "roughly
60%" invites a diligence question the numbers do not require us to invite.

---

## Related

`vault/Decisions/2026-09-26-som-re-derived-against-tier-a-pool.md` ·
`vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md` ·
`vault/Competitive/2026-08-01-salesforce-market-need-assessment.md` (the $15K / 50%-credit
commercial hypothesis, line 84) · `gtm/objection-inventory.md` #7
