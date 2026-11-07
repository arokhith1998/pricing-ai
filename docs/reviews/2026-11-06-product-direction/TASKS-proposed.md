---
title: Proposed tasks, platform-agnostic intake and usage-native guidance
created: 2026-11-06
updated: 2026-11-07
tags: [tasks, proposal, product-direction]
status: active
source: docs/design/2026-11-06-platform-agnostic-intake-and-usage-native-guidance.md
---

# Proposed tasks

**Status 2026-11-07.** Founder answered D1 (a), D3 unknown, D4 approved. Phase A tasks PK-17 to PK-22 and PK-30 are on the board (`docs/agents/PROJECT_STATE.md`); PK-17, PK-18, PK-19, PK-20, PK-22 and PK-30 dispatched, PK-21 waits on PK-20 and PK-6. Owner changes on entry: PK-21 and PK-22 are drafted by customer-success and PK-30 by pricing-strategist, with the founder as approver, because the board needs an agent owner. Phases B to D stay proposed until the plan is approved.

Original proposal text follows. Nothing in Phases B to D enters `project_state.json` until the founder approves. Ids follow the board's PK-16. Days come from the reports. "Gate" names a founder decision (design doc section 5).

Notes on the board:
- Phase A paths (`gtm/`, `vault/`, `docs/ops/`, `docs/legal/`) sit outside the engineering task machine (OWNERSHIP.md), so they do not count against the cap of 2.
- **PK-21 collides with PK-6**, which is READY and claims `docs/ops/incident-response.md`. PK-21 waits.
- `pk-lead` writes ADR-006 (one cost-basis enum) before PK-29.

## Phase A: evidence, no code (7 days)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-17 | Publish a platform census of target accounts | market-sizing-analyst | none | `vault/Competitive/2026-11-06-platform-census-and-ai-native-sizing.md` | 4.5 | none |
| PK-18 | Add the pricing-surface interview module | customer-success | none | `vault/GTM/problem-interview-guide.md`, `docs/ops/funnel-tracker.csv` | 0.5 | none |
| PK-19 | Write per-source data-readiness checklists | customer-success | none | `gtm/data-readiness-checklists.md` | 1 | none |
| PK-20 | Create the data register | customer-success | none | `docs/ops/data-register.md` | 0.25 | none |
| PK-21 | Amend incident response for credentials and new data classes | founder | PK-20, PK-6 | `docs/ops/incident-response.md` | 0.25 | none |
| PK-22 | Draft the NDA data-classes schedule for counsel | founder | none | `docs/legal/one-page-mutual-nda-data-addendum.md` | 0.5 plus counsel | none (D2 shapes Class 3) |

Acceptance:
- **PK-17:** at least 48 accounts, each with CRM, CPQ and billing tool plus a public source. Shares given with n; unknowns marked unknown; HubSpot share stated against 30%.
- **PK-18:** the six questions of customer-success.md s4 sit after Q7. The tracker gains four columns: pricing surface, cost-data availability, commit-setting method, reprice event. No pitch language.
- **PK-19:** quote tool, billing and other CRM sections, column lists only. Each states the closed-lost gate and the shared-deal-ID question.
- **PK-20:** rows for deal rows, Salesforce refresh tokens, `SALESFORCE_TOKEN_ENCRYPTION_KEY`, decision log, mapping headers, and the snapshot (marked "pending D1"). Each row: location, retention, deletion owner.
- **PK-21:** containment revokes customer integration credentials and rotates the token key. Scope reads PK-20. Cost and usage data are named categories.
- **PK-22:** Classes 1 to 3 drafted; Class 3 is a percentage table, excluded from section 9 benchmarking; marked for counsel, not executed.

