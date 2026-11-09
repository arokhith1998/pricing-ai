---
title: Proposed tasks, native connectors (HubSpot, Stripe, Chargebee) and two Phase B follow-ups
created: 2026-11-09
updated: 2026-11-09
tags: [tasks, proposal, connectors, hubspot, stripe, chargebee]
status: approved
source: docs/design/2026-11-09-native-connectors-hubspot-stripe-chargebee.md
---

# Proposed tasks: native connectors

**Status 2026-11-09: approved.** The founder approved this list on 2026-11-09 with pk-lead's seven
recommendations: F1 restricted Stripe key; F2 Phase C lens PK-31 to PK-33 in the second slot during
HubSpot; F3 no HubSpot writeback, read-only scopes; F4 no billing-to-CRM join in v1, side-by-side
readouts; F5 billing-only tenant allowed, with the no-win-rate first line; F6 tenant-declared list price
deferred to interview data; F7 no billing aggregates in the per-tenant snapshot for v1. PK-39 to PK-70,
plus PK-31, PK-32 and PK-33 from `TASKS-proposed.md`, are on the board in BACKLOG
(`docs/agents/PROJECT_STATE.md`); none is assigned. PK-71 is not approved (F4). PK-72 and PK-73 are not
entered (see Optional). Changes made on entry are listed under "Changes on entry" at the end.

Original note: nothing here entered `project_state.json` until the founder approved the list. Ids PK-39 to PK-73;
PK-30 to PK-38 stay reserved for Phases C and D. Format follows `TASKS-proposed.md`. "Gate" names a
founder decision from the design doc section 9 (F1 to F7) or an external prerequisite.

**Founder-only setup**, marked per task:
- **[HS]** HubSpot developer account, an unlisted public app (client id, secret, redirect URI) and a
  test portal seeded per PK-50's spec.
- **[ST]** Stripe test-mode account and a restricted key, seeded per PK-60's spec.
- **[CB]** Chargebee test site (Product Catalog 2.0) and a read-only key, seeded per PK-67's spec.

Agents never read `.env` or hold live keys. Test-mode credentials reach a task only through the
founder's environment.

**Global gates.** PK-25 merged gates every task below except the doc-only ones and PK-39, PK-40. No
task that stores a non-Salesforce credential starts before PK-21 (which waits on PK-6) and PK-44 have
merged.

## Phase B follow-ups (from PK-27, PR 74)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-39 | Route cpq_line exports through the quote-line roll-up and surface ask_user deals | backend-engineer | PK-27 | `pricing/ingest.py#profiles`, `api/routers/diagnostic.py#load_report`, `api/routers/diagnostic.py#map_columns`, `tests/test_ingest_profiles.py` | 2.5 | none |
| PK-40 | Annualise multi-year quote roll-ups from term_months | backend-engineer | PK-39 | `pricing/ingest.py#profiles`, `tests/test_ingest_annualise.py` | 1 | none |

Acceptance:
- **PK-39:**
  - A file detected as the `cpq_line` profile reaches `pricing.mapping.rollup_quote_lines` before
    `_exclude_open` runs; a known-answer fixture of 3 quotes and 7 lines loads as 3 deals with the
    summed `list_acv` and `booked_acv`.
  - Deals with outcome `ask_user` are not counted in `report.excluded_open` and are not dropped
    silently: `LoadReport` carries an `ask_user` section with each raw stage value, its deal count and
    its quote ids, and the diagnostic response includes it.
  - No `ask_user` deal is ever counted as `closed_lost` or enters win rate; a test asserts win rate is
    the same with and without the `ask_user` rows present.
  - A file whose deals are all `ask_user` raises `SchemaError` naming the unresolved stage values, not
    the generic "no closed deals" message.
  - `crm_opportunity` and plain CSV files load exactly as before; existing ingest and mapping suites
    pass unchanged and the pinned dataset is byte-identical.
  - Added 2026-11-09 from the PR 74 review: one stage table, with ingest's `OUTCOME_ALIASES` replaced by
    `mapping.normalize_stage` so "Accepted" and "Declined" are not reported as open; quarantined lines
    (blank or missing quote id) surface in `LoadReport` with their count, never dropped silently; several
    quotes for one opportunity are resolved to one deal by a stated rule (primary or latest, disclosed),
    never double-counted; the `/map-columns` route either goes through layer 0 or is documented as
    header-suggestion only, and bounds the header count.
