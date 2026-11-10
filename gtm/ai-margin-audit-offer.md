---
title: "AI margin audit: one-page pilot offer (draft)"
created: 2026-11-10
updated: 2026-11-10
tags: [gtm, offer, audit-first, ai-margin, pilot, draft]
status: draft
source: gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md (Opportunity tab move 1, Consumer Trends tab bottlenecks 1 to 6); vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md; docs/agents/DECISIONS.md ADR-006; docs/legal/one-page-mutual-nda-data-addendum.md
---

# AI margin audit: one-page offer

Draft for founder review. Nothing here has been sent, and nothing here is a commitment until
the founder says so. The text above the line "Internal notes" is written to be forwardable to a
prospect. The internal notes below it are not.

## The promise, in one sentence

In 14 days from receiving your billing and cost exports, we show you which customers and plans
your inference and storage costs are eroding contribution margin on, using the cost basis you
supply, and we recommend a packaging structure for you to decide on.

No guarantee of recovered revenue. The audit is analytical and advisory, built on your
historical data. Every pricing decision stays with you.

## Who this is for

Seed to Series A AI companies moving from flat-rate or per-seat pricing to usage or outcome
pricing, who suspect some customers cost more to serve than they pay. The usual sign: someone
on your team already reconciles the monthly model-provider bill against Stripe or Chargebee in
a spreadsheet.

## What we audit

Six questions, one per structural pricing bottleneck. Some answers are evidence-backed from your
numbers and some are judgement, and the deliverables say which is which.

**1. Cost floor and negative-margin accounts**
- What does it cost to serve each customer per month: model inference, storage, and hosting?
- Which customers and plans pay less than they cost? How concentrated is cost in a small
  heavy-user tail?
- At what usage does each plan stop covering its own cost?

**2. Packaging and predictability**
- Where does the current structure (flat, per-seat, usage, hybrid) leave money uncollected or
  customers exposed to surprise bills?
- How much does each customer's monthly bill move? Would your buyers' finance teams accept a
  commit, a cap, or a band instead?
- If seats stop being the unit, what happens to revenue as the product gets more effective?

**3. Value metric and outcome pricing**
- Which unit (tasks, documents, outcomes, tokens, seats) tracks the value your customers get
  and also tracks your cost?
- If you priced per outcome, how lumpy would revenue be, and can the outcome be defined in a
  contract today?
- Are early discounts to win logos still sitting in your price book?

**4. Variance and trust**
- Where do inconsistent outputs show up in the commercial record: credits, refunds, re-runs,
  churn reasons, discounts given to keep an account?
- How much human effort sits behind delivery, and is it priced?

**5. Pilot revenue versus true ARR**
- How much of reported recurring revenue comes from pilots or paid trials?
- Of pilots that ended, how many converted, at what price relative to the pilot?
- What does ARR look like with pilot revenue separated out?

**6. Bundling exposure**
- Which of your features could a large incumbent bundle into an existing suite?
- Which parts of your price depend on being a stand-alone add-on, and which on owning the
  workflow and your customers' history?

## What you get in 14 days

1. **Per-customer margin-health table.** One row per customer: plan, monthly revenue, attributed
   cost, contribution margin on a customer-supplied cost basis, a health band, and a
   confidence rating for how the cost was attributed. Labelled "contribution margin,
   customer-supplied cost basis" because the cost figures come from you. Net margin is not
   produced.
2. **Plan-level cost floor.** For each plan, the usage level at which it stops covering its cost.
3. **Heavy-user tail analysis.** Share of cost by customer decile, and who sits in the tail.
4. **Negative-margin account list**, with the drivers for each (plan, usage pattern, discount,
   attribution uncertainty) and how the conclusion changes under different cost allocations.
5. **An optimized packaging structure**, as a recommendation for you to decide on: one
   primary structure and two alternatives, each shown against your actual history as a static
   re-pricing table. This is not a forecast and does not model how customers would react.
6. **Predictability review.** Month-to-month bill variance by customer, and where a commit, cap,
   or band would reduce it.
7. **Discount and packaging review.** Concessions in the price book and on invoices, and
   what they cost.
8. **Pilot-to-ARR view.** Revenue split into pilot and recurring, conversion of ended pilots,
   and ARR restated with pilot revenue separated.
9. **Variance, trust, and bundling notes.** Evidence-backed where your records allow,
   labelled as judgement where they do not.
10. **A 60-minute readout** with your numbers first, and a written PDF you can forward to
    your finance lead or board.
11. **A method appendix.** Every formula, assumption, and judgement call used, so your
    finance lead can audit the work rather than trust it.
12. **A written data-deletion certification** at the end of the engagement.

## What we need from you

Billing exports, model-provider usage and cost exports, cloud and storage cost lines, a customer
list with plan and start date, and your pricing page and packaging history. The exact list,
minimum set, and formats are in [[ai-margin-audit-data-request]] (file
`gtm/ai-margin-audit-data-request.md`). We need a person on your side who can answer pricing
questions and who owns the pricing decision.

We ask for exports only. No API keys, no OAuth tokens, no prompts or model outputs, no
end-user personal data. Customers appear as codes you assign.

## Price

Fee and structure to be confirmed by the founder. See internal notes (F-audit-price).

## Terms (summary)

- **Upfront fee**, due at signature, before work starts.
- **14-day clock starts at data receipt**: the day we receive the minimum set of exports and
  they pass our one-business-day readiness check. If they do not pass, we tell you what is
  missing and the clock has not started.
