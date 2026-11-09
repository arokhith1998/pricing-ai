---
title: Native connectors, HubSpot then Stripe then Chargebee
created: 2026-11-09
updated: 2026-11-09
tags: [design, connectors, hubspot, stripe, chargebee, data-governance]
status: draft
source: vault/Decisions/2026-11-09-named-connectors-hubspot-stripe-chargebee.md
---

# Native connectors: HubSpot, then Stripe, then Chargebee

Status: proposed by pk-lead, 2026-11-09. Not approved to build. Task list:
`docs/reviews/2026-11-06-product-direction/TASKS-connectors-proposed.md` (PK-39 to PK-73).
Modelled on `docs/design/salesforce-crm-workflow-v1.md`. The decision this plans against is
settled; this document records how, not whether.

**What I inspected versus assumed.** Inspected: the Salesforce web libs and routes, `neon/schema.sql`,
`api/routers/crm.py`, the PK-25 worktree (`pricing/guardrail.py`, uncommitted, with a
`DealSourceAdapter` protocol whose only method is a pure `to_canonical`), the PK-27 worktree
(`rollup_quote_lines`, `ask_user`), `pricing/schema.py` on `origin/main` (PK-23 fields;
`SourceSystem` is `csv | salesforce | hubspot | cpq | billing | manual`), `web/src/lib/gate.ts`, and two
unmerged August branches, `feat/crm-provider-schema` and `fix/tenant-key-opaque`, which already hold
a provider-keyed connection migration with a down file, a HubSpot OAuth flow, a HubSpot design doc and
an opaque tenant key. Assumed, from general platform knowledge and not verified against current vendor
docs: every HubSpot, Stripe and Chargebee API detail below (scope names, rate limits, object fields).
Each connector's first web task verifies them before code depends on them.

## 1. Scope, order, and what each connector can deliver

| Connector | Population | Delivers | Cannot deliver |
|---|---|---|---|
| HubSpot (CRM) | Won, lost and open deals | The full loop: win rate by discount band, leakage, realization against list, live exception guidance, decision log, outcome reconciliation | List price when reps type an amount and use no line items (the readiness blocker fires, as on Salesforce) |
| Stripe (billing) | Paying customers only | Contracted versus billed, price realization against a confirmed list, usage actuals by period, coupon and credit concessions, ramp schedules where subscription schedules exist | **Win rate.** Billing holds no closed-lost deals. Commit, unless the tenant marks where it lives. Margin of any kind. |
| Chargebee (billing) | Paying customers only | Same as Stripe, plus contract terms where the site uses them | Same as Stripe |

Said plainly: Stripe and Chargebee on their own give leakage and realization, never win rate. A
tenant that wants win rate pairs a billing connector with a CRM connection (Salesforce or HubSpot) or
a CRM export. Every billing readout states this in its first line, from code, not from copy.

Order is the founder's: HubSpot, Stripe, Chargebee. Nothing starts before PK-25 merges.

## 2. Shared connector framework

### 2.1 One source-keyed connections table (PK-41)

A new table `source_connections`, primary key `(customer_ref, source_system)`, replaces
`salesforce_connections`. Columns: `source_system` (check: `salesforce | hubspot | stripe |
chargebee`), `external_account_id` (Salesforce org id, HubSpot portal id, Stripe account id, Chargebee
site), `instance_url` (nullable, Salesforce only), `credential_kind` (`oauth_refresh | restricted_key |
api_key`), `access_token_encrypted` (nullable), `credential_encrypted`, `key_id`, `scope`,
`token_expires_at`, `status` (`connected | reauth_required | error | revoked`), `last_error`,
`last_sync_at`, `last_sync_counts jsonb`, timestamps. A sibling `source_connection_config` cascades
from it and generalises `salesforce_mappings`: vendor field mapping, confirmed stage map, confirmed
list-price set, policy threshold, default value metric. Config only, never values.

Migration style is expand then contract, not the August rename. PK-41 creates the new tables and
backfills Salesforce rows idempotently; old tables stay. PK-42 moves the web store onto the new table.
PK-70 drops the old tables after a soak, with a guarded down file. Reason: a rename breaks the
running Salesforce code mid-deploy; expand and contract never has a broken intermediate state.

**PK-24 does not absorb this.** PK-24 is on the Phase B critical path to PK-28, it is low risk, and
the founder approved it as scoped. Connection generalisation moves live encrypted tokens and needs a
web cutover and a security-grade review; bundling it would hold Phase B hostage to the custody gates.
Cost of the split: PK-41 serialises behind PK-24 on `neon/schema.sql`, and PK-37 must then run
before or after PK-41, never alongside. PK-41 also adds `access_codes.tenant_ref` (section 2.3), so
the schema file is touched once for both.

