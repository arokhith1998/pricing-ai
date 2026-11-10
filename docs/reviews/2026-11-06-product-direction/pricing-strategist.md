---
title: Product direction review, pricing strategist lens
created: 2026-11-06
updated: 2026-11-06
tags: [review, product-direction, pricing-science, positioning, ubp, margin, evc]
status: draft
source: "pricing-strategist agent, against BRIEF.md and the vault frameworks"
---

**Summary:** Build usage-native contract-structure guidance now (commit, ramp, overage, unit-rate floors) because it deepens the existing wedge. Treat value-based pricing as a human-entered EVC worksheet attached to the decision record. Defer BOM, landed cost and tax to Phase 3. Margin enters only as customer-supplied contribution margin, labeled with its source.

# 1. Findings

**What the engine can express today.** `pricing/metrics.py` scores one lever: `discount_pct = 1 - booked/list` on annualized ACV. It does this through win rate by band, the bootstrapped reference discount, segment, BU and product-line references, and a per-value-metric reference (`value_metric_reference_table`, with only the enum seats, consumption, hybrid). `pricing/governance.py` `exception_verdict` scores a requested discount percent against a 0 to 40% EV grid and a single `floor_pct`. `pricing/diagnostic.py` contains no section that reads contract structure. `pricing/schema.py` already captures `committed_acv`, `overage_rate`, `ramp_year_1_acv`, `ramp_year_2_acv`, `quantity`, `platform_fee_acv`, `usage_acv` and `cogs_acv`, but those fields are referenced only in `generate.py`, `ingest.py`, `mapping.py` and `schema.py`. No metric, model or verdict consumes them. The data model is ahead of the math, which makes the cheapest increment unusually cheap.

**Ask (a), AI-native UBP with deflating unit cost.** The standing commit, ramp and overage pushback is now a live product gap rather than a roadmap line. `vault/Competitive/defensibility-rebuttal.md` already flags it: "V1 governs the discount on committed / annualized ACV only." Deflating token prices raise a value-metric problem before they raise a guidance problem. If a vendor's metric is a pass-through of tokens, which is a means rather than an end (`vault/bertini-koenigsberg-ends-game.md`), then every public token price cut resets the buyer's reference price downward (`vault/nagle-strategy-and-tactics-of-pricing.md`). Price then deflates with cost and NRR erodes, cutting against the expansion claim in `vault/poyar-usage-based-pricing.md`. So the founder's claim implies the record should capture the value metric at finer grain than a three-value enum and should flag cost-indexed metrics, such as tokens, compute or API calls priced near cost, as structural leakage risk (`vault/campbell-willingness-to-pay.md`: the value metric is the most important pricing decision).

**Ask (b), margin from BOM, landed cost and tax.** `vault/Decisions/2026-08-08-crm-honesty-and-ubp-math.md` rules that CRM numbers are never called margin. That rule is correct and stays. `vault/Competitive/2026-08-09-phase3-distribution-manufacturing-sizing.md` names the pocket-price waterfall, the margin objective and the SKU re-grain as roughly 60% of a second engine. It gates that engine on five prerequisites, starting with "SaaS wedge validated", and none of the five is met. BOM, landed cost by shipping location and tax treatment are physical-goods inputs. They are the Phase-3 engine, not an extension of the SaaS one.

**Ask (c), value per customer.** The Nagle note's own watch-out applies here: EVC inputs are "hard to estimate and easy to inflate". Nothing in the engine estimates willingness to pay per customer, and with hundreds of deals per company nothing should try.

**Positioning.** `vault/GTM/seed-deck-outline.md` uses "the decision record for B2B discounts", and its 50-character form line reads "Explainable discount guidance inside Salesforce." The platform-agnostic ask contradicts "inside Salesforce". That contradiction helps: it strengthens the neutrality moat in the defensibility rebuttal and widens Tier B toward Tier A. "Plus margin plus value-based" is what blurs the wedge. It adds two nouns that sit on PROS, Vendavo and Zilliant turf, where the Phase-3 note says explainable guidance is their headline feature rather than our gap.

# 2. What would have to change

**Commit, ramp, overage and floor guidance.** The record should show the following. Each item is deterministic and labeled `method: policy rule` until enough data exists for a modeled curve.

- **Effective committed unit rate**, `committed_acv / quantity`, and its realization against the list unit rate. This metric replaces the discount percent for consumption deals.
- **Commit coverage:** commit divided by forecast usage, where the customer supplies a forecast. With volumes swinging under physical AI, guidance should set the commit near a conservative forecast percentile and accept true-ups, not deep commits bought with discount. A discount buys commit depth or prepayment, in line with "trade, never give" (`vault/simon-kucher-discount-governance.md`).
- **Overage fence:** flag any deal whose `overage_rate` sits at or below its effective committed unit rate. That invites under-commitment, which is arbitrage across Nagle's commitment fence.
- **Ramp depth:** `ramp_year_1_acv` and `ramp_year_2_acv` against steady-state `booked_acv`. Record ramp concession dollars as a concession. The engine's annualization convention already makes the discount ramp-correct, so this adds a lens without re-basing anything.
- **Price floors** expressed as an effective unit rate and an overage rate, not only as `floor_pct`.
- **Repricing cadence** captured as decision fields: rate-card review term, price-protection term, and any committed pass-through of cost declines. A promise to pass future token savings to the buyer is a concession, and it gets logged and traded like a discount. Campbell's "process, not project" points to a quarterly to semi-annual review for AI-native rate cards. The engine records the cadence; it does not set it.

