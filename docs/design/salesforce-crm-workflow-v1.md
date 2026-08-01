# Salesforce-first CRM workflow V1 - design document

Status: approved to build, 2026-08-01. Owner: founding engineer.
Supersedes the earlier "native OAuth later" sequencing in
`docs/design/buyer-funnel.md`. It does not authorize unrelated capability
expansion.

## Product decision

Pricekeel becomes a pricing-intelligence layer that participates in the CRM
workflow. The long-term system can combine CRM/CPQ history, billing/ERP cost and
contract data, product-usage telemetry, and sourced public competitor evidence.
The first production slice is deliberately narrower:

- Salesforce is the first native CRM.
- CRM/CPQ data supports discount intelligence and deal guidance.
- A below-guardrail deal follows `flag -> recommend -> accept/override ->
  approve/reject -> log -> outcome`.
- Competitor evidence is contextual only. It never changes a numerical
  guardrail in V1.
- True margin analysis waits for billing/ERP cost data. Application-level
  recommendations wait for usage telemetry. The UI and landing page must not
  imply otherwise.
- CSV/XLSX stays as the diagnostic and onboarding path, not the primary product
  experience.

The initial customer profile is a sales-led or hybrid B2B SaaS company using
Salesforce, roughly $20M-$100M ARR, with at least 500 closed won/lost
opportunities per year, reliable list and booked values, a documented discount
policy, and recurring exceptions. RevOps or Pricing is the champion; the CFO is
the economic buyer.

Primary outcome: improve price realization without reducing win rate at a
comparable deal mix. Supporting measures are exception turnaround time,
recommendation acceptance/override rate, and incremental booked ACV.

## Why this build is allowed now

The 2026-08-01 progress reset correctly stopped speculative feature expansion.
This workflow is the bounded validation instrument selected with the founder:
it creates the exact operating loop a Salesforce design partner can test. It
does not make synthetic data, a working connector, or a clean demo count as
customer validation. The paid-pilot evidence bar remains unchanged.

## User surfaces

One authenticated Salesforce workspace contains three views of the same live
data and workflow:

1. **Executive** - price realization, discount distribution, win rate at
   comparable discount bands, exception volume, turnaround, and estimated
   booked-ACV impact. No model jargon.
2. **Pricing / RevOps** - segment and product cuts, reference-discount basis,
   top deals to investigate, mapping quality, and data-readiness disclosures.
3. **Deal desk** - current open opportunities, recommendation and comparables,
   accept or override, manager approval/rejection, CRM activity writeback, and
   the append-only decision history.

The existing `/diagnostic`, `/guidance`, and `/competitor-watch` sample paths
remain useful for evaluation. The native workflow lives under `/crm` and
requires a real access code rather than the shared lead-demo identity.

## Salesforce authentication

### Chosen flow

Use a Salesforce **External Client App (ECA)** with OAuth 2.0 web-server
authorization-code flow and PKCE (`S256`). A legacy Connected App with the same
flow remains technically compatible for an existing test org, but setup
documentation defaults to ECA because Salesforce restricted creation of new
Connected Apps in Spring '26.

Requested scopes:

- `api` - read Opportunity metadata and records and, when the connected user
  has permission, create a completed Task activity for a pricing decision.
- `refresh_token` / `offline_access` - continue scheduled and return-session
  analysis without asking the user to log in on every access-token expiry.

Do not request `full`. Salesforce object permissions, field-level security,
sharing, and the ECA's permitted-user policy remain authoritative.

Security controls:

- Generate a high-entropy PKCE verifier and `S256` challenge for every start.
- Bind a short-lived, HMAC-signed OAuth state to the verified Pricekeel tenant.
- Keep the verifier in a short-lived `HttpOnly`, `Secure`, `SameSite=Lax`
  cookie; clear it on success and every failure path.
- Exchange the authorization code only in a server route. Never expose the
  client secret, access token, or refresh token to browser JavaScript.
- Encrypt tokens with AES-256-GCM before Neon storage. Production fails closed
  when the encryption key is missing.
- Refresh after a Salesforce 401 and persist a rotated refresh token when one
  is returned. A failed refresh marks the connection `reauth_required`.
- Restrict the stored `instance_url` to HTTPS Salesforce hosts and use it for
  API traffic after authentication; never accept a caller-supplied instance
  URL.
