---
title: Proposed tasks, audit-first motion and the AI margin wedge
created: 2026-11-10
updated: 2026-11-10
tags: [tasks, proposal, audit-first, ai-margin, lead-magnet, gtm]
status: entered
source: gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md; vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md
---

# Proposed tasks: audit-first motion and the AI margin wedge

Founder instruction 2026-11-10: start on both filled tabs of the research sheet (Consumer Trends,
Opportunity). This file decomposes what follows the first drafts already dispatched today. Ids
PK-94 to PK-111. All eighteen are on the board in BACKLOG; only PK-94 is READY (see "What is
ready"). Format follows `docs/reviews/2026-11-06-product-direction/TASKS-connectors-proposed.md`.

## Not tasks here (dispatched today, first deliverables only)

| Workstream | Agent | First deliverable | Status at 2026-11-10 |
|---|---|---|---|
| Paid audit offer, 14-day runbook, data request | customer-success | `gtm/ai-margin-audit-offer.md`, `gtm/ai-margin-audit-runbook.md`, `gtm/ai-margin-audit-data-request.md` | offer and runbook on disk, uncommitted; data request not yet seen |
| AI-founder interview module, targets, first touches | sales-outreach | interview module and messages | not yet seen |
| LinkedIn series from the Consumer Trends memo | social-media-manager | draft series | not yet seen |
| ICP narrowing and the $2,500 a month anchor | pricing-strategist, cfo | reviews | strategist committed (`pricing-strategist-review.md`, this folder); cfo not yet seen |
| Calculator design doc | web-engineer | "AI pricing and margin audit" design doc | not yet seen |
| Margin-health design doc | backend-engineer | margin-health design doc | not yet seen |

These are off the board, so a task that follows one cannot name it in `--depends`. Each such task
carries an acceptance line beginning "Gate:" and stays in BACKLOG until the gate is met, even where
`agentctl ready` would accept it.

## What I inspected versus assumed

Inspected on `origin/main` (4f6f33b) and the org branch: `pricing/billing.py` (the grain has no
end-customer id; an account is one subscription), `pricing/cost_basis.py`, `pricing/schema.py`
(`CONTRACT_PERIOD_FIELDS` carries no cost field), layer-0 profiles in `pricing/mapping.py` and
their routing in `pricing/ingest.py`, `web/src/app/api/lead/route.ts`, `web/src/lib/store.ts#saveLead`,
the `leads` table in `neon/schema.sql` (no source or magnet column), the live and backlog claims
from `agentctl status`, the runbook and offer drafts, and the strategist review.

Assumed: the two design docs will land at `docs/design/2026-11-10-*.md`; the calculator computes in
the browser so no visitor number reaches the server (if the web design doc chooses a server route,
PK-107 gains `web/src/app/api/margin-audit` at assignment); the readout lives on a new gated route
`/margin` rather than inside `/upload` or `/crm`, to stay clear of PK-81, PK-59 and PK-83.

## Three findings that shape the plan

1. **Margin computation is still gated on D2.** The 2026-11-06 design doc lists D2 (margin target)
   as open, ADR-006 says so, and the runbook draft says "do not add margin computation to the
   product until D2 is settled". The 2026-11-10 decision adds the wedge to the thesis but does not
   answer D2. Every engine task (PK-99 to PK-105) carries "Founder gate: F1".
2. **ADR-006 and the decision record disagree on the basis of a cost CSV.** ADR-006 files any
   cost that arrives by CSV under `crm_proxy`; the decision record and runbook call a founder-supplied
   cost export `declared_cost`. Proposed resolution: ADR-007 in `docs/agents/DECISIONS.md`
   (status proposed), decision F2.
3. **There is no join key.** Billing rows are per subscription with no customer id; cost exports
   are per API key, project or workspace. The join needs a customer-declared key map, and
   unmatched cost must surface as an unallocated line. Written into ADR-007 and PK-101, PK-102.
4. Also: the per-customer cost rollup is outside NDA Class 3 as drafted (the offer draft's
   blocker 1). PK-96 adds it for counsel; no real cost file is received before counsel clears it.

## 30-day checklist mapped to tasks

| Checklist item (Opportunity tab) | Already dispatched | Board tasks | Founder-only |
|---|---|---|---|
| 10 to 15 AI-founder interviews | sales-outreach module and touches | PK-95 tracker columns, PK-94 predicted objections, PK-98 synthesis | runs every call; sends every message |
| 2 to 3 paid manual audits | customer-success offer, runbook, data request; strategist and cfo price review | PK-96 data class for counsel, PK-97 delivery template and workbook spec, PK-95 audit columns | F3, F4, F5, F9; engagement letter; invoices |
| 3-screen clickable prototype | none | PK-111 (after the first audit, on synthetic data) | picks the audit whose method it mirrors |
| "AI pricing and margin audit" calculator | web-engineer design doc | PK-107 formula module, PK-108 migration, PK-109 lead tag, PK-110 page | F6, F7, F8; applies PK-108 migration to prod Neon |
| Product follow-through (margin wedge) | backend-engineer design doc | PK-99 to PK-105 engine, intake, API, readout; PK-106 cost connector spec | F1, F2 |

## Tasks

Doc-only under ADR-003 (every owned path under `gtm/`, `docs/` or `vault/`, so no concurrency slot,
completed on the org branch per the 2026-11-09 amendment): **PK-94, PK-95, PK-96, PK-97, PK-98,
PK-106.** Everything else is a coding task and counts against the cap of four.

| Id | Title | Owner | Deps | Owns | Gate |
|---|---|---|---|---|---|
| PK-94 | Seed the objection inventory with the audit-motion objections, marked predicted | sales-outreach | none | `gtm/objection-inventory.md` | none |
| PK-95 | Add audit-motion columns to the funnel tracker | customer-success | PK-18 | `docs/ops/funnel-tracker.csv`, `docs/ops/funnel-tracker-example.csv` | none |
| PK-96 | Add the per-customer cost rollup data class to the addendum and the data register, for counsel | customer-success | PK-22, PK-20 | `docs/legal/one-page-mutual-nda-data-addendum.md`, `docs/ops/data-register.md` | counsel |
| PK-97 | Write the audit delivery template and the workbook spec mapped to the method log | customer-success | none | `gtm/ai-margin-audit-delivery-template.md`, `gtm/ai-margin-audit-workbook-spec.md` | runbook and offer drafts accepted |
| PK-98 | Synthesise the AI-founder interviews and promote heard objections | pricing-strategist | PK-94, PK-95 | `vault/GTM/2026-11-ai-founder-interview-synthesis.md`, `gtm/objection-inventory.md` | 8 interviews logged |
| PK-99 | Add the customer cost-period grain and plant a cost answer key | data-engineer | none | `pricing/schema.py#cost_period`, `pricing/generate_billing.py#cost_periods`, `tests/test_schema_cost_period.py` | F1, F2, backend design doc |
| PK-100 | Recognise cost exports as a layer-0 source profile | ai-engineer | PK-99 | `pricing/mapping.py#profiles`, `tests/test_mapping_cost_profile.py` | none beyond deps |
| PK-101 | Load a declared cost export with its key map and attribution flags | backend-engineer | PK-99, PK-100 | `pricing/ingest.py#cost_export`, `tests/test_ingest_cost_export.py` | none beyond deps |
| PK-102 | Compute per-account contribution margin from billing and declared cost | backend-engineer | PK-99 | `pricing/margin_health.py`, `tests/test_margin_health.py` | none beyond deps |
| PK-103 | Verify margin health against the planted key and the cost-basis label evals | qa-engineer | PK-101, PK-102 | `tests/test_margin_health_known_answer.py`, `tests/test_cost_basis_margin_health.py` | none |
| PK-104 | Serve margin health from POST /margin/analyze | backend-engineer | PK-101, PK-102 | `api/routers/margin.py`, `api/main.py#routers`, `tests/test_margin_api.py` | none |
| PK-105 | Show the margin-health readout in the workspace | web-engineer | PK-104 | `web/src/app/margin/page.tsx`, `web/src/components/MarginHealthReadout.tsx`, `web/src/lib/api.ts#margin`, `web/test/margin-readout.test.ts` | none |
| PK-106 | Specify the first cost connector from what audit customers actually export | cto | PK-101 | `docs/design/2026-11-cost-connector.md` | 2 audits delivered |
| PK-107 | Compute the calculator figures in a pure module with code-owned labels | web-engineer | none | `web/src/lib/margin-audit.ts`, `web/test/margin-audit.test.ts` | web design doc |
| PK-108 | Add a lead_magnet column to leads, with a down migration | data-engineer | none | `neon/schema.sql`, `neon/migrations/2026-11-11-leads-lead-magnet.sql`, `neon/migrations/2026-11-11-leads-lead-magnet.down.sql`, `neon/MIGRATIONS.md`, `neon/test_migrations.py` | F7, web design doc |
| PK-109 | Tag calculator leads on /api/lead and in the lead form | web-engineer | PK-108 | `web/src/app/api/lead/route.ts`, `web/src/lib/store.ts#saveLead`, `web/src/components/LeadForm.tsx`, `web/test/lead-magnet.test.ts` | PK-80 merged (lead rule) |
| PK-110 | Ship the AI pricing and margin audit calculator page | web-engineer | PK-107, PK-109 | `web/src/app/margin-audit`, `web/src/components/MarginAuditCalculator.tsx`, `web/src/app/sitemap.ts`, `web/test/margin-audit-page.test.ts` | F6, F8 |
| PK-111 | Build the three-screen clickable audit prototype on synthetic data | web-engineer | PK-97, PK-107 | `web/src/app/prototype`, `web/test/prototype-audit.test.ts` | first audit delivered |

### Acceptance

- **PK-94:** a new section scoped "AI margin audit motion" is added and the existing ten objections
  and their ICP paragraph are byte-identical; each new objection is tagged `predicted` (from the
  Consumer Trends memo) and names the bottleneck number it comes from; at least these appear: "we
  will do it in a spreadsheet", "our cost data is too sensitive", "we cannot attribute inference
  cost per customer", "$X is too much for a seed company", "you will tell us to throttle our best
  users"; no answer cites a figure from the founder sheet as fact or claims a customer or result; no
  em dashes.
- **PK-95:** columns added for `motion(diagnostic/audit)`, `interview_date`, `audit_offer_sent`,
  `audit_fee_quoted`, `audit_paid_date`, `data_received_date`, `attribution_method(A/B/C/D)`,
  `audit_delivered_date`, `audit_hours`, `converted_to_subscription`; every existing column keeps its
  name and order; the example file shows one synthetic audit row and one synthetic interview row and
  no real company; the header line of both files is identical.
- **PK-96:** Schedule A gains a class for per-customer cost rollups keyed by a pseudonymous customer
  code (no names, emails or raw usage events), with retention and deletion matching Class 2; the
  existing classes' wording is unchanged; the data register gains a row for the audit workbook and
  the cost export with location, retention and deletion owner; the file is marked for counsel and
  not executed; Gate line: no real cost file is requested before counsel clears this class.
- **PK-97:** Gate: starts only after the founder accepts the customer-success offer and runbook
  drafts. The template has the readout sections the runbook's Day 11 names, and every figure slot
  carries its ADR-006 label from `pricing/cost_basis.py` verbatim; every workbook formula is written
  over named ranges, cites a method-log field, and names the candidate function in
  `pricing/margin_health.py` it becomes; allocated and unallocated cost are separate lines; no
  customer data and no em dashes.
- **PK-98:** Gate: the founder has logged at least 8 interviews in the tracker. The note cites each
  interview by tracker row only (no names); it reports how many of the logged founders could
  attribute inference cost per customer, what they use today, and any price they named; objections
  heard in two or more interviews move from `predicted` to `heard` in `gtm/objection-inventory.md`
  with counts; it states a recommendation on F3 (ICP) backed only by the logged counts.
- **PK-99:** Founder gate: F1 and F2 answered, and the backend design doc accepted. A cost-period
  grain is added beside `CONTRACT_PERIOD_FIELDS` with cost key, period start and end, currency,
  cost amount, cost category (inference, hosting, storage, other) and attribution
  (direct, rolled_up, allocated); it has no end-customer name or email field; the generator plants
  a cost book against the existing billing answer key with at least one negative-margin account, one
  unmatched cost key and one allocated row, and writes the expected per-account result; the
  existing billing generator output and the PK-53 key are byte-identical.
- **PK-100:** `profile_source` returns a `cost_export` profile for a generic cost table and for
  at least two provider usage-export header sets cited from current public docs with links in the
  PR; no cost header set is ever profiled as `crm_opportunity` or `cpq_line` (test); existing
  profile tests pass unchanged.
- **PK-101:** an upload without the per-upload declaration loads as `crm_proxy` and yields no
  margin; with it, `declared_cost`; any `erp_verified` value on upload raises `SchemaError`; the key
  map is required and every cost key absent from it is reported as unallocated with its count and
  share of cost; rows are rollups only and a file with event-level rows is refused; existing ingest
  suites pass unchanged.
- **PK-102:** per account and per period, contribution margin equals invoiced amount minus
  attributed cost in Decimal to the cent; every figure carries `cost_basis.label_for` text and the
  function calls `refuse_margin_for_proxy` on `crm_proxy` input; unallocated cost is its own line and
  is never spread silently; accounts whose sign flips between direct and allocated attribution are
  marked `uncertain`; the cost-tail output (share of cost by decile) is reported beside revenue rank;
  pure, no I/O, no LLM, and no net margin for any basis.
- **PK-103:** the planted answer key from PK-99 is recovered exactly, not within a tolerance;
  `margin_violations` reports zero across every output string on `declared_cost` and refuses on
  `crm_proxy`; a test asserts no output contains "gross margin" unless the basis is `erp_verified`;
  the full Python suite passes; real output is pasted with the CI run id.
- **PK-104:** `POST /margin/analyze` takes billing periods, a cost export and a key map in memory and
  stores no row (test asserts no database write); a `crm_proxy` request returns 422 naming the
  basis, not a caveated figure; the rate limit and perimeter match `/diagnostic`; the claim on
  `api/main.py#routers` is held only while PK-56 does not hold it.
- **PK-105:** `/margin` is gated the same way `/upload` is; every figure shows its ADR-006 label from
  the API response, never a label written in the component (test); unallocated cost and the
  `uncertain` accounts are shown, not hidden; an API error renders the existing error component, not
  a blank panel; eslint, tsc, `npm test` and build pass.
- **PK-106:** Gate: two audits delivered and their method-log learnings committed. The spec names the
  provider to connect first and why, citing the method log's attribution methods, not assumptions;
  states which basis the connector earns under ADR-006 and ADR-007 and how credentials follow
  PK-42 and PK-44; lists the implementation tasks with owners and claims for entry.
- **PK-107:** Gate: the web design doc is accepted. Pure functions with no network call; known-answer
  tests for at least four input sets including a zero-cost and a negative-margin case; the result
  shows each component with its formula and no single opaque score; label strings are pinned to
  `pricing/cost_basis.py` by a test the way `SourceSystem` is pinned; no statistic from the founder
  sheet appears in the module.
- **PK-108:** Founder gate: F7. `leads.lead_magnet text not null default ''` is added with a
  `.down.sql` that drops only that column; `neon/schema.sql` matches the migrated state;
  `neon/MIGRATIONS.md` gains rows for this pair and the PK-24 and PK-41 pairs it lacks; QA pastes
  scratch up, down, up output; the founder applies it to production Neon, no agent does.
- **PK-109:** Lead rule: not assigned until PK-80 is MERGED. `/api/lead` accepts an optional
  `lead_magnet` from an allowlist and stores '' for anything else; every existing lead-route
  behaviour is unchanged, including the honeypot's byte-identical 200 (existing tests pass);
  `LeadForm` takes an optional prop and renders identically without it; no calculator input value is
  sent or stored.
- **PK-110:** the page uses PK-107 for every number and PK-109 for capture; inputs never leave the
  browser (test asserts the only request is the lead post); copy names its basis as "customer-supplied
  cost" and passes the cost-basis guard; no figure from the founder sheet, no customer claim, no em
  dashes; the landing hero and nav are untouched (F6); added to the sitemap; eslint, tsc, `npm test`
  and build pass.
- **PK-111:** Gate: the first audit is delivered. Three screens (input, diagnostic, recommendation)
  on synthetic data only, `noindex`, not in the nav or sitemap; the diagnostic screen uses PK-107
  and the recommendation screen states that the customer decides; no real customer value anywhere;
  eslint, tsc, `npm test` and build pass.

## Dependencies, parallelism and claims

Data flows: cost grain (PK-99), then profile (PK-100) and engine (PK-102) in parallel, then intake
(PK-101), then API (PK-104) and QA (PK-103) in parallel, then UI (PK-105). The calculator track
(PK-107, PK-108 in parallel, then PK-109, then PK-110) shares no file with the engine track and can
run beside it.

Overlaps with existing claims, each resolved by sequencing, none by widening:

- `docs/ops/funnel-tracker*.csv`: PK-18 holds it in REVIEW; PK-95 depends on PK-18.
- `docs/legal/one-page-mutual-nda-data-addendum.md`: PK-22 in REVIEW, PK-45 in BACKLOG. PK-96
  depends on PK-22 and PK-20; `assign` serializes it against PK-45. Recommended order: PK-96 first,
  because audits need it sooner than connectors need PK-45.
- `docs/ops/data-register.md`: PK-20 in REVIEW, PK-44 in BACKLOG; same treatment.
- `gtm/objection-inventory.md`: PK-94 then PK-98 by dependency.
- `api/main.py#routers`: PK-56 claims the same component; whichever is assigned first holds it.
- `neon/schema.sql`: PK-70 also claims it; PK-70 is gated on seven days of prod, so PK-108 goes first.
- `web/src/components/LeadForm.tsx`: PK-80 claims it; lead rule above.
- `pricing/ingest.py#cost_export` and PK-40's `#profiles` are disjoint components;
  `pricing/mapping.py#profiles` has no live claim; `web/src/lib/store.ts#saveLead` is disjoint from
  PK-43's `#access_codes`.

## What is ready

Only **PK-94**: no board dependency and no gate, since it seeds from the committed memo. PK-97,
PK-99, PK-107 and PK-108 have no board dependency but each waits on a draft, a design doc or a
founder decision, so they stay in BACKLOG. Move each with `agentctl ready` when its gate line is
met. Nothing is assigned or dispatched by this entry.

## Founder decisions

| Id | Decision | Recommendation | Gates |
|---|---|---|---|
| F1 | Answer D2 for the margin wedge | Yes, narrowly: D2 option (a) extended to per-customer cost rollups; contribution margin only, `declared_cost` or `erp_verified` only, never net margin. | PK-99 to PK-105 |
| F2 | Accept ADR-007 | Accept: a cost export earns `declared_cost` only by a per-upload declaration, joins through a declared key map, unmatched cost shown as unallocated. | PK-99 onward |
| F3 | ICP wording on the site | Keep the $10M to $100M band and the site as is. Run the narrow AI ICP in the new motion only, defined (per the strategist) as AI-native usage or hybrid companies in the band, with seed to Series A as a paid-audit learning segment. Revisit with PK-98's counts. | any site copy task |
| F4 | Audit price | Fixed fee, fixed 14-day scope, credited against year one if they subscribe within 60 days, never free. Test the strategist's $5K, $7.5K, $10K ladder; wait for the cfo review before quoting. Do not publish $2,500 a month until one audit yields a finance-signed baseline. | offer leaves the vault |
| F5 | Share-of-lift terms | Not offered in the first audits. Later: platform fee floor plus a capped share measured against a constant-unit-price baseline signed by the customer's finance owner. | none now |
| F6 | Does the margin wedge change the landing hero | No. PK-76 just merged. The wedge lives on `/margin-audit` and in content for 90 days; pick one wedge statement after two audits. | PK-110 copy |
| F7 | Calculator lead capture | Result shown ungated; the emailed breakdown sits behind the existing full lead form tagged `lead_magnet`, so revenue range keeps testing F3. Founder applies the PK-108 migration. | PK-108, PK-109 |
| F8 | "Autonomous outcome engine" label (Labelling tab) | Reject for now: it contradicts humans in the loop and the "we recommend, you decide" line in every readout. | PK-110, content |
| F9 | Receiving real cost data | No per-customer cost file before counsel clears PK-96, the entity exists, and E&O and cyber cover is bound (offer draft blockers 1 to 3). | first audit |

## Open questions

1. Where will the two design docs land, and will the calculator need a server route? PK-107's
   claim changes if so.
2. Should the margin-health readout also show contract-structure fields (commit utilization,
   overage) from PK-32? The strategist says margin health without them mis-serves this segment.
   Not scoped here; the backend design doc should say.
3. Content follow-on after the social drafts is not entered; GTM content stays outside the task
   machine unless the founder wants it tracked.
