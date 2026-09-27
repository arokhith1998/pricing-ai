# Pricekeel whole-tool evaluation, fifteen agent lenses

Date: 2026-09-26. Read-only pass. Each agent wrote its own report; the full
texts are in docs/reviews/2026-09-26-agent-reports/. This file is the synthesis.

Agents run: cto, cfo, pricing-strategist, market-sizing-analyst, code-reviewer,
mle-reviewer, silent-failure-hunter, qa-engineer, backend-engineer, ai-engineer,
data-engineer, web-engineer, customer-success, sales-outreach, pk-lead.
Not run: llama-pitch (drives an external CLI), social-media-manager (not about
the tool).

## Bottom line

The engine is more honest than the business around it. Every agent, including
the harshest critics, praised the same things: LoadReport disclosure, method
labels on every verdict, the SSRF-hardened fetcher, the fail-closed perimeter,
and a company that cut its own SAM by 6x against its interest. Nobody called
the foundation unsound.

The verdict is conditional, and the conditions cluster into four groups:

1. The headline leakage number does not tie out and is biased upward.
2. The recommended discount is the least validated number in the system.
3. Multi-tenancy and actor identity are placeholders, so the audit trail is a
   demo artifact until fixed.
4. The commercial motion has not moved: zero real funnel rows, stale ICP
   collateral, unsignable legal paper, no installable Salesforce package.

## Read this first: the checkout is stale

The working branch feat/agent-engineering-org is 6 commits behind and 23 ahead
of origin/main. It predates PK-1 (router split), PK-5 (Anthropic only), and
PK-15 (monotone win model). Several agents read this tree. The following
findings are stale-branch artifacts and are already fixed on main:

- assist.py defaulting to OpenAI (ai-engineer F1, cfo F5 tail). Main is
  Anthropic only.
