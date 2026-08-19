# Pricekeel Salesforce integration runbook

Status: active operator manual, 2026-08-01. Owner: Pricekeel founder/admin.

This is the internal manual for onboarding a customer Salesforce org. It covers
the Pricekeel-controlled application setup, the customer-admin handoff,
verification, incident response, and disconnection. It is not the customer user
guide; see `docs/guides/customer-salesforce-workspace.md`.

## The deployment model

Pricekeel owns one Salesforce External Client App (ECA). Each customer installs
or approves that app in **their own** Salesforce production or sandbox org, then
an authorized customer user completes OAuth. Pricekeel never asks for a
Salesforce password and customers never receive Pricekeel's client secret.

The current Developer Edition connection proves the single-org pilot flow. It
does not by itself make the app distributable to arbitrary customer orgs. For
multi-customer onboarding, use a packaged ECA in a managed package and keep the
source org alive. Salesforce states that local ECAs are limited to their source
org and only packaged ECAs can be deployed elsewhere:
https://help.salesforce.com/s/articleView?id=sf.configure_packageable_external_client_apps.htm&language=en_US&type=5

## One-time Pricekeel setup

### 1. Create and retain the source app

1. Use a durable Salesforce source org with Dev Hub enabled for a 2GP package.
2. In Setup -> App Manager, create an External Client App.
3. Use distribution state `Packaged` for customer distribution. Use `Local`
   only for a controlled test in the same org.
4. Name the app `Pricekeel` and use a monitored support email.
5. Never delete the source ECA while subscriber orgs depend on its global OAuth
   settings.

Salesforce's current ECA creation steps are here:
https://help.salesforce.com/s/articleView?id=sf.create_a_local_external_client_app.htm&language=en_US&type=5

### 2. Configure OAuth

Set the following ECA OAuth settings:

| Setting | Required value |
|---|---|
| OAuth enabled | Yes |
| Callback URL | `https://www.pricekeel.com/api/salesforce/oauth/callback` |
| Flow | Authorization Code / Web Server |
| PKCE | Required |
| Client secret for web-server flow | Required |
| Client secret for refresh-token flow | Required |
| Scope | `api` |
| Scope | `refresh_token` / `offline_access` |

Do not request `full`. Pricekeel refreshes live Opportunity data and can create
a completed Task only when the connected user's Salesforce permissions permit
it. Salesforce's object permissions, field-level security, and sharing rules
remain authoritative.

Official OAuth settings reference:
https://help.salesforce.com/s/articleView?id=xcloud.configure_external_client_app_oauth_settings.htm&language=en_US

### 3. Package for customer orgs

1. Retrieve the ECA metadata into a Salesforce DX project.
2. Add the packageable ECA to a 2GP managed package.
3. Configure package defaults for the OAuth policy.
4. Create and test a beta package version in a clean scratch or sandbox org.
5. Promote only after install, authorize, refresh, and uninstall tests pass.
6. Store the install URL and version in the customer onboarding record.

This is a release gate before the first external customer's org is connected.
The current repository does not yet contain a Salesforce DX package, and the
2026-08-01 Developer Edition test is not a substitute for this step.

### 4. Configure Pricekeel production

Set these server-side Vercel production variables:

```text
SALESFORCE_CLIENT_ID=<consumer key>
SALESFORCE_CLIENT_SECRET=<consumer secret>
SALESFORCE_OAUTH_REDIRECT_URI=https://www.pricekeel.com/api/salesforce/oauth/callback
SALESFORCE_LOGIN_URL=https://login.salesforce.com
SALESFORCE_TOKEN_ENCRYPTION_KEY=<separate high-entropy secret>
SALESFORCE_API_VERSION=67.0
DATABASE_URL=<Neon pooled connection string>
PRICEKEEL_SECRET=<access-cookie signing secret>
```

Use `https://test.salesforce.com` only for a sandbox-specific deployment.
After changing an environment variable, create a fresh production deployment;
do not assume an old deployment snapshot inherited it.

Apply `neon/schema.sql` to the production database. Confirm that the following
tables exist: `access_codes`, `crm_connections`, `crm_mappings`,
`decision_log`, and `competitor_context_sources`. On a database provisioned
before 2026-08-18, apply
`neon/migrations/2026-08-18-crm-provider-generalization.sql` first: it renames
`salesforce_connections` / `salesforce_mappings` and adds the `provider`
column. The migration is idempotent and preserves existing rows.

### 5. Provision the customer tenant

Generate a high-entropy, URL-safe access code outside SQL. Insert it with the
customer name and an explicit expiry:

```sql
insert into access_codes (code, issued_to, expires_at)
values ('<random-token>', '<customer>', now() + interval '30 days');
```

Share the code through an approved secure channel. Never place it in Git,
Obsidian, screenshots, CRM notes, or support logs. V1 uses the verified access
code as the tenant key, so issue one code per customer and revoke it promptly
when the engagement ends.

