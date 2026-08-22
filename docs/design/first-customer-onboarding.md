# Design: onboarding the first real Salesforce and HubSpot customer

Status: draft, pending `cto` and `skeptic` review and founder approval.
Date: 2026-08-22.
Companion to `docs/design/hubspot-crm-integration.md`.

## Goal

A named customer on Salesforce, and a named customer on HubSpot, can each
connect their CRM to Pricekeel and receive a diagnostic. Not a demo. A real org.

## Why this doc exists

The founder asked for HubSpot parity with Salesforce, on the premise that
Salesforce is onboarding-ready. Verification on 2026-08-22 showed that premise is
false in a specific way: Salesforce is **complete in code** and **unproven in
distribution**, and contracting is blocked for both providers. Building HubSpot
slices 3 to 5 without closing those first produces a second provider that is
equally unable to onboard anyone.

## Verified state (2026-08-22)

Gathered read-only against the tree and git history.

**Salesforce: complete in code.** PKCE OAuth, AES-256-GCM token encryption,
refresh with `reauth_required`, five `/crm/*` endpoints, 271 lines of
deterministic logic in `pricing/crm.py` with no LLM on the number path, real
writeback to `sobjects/Task`, 28 tests. `grep "__c"` across `web/src/` returns
zero matches: field selection is fully dynamic via the describe API, so a stock
customer org with no customization can complete the flow. No namespace
dependency. The permission set is least-privilege. No Salesforce security review
is required for direct-install distribution.

**HubSpot: 2 of 5 slices.** Slices 1 and 2 (schema generalization, OAuth
connect) are done and well built: signed-state CSRF with nonce and cookie
binding, proactive refresh, path-prefix allowlist, bounded 429 retry, and a
correct refusal to store a connection lacking a refresh token.
`hubspotApiRequest` has **zero callers**. HubSpot appears in **zero** pages or
components: no human can start the flow.

## Blockers, by category

### A. Legal (blocks BOTH providers; not code; founder-owned)

`docs/legal/` contains one file, `one-page-mutual-nda-data-addendum.md`, whose
own header says **"NOT SIGNABLE in its current form"** pending counsel review and
a formed legal entity. `web/.env.example` confirms `NEXT_PUBLIC_LEGAL_ENTITY` and
`NEXT_PUBLIC_LEGAL_JURISDICTION` await incorporation and render as bracketed
placeholders. Runbook per-customer onboarding step 1 is "execute the NDA/data
addendum."

**That step cannot be executed today.** This is the true gating item. No
engineering work removes it.

### B. Salesforce distribution (unproven; partly founder-owned)

- The unlocked package `04tak000000aPeDAAU` (commit `f04b86a`) has **never been
  installed outside its source org**. `salesforce/config/project-scratch-def.json`
  was added "for package install testing" on 2026-08-08; no result is recorded.
- Unknown whether version 0.1.0-1 was **promoted**. An unpromoted beta cannot
  install into a customer production org.
- The ECA carries `orgScopedExternalApp = 00Dak000016fI9t:Pricekeel`. Whether
  that pins the app to the source org at runtime is unresolved, and only an
  install test settles it.
- If `00Dak000016fI9t` is a Developer Edition org, every subscriber's OAuth
  depends on an org subject to inactivity deactivation.

### C. Documentation defects (cheap; engineering-owned)

- `docs/ops/salesforce-2gp-packaging.md` says `--package-type Managed` and
  requires registering a namespace. The real package is **Unlocked** with
  `"namespace": ""`. Following that doc creates a second, wrong package and
  orphans the alias. **Destructive if followed.**
- Runbook line 72 claims no DX package exists. It has existed since 2026-08-08.
- Runbook lines 12-15 say each customer "installs or approves" the app. For a
  packaged ECA, install is mandatory; the approve-only path is not available.
- No **admin-facing** install guide exists. The customer guide says to ask your
  admin to install, then stops: no install URL, no permission-set assignment, no
  FLS grant steps.
- Salesforce edition requirements are documented nowhere. API access is standard
  on Enterprise and above, a paid add-on on Professional, absent on Essentials.
  Part of the ICP will be Professional orgs.

### D. Code defects (engineering-owned)

- **`SALESFORCE_LOGIN_URL` is deployment-wide.** `salesforceLoginUrl()`
  (`web/src/lib/salesforce-oauth.ts:44`) feeds authorize, token exchange,
  refresh (`salesforce-client.ts:69`), and revoke (`:251`). One deployment serves
  production **or** sandbox, never both. The runbook promises sandbox-first at
  line 128 and contradicts itself at line 90.
