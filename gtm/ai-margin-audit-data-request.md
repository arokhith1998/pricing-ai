---
title: "AI margin audit: data request (draft)"
created: 2026-11-10
updated: 2026-11-10
tags: [gtm, data-request, audit-first, ai-margin, billing, inference-cost, draft]
status: draft
source: gtm/ai-margin-audit-offer.md; docs/design/2026-11-09-native-connectors-hubspot-stripe-chargebee.md (billing field names); gtm/data-request.md; gtm/data-readiness-checklists.md; docs/legal/one-page-mutual-nda-data-addendum.md Schedule A; docs/agents/DECISIONS.md ADR-006
---

# AI margin audit: data request

Draft for founder review, not yet sent. Companion to [[ai-margin-audit-offer]] and
[[ai-margin-audit-runbook]]. Unlike `gtm/data-request.md` (a CRM closed-deal export), this asks
for billing, model-provider, and cost exports, joined per customer.

**What has not been verified.** Column names for Stripe, Chargebee, OpenAI, and Anthropic exports
below come from general platform knowledge and from the field names in our own connector design.
No named vendor's current export has been checked. The intake call confirms each export against
the customer's actual headers. Treat every vendor column list as a hypothesis, and accept their
natural headers: we map them.

## How to send, and what not to send

- **Exports only.** CSV or XLSX. No API keys, no OAuth tokens, no restricted keys, no read-only
  integration users. If you offer credentials, we decline and restate this.
- **Customer codes, not customer names.** Replace every end-customer identifier (Stripe or
  Chargebee customer id, company name, email, domain) with a code you assign, for example
  `C-0001`. Use the same code in every file. Keep your own lookup table; we never receive it.
  Each file contains the code and nothing that identifies the customer.
- **Monthly rollups, not events.** Per customer per month. No request-level logs, no per-call
  rows.
- **No content.** No prompts, no model outputs, no documents, no end-user data, no contact
  names or emails.
- **One currency per file**, or tell us the exchange rate and date to use.
- **Delivery route** is confirmed by the founder at intake. Files go into the encrypted
  customer folder per `docs/ops/data-handling-sop.md`. They are never sent to a cloud AI service.
- **Cost data.** The cost exports are your own statement of what serving each customer cost, and
  we treat them as your cost basis. Results are labelled "contribution margin, customer-supplied
  cost basis". We do not verify cost against your ledger.

Window: the last **6 months** is the target, **3 months** the minimum. Twelve months is better for
pilot-to-ARR conversion.

## A. Billing: Stripe or Chargebee

Ask for the exports below from your billing admin. The "Field" column uses the names from our
native connector design (`docs/design/2026-11-09-native-connectors-hubspot-stripe-chargebee.md`,
the `contract_period_actuals` grain and the canonical deal fields) so a future connector reads
the same shape. Your headers will differ.

| File | Columns we need | Field name we map to | Needed |
|---|---|---|---|
| **A1. Invoices with line items**, one row per invoice line | Invoice date or period start and end | `period_start`, `period_end` | Required |
| | Customer code | (code you assign) | Required |
| | Currency | `currency` | Required |
| | List or catalog amount on the line, if known | `list_amount` | Strongly wanted |
| | Invoiced amount, tax excluded | `invoiced_amount` | Required |
| | Discount amount on the line | `discount_amount` | Required |
| | Credit or credit-note amount applied | `credit_amount` | Required |
| | Metered units billed, and unit name | `usage_units` | Required if any usage pricing |
| | Metered amount billed | `usage_amount` | Required if any usage pricing |
| | Committed or minimum amount | `committed_amount` | If it exists |
| | Plan or price name, and product name | `product_tier`, `sku` | Required |
| | Line type: recurring fee, usage, one-time, setup | (flag) | Required |
| **A2. Subscriptions** | Customer code | | Required |
| | Subscription start, end, canceled date, status | `close_date` (proxy), `term_months` | Required |
| | Plan, interval (monthly or annual), quantity or seats | `product_tier`, `quantity` | Required |
| | Contracted recurring price after coupons or custom pricing | contracted amount, not "booked" | Required |
| | Trial days, trial end | `credits_tcv` source | If used |
| | Pilot or paid-trial flag, if you track one | (flag) | Strongly wanted |
| | Ramp or schedule phases and amounts | `ramp_year_1_acv`, `ramp_year_2_acv` | If used |
| **A3. Credit notes and refunds**, one row per note | Customer code, date, amount, reason | `credit_amount` | Strongly wanted |
| **A4. Coupons and discounts in use** | Name, percent or amount, duration, customers using it (by code) | | Nice to have |

Notes:
- In Stripe the export names likely include invoices, invoice line items, subscriptions,
  customers, and credit notes. In Chargebee, subscriptions, invoices with line items, and credit
  notes. Chargebee sites on Product Catalog 1.0 may need an extra mapping step.
