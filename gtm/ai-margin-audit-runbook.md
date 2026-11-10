---
title: "AI margin audit: 14-day hand-delivery runbook (draft)"
created: 2026-11-10
updated: 2026-11-10
tags: [gtm, runbook, audit-first, ai-margin, wizard-of-oz, draft]
status: draft
source: gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md (Opportunity tab, Wizard of Oz MVP); gtm/ai-margin-audit-offer.md; gtm/readout-close-script.md; docs/ops/data-register.md; docs/agents/DECISIONS.md ADR-006
---

# AI margin audit: 14-day runbook for a solo founder

Draft. Untested: no audit has been run. Hour estimates are hypotheses. This is the "Wizard of Oz"
version: every analysis is done by hand in a spreadsheet, and every step is logged so it can later
become software. Nothing here sends anything. The founder sends every message and invoice.

Companion files: [[ai-margin-audit-offer]] · [[ai-margin-audit-data-request]] · [[readout-close-script]].

## Ground rules

1. **Day 0 is data receipt**, not the call and not payment. The clock starts when the minimum
   viable set (see the data request) is received and passes the readiness check within one
   business day. Day 14 is the written deliverable.
2. **No LLM touches customer data.** No customer rows, codes, or amounts pasted into any cloud
   model, including for "thought partner" help. A model may help with generic formula syntax
   using synthetic values only (data register, deal rows class: never pasted into any LLM).