**SaaS pocket-price waterfall, revenue-side only.** List, then booked (discount), then ramp concessions, credits and free months, then payment terms. This is Simon-Kucher's "govern the waterfall" applied to SaaS. It needs no cost input and fits the honesty rule: it is still price, not margin.

**Margin only as contribution margin, customer-supplied.** When a customer supplies `cogs_acv` or a variable unit cost, show "contribution margin, customer-supplied cost basis" per deal. Never infer cost from CRM or billing data. Decline "net margin per deal". Net margin needs opex allocation and has no defensible deal-level meaning, so a Head of Pricing could not defend it in committee.

**Value-based pricing as an EVC worksheet.** Inputs, each entered by a human with a source label of asserted or measured:
- the next best alternative and its cost (competitor, build in-house, or the manual status quo);
- one to three differentiation drivers with the customer's own quantities;
- the resulting EVC, the value gap (EVC minus quoted price), and the share of value captured (price divided by EVC).

The engine only does arithmetic, and the LLM never fills a cell. Make it optional and reserve it for large exceptions. Segment-level reference prices (the existing win points) remain the data-backed layer, and per-customer EVC is evidence attached to a decision. Once enough decisions carry a worksheet, test whether price/EVC predicts wins.

**Value metric field:** add a free-text `value_metric_unit` (tokens, tasks, GB, robot-hours) alongside the enum. A `cost_indexed` flag can then be raised against it.

**Proposed vault note:** `vault/Decisions/2026-11-06-usage-native-contract-structure-and-margin-boundary.md` (tags `#decision #ubp #margin #positioning`), linking [[2026-08-08-crm-honesty-and-ubp-math]], [[2026-08-09-phase3-distribution-manufacturing-sizing]] and [[defensibility-rebuttal]]. Proposed only; not written.

# 3. Risks and tradeoffs

- **Scope creep against pilots.** "Add more features" across four directions plus three new asks, for a pre-user solo founder, is Ramanujam's feature shock (`vault/ramanujam-monetizing-innovation.md`). The critical path is still a paid pilot. Every item above must pass one test: would a design partner's deal desk use it in the readout?
- **Cold start is worse for AI-native ICPs.** Young companies have fewer closed deals, and commit or overage bands split the book further. Contract-structure guidance has to start rule-based, with "insufficient data" for any modeled curve. The engine must not claim to learn.
- **Billing-platform intake means data dependency on the feared entrant.** Stripe/Metronome, Adyen/Orb and Salesforce/m3ter own the usage actuals. Integrate many of them to stay neutral, never one deeply.
- **Margin pulls toward the incumbents' home turf.** Physical-goods margin attacks PROS, Vendavo and Zilliant with a shallower version of their own science (the defensibility flip in the Phase-3 note).
- **Tax is not a pricing input in most SaaS deals.** Sales tax and VAT pass through. Withholding tax on cross-border deals does affect net receipts, but that is a finance-system concern.
- **Tradeoff:** declining BOM and landed cost now may disappoint the founder's physical-AI thesis. Pulling the Phase-3 engine forward without a validated wedge risks building two half-engines.

# 4. Recommended first increment

**Contract-structure lens v0 on the CSV path.** Its parts:

1. A new deterministic metrics section using fields that are already captured: effective committed unit rate and its realization, commit share of booked, the overage-fence flag, ramp depth and ramp concession dollars, and a revenue-side pocket waterfall.
2. Each output labeled `method: policy rule`, with "insufficient data" wherever fields are missing.
3. A readout section that lists the deals behind each flag.
4. Decision-record fields for any commit, ramp, overage or repricing concession, and for what was traded for it.

The increment adds no connector, no margin and no EVC. Stripe, Metronome and CPQ exports map onto the existing four-layer header mapper (`docs/design/richer-ingest.md`), which tests platform-agnostic intake for free.

**Effort:** about 1.5 days of pricing spec plus 5 to 7 days of engineering, including tests.

**Validation:** run it on one design partner's export and ask the deal desk which flags they would have acted on. Measure commit coverage, effective-rate realization, and ramp concession as a percent of booked.

**Next increment, gated on a partner supplying cost:** customer-supplied contribution margin, about 3 days.

# 5. Positioning that survives

"Pricekeel is the neutral decision record for usage-based deal concessions: it prices every discount, commit and overage exception before approval, from your own won and lost deals, wherever the deal is quoted."

Form line (47 characters): "Explainable approval for usage-based deal terms." Margin and EVC are evidence inside the record, not nouns in the sentence.

# 6. Open questions for the founder

1. Does the ICP stay at $10M to $100M ARR usage-based SaaS, or do physical-AI companies that sell hardware plus usage become a target now? Only the second answer justifies BOM inputs before Phase 3.
2. Would contribution margin per deal, from customer-supplied variable cost, meet the margin ask, or is net margin a hard requirement? I recommend against net margin.
3. Which non-Salesforce intake comes first: a billing export, which brings usage actuals and so overage realization, or a CPQ export, which brings quoted terms and so commit and ramp at decision time?
4. Will the first design partner share unit cost data? If not, margin waits regardless of priority.
