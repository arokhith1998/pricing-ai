# Design: onboarding the first real Salesforce and HubSpot customer

Status: **revised after `cto` review, 2026-08-22.** Pending `skeptic` review and
founder approval.
Companion to `docs/design/hubspot-crm-integration.md`.

## Goal

A named customer on Salesforce, and a named customer on HubSpot, can each
connect their CRM to Pricekeel and receive a diagnostic. Not a demo. A real org.

## Revision note

The first draft framed onboarding as a **distribution** problem. Review found it
is mostly a **tenancy and identity** problem, and found one factual error in the
draft itself (see "Corrections to the first draft"). The sequence below replaces
the original five serial phases with two parallel tracks.

## Verified state (2026-08-22)

**Salesforce: complete in code.** PKCE OAuth, AES-256-GCM token encryption,
refresh with `reauth_required`, five `/crm/*` endpoints, 271 lines of
deterministic logic in `pricing/crm.py` with no LLM on the number path, real
writeback to `sobjects/Task`, 28 tests. `grep "__c"` across `web/src/` returns
zero matches: field selection is fully dynamic via the describe API, so a stock
customer org with no customization can complete the flow. No namespace
dependency. The permission set is least-privilege. No Salesforce security review
is required for direct-install distribution.

**HubSpot: 2 of 5 slices.** OAuth connect is done and well built.
`hubspotApiRequest` has **zero callers**. HubSpot appears in **zero** pages or
components: no human can start the flow.

## Corrections to the first draft

1. **`source` is not a column on `decision_log`.** The draft proposed migrating
   or dual-reading `salesforce_crm` rows. There is nothing to migrate. `source`
   is a key inside `payload jsonb` and is filtered with `payload->>'source'`
   (`pricing/governance.py:191`, `:234`). The correct change is additive and
   costs no row writes. See "Provider dimension" below.
2. **`salesforceLoginUrl()` already validates hosts.** `web/src/lib/salesforce-oauth.ts:44`
   enforces HTTPS, rejects embedded credentials, and allow-lists
   `login.salesforce.com`, `test.salesforce.com`, and `*.my.salesforce.com`. The
   draft implied per-connection hosts would introduce unvalidated input.
3. **Phase 1 is not a prerequisite for HubSpot.** HubSpot's host is a
   compile-time constant (`hubspot-oauth.ts:25`), the client refuses any other
   origin (`hubspot-client.ts:32`), and no HubSpot code path consumes anything
   produced by the Salesforce package. That coupling was false. The package
   install test still goes first, but as **founder time running in parallel**,
   never as a gate on engineering.

## Blockers

### A. Tenancy and identity (highest consequence; retrofit is expensive)

**A1. The access code is overloaded four ways.** `web/src/lib/gate.ts:58`
returns the verified access code itself as the tenant key. That value becomes a
plaintext primary key in `crm_connections.customer_ref` and
`decision_log.customer_ref`, and travels to Render as `X-Pricekeel-Customer`. It
is also the credential shared over email. Three consequences:

- Rotating or expiring a code orphans that customer's CRM tokens and mapping.
- A shared bearer secret is stored in plaintext as a database key in two tables.
  A security review will call this a credential-in-database finding.
- **Offboarding is broken in the order the runbook prescribes.** The runbook says
  revoke the access code, then disconnect. In that order `isValidAccessCode`
  fails, `customerRef()` falls back to `"default"`, and disconnect targets the
  wrong tenant. The customer's encrypted refresh token stays in the database and
  stays live at Salesforce, with no in-product way to revoke it.

Fix: add `tenant_ref` to `access_codes`, populate with an opaque random id at
issue time, return that from `customerRef()`. All other call sites consume the
return value unchanged. Zero production rows to migrate.

**A2. There is no deletion path for `decision_log`.** `pricing/governance.py`
has `insert`, `list`, and `latest_by_deal`, and no `delete` or `purge`.
Meanwhile `docs/ops/data-handling-sop.md` promises 30-day deletion with written
certification and `/privacy` promises retention of engagement plus 12 months.
Neither is executable. Append-only forbids **mutation**; it does not forbid a
contractually scoped tenant purge.