3. **Spreadsheets live in the customer folder** `C:\pricekeel-customer-data\<customer-slug>\`
   (encrypted volume, excluded from sync, per `docs/ops/data-handling-sop.md`). One workbook per
   audit. Verify the volume is actually encrypted before the first audit; the register marks it
   unverified.
4. **Register on the day.** Add a Part B row to `docs/ops/data-register.md` the day anything
   arrives, and update it the day anything is deleted. Slug only, no contact names, no values.
5. **Cost basis wording (ADR-006).** A founder-supplied cost export is `declared_cost`. The word
   margin is used only on that basis, always as "contribution margin, customer-supplied cost
   basis". Never gross margin (that is `erp_verified`, which this audit never has). Never net
   margin. Never margin on any revenue-only or CRM figure. Provider processing fees and payment
   fees are not cost of goods.
6. **Capacity.** At most two audits in flight, with starts at least four days apart. Hypothesis:
   25 to 35 hours per audit, so one audit consumes most of a focused week-and-a-half.
7. **No em dashes** in anything the customer reads.
8. **Human in the loop and audit trail** lead every conversation: we recommend, they decide, and
   every number traces to a formula in the method log.

## Gates before Day 0 (all must be true)

- [ ] Mutual NDA and data addendum signed (counsel-reviewed, entity formed). Not true today.
- [ ] Written amendment covering per-customer cost rollups and customer codes signed
      (F-audit-data-class in the offer). Not true today.
- [ ] Engagement letter signed and fee paid (F-audit-price decided by the founder).
- [ ] E&O and cyber insurance bound (security one-pager roadmap item 4).
- [ ] WIP check: fewer than two audits in flight.
- [ ] Benchmarking consent asked and recorded as yes or no (opt-in box, section 9). A no costs
      nothing and changes nothing.
- [ ] Method log file exists: `gtm/ai-margin-audit-method-log.md` (created at the first audit).

## Pre-clock: intake call (30 to 40 minutes)

Held after the offer is accepted and before data moves, or as the qualifying call before the
offer. Goal: confirm the audit is deliverable and agree the cost attribution method.

Agenda:

1. **Why now (5 min).** What triggered the question: a surprise provider bill, a board question,
   a pricing change in flight? Who else is involved?
2. **Pricing today (5 min).** Current plans, units, discounts. History: what changed and when.
   Planned move: flat or per-seat to usage or outcome? Who owns pricing decisions (name and
   role, written down).
3. **The manual workaround (3 min).** How do they reconcile provider bills to Stripe today?
   The honest answer sizes the audit.
4. **Cost attribution reality (10 min, the most important section).** Walk the decision tree in
   the data request. Do they have per-customer API keys, projects, or workspaces? App-side
   request logging with a customer id? Neither? Record the best available method (A, B, C, or D)
   and the expected confidence.
5. **Data readiness gates, adapted for the audit (5 min).** Billing history of 3 or more months
   and about 10 or more billed customers (hypothesis, adjustable). Cost attributable by one of
   methods A to C. A written pricing or discount policy, or an honest "no". A named decision
   owner. No usable data means no audit, and we say so now.
6. **Data handling (5 min).** Exports only, no keys, no prompts or outputs, customer codes not
   names. Walk the NDA and the amendment. Benchmarking consent: opt-in, off by default, cost
   data never included. Do not push it.
7. **Expectations (2 min).** 14 days from data receipt. A readout meeting on day 13. No
   guarantee of recovered revenue. They decide.

Two answers to have ready, because every CEO or CFO asks:

- **"Who else like us uses this?"** Honest answer: no verified peers yet. You would be one of the
  first audits. Nothing of yours is used for anyone else, and cost data can never join a
  benchmark. If we reach a cohort of consenting customers, you would see yourself against it
  at no extra charge, if you opted in. Do not claim customers we do not have.
- **"What happens to our data?"** Exports only, held in an encrypted, access-logged folder,
  processed by hand in a spreadsheet, never sent to a cloud AI service, never used to train a
  model or help another customer. Deleted within 30 days of the readout or sooner on request,
  with written certification.

Output of the call: a one-paragraph scoping note in the method log (no customer values), the
chosen attribution method, and the data request sent by the founder.

## Day-by-day plan

Day numbers count from Day 0 (data receipt). Skip no day; if a day is blocked, the log says why.

### Day 0: Receipt and register

- Save files to the customer folder. Hash or record file names and row counts only.
- Register the receipt in `docs/ops/data-register.md` Part B the same day.
- Start the clock only if the minimum viable set is present. If a file is missing, tell the
  founder to tell the customer what is missing, and the clock has not started.
- Open the method log entry for this audit (slug only).

### Day 1: Readiness check and data dictionary (go or no-go)

- Check each file against the data request: columns present, date ranges, currency, tax
  treatment, one row per expected grain. Headers only first, then row counts.
- Write a data dictionary tab in the workbook: each column, meaning, as stated by the customer.
- Test the join: do the customer codes match across billing, cost, and customer list? Count
  matched, unmatched, duplicated.
- Reconcile totals: invoiced revenue by month against any total the customer states; provider
  cost by month against the provider bill total. Record the coverage percentage of cost that is
  attributable to a customer.
- Decision by end of day: **go, go with limits, or stop.** "Go with limits" names which analyses
  are impossible (use the "impossible without" table in the data request). Founder tells the
  customer what is missing within one business day.

### Day 2: Clean revenue

- Build the customer-month revenue table from invoices: exclude tax, exclude one-time fees from
  recurring (flag them), subtract credit notes and refunds into a separate column, keep
  discounts visible. One currency per file, or stop and ask.
- Separate platform fee, usage, and overage where line items allow.
- Handle proration, mid-month starts, multiple subscriptions per customer, and annual
  prepayments by recognising revenue by month. Every treatment is a logged judgement call.
- Check: monthly total ties to the invoices total, within a stated tolerance.

### Day 3: Clean cost and attribute it

- Build the customer-month cost table by the agreed method:
  - **A. Direct** (per-customer key, project, or workspace): cost joins on the code.
  - **B. App-side rollup** (customer code, month, model, token counts, cost): validate token
    totals against the provider total.
  - **C. Allocated** (proportional to a stated driver such as requests, tokens, tasks, or
    storage bytes): driver must be a column in the data; label every row "allocated".
  - **D. Not attributable**: no per-customer cost. Switch to the plan-level view for the
    cost-floor questions and tell the customer the per-customer table cannot be produced.
- Add cloud and storage lines: attribute by storage volume per customer where given, otherwise
  allocate by a stated driver or hold as unallocated overhead. Never smear unallocated cost
  silently. Unallocated cost is its own line.
- Compute the **attribution coverage**: attributed cost divided by total provider and hosting
  cost. Below about 80 percent, the margin-health table carries a warning (threshold is a
  hypothesis to refine).
- Assign every customer an attribution confidence: direct, rolled up, allocated.

### Day 4: Analysis 1, per-customer revenue joined to cost

- Join revenue and cost by customer code and month. Compute contribution margin on the
  customer-supplied cost basis: revenue minus attributed cost, per customer-month and per
  customer over the window.
- Build the **margin-health table**: customer code, plan, months active, revenue, attributed
  cost, contribution margin, margin percent, attribution confidence, health band. Band
  thresholds are a logged judgement call (for example: negative, 0 to 30 percent, above 30
  percent; the founder sets them with the customer).
- Label every output with the ADR-006 string. No other use of the word margin.
- Double-check: recompute the total revenue and total cost through a second, independent method
  (for example a pivot against the formula tab) and require them to match.

### Day 5: Analysis 2, the heavy-user tail

- Rank customers by attributed cost per month. Compute share of total cost by decile, the
  cumulative curve, and the top-customer concentration.
- Compare cost rank to revenue rank: who is in the cost tail but the revenue middle.
- Compute usage per plan (tokens, requests, tasks): median, 90th and 99th percentile, and the
  multiple of median at the 99th. Flag the "token maxers".
- Note months with spikes (an agentic loop, a bulk job) versus sustained heavy use.

### Day 6: Analysis 3, negative-margin accounts and the cost floor

- List every customer with negative contribution margin over the window, and every one that is
  negative in the most recent three months.
- For each: plan, discount, usage pattern, attribution confidence, and what drives the gap
  (price too low, usage too high, discount, cost allocation).
- **Sensitivity:** recompute under an alternative allocation or driver and record whether the
  account stays negative. Accounts that flip are marked uncertain, not asserted.
- **Cost floor per plan:** cost per unit at the median and 90th percentile, and the usage level
  at which the plan price stops covering cost. State it as an arithmetic result on the declared
  cost basis, not a recommended price.
- Mid-point check with the founder: confirm that the story is coherent before building
  recommendations on it.

### Day 7: Checkpoint and clarifications

- Single batched list of questions to the customer (through the founder), covering anything that
  changes a number: unexplained spikes, a customer with a special deal, a free pilot, a cost
  that was one-off. Short call of 15 to 20 minutes if needed. No new data requests after day 7
  unless a gap blocks an analysis; the 14-day clock does not stop.
- Freeze the cost and revenue tables except for corrections. Log every correction.

### Day 8: Analysis 4, discount and packaging review

- Price book versus invoices: list price, invoiced price, discount and credit by customer and
  plan, concessions as a share of list.
- Plan fit: customers whose usage sits far above or below what their plan implies.
- **Predictability:** month-to-month bill variation by customer (coefficient of variation of
  monthly invoice, and largest month-over-month swing). Which customers would see a surprise
  bill under pure usage pricing, using their historical usage.
- Seat erosion check: if per-seat, how seat counts moved against usage over time.
- Discounts given to win early logos: when, how large, still in force.

### Day 9: Analysis 5, pilot-to-ARR conversion

- Classify each customer-month as pilot or recurring using the customer's flag, contract type,
  or term and price pattern. Unclear cases are marked "unclassified", never guessed.
- Compute: pilot revenue share, ended pilots, converted pilots, conversion rate, price change
  at conversion, time to conversion.
- Restate ARR with pilots separated (annualised recurring revenue from classified-recurring
  customers). Label it a hand-classified view and list every judgement call.
- If delivery effort per customer is available (support or forward-deployed hours), add an
  effort overlay and show the revenue per hour. If it is not, say the human-middleware question
  cannot be answered from the data.

### Day 10: Packaging options, value metric, and the qualitative bottlenecks

- Draft **one primary and two alternative packaging structures**. Typical building blocks: a
  platform fee, an included usage allowance, overage rates, a commit, a cap, a band, a
  per-outcome component. Pick the value metric that best tracks both customer value and cost,
  using the data (correlation of candidate units with cost) and the intake interview.
- **Static re-pricing table:** apply each structure to each customer's historical usage and
  show the revenue and contribution margin change per customer. Say plainly that it assumes
  customers behave as they did, and is not a forecast or an elasticity estimate.
- Variance and trust: from credit notes, refunds, churn reasons, and any eval or accuracy
  results the customer shared, summarise the commercial record of inconsistency. Mark it
  judgement where records are thin.
- Bundling exposure: from the intake call, the feature list, and the customer's own competitor
  notes, rate each feature as stand-alone add-on risk or workflow-owned. This is judgement, and
  the readout says so.

### Day 11: Write the readout and the method appendix

- Headline first, per the close script: one sentence on their numbers. Then the disclosure block
  (rows read per file, duplicates, unmatched codes, attribution coverage, excluded items) before
  any finding.
- Deliverables list from the offer: items 1 to 9 plus the appendix.
- The method appendix is generated from the method log: every formula, assumption, threshold,
  and judgement call, with the alternative considered.
- Mark each finding as one of: computed from data, computed under an assumption, judgement.

### Day 12: Quality gate and rehearsal

- **Triple-check the headline** from the raw files: re-run the headline number two ways and
  confirm the slide equals the spreadsheet. If we are wrong about our own headline, the thesis
  dies on this call.
- **Advisor sign-off** on the readout before it goes out, with synthetic or fully de-identified
  figures only if a third party reviews (per the close script, no real-data readout goes out
  without sign-off). Confirm the advisor review route is allowed under the NDA.
- Rehearse the top five accounts cold: code, plan, revenue, cost, margin on the declared basis,
  attribution confidence, the one-line driver.
- Prepare "what we would not change": the plans and customers that work. Without it the
  readout reads as an accusation.
- Check every use of the word margin against the ADR-006 label. Check for em dashes.

### Day 13: Readout meeting (60 minutes)

| Time | Segment |
|---|---|
| 0 to 3 | Headline sentence on their numbers, then the disclosure block |
| 3 to 20 | Margin-health table, heavy-user tail, the negative-margin accounts with receipts |
| 20 to 30 | Pilot-to-ARR view and the packaging diagnosis |
| 30 to 40 | The recommended structure and two alternatives, with the static re-pricing table and its limits |
| 40 to 50 | Questions, especially from finance. What we would not change |
| 50 to 60 | The close (below), with a date |

Say the caveats before they ask: historical and correlational, built on the cost basis they
supplied, not a forecast, not a recovery promise, their decision.

### Day 14: Deliver and close

- Founder sends the written PDF and the method appendix. Nothing is sent by anyone else.
- Offer deletion now: "Say the word and I certify deletion this week." Default is within 30 days.
- Close conversation, adapting `gtm/readout-close-script.md`:
  - Keep: their numbers carry the call; the trap-check question ("If you had caught these
    accounts before they renewed or before this packaging was set, what would that have been
    worth?"); the three stall replies; "never end on think it over"; the same-day decision-log
    entry and five-line recap.
  - Replace: the $15K, 90-day Salesforce pilot sentence and the 20-deals usage criterion do not
    apply. No product exists yet for the margin wedge, and margin computation in the product is
    still an open founder decision. The next step offered is a founder decision
    (F-audit-followon): for example a re-run on the next quarter's exports, help implementing
    the packaging, or a seat on the design-partner list for the product. Do not price or promise
    a product that has not been built.
  - Keep the honest sentence: "The audit is a rear-view mirror on your data. What it cannot tell
    you is how your customers react to a new price."
- Log: decision, date of next step, and the willingness-to-pay data point (price tested,
  accept or decline, stated reason).

## What to capture for the product

Everything done by hand becomes the specification for the software. The **method log** is
`gtm/ai-margin-audit-method-log.md`. It is created at the first audit and lives in the repo, so it
must hold **no customer data**: no names, codes, amounts, or counts that identify a customer.
Examples in it use synthetic values. Real values stay in the customer folder only.

One entry per formula or judgement call, with these fields:

| Field | Content |
|---|---|
| ID | ML-001, ML-002, and so on |
| Date and audit slug | Slug only |
| Step | Day and analysis (for example Day 3, cost attribution) |
| Rule in words | What was done and why |
| Formula | Spreadsheet formula in generic form, with named ranges, not cell references to real data |
| Inputs | Columns required (names only) |
| Judgement call | The decision a person made that code cannot make without a rule |
| Alternative considered | And why rejected |
| Sensitivity | How much the result moved under the alternative, as a percentage, not as values |
| Basis label | `declared_cost`, or revenue-only |
| Time taken | Minutes, to find what to automate first |
| Candidate software function | Name of the future function, and which hand step it replaces |
| Failure or surprise | What went wrong, what the data looked like |

Also capture after each audit, in the same log, under a "Learnings" heading, with no customer
values: which data requests the customer could not meet, which attribution method was used and
its confidence, how long each day took against the plan, which findings the customer
challenged, and the price tested and the response.

Engineering reads the log to decide what to build first. The likely first candidates: join and
reconcile, cost attribution, customer-month margin table, tail concentration, packaging
re-pricing table. This is a hypothesis; the log decides.

Do not add margin computation to the product until founder decision D2 is settled. The log
informs D2; it does not pre-empt it.

## Risks specific to doing this by hand

- A formula error you cannot see. Mitigation: second independent method for every total, and the
  Day 12 headline check.
- Scope creep: customers will ask for "one more cut". The clock and the deliverables list are
  the answer. Extra cuts are the follow-on.
- Attribution overclaim: an allocated cost presented as measured. Mitigation: confidence column
  on every row and the coverage figure in the disclosure block.
- Leaking customer data into the repo or an LLM. Mitigation: ground rules 2 and 3, and the method
  log rule above.
- Founder time: an audit in flight displaces the 10 to 15 problem interviews. Mitigation: two-audit
  cap and spaced starts.

## Related

[[ai-margin-audit-offer]] · [[ai-margin-audit-data-request]] · [[readout-close-script]] ·
[[2026-11-10-audit-first-motion-and-ai-margin-wedge]] · `docs/ops/data-register.md` ·
`docs/ops/data-handling-sop.md` · `docs/legal/one-page-mutual-nda-data-addendum.md`
