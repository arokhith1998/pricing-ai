# Pricekeel Salesforce end-to-end acceptance record

Status: production-deployed engineering evidence; customer-launch gates remain.
Recorded: 2026-08-01.

## Result

The merged release is free of known test, lint, TypeScript, and production-build errors.
The real production Salesforce connector is verified through OAuth, metadata,
mapping, encrypted persistence, and bounded sync. The complete live pricing
decision loop is **not** claimed: the dedicated Developer Edition org has 18
usable closed outcomes, below the deliberate 30-outcome evidence floor.

That warning is an evidence-quality control, not a software failure. Do not
lower the threshold or describe synthetic data as customer validation.

## Automated gates

| Gate | Result |
|---|---|
| Python business/API suite | 195 passed |
| TypeScript Salesforce connector suite | 5 passed across 3 files |
| ESLint | Passed |
| Next production build | Passed, 40 routes, Next 16.2.12 |
| `git diff --check` | Passed |

The TypeScript suite now covers tenant-bound signed OAuth state, S256 PKCE,
tamper rejection, one-time access-token refresh with refresh-token
preservation, reauthorization after a second 401, and rejection of unreadable
Salesforce mapping fields.

The Python suite now covers the decision-integrity corrections plus:

- pending overrides receive a closed outcome;
- reconcile performs one latest-history lookup for the whole batch;
- deal history is scoped by `deal_id` before applying a limit;
- Salesforce Task success/failure is appended as a separate audit event;
- writeback events do not replace the underlying workflow state.

## Live production evidence

Verified against the founder's Salesforce Developer Edition org:

- PR #45 merged to `main` at `ccdaf31` and the attached Vercel production
  deployment completed successfully;
- External Client App authorization-code flow with PKCE;
- API plus offline/refresh scope consent;
- expected-org binding;
- AES-256-GCM encrypted access and refresh values in Neon;
- Opportunity field discovery;
- field mapping save/reload;
- on-demand Salesforce query and canonical mapping;
- 18 usable closed and 13 usable open Opportunities;
- correct analytical block below 30 usable closed outcomes;
- post-deploy Salesforce refresh on `www.pricekeel.com/crm` returned the same
  counts and blocker with no browser console errors;
- landing, sample, pricing, trust, and contact routes rendered without an
  application error or browser console error;
- both temporary internal Pricekeel acceptance codes were revoked after the
  live check. The Salesforce connection remains encrypted and tenant-bound.

No Salesforce password, OAuth token, encryption key, or Pricekeel access code
is stored in this record.

## Code defects closed in this branch

- Approve/reject decides the terms saved on the override request rather than a
  percentage posted at approval time.
- A requester cannot approve or reject their own request under the normalized
  self-asserted actor check.
- A pending override remains reachable after the Opportunity leaves the open
  set.
- Closing while `flagged` or `override_requested` no longer drops the outcome.
- Outcome reconciliation no longer performs one database query per closed
  Opportunity.
- Deal history no longer loads the tenant's latest 500 rows and filters in
  Python.
- Salesforce Task failures retain a sanitized Salesforce reason and an
  append-only writeback result.
- A token rejected after a successful refresh becomes `reauth_required`; a
  later healthy request clears a transient connection error.
- A revoked or missing Pricekeel access code shows a tenant-aware sign-in card
  instead of a false warning that Salesforce production variables are absent.
- Next was upgraded from 16.2.6 to 16.2.12 to close the direct current Next
  advisories reported by npm.

## Known release gates

1. Run the live decision/writeback/reconcile lifecycle with 30+ credible closed
   fixtures and one open fixture.
2. Verify disconnect/revocation and reconnect.
3. Build and install the packaged ECA through a Salesforce DX managed-package
   release in a subscriber org before connecting an external customer.
4. Replace self-asserted actor names with authenticated per-user identity and
   an approver role/allowlist before claiming formal segregation of duties.
5. `npm audit --omit=dev` still reports three high transitive advisories in the
   PostCSS and Sharp versions bundled by Next 16.2.12. npm proposes only an
   unsafe forced downgrade. The app does not accept customer CSS and does not
   use `next/image`, which reduces exposure, but this is a tracked dependency
   exception—not a zero-vulnerability claim. Re-test on the next patched Next
   release.

## Market and operating evidence

The category has credible budget and incumbent activity, documented in
`docs/reviews/2026-08-01-market-need-assessment.md`. Pricekeel demand remains
unvalidated until real operators authorize data and two customers pay for the
90-day pilot. Engineering acceptance must never be reported as market proof.
