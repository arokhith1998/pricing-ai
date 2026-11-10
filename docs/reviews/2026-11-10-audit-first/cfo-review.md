---
title: CFO review, audit-first economics and the $2,500 a month anchor
created: 2026-11-10
updated: 2026-11-10
tags: [review, cfo, pricing, audit-first, unit-economics, market-sizing]
status: draft
source: "gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md; vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md; docs/reviews/2026-11-06-product-direction/cfo.md"
---

# CFO review: audit-first economics and the subscription anchor

Verified: zero customers, no observed ACV, churn or NRR. (A) marks an assumption. Founder time is imputed at $150 an hour (A), as in the 2026-11-06 CFO review.

## 1. The paid audit as a product

No runbook is in the repo yet. Hours by phase:

| Phase | Steady state h (A) | First audit h (A, 1.5x) |
|---|---|---|
| Sell and scope | 6 | 6 |
| Intake | 4 | 6 |
| Data readiness (Stripe joined to model and cloud cost exports) | 10 | 15 |
| Per-customer margin analysis | 14 | 21 |
| Packaging review | 10 | 15 |
| Readout | 6 | 9 |
| **Total** | **50** | **72** |

| Fee | Rate at 50 h | Rate at 72 h | Against $150 imputed |
|---|---|---|---|
| $2,500 | $50 | $35 | Loses $5,000 to $8,300 |
| $7,500 | $150 | $104 | Breaks even at steady state |
| $15,000 | $300 | $208 | Matches the $15K pilot hypothesis |

**Opportunity cost.** An interview costs about 3 hours all-in (A), so one audit is 17 to 24 interviews, or 1.25 to 1.8 founder-weeks of product work. A $2,500 audit is a discovery call the founder pays $5,000 to run.

**Automation break-even.** Assume (A) automation cuts delivery from 44 to 14 hours (30 h, $4,500 saved per audit) and costs 160 to 240 hours to build.

| Build | Saved per audit | Break-even |
|---|---|---|
| 160 h | 30 h | 6 audits |
| 240 h | 30 h | 8 audits |

**Use 8.** Do not build until 3 paid audits have run by hand on the same steps and 8 more are visible in the next 12 months.

## 2. The $2,500 a month anchor

ACV = $2,500 x 12 = **$30,000**: the bottom of the $30K to $60K wedge band and the top of the page's "low five figures" ($10K to $30K per the 2026-05-29 panel). Not a price rise. The buyer changes: $30K is 0.075% of revenue at a $40M ARR company and 1% to 3% at a $1M to $3M ARR seed AI company (A), a cash-constrained buyer by definition.

**Year-one gross margin** on the 2026-11-06 cost shape: infra plus LLM $1.5K a year (LLM narrates only), cost-data onboarding 30 h (A), manual monthly readout (A).

| Case | COGS | GM |
|---|---|---|
| Onboarding bundled, 3 h a month | $1.5K + $4.5K + $5.4K = $11.4K | **62%** |
| Onboarding bundled, 6 h a month | $1.5K + $4.5K + $10.8K = $16.8K | **44%** |
| Paid audit doubles as onboarding | $1.5K + $5.4K = $6.9K | **77%** |

Inference is not the drag. Founder service hours are.

**CAC payback** = CAC / (ACV x GM / 12): $1,550 a month at 62%, $1,925 at 77%.

| CAC (A) | Basis | At 62% | At 77% |
|---|---|---|---|
| $8K | 40 founder h + $2K | 5.2 mo | 4.2 mo |
| $15K | 80 founder h + $3K | 9.7 mo | 7.8 mo |
| $30K | first sales hire | 19.4 mo | 15.6 mo |

**Churn: 35% a year (A)** against 15% (A) for the $10M to $100M ICP. Seed churn is structurally worse: many seed companies never raise a Series A, survivors pivot pricing or ICP, the founder buyer cuts tools when runway tightens, and a margin fix is partly one-shot ("solve and leave"). A flat fee has no expansion lever, so NRR equals GRR, about 65%.

LTV = ACV x 77% / churn.

| CAC | LTV/CAC, 35% churn (LTV $66K) | 50% churn (LTV $46K) | Mid-market: $45K, 79%, 15% (LTV $237K) |
|---|---|---|---|
| $8K | 8.3x | 5.8x | 29.6x |
| $15K | 4.4x | 3.1x | 15.8x |
| $30K | 2.2x | 1.5x | 7.9x |

**Milestone.** Assume (A) seed needs $1M ARR, built over 18 months with linear signups (average tenure 0.75 years).