- **PK-40:**
  - Annualisation runs only when the caller states the amount basis: `total_contract` divides
    `list_acv` and `booked_acv` by `term_months / 12`; `annual` leaves them unchanged.
  - Basis unknown: no transform, plus a multi-year disclosure in `LoadReport` when 10 percent or more
    of deals have `term_months` of 24 or more (the Salesforce adapter's threshold).
  - Missing or non-positive `term_months` is never filled in or assumed to be 12; those deals are
    listed and left unannualised.
  - Ramp fields are not touched, and the steady-state convention in `pricing/schema.py` (year 3 is
    `booked_acv`) is unchanged; a test asserts it.
  - Known-answer test: a 36-month quote with total booked 360,000 and basis `total_contract` loads with
    `booked_acv` 120,000.

## Shared framework and credential custody

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-41 | Add a source-keyed connections table, backfill Salesforce, and an opaque tenant ref | data-engineer | PK-24, PK-25 | `neon/schema.sql`, `neon/migrations/2026-11-source-connections.sql`, `neon/migrations/2026-11-source-connections.down.sql`, `neon/test_migrations.py` | 1.5 | plan approval |
| PK-42 | Move connection storage and token crypto onto source_connections, with key ids | web-engineer | PK-41 | `web/src/lib/connector-store.ts`, `web/src/lib/connector-crypto.ts`, `web/src/lib/salesforce-store.ts`, `web/src/lib/salesforce-crypto.ts`, `web/test/connector-store.test.ts`, `web/test/connector-crypto.test.ts` | 2.5 | none |
| PK-43 | Key tenants by opaque ref and revoke every credential for a tenant on request | web-engineer | PK-42 | `web/src/lib/gate.ts#customerRef`, `web/src/lib/store.ts#access_codes`, `web/scripts/revoke-tenant-connections.ts`, `web/test/tenant-key.test.ts`, `web/test/revoke-tenant.test.ts` | 2 | none |
| PK-44 | Register the connector credential classes and their revoke paths in incident response | customer-success | PK-21 | `docs/ops/data-register.md`, `docs/ops/incident-response.md`, `docs/ops/salesforce-integration-runbook.md` | 0.5 | founder approves |
| PK-45 | Draft the per-customer credentials amendment and update the readiness access-method lines | customer-success | PK-22, PK-19 | `docs/legal/one-page-mutual-nda-data-addendum.md`, `gtm/data-readiness-checklists.md` | 0.5 plus counsel | counsel |
| PK-70 | Drop the legacy salesforce_connections and salesforce_mappings tables | data-engineer | PK-42, PK-41 | `neon/schema.sql`, `neon/migrations/2027-01-drop-legacy-salesforce-tables.sql`, `neon/migrations/2027-01-drop-legacy-salesforce-tables.down.sql` | 0.5 | founder confirms 7 days on prod with no legacy reads |

Acceptance:
- **PK-41:**
  - `source_connections` has primary key `(customer_ref, source_system)`, a check on `salesforce |
    hubspot | stripe | chargebee`, the columns in design section 2.1, and no column that can hold a
    plaintext credential or a deal value.
  - `source_connection_config` cascades on delete from `source_connections`.
  - The up migration copies every `salesforce_connections` and `salesforce_mappings` row idempotently
    (run twice, same counts) and leaves the legacy tables untouched.
  - `access_codes.tenant_ref` is added; existing rows backfill to their current code so no
    `decision_log` or connection row is rewritten; new codes get an opaque random value.
  - The down file refuses and aborts if any `source_connections` row has a `source_system` other than
    `salesforce`. QA pastes scratch up, down, up output.
  - `neon/schema.sql` matches the migrated state; `neon/test_migrations.py` passes.
- **PK-42:**
  - Salesforce connect, refresh, disconnect and mapping read and write `source_connections` and
    `source_connection_config` only; every existing `web/test/salesforce-*.test.ts` passes unchanged.
  - New ciphertexts use a `v2` format carrying a key id and AES-GCM additional data
    `customer_ref|source_system|field`; a ciphertext moved to another row or tenant fails to decrypt.
  - `v1` ciphertexts still decrypt and are rewritten as `v2` on the next token refresh.
  - A decrypt-only previous key decrypts old ciphertexts after rotation; a test rotates the key with a
    live connection and the connection survives.
  - Production still fails closed when the encryption key is missing; no token appears in any response,
    log line or error message (test scans them).
- **PK-43:**
  - `customerRef()` returns `access_codes.tenant_ref`, not the access code; legacy codes resolve to the
    same value as before (no tenant changes identity).
  - The operator script, given a tenant ref and no session, revokes Salesforce and HubSpot tokens by
    API, deletes every `source_connections` row for the tenant, and prints which Stripe and Chargebee
    keys the customer must roll.
  - The script is not reachable over HTTP and refuses to run without an explicit tenant ref; it never
    prints a credential.
  - Revoking an access code before disconnect no longer leaves a connection row orphaned under
    `default` (test).
  - eslint, tsc, `npm test` and build pass.
- **PK-44:**
  - Part A gains rows for HubSpot refresh tokens, Stripe restricted keys, Chargebee API keys and site
    names, the connector encryption key and its previous key, and the HubSpot app client secret, each
    with location, retention, and deletion or rotation owner.
  - A row states billing rows and invoice lines are processed in memory only, with nothing retained.
  - Incident containment lists: rotate the connector key, delete stored credentials, revoke HubSpot and
    Salesforce tokens by API, and notify each Stripe and Chargebee tenant to roll their key, stating
    Pricekeel cannot revoke those.
  - The Salesforce runbook's offboarding order is corrected to: run the operator revoke, then revoke
    the access code.
  - No secret values appear in any of the three files.
- **PK-45:**
  - A one-page amendment template names each credential (vendor, key type, permissions), the 24-hour
    revoke-on-request duty, and the customer's own duty to roll Stripe and Chargebee keys.
  - The readiness checklists keep "export only" as the default and add the connector path as an
    option that requires the signed amendment.
  - Billing sections still say billing gives no win rate; marked for counsel, not executed.
- **PK-70:**
  - The drop runs only if every legacy row exists in `source_connections`; otherwise it aborts.
  - The down file recreates both legacy tables and copies Salesforce rows back from
    `source_connections`; QA pastes scratch up, down, up output.
  - No application code references the legacy table names (grep in the PR).

## HubSpot

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-46 | Map HubSpot deals, confirmed stage maps and properties to canonical deals | backend-engineer | PK-25 | `pricing/adapters/__init__.py`, `pricing/adapters/hubspot.py`, `api/routers/crm.py#adapters`, `tests/test_adapter_hubspot.py`, `tests/fixtures/hubspot/**` | 3 | none |
| PK-47 | Connect, refresh and disconnect a HubSpot portal by OAuth | web-engineer | PK-43, PK-44 | `web/src/lib/hubspot-oauth.ts`, `web/src/lib/hubspot-client.ts`, `web/src/app/api/hubspot/oauth/**`, `web/src/app/api/hubspot/connection/**`, `web/test/hubspot-oauth.test.ts`, `web/test/hubspot-client.test.ts` | 2.5 | F3 [HS] |
| PK-48 | Discover pipelines and properties and sync a bounded HubSpot book | web-engineer | PK-47, PK-46, PK-26 | `web/src/lib/hubspot-sync.ts`, `web/src/lib/connector-workspace.ts`, `web/src/lib/salesforce-workspace.ts`, `web/src/app/api/hubspot/metadata/**`, `web/src/app/api/hubspot/mapping/**`, `web/src/app/api/hubspot/workspace/**`, `web/src/app/api/hubspot/workflow/**`, `web/test/hubspot-sync.test.ts` | 4 | [HS] |
| PK-49 | Give /crm a source switcher and a HubSpot stage-map confirmation screen | web-engineer | PK-48 | `web/src/app/crm/page.tsx`, `web/src/components/SalesforceWorkspace.tsx`, `web/src/components/ConnectorWorkspace.tsx`, `web/src/components/HubspotSetup.tsx`, `web/test/hubspot-workspace.test.ts` | 3 | none |
| PK-50 | Verify HubSpot end to end against a planted test portal | qa-engineer | PK-49 | `tests/connectors/test_hubspot_known_answer.py`, `tests/fixtures/connectors/hubspot_portal_seed.json` | 1.5 | [HS] |
| PK-51 | Write the HubSpot runbook and customer guide | customer-success | PK-48, PK-44 | `docs/ops/hubspot-integration-runbook.md`, `docs/guides/customer-hubspot-workspace.md` | 0.5 | none |
| PK-52 | Name HubSpot on the privacy, trust and pricing pages | web-engineer | PK-50, PK-6 | `web/src/app/privacy`, `web/src/app/trust`, `web/src/app/pricing/page.tsx`, `web/test/claims-connectors.test.ts` | 0.5 | none |

Acceptance:
- **PK-46:**
  - `to_canonical` is pure (no network, no input mutation) and sets `source_system=hubspot`,
    `source_record_id`, `source_account_id` and an absolute `source_url` on every deal.
  - Outcome comes only from the confirmed stage map: a stage absent from it, or present but unconfirmed,
    yields `ask_user`; no input produces `closed_lost` without a confirmed lost stage (property test).
  - An open-stage deal with a past close date stays `open`.
  - Known-answer fixtures (2 pipelines, custom stage labels, one pipeline without line items) return the
    planted list, booked, outcome and currency per deal; the no-line-item pipeline yields `list_source:
    none` and the existing missing-list blocker.
  - `POST /crm/analyze` with `source_system=hubspot` uses the HubSpot adapter; Salesforce requests and
    `tests/test_crm.py` are unchanged.
  - No string "Salesforce" appears in `pricing/adapters/hubspot.py`; no field is labelled margin.
  - Note: if PK-25 places adapter resolution outside `api/routers/crm.py`, the lead re-scopes the
    `#adapters` claim before assign.
- **PK-47:**
  - Before code depends on them, the PR records the verified scope names (including what pipelines
    need), token lifetimes and rate limits from HubSpot's current docs, with links.
  - Requested scopes are read-only and include no contact scope and no write scope (F3 answered 2026-11-09: no
    writeback in v1).
  - Signed state plus a tenant-bound signed httpOnly cookie; mismatch, expiry or a replayed state fail
    closed and clear the cookie.
  - Tokens are stored only through PK-42's store; refresh runs ahead of expiry; a failed refresh sets
    `reauth_required`.
  - Disconnect deletes the refresh token at HubSpot (best effort, result reported) and deletes the row.
  - The client accepts only `https://api.hubapi.com` with an allowlisted path prefix and refuses
    redirects (test). Connect returns 403 in production while `HUBSPOT_CONNECT_ENABLED` is unset.
- **PK-48:**
  - Closed deals are fetched for 730 days plus all open deals, capped at 10,000, with the fetched count
    and any truncation disclosed in readiness.
  - The field whitelist drops everything not mapped before data leaves `hubspot-sync.ts`; a test
    asserts no contact, email or phone field reaches the API payload or a log.
  - Pipelines and stages are returned for confirmation with the proposed outcome per stage; the
    confirmed map is saved to `source_connection_config` and invalidated per pipeline when a stage is
    added.
  - Analysis does not run while any pipeline in scope is unconfirmed.
  - Workflow events log with `source.system = hubspot`; outcome reconciliation is idempotent (running
    sync twice records one `outcome_recorded` per deal).
  - The Salesforce workspace still passes its suites after `salesforce-workspace.ts` is generalised.
- **PK-49:**
  - `/crm` shows each connected source and switches between them; the Salesforce view is unchanged
    (existing tests pass).
  - The stage-map screen lists every stage with its proposed outcome and deal count; `ask_user` stages
    show their deals as excluded with the reason.
  - The decision loop (flag, accept or override, approve or reject) works on a HubSpot deal through the
    shared `ConnectorWorkspace`; the deal link opens the HubSpot record.
  - No writeback control appears for HubSpot (F3 answered 2026-11-09: no writeback in v1).
  - Brand rules: status colours carry a text label; no em dashes; eslint, tsc, build pass.
- **PK-50:**
  - The seed spec plants at least 40 closed and 10 open deals across 2 pipelines with known list,
    booked, outcome and band win rates; the run reproduces the planted band win rates.
  - An added unconfirmed stage blocks analysis and shows the affected deals.
  - After disconnect, the connection row is gone and the HubSpot token no longer works.
  - Neon holds no deal values after a full sync (query output pasted).
  - Server logs for the run contain no deal value, account name or token (grep output pasted).
  - Green CI run id recorded.
- **PK-51:**
  - Covers app setup, scopes, install link, stage-map confirmation, disconnect, operator revoke and
    rotation; matches PK-44's register rows.
  - States that HubSpot without line items gives no list price and therefore no leakage figure.
- **PK-52:**
  - Privacy names HubSpot as a data source with what is read, what is kept (connection metadata,
    encrypted token, config) and what is not (deal rows).
  - Pricing and trust say "Salesforce and HubSpot live", read-only, and no other connector is implied.
  - If PK-35 has merged, the status comes from `PLATFORM_STATUS` and this task claims
    `web/src/data/platform-status.ts` instead of editing page text.
  - A claims test fails if any page names a connector that is not shipped. No em dashes.

## Stripe, including shared billing work

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-53 | Add the contract_period_actuals grain and stripe and chargebee source values | data-engineer | PK-25 | `pricing/schema.py`, `pricing/generate_billing.py`, `tests/test_schema_billing.py` | 2.5 | F2 |
| PK-54 | Compute realization, contracted versus billed and usage actuals from billing | backend-engineer | PK-53 | `pricing/billing.py`, `tests/test_billing.py` | 3 | F2 |
| PK-55 | Map Stripe subscriptions and invoices to canonical deals and period actuals | backend-engineer | PK-53, PK-46 | `pricing/adapters/stripe.py`, `pricing/adapters/billing_common.py`, `tests/test_adapter_stripe.py`, `tests/fixtures/stripe/**` | 3 | none |
| PK-56 | Serve the billing readout from POST /billing/analyze | backend-engineer | PK-54, PK-55 | `api/routers/billing.py`, `api/main.py#routers`, `tests/test_billing_api.py` | 1.5 | none |
| PK-57 | Connect Stripe with a customer-created restricted key | web-engineer | PK-43, PK-44 | `web/src/lib/stripe-client.ts`, `web/src/lib/stripe-credentials.ts`, `web/src/app/api/stripe/connection/**`, `web/test/stripe-connection.test.ts` | 2 | F1 [ST] |
| PK-58 | Sync a bounded Stripe book and confirm which prices are list | web-engineer | PK-57, PK-55, PK-56 | `web/src/lib/stripe-sync.ts`, `web/src/app/api/stripe/metadata/**`, `web/src/app/api/stripe/mapping/**`, `web/src/app/api/stripe/workspace/**`, `web/test/stripe-sync.test.ts` | 3.5 | [ST] |
| PK-59 | Show the billing readout and the no-win-rate line in the workspace | web-engineer | PK-58, PK-49 | `web/src/components/BillingReadout.tsx`, `web/src/components/StripeSetup.tsx`, `web/src/components/ConnectorWorkspace.tsx`, `web/test/billing-readout.test.ts` | 2.5 | F5 |
| PK-60 | Verify Stripe end to end against a planted test-mode account | qa-engineer | PK-59 | `tests/connectors/test_stripe_known_answer.py`, `tests/fixtures/connectors/stripe_test_seed.json` | 1.5 | [ST] |
| PK-61 | Write the Stripe runbook and key-creation guide | customer-success | PK-57, PK-44 | `docs/ops/stripe-integration-runbook.md`, `docs/guides/customer-stripe-key.md` | 0.5 | none |
| PK-62 | Name Stripe on the privacy, trust and pricing pages | web-engineer | PK-60, PK-52 | `web/src/app/privacy`, `web/src/app/trust`, `web/src/app/pricing/page.tsx`, `web/test/claims-connectors.test.ts` | 0.5 | none |

Acceptance:
- **PK-53:**
  - `SourceSystem` gains `stripe` and `chargebee`; `billing` stays; existing files load unchanged and the
    pinned dataset is byte-identical.
  - A `CONTRACT_PERIOD_FIELDS` list defines the grain in design section 4, all money in one currency per
    row, tax excluded, with no field for contact data or end-customer identifiers.
  - `pricing/generate_billing.py` uses its own RNG stream and plants a known answer key: list versus
    contracted gaps, a 100-percent-off coupon, a ramp schedule, 6 and 5 billed-period accounts, and a
    tiered price.
  - Nothing in the grain is called margin, and `cost_basis` is not on it.
  - Treated as a schema decision: the PR links this design doc.
- **PK-54:**
  - Each output carries a method name (`billing_realization`, `contracted_vs_billed`,
    `usage_actuals`) and per-lever status `scored | insufficient_data | not_provided`.
  - Win rate is always `not_provided` with the reason text from the design doc; the guardrail refuses
    rows whose `source_system` is `stripe`, `chargebee` or `billing` (test).
  - Accounts with fewer than 6 billed periods return `insufficient_data` for usage, never zero.
  - The planted answers from PK-53 are recovered exactly (Decimal or rounded to the cent, stated).
  - The word "margin" never appears in any output (test scans payloads).
- **PK-55:**
  - `to_canonical` is pure and sets `source_system=stripe`, subscription id, customer id and an
    absolute dashboard `source_url` (test-mode path in test mode).
  - Each derivation in design section 4 is implemented with its stated fallback; tiered prices give
    `not_provided` for `overage_rate` and `list_unit_rate`; unconfirmed list gives `insufficient_data`.
  - `committed_acv` is filled only from the user-marked source, never guessed.
  - Invoice lines become `contract_period_actuals`; void invoices are excluded and counted; credit
    notes reduce `invoiced_amount`.
  - Known-answer fixtures reproduce PK-53's planted answers; `cost_basis` and `cogs_acv` are never set.
- **PK-56:**
  - `POST /billing/analyze` takes canonical billing deals plus period actuals, enforces the 10,000
    cap, and returns PK-54's readout with method and status per lever.
  - The rate limiting and `X-Pricekeel-Customer` tenant scoping match `/crm/*`.
  - No request rows are retained; errors carry codes and counts, never values (test).
  - Sequenced against PK-34 on `api/main.py#routers`.
- **PK-57:**
  - The PR records the restricted-key permission list and rate limits from Stripe's current docs.
  - Keys starting `sk_` are refused with a message telling the user to create a restricted key; only
    `rk_` keys are accepted; one read call validates the key.
  - The key is stored only through PK-42's store and is never returned to the browser after save.
  - Disconnect deletes our copy and tells the user to roll the key in Stripe.
  - The client accepts only `https://api.stripe.com` with an allowlisted path prefix, refuses
    redirects, and connect returns 403 in production while `STRIPE_CONNECT_ENABLED` is unset.
- **PK-58:**
  - Fetches subscriptions active in or canceled within 730 days, their invoices, credit notes,
    discounts, schedules and prices, capped at 10,000 subscriptions with the count disclosed.
  - The whitelist keeps customer id, name and metadata keys the user mapped; a test asserts no email,
    phone, address, payment method or tax id reaches the API payload or a log.
  - The user confirms which prices are list; the set saves to `source_connection_config`; analysis does
    not run before confirmation.
  - Meter event and usage-record endpoints are never called (test on the path allowlist).
- **PK-59:**
  - The billing readout's first line states that billing gives no win rate and why.
  - Contracted versus billed, realization, concessions and usage actuals each show method, status and
    n; `insufficient_data` and `not_provided` render as labelled states, never blanks or zeros.
  - With a CRM source connected, both readouts appear side by side; no figure is joined across them
    (F4 answered 2026-11-09: no join in v1).
  - A billing-only tenant, with no CRM source connected, sees the full billing readout with the
    no-win-rate first line (F5 answered 2026-11-09: allowed). Added on entry.
  - No "margin" wording anywhere; no em dashes; eslint, tsc, build pass.
- **PK-60:**
  - The seed spec reproduces PK-53's planted cases in test mode; the run recovers each planted figure.
  - An `sk_` key is refused in the live UI.
  - Neon holds no invoice or subscription values after sync; logs hold no values or keys (output
    pasted). Green CI run id recorded.
- **PK-61:**
  - Gives the exact permission list for the restricted key, how to roll it, and that Pricekeel cannot
    revoke it; matches PK-44.
- **PK-62:**
  - Same rules as PK-52; the pricing page line saying billing connectors are not in V1 is updated to
    name Stripe as read-only, with "no win rate from billing alone".

## Chargebee

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-63 | Map Chargebee subscriptions and invoices to canonical deals and period actuals | backend-engineer | PK-55, PK-56 | `pricing/adapters/chargebee.py`, `api/routers/billing.py#adapters`, `tests/test_adapter_chargebee.py`, `tests/fixtures/chargebee/**` | 2.5 | none |
| PK-64 | Connect Chargebee with a site name and read-only key | web-engineer | PK-57 | `web/src/lib/chargebee-client.ts`, `web/src/app/api/chargebee/connection/**`, `web/test/chargebee-connection.test.ts` | 1.5 | [CB] |
| PK-65 | Sync a bounded Chargebee book | web-engineer | PK-64, PK-63 | `web/src/lib/chargebee-sync.ts`, `web/src/app/api/chargebee/metadata/**`, `web/src/app/api/chargebee/mapping/**`, `web/src/app/api/chargebee/workspace/**`, `web/test/chargebee-sync.test.ts` | 3 | [CB] |
| PK-66 | Add the Chargebee setup panel to the workspace | web-engineer | PK-65, PK-59 | `web/src/components/ChargebeeSetup.tsx`, `web/src/components/ConnectorWorkspace.tsx`, `web/test/chargebee-setup.test.ts` | 1 | none |
| PK-67 | Verify Chargebee end to end against a planted test site | qa-engineer | PK-66 | `tests/connectors/test_chargebee_known_answer.py`, `tests/fixtures/connectors/chargebee_test_seed.json` | 1.5 | [CB] |
| PK-68 | Write the Chargebee runbook and key-creation guide | customer-success | PK-64, PK-44 | `docs/ops/chargebee-integration-runbook.md`, `docs/guides/customer-chargebee-key.md` | 0.5 | none |
| PK-69 | Name Chargebee on the privacy, trust and pricing pages | web-engineer | PK-67, PK-62 | `web/src/app/privacy`, `web/src/app/trust`, `web/src/app/pricing/page.tsx`, `web/test/claims-connectors.test.ts` | 0.5 | none |

Acceptance:
- **PK-63:**
  - Same purity, provenance and no-cost rules as PK-55, with `source_system=chargebee`.
  - `unit_price` overrides against the item price give list versus contracted; contract terms set
    `term_months`; ramps fill ramp fields; promotional credits fill `credits_tcv`.
  - Shared logic lives in `billing_common.py`; no Stripe-specific code is copied (reviewer checks).
  - Known-answer fixtures recover PK-53's planted cases; `POST /billing/analyze` dispatches
    `chargebee` rows to this adapter.
- **PK-64:**
  - The site name must match `^[a-z0-9-]{1,63}$`; the host is built only as `<site>.chargebee.com`;
    any other input is refused (tests include `evil.com#`, `a.b`, and an IP literal).
  - The PR records rate limits and the Product Catalog 2.0 detection from Chargebee's current docs; a
    1.0 site is refused with a clear message.
  - The setup screen states that Pricekeel cannot verify the key is read-only.
  - Storage, disconnect and the production connect flag follow PK-57.
- **PK-65:**
  - Same window, cap, whitelist and no-usage-events rules as PK-58; the usages API is never called.
  - List confirmation is not needed where item prices exist; overrides are shown for review.
- **PK-66:**
  - The Chargebee panel reuses `BillingReadout` unchanged; Stripe and Salesforce views unchanged.
  - eslint, tsc, build pass; no em dashes.
- **PK-67:**
  - As PK-60, for a Chargebee test site, plus a refused malformed site name in the live UI.
- **PK-68:**
  - As PK-61, for Chargebee, including site name handling.
- **PK-69:**
  - Same rules as PK-62.

## Optional, gated

Status 2026-11-09: none of these is on the board. PK-71 is **not approved** (F4: no billing-to-CRM join in
v1). PK-72 is not entered: its gate (a credential-free billing path) was not part of the F answers and
stays open. PK-73 is not entered: it depends on PK-38, which is Phase D and not on the board; it is
consistent with F7, since billing rows never enter the snapshot.

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-71 | **Not approved (F4).** Link billing accounts to CRM deals with a disclosed link method | backend-engineer | PK-56, PK-46 | `pricing/billing_join.py`, `api/routers/billing.py#join`, `tests/test_billing_join.py` | 2.5 | F4 |
| PK-72 | Add Stripe and Chargebee export profiles to the mapper | ai-engineer | PK-27, PK-53 | `pricing/mapping.py`, `tests/test_mapping_billing_profile.py`, `tests/fixtures/mapping_profiles/billing/**` | 1.5 | founder wants a credential-free billing path |
| PK-73 | Refresh the per-tenant snapshot after each CRM connector sync | backend-engineer | PK-38, PK-48 | `pricing/snapshot.py#refresh`, `api/routers/crm.py#snapshot_refresh`, `tests/test_snapshot_refresh.py` | 1 | D1(a), PK-38 |

Acceptance:
- **PK-71 (not approved, F4):** link order is user-mapped metadata key, then exact `source_account_id` crosswalk, then
  normalised name; every link carries `link_method` and confidence; no silent merge; coverage below the
  stated floor returns `insufficient_data`.
- **PK-72:** billing exports detect as a `billing` profile; subscription status never maps to
  `outcome`; the LLM payload holds headers only.
- **PK-73:** the snapshot holds only D1 aggregates; the PK-38 no-rows test passes on a HubSpot-sourced
  book; billing rows never enter it.

## Totals

| Group | Tasks | Days |
|---|---|---|
| Phase B follow-ups | 2 | 2.5 |
| Shared framework and custody (PK-41 to PK-45, PK-70) | 6 | 7.5 (1 doc-only) |
| HubSpot (PK-46 to PK-52) | 7 | 15 (0.5 doc-only) |
| Stripe and shared billing (PK-53 to PK-62) | 10 | 20.5 (0.5 doc-only; shared billing PK-53, PK-54, PK-56, PK-59 is 9.5) |
| Chargebee (PK-63 to PK-69) | 7 | 10.5 (0.5 doc-only) |
| **Connectors core** | **30** | **53.5** |
| Optional (PK-71 to PK-73) | 3 | 5 |

## What can run in parallel, and what cannot

- **Doc-only tasks** (PK-44, PK-45, PK-51, PK-61, PK-68) take no slot under the ADR-003 amendment.
- **Now, before PK-25 merges:** nothing here except dispatching **PK-6**, which is READY and sits on the
  HubSpot critical path (PK-6, then PK-21, then PK-44, then PK-47). PR #62 (PK-19, PK-20, PK-22) must
  merge for PK-45.
- **After PK-25:** PK-46 (HubSpot adapter) can run beside the framework chain PK-24, PK-41, PK-42,
  PK-43. PK-53 can run beside the HubSpot web chain once a slot is free (F2 decides whether Phase C
  takes that slot first).
- **Must sequence, by claim:**
  - PK-24, then PK-41, then PK-70 on `neon/schema.sql`; PK-37 must not overlap any of them.
  - PK-39, then PK-40 on `pricing/ingest.py#profiles`.
  - PK-46 against PK-34 on `api/routers/crm.py` (PK-34 claims the whole file).
  - PK-56 against PK-34 on `api/main.py#routers`.
  - PK-49, then PK-59, then PK-66 on `ConnectorWorkspace.tsx`.
  - PK-52, then PK-62, then PK-69 on the privacy, trust and pricing pages, all after PK-6.
  - PK-44 after PK-21 on `docs/ops/incident-response.md`, and after PK-20 merges on the register.
  - PK-53 against PK-31 only if PK-31 also edits `pricing/schema.py`; it is planned not to.
- **Checked disjoint:** PK-42 (`salesforce-store.ts`, `salesforce-crypto.ts`) against PK-26
  (`salesforce-adapter.ts`, `salesforce-types.ts`); PK-39 (`diagnostic.py#load_report`) against PK-28
  (`#map_headers`) and PK-33 (`#response`); PK-46 against PK-25's live claims (new files only, plus the
  `#adapters` component after PK-25 merges).