**A3. `/privacy` understates what the decision log retains.** Line 237 says live
Salesforce Opportunity rows are "not persisted in the Pricekeel database. They
exist only for the duration of the server-to-server analysis request."
`api/main.py:1086-1097` persists, per decision, the Opportunity id (`deal_id`),
the account name, the discount figures, and a verdict.

To be fair to the code: the analysis **row set** genuinely is not persisted, and
only deals a human acted on produce a decision record. That distinction is real
and defensible. But the privacy language is absolute and carves out no
exception, so a reviewer diffing the retention schedule against the schema will
flag it. **The fix is to amend the privacy copy, not the code.** The audit trail
is the product.

**A4. Actor identity is self-asserted.** `api/main.py:1089` records
`"actor_assertion": "self_asserted"`, honestly. But the product sold is a
decision-integrity audit trail routed to an approver, and an approval chain where
the approver's name is free text a rep types is not segregation of duties. Decide
explicitly: either ship V1 with that labeled in the product UI and the pilot
agreement, or gate on real identity. Silence turns a pilot into a dispute.

**A5. Encryption-key rotation is documented but not implemented.**
`web/src/lib/crm-crypto.ts:27` resolves a single key and the ciphertext carries a
format version but **no key id**. The runbook instructs rotating the key. There
is no re-encryption routine, so following that step destroys every live
connection. Either add a key id plus a decrypt-only previous key, or change the
runbook to say rotation requires reconnecting every customer.

### B. Legal (blocks BOTH providers; founder-owned; runs in parallel)

`docs/legal/` contains one file whose header says **"NOT SIGNABLE in its current
form"** pending counsel and a formed legal entity. Runbook onboarding step 1 is
"execute the NDA/data addendum." That step cannot be executed today. No
engineering work removes it, and it does not argue against building.

### C. Salesforce distribution (unproven; founder-owned)

- Package `04tak000000aPeDAAU` has **never been installed outside its source
  org**, despite a scratch-org definition added for exactly that test on
  2026-08-08.
- Unknown whether version 0.1.0-1 was **promoted**. An unpromoted beta cannot
  install into a customer production org.
- Whether `orgScopedExternalApp = 00Dak000016fI9t:Pricekeel` pins the app to its
  source org at runtime is unresolved. Only the install test settles it.
- If `00Dak000016fI9t` is a Developer Edition org, every subscriber's OAuth
  depends on an org subject to inactivity deactivation.

### D. Provider coupling (prerequisite for HubSpot)

- **Provider dimension.** Add `"provider"` as a **new key** in the payload
  written at `api/main.py:1087`, `:1144`, `:1160`, `:1213`. Keep `source` as the
  kind discriminator; do not invent a `hubspot_crm` source value, which would
  duplicate the provider dimension into a string enumerated at every filter.
  Read provider-tolerantly at `:1255`, `:951`: a row with no `provider` key is
  Salesforce by definition, because no other provider existed when it was
  written. **No rows are touched.** If provider filtering becomes hot, add an
  expression index on `payload->>'provider'`, which is derived rather than
  written.
- **`CanonicalCrmDeal` is not provider-neutral.** `salesforce-adapter.ts:36`
  declares `salesforce_url`, set at `:274` as a **relative** Lightning path, and
  `SalesforceWorkspace.tsx:53` concatenates it onto the instance URL.
  `pricing/crm.py:182` reads the same field. HubSpot's deep link is absolute.
  Rename to `crm_deal_url` carrying an absolute URL and drop the concatenation.
- **Operator-facing copy hardcodes Salesforce** in `pricing/crm.py` at `:49`,
  `:58`, `:88`, `:215`, `:271`.
- **Privacy, subprocessors, and trust pages name Salesforce only.** Connecting a
  HubSpot portal under them is processing described nowhere.
- **`SALESFORCE_LOGIN_URL` is deployment-wide**, so one deployment serves
  production or sandbox, never both. The runbook promises sandbox-first at line
  128 and contradicts itself at line 90.

### E. HubSpot-specific risks