| | Live for $1M | Retention | Gross signups |
|---|---|---|---|
| $30K, 35% churn | 34 | 0.65^0.75 = 0.72 | **47** |
| $45K, 15% churn | 23 | 0.85^0.75 = 0.89 | **26** |

47 signups in 18 months exceeds the whole five-year SOM of 33 to 50 accounts. The anchor needs about 1.8x the logos.

**Quarter-one self-pricing.** A $2M ARR customer (A) books $500K a quarter. The $7,500 quarterly fee needs 1.5 points of margin recovered. Plausible if margins are truly negative, but migrating monthly-billed customers eats most of the quarter.

## 3. Share-of-lift

| Element | Requirement |
|---|---|
| Measure | Baseline: trailing 3-month GM percent per plan, frozen at signing (Stripe revenue minus provider invoices). Lift = actual gross profit minus baseline GM percent x actual revenue, so growth is not credited |
| Confounds | Restate COGS at baseline token prices, or vendor price cuts get credited to us |
| Attribute | Holdout or grandfathered cohort, difference in differences. No holdout, no share |
| Audit | Customer's controller computes on our worksheet; audit-rights clause; named independent accountant for disputes |
| Recognise | ASC 606 variable consideration, after quarter close and customer sign-off. Not ARR |
| Floor and cap | Floor $1,500 a month, non-refundable. 10% of verified lift for 12 months. Year-one total capped at $60K |

**Why seed buyers will not sign.** It is an open claim on the margin they must show investors; the bill is unforecastable; a founder or fractional CFO cannot run the audit; baselines move 3x a year, so disputes are near certain; legal cost exceeds the fee; and founders resent paying a share of a price change they made. For us it is lumpy and absent from ARR. Offer it only as a capped kicker above the floor.

## 4. Market honesty

2026-09-26 SOM: 33 to 50 accounts, $1.5M to $2.3M five-year wedge ARR. Sheet ICP pool, all inputs (A):

| Step | Factor | Accounts |
|---|---|---|
| US seed to Series A AI companies | | 4,000 to 7,000 |
| Real inference COGS | 50% | 2,000 to 3,500 |
| Negative GM | 20% to 35% | 400 to 1,225 |
| Changing pricing now | 50% | 200 to 610 |
| 30+ paying customers, cost export | 40% | **80 to 245** |

The pool turns over. About a third (about 55) is new each year; win 10%, so 5 to 6 logos a year; steady state at 35% churn is about 16 live. At $24K ACV (A) that is about $0.4M ARR.

**Verdict: the SOM shrinks roughly 3x in ARR (range 2x to 5x)**, driven by ACV and churn more than account count. Upside: graduates past $10M ARR become core ICP. Unproven.

**What would change it:** share of interviewees stating a negative GM with a number; share producing a cost export within a week; two audits paid at $7,500 or more; 12-month retention of the first cohort; a census of US AI companies with published usage pricing.

## 5. The 30-day checklist

| Item | Founder h (A) | Cash (A) |
|---|---|---|
| 10 to 15 interviews plus outreach | 45 to 60 | $0 to $100 |
| 2 to 3 paid audits, first runs | 144 to 216 | $0 to $100 |
| Clickable prototype | 12 to 20 | $0 to $50 |
| Lead-magnet calculator | 26 to 34 | $0 |
| **Total** | **227 to 330** | **$0 to $250** |

A founder month is about 200 hours (A): this is 1.1 to 1.7 months, $34K to $50K imputed. It does not fit. Make the prototype the audit output template, and defer the calculator until one audit is done, since it encodes the audit method. Re-check the Render API before wiring lead capture.

**Two metrics from day one:**

1. **Paid-audit conversion** = paid audits signed / qualified interviews (AI company, usage or hybrid pricing, 30+ paying customers, obtainable cost export). Real rows only in `docs/ops/funnel-tracker.csv`, per the 2026-08-01 progress reset.
2. **Founder hours per audit by phase**, against the section 1 rows; it drives the 8-audit break-even. Proposed home: `docs/ops/audit-time-log.csv` (not created, founder to approve).

At day 90 add recovered margin / fee per audit. Below 1.0, the ROI story fails.

## Recommendations

1. Price the audit at $7,500 minimum, credited against the first subscription quarter, so it funds onboarding and holds subscription margin near 77%.
2. Hold $2,500 a month as the seed AI floor with share-of-lift only as a capped kicker, and keep the $30K to $60K mid-market ICP as the sizing basis until audits produce observed ACV and retention.
3. Build the automated audit only after 3 hand-run paid audits on stable steps and 8 more in visible pipeline.