- Disconnect revokes the Salesforce token best-effort, then removes the local
  connection.

Production ECA distribution is a packaging task: a local ECA is sufficient for
the first controlled org, while customer orgs require the packaged ECA to be
installed and approved by their Salesforce administrator.

Official references, verified 2026-08-01:

- Salesforce web-server OAuth flow and PKCE recommendation:
  https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_web_server_flow.htm&language=en_US&type=5
- External Client App OAuth settings, callback matching, and refresh-token
  rotation:
  https://help.salesforce.com/s/articleView?id=xcloud.configure_external_client_app_oauth_settings.htm&language=en_US
- Spring '26 Connected App creation restriction and ECA migration direction:
  https://help.salesforce.com/s/articleView?id=005228017&language=en_US&type=1
- Salesforce ECA security and packageable-vs-local model:
  https://developer.salesforce.com/blogs/2025/01/secure-your-org-with-external-client-apps
- Summer '26 current Platform API version 67.0:
  https://developer.salesforce.com/blogs/2026/06/the-salesforce-developers-guide-to-the-summer-26-release

## Tenant and persistence model

The verified `pk_access` code is the V1 tenant key. Lead-only visitors cannot
connect a CRM because all Salesforce setup, metadata, sync, workflow, and
disconnect routes call `requireAccess()`.

Neon stores:

- encrypted Salesforce tokens and org/connection metadata;
- the selected field mapping and policy threshold;
- sync health and counts, but not raw Salesforce opportunity rows;
- the append-only decision log and its deterministic evidence;
- competitor watchlist/source metadata and extracted claims, each with URL,
  capture date, last-verified date, confidence, and source type.

Raw Salesforce rows are fetched server-to-server, transformed in memory, sent
to the existing protected FastAPI service, analyzed, and discarded. The
browser receives only the derived dashboard, the bounded open-deal view needed
for the workflow, and evidence for the selected deal. This means a refresh
queries Salesforce again; V1 chooses a simpler trust boundary over a local CRM
replica. Aggregate materialization can be added only after real-org performance
measurement.

## Field mapping and readiness

Salesforce schemas vary. The connector discovers readable Opportunity fields
through `sobjects/Opportunity/describe` and persists an explicit mapping.
Dynamic SOQL fields must come from that describe response and match a strict API
name pattern; user input is never interpolated directly.

Standard defaults:

| Pricekeel field | Salesforce source |
|---|---|
| opportunity/account IDs and names | `Opportunity.Id`, `Name`, `AccountId`, `Account.Name` |
| outcome | `IsClosed` + `IsWon` |
| created / close dates | `CreatedDate`, `CloseDate` |
| booked ACV | `Amount`, unless mapped to an annualized custom field |
| list ACV | sum of `OpportunityLineItems.ListPrice * Quantity`, unless mapped |
| booked line value | sum of `OpportunityLineItems.TotalPrice`, fallback `Amount` |
| product | first line's `PricebookEntry.Product2.Family`, unless mapped |
| segment | mapped custom field, fallback `Account.Type`, then `Unknown` |
| value metric | mapped field, otherwise an explicit workspace default |
| rep | `OwnerId` / `Owner.Name` |
| competitor, approver, term | optional mapped fields |

Readiness is explicit, never silently repaired:

- block analytical claims below 30 usable closed opportunities;
- label the recommended ICP threshold of 500 closed outcomes per year;
- block discount analysis when list or booked value is missing/non-positive;
- report excluded open records, missing line items, missing outcomes, and
  fallback/defaulted dimensions;
- preserve the Salesforce currency code when available and refuse to combine
  multiple currencies in one dollar total in V1.

## Analytics and recommendation boundary

The backend reuses the existing canonical schema and deterministic pricing
metrics. Closed Salesforce opportunities create the retrospective book. Open
opportunities are scored against the book without inventing a causal model:

- reference discount = the earliest adequately supported discount band whose
  win rate is statistically consistent with the peak;
- segment reference is used only when the existing sufficiency rules are met,
  otherwise the global reference is disclosed as the fallback;
- if the requested discount is at or below the reference, Pricekeel does not
  recommend increasing it;
- if it is above the reference, the reference becomes the guardrail and the
  difference in booked ACV is shown;