- **Mutual NDA and data addendum** signed before any data moves.
- **No data leaves the audit.** Your data is used only to deliver your audit. It is never sent
  to a cloud AI service, never used to train models, never used for another customer. Working
  files are encrypted, access-logged, and deleted within 30 days of the readout (sooner on
  request), with written certification.
- **Benchmarking is opt-in and off by default.** If you opt in under the existing addendum
  language, only aggregated, anonymized, revenue-side statistics may ever join a cross-customer
  benchmark, and only above a minimum cohort size. Your cost data is never included, even if
  you opt in. The audit is identical either way.
- **No guarantees.** Findings are historical and correlational. They do not promise recoverable
  revenue.
- **Human in the loop.** We recommend; you decide. Everything in the readout traces back to a
  documented formula and your own rows.

## Who this is not for

- Companies with fewer than about 10 billed customers or under 3 months of billing history.
- Companies that cannot attribute any model or hosting cost to customers and will not instrument
  it. We can run a plan-level view, but not the per-customer table (see the data request).
- Anyone who wants a guaranteed margin recovery or a tool they can log into. This is a done-for-you
  analysis delivered by a person, not software.
- Companies whose main cost is owned GPU capacity that cannot be allocated to customers.
- Teams that want us to hold API keys or connect to their systems. We work from exports.
- Anyone unwilling to sign the NDA and data addendum.

---

## Internal notes (remove before this leaves the vault)

### F-audit-price: founder decision, fee not set

Recommendation: a fixed fee in the range **$4,500 to $7,500**, test at **$6,000** for the first
two audits. Reasoning:

- **Buyer budget.** A seed to Series A founder can usually approve a one-time spend of this size
  on a card or without a board conversation. This is a judgement, not evidence. Above roughly
  $10,000 it becomes a procurement and runway discussion, which is a slower and different
  sale.
- **The sheet's anchors.** The Opportunity tab argues for value pricing, around $2,500 a month
  or a share of the margin lift, and against cheap pricing that signals low quality. A 14-day
  audit at $6,000 is about two and a half months of that anchor, for a fixed deliverable. The
  floor of $4,500 stays well above the $2,500 level that reads as a tire-kicker price.
- **Our cost.** Estimated 25 to 35 solo hours per audit (hypothesis, untested). $6,000 over 30
  hours is about $200 an hour, defensible for pricing expertise and not a windfall.
- **What the price must test.** The purpose is willingness to pay. A price low enough that
  nobody hesitates proves little. A corporate-card purchase at $5,000 to $7,500 is a real
  signal.
- **Different from the $15K pilot.** The existing $15K, 90-day pilot is the Salesforce discount
  product. Do not stack or reuse it here. No product exists yet for the margin wedge, so the
  audit must not be priced as if software were included.
- **Adjustment rule.** If three of the first five qualified prospects who hear the price decline
  on price, test $4,500. If none hesitate, test $7,500.
- **Alternatives, not recommended now.** Share of margin lift (unmeasurable on a historical
  audit, invites a dispute about attribution) and a monthly retainer (premature; no follow-on
  deliverable is defined).
- **Open sub-decisions:** whether any fee is credited to a later Pricekeel agreement (the
  recommendation is no credit for the first two, to keep the willingness-to-pay signal clean);
  whether a follow-on monthly re-run is offered (F-audit-followon, not priced here).

### Blockers before this offer can go to a prospect

1. **Data classes need a written amendment (F-audit-data-class).** The audit needs per-customer
   revenue joined to per-customer cost. The current addendum Schedule A says Class 2 usage data
   is rollups only with no end-customer identifiers, and Class 3 cost data is only a rate or
   margin-percentage table by product family, off by default. The audit's per-customer cost
   rollups, keyed by a customer code, fall outside Class 3 as written. Pseudonymous codes
   plausibly satisfy the no-identifier rule but counsel must confirm. Until a counsel-reviewed
   amendment exists, do not request per-customer cost. The checklist line "What we will not
   ask for: cost data" in `gtm/data-readiness-checklists.md` is the pilot 1 rule; the audit
   needs a stated exception.
2. **The addendum is not signable.** Legal entity not formed; counsel review in progress
   (`docs/legal/one-page-mutual-nda-data-addendum.md`, header). Sections 9 to 12 are drafts.
3. **E&O and cyber insurance** are listed in the security one-pager roadmap as bound before the
   first paid engagement. Not yet bound.
4. **An engagement letter** carrying the fee, the clock definition, and the section 11
   disclaimer does not exist. Section 10 of the addendum says "validated intake" for the SLA,
   while this offer says "data receipt". The definition here (minimum set received and passing
   a one-business-day check) is meant to reconcile them; counsel should confirm.
5. **ICP conflict is open.** This offer targets the narrow AI ICP for the new motion only. The
   site's $20M to $100M ARR band and the Salesforce-first product are unchanged until the
   founder rules (see the decision note).
6. **Payment is a commercial action.** The founder sends the offer, the invoice, and the
   agreement. Nothing here is sent by anyone else.

### Wording rules applied

- "Margin" appears only attached to a customer-supplied cost basis (`declared_cost` under
  ADR-006, label "contribution margin, customer-supplied cost basis"). Never on a CRM figure.
  Never "gross margin" (reserved for `erp_verified`), and never net margin per deal.
- No "proven", no guarantees, no recovery figure. The sheet's $50,000 and $2,500 figures are
  the founder's synthesis, not evidence, and are not used in customer copy.
- No em dashes.

### Related

[[2026-11-10-audit-first-motion-and-ai-margin-wedge]] · [[ai-margin-audit-runbook]] ·
[[ai-margin-audit-data-request]] · [[readout-close-script]] · [[security-one-pager]]
