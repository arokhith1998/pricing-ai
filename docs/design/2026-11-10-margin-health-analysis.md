---
title: Margin-health analysis on declared cost, engine design
created: 2026-11-10
updated: 2026-11-10
status: draft
tags: [design, spec, ai-margin, billing, declared-cost, adr-006]
source: "Founder instruction 2026-11-10 (audit-first motion and AI margin wedge); drafted by backend-engineer for founder approval"
related:
  - "[[2026-11-10-audit-first-motion-and-ai-margin-wedge]]"
  - "[[2026-11-09-native-connectors-hubspot-stripe-chargebee]]"
  - "[[2026-11-06-platform-agnostic-intake-and-usage-native-guidance]]"
  - "[[2026-11-07-contract-structure-lens-spec]]"
---

# Margin-health analysis on declared cost, engine design

Decision record: `vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md` (decided item 2: per-customer revenue from billing joined to per-customer inference and storage cost gives a margin-health readout, on `declared_cost` or `erp_verified`, never on `crm_proxy`). Founder thesis: `gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md`, Consumer Trends bottleneck 1 (cost floor, negative-margin trap, cost-plus dilemma) and bottleneck 2 (packaging, predictability), and Opportunity move 1 (the audit promise to "identify where tokens and churn are eroding your gross margins"). The sheet's figures (storage 5 to 50 percent of COGS, $1.60 to $3.00 lost per dollar) are the founder's synthesis, not evidence. No threshold below is derived from them.

Sources read for this spec, as they stood on 2026-11-10: `pricing/billing.py`, `pricing/schema.py`, `pricing/mapping.py`, `pricing/cost_basis.py` and `pricing/generate_billing.py` from `origin/main` at 4f6f33b (PR 93 merged; the working branch predates it); ADR-006 in `docs/agents/DECISIONS.md`; the connector design doc sections 4 to 6; the lens spec for house style; `docs/agents/OWNERSHIP.md`; `python tools/agentctl.py status` at 2026-11-10T22:51Z (no task in progress).

## 1. Purpose, scope and binding rules

Join what each customer paid (billing grain) to what each customer cost to serve (a founder-supplied cost export), and answer, per customer and for the book: who loses money, how heavy usage turns a flat price negative, what it costs to serve one unit of the vendor's value metric, whether price is merely tracking falling model cost, and whether storage is taking over cost.

Binding rules:

1. **Label.** Every figure that is a revenue-less-cost result carries the ADR-006 label built by `pricing/cost_basis.py` (`label_for`, `weakest_basis`, `refuse_margin_for_proxy`). No label text is written in `pricing/margin.py`. On `declared_cost` the label is "contribution margin, customer-supplied cost basis". The words "gross margin" appear only on `erp_verified`; a test asserts it. This differs from the audit promise's "gross margins": the export covers only the cost lines the founder supplied, so it is not full COGS, and ADR-006 already fixed the wording. The audit one-pager may keep its service language; engine output may not.
2. **Cost basis is set by code, never by the file.** Every row of a `cost_export` is `declared_cost`, set by the endpoint after the caller confirms the declaration ("these figures are my own export"). `erp_verified` is reserved for a connector Pricekeel operates; a `cost_basis` cell holding `erp_verified` in an uploaded file is a 422 `SchemaError`, the same trust boundary `ingest` enforces. A cell holding `crm_proxy`, or no declaration, makes the basis `crm_proxy`, and the margin-bearing metrics refuse (section 4.2).
3. **Never zero.** A cost that is absent is not a zero cost. An account with revenue and no cost rows is excluded and counted, never reported at 100 percent. A blank cell, a missing column and a missing period are each "not in the file", with a count and, where money is involved, the dollars.
4. **No win rate.** This analysis reads the billing grain and the cost grain only. It produces no deal row, sets no `outcome`, and returns the billing readout's win-rate line as `not_provided`.
5. **Describe, never set.** No output sets, recommends or optimizes a price. Anything price-affecting stays a human decision in the decision log.
6. **Deterministic.** No LLM computes, maps or narrates any figure. Money is `Decimal`; ratios are rounded half-up to 4 places; sums are exact.
7. **Commit, ramp, overage.** The unit metrics split revenue into a fixed part (platform fee, commit, seats) and a metered part (`usage_amount`), because a flat or committed price against metered cost is where the loss comes from (section 4.5). A seat-only view would miss it.
8. **No em dashes** in any generated text.

Out of scope for v1, each named so nobody assumes it: FX conversion between currencies; pro-rating a cost line across billing periods; reading request-level usage events (NDA Class 2 stays: rollups only); churn (the audit promise says "tokens and churn"; this analysis covers tokens, cloud and storage only, and churn stays with the realization and contracted-versus-billed levers); a bundled model-price history; net margin of any kind; the web readout component; a per-tenant snapshot of margin aggregates (decision D1 applies later).

## 2. Inputs

### 2.1 Revenue: the billing grain

Source: `contract_period_actuals`, `pricing/schema.py` `CONTRACT_PERIOD_FIELDS`, cleaned by the same routine `pricing/billing.py` uses (`_clean_periods`, `_whole_months`). Fields read:

| Field | Use |
|---|---|
| `source_record_id` | the account key. The grain carries no end-customer id by design (`billing.py` docstring), so "customer" in this spec means one subscription or contract unless the caller supplies a crosswalk (section 2.3) |
| `period_start`, `period_end` | the billing period, whole calendar months only (section 3.1) |
| `currency` | must equal the cost currency (section 3.3) |
| `invoiced_amount` | revenue R: after discounts and credits, tax excluded |
| `usage_units` | units U in the vendor's value metric, an invoice-line rollup |
| `usage_amount` | the metered part V of R. The fixed part is F = R minus V |

`list_amount`, `discount_amount`, `credit_amount` and `committed_amount` are not read. A blank `usage_units` or `usage_amount` makes the unit metrics for that period "not in the file"; it is never read as 0. If the `usage_units` column is absent, every unit metric is `not_provided` with reason `usage_units_column_not_in_file`, and the readout says "Excludes usage units: not in the file."

Value-metric unit label: the request carries `value_metric_unit` (free text such as "credit" or "1K tokens", the same meaning as the schema field). Absent, sentences say "unit" and the readout says "Excludes the unit label: not in the file."

### 2.2 Cost: the founder-supplied cost export

A cost export is one or more CSV files of cost lines, sent as one or several parts. It becomes a third in-memory grain, `cost_period_actuals`, defined like the billing grain: its own field list (`COST_PERIOD_FIELDS`, data-engineer, `pricing/schema.py`), not in `FIELDS` or `ALL_COLUMNS`, so deal files, the mapper's deal fields, the pinned `data/synthetic/deals.csv` and `gtm/data-request.md` are unchanged.

| Field | dtype | Meaning |
|---|---|---|
| `cost_vendor` | str | who billed it: `openai`, `anthropic`, `aws`, free text. Display and de-duplication only |
| `cost_category` | enum | `inference`, `compute`, `storage`, `other`. Blank is `uncategorized`. Set from a user-confirmed table (header or line-item value to category); never guessed |
| `cost_line` | str | the line dimension that makes a row unique within a day: model, `line_item`, `description`, product code |
| `customer_key` | str | the attribution key as exported (section 2.3) |
| `customer_key_type` | enum | `source_record_id`, `api_key_id`, `project_id`, `workspace_id`, `customer_tag` |
| `cost_start`, `cost_end` | date | the day or range the line covers, end inclusive. Daily rows have start equal to end |
| `cost_currency` | str | ISO 4217, upper-cased on read ("usd" becomes "USD") |
| `cost_amount` | Decimal | cost for the range, in `cost_currency`, at source precision (fractions of a cent kept, rounded half-up to the cent only on output) |
| `cost_basis` | enum, optional | exact-only. `declared_cost` or absent in an upload; see rule 2 |

Tokens are not dollars. Both providers report tokens in their usage endpoints and dollars in their cost endpoints, and the two have different attribution dimensions. v1 reads dollars. A tokens-times-rate-card path is specified as an optional task (section 8, MH-10) and is what `declared_cost` means in the ADR's own words: "a cost rate or percentage table the customer typed or supplied in writing". Without it, a usage export with tokens and no dollar column is `not_provided` with reason `cost_amount_column_not_in_file`.

