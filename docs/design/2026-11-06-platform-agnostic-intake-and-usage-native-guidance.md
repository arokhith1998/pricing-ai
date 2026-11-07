---
title: Platform-agnostic intake and usage-native guidance, first increment
created: 2026-11-06
updated: 2026-11-06
tags: [design, product-direction, intake, ubp, decision-log]
status: draft
source: docs/reviews/2026-11-06-product-direction/ (BRIEF.md and nine reports)
---

# Platform-agnostic intake and usage-native guidance

Proposal. Nothing is dispatched until the founder answers section 5. Tasks: `docs/reviews/2026-11-06-product-direction/TASKS-proposed.md`.

## 1. Direction and what the reviews concluded

### The founder's words (BRIEF.md)

1. "Most of the deals are not done on Salesforce/HubSpot. So it should be like an add-on to any platform." Named surfaces: CPQ tools (DealHub, PandaDoc, Proposify, Salesbricks), billing and metering (Stripe, Chargebee, Maxio, Metronome, Orb), other CRMs (Pipedrive, Zoho, Close, Attio, Freshsales).
2. "Add more features to what it can do." All four: platform-agnostic intake, guidance wherever the rep works, the next pillars, usage-native pricing.
3. "With AI companies growing, usage based pricing is gonna fluctuate as physical AI ramps up, token cost might come down. Also, margin guidance: from BOM, shipping location, tax deals to evaluate the gross and net margin and pricing based on what each customer values."

### Where all nine agree

- **The engine is source-agnostic; the perimeter is not.** Coupling sits in `pricing/crm.py:58`, `api/routers/crm.py` (`source="salesforce_crm"`, line 583 filter) and `pricing/governance.py:459-496` (cto.md s1, backend-engineer.md s1, data-engineer.md s1).
- **No native connectors before a paid pilot.** File-first intake (cto.md s1, cfo.md s2, customer-success.md s2, market-sizing-analyst.md s3, web-engineer.md s2).
- **Billing data has no closed-lost deals,** so it cannot produce win rate by band. It enriches won deals only (cto.md s1, customer-success.md s2, ai-engineer.md s1).
- **Commit, ramp and overage are captured, never scored** (pricing-strategist.md s1, backend-engineer.md s1, ai-engineer.md s1).
- **BOM, landed cost and tax margin is Phase 3.** It meets one of five Phase-3 gates (market-sizing-analyst.md s1.4, pricing-strategist.md s1). Customer-supplied contribution margin, labeled with its basis, is the most any report supports for the SaaS wedge.
- **Pillars 2 to 4 and per-customer EVC are not first-increment work.** Pilot-size books cannot identify them (cto.md s3, cfo.md s1, customer-success.md s3).
- **Browser overlay is deferred** (web-engineer.md s2, cto.md s2).
- **The unified decision log is the compounding asset.** Ship it before any channel or each channel forks the record (web-engineer.md s5, cto.md s3).
- **Governance gaps:** no `docs/ops/data-register.md`; incident response never revokes customer integration credentials (cto.md s1, customer-success.md s1).

### Where they disagree

| Question | Positions |
|---|---|
| When to build | Strategist: build the lens now (pricing-strategist.md s4). CFO: only when a named usage-based prospect shares a billing export (cfo.md s4). CTO: not until a non-Salesforce prospect is named (cto.md s4). Customer success: no product work until one partner confirms pricing outside Salesforce or HubSpot (customer-success.md s6). |
| What first | Evidence (customer-success, market-sizing), contract and adapter (backend, 9d), provenance (data, 6d), mapper profiles (ai, 8d), quote screen (web, 8d plus 3d API), contract-structure lens (strategist and CFO). |
| Which platform | Founder: long-tail CRMs, CPQ, billing. Market analyst: by account count HubSpot is next; long-tail CRMs total 18 to 72 accounts (market-sizing-analyst.md s1.2). |
| Usage grain | Data engineer: a `usage_event` child entity, in memory (data-engineer.md s2.2). CTO: raw events never enter; only `contract_period_actuals` aggregates (cto.md s2). |
| Margin depth | Backend specifies a full cost book with net margin (backend-engineer.md s2c). Strategist declines net margin per deal (pricing-strategist.md s2). The three cost-basis enums differ (backend, data, ai). |
| EVC | Strategist: optional human-entered worksheet. AI: an `evc_calculator` corridor. CTO and customer success: consulting, not software. |