- Payment processing fees (Stripe or other) are not cost of goods and are not part of the cost
  basis unless you tell us to treat them separately. Send them only if you want them shown as a
  separate line.
- Billing holds paying customers only. The audit has no win or loss rates from billing.

## B. Model-provider usage and cost exports

Goal: monthly cost per customer for model inference. What exists depends on how you call the
provider. Field lists below are from general knowledge and must be confirmed against your
dashboard or Admin API.

### B1. OpenAI

Likely sources: the organization usage and costs views and their CSV export, or the usage and
costs endpoints in the admin API (an admin key is needed to call the API; **do not send us the
key**, run the export yourself).

Columns that typically exist, to confirm:
- Date or time bucket (day or month).
- Model name.
- Input tokens, output tokens, cached input tokens, request count.
- Project, API key id, or user id, depending on the grouping you choose.
- Cost: amount, currency, and a line item label (the costs data is separate from the usage data;
  we want both, or cost alone).

### B2. Anthropic

Likely sources: the Console usage and cost views and their CSV export, or the usage and cost
reports in the admin API. Again, run it yourself.

Columns that typically exist, to confirm:
- Date or time bucket.
- Model name.
- Uncached input, cached input (read and write), and output token counts.
- Workspace, API key id, or similar grouping.
- Cost: amount and currency, grouped by model or workspace.

### B3. Per-customer attribution: decision tree

Ask in this order and record where the customer lands. This is the key question of the whole
audit.

1. **A. Direct.** Do you use a separate API key, project, or workspace for each customer (or
   each group of customers)? Then group the provider export by that key, project, or workspace
   and give us a small mapping from key or project id to customer code. We need the mapping, not
   the keys.
2. **B. App-side rollup.** Does your application log the customer on each model call (a
   metadata field, a tag, a request log)? Then send a monthly rollup per customer code per model:
   request count, input, cached input, output tokens, and cost computed from the provider's
   price list or your own meter. We reconcile the token total back to the provider total.
3. **C. Allocated.** Neither exists, but you have a usage driver per customer (tasks completed,
   documents processed, minutes, requests in your own database). Send the monthly driver per
   customer code, and the provider total per month. We allocate cost in proportion to the
   driver. Every row is labelled "allocated", the allocation is shown as an assumption, and the
   result is lower confidence.
4. **D. Not attributable.** None of the above. We cannot build the per-customer table. We deliver
   a plan-level and company-level cost floor from the provider total divided by billed units,
   and we tell you what to instrument (a key or project per customer, a metadata field on every
   call) so the next run can do it properly. The negative-margin account list and the heavy-user
   tail by customer are not produced.

Whatever the method, also send the **provider's total cost per month** so we can compute what
share of cost is attributable.

## C. Cloud, storage, and hosting cost lines

Needed in full if storage or hosting is a meaningful share of your serving cost. For video- or
data-heavy products, ask the question directly at intake: roughly what share of cost of serving
is storage and hosting today, and how is it trending?

| File | Columns | Needed |
|---|---|---|
| **C1. Cloud bill by month**, grouped by service (compute, GPU, object storage, database, bandwidth, vector database) | Month, service, cost, currency | Required if infrastructure is above about 10 percent of serving cost (hypothesis), otherwise nice to have |
| **C2. Storage per customer** | Customer code, month, bytes or GB stored | Wanted if storage is customer-driven |
| **C3. Compute or GPU per customer** (owned or reserved capacity) | Customer code, month, a usage driver such as GPU hours or jobs | Nice to have, needed for method C on hosting |
| **C4. Cost tags or labels per customer**, if the cloud account tags resources per customer | Tag value mapped to customer code, month, cost | Nice to have, makes it direct |

Third-party tools that sit in the cost of serving (vector database, speech, OCR, retrieval, human
review vendors) are included as lines in C1, with the allocation driver if there is one.

Do not send: supplier contract terms or rate cards, bills that show account or personal data, or
any named customer.

## D. Customer list with plan and start date

One row per billed customer, by code.

| Column | Meaning | Needed |
|---|---|---|
| Customer code | Same as everywhere | Required |
| Plan or package | Current plan name | Required |
| Start date | First paid date | Required |
| End or cancel date, if any | | Required if applicable |
| Contract type | Pilot, paid trial, monthly, annual, enterprise agreement | Required for pilot-to-ARR |
| Pilot end date and whether it converted | | Required for pilot-to-ARR |
| Segment or size band | Your own labels | Nice to have |
| Included allowance or commit, if any | | Nice to have |
| Special terms (a custom price, a promise, a free period, and why) | | Strongly wanted |
| Delivery effort: support or forward-deployed hours per month | The "human middleware" check | Nice to have |

