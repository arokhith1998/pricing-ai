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

In 14 days from validated intake of your billing and cost exports, we show you which customers
and plans your inference and storage costs leave with thin or negative contribution margin,
customer-supplied cost basis, and we recommend a packaging structure for you to decide on.

The promise is to find which customers cost more to serve than they pay, and the packaging that
fixes it. If we do not deliver the 14-day readout, you pay nothing. That is the only guarantee.
We do not guarantee any outcome: no recovered revenue, no change in contribution margin, no
result from any pricing decision. The audit is analytical and advisory, built on your
historical data. Every pricing decision stays with you.

## Who this is for

AI companies moving from flat-rate or per-seat pricing to usage or outcome pricing, who suspect
some customers cost more to serve than they pay. The usual sign: someone on your team already
reconciles the monthly model-provider bill against Stripe or Chargebee in a spreadsheet.

Seed-to-Series-A AI companies are the audit's learning segment: the fastest place to learn
what this analysis needs to answer. The product's ICP is AI-native usage or hybrid companies in
the $20M to $100M ARR band (F3). Both are welcome to ask for the audit.

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
   customer-supplied cost basis" because the cost figures come from you. Cost you cannot
   attribute to a customer is shown as an unallocated line, and if more than 20 percent of
   cost cannot be attributed, the readout says it is an upper bound.
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
end-user personal data. Customers appear as codes you assign. You also confirm in writing that
the cost file is your own cost of serving, and give us a key map from each cost key to a
billing account.

## Before we can accept any file

We do not receive any customer cost file until all four of these are in place: counsel has
signed the data-addendum amendment covering per-customer cost, our legal entity is formed, our
insurance is bound, and an engagement letter is signed. Until then we can talk, and you can use
the calculator, neither of which needs any of that. We will tell you when each is done.

## Price

**$7,500, fixed, paid upfront, delivered 14 days from validated intake.** No share of results,
no success fee. There is no credit toward a later subscription on the first two audits.

**Delivery guarantee:** If we do not deliver the 14-day readout, you pay nothing. Nothing else
is guaranteed: not recovered revenue, not any change in contribution margin, not any result
from a pricing decision you make.

## Terms (summary)

- **Upfront fee**, $7,500 fixed, due at signature, before work starts.
- **14-day clock starts at validated intake**: the day we receive the minimum viable set of
  exports and they pass our one-business-day readiness check. If they do not pass, we tell you
  what is missing and the clock has not started.
- **Mutual NDA and data addendum** signed before any data moves.
- **No data leaves the audit.** Your data is used only to deliver your audit. It is never sent
  to a cloud AI service, never used to train models, never used for another customer. Working
  files are encrypted, access-logged, and deleted within 30 days of the readout (sooner on
  request), with written certification.
- **Benchmarking is opt-in and off by default.** If you opt in under the existing addendum
  language, only aggregated, anonymized, revenue-side statistics may ever join a cross-customer
  benchmark, and only above a minimum cohort size. Your cost data is never included, even if
  you opt in. The audit is identical either way.
- **One guarantee, on delivery only.** If we do not deliver the 14-day readout, you pay nothing.
  There is no outcome or margin guarantee. Findings are historical and correlational. They do
  not promise recoverable revenue.
- **Human in the loop.** We recommend; you decide. Everything in the readout traces back to a
  documented formula and your own rows.

## Who this is not for

- Companies with fewer than about 10 billed customers or under 3 months of billing history.
- Companies that cannot attribute any model or hosting cost to customers and will not instrument
  it. We can run a plan-level view, but not the per-customer table (see the data request).
- Anyone who wants a guaranteed result or a tool they can log into. This is a done-for-you
  analysis delivered by a person, not software.
- Companies whose main cost is owned GPU capacity that cannot be allocated to customers.
- Teams that want us to hold API keys or connect to their systems. We work from exports.
- Anyone unwilling to sign the NDA and data addendum.

---

## Internal notes (remove before this leaves the vault)

### F-audit-price: decided (F4, 2026-11-10)

**$7,500 fixed, paid upfront. The clock starts at validated intake** (minimum viable set
received and passed a one-business-day readiness check). **No credit toward a later
subscription on the first two audits.** Credit terms are decided per deal after the third
audit, when a subscription exists. Reasoning:

- **Our cost.** The CFO review puts break-even near $7,500 at a $150 an hour founder rate for a
  50 to 72 hour hand-run audit (the earlier 25 to 35 hour estimate was low). A lower fee loses
  money on every audit.
- **What the price must test.** The purpose is willingness to pay. A price low enough that
  nobody hesitates proves little. A corporate-card or approved purchase at $7,500 is a real
  signal. Above roughly $10,000 it becomes a procurement and runway discussion, a slower sale.
- **Different from the $15K pilot.** The existing $15K, 90-day pilot is the Salesforce discount
  product. Do not stack or reuse it here. No product exists yet for the margin wedge, so the
  audit must not be priced as if software were included.
- **F16 (2026-11-11): price unchanged, guarantee added.** $7,500 fixed stays. The only guarantee
  is on delivery: "If we do not deliver the 14-day readout, you pay nothing." No outcome or
  margin guarantee. The $2,500 a month follow-on exists only in the runbook's Day 14 close. It
  never appears in this page's price line or on the site.
- **Adjustment rule.** If three of the first five qualified prospects who hear the price decline
  on price, test $6,000 and record why they declined.
- **Not offered.** No share of any improvement (F5: attribution on a historical audit is
  disputable). Revisit only after one audit has produced a finance-signed per-customer baseline
  at constant input unit prices. No monthly retainer in the offer itself.
- **Follow-on settled (F16):** $2,500 a month, offered only in the Day 14 close, to keep the
  per-customer contribution margin view current and re-measure at 60 to 90 days (see the
  runbook's Re-measure step and PK-115).

### Blockers before this offer can go to a prospect

0. **F11 gate: no customer cost file is received until** counsel has signed the data-addendum
   amendment for per-customer cost (PK-96), the entity is formed, insurance is bound and an
   engagement letter exists. Interviews and the calculator need none of it.
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
   while this offer now says "validated intake" too. The definition (minimum viable set received
   and passing a one-business-day check) is meant to match; counsel should confirm.
5. **ICP settled (F3).** Seed-to-Series-A AI companies are the audit's learning segment. The
   product's ICP is AI-native usage or hybrid companies in the $20M to $100M ARR band. The
   site and the Salesforce-first product are unchanged. Record the ICP sentence in the vault
   before any site copy changes.
6. **Payment is a commercial action.** The founder sends the offer, the invoice, and the
   agreement. Nothing here is sent by anyone else.

### Wording rules applied

- "Margin" appears only as "contribution margin, customer-supplied cost basis" (`declared_cost`
  under ADR-006 and ADR-007, F1). Every promise and output uses that label. Never on a CRM
  figure. No other margin label is used anywhere.
- No "proven", no guarantees, no recovery figure. The sheet's $50,000 and $2,500 figures are
  the founder's synthesis, not evidence, and are not used in customer copy.
- No em dashes.

### Related

[[2026-11-10-audit-first-motion-and-ai-margin-wedge]] · [[ai-margin-audit-runbook]] ·
[[ai-margin-audit-data-request]] · [[readout-close-script]] · [[security-one-pager]] ·
`docs/reviews/2026-11-10-audit-first/FOUNDER-DECISIONS.md`