- **Privacy policy names Salesforce 6 times, HubSpot 0 times.** Connecting a
  HubSpot portal today processes CRM data under a policy that does not describe
  it. Legal exposure, not polish.
- **`api/main.py` hardcodes the Salesforce audit source.** Literal
  `source="salesforce_crm"` at `:1087`, `:1144`, `:1160`, `:1213`, and a filter on
  exactly `salesforce_crm` plus `salesforce_crm_writeback` at `:1255`. A HubSpot
  decision logged today is mislabeled as Salesforce, and `_crm_deal_history`
  (`:949`) looks up history by that same hardcoded source.
- **Operator-facing copy hardcodes Salesforce** in `pricing/crm.py` at `:49`,
  `:58`, `:88`, `:215`, `:271`. A HubSpot customer sees Salesforce errors.
- **Access-code rotation destroys CRM connections.** `web/src/lib/gate.ts:58`
  returns the raw access code as the tenant key, and `crm_connections` is keyed on
  `customer_ref`. The runbook's 30-day expiry silently orphans a customer's tokens
  and field mapping.

## Proposed sequence

Ordered so each step either unblocks a later one or removes a live hazard.
Steps marked FOUNDER are not engineering work.

**Phase 0. Stop the bleeding (small, immediate)**

1. Fix `salesforce-2gp-packaging.md`: Unlocked, drop the namespace prerequisite.
   Prevents a destructive second package.
2. Fix the stale and contradictory runbook lines (72, 12-15, 90 versus 128).
3. FOUNDER: run `sf package version list` and confirm `IsReleased`. Confirm the
   org type of `00Dak000016fI9t`.

**Phase 1. Prove the distribution model (the load-bearing unknown)**

4. FOUNDER plus engineering: install `04tak000000aPeDAAU` into a fresh scratch
   org and complete a full OAuth round trip. Commit the result. Until this
   passes, every downstream estimate is a guess.
5. Write the admin install guide.

**Phase 2. Make one deployment serve both org types**

6. Store the login host per connection at connect time; thread it through
   `salesforceLoginUrl()`, refresh, and revoke. Remove the runbook contradiction.

**Phase 3. Make the platform provider-neutral (prerequisite for HubSpot)**

7. De-hardcode the audit source in `api/main.py`; carry `provider` through the
   decision log. Migrate or dual-read existing `salesforce_crm` rows.
8. Parameterize operator-facing copy in `pricing/crm.py`.
9. Amend the privacy policy to cover HubSpot. **Blocks any HubSpot connection.**

**Phase 4. HubSpot to parity**

10. Slice 3: pipelines and stage map. An unmapped stage is a **blocker**, never
    "open". Highest risk; own slice; own tests.
11. Slice 4: deal fetch, normalization to `CanonicalCrmDeal`, HubSpot readiness
    with thresholds revalidated rather than inherited from Salesforce.
12. UI: provider selector and a Connect HubSpot entry point.
13. Slice 5: extract the adapter interface the two implementations justify.
14. HubSpot customer guide. Determine and document the minimum tier.

**Phase 5. Contracting (FOUNDER, parallel, gates go-live)**

15. Incorporate; set the legal env vars.
16. Counsel review of the NDA and data addendum.
17. Extend `docs/ops/data-handling-sop.md` to cover CRM data.
18. Correct the effective dates on `/subprocessors` and `/terms`.

## Explicit non-goals

- HubSpot writeback. Scopes are read-only; the write-scope decision is deferred
  until after slice 3, per the founder.
- AppExchange or App Marketplace listing. Direct install is sufficient, and that
  decision is already documented and correct.
- A generic `CrmAdapter` interface before slice 5.
- Any LangGraph adoption in `pricing/`.

## Open questions for review

1. Does phase 3 need a data migration for existing `salesforce_crm` decision-log
   rows, or is dual-read acceptable? Rewriting an append-only audit log is itself
   a governance question.
2. Is the per-connection login host the right fix, or should sandbox pilots be
   refused in V1 and the runbook corrected instead? The second is nearly free.
3. Should the access-code-as-tenant-key defect be fixed before the first
   customer, or documented as a do-not-rotate operational constraint?
4. Is phase 1 genuinely blocking, or can HubSpot proceed in parallel on the
   theory that its OAuth model carries no equivalent packaging risk?
