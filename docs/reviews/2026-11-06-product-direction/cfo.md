---
title: CFO review, product direction 2026-11-06
created: 2026-11-06
updated: 2026-11-06
tags: [review, finance, unit-economics, product-direction]
status: draft
source: docs/reviews/2026-11-06-product-direction/BRIEF.md
---

**One line:** The full direction costs 60 to 111 founder-weeks, more than two years of a solo founder's build time, and it moves no number on the readiness scorecard. Build zero connectors now. Add usage-structure and unit-cost scoring to the CSV path only when a named usage-based prospect asks for it, because that is the only part that grows the dollars a pilot can recover.

Every number below is **assumed** unless marked verified. With zero customers, ACV, NRR, CAC and win rate are hypotheses, not inputs.

## 1. Findings

**Baseline unit economics (assumed).** I use $45K ACV, the midpoint of $30K to $60K. Year-one COGS per account: infra plus LLM $1.5K. The LLM narrates only: about 1,000 calls a month at 5K tokens in and 1K out, priced at $3 and $15 per million, is about $30 a month. Onboarding is 25 hours and support is 25 hours, both at an imputed $150 an hour, so $4K each. Total COGS $9.5K, **GM 79%**. CAC for the first logos is 120 founder hours ($18K) plus $5K in tools and travel, so $23K. Payback = 23 / (45 x 0.79 / 12) = **7.8 months**. At a $30K ACV, GM falls to 68% and payback rises to **13.5 months**. Inference is not the margin risk. Services and integration maintenance are.

**Effect of each direction on the unit economics:**

| Direction | ACV effect | GM effect (year 1, $45K) | Time-to-value | CAC payback |
|---|---|---|---|---|
| Platform-agnostic intake (14 connectors) | Neutral at first. Turns a diagnostic sale into a live workflow, which helps GRR | Maintenance of 80 founder-days a year ($96K) spread over 5 customers is $19K each, so **GM 37%**. Over 15 customers, 65% | Customer security review of a third-party app that reads billing data adds 2 to 6 weeks. CSV takes days | 18 months at 5 customers |
| Guidance wherever the rep works | Neutral. Protects GRR (an ignored tool churns quietly, see the panel review) | Browser overlay breaks when host pages change, a recurring cost. Slack is cheap | Better adoption after go-live, no faster first value | Neutral |
| Pillars 2 to 4 | **This is the 2 to 3x expansion multiplier**, the financial model itself (2026-09-11 note, Fix 3) | Neutral, but at a few hundred deals most models return "insufficient data" | None for the wedge | Improves only through NRR, which cannot be measured with no customers |
| Usage-native (commit, ramp, overage) | Grows what the product can recover. Supports the positioning | Neutral if it runs on CSV or a billing export | Days | Improves, because a pilot is more likely to pay for itself |
| 3a. AI-native UBP plus unit cost per usage unit | Same as above. A cost floor per deal makes the CFO pitch sharper | Neutral if the customer supplies one cost number per unit | Days | Improves |
| 3b. BOM, landed cost, tax margin | Different buyer (Phase 3, physical goods) | Cost-data onboarding of 60 to 120 hours ($9K to $18K) takes GM to **39 to 59%**, the 60% drag from the panel review | 4 to 8 weeks of ERP data work | 13 months or more |
| 3c. Per-customer value-based pricing (EVC) | Possible premium SKU later | Heavy services: someone has to interview each customer about value drivers | Weeks | Gets worse |

**Does the product price itself in quarter one?** Assume new and expansion bookings equal 30% of ARR. A $30M ARR company books $2.25M a quarter, so one point of price realization is worth $22.5K. That covers a $15K pilot 1.5 times. A $15M ARR company books $1.125M a quarter, so one point is $11.25K. That does not cover the $15K pilot: it needs **1.33 points**. On a usage-based company, discounts on committed ACV are only part of the leakage. Overage waivers and soft commits are the rest. Usage-native scoring makes the quarter-one ROI case possible for the lower half of the ICP. No other direction does that.

**Tier A does not widen.** `vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md` already defines Tier A as "diagnostic-addressable, **any CRM**." Its gates are 500+ closed outcomes, data readiness, a policy owner, a champion and a CFO buyer. Which CRM a company uses is not one of the gates. So connectors add **zero** accounts to the 350 to 480. What they do is move accounts from Tier A to live-workflow status, the Tier B equivalent. Salesforce is about 40% of the pool, which leaves roughly 210 to 290 non-Salesforce accounts spread over 14 platforms, about 15 to 20 per connector before overlap. Win 10% of them over three years and each connector earns 1.5 to 2 customers for 1.5 to 3 founder-weeks of build plus maintenance forever. The result is higher integration cost per account and an unchanged account count. The founder's claim that most deals happen outside Salesforce and HubSpot partly fits the 60% non-Salesforce figure, but nobody has checked the HubSpot share or the billing and CPQ shares.

## 2. What would have to change