The August branches are reference material, not merge candidates: they predate PK-1, PK-23 and the
2026-09 fixes. Agents read them and port what still fits.

### 2.2 Credential custody per vendor

| Vendor | Credential | Lifetime | Pricekeel can revoke at vendor? |
|---|---|---|---|
| HubSpot | OAuth public app, unlisted, direct install link; refresh token plus 30-minute access token | Refresh token until uninstall | Yes: refresh-token delete call, then the customer uninstalls |
| Stripe | Customer-created **restricted key**, read-only on a listed resource set (recommended, F1) | Until the customer rolls it | **No.** We delete our copy; only the customer can roll the key |
| Chargebee | Customer-created read-only API key plus site name | Until the customer deletes it | **No.** Same as Stripe |

**Stripe: restricted key, not Connect or Stripe App OAuth, for v1.** Reasons: no platform application
or app review on Pricekeel's side; the customer chooses the exact read permissions in their own
dashboard and can kill the key instantly; free test mode works the same way; there is no refresh logic
to get wrong. Costs: a long-lived bearer secret sits in our database, and revocation depends on the
customer. Controls: refuse any key starting `sk_` (full secret key) and accept only `rk_`; validate
with one read call on save; never display the key again. Revisit Stripe App OAuth (short-lived tokens)
at three Stripe tenants or the first security review that asks. Chargebee keys carry no prefix that
reveals read-only, so we cannot verify the permission level; the setup screen and runbook say so.

**Encryption.** Same AES-256-GCM scheme as `salesforce-crypto.ts`, one key for all vendors, extended in
PK-42: a `v2` ciphertext format with a key id, additional authenticated data binding
`customer_ref|source_system|field` (so a ciphertext cannot be transplanted between rows or tenants), and
a decrypt-only previous key. `v1` Salesforce ciphertexts still decrypt and are rewritten as `v2` on
the next refresh. This closes the August finding that key rotation, as written in the runbook, would
destroy every live connection.

**Revoke on request, within 24 hours** (NDA section 12). PK-43 adds an operator path that, given a
tenant ref and no customer session, decrypts each stored credential, revokes at the vendor where an
API exists (Salesforce, HubSpot), deletes every row, and prints the keys the customer must roll
themselves (Stripe, Chargebee). The opaque tenant key fixes the August finding that revoking the
access code first makes disconnect target the wrong tenant.

**What the data register and incident response must list (PK-44)**: one row each for HubSpot refresh
tokens, Stripe restricted keys, Chargebee API keys and site names, the connector encryption key and
its previous key, and the HubSpot app client secret; one row stating billing rows and invoice lines are
in memory only, nothing retained. Incident containment: rotate the connector key, delete all stored
credentials, revoke HubSpot and Salesforce tokens by API, and notify each Stripe and Chargebee tenant
to roll their key, because we cannot. PK-45 drafts the per-customer credentials amendment the NDA
already requires and updates the readiness checklists, which today tell prospects "no API keys".

### 2.3 Bounded sync, reused from Salesforce

Salesforce today pulls closed deals from the last 730 days plus all open deals, capped at 9,999 rows,
on each workspace load; nothing is persisted. Every connector uses the same contract:

- **Closed window**: 730 days. **Open**: all open deals (CRM only). **Cap**: 10,000 records per
  analysis, the existing `/crm/analyze` limit, with the fetched count disclosed.
- **On demand**: pulled when the workspace loads or the user refreshes. No background jobs, no webhooks
  in v1, so there is no webhook signature surface yet.
- **Idempotent reconciliation**: the existing `/crm/reconcile` path records `outcome_recorded` once
  per `(tenant, source_system, source_record_id, outcome)`.
- **Field whitelist at fetch**: the web tier drops every field not on the whitelist before anything
  leaves the fetch function. No contact, email, phone, address or tax id ever reaches Python, logs or
  the browser.

Where code runs: auth, fetch and the whitelist live in the web tier (as Salesforce does); vendor to
canonical mapping and all money arithmetic live in Python adapters behind PK-25's protocol, pure and
known-answer tested. That keeps the rule that no surface computes a number, and lets backend and web
work run in parallel.

### 2.4 Mapping to the canonical deal, with provenance