**E1. Scope changes are irreversible after install.** `hubspot-oauth.ts:31`
requests six scopes chosen for slice 2. Slice 3 needs
`GET /crm/v3/pipelines/deals`. Verify whether that is covered by
`crm.objects.deals.read` or requires `crm.pipelines.deals.read` **before any
customer installs**, because adding a scope forces every existing install to
reauthorize. This is HubSpot's analogue of the packaging risk.

**E2. The list-price data risk may invalidate slice 4.**
`MISSING_LIST_BLOCK_SHARE = 0.2` and `DEGENERATE_LIST_SHARE = 0.9`
(`salesforce-adapter.ts:59`) plus the 30-closed floor (`pricing/crm.py:230`)
mean a stock HubSpot portal where reps type an amount onto the deal, with no
line items, produces **zero output**, correctly and by design. If that is the
common case, slice 4 builds a connector that blocks on most portals. Half a day
in a free HubSpot developer account settles it. **This spike goes first and can
invalidate the rest of the HubSpot work.**

## Sequence: two parallel tracks

**Track A (founder; gates go-live, gates no engineering)**

1. `sf package version list --target-dev-hub devhub`, read `IsReleased`.
2. Confirm the org type of `00Dak000016fI9t`.
3. Install `04tak000000aPeDAAU` into a fresh scratch org, full OAuth round trip.
   Commit the result, pass or fail.
4. Admin install guide (install URL, permission-set assignment, FLS grant).
5. Incorporate; set the legal env vars.
6. Counsel review of the NDA and data addendum.

**Track B (engineering; ordered by consequence)**

0. Phase 0 doc fixes. Packaging runbook done at `20b9345`. Remaining: the
   offboarding order, the key-rotation claim, and runbook lines 72 and 12-15.
1. **Tenant-key fix** (A1). One function, one additive migration, zero rows.
2. **Provider-neutralization** (D): payload `provider` key with dual-read,
   `crm_deal_url` rename, `pricing/crm.py` copy, privacy policy covering HubSpot.
3. **Decision-log tenant purge** (A2), and reconcile `/privacy` retention with
   the data addendum and the SOP (A3).
4. **Login host**: use the stored, already-validated instance origin for refresh
   and revoke; store a `login_env` enum, not a host string, for authorize. Free
   text never enters the system, so the validation question disappears rather
   than being answered.
5. **Actor-identity decision** (A4) recorded as an ADR, whether built or labeled.
6. **HubSpot data spike** (E2). Half a day. May invalidate step 7.
7. Slice 3 (stage map; unmapped stage is a **blocker**, never "open"), slice 4,
   and a minimal HubSpot UI entry point.

Steps 1 through 5 are days, not weeks, and every one is work required before any
real org connects, regardless of which CRM it uses.

## Scope decision: not "full parity"

Slice 5 (adapter extraction) and the HubSpot customer guide are **deferred**. The
HubSpot spec's own argument, extract the interface after two implementations on
evidence, applies with more force after a customer exists than before. Slice 5
buys zero customer value now.

The minimal HubSpot UI entry point is **kept**: without it, slices 1 and 2 are
dead code, which is the worst possible state.

The deeper reason parity is the wrong target: the ICP is usage-based and hybrid
SaaS, but `list_acv` and `booked_acv` come from CRM Amount fields. That is
quote-time list versus booked, which is legitimate and scrupulously labeled as
such in the code. It is **not** commit, ramp, overage, or realized price, which
live in the billing platform. Doubling the connector surface for the layer that
does not hold the pricing truth, before one customer has accepted the CRM-only
framing, is scope creep wearing a completeness costume.

## Explicit non-goals

- HubSpot writeback. Scopes are read-only; that decision is deferred until after
  slice 3, per the founder.
- AppExchange or App Marketplace listing. Direct install is sufficient.
- A generic `CrmAdapter` interface (slice 5).
- Any LangGraph adoption in `pricing/`.

## Open questions remaining after review

1. A4: label self-asserted actors in the UI and pilot agreement, or gate on real
   identity before the first customer? This is a positioning call, not a
   technical one.
2. A5: implement key-id rotation, or downgrade the runbook to say rotation is a
   planned outage requiring every customer to reconnect?
3. What retention period for CRM-derived decision records goes into both
   `/privacy` and the data addendum? They must agree, and counsel review (Track A
   step 6) is the natural forcing function.
