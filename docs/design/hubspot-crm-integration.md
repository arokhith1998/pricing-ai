# HubSpot CRM integration - design document

Status: proposed, 2026-08-18. Owner: founding engineer. Not approved to build.
Second native CRM after `docs/design/salesforce-crm-workflow-v1.md`. Reuses that
document's product decision, evidence boundary, and workflow. It does not widen
scope: HubSpot becomes a second source for the same canonical deal frame.

## Why now

Salesforce-only cuts the stated ICP roughly in half. B2B SaaS in the $10M-$100M
ARR band skews HubSpot, and `pricing/mapping.py:30` already carries HubSpot's
"Record ID" as a mapping synonym with `data/synthetic/format-fixtures/
hubspot_export.csv` as a fixture, so the CSV path was built multi-CRM from the
start. Only the live-sync path is Salesforce-specific.

## Finding that changes the auth approach

**HubSpot private apps are not viable here, despite being the obvious fast
path.** A private app token is created inside the customer's own portal, needs
no marketplace listing, and never expires, which makes it look ideal for
design-partner pilots.

HubSpot's own documentation rules it out for this use: the token carries the
access of the user who created it, and API calls fail if that person leaves the
account. For a vendor reading a customer's CRM that is an outage with no
warning and no recovery path we control. HubSpot has also moved private app
creation under "Legacy apps" in the developer UI, which is a direction signal.

**Decision: OAuth 2.0 public app, unlisted, installed via a direct install
link.** This is the structural equivalent of the Salesforce External Client App
already built, so the existing token lifecycle carries over almost unchanged.
No App Marketplace listing is required to install via direct link.

Differences from the Salesforce flow: HubSpot uses a client-secret exchange
rather than PKCE, access tokens are short-lived (30 minutes) while refresh
tokens do not expire. The refresh-and-reauth logic in
`web/src/lib/salesforce-client.ts:64-119` maps over directly.

## Object model deltas

| Concern | Salesforce (built) | HubSpot |
|---|---|---|
| Object | Opportunity | Deal |
| Field discovery | `sobjects/Opportunity/describe` | `GET /crm/v3/properties/deals` |
| Query | SOQL with pagination | `POST /crm/v3/objects/deals/search`, `after` cursor |
| Won / lost | `IsWon`, `IsClosed` on the record | **Not on the record.** See below |
| Line items | `OpportunityLineItems` subquery in one SOQL call | Separate associations call, then batch read |
| Currency | `CurrencyIsoCode` | `deal_currency_code`, multi-currency is a paid tier |
| Annualized value | Not native, must be derived | `hs_acv`, `hs_arr`, `hs_mrr`, `hs_tcv` native |

### The outcome-resolution trap

This is the highest-risk difference and it has no Salesforce analogue.

A HubSpot deal's outcome is not a field on the deal. `dealstage` holds a stage
ID, and whether that stage means won, lost, or open lives in the pipeline
definition: `GET /crm/v3/pipelines/deals` returns stages carrying
`metadata.isClosed` and `metadata.probability`, where closed-won is
`isClosed: true` with `probability: 1.0` and closed-lost is `isClosed: true`
with `probability: 0.0`.

Pipelines are per-portal, customer-configured, and may carry up to 100 stages
across multiple pipelines. Getting this wrong misclassifies the entire book
silently, which is strictly worse than the degenerate-list-value trap that
`pricing/crm.py:_guard_degenerate_list` already defends against, because a
misclassified book still produces plausible-looking numbers.

Required: fetch pipelines, build a stage-ID to outcome map, and treat any deal
whose stage ID is absent from the map as a **blocker**, never as "open". A
readiness check must report the resolved stage map back to the operator during
onboarding so a human confirms it before any diagnostic runs.

### List price is weaker than in Salesforce

Salesforce has Pricebooks and `ListPrice` / `UnitPrice` / `TotalPrice` on line
items. HubSpot has a product library with a price and
`hs_discount_percentage` on line items, but a large share of HubSpot users type
an amount directly onto the deal and never create line items at all.

Consequence: `list_source: "none"` will be far more common than on Salesforce.
The existing `MISSING_LIST_BLOCK_SHARE` and `DEGENERATE_LIST_SHARE` guards in
`web/src/lib/salesforce-adapter.ts:56-59` become more load-bearing, not less,
and their thresholds should be re-validated against HubSpot data rather than
inherited unexamined.