Every connector sets `source_system`, `source_record_id`, `source_account_id`, `source_quote_id` (when
one exists) and an absolute `source_url` on every canonical deal. PK-53 adds `stripe` and `chargebee`
to `SourceSystem` (vendor-level, like `salesforce` and `hubspot`); `billing` stays for vendor-unknown
CSV exports. PK-23's `value_metric_unit`, `list_unit_rate` and `credits_tcv` are filled where a
vendor can supply them and left blank otherwise. No connector sets `cost_basis` or `cogs_acv`.

### 2.5 Where the per-tenant snapshot (D1) fits

Connectors do not depend on it. The live workspace scores against a freshly pulled book, as Salesforce
does. When PK-38 lands, PK-73 refreshes the snapshot after each successful CRM sync, so `/quote` can
score HubSpot tenants. D1 approved aggregates the guidance engine needs (band win rates, references,
policy); billing aggregates are not in that list, so nothing billing-derived persists unless the founder
extends D1 (F7).

## 3. HubSpot

**Outcome resolution, the highest-risk mapping.** A deal's outcome is not on the deal: `dealstage`
holds a stage id whose meaning lives in the pipeline definition. Rules:

- Fetch every deal pipeline and its stages. Propose closed won where the stage metadata says closed
  with probability 1.0, and closed lost where it says closed with probability 0.0.
- **The user confirms the stage map before the first analysis.** Unconfirmed, unknown or ambiguous
  stages are `ask_user`. Those deals are shown to the user by stage and count, excluded from analysis,
  and never treated as lost. A deal in an open stage with a past close date is open, never lost.
  Lost is never inferred.
- Each pipeline is resolved separately. A stage added after confirmation flips the map back to
  unconfirmed for that pipeline.

**Properties to canonical fields.** `amount` to `booked_acv` unless the user maps an annualised
property (`hs_acv` where populated); list from line items (unit price times quantity, before line
discounts) unless a list property is mapped; `closedate`, `createdate`, `hubspot_owner_id` to `rep_id`,
pipeline or a mapped property to `product_tier`, mapped properties for segment, term, approver,
competitor, value metric. Line item property names are verified in PK-47 before PK-46's mapping is
final.

**Amount and currency.** `deal_currency_code` per deal; the existing guard refuses to sum mixed
currencies. A user may map `amount_in_home_currency` instead; the readout then states that HubSpot's own
exchange rates converted the values.

**Associations.** Deal to company through the associations API: company name to `account_name`,
company id to `source_account_id`, plus user-mapped company properties for segment and industry. No
contacts are read and no contact scope is requested.

**Rate limits.** Assumed about 100 to 190 requests per 10 seconds per install and a slower search
endpoint with a 10,000-result cap per query; batch reads for associations and line items, date-sliced
searches above the cap, one bounded retry honouring `Retry-After`. Verified in PK-47.

**Scopes, least privilege.** Read-only: deals, companies, line items, deal schemas (properties),
owners, plus whatever pipelines require. Adding a scope after install forces every customer to
reauthorise, so the scope list is frozen by PK-47's verification before any customer install, and the
writeback question (F3) is answered first.

**Web surface.** `/crm` gains a source switcher. `SalesforceWorkspace.tsx` is split into a shared
`ConnectorWorkspace` (executive, pricing, deal-desk views, `DecisionControl`, decision log) and a
per-vendor setup panel; HubSpot adds the stage-map confirmation screen. Types use PK-26's
`CanonicalDeal`. The decision loop (flag, accept or override, approve or reject, log, outcome) is
unchanged. No writeback in v1 unless F3 says otherwise.

## 4. Stripe

**Objects read.** Customers (id, name, metadata only), subscriptions with items, prices and products,
subscription schedules, invoices and invoice lines for the window, credit notes, coupons and discounts,
credit grants where the account uses them. Never payment methods, charges or customer contact fields.

**Derivations (all in `pricing/adapters/stripe.py`, method named on each):**