- **Integration cost per account becomes a gated metric.** A connector gets built only after two paying or LOI-signed accounts are named on that platform.
- **Implementation priced separately.** Charge $5K to $10K on any non-CSV or cost-data onboarding, or automate it away. Keep the $15K pilot CSV-only so pilot margin does not go negative. Pilot today: $15K minus $4K onboarding, $6K of readout work and $1.5K infra leaves **23% GM**. Add BOM onboarding and it is **negative**.
- **The margin rule survives.** CRM numbers are still never called margin (vault `Decisions/2026-08-08-crm-honesty-and-ubp-math.md`). Contribution margin appears only when the customer supplies cost per unit, and the output labels it that way.
- **A per-direction ledger** in the plan, in founder-weeks and cash:

| Direction | Founder-weeks | Third-party cash, year 1 (assumed, unverified) |
|---|---|---|
| 14 connectors | 21 to 42, plus 4 to 6 a year to maintain | $5K to $15K. Stripe test mode is free. Metronome, Orb, Maxio and DealHub sandboxes are partner-gated, so the cost is time. PandaDoc and Proposify APIs need paid tiers. Marketplace listings push toward SOC 2: $10K to $25K a year for Vanta or Drata plus a $10K to $20K audit |
| Rep surfaces (Slack, email, overlay, quote screen) | 9 to 15 | Under $1K |
| Pillars 2 to 4 | 18 to 30 | Under $2K for compute |
| Usage-native | 4 to 8 | $0 |
| 3a unit cost / 3b BOM and tax / 3c EVC | 1 to 2 / 6 to 10 plus ERP connectors / 4 to 8 | 3b: NetSuite or SAP sandboxes, probably $5K or more plus tax-liability legal review |
| **Total** | **60 to 111** | **$30K to $70K including SOC 2** |

## 3. Risks and tradeoffs: the board story

**Founder capacity.** The fundraise plan (`vault/GTM/2026-11-06-fundraise-plan-pricekeel.md`) gives the next 16 weeks to 15 interviews, two $15K proposals and accelerator applications. Even if half of two quarters went to building, that is 13 founder-weeks. The full direction would take **4.6 to 8.5 such half-years**.

**Two quarters of breadth (to April 2027):** ARR $0, customers 0, and NRR, GRR, CAC payback and price realization all undefined. Connectors shipped: perhaps 4 to 6. Burn continues and integration maintenance has started. Scorecard: traction 1, PMF 1, unit economics 1. The February gate (a signed pilot or LOI) is missed, so the sprint is skipped. A board would read the connectors as cost with no demand behind them.

**Two quarters of depth on one pilot:** $15K booked, plus observed facts: time to first readout, discount leakage %, price realization, recovered dollars against the fee, and a conversion yes or no at an observed ACV. Traction 1 to 2 or 3, unit economics 1 to 2, PMF 1 to 2. The SOM re-derivation runs on a real ACV. If the pilot fails, you learn why in 90 days, not after nine months of building.

**What the round would have to fund.** Breadth in 12 months means 1.4 to 2.5 engineers ($225K loaded each, assumed Bay Area), SOC 2, third-party fees and founder pay: about $600K to $650K a year, so **$0.9M to $1.3M** for 18 to 24 months of runway. The plan's angel planning assumption is $500K to $750K, which does not cover it. Depth costs the founder plus a part-time contractor, about $250K to $400K a year, so $500K to $750K buys 18 to 24 months. Only depth fits the round the company can plausibly raise.

**Other risks.** 3b pulls a SaaS wedge into Phase 3 before the wedge has paid, against the gate in `vault/Competitive/2026-08-09-phase3-distribution-manufacturing-sizing.md`, and tax treatment carries advice liability. Pillars 2 to 4 built before any customer data will mostly return "insufficient data" at a few hundred deals per company. The decision in `vault/Decisions/2026-08-01-progress-reset.md` still stands: no discretionary feature work until the proof milestone, unless prospects document a blocker.

## 4. Recommended first increment

**Usage-structure and unit-cost scoring on the existing CSV path. About 8 to 10 days. Built only when one named usage-based prospect agrees to share a billing export.**

- Score commit, ramp and overage terms (today these are captured but not scored, per BRIEF): realized versus list per unit, waived overage, and commit shortfall. About 5 to 7 days.
- An optional customer-supplied cost per usage unit, returning a per-deal contribution floor labeled as customer-supplied. This covers the AI-native, deflating-cost ask (3a) without touching BOM. About 2 days.
- A mapping template for one billing export (a Stripe CSV export, not an API connector). About 1 day.

Validation test: in the design partner's readout, does recovered dollars per quarter exceed the $15K fee, and by how much more than discount-only scoring? If it does not, the ROI story fails and no amount of breadth fixes that.

Do this first, at about 1 day: add three questions to the interview script. Where is the deal priced and approved (system name)? Is usage data exportable? Do you know cost per unit? After 15 interviews this turns the platform-agnostic claim from assumption into a count.

## 5. Open questions for the founder

1. Cash on hand and monthly burn. This decides whether any of the breadth plan is fundable at all.
2. Will you charge implementation separately ($5K to $10K) for non-CSV and cost-data onboarding? If not, 3b stays out.
3. In the problem conversations so far, which systems did each prospect actually price deals in? Name the systems. If none names the same non-Salesforce platform twice, no connector gets built.
4. Is margin guidance on physical goods (3b) an investor-story ask or a buyer ask? If no ICP prospect has raised it, it stays gated to Phase 3.
