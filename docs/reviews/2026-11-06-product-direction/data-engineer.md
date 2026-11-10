# Data engineer review: canonical model for multi-source, usage-native, margin-aware pricing

Summary: the canonical schema is one flat row per closed CRM opportunity with one `cogs_acv` column; it can carry this direction only with a source-and-provenance layer plus child entities, and the smallest safe first step is that contract and a margin-label guard, not margin itself.

## 1. Findings

- `pricing/schema.py` is a flat deal. No `source_system`, no external ids beyond `opportunity_id` and `account_id`, no lineage. The only provenance is `LoadReport.field_sources` (`pricing/ingest.py`), per upload, in memory, discarded. That fits the delete-rows rule but means provenance cannot reach the decision record.
- UBP fields are scalars: `committed_acv`, `overage_rate`, `ramp_year_1_acv`, `ramp_year_2_acv`, with year 3 defined as `booked_acv`. That cannot express a 5-year ramp, tiered overage, or several meters. They are captured, never scored.
- `cogs_acv` is the only cost field, and the generator fills it as a flat 8 to 38 percent of booked. Nothing in the types stops a CRM-derived number landing there and being read as margin. The discipline lives in docs, not code.
- Neon holds no deal rows by design (`neon/schema.sql`, `docs/design/salesforce-crm-workflow-v1.md`). Tables are Salesforce-named, keyed by `customer_ref`. Branch `feat/crm-provider-schema` already has a provider generalization with a down file; reuse it.
- Migration discipline is sound (`neon/MIGRATIONS.md`), but `neon/test_migrations.py` is structural only; no CI database.
- Sufficiency gates are CRM-shaped: `MIN_CLOSED_DEALS = 30` (`ingest.py`), `SEGMENT_REF_MIN_DEALS = 100`, `SEGMENT_REF_MIN_BANDS = 3` (`metrics.py`), explicit "insufficient data" basis. Nothing equivalent exists for invoices, usage periods, or cost coverage.

## 2. What would have to change

### 2.1 Multi-source and provenance (about 8 days)

All additions optional, so the old CSV still works.
- Header: `source_system` enum (salesforce, hubspot, pipedrive, zoho, close, attio, freshsales, dealhub, pandadoc, proposify, salesbricks, stripe, chargebee, maxio, metronome, orb, csv), `source_record_id`, `source_account_id`, `source_quote_id`, `source_subscription_id`, `source_updated_at`.
- Child entities, each its own list in schema.py and its own file in the data request: `quote_line` (quote, line, sku, qty, unit list, unit net, term), `invoice_line` (period, amount, currency, credit flag), `usage_event` (meter, period, units, unit price, billed), `cost_line` (2.3).
- Identity crosswalk `(tenant, source_system, source_record_id) -> canonical_deal_id`. Quote-to-opportunity joins carry `link_method` (exact id, account plus date window, manual) and confidence. No silent merge.
- Field provenance: an in-memory sidecar per field `(source_system, source_field, mapping layer, transform)`, generalizing `field_sources`. Only aggregates persist, as evidence in the `decision_log` payload ("booked_acv from invoices, 94 percent coverage"). Conflicts: precedence declared per field (billing over CPQ over CRM for realized price; CPQ over CRM for list); the loser is kept as `<field>__alt`; a disagreement over 2 percent is a gate warning.
- Neon migration, additive: `source_connections` (generalizes `salesforce_connections`) and `source_field_coverage`. Down file with the row-count guard pattern. Deploy order: migration before code; new tables only, so the intermediate state works. Never rename `salesforce_*`.
- Downstream consumers of any schema.py change: `pricing/generate.py`, `pricing/ingest.py` (`_NUMERIC`, `_coerce_types`, `_FX_MONEY_COLS`), `pricing/mapping.py` (`SYNONYMS`), `pricing/crm.py`, `gtm/data-request.md` (per-source variants), the web mapping UI, and tests pinned to the generated dataset. Each connector is its own task (5 to 10 days each, not in this slice).

### 2.2 Usage-native fields (about 6 days)

- Commit, ramp, overage attach to the contract: a `contract_term` child (term number, start, end, committed amount, platform fee) replaces the ramp pair and the year-3 convention. Old columns stay as a derived flat view.
- `rate_card` child (meter, tier floor, tier ceiling, unit price, overage flag, effective date) makes tiered overage and multi-meter expressible.
- Consumption history attaches to the customer: `usage_event` keyed by canonical account, meter and period, optionally linked to a term. Derived, not stored: commit attainment, volatility by meter, overage share.
- Token-cost deflation needs dated unit prices per event; without them a decline cannot be detected or tested.
- Neon: nothing. Row-level stays in memory.

### 2.3 Cost and margin (about 7 days, after 2.1)