## Phase B: source-neutral refactor (16.5 days)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-23 | Add source, provenance and contract-structure fields to the canonical deal | data-engineer | none | `pricing/schema.py`, `pricing/ingest.py#numeric`, `pricing/mapping.py#synonyms`, `gtm/data-request.md`, `tests/test_schema_provenance.py` | 2 | plan approval |
| PK-24 | Add a migration for saved mappings and a decision-log source index | data-engineer | PK-23 | `neon/schema.sql`, `neon/migrations/2026-11-*-source-mappings*.sql` | 1 | plan approval |
| PK-25 | Make Salesforce the first adapter behind a neutral guardrail | backend-engineer | PK-23 | `pricing/crm.py`, `pricing/guardrail.py`, `api/routers/crm.py`, `pricing/governance.py#exception_source`, `tests/test_guardrail.py` | 3 | plan approval |
| PK-26 | Rename the web canonical type to CanonicalDeal | web-engineer | PK-25 | `web/src/lib/salesforce-*.ts` | 1 | plan approval |
| PK-27 | Add source profiles and export presets to the mapper | ai-engineer | PK-23, PK-17 | `pricing/mapping.py`, `tests/test_mapping_profiles.py`, `tests/fixtures/mapping_profiles/**` | 6 | D3, D4 |
| PK-28 | Persist the confirmed mapping per tenant, headers only | backend-engineer | PK-24, PK-27 | `pricing/mapping_store.py`, `api/routers/diagnostic.py#map_headers` | 1 | D3 |
| PK-29 | Add numeric-fidelity and cost-basis label evals | ai-engineer | ADR-006 | `tests/test_numeric_fidelity.py`, `tests/test_cost_basis_label.py` | 3 | none |

Acceptance:
- **PK-23:** all new fields are optional (`source_system`, source ids, `source_url`, `value_metric_unit`, `cost_basis` defaulting to `crm_proxy`, plus `list_unit_rate` and `credits_tcv` approved 2026-11-07 per the lens spec section 2: in `FIELDS` after `ramp_year_2_acv`, in ingest `_NUMERIC` and `_FX_MONEY_COLS`, mapper synonyms added, listed as optional in `gtm/data-request.md`). Existing fixtures load unchanged; pinned dataset byte-identical.
- **PK-24:** up and down, with a row-count guard; QA pastes scratch up/down/up output; no deal rows stored.
- **PK-25:** no "Salesforce" string remains in `guardrail.py`. Legacy `salesforce_crm` rows resolve; a CSV-sourced exception appears in the log filter; `tests/test_crm.py` and governance suites pass unchanged.
- **PK-26:** tsc, tests and build pass; `/crm` unchanged.
- **PK-27:** fixtures detect crm_opportunity and cpq_line profiles. Quote lines roll up to one deal; unknown stage goes to "ask user", never "lost"; refuse path fires without outcome; LLM payload holds headers only.
- **PK-28:** same headers skip confirmation; a test asserts no row values persist.
- **PK-29:** every figure in narrated text appears in the source dict. The word "margin" never appears when basis is `crm_proxy`.

## Phase C: contract-structure lens (9.5 days)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-30 | Specify the contract-structure lens | founder (pricing-strategist drafts) | none | `docs/design/2026-11-*-contract-structure-lens-spec.md` | 1.5 | none |
| PK-31 | Plant contract-structure answers in the generator | data-engineer | PK-23, PK-30 | `pricing/generate.py`, `tests/test_generate_contract.py` | 1 | D3 |
| PK-32 | Score commit, ramp, overage and unit-rate floors | backend-engineer | PK-31 | `pricing/contract_structure.py`, `tests/test_contract_structure.py` | 5 | D3 |
| PK-33 | Add the lens readout and concession fields to the decision record | backend-engineer | PK-32, PK-25 | `pricing/diagnostic.py#readout`, `pricing/governance.py#concessions`, `api/routers/diagnostic.py#response` | 2 | D3 |

Acceptance:
- **PK-30:** formulas, labels and thresholds per lever; `method: policy rule`; no cost input.
- **PK-31:** new RNG stream, pinned dataset unchanged; known-answer key for overage-fence and ramp-concession cases.
- **PK-32:** planted answers recovered; each lever returns `scored | insufficient_data | not_provided`, no global fallback; flat ramp equals flat discount; nothing labeled margin.
- **PK-33:** readout lists the deals behind each flag; concession fields round-trip through the decision log.