## E. Pricing page and packaging history

| Item | Detail | Needed |
|---|---|---|
| **E1. Current pricing page** | Plans, units, included usage, overage, enterprise note. A screenshot or PDF is fine. | Required |
| **E2. Packaging history** | A short dated list: when pricing or plans changed, what changed, and why. Include any planned change. | Strongly wanted |
| **E3. Discount policy** | Written, or an honest statement that there is none. Name the owner. | Required (gate) |
| **E4. Quote or order form template** | For commit and term structures | Nice to have |
| **E5. Competitor and bundling notes** | Which incumbents or platforms offer a similar feature, and any deal where bundling came up | Nice to have |
| **E6. Accuracy or evaluation summary** | Any eval pass rate, and the date, you are willing to share. No prompts or outputs. | Nice to have |

## Minimum viable set and nice-to-haves

**Minimum viable set (the clock does not start without all four):**

1. A1 and A2: invoices with line items and subscriptions, at least 3 months, customer codes.
2. B or C1 cost: inference cost per customer per month by method A, B, or C, plus the provider
   total per month. (Method D gives a plan-level audit only. The offer says the per-customer
   table cannot then be produced.)
3. D: the customer list with plan and start date.
4. E1 and E3: the current pricing page and the discount policy statement and owner.

**Nice-to-haves:** A3 and A4, B usage columns beyond cost, C1 to C4, D contract type and pilot
fields, delivery effort, E2, E4 to E6. Each one sharpens a named analysis (below) and none stops
the clock.

## What each analysis is impossible without

| Analysis | Impossible without | Degrades without |
|---|---|---|
| Per-customer margin-health table | A1 or A2 per customer per month, cost by method A, B, or C, and a common customer code across files | C1 (cost floor incomplete if infrastructure matters), A3 (credits make revenue look higher than collected) |
| Heavy-user tail | Per-customer cost or per-customer usage units (B or C driver) | Usage columns beyond cost |
| Negative-margin accounts | Both revenue and cost per customer on a shared code | Allocation sensitivity needs the driver in method C |
| Plan-level cost floor | Provider total per month plus billed units or plan counts (works with method D) | Customer-level usage percentiles |
| Predictability review | 3 or more months of invoices per customer (A1) | Metered units (to model pure usage) |
| Discount and packaging review | E1 plus A1 discount and credit fields, A2 plan and quantity | E2 history, A4 coupons, E4 templates |
| Pilot-to-ARR conversion | D contract type or the A2 pilot flag, start dates, and at least some ended pilots | 12 months of history, pilot end dates |
| Value metric review | Any per-customer unit count (tasks, documents, outcomes) or metered usage | Outcome definitions from the intake call |
| Variance and trust notes | A3 credit notes or a stated churn reason list | E6 evals, delivery effort |
| Bundling exposure | Nothing computed: it is a judgement from the intake call | E5 notes |

## Readiness check (what we do on day 1)

- Headers and row counts for every file, then the join test on customer codes: matched,
  unmatched, duplicated.
- Revenue by month against any total you state. Provider cost by month against the provider bill.
- Attribution coverage: the share of cost attributable to a customer.
- Outcome: go, go with limits (we name the analyses that cannot run), or stop.

## Handling and contract status (internal, remove before sending)

- **Blocker: this request asks for data the current addendum does not cover.** Schedule A says
  Class 2 usage is rollups with no end-customer identifiers (customer codes plausibly satisfy
  this, counsel to confirm), and Class 3 cost is only a rate or margin-percentage table by
  product family, off by default and excluded from benchmarking. Per-customer, per-month cost
  rollups are not a rate table. A written amendment is needed before any cost file moves
  (F-audit-data-class). Until then, this request is a draft only.
- `gtm/data-readiness-checklists.md` says "What we will not ask for: cost data" for pilot 1. This
  request is the stated exception, by amendment, for the audit only.
- Data register: add a class row for per-customer billing and cost rollups before the first
  receipt, and a Part B row on the day files arrive. No credentials are held, so no credential
  row is needed.
- Benchmarking (section 9) never covers cost data, even on opt-in. If the customer opts in, only
  revenue-side aggregates could qualify, and nothing publishes below the minimum cohort size.
- ADR-006: a customer-supplied cost export is `declared_cost`. Label every figure "contribution
  margin, customer-supplied cost basis". Never gross margin. Never net margin. The word margin
  never describes revenue-only or CRM figures.
- Stripe and Chargebee connectors do not exist yet (earliest early 2027). This audit is export
  only, which also matches the pilot 1 rule of no keys.
- No em dashes.

## Related

[[ai-margin-audit-offer]] · [[ai-margin-audit-runbook]] · [[data-request]] ·
`gtm/data-readiness-checklists.md` · `docs/ops/data-register.md`