| Canonical field | From | When not derivable |
|---|---|---|
| `list_acv` | Product default price (confirmed by the user as list) times quantity, annualised by interval | Price not confirmed as list: `insufficient_data` |
| `booked_acv` | Contracted recurring amount after coupons and custom prices, annualised. Labelled "contracted (billing)", never "booked" | none |
| `platform_fee_acv` | Licensed (non-metered) items, after discounts | none |
| `usage_acv` | Trailing billed metered amount from invoices, annualised | Fewer than 6 billed periods: `insufficient_data` |
| `list_unit_rate` | Default price unit amount of the metered product | Tiered prices: `not_provided` in v1 |
| `overage_rate` | Customer's per-unit metered price | Tiered prices: `not_provided` in v1 |
| `committed_acv` | Only from a source the user marks (a metadata key or a commit product) | `not_provided`. Stripe has no first-class commit |
| `credits_tcv` | Trial days at list, 100-percent-off coupon periods, promotional credit grants | blank |
| `ramp_year_1_acv`, `ramp_year_2_acv` | Subscription schedule phases | No schedule: blank |
| `term_months` | Schedule or `cancel_at` | Evergreen: blank, flagged |
| `outcome`, dates | `closed_won` by construction; start and created dates as proxies, flagged | |

**Billing grain (PK-53).** `contract_period_actuals`, the second grain the CTO proposed and Phase B
deferred: one row per subscription per billed period with `period_start`, `period_end`, `currency`,
`list_amount`, `invoiced_amount` (tax excluded), `discount_amount`, `credit_amount`, `usage_units`,
`usage_amount`, and `committed_amount` when known. Built from invoice lines, which are already period
rollups, so NDA Class 2 (rollups only, no row-level usage events) holds. Meter event streams are never
read. In memory only.

**The closed-lost gap.** Billing-sourced rows never enter the win-rate path: the guardrail refuses
them and the billing readout returns the win-rate lever as `not_provided` with the reason "billing data
holds paying customers only; win rate needs closed-lost deals from a CRM". The readout shows
contracted versus billed, realization against confirmed list, concessions, and usage actuals, side by
side with a connected CRM's readout. Joining billing rows to CRM deals per account is PK-71, gated
on F4.

## 5. Chargebee: differences only

- Credential: read-only API key plus site name. The host is built as `<site>.chargebee.com` from a
  site name validated against `^[a-z0-9-]{1,63}$`; nothing else is caller-supplied.
- Catalog: v1 supports Product Catalog 2.0 sites only (item prices, subscription items with
  `unit_price` overrides, which give list versus contracted directly). Catalog 1.0 sites are refused
  with a clear message. To verify in PK-64.
- Contract terms: where the site uses contract terms, `term_months` and term value come from them.
- Ramps: Chargebee ramps feed the ramp fields the same way as Stripe schedules.
- Promotional credits feed `credits_tcv`; usage comes from invoice line items, never the usages API.

## 6. Hard rules

1. The LLM computes nothing. Connectors do not touch the mapper or the LLM layer; stage maps and list
   prices are confirmed by a person.
2. Every output names its method (`band_guardrail`, `billing_realization`, `contracted_vs_billed`),
   and every derived field records how it was derived.
3. Insufficient data is per lever and explicit: `scored | insufficient_data | not_provided`. No global
   fallback, no zero fill.
4. No margin from a proxy (ADR-006). Billing holds no product cost: no connector sets `cost_basis` or
   `cogs_acv`, and no output says "margin". Stripe processing fees are not cost of goods.
5. Row-level customer data is processed in memory and deleted. Only connection metadata, encrypted
   credentials, config, the decision log and the D1 aggregates persist.
6. No customer data in logs: no deal rows, invoice values, account names or tokens in server logs,
   errors or Sentry. Errors carry codes and counts.

## 7. Security review items for code-reviewer

- **Outbound calls.** All vendor calls run in the web tier with a compile-time host (`api.hubapi.com`,
  `api.stripe.com`) or the validated Chargebee subdomain, a path prefix allowlist (as in the August
  `hubspotTarget`), redirects refused, and timeouts. Any Python outbound call goes through
  `pricing/_safe_fetch.py`; the design has none.
- **Token encryption.** `v2` format with key id and AAD; production fails closed without the key;
  plaintext never reaches the browser, a response, or a log.
- **Tenant scoping.** Every read and write filters on `customer_ref` from `customerRef()`, never from
  the request. The operator revoke path is not reachable from the internet.
- **OAuth.** HubSpot has no PKCE; the signed state plus a signed httpOnly cookie bound to the tenant are
  the CSRF control, as in the August branch.
- **Key intake.** Stripe `sk_` keys refused; keys are write-only in the UI.
- **Webhooks.** None in v1. Any later webhook verifies the vendor signature before parsing.
- Trust-critical diffs (custody, crypto, migrations, billing money math) get `tools/oai_review.py
  --diff`, with no customer data.

## 8. Effort and sequence