## Phase D: quote screen and unified decision log (14.5 days)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-34 | Ship POST /v1/decisions and actions, with /crm as a shim | backend-engineer | PK-25, PK-32 | `api/routers/decisions.py`, `api/main.py#routers`, `api/routers/crm.py`, `tests/test_decisions_contract.py` | 3 | none |
| PK-35 | Unify the decision log with source, deep links and PLATFORM_STATUS | web-engineer | PK-34, PK-26 | `web/src/components/Decision*.tsx`, `web/src/app/decisions/**`, `web/src/app/api/decisions/**`, `web/src/data/platform-status.ts`, `web/src/components/Nav.tsx`, `web/test/decisions.test.ts` | 3 | none |
| PK-36 | Ship the standalone quote screen | web-engineer | PK-35 | `web/src/app/quote/**`, `web/src/app/api/quote/**`, `web/src/components/Guidance*.tsx`, `web/src/components/Nav.tsx`, `web/test/quote.test.ts` | 5 | D1 |
| PK-37 | Add a migration for the derived snapshot table | data-engineer | PK-24 | `neon/schema.sql`, `neon/migrations/2026-11-*-book-snapshot*.sql` | 0.5 | D1(a) |
| PK-38 | Build BookSnapshot from aggregates, with no rows or named comparables | backend-engineer | PK-37, PK-34 | `pricing/snapshot.py`, `api/routers/decisions.py#snapshot`, `tests/test_snapshot.py` | 3 | D1(a) |

Acceptance:
- **PK-34:** JSON-schema snapshot of request and response; replayed `request_id` is idempotent; self-approval block and fail-closed 503 kept; `/crm/*` tests pass.
- **PK-35:** `requireAccess()`, not `requireLead()`; one log with a `source` filter; `/decisions/[id]` renders `DecisionCard`; landing, pricing and trust read `PLATFORM_STATUS`; landing copy unchanged.
- **PK-36:** confirm table before scoring; no PDF or free-text extraction; "insufficient data" with no book; logged as `source.system = "manual"`; eslint, tsc, build pass.
- **PK-38:** a test asserts no row values or account names in the snapshot; `evidence_version` stamped.

**Totals:** 22 tasks, 48 days (PK-23 grew by 0.5 day on 2026-11-07 for the two lens fields). Phase A (7 days) and PK-30 need no answer. Without D1(a), drop PK-37 and PK-38: 20 tasks, 44 days.

## What can run in parallel

- **Now:** PK-17, PK-18, PK-19, PK-20, PK-22 and PK-30 together (disjoint files, outside the cap). PK-21 follows PK-20 and PK-6.
- **Phase B:** PK-23 first (schema serializes). Then two at a time: PK-25 with PK-27 or PK-24. PK-29 any time after ADR-006.
- **Must sequence:**
  - PK-35 before PK-36, because both claim `Nav.tsx`.
  - PK-24 before PK-37, because both claim `neon/schema.sql`.
  - PK-25 before PK-34, because both claim `api/routers/crm.py`.
  - PK-23 before PK-31, because of the schema ripple.

## Not now

| Item | Reason | Trigger to un-defer |
|---|---|---|
| Native CRM, CPQ or billing connectors | 1.5 to 3 founder-weeks each, zero added Tier A accounts (cfo.md s1) | Census plus two paying or LOI accounts on one platform |
| HubSpot deals preset as native surface | Unmeasured share | PK-17 shows HubSpot at 30% or more |
| Billing and usage profiles, `contract_period_actuals` | No partner file; key custody risk | A partner shares a billing export after PK-32 |
| Child entities `quote_line`, `contract_term`, `rate_card` | Shape unknown | First real partner export |
| Slack approve, email notify (5 to 8 days) | Approver unknown (D5) | Three real quotes in a week on `/quote` |
| Browser overlay (10 to 15 days) | Brittle | Partner refuses `/quote` and API |
| SaaS contribution margin (2 to 6 days) | D2 open | D2(a) plus a partner supplying unit cost |
| BOM, landed cost, tax cost book | Phase-3 gate unmet | Named manufacturer prospect plus Phase-3 gates |
| EVC worksheet or corridor | No inputs exist | Large exceptions in a live pilot |
| Multi-lever win model, pillars 2 to 4 | Insufficient data at pilot scale | A partner book with populated levers |
| Token-cost deflation scenarios | Needs billing actuals | After the lens and billing profile ship |