Partial offset: `hs_acv` and `hs_arr` are native, which helps the ramp and
annualization disclosure problem that the Salesforce adapter can only warn
about. They are only populated when the customer uses line items with recurring
terms, so their presence is itself a readiness signal.

## Architecture: do not build a generic adapter interface yet

Recommendation: keep `CanonicalCrmDeal` and the readiness result as the shared
contract, and write `hubspot-*.ts` modules alongside the Salesforce ones. Do
not refactor Salesforce behind a polymorphic `CrmAdapter` first.

Reasoning: `CanonicalCrmDeal` in `web/src/lib/salesforce-adapter.ts:19-40`
already is the seam. It is the normalization target, it is provider-neutral,
and everything downstream of it already works for any CRM. The divergences
above (auth exchange, query language, outcome resolution, line-item retrieval)
are large enough that an interface designed before the second implementation
will encode Salesforce's shape and then need rewriting. The second
implementation is what teaches you where the seam actually belongs. Refactor
after, on evidence, not before, on speculation.

The genuine shared infrastructure is narrower and should be extracted now:

- `salesforce-crypto.ts` is provider-agnostic AES-256-GCM already. Rename to
  `crm-crypto.ts`, no logic change.
- The connection and mapping tables need a provider dimension (below).
- Readiness scoring shares its output type and most of its threshold logic.

## Schema change

`neon/migrations/2026-08-01-salesforce-crm-workflow.sql` defines
`salesforce_connections` keyed on `customer_ref` alone, with
`salesforce_mappings` referencing it.

Proposal: generalize to `crm_connections` and `crm_mappings` with a `provider`
column (`salesforce` | `hubspot`) and a composite primary key of
`(customer_ref, provider)`. `instance_url` generalizes to a nullable
`instance_url` (Salesforce) plus `portal_id` (HubSpot), or a single `provider_
account_id` text column carrying whichever applies.

**Do this now rather than adding a parallel `hubspot_connections` table.** With
zero customers there is no production data to migrate, so this is the cheapest
moment in the product's life to change the schema. Every month of delay makes
it more expensive and the duplication harder to unwind.

## Failure modes

| Failure | Mitigation |
|---|---|
| Unmapped deal stage silently read as "open" | Blocker on any stage ID absent from the pipeline map; operator confirms the map at onboarding |
| Multiple pipelines with conflicting stage semantics | Resolve per pipeline, never globally; report each pipeline separately in readiness |
| No line items, so no list price | Existing missing-list blocker fires; thresholds re-validated for HubSpot |
| Token invalid after connecting user leaves | OAuth app rather than private app, which is the reason for that decision |
| Search API result cap on large books | Cursor pagination with an explicit fetched-count disclosure, matching the Salesforce `LOOKBACK_DAYS` bound |
| Rate limits (100-190 requests per 10s by tier) | Batch reads, bounded lookback, backoff on 429 |

## Build slices

1. **Schema migration and crypto rename.** `crm_connections` / `crm_mappings`
   with `provider`, `crm-crypto.ts`, Salesforce paths updated to the new tables.
   No HubSpot code. Existing tests must stay green, which is the gate.
2. **OAuth connect flow.** Install link, callback, encrypted token storage,
   refresh and reauth, disconnect. Mirrors `salesforce-oauth.ts`.
3. **Pipeline and property discovery.** Fetch pipelines, build the stage map,
   fetch deal properties for mapping. Surface the stage map for confirmation.
   This is the risky half and deserves its own slice.
4. **Deal fetch and normalization to `CanonicalCrmDeal`,** plus HubSpot-specific
   readiness assessment.
5. **Refactor pass.** With two live implementations, extract the interface the
   evidence supports.

Slice 1 is a pure refactor with a test gate and no new capability, so it is
safe to land independently of whether the rest proceeds.

## Testing

- Fixture-based normalization tests mirroring `web/test/*.test.ts`, including a
  multi-pipeline portal and a portal with custom stage labels.
- Outcome-resolution tests: unmapped stage must block, never default to open.
- Missing-line-item portal must produce `list_source: "none"` and the blocker.
- Token-refresh and reauth paths, mirroring the Salesforce coverage.

## Open decisions

- Single `provider_account_id` column versus separate `instance_url` and
  `portal_id`.
- Whether slice 1 lands on `feat/link-tracking` or its own branch.
- Whether HubSpot onboarding reuses the Salesforce workspace guide at
  `docs/guides/customer-salesforce-workspace.md` or needs its own.