## 2. The decision for a first increment

**Prove the premise before building for it, then make the product source-neutral and usage-literate on the CSV path, with one surface that needs no integration.** Concretely:

1. **Evidence, no code (about 7 days).** Platform census, interview module, per-source data-readiness checklists, data register, incident-response amendment, NDA data-classes draft.
2. **Source-neutral refactor.** Canonical deal with provenance, Salesforce reduced to the first adapter, parameterized source tags with legacy aliases, saved per-tenant mapping presets (headers only), and a numeric-fidelity and cost-basis eval harness.
3. **Contract-structure lens.** Commit, ramp, overage and unit-rate floors scored deterministically on the CSV path. This is where the pricing-strategist (s4) and CFO (s4) converge: it is the only direction that grows the dollars a pilot recovers. The CFO's arithmetic: at $15M ARR a $15K pilot needs 1.33 points of realization in a quarter, and discount-only scoring misses waived overage and soft commits.
4. **Standalone quote screen plus unified decision log,** on one surface-neutral decision contract. This is where cto (s2), backend (s2d) and web (s2) converge: one contract, saved mapping presets, `/quote`, no channel yet.

**Why not the full direction.** The CFO prices it at 60 to 111 founder-weeks and $30K to $70K of third-party cash including SOC 2, against about 13 founder-weeks available in two quarters (cfo.md s2, s3). Breadth leaves ARR $0 and the February gate missed.

**Why measure before connectors.** The market analyst found no public data supporting "most deals are not on Salesforce or HubSpot" for $10M to $100M ARR SaaS. Working estimate (assumed): Salesforce plus HubSpot hold 75% to 85% of Tier A. The narrower truth is that the quote is often produced in a CPQ, while the record still lands in the CRM (market-sizing-analyst.md s1.1). Intake widens Tier A by at most about 120 accounts (s1.2). The CFO adds that CRM choice is not a Tier A gate, so connectors add zero accounts (cfo.md s1).

### Deferred, and why

| Item | Reason | Trigger to revisit |
|---|---|---|
| Native connectors (14 named) | 1.5 to 2 customers per connector over three years (cfo.md s1) | Census plus two paying or LOI accounts on one platform (cfo.md s2) |
| Billing API, usage events | Key custody; in-memory posture | A partner billing export validates the lens |
| Slack and email | Approver identity question unanswered | Partner runs three real quotes in a week on `/quote` (web-engineer.md s6) |
| Browser overlay | Brittle | Partner refuses both `/quote` and an API path |
| Pillars 2 to 4, multi-lever win model | Returns insufficient data at pilot scale | A partner book with populated levers |
| BOM, landed cost, tax margin | Phase-3 gate; Vendavo shipped there 2026-10-20 | Named manufacturer prospect plus Phase-3 gates |
| SaaS contribution margin | Founder decision D2 | D2 answered plus a partner supplying unit cost |
| EVC worksheet | Needs inputs no partner has ready | Large exceptions in a live pilot |

## 3. Architecture of the first increment

### 3.1 Canonical deal and provenance layer

`pricing/schema.py` gains optional fields, so every existing CSV still loads: `source_system` (enum, `csv` default), `source_record_id`, `source_account_id`, `source_quote_id`, `source_url`, `value_metric_unit` (free text beside the enum, per pricing-strategist.md s2) and `cost_basis` (default `crm_proxy`). Provenance stays an in-memory sidecar; only coverage aggregates reach the decision record (data-engineer.md s2.1). Child entities (`quote_line`, `invoice_line`, `contract_term`, `rate_card`) wait for a partner file. The web type `CanonicalCrmDeal` in `web/src/lib/salesforce-adapter.ts` becomes `CanonicalDeal`.

`pricing/crm.py` splits into `pricing/guardrail.py` (engine) and a thin Salesforce `to_canonical`. Source strings become `source.system`, with `salesforce_crm` and `salesforce_crm_writeback` read as aliases so existing `decision_log` rows still resolve. The adapter protocol (backend-engineer.md s2a) gets two implementations only: Salesforce and CSV.

