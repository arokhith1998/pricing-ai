# Data register

Owner: Adhithya Bhaskar (adhithya@pricekeel.com). Created 2026-11-07 (task PK-20).
Contract: `docs/ops/data-handling-sop.md` section 5. Used by: `docs/ops/incident-response.md`
section 2 (scoping).

## How this register is used, and what it never holds

In an incident, open this file first. Part A says which classes of data the system holds,
where, and who deletes or rotates them. Part B says which customers' data sits in those
places. Together they answer the scoping questions: which customers, which categories,
which window, confirmed or only possible.

This register holds locations only. It contains no customer data, no customer deal values,
and no secret values (no keys, tokens, passwords, or access codes). Part B uses the
customer slug, never a contact name.

If the register and reality disagree, that is an incident-response trigger, not a paperwork
error. A location marked "unverified" has not been confirmed from the repo or a console and
must be confirmed before it is relied on in scoping.

## Part A. System-held data classes

One row per class. Verified date 2026-11-07 means checked against the repo on that date, not
against a live console.

| Data class | Contains | Never contains | Location | Retention | Deletion or rotation owner | Last verified |
|---|---|---|---|---|---|---|
| Customer deal rows | Closed-deal rows a customer sent: list and booked values, discount, dates, segment fields. Derived working files and readouts made from them. | Nothing is excluded; this is the most sensitive class. Never pasted into any LLM or third-party service. | Web path (pricekeel.com/upload): process memory during the request only, nothing retained. Emailed path: `C:\pricekeel-customer-data\<customer-slug>\` on the founder machine (BitLocker or VeraCrypt volume, excluded from sync, indexing, backup). Whether the volume is actually encrypted and excluded: unverified. | Web path: none, discarded when the request ends. Emailed path: delete within 30 days of engagement end or on request, whichever is sooner (SOP section 4), with written certification. | Founder (Adhithya Bhaskar) | 2026-11-07 (SOP and design docs only); folder state unverified |
| Salesforce access and refresh tokens | Encrypted access token and encrypted refresh token, org id, user id, instance URL, scope, connection status, last sync time and counts. Table `salesforce_connections`. | Plaintext tokens. Opportunity rows (the connector queries on demand and never persists them). | Neon Postgres, table `salesforce_connections`, one row per tenant (`customer_ref`). Neon project and region: unverified. | Until the customer disconnects or the pilot ends. Revoke on request. | Founder. Use Disconnect Salesforce, then verify the connection row and its cascading mapping row are gone; revoke at the Salesforce side too (runbook, Rotation and offboarding). | 2026-11-07 (neon/schema.sql, runbook) |
| SALESFORCE_TOKEN_ENCRYPTION_KEY | The secret that encrypts and decrypts the stored Salesforce tokens. Value is not recorded here. | Never in the repo, the vault, or this register. | Vercel environment variables and Render environment variables, per the runbook and design doc. Which environments and projects hold it today, and any other copy: unverified. | Until rotated. Rotation needs a written migration plan; changing it without re-encrypting stored tokens breaks every connection. | Founder owns rotation. Rotate on any suspected exposure (incident-response section 3 must list it; it is currently absent there, tracked under PK-21). | 2026-11-07 (docs only); live environments unverified |
| Decision log | Append-only record of copilot decisions and discount-exception requests: tenant ref, kind, deal id, payload (deterministic evidence), decision, justification, requested-by, timestamp. Table `decision_log`. | Raw Opportunity rows are not meant to be stored here. Payload contents are not enforced by schema: unverified that no account names or row values appear in payload. | Neon Postgres, table `decision_log`. Fallback to process memory when the database is unavailable has been reported in earlier reviews: current behavior unverified. | No retention period is defined today; the table is unbounded (finding from the 2026-09-27 review). Retain only under the contracted period. Delete on tenant request. | Founder. Deletion on tenant request is a manual delete scoped by `customer_ref`. | 2026-11-07 (neon/schema.sql) |
| Confirmed mapping headers | Column names the customer confirmed for field mapping, the policy threshold percent, and default value metric. Table `salesforce_mappings` (jsonb `mapping`). | Column values or any row data. Headers only. | Neon Postgres, table `salesforce_mappings`, cascades from `salesforce_connections`. Any non-Salesforce (CSV) mapping store: unverified. | Until disconnect (deleted with the connection row via cascade). | Founder | 2026-11-07 (neon/schema.sql) |
| Per-tenant derived snapshot | Aggregates only: win rate by discount band with n per band, segment, business-unit and product-line reference discounts, the tenant policy (floor, bands), and an `evidence_version` stamp. | Deal rows, account or customer names, named comparable deals, contact data, any row-level value. A test must assert this (PK-38). | Neon Postgres when built; table and location not yet decided. | Until deletion on request; period to be set when built. Counsel review of the NDA addendum sentence is tracked under PK-22. | Founder; deletable on tenant request | Status: approved D1(a) on 2026-11-07, not yet built. Nothing exists to verify. |

Classes not yet in the system, so no rows: billing API keys or OAuth tokens (Stripe,
Chargebee), usage event streams. Before any is held, add a row here first, with
revoke-on-request within 24 hours for credentials.

## Part B. Per-customer register

One row per customer. A row is added the same day anything is received, and updated the same
day anything is deleted. Never record customer contact names or any data values here.

| Customer | What we hold | Where | Since | Status (held / deleted+certified) |
|---|---|---|---|---|
| (none today: zero customers, nothing held) | | | | |

Format of a future row, for reference only: customer slug, file names and row counts plus
derived artifacts, the exact folder or table, the received date, and the status. Include
any Part A class that holds that customer's data (for example a Salesforce connection row or
a snapshot) as part of "What we hold".