- Typed `cost_line`: amount, currency, `cost_basis` in {bom_standard, bom_actual, landed_actual, infra_metered, allocated_overhead, crm_proxy}, `ship_to` (country, region), incoterm, `tax_treatment` (exclusive, inclusive, exempt, reverse_charge, unknown), `evidence_ref`.
- Make the discipline structural. At the ingest boundary, any CRM or CSV `cogs_acv` is relabelled `cost_proxy_acv` with `cost_basis=crm_proxy` (alias kept for old files). The gross-margin function raises on proxy-only input. Output labels come from a closed set: "gross margin (BOM)", "contribution (landed)", "net margin (after freight and tax)", "cost proxy, not margin". A test asserts the word "margin" is never emitted for proxy inputs. Partial coverage: report on the covered subset with the coverage percent, else "insufficient cost data".
- We record tax treatment; we do not compute tax or recoverability.
- The `cogs_acv` relabel ripples to the generator, mapper synonyms ("cogs", "cost") and `gtm/data-request.md`; it is its own task.

## 3. What the synthetic generator must produce (about 7 days)

Each new signal is planted with a known answer key. Use independent RNG streams (seed+3 and up) so the pinned 2,000-row dataset and model tests do not shift.
- Aligned CRM, CPQ and billing extracts of the same deals, with planted disagreements: 3 to 5 percent list mismatch, ids missing on 20 percent of quotes, late invoices.
- Monthly meter series per account in four regimes: steady, ramping, seasonal, step-down after a unit-price cut. One meter family with a 20 to 40 percent annual unit-price decline. Commit attainment from 40 to 140 percent so under-commit and overage both occur.
- A separate physical-goods profile (never mixed into the SaaS set): BOM lines, landed cost by ship-to with freight and duty bands, mixed tax treatments. Plant a margin-negative segment (deep discount into a high-freight region) as the discoverable story, plus a proxy-only fixture that must return "cost proxy, not margin".
- A hidden per-account willingness to pay driven by observable attributes, so value-based scoring can be checked against truth.
- One gate fixture per failure (thin invoices, 40 percent missing cost, mixed currency, stale usage), each with its expected message.
- Labelled synthetic; `data/private/` untouched.

## 4. Quality gates per source (about 4 days)

One declarative table keyed by (source, entity): required fields, count floor, coverage floor, freshness, block or warn. Reuse `LoadReport` and add a `source_readiness` section. Same rule everywhere: never repair silently, say what was excluded.

| Entity | Block | Warn |
|---|---|---|
| CRM opportunity | under 30 closed; list or booked missing (existing) | under 500 per year |
| CPQ quote line | under 80 percent of closed deals linked | line sum differs from header by over 2 percent |
| Billing invoice | under 6 billed periods per account; mixed currency | unflagged credit memos |
| Usage event | under 6 months per meter; gaps over 15 percent | unit price missing |
| Cost line | under 60 percent of booked ACV covered by non-proxy cost | tax treatment unknown on over 25 percent |

These numbers are hypotheses, to be set from a real partner file. What generalizes: sufficiency is per (entity, slice) with a count floor plus a populated-bands-or-periods floor (the `MIN_DEALS` plus `MIN_BANDS` pair); the fallback chain is slice, then global, then explicit "insufficient data" as NaN, never zero. Value-based scoring gets its own floor: accounts with usage history, not deals.

## 5. Risks and tradeoffs

- Schema breadth is the scope-creep vector. The child-entity contract is cheap; connectors are not.
- Billing platforms are the feared entrant (BRIEF). The durable data position is the neutral crosswalk plus the decision record, so identity and provenance come first, margin does not.
- BOM margin needs ERP data a pre-seed customer will not hand over early. Selling margin before one customer supplies non-proxy cost breaks the honesty rule.
- In-memory provenance means "which row?" cannot be answered after deletion. That is the price of the delete-rows rule.
- None of this advances paid-pilot validation unless the first partner's data is not CRM-only.

## 6. Recommended first increment (about 6 days)

Source-and-provenance contract with CRM-only behaviour unchanged:
1. schema.py: `source_system`, source ids, `link_method`, `quote_line`, `cost_basis`, and the `cogs_acv` to proxy relabel with alias. 2 days.
2. ingest.py and mapping.py: provenance sidecar, `source_readiness` in `LoadReport`, margin-label guard with test. 2 days.
3. generate.py: aligned CRM plus CPQ extract with planted disagreements on a new RNG stream. 1 day.
4. Neon migration `source_connections` and `source_field_coverage` with down and guard; scratch up/down/up output pasted. 1 day, migration before code.

Validate by running one design-partner export through the mapper and showing the source-coverage report. After that file arrives: usage events 4 days, cost lines 5, contract terms 3.

## 7. Open questions for the founder

1. Which source does the first design partner actually price in? That picks the first connector and whether billing or CPQ child entities come first.
2. Is physical-goods margin a funded near-term bet or a deferred adjacency? If deferred, ship only the `cost_basis` label guard and skip BOM and landed-cost tables.
3. May aggregate provenance and coverage (no row data) live in Neon, or must it stay in memory? This changes the audit story.