## Exact commands, after founder approval only

Not run. For each task, in id order, the same shape as the Phase B entries, for example:

```powershell
$env:PYTHONPATH = "C:\Pricing-AI"
python tools/agentctl.py add PK-39 "Route cpq_line exports through the quote-line roll-up and surface ask_user deals" `
    --agent backend-engineer --depends PK-27 `
    --acceptance "cpq_line files reach rollup_quote_lines before _exclude_open" `
    --acceptance "ask_user deals are surfaced in LoadReport, never dropped or counted as lost" `
    --test tests/test_ingest_profiles.py --test tests/test_ingest.py
python tools/agentctl.py assign PK-39 --worktree .claude/worktrees/PK-39 `
    --own "pricing/ingest.py#profiles" --own "api/routers/diagnostic.py#load_report" --own tests/test_ingest_profiles.py
```

`agentctl assign` referees every claim above; a refusal means the sequence in this file is wrong, and
the fix is to re-plan, not to force.

## Changes on entry, 2026-11-09

Entered by pk-lead with `agentctl add`, 35 tasks, all in BACKLOG, owners and dependencies exactly as in
the tables above. `python tools/agentctl.py check` after entry: `OK: 66 task(s), 0/2 active, no
collisions, no unmet dependencies on live work.`

Claims changed:
- **PK-46: `api/routers/crm.py#adapters` replaced by `api/routers/crm.py#analyze` and
  `api/routers/crm.py#source`.** Checked against the PK-25 worktree (PR #75 head `c2c2fbf`, read-only):
  there is no adapter resolution and no `pricing/adapters/` package. `SalesforceAdapter` lives in
  `pricing/crm.py` as a module singleton `ADAPTER`, `CsvAdapter` in `pricing/csv_adapter.py`, the
  protocol in `pricing/guardrail.py`, and `api/routers/crm.py` binds `_SOURCE = crm_mod.ADAPTER.system`
  at module scope and uses it for the decision log in workflow, reconcile, writeback and the log read.
  PK-46 therefore claims the analyze route plus the source binding, and gains one acceptance line: the
  registry in `pricing/adapters/__init__.py` imports the two existing adapters without moving or editing
  them (so PK-46 does not touch `pricing/crm.py` or `pricing/csv_adapter.py`), the router resolves the
  adapter and the log source per request, and a request with no `source_system` resolves to salesforce.
  Without the `#source` claim, PK-48's "workflow events log with source.system = hubspot" had no owner
  on the API side.
- **Glob claims converted to directory claims**, because `agentctl` refuses glob patterns: `tests/fixtures/hubspot/**`,
  `tests/fixtures/stripe/**`, `tests/fixtures/chargebee/**`, and every `web/src/app/api/<vendor>/<route>/**`
  in PK-47, PK-48, PK-57, PK-58, PK-64 and PK-65 are now the directory without `/**`. A directory claim
  conflicts with everything beneath it, so the coverage is the same.

No claim was changed to resolve a collision: `check` reported none, and a dry-run of every new claim
against live and backlog claims found only overlaps that the dependency chains already sequence
(PK-44 after PK-6 and PK-20 via PK-21; PK-45 after PK-19 and PK-22; PK-46 after PK-25; PK-52, PK-62,
PK-69 after PK-6 and each other; PK-39 then PK-40; PK-24 then PK-41 then PK-70; PK-49 then PK-59 then
PK-66; PK-56 then PK-63).

Acceptance changes on the board: F3, F4 and F5 lines are written into PK-47, PK-49, PK-56, PK-57, PK-59 and PK-64; F6
is noted on PK-46 and PK-55. Founder-only prerequisites appear on the board as acceptance lines that
begin "Founder setup:" (PK-47, PK-48, PK-50 for HubSpot; PK-57, PK-58, PK-60 for Stripe; PK-64, PK-65,
PK-67 for Chargebee) or "Founder gate:" (PK-44 founder approval, PK-45 counsel, PK-70 seven days on prod).
Required tests are the test files in each task's owns, plus regression suites named in acceptance:
`tests/test_ingest.py` on PK-39, `tests/test_crm.py` and `tests/test_guardrail.py` on PK-46,
`neon/test_migrations.py` on PK-70.

Open, for the lead of record: on `origin/main` the `/diagnostic` response is built by
`diagnostic_payload` in `api/shared.py`, not in `api/routers/diagnostic.py`. PK-39 ("the diagnostic
response includes" the ask_user section) and PK-33 (`api/routers/diagnostic.py#response`) will both
likely need `api/shared.py#diagnostic_payload`, which neither claims. Before either is assigned, add
that component to the claim of whichever runs first and sequence the other behind it; do not let either
edit outside its claim.

## Lead resolutions on entry, 2026-11-09

1. `api/shared.py#diagnostic_payload` is claimed by PK-39 when it is assigned; PK-33 sequences behind PK-39 and claims the component after PK-39 merges.
2. One adapter layout, revised at PK-46 assignment on 2026-11-09 to match the board acceptance: PK-46 creates the `pricing/adapters/` package with a registry that imports `SalesforceAdapter` from `pricing/crm.py` and `CsvAdapter` from `pricing/csv_adapter.py` without moving or editing either (PK-25 had just merged, and a move would churn a reviewed module). New adapters (HubSpot, Stripe, Chargebee) live in the package; moving the two existing ones in is a later cleanup task, not part of PK-46, PK-55 or PK-63.
3. F2 stays a sequencing recommendation, not a declared dependency: PK-54 does not depend on PK-32.

## Sequencing note, 2026-11-09: site redesign overlap

The site redesign (PK-75 to PK-84, `TASKS-redesign-proposed.md`) was entered on 2026-11-09. PK-77 owns `web/src/app/pricing/page.tsx` and PK-82 owns the trust and privacy pages, which PK-52, PK-62 and PK-69 also claim. `agentctl` cannot add dependencies to tasks already on the board, so the order is a lead rule: **PK-52 is not moved to READY or assigned until PK-77 and PK-82 are MERGED**; PK-62 and PK-69 inherit the order through their existing dependency on PK-52. `assign` refuses the overlap while either side holds a live claim. PK-83 (the `/crm` workspace restyle) depends on PK-49 on the board and starts from PK-49's merged version. No redesign task claims a `web/src/lib` connector or Salesforce path or anything under `web/src/app/api`.

## Lead notes from the PR 78 and PR 74 reviews, 2026-11-09

- PK-44 (data register amendment) adds a row for `source_mappings`: header strings and field names only, no FK, no cascade, deleted by `customer_ref` on disconnect or tenant revoke.
- PK-43 (operator revoke path) includes `source_mappings` in the rows it deletes for a tenant.
- PK-28 carries an explicit acceptance line: the database CHECKs enforce shape only; `pricing/mapping_store.py` enforces that no header string or mapping value is a row value, with a test.
- Migration file names follow `YYYY-MM-DD-slug`; PK-24 renames to `2026-11-09-source-mappings`, and PK-41 uses a later date so the files sort in dependency order.
- PK-39 cites the common Stripe subscriptions export header set (`id, Customer ID, Plan, Interval, Amount, Status`) as a billing shape that the mapper does not refuse because its id column is bare; PK-39 or the Stripe connector decides how it is recognised.

## Lead decision from PK-53, 2026-11-09: billing rows never enter win rate, enforced twice

PK-53 found that `pricing/guardrail.py` has no source awareness: a billing-sourced row with outcome `closed_won` would be accepted into win rate today. Decision: (1) at the schema level, billing-sourced deal rows carry the marker outcome `billing_only`, never `closed_won` or `closed_lost`; the contract-period grain itself has no outcome column; adapters for Stripe and Chargebee (PK-55, PK-63) emit the marker. (2) At the engine level, PK-54 gains an acceptance line: the guardrail or the billing analysis path refuses rows whose `source_system` is a billing source from any win-rate computation by source, not only by outcome, with a test that a billing row labelled `closed_won` by a buggy caller is still excluded and disclosed. The connector design doc row that said billing outcome is "closed_won by construction" is superseded by this note.

## Lead decisions from the PR 84 review, 2026-11-09

- `discount_amount` on the contract-period grain holds coupon and discount objects only (percentage or amount off). Custom-price overrides and ramp-phase gaps are not discounts: they appear as `list_amount` minus `invoiced_amount` with `discount_amount` 0, so the identity is `list_amount >= invoiced_amount + discount_amount + credit_amount`. Free months (a 100 percent coupon for N periods) map to credits, never also to `discount_amount`, matching lens spec section 2.2.
- PK-54 gains two acceptance lines: readiness discloses billing-sourced rows by count (today they are counted nowhere on the guardrail path); the refusal by `source_system` does not rely on `win_rate_eligible` alone until PK-72 lands alias handling (unknown aliases such as `stripe_billing` currently read as csv).
- The answer key carries the committed figure for metered accounts so PK-54 and PK-55 have a commit value to recover.