## Customer-admin prerequisites

The customer should designate a least-privilege Salesforce integration user.
It needs:

- API Enabled.
- Read access to Opportunity and the fields selected in Pricekeel mapping.
- Read access to Account name/type/industry and Opportunity Products when
  those fallbacks are used.
- Create access to Task only if Salesforce writeback will be enabled.
- Sharing access to every Opportunity the customer expects Pricekeel to
  analyze.
- Permission to use the installed ECA, preferably through a dedicated
  permission set.

For the first pilot, request a sandbox before production whenever the customer
has one. Do not ask for Modify All Data.

## Per-customer onboarding

1. Execute the NDA/data addendum and record the customer's Salesforce admin,
   business owner, and technical contact.
2. Confirm data readiness before installation: one currency for V1, at least
   30 usable closed outcomes for a directional view, a target of 500+ closed
   outcomes per year for operating guidance, reliable booked value, and a
   reliable annualized list value or Opportunity Product list value.
3. Send the managed-package install URL and the requested permission list to
   the Salesforce admin.
4. The admin installs the package, approves the ECA policy, and assigns its
   permission set to the designated integration user.
5. Give the customer their Pricekeel access code.
6. The integration user signs in at `https://www.pricekeel.com/login`, opens
   `/crm`, and chooses **Connect Salesforce**.
7. The user signs in to the intended Salesforce org, verifies the org name,
   reviews the two scopes, and selects **Allow**.
8. Back in Pricekeel, confirm `Connected`, the intended org, and no OAuth
   error.
9. In **Field mapping**, map booked value and annualized list value first, then
   optional segment, product, value metric, competitor, approver, and term
   fields. Set the customer's documented policy threshold and save.
10. Select **Refresh analysis** and review the readiness panel with RevOps. Do
    not suppress blockers by inventing mappings.

## Acceptance checklist

Record pass/fail and timestamp for every item. Store counts and statuses, not
tokens or raw customer rows.

- OAuth start, callback, and connected status succeed.
- The returned org is the intended org.
- API and refresh-token scopes are present; no broader scope is present.
- Access and refresh tokens exist only as AES-256-GCM ciphertext in Neon.
- Field discovery returns the customer's readable Opportunity fields.
- Mapping saves and reloads for the same tenant.
- A refresh reports fetched, usable closed, usable open, excluded, and
  currency counts.
- No raw Opportunity row is stored in the Pricekeel database.
- An open test Opportunity appears in Deal desk.
- A rep can accept guidance or request an override with a justification.
- An approver using a different identity can approve or reject the recorded
  request without altering the requested terms.
- When enabled, a completed Salesforce Task is related to the Opportunity and
  contains the evidence summary.
- Closing the test Opportunity produces one `outcome_recorded` event.
- A pending override remains actionable after its Opportunity leaves the open
  set.
- Disconnect removes the tenant connection and Salesforce access is revoked
  best-effort; reconnect succeeds.

The actor field is still self-asserted in V1. The same-actor guard prevents the
obvious self-approval path, but this is not equivalent to authenticated
separation of duties. Do not represent the audit trail as production-grade
approval governance until per-user SSO and an approver role/allowlist ship.

## Troubleshooting

| Symptom | Check | Action |
|---|---|---|
| `authorization_denied` | User denied consent or lacks app access | Assign ECA permission and retry |
| `invalid_oauth_state` | Attempt expired, cookie missing, or different tenant session | Return to `/crm` and restart OAuth |
| `token_exchange_failed` | Callback mismatch, wrong secret, or ECA disabled | Compare the callback character-for-character and rotate the secret if needed |
| `reauth_required` | Refresh token expired/revoked | Reconnect from `/crm` |
| Missing fields | Field-level security on integration user | Grant read access or select another readable field |
| Fewer rows than expected | Salesforce sharing or 730-day lookback | Check the integration user's list view/API visibility and close dates |
| Fewer than 30 usable closed | Missing/non-positive list or booked values | Fix CRM data/mapping; do not lower the evidence floor |
| Multiple-currency blocker | More than one `CurrencyIsoCode` | Segment by currency in a future release; V1 must not combine dollar totals |
| Decision logged, Task failed | Task create permission or Salesforce outage | Keep the Pricekeel event, correct Task permission, and retry as a new explicit action |

## Rotation and offboarding

- Rotate the ECA client secret and `SALESFORCE_TOKEN_ENCRYPTION_KEY` under a
  written migration plan; changing the encryption key without re-encrypting
  stored tokens breaks every connection.
- Revoke the customer's access code when the pilot ends.
- Use **Disconnect Salesforce** before deleting customer records.
- Verify the `crm_connections` row (provider `salesforce`) and its cascading
  mapping row are gone.
- Retain the append-only decision record only under the contracted retention
  period and data-handling SOP.
