# Founder research sheet: Economics

Source: CFO, 2026-11-10, from docs/reviews/2026-11-10-audit-first/ (cfo-review, pricing-strategist-review, FOUNDER-DECISIONS). Verified: zero customers, zero paid audits. Founder time imputed at $150 an hour.

## 1. The audit as a product

Hours by phase (first run 1.5x on delivery):
Phase | Steady h | First run h
Sell and scope | 6 | 6
Intake | 4 | 6
Data readiness | 10 | 15
Margin analysis | 14 | 21
Packaging review | 10 | 15
Readout | 6 | 9
Total | 50 | 72

Runbook conflict: the runbook estimates 25 to 35 hours for the last four phases, against 40 here. The time log settles it after audit one.

Fee and rate: $7,500 fixed, upfront, no credit on the first two (F4). That is $150 an hour at 50 h, $104 at 72 h.

Contribution per audit: about $7,400 cash after up to $100 of tools. Net of imputed founder time: about $0 steady, minus $3,300 on a first run. The audit funds learning, not profit.

Automation break-even: automation saves 30 h ($4,500) per audit and costs up to 240 h. 240 / 30 = 8 audits. Build only after three hand-run audits on the same steps (F13) and eight more visible within 12 months.

## 2. The subscription anchor we are not publishing (F6)

Strategist tiers, fenced by revenue under management: Monitor $1,000 to $1,500 a month (sub-$10M ARR), Operate $2,500 to $4,000 a month (core band). Midpoints used.

Cost to serve: infra plus LLM $1.5K a year, readout 3 h a month ($5.4K a year), onboarding 30 h ($4.5K) unless the paid audit doubles as onboarding. Founder hours drag margin, not inference.

Tier | ACV | GM, audit onboards / bundled | Churn | Payback, CAC $8K / $15K | LTV | LTV/CAC, $8K / $15K
Monitor | $15K | 54% / 24% | 35% | 11.9 / 22.2 mo | $23K | 2.9x / 1.5x
Operate | $39K | 82% / 71% | 15% | 3.0 / 5.6 mo | $213K | 26.7x / 14.2x

Formulas: payback = CAC / (ACV x GM / 12); LTV = ACV x GM / churn. Flat fee, so NRR equals GRR.

Read: Monitor does not close unless the readout is automated to about 1 hour a month (GM 78%). Operate's ratios rest on an invented 15% churn; at 35% they are 11x / 6x.

Publish no tier until the first three audits show: (a) two of three paid at $7,500 undiscounted; (b) recoverable contribution margin per quarter at least the quarterly fee ($3,750 Monitor, $9,750 Operate); (c) readout at or below 3 hours; (d) one finance-signed baseline at constant input unit prices (F5). If all three buyers are seed, only Monitor is evidenced, and it fails.

## 3. Cost of the 30-day plan

Unsequenced: 227 to 330 founder hours ($34K to $50K imputed), $0 to $250 cash, against about 200 hours. Does not fit.

Sequenced per F13:
Weeks | Work | Founder h
1 to 2 | 10 to 15 interviews | 45 to 60
1 to 4 | 8 content posts | 12
2 to 4 | First paid audit | 72
2 to 4 | Review calculator (agent builds PK-107 to PK-111) | 6
Total | | 135 to 150

Fits, with 50 to 65 hours of slack, not enough for a second audit. Audits two and three run in month two; the third lands around day 75.

Cash: $0 to $250 plus the F11 legal gate (counsel, entity, insurance), unpriced and blocking the first audit. Inflow: $7,500 per audit, upfront.

## 4. Market honesty

Core ICP, AI-native inside $20M to $100M: 2026-09-26 SOM is 33 to 50 accounts, $1.5M to $2.3M five-year ARR; the AI-native slice is unsized and smaller.

Seed ICP: 80 to 245 qualified accounts, 14 to 16 live at 35% churn, about $0.4M ARR at $24K ACV. Factor: 4x to 6x less ARR (the review's 3x headline understated its own inputs).

Moves it: interviewees quoting a negative GM, cost exports within a week, audits paid at $7,500, 12-month cohort retention.

## 5. Two metrics from day one

Paid-audit conversion = paid audits signed / qualified interviews (AI-native, usage or hybrid pricing, 30+ paying customers, cost export obtainable). Recorded in docs/ops/funnel-tracker.csv, real rows only; zero today. Proposed: an audit_paid stage and audit_fee column.

Founder hours per audit by phase, logged daily against the section 1 phases. Drives the break-even of 8 and gate (c). Proposed file: docs/ops/audit-time-log.csv (audit_slug, date, phase, hours, note), not created.

## 6. Assumptions register

Number | Value | Label
Customers, paid audits | 0 | measured
Founder rate | $150/h | assumption
Audit hours, steady / first | 50 / 72 | assumption
Runbook hours, last four phases | 25 to 35 | estimate
Audit fee | $7,500 | assumption (decided F4, demand unmeasured)
Tools per audit | up to $100 | estimate
Automation saving / build | 30 h / 240 h | assumption
Break-even | 8 audits | estimate
Tier prices | $1,000 to $4,000/mo | assumption
Infra plus LLM | $1.5K/yr | estimate
Readout / onboarding | 3 h/mo / 30 h | assumption
CAC | $8K / $15K | assumption
Churn, seed / core | 35% / 15% | assumption
Founder month | 200 h | assumption
Interviews, posts, review | 45 to 60 h, 12 h, 6 h | assumption
Core SOM | 33 to 50 accounts | estimate
Seed pool, ACV | 80 to 245, $24K | assumption
Legal gate cash | unknown | not estimated