| Group | Tasks | Days |
|---|---|---|
| Phase B follow-ups from PK-27 | PK-39, PK-40 | 2.5 |
| Shared framework and custody | PK-41 to PK-45, PK-70 | 7.5 (1 doc-only) |
| HubSpot | PK-46 to PK-52 | 15 (0.5 doc-only) |
| Stripe, including shared billing work | PK-53 to PK-62 | 20.5 (9.5 of it shared billing) |
| Chargebee | PK-63 to PK-69 | 10.5 |
| **Connectors total** | 30 tasks | **53.5** |
| Optional, gated | PK-71 join, PK-72 billing export profile, PK-73 snapshot refresh | 5 |

**Against the CFO and decision estimates.** The decision priced the three connectors at 7 to 9 weeks
(about 35 to 45 days). This plan is 53.5 days, about 10.5 founder-weeks. The difference is honest, not
padding: custody and tenancy work the decision did not price (opaque tenant key, key rotation, operator
revoke: about 6 days); per-connector QA, runbooks and claim copy (about 7.5 days across the three); and
shared billing work at 9.5 days rather than "roughly a week", because no billing analysis exists today.
HubSpot alone (15 days, 3 weeks) and Chargebee (10.5 days, about 2 weeks) match the decision; Stripe
does not.

**Under the two-slot cap.** Doc-only tasks (PK-44, PK-45, PK-51, PK-61, PK-68) take no slot. Phase B
remainders (PK-24, PK-26, PK-28, PK-29) plus PK-39, PK-40 and PK-6 total about 12 days and share the
two slots with the framework. The HubSpot critical path is PK-24, PK-41, PK-42, PK-43, PK-47, PK-48,
PK-49, PK-50: 18 task-days serial, plus about a day of review, QA and human merge per task. The
HubSpot Python adapter (PK-46) runs in the other slot. **PK-6 is on this critical path**: PK-47 needs
PK-44, which needs PK-21, which needs PK-6, which is READY and unstarted. Dispatch PK-6 next.

**Earliest live dates.** "Live" means running on production against the founder's test portal or test
account. Customer-live also needs a partner on that platform and a signed credentials amendment
reviewed by counsel; neither exists.

- **HubSpot**: earliest 2026-12-18; realistic early to mid January 2027, given US holidays and
  founder merge throughput.
- **Stripe**: earliest 2027-01-22; realistic early February 2027. Assumes Phase C runs in the second
  slot during HubSpot (F2).
- **Chargebee**: earliest 2027-02-12; realistic late February to early March 2027.

That spends most of the 13 founder-weeks the CFO counted for two quarters, and it overlaps the February
pilot or LOI gate in the fundraise plan. The founder accepted this trade on 2026-11-09; it is stated
here so the dates are not a surprise.

## 9. Founder decisions required (only those that change what gets built)

- **F1. Stripe credential mode.** Restricted key (recommended, section 2.2) or Stripe App OAuth (about
  3 more days plus Stripe app review, shorter-lived tokens). Needed before PK-57.
- **F2. Billing connectors before or after the Phase C lens.** Recommended: run PK-31 to PK-33 in the
  second slot during HubSpot, so Stripe data feeds scored commit, ramp and overage levers. Otherwise
  Stripe ships descriptive only, and Phase C slips about two weeks. Needed by early December.
- **F3. HubSpot writeback.** Recommended: none in v1, read-only scopes; Pricekeel's log is the record
  and the readout deep-links to the deal. If yes (a note or task on the deal, like the Salesforce Task),
  add about 1.5 days and a write scope, decided before any install because a scope change forces
  reauthorisation.
- **F4. Join billing to CRM deals in v1 (PK-71, 2.5 days)?** Recommended: no; side-by-side readouts
  first, the join after a partner shows a shared deal id.
- **F5. Allow a billing-only tenant?** (Part of open D6.) Recommended: yes, with the no-win-rate line.
  If no, the Stripe and Chargebee connect screens require a CRM source first.
- **F6. Tenant-declared list price book** as the list fallback for HubSpot portals without line items
  and Stripe custom prices, labelled "declared list". About 2 days, no tasks written. Recommended:
  decide after the interview module shows how many HubSpot prospects use line items.
- **F7. Persist billing aggregates** (extends D1). Recommended: no for v1. Only needed if billing
  realization should appear on `/quote`.

Prerequisites, not decisions: PR #62 (PK-20, PK-22, PK-19 in REVIEW) must merge; the founder creates a
HubSpot developer account, app and test portal, a Stripe test-mode account and a Chargebee test site.