Mapping: the mapper gains a deterministic "layer 0" source profile (crm_opportunity, cpq_line) with presets, line-to-quote roll-up, stage normalization into a closed enum, and a refuse path when an export cannot supply outcome (ai-engineer.md s2A). The confirmed mapping persists per tenant and source as header strings only, closing the deferral in `docs/design/richer-ingest.md`. Billing and usage profiles wait.

**Cost-basis enum, one ADR.** Backend, data and AI proposed three different enums. Before any margin code, `pk-lead` writes one ADR to `docs/agents/DECISIONS.md`. The proposal: `crm_proxy | declared_cost | erp_verified`, with label text owned by a response builder and a test that no payload says "margin" for `crm_proxy`.

### 3.2 Decision request contract

One endpoint, `POST /v1/decisions`. The CTO's `/decisions/request` and web's `/quote/guidance` collapse into it.

- Request: `request_id` (idempotency), `surface` (`quote_screen | crm | api`), `source {system, tenant_ref, record_id, url}`, `deal` (CanonicalDeal), `levers`, `book_ref`, `actor {id, assertion}`.
- Response: `decision_id`, `status (ok | insufficient_data | blocked)`, `verdict {method, levers[{lever, status: scored | insufficient_data | not_provided, current, recommended, reference, basis, band_counts}]}`, `why`, `caveats`, `evidence_version`, `allowed_actions`.
- `POST /v1/decisions/{id}/actions` reuses the existing event machine, self-approval block and fail-closed 503.
- `/crm/*` stays as a shim. No surface computes a number.

### 3.3 The per-tenant derived snapshot

Today `/crm/workflow` recomputes from the full submitted book on every call (backend-engineer.md s1). A Salesforce tenant can do that because the web tier pulls the book live. A CSV tenant has no book after the request ends, so `/quote` can only say "insufficient data". Three ways out, and this is founder decision D1:

- **Persisted aggregates:** band win rates, segment references, policy, `evidence_version`, n per band; no rows, no named comparables. This unblocks `/quote` for CSV tenants and every later channel. It changes the retention promise wording.
- **Client-held book (my inference, not proposed by a reviewer):** the browser keeps the parsed CSV in memory and resends it with each request. Retention stays unchanged, but it only works inside the web app and dies on reload.
- **Salesforce-only scoring:** `/quote` limited to Tier B (130 to 190 accounts).

### 3.4 Standalone quote screen

`/quote`: a typed form or one-row upload through the existing mapper. Then a confirm table with readable labels; no PDF or free-text extraction in v1. The `Recommendation` output follows, with method and confidence, and "insufficient data" is honored. The decision is recorded through `DecisionControl` to the tenant-scoped unified log, with `source.system = "manual"`. It is gated by `requireAccess()`, not the demo `requireLead()`. `/decisions` and `/decisions/[id]` give the deep link that Slack and email would later reuse. A `PLATFORM_STATUS` constant under `web/src/data/` feeds the landing, pricing and trust pages. Landing copy stays "Salesforce plus CSV" until `/quote` works on real non-Salesforce data (web-engineer.md s3).

### 3.5 Contract-structure lens

This is a new deterministic module, every output labeled `method: policy rule` (pricing-strategist.md s2, backend-engineer.md s2b). Commit, rate and ramp-adjusted discount are reported as separate levers, never blended:

- effective committed unit rate (`committed_acv / quantity`) and its realization against list
- commit share of booked
- overage-fence flag: `overage_rate` at or below the effective committed unit rate
- ramp depth and ramp concession dollars, with the TCV-weighted effective discount
- a revenue-side pocket waterfall: list, booked, ramp concessions, credits

Each lever returns `scored | insufficient_data | not_provided`, no global fallback. Decision-record fields capture each concession and what was traded for it. No model change, no cost input.

## 4. Hard rules that do not move

1. Explainability over accuracy. Every recommendation names its method.
2. Humans decide. No surface approves on its own; email links land on a confirm page.
3. The LLM never computes a number. It maps headers and stage strings, and it narrates.
4. Thin data returns "insufficient data", per lever, never a silent global fallback or a zero.
5. Row-level customer data is processed in memory and deleted. Only aggregates, header strings and the decision log persist.
6. CRM numbers are never called margin. "Margin" appears only with a non-proxy cost basis.
7. No claim on the site exceeds what ships. No em dashes.

