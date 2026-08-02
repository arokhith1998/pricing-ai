# Pricekeel market-need assessment

Status: active decision memo. Research date: 2026-08-01.

## Verdict

**The category need is real; Pricekeel-specific demand is not yet proven.**

Proceed with a tightly scoped Salesforce design-partner motion. Do not claim
product-market fit, publish a top-down TAM as evidence, or broaden the build.
The next proof is two paid pilots using real customer data and a recurring
decision workflow—not more synthetic functionality.

## What the market evidence proves

1. **Customers already budget for revenue and pricing workflow software.**
   Salesforce currently lists Revenue Cloud Growth at $150/user/month and
   Advanced at $200/user/month, billed annually. It includes quoting,
   subscriptions, contracts/orders, AI, and analytics:
   https://www.salesforce.com/sales/revenue-lifecycle-management/revenue-optimization-pricing/
2. **The requested capability is an established category, not an invented
   problem.** Salesforce describes product/price management, discount
   matrices, price-waterfall visibility, automated approvals, revenue
   dashboards, and support for subscription, usage, and hybrid models:
   https://www.salesforce.com/sales/revenue-lifecycle-management/revenue-cloud/
3. **Specialists sell the same core job.** Vendavo markets target/floor
   guidance, margin guardrails, approvals, and quote-workflow analytics:
   https://www.vendavo.com/solutions/deal-guidance-and-negotiation/
   Pricefx offers negotiation guidance, product recommendations, historical
   segmentation, discount/margin guardrails, and workflow integration:
   https://www.pricefx.com/software/ai-optimization
4. **Strategic capital validates the category's economic importance, not
   Pricekeel's fit.** The December 2025 acquisition of PROS valued the company
   at about $1.4B and contemplated combining its B2B pricing business with
   Conga's CPQ/contract platform:
   https://www.sec.gov/Archives/edgar/data/1392972/000119312525312044/d54162dex993.htm

This evidence establishes an existing budget, competitive supply, and buyer
attention. It does not establish that a $20M-$100M ARR B2B SaaS company will
replace or augment its current stack with Pricekeel.

## The competitive implication

The phrase "AI pricing platform" is too broad and puts Pricekeel head-to-head
with mature suites. Salesforce already owns the transaction workflow; Pricefx
and Vendavo already sell pricing optimization and deal guidance.

The defensible initial wedge is narrower:

> The decision-integrity layer for Salesforce discount exceptions: show the
> comparable evidence, preserve the rep's requested terms, require a human
> disposition, write the decision back to the CRM, and reconcile the outcome.

That positioning is useful only if Pricekeel can install faster, work with the
customer's existing Opportunity fields, expose evidence more clearly, and
prove price-realization or cycle-time value without a CPQ replacement.

## Target customer and disqualifiers

Focus on sales-led or hybrid B2B SaaS companies with:

- $20M-$100M ARR;
- Salesforce as the operating CRM;
- 500+ closed outcomes per year as the target data volume;
- recurring non-standard discount requests;
- reliable annualized list and booked values;
- a documented approval policy;
- RevOps/Pricing as champion and CFO/finance as economic buyer.

Disqualify or defer companies with fewer than 30 usable closed outcomes, no
reliable pre-discount value, unmanaged multi-currency data, no recurring deal
desk, or no executive owner for price realization.

## What remains unproven

As of this memo, the repository and vault contain no signed design partner, no
real customer Salesforce dataset, no completed willingness-to-pay interview,
and no measured change in price realization, win rate, or exception time. The
Developer Edition org and synthetic tests prove engineering behavior only.

The product also does not yet have:

- authenticated per-user identity and approver roles;
- a packaged Salesforce ECA install tested in a subscriber org;
- true margin data from billing/ERP costs;
- usage telemetry for application-level recommendations;
- evidence that public competitor context changes customer decisions;
- causal proof that the recommended discount changes win probability.

## Validation program and decision gates

### Stage 1: problem proof

- Interview 15 ICP operators: at least five Pricing/RevOps, five sales/deal
  desk leaders, and five finance leaders.
- Require a recent real discount exception in every interview; do not ask
  hypothetical feature-preference questions.
- Pass when at least 10 describe the same recurring workflow failure, at least
  six can name an owner and budget, and at least five agree to a data-readiness
  review.

### Stage 2: install and data proof

- Complete five Salesforce field/readiness assessments.
- Install in three customer sandboxes.
- Pass when at least three have reliable list/booked values, 500+ annual closed
  outcomes, and one open exception that Pricekeel can reconstruct without
  manual data repair.

### Stage 3: willingness-to-pay proof

- Offer the existing commercial structure: $15K for a 90-day pilot, with 50%
  credited to a $30K-$60K annual subscription if signed within the agreed
  window.
- Pass when two customers sign and pay. Free pilots do not clear this gate.

### Stage 4: outcome proof

Pre-register the pilot measures:

- price realization at comparable deal mix;
- win rate by discount band;
- median exception turnaround time;
- recommendation acceptance and override rate;
- incremental booked ACV retained;
- user adoption by rep and approver.

Renew only when the customer accepts at least one economic threshold and the
workflow is used repeatedly without founder intervention.

## TAM and SAM discipline

Do not use the total pricing-software market as Pricekeel's TAM proof. Build a
bottom-up model after the first 15 interviews:

```text
TAM = Salesforce B2B SaaS accounts in the $20M-$100M ARR band
      that run a recurring deal desk
      x validated annual contract value

SAM = TAM accounts in reachable geographies
      x share that passes Pricekeel data/readiness requirements
      x share that is not locked into a sufficient incumbent workflow

SOM (36 months) = accounts reachable by founder-led sales
                 x observed meeting-to-pilot conversion
                 x observed pilot-to-paid conversion
                 x validated annual contract value
```

Use the current $30K-$60K annual contract range only as a hypothesis until paid
pilots validate it. Interview and funnel observations must replace assumed
conversion rates.

## Decision

Continue the Salesforce workflow and founder-led outreach. Freeze margin,
application, and quantitative competitor features until the required cost,
usage, and customer evidence exists. The next company milestone is not a
broader feature set; it is the first paid customer decision loop.