- model.py lacking the monotone constraint (pricing-strategist F4). Main has it.
- api/main.py as a 1408-line monolith (pk-lead F2, OWNERSHIP.md staleness).
  Main has api/routers/*.

Everything below was re-checked against origin/main unless marked otherwise.

## Verified state

| Check | Result |
|---|---|
| Python suite | 279 passed, 0 failed |
| Web lint, tsc, tests, build | all clean, 11 web tests pass |
| CI on main | run 35029845998, green |
| CI on this branch | run 35033658978, green |
| Open PRs | 7 (#62 org, #61 tenant key, #60, #59, #38, #37, #36) |

## Convergent findings, ranked

Severity reflects how many independent lenses hit the same thing and whether
it was reproduced.

### 1. The leakage headline uses three reference bases and is biased up
Raised by cfo, pricing-strategist, backend-engineer, market-sizing-analyst.
Verified on main.
- pricing/metrics.py:298 relaxes the 15-deal floor to 1 when no band clears it,
  so sparse books collapse the reference to 0% and all discount reads as
  leakage. Global reference has no sufficiency gate; segments do (100 deals).
- pricing/metrics.py:320 sets the threshold at the band floor, so discount
  inside the winning band is charged as excess.
- pricing/metrics.py:546 (defended_vs_investigate) and :655 (trend_by_quarter)
  use the global reference while leakage() and top_leak_deals use the
  segment-aware one. A CFO reconciling sections will find they disagree.
- web/src/app/sample/page.tsx:146,292 and UploadClient.tsx:109 render the
  global excess_vs_reference_won, which the engine itself says overstates
  (11.2M vs 8.95M on the bundled sample, a 25% overstatement in the lead gate).
- PK-16 confirmed: no BU or product-line reference table exists at all.
- Policy simulations and copilot recoverable shares overlap and are presented
  as additive.

Fix: one per-deal reference everywhere, explicit insufficient_data state,
threshold at the in-band median, re-point every public surface at the
segment-aware figure, print a non-additive line.

### 2. The recommended discount is in-sample, miscalibrated, and extrapolated
Raised by mle-reviewer (measured with probe scripts against main),
code-reviewer.
- pricing/model.py:105 random stratified split on time-ordered deals; params
  tuned on that split. Time-split AUC 0.564, Brier skill negative (worse than
  quoting the base rate).
- Calibration gate cannot fail: a constant predictor passes test_model.py:59-63.
- Grid sweeps 0 to 40% for every deal; 85% of Enterprise recommendations fall
  below the 5th percentile of observed Enterprise discounts.
- SHAP panel explains the current discount, headline shows the recommended one;
  top factor differs in 14% of deals.
- /recommend ships dollar uplift without the correlational caveat every other
  surface carries (code-reviewer; not independently verified).
- An unmerged branch, agent/ai-engineer/fix-time-split-silent-failures, already
  does the time split and retune but has no PK id, PR, or CI run.

Fix: land the time split branch under a PK id, add Brier-skill and per-segment
calibration gates, clip the grid to cohort support, explain the recommended row.

### 3. Tenant and actor identity are placeholders
Raised by cto, code-reviewer, data-engineer, customer-success.
- neon/schema.sql:47 customer_ref defaults to the literal 'default'; every
  lead-gated visitor shares one bucket and can read other visitors' typed
  names and justifications back from GET /exceptions. Justification length is
  uncapped.
- api/routers/crm.py:219 records actor_assertion self_asserted; segregation of
  duties is a string compare on typed names.
- _DOC_STORE keyed on client session_id alone, no customer check on /ask.
- governance.py:137-161 degrades a failed audit write to process memory and
  returns persisted False; nothing blocks or alerts.
- No evidence_version on verdicts despite the acceptance criteria promising one.
- PR #61 (opaque tenant key) has been open since 2026-08-22.

Fix: merge #61, per-user identity with approver allowlist, fail closed on CRM
workflow writes, evidence_version hash, tenant-scope the doc store.

### 4. Weekly digest miscounts CRM activity (reproduced)
Raised by code-reviewer. Verified on main: governance.py:435-437 counts every
kind=exception row, including approvals and Salesforce writeback receipts, and
reads below_floor which the CRM path never sets. One override plus its approval
plus one receipt renders as 3 requests, 0 below floor. This is emailed.

Fix: filter to request events, exclude writeback source, read outside_guardrail
too, add a known-answer test.

### 5. Silent failures in the LLM-adjacent stack
Raised by silent-failure-hunter, ai-engineer, qa-engineer.
- copilot.py get-or-0 pattern turns a missing key into a zero into "no
  opportunity" with no log; copilot, rag, mapping, matching do not import
  logging at all.
- rag.py web_search swallows provider errors and reports usedWeb false,
  indistinguishable from "web not needed".
- matching.py returns empty plans on SSRF block, fetch error, or parse error
  with no per-URL status; extracted competitor prices are never checked
  against page text.
- /ask forwards analysis arrays containing account names and opportunity ids
  to the provider while three docstrings promise row-level data never leaves.
- No tests exist for rag.py, mapping.py, or docs.py.

Fix: missing-vs-zero sentinel, logging in all four modules, tri-state web
status, per-URL match status, strip deal-level arrays in rag.ask, write
test_rag.py with an injection fixture.

### 6. Usage-based pricing is schema decoration
Raised by cto, backend-engineer, pricing-strategist, market-sizing-analyst.
committed_acv, overage_rate, ramp_year_* exist in pricing/schema.py:121-140 and
are read by nothing that makes a decision. The Salesforce adapter has no such
fields. The landing page sells usage and hybrid SaaS. Either state plainly that
V1 governs discount on CRM contract values, or build the value-metric cell into
the per-deal reference before quoting Tier A as usage-native.

### 7. Data layer gaps
Raised by data-engineer, qa-engineer.
- The only migration on main has no down file; the guarded pattern exists on
  two unmerged branches.
- No currency column; mixed $ and EUR books warn, then sum as one number.
- decision_log has no tenant-scoped index; leads has no email uniqueness.

### 8. Perimeter and scaling nits
Raised by backend-engineer, code-reviewer.
- /crm/* JSON bodies bypass the upload byte cap until after full deserialization.
- /recommend is the one uncapped model-cost endpoint.
- Rate limiter keys on X-Forwarded-For, which the Next proxy never forwards, so
  all customers share one bucket; single-process dict, so limit times workers.
- reference_discount bootstrap recomputed roughly a dozen times per run; a fresh
  DB connection per store operation.

### 9. Commercial and org state
Raised by sales-outreach, customer-success, cfo, market-sizing-analyst, pk-lead.
- docs/ops/funnel-tracker.csv is header only. Two intro calls, no NDA, no data.
- gtm/personas.md and outreach-sequence.md describe the June ICP and carry
  expired seasonal hooks; objection-inventory says $15-60M ARR.
- docs/legal NDA and data addendum marked not signable; legal.ts still defaults
  to a bracketed entity name.
- No 2GP Salesforce package; a prospect cannot install the app in their org.
- SOM (100-250 customers, $5-15M ARR) was never re-derived after the SAM was
  cut to $11-29M Tier A; it implies 24-60% share of 350-480 accounts.
- Deck arithmetic: funnel collapse stated as 4-6x, table shows about 8x;
  expansion bridge multiplies to 12-36x, not 15-40x; Adyen/Orb and
  Salesforce/m3ter closed 1 July and copy still says "agreed to acquire".
- Pricing page has no price, gives the diagnostic away, and the ROI thresholds
  are asserted; one does not compute.
- PR #62 carrying the whole agent org has been open 28 days; main has no
  docs/agents/. Six PRs (#36 through #61) are untriaged; #36 and #37 hold
  ingest silent-corruption fixes.
- PK-6, PK-12, PK-14 are READY, not done: /trust names OpenAI as the only LLM
  subprocessor, GuidanceClient.tsx:295 says "more in expected value" even when
  uplift is negative, FounderCta.tsx is dead code with a retracted claim.
- No ADR for the monotone constraint despite the PK-15 review requiring one.

## Per-agent verdicts

| Agent | Verdict in one line |
|---|---|
| cto | Conditional yes; ship a pilot-admissibility branch (identity, durable writes, evidence_version) before real data |
| cfo | Engineering more honest than the commercial model; readout must tie out, SOM never re-derived |
| pricing-strategist | Disclosure layer strong, core reference number breaks on sparse books and band floors |
| market-sizing-analyst | Top-decile sizing structure, arithmetic inside it does not reproduce |
| code-reviewer | Reject: digest miscount, shared tenant bucket, uncaveated /recommend |
| mle-reviewer | Two blockers: random split on time data, calibration gate that cannot fail |
| silent-failure-hunter | Deterministic layers honest; copilot/rag/matching/mapping go quiet without logging |
| qa-engineer | PASS, 279/0, CI green; no tests for rag, mapping, docs; no down migrations |
| backend-engineer | Disciplined core; PK-16 confirmed and worse than described; UBP fields dead |
| ai-engineer | Design sound; branch stale; competitor price extraction unverified; injection untested |
| data-engineer | Schema and ingest strong; no down migration, tenant key not opaque, no currency |
| web-engineer | Structurally good and honest; PK-6/12/14 defects still live |
| customer-success | Conditional, not yet: no package, no signable paper, no pipeline |
| sales-outreach | Sellable in principle; validation program near zero, collateral stale |
| pk-lead | Gates were real; org unmerged; checkout stale; critical path is not engineering |

## What every lens agreed is genuinely good

- pricing/_safe_fetch.py: resolve-then-pin SSRF defense with per-hop
  revalidation. Called staff-level by three separate agents.
- LoadReport in pricing/ingest.py: every drop, coercion, and ambiguity is a
  visible line before any number reaches a dashboard.
- Honesty enforced in code: method labels (modeled_ev_curve vs band_guardrail),
  persisted flag, actor_assertion, _guard_degenerate_list refusing a confident
  zero, _RECOVERABLE_CAVEAT on every copilot dollar.
- The 2026-09-11 decision that cut the SAM by 6x and recorded that the old
  number had been said to an investor.
- The org gates were not theater: PK-5 rejected twice, PK-11 rejected on a
  reproduced numeric blocker.

## Recommended next two weeks

Order matters. Items 1 to 3 unblock everything else.

1. Rebase this branch on origin/main, split PR #62 (org plus agentctl in one
   PR, deck and GTM in another), merge the org PR. Owner: pk-lead plans, founder
   merges.
2. Merge PR #61 (opaque tenant key), then the pilot-admissibility set: per-user
   actor identity with approver allowlist, fail-closed CRM workflow writes,
   evidence_version. Owner: backend-engineer. Acceptance: two visitors cannot
   read each other's exception rows; a failed audit write returns 503.
3. Fix the digest miscount with a known-answer test. Owner: backend-engineer.
4. Make the readout tie out: gate the global reference, move the threshold off
   the band floor, one per-deal reference in defended_vs_investigate and
   trend_by_quarter, BU and product-line reference tables (PK-16), re-point the
   sample and upload pages at the segment-aware figure, non-additive line on
   policy simulations. Owner: backend-engineer, then web-engineer.
5. Give the orphan time-split branch a PK id and PR; add Brier-skill and
   per-segment calibration gates; clip the recommendation grid to cohort
   support; explain the recommended row. Owner: ai-engineer, mle-reviewer
   reviews.
6. PK-6, PK-12, PK-14 as one web sequence after item 4. Owner: web-engineer.
7. Logging plus missing-vs-zero in copilot, rag, mapping, matching; strip
   deal-level arrays from the /ask prompt; write test_rag.py and test_mapping.py.
   Owner: ai-engineer.
8. Down migration for 2026-08-01-salesforce-crm-workflow.sql; currency column.
   Owner: data-engineer.
9. In parallel and founder-owned: five real problem interviews logged to the
   funnel tracker, rewrite personas and outreach to the Aug 1 ICP, close entity
   and counsel status, re-derive SOM against the Tier A pool, fix the deck
   arithmetic and the July M&A closes, put a price on the pricing page.
10. Build and test the 2GP Salesforce package in a fresh scratch org. This is
    the single bounded engineering item between "works in the founder's org"
    and "a design partner can connect".

Triage PRs #36, #37, #38, #59, #60 with a stated reason each (PK-4).

## Closure status, end of 2026-09-26

Branch fix/agent-eval-findings, two fix rounds, reviewed by the code, ML and
silent-failure lenses between rounds (round-1 reports are in the agent-reports
folder). Python suite 386 passed; web typecheck, lint, tests and build green.

Closed on the branch:
- Finding 1: global reference gated on sufficiency with an explicit
  insufficient-data state that propagates to every consumer (deal list,
  hierarchy slices, policy union, CRM guidance, web); one per-deal reference
  across the readout; BU and product-line reference tables (PK-16);
  non-additive union figure; public pages headline the segment-aware figure.
- Finding 2: time-ordered holdout and forward-fold tuning; Brier-skill gate a
  constant predictor fails; per-band and per-segment calibration; cohort
  clipping with support_floor labeling; uplift scored at the deal's own
  discount; NaN safety; leakage_vs_model on the same cohort grid; exceptions
  and recommend agree; reproducibility stamp.
- Finding 3, partial: per-visitor demo tenant, tenant-scoped doc store, tenant
  header on every proxy, length caps, fail-closed CRM audit writes,
  evidence_version with a records hash.
- Finding 4: digest counts request events only; known-answer test.
- Finding 5: logging and missing-vs-zero in copilot; tri-state web status;
  per-URL match status and price-in-page verification; deal-level arrays
  stripped from the RAG prompt; test_rag.py and test_mapping.py added.
- Finding 7: down migration, tenant-scoped indexes, currency column with
  blocking on mixed currencies surfaced as 422.
- Finding 8: CRM body cap, /recommend rate limit, customer-keyed limiter,
  one reference computation per run.
- Finding 9, partial: PK-6, PK-12, PK-14; M&A tense on the site; GTM
  collateral aligned to the current ICP; SOM re-derivation drafted in the
  vault; sizing arithmetic corrected in the vault notes.

Still open, and why:
- Per-user authenticated actor identity and PR #61 merge (finding 3): a
  build with a design doc, and a merge decision.
- Reference threshold at the band floor (finding 1): changes every published
  number; reference_band_median_discount is disclosed so the alternative can
  be compared. Founder decision.
- Usage-based pricing positioning (finding 6): copy or build decision.
- Price on the pricing page and the ROI table (finding 9): founder decision.
- Deck and pitch-base arithmetic (finding 9): those files live only on PR #62;
  the corrected numbers are in the vault notes and a paste-ready insert in
  gtm/llama-ventures.
- PR #62 split and merge, PR triage (#36 to #61), ADR-006 for the monotone
  constraint, OWNERSHIP.md refresh: docs/agents exists only on PR #62.
- Interviews, legal entity and counsel, the 2GP Salesforce package: founder
  work, not code.