- historical band win rates and nearest comparable won/lost deals are evidence,
  not causal promises;
- competitor context can explain the rep's justification but cannot move the
  guardrail in V1.

## Workflow and Salesforce writeback

Every action is append-only in `decision_log` and tenant-scoped:

- `flagged` - requested discount exceeds the disclosed guardrail;
- `accepted` - rep accepts the recommendation;
- `override_requested` - rep requests a larger discount with justification;
- `approved` / `rejected` - manager disposition;
- `outcome_recorded` - the opportunity later closes won/lost.

For a completed action, the connector can create a Salesforce Task related to
the Opportunity (`WhatId`) with a Pricekeel subject and a compact evidence
summary. Writeback is explicit in the action request and is never required for
the Pricekeel log to succeed. A Salesforce write failure is reported separately
so the user never sees a false "logged in Salesforce" claim.

V1 does not install Apex, create custom fields, or silently update Opportunity
financial fields. A later managed package can add native Lightning components
and custom objects after the workflow is validated.

## Competitor context

The customer selects 3-10 named competitors. Public inputs may include pricing
pages, product documentation, release notes, case studies, funding
announcements, executive interviews, and, for public companies, quarterly
earnings/investor materials. Collection is quarterly plus event-triggered.

Every surfaced claim must carry its source URL, source type, captured date,
last-verified date, confidence, and a stale marker. The existing safe-fetch and
robots/host kill-switch boundary remains. Claims are qualitative annotations in
the deal view; they do not alter discount math.

## API and component boundaries

Next.js is the browser-facing backend-for-frontend:

- `/api/salesforce/oauth/start` and `/callback` own OAuth.
- `/api/salesforce/connection` returns safe status and disconnects.
- `/api/salesforce/metadata` discovers readable fields.
- `/api/salesforce/mapping` reads/writes tenant mapping.
- `/api/salesforce/workspace` fetches live Salesforce data and calls FastAPI.
- `/api/salesforce/workflow` logs a decision and optionally writes a Task.

FastAPI owns pricing business logic:

- `/crm/analyze` accepts bounded canonical records, returns diagnostic and
  per-open-deal guidance, and retains no request rows.
- `/crm/workflow` recomputes the selected verdict from submitted evidence and
  appends the workflow event. The browser cannot submit an arbitrary dollar
  impact as truth.

The Salesforce adapter and crypto/token store live in server-only TypeScript
modules. React components never import them.

## Configuration

Required for a real connection:

```text
SALESFORCE_CLIENT_ID=
SALESFORCE_CLIENT_SECRET=
SALESFORCE_OAUTH_REDIRECT_URI=https://pricekeel.com/api/salesforce/oauth/callback
SALESFORCE_LOGIN_URL=https://login.salesforce.com
SALESFORCE_TOKEN_ENCRYPTION_KEY=<32+ random bytes, base64 or high-entropy text>
SALESFORCE_API_VERSION=67.0
```

The sandbox login URL can be set to `https://test.salesforce.com`. Client ID,
secret, token encryption key, refresh tokens, and access tokens must never be
committed or pasted into logs.

## Acceptance criteria

1. A verified Pricekeel customer can connect and disconnect a Salesforce test
   org through real authorization-code OAuth with PKCE.
2. Tokens are encrypted at rest, tenant-scoped, redacted from responses, and
   refresh correctly after an access-token failure.
3. The setup view discovers fields, saves a mapping, and reports data readiness
   without fabricating required values.
4. A live sync returns the three product surfaces from real Opportunity data;
   no raw rows are persisted by Pricekeel.
5. A below-guardrail open deal can be accepted or overridden, approved or
   rejected, reconstructed from the append-only log, and optionally written to
   Salesforce as a completed Task.
6. Competitor evidence is sourced, dated, confidence-marked, stale-aware, and
   excluded from numerical guardrail computation.
7. Landing/pricing/trust/privacy copy matches the real data paths and removes
   unsupported V1 margin/application claims.
8. Python business-logic and API-perimeter tests, TypeScript lint, Next
   production build, and security checks pass.

Live acceptance criteria 1-5 remain unverified until the founder supplies a
Salesforce Developer/Sandbox org ECA configuration and production environment
variables. GitHub push and pull request remain separate from local completion
until `gh` authentication is restored.