**Provider exports as they exist today.** Retrieved 2026-11-10. Neither vendor documents a CSV in the pages below; both document a JSON API, and the CSV a founder holds is a flattening of those fields (Anthropic's page lists "CSV export: Generate reports for finance teams" as a use case built on the API). The dashboard export header names were not verifiable from public documentation on this date. MH-3 therefore captures the real headers from a founder-supplied sample (headers only, no rows) before any preset ships, and this section is corrected from that sample. OpenAI's platform documentation (`platform.openai.com`) returned HTTP 403 to automated retrieval on 2026-11-10; the OpenAI fields below come from the OpenAI Cookbook page, which prints live response bodies.

| Vendor and export | Fields | Dollar column | Attribution dimension |
|---|---|---|---|
| OpenAI Completions Usage API (`/v1/organization/usage/completions`) | `start_time`, `end_time` (Unix seconds), `input_tokens`, `output_tokens`, `input_cached_tokens`, `input_audio_tokens`, `output_audio_tokens`, `num_model_requests`, `project_id`, `user_id`, `api_key_id`, `model`, `batch`. `bucket_width` 1m, 1h or 1d | none, tokens only | `project_id`, `api_key_id`, `user_id`, `model` |
| OpenAI Costs API (`/v1/organization/costs`) | `start_time`, `end_time`, `amount.value` (a float, for example 0.1308), `amount.currency` (lowercase `usd`), `line_item`, `project_id`, `organization_id`. 1d only | `amount.value` | `project_id`, `line_item` |
| Anthropic usage report (`/v1/organizations/usage_report/messages`) | `starting_at`, `ending_at`, `uncached_input_tokens`, `cache_creation.ephemeral_1h_input_tokens`, `cache_creation.ephemeral_5m_input_tokens`, `cache_read_input_tokens`, `output_tokens`, `server_tool_use.web_search_requests`, `model`, `service_tier`, `speed`, `context_window`, `inference_geo`, `api_key_id`, `workspace_id`, `account_id`, `service_account_id`. 1m, 1h or 1d | none, tokens only | `api_key_id`, `workspace_id`, `model` |
| Anthropic cost report (`/v1/organizations/cost_report`) | `starting_at`, `ending_at`, `amount` (a decimal string), `currency` (`USD`), `cost_type`, `token_type`, `description`, `model`, `service_tier`, `speed`, `context_window`, `inference_geo`, `workspace_id`. 1d only. Group by `workspace_id` or `description` only | `amount`, **in cents, not dollars** | `workspace_id` |

URLs, all retrieved 2026-11-10: `https://platform.claude.com/docs/en/api/usage-cost-api` (legacy endpoints; states the cost report is USD "in lowest units (cents)", daily only, Priority Tier excluded, the default workspace has `workspace_id` null, Playground usage has `api_key_id` null); `https://platform.claude.com/docs/en/api/admin/usage_report/retrieve_messages`; `https://platform.claude.com/docs/en/api/admin/cost_report/retrieve`; `https://cookbook.openai.com/examples/completions_usage_api`. The Anthropic page says new integrations should use the Usage and Cost Analytics API, which groups by more dimensions (it names `actor`, and `api_key_id` on cost); its field list was not retrieved, so it is a follow-up and not an input of this spec.

Three consequences that shape the design:

1. **No end-customer field exists in either vendor's usage or cost output.** Neither the OpenAI nor the Anthropic response bodies above carry request metadata. Per-customer attribution is possible only when the founder gave each customer its own project, workspace or API key (the crosswalk case), or exports from their own gateway or application log, where a customer tag exists (`customer_tag`). Everything else is shared cost.
2. **Anthropic cost amounts are cents.** A preset that reads `amount` as dollars overstates cost 100 times and turns most accounts negative. The `anthropic_cost_report` preset applies a unit scale of 0.01, the caller must confirm "amounts are in cents" in the same step that confirms the cost basis, the response echoes the scale, and a test plants the 100-times error (section 7). OpenAI's `amount.value` is read as dollars because `amount.currency` is `usd`; MH-3 confirms this on a real sample.
3. **Daily buckets.** Both providers' cost endpoints are daily only. Cloud and storage lines usually arrive monthly. Section 3.1 says what happens to each.

Cloud and storage cost lines (AWS, GCP, Azure, a vector store, object storage) come as the founder's own export or a typed table. They enter with `cost_category` `compute` or `storage` and, if the founder can tag by customer, a `customer_key`; otherwise they are shared cost.

### 2.3 Attribution: from a cost line to an account

A cost line reaches an account in exactly one of three ways, recorded per line in the output as `attribution`:

- `direct`: `customer_key_type` is `source_record_id` and the key equals a billing account, or the key is in a **crosswalk** the caller confirmed: rows of `{customer_key_type, customer_key, source_record_id}`. Several keys may map to one account. One key mapping to two accounts is rejected (422, `crosswalk_key_not_unique`); that is an allocation, not an attribution.
- `allocated`: the line belongs to a **pool** the caller confirmed an allocation rule for (section 2.4).
- `not_attributable`: everything else, including a key with no crosswalk entry, a blank key, a key whose account has no billing rows, and any pool with no confirmed rule. It is never dropped and never spread: its rows and dollars are disclosed, and it stays in book-level cost totals and in the storage-share metric (section 4.9), which need no attribution.

Absent attribution is the common case for an audit, and the readout states it plainly (sentence S04) rather than papering over it.

### 2.4 Allocation: only with a rule the user confirms

An **allocation rule** is confirmed per pool. A pool is a filter over not-yet-attributed lines: any of `cost_category`, `cost_vendor`, `cost_line`, and always the attribution status `not_attributable`. A rule is one of:

| Rule id | Driver | Note |
|---|---|---|
| `proportional_to_usage_units` | the account's `usage_units` in the same billing period | an account with blank units gets no share and is counted |
| `proportional_to_invoiced_amount` | the account's `invoiced_amount` in the same billing period | never a default. It gives every account the same result on that pool by construction, so it hides the heavy-user signal the analysis exists to find. Permitted only when the caller confirms it by id, and the readout says so (S05b) |

A rule is `{pool, rule, confirmed: true, confirmed_by, confirmed_at}`. `confirmed` absent or false is treated as no rule. The engine never infers a rule, never applies one to a pool it was not confirmed for, and never carries a rule across files.

Mechanics, so results are exact: the pool total for a billing period is split by the driver in `Decimal`, each share rounded half-up to the cent, and the remaining cents are given one at a time to the largest fractional remainders, ties broken by `source_record_id` ascending. The allocated cents of a pool in a period always sum to the pool's cents exactly (a property test, section 7). Example: 1,000.00 over three accounts with equal units gives 333.34, 333.33, 333.33, the extra cent to the lowest id. A pool whose driver sums to zero or is missing for the period stays `not_attributable` for that period, with reason `allocation_driver_missing`.

Why direct and allocated stay visible: allocated cost carries no per-customer information beyond the driver. A pool allocated by usage units gives every account the same cost per unit on that pool. So every account-level result reports `allocated_share` of its cost, and the book-level readout reports the allocated share of all cost, with sentence S05 at or above `ALLOCATED_SHARE_CAUTION` of 0.30.

### 2.5 Mapping profile `cost_export`

New profile in `pricing/mapping.py` (ai-engineer): `PROFILE_COST = "cost_export"`, grain `cost_line`. It is a profile, not a new deal field set: the profile's roles feed the `cost_period_actuals` fields, and no deal field is claimed.

**Fingerprint** (header-only and deterministic, like `_billing_fingerprint`; no row value, no LLM). It fires only when all three hold:

1. **A cost-amount header:** a header with token `cost`, `spend`, `charge` or `unblended`, or the provider shape `amount` beside `currency` together with at least one of `line_item`, `cost_type`, `token_type`, `description`.
2. **A cost dimension:** a header with token `model`, `project`, `workspace`, `key` (as in api key), `service`, `product`, `line item`, `resource`, `input tokens`, `output tokens`, or `requests`.
3. **No CRM or billing veto:** no opportunity id, no stage header, and `_billing_fingerprint` is false (a subscription id beside an interval, plan, MRR or period header, or an invoice number or amount-due header, is a billing file).

A bare `Amount` beside `Stage`, `Customer` or `Account` never fires it: Salesforce and HubSpot both export `Amount` on every opportunity. A file that fires both the billing and the cost fingerprint is `unknown`, with reason `ambiguous_billing_and_cost`, and the caller must say which it is.

**Outcome refusal.** `outcome_refusal` gains a branch: a `cost_export` profile has no outcome and is refused with reason `cost_export_not_a_deal_file` and the message "This is a cost export. It cannot supply deal outcome. Send it to the margin analysis." Layer 4 (the LLM fallback) is not run for a cost export, as it is not run for billing-state headers. `ingest.py` refuses a cost-export profile on the deal path with the same reason, so a cost file can never be scored as deals.

**Exact-only fields** (`COST_EXACT_ONLY_FIELDS`, same mechanism and same reason as `EXACT_ONLY_FIELDS`: bare words collide with real columns): `customer_key` ("Customer", "Account" and "Project" are different things, and mapping a provider project to a customer is an attribution decision a person confirms, never a fuzzy match), `customer_key_type`, `cost_amount` (bare "Amount"), `cost_category` (set by the confirmed table in 2.2), `cost_basis` (already exact-only), `source_record_id` (already exact-only).

**Presets** (header sets recognised exactly, each with a unit scale and currency rule that the caller confirms): `openai_costs`, `anthropic_cost_report` (scale 0.01), `generic_cost_lines`. Usage-only presets (`openai_completions_usage`, `anthropic_usage_report`) are recognised so the refusal can say "this export has tokens and no dollars; add a rate card or the cost export".

### 2.6 How the cost basis label is set

1. Parse and map. A `cost_basis` column, if present, may hold only `declared_cost`; `erp_verified` is a 422; any other value makes the row `crm_proxy`.
2. The caller sets `cost_basis_declared: true` and `declared_by` in the confirmation. Then every cost row is `declared_cost`.
3. `weakest_basis(rows)` decides the response basis. One `crm_proxy` row makes the whole readout `crm_proxy`. `label_for(basis)` builds the label; `margin_violations(text, basis)` runs over the whole serialized response in a test.
4. `erp_verified` is not produced here. A future connector that reads cost from a billing or ERP system Pricekeel operates sets it on its own path, and `weakest_basis` keeps a mixed book at `declared_cost`.

## 3. Grain and joins

### 3.1 Aligning cost periods to billing periods

The unit of analysis is the **aligned account-period**: one account, one billing period, with the cost rows that fall inside it. It exists only when all of these hold; the first failing condition decides the exclusion and is counted with its reason:

| Order | Condition | Reason code when it fails |
|---|---|---|
| 1 | the account's revenue rows survive `_clean_periods` (identical repeats collapsed; differing rows for one period, or overlapping periods, are conflicts excluded with a count, never first-row-wins) | `period_billing_conflict` |
| 2 | `invoiced_amount` present and not negative (a refund is `invalid_money_value`, left out, as in realization) | `revenue_blank`, `invalid_money_value` |
| 3 | the period is a whole number of calendar months by `billing._whole_months` (Jan 1 to Jan 31, Jan 15 to Feb 14). A weekly period, a prorated stub or an odd interval is left out and counted, never rounded to a month | `period_not_whole_months` |
| 4 | the period lies wholly inside the cost file's coverage: from the earliest `cost_start` to the latest `cost_end` over valid cost rows. A billing period that starts before the cost file begins or ends after it ends cannot be judged, because missing cost would read as zero | `period_outside_cost_coverage` |
| 5 | at least one attributed cost row (direct or allocated) lands inside the period for this account | `period_no_cost_rows` |
| 6 | the cost currency of those rows equals the billing currency (section 3.3) | `period_currency_mismatch` |

The whole-month rule is reused unchanged, for the reason `billing.py` states: day-based scaling would move the exact answer for monthly books. A period of N whole months is divided by N only where a per-month figure is needed (usage per month, break-even); dollar results are per period, as in the billing grain.

**Cost rows to periods, containment only.** A cost row belongs to a billing period when its whole `[cost_start, cost_end]` lies inside the period. Nothing is pro-rated.

- **Daily cost, monthly billing** (the provider case): each daily row falls inside exactly one billing period, including periods anchored mid-month (Jan 15 to Feb 14), because the check is on the row's date, not the calendar month. Rows are summed into the period. This is the supported path.
- **Monthly cost, calendar-month, against billing anchored on the 1st:** contained, supported.
- **Monthly cost against billing anchored mid-month, or any cost row spanning two billing periods:** the row straddles; it is excluded and counted with its dollars as `cost_straddles_periods`, and the readout says so (S80). It is not split by days and not assigned to the larger half. A majority-of-days assignment would be a declared rule like an allocation rule, and it is deferred until a partner file needs it.
- **A cost row outside every aligned period of its account** (before the first invoice, after the last, or in a conflicted or non-whole-month period) is excluded as `cost_outside_billing_periods`, counted with dollars. It stays in book-level cost totals.

**Cost-row hygiene**, in this order, each counted with dollars: a row missing a date or with `cost_end` before `cost_start` (`cost_missing_date`); a `cost_amount` present but not a number ("1,200", "$100": `cost_unparseable_amount`, never read as blank); a blank `cost_amount` cell (`cost_blank_amount`, never 0); a negative `cost_amount` such as a vendor credit (`cost_negative_amount`, left out until a person confirms credits are in scope; a conservative v1 choice); identical rows (same vendor, category, line, key, range, currency and amount) collapse to one (`cost_duplicate_collapsed`, which catches overlapping export pulls); rows with the same vendor, category, line, key, range and currency but different amounts are a conflict and both are excluded (`cost_conflict`). Daily provider rows are unique at vendor, line, key and day, so a legitimate second row with those fields identical does not occur.

### 3.2 Whole-book coverage disclosures

`scope` and `exclusions` in the response list: billing accounts; accounts with at least one aligned account-period; accounts with revenue and no cost rows (`cost_not_in_file`, shown as a count and their revenue dollars, never as a result); cost dollars that reached an aligned period; cost dollars by exclusion reason; and the cost file's date range.

### 3.3 Currency

Billing is one currency per row, and `billing.py` sums nothing across currencies. Cost carries `cost_currency`. A cost row reaches an aligned period only when its currency equals that period's billing currency; otherwise the account-period is excluded as `period_currency_mismatch` and its cost and revenue dollars are counted. No conversion is applied in v1, so a EUR-billed customer against USD provider cost is excluded and disclosed, not converted with a rate we chose. Section 8 lists a declared-FX option as deferred. A book-level metric (cost per unit, storage share, cost-plus) is computed within one currency: the book currency is the billing currency with the most aligned account-periods, other currencies are listed with counts, and nothing is summed across them. If two currencies tie, the metric is `not_provided` with reason `currency_tie`, never a pick.

## 4. Metrics

### 4.1 Notation and constants

For one aligned account-period: R = `invoiced_amount`; C = direct cost plus allocated cost, summed at source precision; U = `usage_units`; V = `usage_amount`; F = R minus V; N = whole months in the period. For an account, sums are over its aligned account-periods that have the needed fields.

| Constant | Value | Reason |
|---|---|---|
| `MARGIN_MIN_ACCOUNTS` | 15 | book-level shares, p50 and dispersion; mirrors `CONTRACT_LENS_MIN_SCORED` and the 15-deal band floor in `metrics.reference_discount` |
| `MARGIN_MIN_ACCOUNTS_P90` | 20 | a 90th percentile from 15 points rests on one observation above it; 20 gives at least two |
| `MARGIN_MIN_COHORT` | 3 | accounts in a usage cohort |
| `BREAKEVEN_MIN_PERIODS` | 3 | aligned periods with units, metered amount and cost for one account's break-even |
| `TREND_MIN_PERIODS` | 6 | monthly buckets for any trend; equals `billing.MIN_USAGE_PERIODS`, a test pins equality |
| `TREND_MIN_ACCOUNTS` | 5 | accounts in a monthly bucket for the bucket to count |
| `COHORT_HALF_WIDTH` | 10 | percentile points either side of q |
| `NEAR_BREAKEVEN_HEADROOM` | 1.25 | an account within 25 percent of its break-even usage |
| `UNATTRIBUTED_SHARE_CAP` | 0.20 | founder decision 2 (section 9) |
| `ALLOCATED_SHARE_CAUTION` | 0.30 | allocated share at or above which sentence S05 appears |
| `UNCATEGORIZED_MAX` | 0.10 | uncategorized share of cost above which the storage share is not stated |
| `MOVE_LINE` | 0.10 | a change of 10 percent counts as a move (cost-plus check) |
| `MARKUP_BAND` | 0.05 | a markup change inside plus or minus 5 percent counts as held |
| `STORAGE_SHIFT_POINTS` | 0.05 | a storage share change of 5 points counts as a shift |

All are policy starting points, not estimates from data, and tenant-configurable in the request. The lens spec's caveat applies: calibrate against the partner's book rather than setting thresholds maximally strict.

Every metric returns the billing-lever shape `{method, status, reasons, values}` with status `scored | insufficient_data | not_provided`, no global fallback, and `method` a fixed string. Percentile means **nearest rank**: for n sorted values, the q-th percentile is the value at position ceil(q/100 times n), no interpolation.

### 4.2 Metric ids and the margin-word rule

Metric ids carry no affirmative margin wording so that the word guard can scan keys and values together: `account_result`, `usage_cohorts`, `break_even_usage`, `negative_accounts`, `cost_per_unit`, `cost_plus_check`, `storage_share`. `account_result`, `usage_cohorts`, `break_even_usage`, `negative_accounts` and `cost_plus_check` are **basis-bearing**: they relate revenue to cost, so they require `declared_cost` or `erp_verified`. Under `crm_proxy` they return `not_provided` with reason `cost_basis_not_declared` through `refuse_margin_for_proxy`, and no figure is computed and caveated. `cost_per_unit` and `storage_share` are cost-only and run on any basis, carrying the proxy label.

### 4.3 M1 `account_result`: result per customer per period

Method string: `billing revenue less declared cost`. Displayed with the ADR-006 label, which on `declared_cost` is "contribution margin, customer-supplied cost basis".

```
result          = R - C                          (Decimal, cents)
result_pct      = round(result / R, 4)           only when R > 0, else null with reason zero_revenue
allocated_share = allocated cost / C             null when C = 0
```

Per account over all its aligned periods: sums of R and C, and the same two ratios. A period with R = 0 (a 100-percent coupon month, a trial) and C > 0 is kept: the dollar result is minus C, and the percentage is null with `zero_revenue`. It is never infinite and never 0 percent.

Exclusions: the aligned-period conditions of section 3.1, plus any account with revenue and no cost rows (`cost_not_in_file`, listed, not scored).

States, per account: `scored` when at least one aligned period exists; `not_provided` with `cost_not_in_file` when the account has revenue and no cost rows inside cost coverage; `not_provided` with the first period exclusion otherwise. Book level (`values.book`): totals of R and C over scored accounts, pooled result percentage (sum of results over sum of R, not a mean of ratios), counts by exclusion. The book percentage is stated when scored accounts number at least `MARGIN_MIN_ACCOUNTS`; below that the totals are listed and no percentage is given (S21).

Worked example. Account A: flat fee 3,000.00, no metered amount, 2,000,000 units, cost 8,000.00 in one period: result minus 5,000.00, result_pct minus 1.6667.

### 4.4 M2 `usage_cohorts`: result at p50 and p90 of usage

Method string: `pooled result by usage cohort`.

Account usage is units per month: the sum of U over the account's aligned periods that have U, divided by the sum of their N. An account with no period carrying U is excluded (`usage_units_blank`, counted). Rank accounts by usage per month. For q in {50, 90}: the **usage at q** is the nearest-rank value; the **cohort at q** is every account whose percentile rank lies in [q minus 10, q plus 10], clipped to [0, 100] (so the p90 cohort is ranks 80 to 100). Cohort result = (sum of R minus sum of C) / sum of R over the cohort's aligned periods, pooled. Values: usage at q, cohort size, sum R, sum C, cohort result_pct.

A cohort is used because a single account at an exact percentile is noise. The window is an interpretable choice, not a fit.

States: needs the `usage_units` column (else `not_provided`, `usage_units_column_not_in_file`); at least `MARGIN_MIN_ACCOUNTS` accounts with usage and cost for p50 and `MARGIN_MIN_ACCOUNTS_P90` for p90; each cohort at least `MARGIN_MIN_COHORT` accounts. Otherwise `insufficient_data` with the counts (S41, S42). A cohort whose sum R is 0 has percentage null, reason `zero_revenue`.

### 4.5 M3 `break_even_usage`: the heavy-user break-even

Method string: `linear unit cost, fixed plus metered revenue`.

The question: at what usage does this account's revenue stop covering its cost, given how it is priced. Revenue is split into the fixed part F (platform fee, commit, seats: the part that does not move with units) and the metered part V. Using the account's totals over aligned periods with U, V and C all present, and months M = sum of N:

```
p  = V / U          effective price per unit
c  = C / U          observed cost per unit
Fm = F / M          fixed revenue per month
um = U / M          observed usage per month
result per month at usage u = Fm + (p - c) * u         (linear; equals the observed result at u = um, a property test)
break-even u* = Fm / (c - p)        when c > p and Fm > 0
headroom      = u* / um
```

Account states and reasons, in order:

| Order | Condition | Status | Reason |
|---|---|---|---|
| 1 | `usage_units` or `usage_amount` column absent | not_provided | `usage_units_column_not_in_file`, `usage_amount_column_not_in_file` |
| 2 | account has fewer than `BREAKEVEN_MIN_PERIODS` aligned periods carrying U, V and C | insufficient_data | `fewer_than_3_periods` |
| 3 | U = 0 over those periods | insufficient_data | `zero_usage_units` (cost per unit is undefined, never 0) |
| 4 | F < 0 (metered amount above invoiced) | insufficient_data | `invalid_money_value` |
| 5 | c <= p | scored, `shape: price_above_cost` | no break-even: every extra unit adds result |
| 6 | c > p and Fm = 0 | scored, `shape: negative_at_any_usage` | no positive usage covers cost |
| 7 | c > p and Fm > 0 | scored, `shape: break_even`, `u*`, `headroom` | headroom below 1 means the account is already past break-even |

Book level: counts of accounts past break-even (headroom below 1), near it (headroom from 1 up to 1.25), `price_above_cost`, and `negative_at_any_usage`. Shares are stated only when at least `MARGIN_MIN_ACCOUNTS` accounts are scored; otherwise counts and the list only. No book-wide break-even number is produced: the accounts differ in fixed fee, and a pooled u* would be a blend that matches no contract.

Limits stated in the readout (S34) and in `values.assumptions`: cost is assumed proportional to units at the account's observed cost per unit, so cost that does not scale with units (a fixed hosting fee inside C) is treated as variable.

Worked examples. A (flat): F 3,000.00, V 0, U 2,000,000, C 8,000.00 in one month: c 0.004, p 0, u* = 3,000 / 0.004 = 750,000, headroom 0.375, past break-even. B (hybrid): R 2,000.00, V 1,000.00, U 100,000, C 400.00: p 0.01, c 0.004, `price_above_cost`, result 1,600.00. C (hybrid, thin): R 1,000.00, V 600.00, U 100,000, C 800.00: F 400.00, p 0.006, c 0.008, u* = 400 / 0.002 = 200,000, headroom 2.0, result 200.00 (check: 400 plus (0.006 minus 0.008) times 100,000).

### 4.6 M4 `negative_accounts`

Method string: `accounts whose declared cost exceeds revenue`.

An account is negative when, over its aligned periods, the sum of C exceeds the sum of R. Per account also: `negative_period_count` of its aligned periods, and `persistent` when it has at least 3 aligned periods and all are negative. Book values: `n_scored` accounts; `count` negative; `share_of_accounts` = count / n_scored; `share_of_revenue` = sum R of negative accounts / sum R of scored accounts; `share_of_cost` = sum C of negative accounts / sum C of scored accounts; `shortfall` = sum of (C minus R) over negative accounts.

Exclusions: as M1. Never-zero: if the sum of R over scored accounts is 0, `share_of_revenue` is `not_provided` (reason `zero_revenue`); if the sum of C is 0, `share_of_cost` likewise. A zero-revenue account with positive cost is negative and is counted, flagged `zero_revenue_account`.

Minimums: the count, the list and the shortfall are stated for any number of scored accounts, with the count of scored accounts beside them. The three shares are stated only at `MARGIN_MIN_ACCOUNTS` scored accounts or more (S21).

Missing-cost bias, which drives founder decision 2: leaving cost out can only raise an account's result, so a negative finding survives complete attribution and can only get worse, while a healthy finding may not survive it. That asymmetry is why sentence S06 and the `upper_bound` state exist.

Worked example, accounts A, B, C above: A is negative. Share of revenue 3,000 / 6,000 = 0.5; share of cost 8,000 / 9,200 = 0.8696; shortfall 5,000.00. Three accounts is below 15, so the real readout would list them without the shares.

### 4.7 M5 `cost_per_unit`: cost to serve one unit of the value metric

Method string: `declared cost per metered unit`.

Per account: c = sum of C / sum of U over aligned periods with both. Book: pooled c = sum of C / sum of U over scored accounts, in the book currency. Dispersion: nearest-rank p50 and p90 of per-account c, and `p90_over_p50` = p90 / p50. Allocated cost is included and `allocated_share` is reported; with a usage-based allocation rule, the allocated part of c is the same for every account, so dispersion then reflects direct cost only, and S05 says so.

States: needs the `usage_units` column; an account is scored with at least one aligned period having U > 0; U = 0 gives `zero_usage_units`, never a cost per unit of 0; the book pooled value and dispersion need `MARGIN_MIN_ACCOUNTS` scored accounts, else `insufficient_data`. If p50 is 0, `p90_over_p50` is `not_provided` (reason `median_cost_zero`), never infinity. An account with positive U and C exactly 0 is scored and flagged `cost_zero_with_usage` for the founder to check the export.

### 4.8 M6 `cost_plus_check`: is price just following cost down

Method string: `first three against last three months`.

The cost-plus trap in the sheet is pricing as a fixed markup over token cost, so that every fall in model price is passed straight through. The indicator compares how price per unit and cost per unit moved over the same months and, when the caller supplies it, the model-price index.

Monthly buckets: use aligned account-periods that are exactly 1 whole month and carry U > 0, V > 0 and C. Account-periods with no metered revenue are left out of this metric and counted (`no_metered_revenue`), because a flat fee is not a unit price. A bucket is the calendar month of `period_start` (a Jan 15 to Feb 14 period is the January bucket; the response lists the rule). A bucket counts only with at least `TREND_MIN_ACCOUNTS` accounts. For bucket t, in the book currency:

```
p_t = sum of V / sum of U       price per metered unit
c_t = sum of C / sum of U       cost per unit
k_t = p_t / c_t                 markup, a multiple (not a margin)
```

Let first3 and last3 be the first and last three surviving buckets, each pooled (sum over the three buckets, not an average of ratios): `price_change = p_last3 / p_first3 minus 1`, `cost_change` likewise, `markup_change = k_last3 / k_first3 minus 1`.

| State | Condition |
|---|---|
| `cost_plus_pattern` | `cost_change` <= minus `MOVE_LINE` and `price_change` <= minus `MOVE_LINE` and absolute `markup_change` <= `MARKUP_BAND` |
| `markup_expanding` | `cost_change` <= minus `MOVE_LINE` and `markup_change` >= plus `MOVE_LINE` |
| `markup_squeezed` | `cost_change` >= plus `MOVE_LINE` and `markup_change` <= minus `MOVE_LINE` |
| `no_clear_pattern` | none of the above, including cost moving less than `MOVE_LINE` |

These describe what happened in the file; they are not a claim about intent or a prescription. If `c_t` is 0 or the sum of U is 0 in a bucket, the bucket is dropped and counted (`zero_cost_or_usage`), never given a markup of 0 or infinity.

**Model-price index.** The caller may supply a series `{period: YYYY-MM, index: number > 0}` with `source` (a URL or document name) and `as_of` (a date). A series without `source` and `as_of` is a 422: an unsourced price history is a fabricated figure. v1 ships no default series, because every vendor and model has its own history and a wrong default would be a cited number we cannot support; a cited default is a later task that carries URLs and retrieval dates in the file. With a series covering the surviving buckets: `index_change = D_last3 / D_first3 minus 1` and `pass_through = price_change / index_change`, stated only when the absolute `index_change` is at least `MOVE_LINE` (else `not_provided`, reason `index_move_below_line`, never a ratio over a near-zero move). A `pass_through` near 1 says price per unit has fallen as fast as the index. Without a series the state above still stands and the readout says "Excludes the model-price index: not in the file."

Minimums: at least `TREND_MIN_PERIODS` surviving buckets, else `insufficient_data` (S65). Needs `usage_units`, `usage_amount` and cost. Basis-bearing (4.2).

Worked example. First three months p 0.0100, c 0.0040, k 2.5. Last three: p 0.0050, c 0.0020, k 2.5. price_change minus 0.5, cost_change minus 0.5, markup_change 0: `cost_plus_pattern`. An index falling 50 percent gives pass_through 1.0.

### 4.9 M7 `storage_share`: storage share of cost, trend

Method string: `storage lines over all cost lines`.

This needs no attribution and no revenue: it is a cost mix, computed on all valid cost rows including `not_attributable` ones, bucketed by the calendar month of `cost_start` (rows spanning two calendar months are excluded and counted as `cost_straddles_periods`). A calendar month is **complete** when it lies strictly inside the file's cost date range, or is its first or last month and the range begins on the 1st or ends on the last day respectively. Incomplete months are dropped and counted.

```
s_t   = sum of storage cost in month t / sum of all cost in month t
shift = s_last3 - s_first3        pooled over the first and last three complete months
```

States: `not_provided` when no row has `cost_category` `storage` (reason `no_storage_lines_in_file`; the readout says "Excludes storage cost: not in the file", never 0 percent); `insufficient_data` when there are fewer than `TREND_MIN_PERIODS` complete months, or when the uncategorized share of cost exceeds `UNCATEGORIZED_MAX` (reason `uncategorized_share`, because the true storage share could sit anywhere in that gap). `scored` gives first-three share, last-three share, `shift`, direction `up` when `shift` >= `STORAGE_SHIFT_POINTS`, `down` when it is at most minus that, else `flat`, plus the latest complete month's share. Cost-only, so it runs on any basis.

## 5. Readout

Deterministic templates, no LLM, no em dashes. A sentence is emitted only when its condition holds. Every sentence the engine can emit is in this list with an id, and the response carries `readout.sentences: [{id, text}]` in this order. `{label}` is `label_for(basis).label`; `{figure_label}` is `label_for(basis, figure).labeled`. Money is `${x:,.2f}`. `{unit}` is `value_metric_unit` or "unit".

### 5.1 States

`readout_state`, one value, set in this order:

| Order | Condition | State |
|---|---|---|
| 1 | no cost export, or no billing grain | `no_cost_export`, `no_billing` |
| 2 | basis is `crm_proxy` | `cost_basis_not_declared` |
| 3 | not-attributable share of cost dollars is above `UNATTRIBUTED_SHARE_CAP` | `upper_bound` or `withheld`, per founder decision 2 |
| 4 | otherwise | `ready` |

Per-metric states are the three lens states, with the reason codes of section 4.

### 5.2 Sentences

Basis and scope:

- **S01** (basis `declared_cost` or `erp_verified`): "Basis: {label}. Cost is the lines in the export you supplied ({categories}); it is not full cost of goods sold. Method: billing revenue less declared cost." `{categories}` lists the categories present, for example "inference, storage".
- **S02** (basis `crm_proxy`): "This cost figure is a cost proxy, not margin. No revenue-less-cost result is stated. Cost per unit and storage share are shown." The label text is `LABELS[crm_proxy]`; "not margin" is on the ADR-006 allowlist.
- **S03**: "{a} of {b} billed accounts have cost in the file for at least one whole-month billing period. {c} account-periods from {start} to {end}, in {currency}."
- **S04**: "Of ${total:,.2f} in cost, {direct_pct:.0%} was attributed to a customer directly, {alloc_pct:.0%} was allocated by your rule, and {na_pct:.0%} (${na:,.2f}, {rows} lines) could not be attributed."

Attribution cautions:

- **S05** (allocated share at or above 0.30): "{x:.0%} of the cost behind these figures was allocated by your rule ({rules}), so it shows the rule, not measured use by customer."
- **S05b** (any `proportional_to_invoiced_amount` pool): "The rule for {pool} allocates cost in proportion to revenue, which gives every account the same result on that cost by construction."
- **S06** (state `upper_bound`): "Cost that could not be attributed is {x:.0%} of cost dollars, above the {cap:.0%} line. Every account figure is an upper bound on its result: attributing the missing cost can only lower it."
- **S07** (state `withheld`): "Cost that could not be attributed is {x:.0%} of cost dollars, above the {cap:.0%} line, so no per-customer result is stated. Cost per unit and storage share are shown."

Negative accounts (M4):

- **S20** (scored, 15 or more accounts): "{k} of {n} accounts cost more to serve than they paid in this period, {share:.0%} of accounts. They are {rev:.0%} of revenue and {cost:.0%} of cost, with a combined shortfall of ${gap:,.2f}. {label}."
- **S21** (fewer than 15): "Fewer than 15 accounts have aligned cost, so no share is reported. {k} of {n} account(s) cost more to serve than they paid; they are listed below."
- **S22** (k = 0, state `ready`): "No account with aligned cost paid less than its declared cost in this period."
- **S22b** (k = 0, state `upper_bound`): "No negative account is visible, but {x:.0%} of cost could not be attributed, so this is not a finding."
- **S23** (persistent accounts exist): "{p} of these accounts were negative in every period we could align (at least 3)."

Break-even (M3):

- **S30**: "{past} accounts are already past their break-even usage and {near} more are within 25 percent of it. Break-even is the usage at which an account's revenue equals its cost, at its observed cost per {unit}. Method: linear unit cost."
- **S31**: "{k} accounts pay more per {unit} than it costs to serve, so they have no break-even usage."
- **S32**: "{k} accounts are negative at any usage: their fixed fee is zero and the metered price is below cost per {unit}."
- **S33**: "Break-even needs at least 3 aligned periods with usage, metered revenue and cost. {k} accounts had fewer and are not scored."
- **S34** (always with S30): "Break-even assumes cost is proportional to {unit} usage at each account's own cost per {unit}. Cost that does not scale with usage is treated as if it did."

Cohorts (M2):

- **S40**: "At median usage ({u50:,.0f} {unit} per month) the cohort's result is {figure_label}; at the 90th percentile of usage ({u90:,.0f}) it is {figure_label}. Each cohort is the accounts within 10 percentile points of that usage, pooled."
- **S41** (15 to 19 accounts): "At median usage ({u50:,.0f} {unit} per month) the cohort's result is {figure_label}. A 90th-percentile result needs at least 20 accounts; {n} have usage and cost."
- **S42** (fewer than 15): "Fewer than 15 accounts have usage and aligned cost, so no usage-cohort result is reported."

Cost per unit (M5):

- **S50**: "Serving one {unit} costs ${c:.4f} across the book. The costliest tenth of accounts cost at least {r:.1f} times the median per {unit}."
- **S51** (fewer than 15 accounts): "Fewer than 15 accounts have usage and aligned cost, so no book-level cost per {unit} is reported. Per-account figures are listed."
- **S52** (flags): "{k} account(s) show usage and zero cost; check that their cost lines are in the export."

Cost-plus check (M6):

- **S60** (`cost_plus_pattern`): "Cost per {unit} fell {y:.0%} and price per {unit} fell {x:.0%}, so the markup held at {m:.1f} times. Price is moving with cost. Compared: the first three against the last three months."
- **S61** (`markup_expanding`): "Cost per {unit} fell {y:.0%} while price per {unit} moved {x:+.0%}, so the markup rose from {m0:.1f} to {m1:.1f} times."
- **S62** (`markup_squeezed`): "Cost per {unit} rose {y:.0%} while price per {unit} moved {x:+.0%}, so the markup fell from {m0:.1f} to {m1:.1f} times."
- **S63** (`no_clear_pattern`): "Cost per {unit} moved {y:+.0%} and price per {unit} moved {x:+.0%}. The moves do not match a pattern the check defines, so none is stated."
- **S64** (index supplied and `pass_through` scored): "The model-price index you supplied ({source}, as of {as_of}) moved {d:+.0%} over the same months. Price per {unit} moved {r:.0%} as far."
- **S65** (insufficient): "A cost-plus check needs 6 months with at least 5 accounts each. {k} month(s) qualified."

Storage share (M7):

- **S70**: "Storage was {s0:.0%} of cost in the first three complete months and {s1:.0%} in the last three, {dir} {pts:.0f} points."
- **S71** (always with S70): "Storage was {s:.0%} of cost in the latest complete month ({month})."
- **S72** (insufficient, months): "A storage trend needs 6 complete months of cost. The file has {k}."
- **S73** (insufficient, uncategorized): "{x:.0%} of cost has no category, above the 10 percent line, so no storage share is stated."

Exclusions, win rate, scope:

- **S80** (one per reason with a nonzero count, in the order of section 3): "Left out: {reason_text}: {count} {noun}, ${dollars:,.2f}." `reason_text` is the plain-language form of the code (for example `cost_straddles_periods` is "cost lines that span two billing periods"; `period_outside_cost_coverage` is "billing periods outside the dates of the cost file"; `period_currency_mismatch` is "billing periods whose currency differs from the cost currency"). Counts of rows, account-periods and accounts are named by noun, never mixed.
- **S81** (accounts with revenue and no cost rows): "{k} billed accounts (${rev:,.2f} of revenue) have no cost rows in the file. They are not scored, and an absent cost is not read as zero."
- **S82** (always): "Win rate: not provided, {WIN_RATE_REASON}." The reason is `billing.WIN_RATE_REASON`, imported and not retyped: "billing data holds paying customers only; win rate needs closed-lost deals from a CRM".
- **S83** (always): "This readout compares revenue with the cost you supplied. It does not set or recommend a price."

### 5.3 "Excludes X: not in the file" cases

Each is emitted as "Excludes {item}: not in the file." when the item is absent, in this order:

1. `usage units` (billing `usage_units` column absent or blank on every period): M2, M3, M5, M6 are `not_provided`.
2. `metered amount` (billing `usage_amount` absent): M3 and M6 are `not_provided`.
3. `storage cost` (no `cost_category` storage): M7 is `not_provided`.
4. `cost categories` (no `cost_category` column and no category table): M7 is `not_provided`; the readout cannot say which part of cost is storage.
5. `the model-price index` (no series supplied): M6 still stated, S64 omitted.
6. `the unit label` (no `value_metric_unit`): sentences say "unit".
7. `customer attribution` (no `customer_key` column, or no crosswalk and no rule): all cost is `not_attributable`; M1 to M6 are `not_provided` with reason `no_attribution`, and only M7 runs.
8. `an allocation rule` (shared cost present, no confirmed rule): the shared cost is `not_attributable` and S04 shows its dollars.
9. `cost currency` (no `cost_currency` column): the caller must state one currency in the request (`cost_currency_default`), echoed in S03; without it the rows are not usable (`cost_currency_missing`, counted).

## 6. API

**Decision: a new endpoint, `POST /billing/margin`, in a new router `api/routers/margin.py`, not an extension of PK-56's `/billing/analyze`.** Reasons: the cost file is a second upload and a new data class (cost exports, to be registered by customer-success before real files arrive); the two readouts have different consent and retention stories; PK-56 owns `api/routers/billing.py` and PK-63 extends it, so extending `/billing/analyze` would make this work wait on both and collide with both. `/billing/margin` calls the same billing cleaner and returns the same win-rate and readiness blocks, so the two stay consistent without sharing a file. The route name says "margin"; basis-bearing results are still withheld under `crm_proxy` (4.2), and response keys avoid the word.

Perimeter: the existing shared-secret perimeter, rate limits and `_read_capped` size caps apply unchanged; the tenant is scoped by `_customer_ref`. Rows are processed in memory and discarded. No row, customer id, key or invoice value is logged; errors carry codes and counts (connector rule 6).

**Request** (multipart): `billing` (CSV in the PK-53 grain shape), `cost` (one or more CSV parts), `confirmation` (JSON):

```json
{
  "cost_profile": "cost_export",
  "preset": "anthropic_cost_report",
  "mapping": {"<header>": "<field>"},
  "unit_scale": {"cost_amount": "0.01", "confirmed_cents": true},
  "category_table": [{"match": {"cost_line": "Storage"}, "category": "storage"}],
  "cost_basis_declared": true,
  "declared_by": "name or email of the person declaring",
  "cost_currency_default": "USD",
  "attribution": {"crosswalk": [{"customer_key_type": "workspace_id", "customer_key": "wrkspc_x", "source_record_id": "sub_1"}]},
  "allocation": [{"pool": {"cost_category": "storage"}, "rule": "proportional_to_usage_units", "confirmed": true, "confirmed_by": "same", "confirmed_at": "2026-11-12T09:00:00Z"}],
  "value_metric_unit": "credit",
  "model_price_index": {"points": [{"period": "2026-01", "index": 100}], "source": "https://...", "as_of": "2026-11-10"},
  "thresholds": {"unattributed_share_cap": 0.20}
}
```

A missing `cost_basis_declared` yields basis `crm_proxy` (200, basis-bearing metrics refuse) and not an error, so the refusal is visible. 422 for: `erp_verified` in the file; a crosswalk key mapped to two accounts; a price index without `source` and `as_of`; an `anthropic_cost_report` preset without `confirmed_cents` (`cost_unit_unconfirmed`); an unknown rule id; a profile that is not `cost_export`; a billing file that fires the cost fingerprint; a cost file that fires the billing or CRM fingerprint.

**Response** (money as decimal strings to the cent, ratios as numbers to 4 places, as the billing readout returns them):

```json
{
  "method": "margin_health",
  "readout_state": "ready",
  "basis": {"cost_basis": "declared_cost", "label": "contribution margin, customer-supplied cost basis", "may_say_margin": true},
  "scope": {"billing_accounts": 0, "accounts_with_aligned_cost": 0, "aligned_account_periods": 0,
            "cost_coverage": {"start": "", "end": ""}, "currency": "USD", "other_currencies": {}},
  "attribution": {"direct": {"rows": 0, "amount": "0.00"}, "allocated": {"rows": 0, "amount": "0.00", "rules": []},
                  "not_attributable": {"rows": 0, "amount": "0.00", "share": 0.0}},
  "metrics": {"account_result": {}, "usage_cohorts": {}, "break_even_usage": {}, "negative_accounts": {},
              "cost_per_unit": {}, "cost_plus_check": {}, "storage_share": {}},
  "accounts": [],
  "exclusions": {"by_reason": {"<code>": {"count": 0, "noun": "rows", "amount": "0.00"}}},
  "assumptions": {"declared_by": "", "unit_scale": {}, "allocation": [], "crosswalk_entries": 0, "monthly_bucket_rule": "calendar month of period_start"},
  "win_rate": {"method": "win_rate", "status": "not_provided", "reasons": ["billing data holds paying customers only; win rate needs closed-lost deals from a CRM"], "values": {}},
  "readiness": {},
  "readout": {"sentences": [{"id": "S01", "text": ""}]}
}
```

Each metric is the billing-lever dict `{method, status, reasons, values}`. `accounts` is the per-account list (account id, result, result_pct, allocated_share, usage per month, c, p, break-even fields, flags), capped and sorted deterministically (result ascending, ties by `source_record_id`), with `truncated`. `assumptions` echoes the human-confirmed context so a stored readout can be re-read.

**Reuse of the guardrail and the billing-only outcome rule.** `pricing/margin.py` never builds a deal row and never reads or writes `outcome`. It does not call the win-rate path. The response's `win_rate` is `billing.win_rate_lever()` and `readiness` is `billing.readiness_disclosure(deal_records, periods)`, so a request that also carries deal rows gets the same count of billing-sourced rows refused from win rate (`partition_for_win_rate`, wired into the guardrail by PK-91) that `/billing/analyze` shows. A static test asserts `pricing/margin.py` imports nothing from `pricing.guardrail`, the win-rate functions of `pricing.metrics`, or `pricing.model`; a behavioural test feeds deal rows labelled `closed_won` with `source_system: stripe` through the endpoint and asserts win rate stays `not_provided` and `billing_rows_labelled_closed` counts them. `BILLING_ONLY_OUTCOME` rows stay out of win rate by `win_rate_eligible`; this analysis adds no path around it.

**Audit trail.** The readout is an analysis, not a decision. The human inputs it depends on are the declaration, the crosswalk, the allocation rules, the unit scale and the index. MH-8 records them: an assumption record (rule ids, pool filters, driver, `confirmed_by`, `confirmed_at`, crosswalk entry count, unit scale, index source, thresholds, and the exclusion counts; no customer key and no row) is written to the decision log as kind `margin_assumption` through `governance.py`, so a past figure can be traced to the assumptions behind it. Any pricing action a reader takes from the readout is recorded as a normal decision in the existing exception flow.

**Readiness disclosures** (`readiness` plus the sentences): billing-sourced rows refused from win rate, by count; contract-period and cost rows held, by count; cost exclusions by reason with dollars; the allocated and not-attributable shares; and the standing line that rows are processed in memory and not retained.

## 7. Tests

### 7.1 Planted-answer generator

New module `pricing/generate_cost.py` (data-engineer), opt-in and separate from `pricing/generate.py` and `pricing/generate_billing.py`, which stay byte-identical:

```python
def generate_cost_fixture(seed: int = 7, filler: int = 20,
                          price_policy: str = "cost_plus") -> tuple[pd.DataFrame, pd.DataFrame, dict]
# returns (billing_periods, cost_lines, answer_key); price_policy in {"cost_plus", "held"}
```

- **Own stream.** `np.random.SeedSequence(entropy=seed, spawn_key=(0x4D48,))`, a key no other generator uses, so it shares no state with `generate()` (seed, seed + 1, seed + 2, seed + 3) or `generate_billing`. A test asserts the three existing pins still hold.
- **Planted accounts are fixed amounts, independent of the seed**; only filler accounts draw from the stream. Money is integer cents; the answer key is `Decimal`; no float drift. Synthetic ids only; no real customer data, no contact fields.
- **Hash-pinned like `data/synthetic/deals.csv`.** `tests/test_generate_cost.py` pins the sha256 of `to_csv(index=False, lineterminator="\r\n")` as UTF-8 text for the billing frame and the cost frame under each `price_policy` (CRLF fixed so Linux CI and Windows agree, as `tests/test_generate_contract.py` does), plus per-column sha12 pins that name the column that moved. The committed fixtures live under `data/synthetic/cost-export/` (`billing.csv`, `cost-cost-plus.csv`, `cost-held.csv`, `cost-anthropic-cents.csv`, `answer-key.json`) and the test regenerates and compares bytes.
- **Calendar.** 2026-01 to 2026-12, monthly billing periods anchored on the 1st, USD, value metric "credit".
- **Independent oracle.** `tests/oracle_margin.py` recomputes every metric by slow, obviously-correct `Decimal` loops over the cents and does not import `pricing.margin`. Distribution metrics depend on the seeded filler, so they are verified against the oracle and pinned by hash; the planted-account answers below are baked and exact.

Planted accounts (filler accounts are 20 ordinary hybrid accounts: fixed 1,000.00 plus metered 0.01 per credit on 50,000 to 150,000 credits a month, cost per credit well below price):

| Id | Construction | Expected answer |
|---|---|---|
| MA-01 `sub_heavy_1` | flat 3,000.00 a month, no metered amount, 2,000,000 credits a month, cost per credit 0.0040 | cost 8,000.00 a month; result minus 5,000.00 and result_pct minus 1.6667 every month; `break_even`, u* 750,000, headroom 0.3750; negative, persistent, 12 negative periods |
| MA-02 `sub_heavy_2` | flat 5,000.00, 1,500,000 credits, cost per credit 0.0040 | cost 6,000.00; result minus 1,000.00; u* 1,250,000; headroom 0.8333; negative, persistent |
| MA-03 `sub_thin` | R 1,000.00, V 600.00, 100,000 credits, cost per credit 0.0080 | cost 800.00; result 200.00 (0.2000); p 0.006, c 0.008, u* 200,000, headroom 2.0000; not near, not negative |
| MA-04 `sub_near` | flat 3,000.00, 700,000 credits, cost per credit 0.0040 | cost 2,800.00; result 200.00; u* 750,000; headroom 1.0714; counted in "near" |
| MA-05 `sub_hybrid_ok` | R 2,000.00, V 1,000.00, 100,000 credits, cost per credit 0.0040 | cost 400.00; result 1,600.00; `price_above_cost` |
| MA-06 `sub_free` | R 0.00 for Jan to Mar (100-percent coupon, `credit_amount` positive), 100,000 credits, cost 400.00 a month; paid from April at R 1,000.00 | Jan to Mar: result minus 400.00 each, result_pct null `zero_revenue`; account scored |
| MA-07 `sub_nocost` | billed all year, no cost line anywhere | `not_provided`, `cost_not_in_file`; its revenue is in S81; never a 100-percent result |
| MA-08 `sub_eur` | billed in EUR, cost in USD | every period `period_currency_mismatch`; counted with dollars |
| MA-09 `sub_weekly` | weekly billing periods | every period `period_not_whole_months` |
| MA-10 `sub_conflict` | two differing rows for the March period | March excluded `period_billing_conflict`; other months scored |
| MA-11 `sub_zero_usage` | 0 credits in three months with cost 150.00 each | break-even `insufficient_data`, `zero_usage_units`; cost per unit not given |
| MA-12 shared pool | monthly shared compute line 1,200.00 with no key, plus a storage line allocated by `proportional_to_usage_units` in one variant | unconfirmed: `not_attributable`, 14,400.00 for the year in S04. Confirmed (variant): allocated cents sum to the pool exactly each month |
| MA-13 `proj_unmapped` | daily inference 25.00 for March, key not in the crosswalk | `not_attributable`, 775.00, 31 rows |
| MA-14 storage trend | storage cents each month derived from that month's non-storage cents so the planted share rises 10 percent in January to 40 percent in December | shift and shares recovered exactly from the realized cents (the key stores them); direction `up` |
| MA-15 price policy | cost per credit on the filler accounts falls 50 percent across the year; `cost_plus`: filler price is 2.5 times cost each month; `held`: filler price stays 0.01 | `cost_plus`: `cost_plus_pattern`, pass_through 1.0 against a supplied index falling 50 percent. `held`: `markup_expanding` |

Planted hygiene rows in the cost file, each with a known count and dollar amount in the answer key: a straddling monthly line (2026-05-15 to 2026-06-14) for `cost_straddles_periods`; a line dated 2025-12 for `cost_outside_billing_periods` while inside file coverage; a duplicated pull of Feb 1 to 7 for MA-01 (`cost_duplicate_collapsed`); two same-key same-day same-line rows with different amounts (`cost_conflict`); three blank `cost_amount` cells, two unparseable ("1,200", "$100") and one negative.

### 7.2 Silent-failure cases

Each is a named test with the expected status, reason and count, and each asserts the failure is disclosed and the result is not a plausible-looking zero or 100 percent.

| Case | Expected |
|---|---|
| `cost_amount` column absent | all metrics `not_provided`, `cost_amount_column_not_in_file`; sentence "Excludes cost: not in the file" |
| blank cost cells | counted `cost_blank_amount` with row count; sums unchanged by them; never 0 |
| unparseable cost cells | counted `cost_unparseable_amount`, not read as blank |
| unattributable cost | disclosed in S04 with rows and dollars; in book cost totals and storage share; not in any account |
| no crosswalk and no rule | `no_attribution`; M1 to M6 `not_provided`; M7 runs |
| allocation rule `confirmed: false` | treated as no rule |
| allocation driver missing | pool stays `not_attributable`, `allocation_driver_missing` |
| account with revenue, no cost rows | `cost_not_in_file`, not scored, in S81, absent from every share |
| billing period before or after cost coverage | `period_outside_cost_coverage`, not scored |
| in-coverage period with no cost rows | `period_no_cost_rows`, not scored |
| currency mismatch (EUR billing, USD cost) | `period_currency_mismatch`, counted with dollars, nothing converted |
| two billing currencies tied at the top | book metrics `not_provided`, `currency_tie` |
| lowercase `usd` | read as `USD`; no mismatch |
| Anthropic cost report read as dollars | `cost_unit_unconfirmed` 422 without `confirmed_cents`; with it, totals equal the dollar fixture exactly; a mutation test that drops the scale fails by exactly 100 times |
| billing period conflict | excluded, `period_billing_conflict`, reuses `_clean_periods` output |
| cost duplicate pull | collapsed, counted once, sums unchanged |
| cost conflict | both rows excluded, `cost_conflict`, dollars counted |
| straddling cost row | `cost_straddles_periods`, dollars counted, not split |
| weekly billing | `period_not_whole_months`, never rounded to a month |
| zero usage with cost | `zero_usage_units`, no cost per unit, no break-even |
| usage units blank in some periods | those periods excluded from unit metrics and counted; result metrics still use them |
| zero revenue period | kept; result minus cost; percentage null |
| negative revenue (refund) | `invalid_money_value`, left out |
| negative cost (vendor credit) | `cost_negative_amount`, left out, counted |
| missing storage category | M7 `not_provided`, "Excludes storage cost: not in the file", never 0 percent |
| fewer than 15 accounts | counts and list only, no shares, S21 or S42 |
| fewer than 6 monthly buckets | `insufficient_data`, S65 or S72 |
| model-price index without `source` | 422 |
| `erp_verified` in a `cost_basis` cell | 422 `SchemaError` |
| `crm_proxy` in a `cost_basis` cell, or no declaration | basis `crm_proxy`; M1 to M4 and M6 `not_provided`; S02 |
| a CRM export with `Amount` and `Stage` | not a `cost_export` |
| a billing export | not a `cost_export`; both fingerprints firing gives `unknown` |
| a cost file sent to `/diagnostic` | refused `cost_export_not_a_deal_file` |
| deal rows `closed_won` with `source_system: stripe` | win rate `not_provided`; counted in `billing_rows_labelled_closed` |
| row order shuffled, two runs | byte-identical JSON |
| inputs after the call | unmodified (no mutation) |

### 7.3 The margin-word guard

1. Under a `crm_proxy` basis, `margin_violations(text, basis)` over every string in the serialized response (keys and values, recursively) returns nothing, and S02 passes the allowlist.
2. Under `declared_cost`, the text "gross margin" and "net margin" never appear anywhere in the response; the only "margin" label text is the one `label_for` builds. Under `erp_verified`, "gross margin, ERP-verified cost" is the only gross wording.
3. A source scan of `pricing/margin.py` and `api/routers/margin.py` finds no literal label text and no string containing "margin" outside the metric-method strings, which the guard test lists explicitly.
4. Basis-bearing metrics under `crm_proxy` never compute: the test monkeypatches the compute functions to raise and asserts the endpoint still returns 200 with `not_provided`.
5. The serialized response contains no em dash, scanned explicitly.
6. `COST_EXACT_ONLY_FIELDS` parity: `cost_basis` is exact-only in both field sets.

### 7.4 Property tests

A seeded loop of 500 random valid books, `hypothesis` where already a dependency: allocation conservation to the cent; result at observed usage from M3 equals the M1 result; pooled shares lie in [0, 1]; M4 count equals the number of accounts with result below 0; M5 pooled c equals sum C over sum U; M6 `cost_plus_pattern` requires both moves; M7 shares lie in [0, 1]; duplicating the whole cost file changes nothing (idempotence); permuting rows changes nothing.

No LLM eval applies: nothing in this analysis calls a model.

## 8. Build plan

Task ids are provisional (MH-n); the lead assigns board ids. Estimates are in half-days, are my estimates for the owner named, and are not calibrated against shipped work. Claims were checked against `docs/agents/OWNERSHIP.md` and `python tools/agentctl.py status` at 2026-11-10T22:51Z (no task in progress). Claims already on the board that touch nearby code: PK-55 (`pricing/adapters/stripe.py`, `pricing/adapters/billing_common.py`, `tests/test_adapter_stripe.py`, `tests/fixtures/stripe`), PK-56 (`api/routers/billing.py`, `api/main.py#routers`, `tests/test_billing_api.py`), PK-63 (`pricing/adapters/chargebee.py`, `api/routers/billing.py#adapters`, `tests/test_adapter_chargebee.py`, `tests/fixtures/chargebee`), PK-91 (`pricing/guardrail.py#source_partition`, `tests/test_guardrail.py`), PK-40 (`pricing/ingest.py#profiles`), PK-33 (`pricing/governance.py#concessions`). None of them claims a path below, with the two sequencing notes on MH-3b and MH-7.

| Task | Owner | Claims | Deps | Half-days |
|---|---|---|---|---|
| **MH-1** Add the `cost_period_actuals` grain: `COST_PERIOD_FIELDS`, `CostCategory`, `CustomerKeyType`, allocation rule ids, key and money field lists; not in `FIELDS` | data-engineer | `pricing/schema.py`, `tests/test_schema_cost.py` | an ADR (see section 10, item 5) | 2 |
| **MH-2** Plant the margin answers in a seeded, hash-pinned generator (7.1), with committed fixtures and the answer key | data-engineer | `pricing/generate_cost.py`, `data/synthetic/cost-export/**`, `tests/test_generate_cost.py` | MH-1 | 4 |
| **MH-3** Add the `cost_export` mapping profile: fingerprint, `COST_EXACT_ONLY_FIELDS`, presets, outcome refusal branch, captured real headers | ai-engineer | `pricing/mapping.py#cost_profile`, `tests/test_mapping_cost.py`, `tests/fixtures/mapping_profiles/cost_export*.csv` | MH-1; a founder header sample | 3 |
| **MH-3b** Refuse a cost-export profile on the deal path | backend-engineer | `pricing/ingest.py#cost_refusal`, `tests/test_ingest_cost_refusal.py` | MH-3; sequence after PK-40 if the lead reads the two `ingest.py` components as overlapping | 1 |
| **MH-4** Core: cost cleaning, attribution, crosswalk, allocation with exact cents, alignment, M1 `account_result`, M4 `negative_accounts`; imports `billing._clean_periods` and `_whole_months` read-only, with a test pinning their names and behaviour (no edit to `pricing/billing.py`) | backend-engineer | `pricing/margin.py#core`, `tests/test_margin_core.py` | MH-1 | 6 |
| **MH-5** Unit metrics: M2 `usage_cohorts`, M3 `break_even_usage`, M5 `cost_per_unit` | backend-engineer | `pricing/margin.py#unit_metrics`, `tests/test_margin_unit.py` | MH-4 | 4 |
| **MH-6** Trends and readout: M6 `cost_plus_check`, M7 `storage_share`, readout state and every sentence in 5.2, label through `cost_basis.py` | backend-engineer | `pricing/margin.py#trends_readout`, `tests/test_margin_trends.py`, `tests/test_margin_readout.py` | MH-5, MH-2 | 5 |
| **MH-7** `POST /billing/margin`: router, request validation, 422 cases, response, win-rate and readiness blocks | backend-engineer | `api/routers/margin.py`, `api/main.py#routers`, `tests/test_margin_api.py` | MH-6, MH-3, MH-3b; sequence after PK-56 merges so `api/main.py#routers` is free | 4 |
| **MH-8** Record the human confirmations as a `margin_assumption` decision-log payload | backend-engineer | `pricing/governance.py#assumptions`, `tests/test_margin_assumptions.py` | MH-7; sequence after PK-33 if the lead reads `#assumptions` and `#concessions` as overlapping | 2 |
| **MH-9** Cross-cutting verification: oracle, known answers, silent-failure matrix (7.2), margin-word guard (7.3), property tests (7.4) | qa-engineer | `tests/oracle_margin.py`, `tests/test_margin_known_answer.py`, `tests/test_margin_silent_failures.py`, `tests/test_margin_word_guard.py` | MH-7, MH-2 | 3 |
| **MH-10** Stretch, cuttable: tokens-times-rate-card path, `declared_cost` from a confirmed rate table | backend-engineer | `pricing/margin.py#rate_card`, `tests/test_margin_rate_card.py` | MH-6 | 4 |

Total without MH-10: 34 half-days (17 working days) across three owners. Critical path: MH-1, MH-4, MH-5, MH-6, MH-7, MH-9 is 2 + 6 + 4 + 5 + 4 + 3 = 24 half-days (12 working days); MH-2, MH-3 and MH-3b run beside MH-4 and MH-5 and finish before MH-6 needs them, and MH-8 runs beside MH-9. The estimate assumes PK-56 has merged when MH-7 starts; if it has not, MH-7 waits, because `api/main.py#routers` is claimed there and the two are serialized, not parallelized.

Work outside engineering claims, flagged as dependencies and not claimed here: register the cost-export data class in `docs/ops/data-register.md` and the NDA data-classes schedule and add the cost-export request to the data-request list (customer-success; those files are claimed by PK-20, PK-44 and PK-45 and need sequencing by the lead); the web readout (web-engineer, later).

Deferred, each with the trigger that would revive it: declared FX rates for mixed currencies (a partner billing in EUR against USD cost); majority-of-days assignment for monthly cost on mid-month billing (a partner whose billing anchor is not the 1st); vendor credits as negative cost; a cited model-price series (a source list with URLs and dates); the Anthropic Usage and Cost Analytics API fields; a connector that reads cost and sets `erp_verified`.

## 9. Founder decisions

Two decisions change what gets built. Both have a default in this spec so MH-4 and MH-6 can start before the answer; a different answer changes a constant and a sentence, not the architecture.

**Decision 1: the allocation rule default.** Cost that no key attributes (shared compute, unkeyed provider spend, storage) is the common case in an audit.

- **A (recommended).** No default: shared cost stays `not_attributable` until the caller confirms a rule per pool, and the runbook suggests `proportional_to_usage_units` for inference and compute pools. `proportional_to_invoiced_amount` is never suggested and needs an explicit id.
- **B.** `proportional_to_usage_units` is preselected for every shared pool, and the caller confirms it once for all.
- **C.** `proportional_to_invoiced_amount` as the default.

Recommendation A. Allocated cost carries only the driver's information, so a preselected rule turns the founder's accounting convention into a finding about the founder's customers. C is wrong by construction: it makes every account's result equal on that cost, which hides the heavy users the analysis exists to find. The price of A is that an unconfirmed audit shows more `not_attributable` cost and, under decision 2, may show fewer per-customer figures. Storage is a weak case for B as well: usage units are the wrong driver for storage volume.

**Decision 2: does unattributable cost block the readout or only mark it.** At `UNATTRIBUTED_SHARE_CAP` (default 20 percent of cost dollars).

- **A. Block.** Above the cap, no per-customer result is stated (`withheld`, S07). Cost per unit and storage share still show.
- **B. Mark only.** Everything is stated with a banner.
- **C (recommended).** `upper_bound`: above the cap, every figure is stated as an upper bound on the result (S06), negative-account findings are stated in full because they can only worsen when the missing cost is attributed, and no healthy-direction statement is made (S22b replaces S22, the cohort and cost-plus sentences carry S06).

Recommendation C. Missing cost can only raise an account's result, so a loss finding is robust to it and a healthy finding is not. A blocks a finding the founder can already act on; B lets a missing-cost "healthy" figure read as a fact. If the founder wants the stricter behaviour for an audit deliverable that goes to a customer's board, A is one switch (`withheld`) and is built behind the same state. The cap itself (20 percent) is a starting point to be set against the first partner's file.

## 10. Open items and dependencies, not founder decisions

1. **Copy.** The audit offer says "gross margins". Engine output on `declared_cost` says "contribution margin, customer-supplied cost basis" (ADR-006), and "gross margin" only on `erp_verified`. The one-pager and any lead-magnet calculator copy should say "margin" or "contribution margin" for what this analysis produces. Founder or pricing-strategist to align before the audit one-pager is sent.
2. **Vendor CSV headers.** The OpenAI and Anthropic dashboard export headers were not verifiable on 2026-11-10 (section 2.2). MH-3 needs a founder-supplied sample of headers only. Until then the presets are built on the API field names above, and section 2.2 is corrected from the sample.
3. **Billing CSV to grain.** `contract_period_actuals` is built by the connectors (PK-55, PK-63) in memory. A founder's manual Stripe or Chargebee invoice CSV has no task that shapes it into the grain, so for a manual audit before the connectors ship, the 14-day runbook either shapes the file by hand to the PK-53 grain columns or the lead adds a small mapping task. This spec accepts the grain-shaped CSV only.
4. **Customer identity.** The grain's account is a subscription, not a customer, by design. A customer with several subscriptions shows several accounts unless the crosswalk maps their cost keys to one `source_record_id`. A customer-level rollup across subscriptions needs a customer id the grain does not carry and is not in v1.
5. **ADR for the new grain.** `docs/agents/OWNERSHIP.md` calls a schema change ADR-worthy. The `cost_period_actuals` grain, the allocation rule ids and the rule that the cost file never sets `erp_verified` should be recorded by pk-lead in `docs/agents/DECISIONS.md` (provisionally ADR-007) before MH-1 starts. This design doc does not edit that file.
6. **Ownership of `pricing/cost_basis.py`.** It is not in the OWNERSHIP table. This design changes nothing in it and only calls it. If a future change is needed (a new allowlist phrase), the lead assigns it.
7. **ICP.** The decision record leaves the ICP conflict (the $20M to $100M usage and hybrid band against seed-to-Series-A AI agent companies) open. This analysis serves either: it needs a billing export, a cost export and a value metric, and nothing in it depends on ARR band.
8. **New data class.** Cost exports are a new class of customer data. Retention is in memory only; the decision-log record carries no row and no key. Counsel and customer-success review the NDA schedule before a real export arrives.