## 5. Founder decisions required before dispatch

| # | Decision | Options and what each unblocks | Sources |
|---|---|---|---|
| D1 | Per-tenant derived snapshot versus the retention promise | (a) Persist aggregates: unblocks PK-37 and PK-38, `/quote` for CSV tenants, later Slack. Needs a register row and revised retention copy. (b) Client-held book: `/quote` in-app only, no channel. (c) Salesforce-only scoring: Tier B only. | backend s6 Q1, web s7 Q1, data s7 Q3, cto s2 |
| D2 | Margin target | (a) SaaS declared cost per usage unit, contribution margin labeled customer-supplied (2 to 6 days, after D2 and the ADR). (b) Phase-3 cost book, BOM, landed cost, tax (about 14 to 18 backend days plus 7 data days plus counsel); reopens the Phase-3 gate. (c) Neither now. Also: net margin is recommended against; is cost data accepted before signature? | backend Q3, strategist Q2 Q4, data Q2, cfo Q4, customer-success Q3, ai Q3, cto Q3, market Q2 |
| D3 | Is the first design partner's tool known? | Known: PK-27 is scoped to that tool's export, and the lens builds against its real file. Unknown: PK-27 waits on the census; the lens builds on synthetic fixtures only if the founder overrides the CFO timing rule. | cto Q1, backend Q2, data Q1, ai Q1, cfo Q3, strategist Q3, market Q1 |
| D4 | Census as the gate for any connector | Approve: no native connector until the census plus two paying or LOI accounts on one platform; HubSpot preset only if HubSpot is 30% or more of the census. Reject: presets for the founder's named platforms now. | market s4, cfo s2 |
| D5 | Guidance consumer: rep at quote time or approver at exception time | Rep: `/quote` is enough for pilot 1. Approver: Slack approve after `/quote`, about 5 to 8 more days. | cto Q2, web Q2, customer-success Q4 |
| D6 | Pilot shape | Accept a billing-only partner (leakage and realization, no win rate)? Sell a descriptive-only usage pilot at $15K before the lens ships? | customer-success Q1 Q2 |
| D7 | ICP | AI-native as lead ICP or a tag inside Tier A; physical-AI hardware plus usage now or Phase 3. | strategist Q1, market Q3, ai Q2 |
| D8 | Economics | Cash and burn; separate $5K to $10K implementation fee for non-CSV or cost-data onboarding. | cfo Q1 Q2 |
| D9 | DealHub: channel or competitor | DealHub scores quotes against look-alike deals. Decides whether a DealHub preset is built. | market Q4 |

## 6. Validation plan

One named design partner, CSV only, two sources at most (customer-success.md s5).

1. **Premise:** ten interviews with the new module plus the census. Pass: a named non-Salesforce, non-HubSpot system appears twice as the pricing surface (cfo.md s5 Q3).
2. **Intake:** the partner's export reaches a readout without hand-mapping, and the source-coverage report is shown (cto.md s4, data-engineer.md s6).
3. **Lens:** in the readout, recovered dollars per quarter exceed the $15K fee, reported against discount-only scoring (cfo.md s4); the deal desk names flags they would have acted on (pricing-strategist.md s4).
4. **Surface:** a deal desk member runs three real quotes in a week, and the recorded decision matches what they would have done (web-engineer.md s6). Recurring use means 3 or more decisions in each of weeks 4 to 12 from at least 2 requesters.

## 7. Not assessed

- Vendor API terms and sandbox costs (cto.md s1, cfo.md s2).
- CRM share for $10M to $100M ARR SaaS: no primary source; 75% to 85% is assumed.
- DPA execution: assumed not done (cto.md s1).
- How ingest treats unknown stage strings (ai-engineer.md s1).
- Mapper handling of one-to-many quote-line exports (customer-success.md s5).
- Whether DealHub's Price Optimization AI shipped (market-sizing-analyst.md s1.5).
- Willingness to pay for usage-native guidance: zero evidence.
- Effort figures are the reports' own. The `feat/crm-provider-schema` branch was not inspected for reuse.
