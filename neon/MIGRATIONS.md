# Neon migration runbook

Companion to `neon/CUTOVER.md` (which covers the one-time Supabase -> Neon
move). This file covers the ongoing discipline for every migration that
lands in `neon/migrations/` after that.

## The rule

Every migration is additive, transactional, and reversible:

- Ship `<date>-<slug>.sql` together with `<date>-<slug>.down.sql`. A migration
  with no down is not done.
- Wrap both files in `begin; ... commit;`.
- Guard destructive drops: if a down-migration would delete rows (drop a
  column, drop a table, collapse a key), it must check for data first and
  `raise exception` to abort the transaction rather than delete it. See the
  DO-block pattern in `2026-08-01-salesforce-crm-workflow.down.sql` and
  `2026-09-26-tenant-scoped-indexes.down.sql` (no guard needed there, index
  drops never destroy data).
- Use `if not exists` / `if exists` everywhere so the file is safe to apply
  twice.
- State deploy order explicitly in the file's header comment: whether it must
  run before, after, or has no dependency on, the code deploy. A rename or
  drop that breaks the running app between the two steps is a production
  incident, not a migration.

## Verifying a migration (up, then down, then up again)

Against a scratch database (never a real one for this step):

```bash
createdb pricekeel_scratch
psql pricekeel_scratch -f neon/schema.sql            # baseline schema
psql pricekeel_scratch -f neon/migrations/<file>.sql       # up
# ... inspect: \d <table>, \di <index>, spot-check a row ...
psql pricekeel_scratch -f neon/migrations/<file>.down.sql  # down
# ... confirm the table/column/index is gone ...
psql pricekeel_scratch -f neon/migrations/<file>.sql       # up again (rerunnable)
dropdb pricekeel_scratch
```

See "Verification run, 2026-09-26" below for the actual output from this
exercise against `2026-08-01-salesforce-crm-workflow.sql` and
`2026-09-26-tenant-scoped-indexes.sql`.

## Why leads_lower_email_idx is a plain index, not a unique one

`2026-09-26-tenant-scoped-indexes.sql` originally added `leads_lower_email_key`
as a UNIQUE index on `lower(email)`. Code review the same day caught two
problems before this shipped to a real database: `email` was never unique on
`leads`, and lead capture (`web/src/lib/store.ts`'s `saveLead`) does a plain
`INSERT` with no `ON CONFLICT` clause and no pre-check. A unique index would
(a) fail the whole migration outright the first time it hit a prod database
with two existing rows sharing a case-insensitive email (`CREATE UNIQUE INDEX`
rolls back the entire transaction), and (b) once past that, would 500 every
returning visitor who resubmits the lead-gate form (an ordinary retry or
double-click), since nothing in the write path catches the constraint
violation. The migration now creates `leads_lower_email_idx` as a PLAIN index:
same case-insensitive lookup speed-up, no write-time failure mode the app was
not built to handle. See the verification transcript below for the unique-
index failure mode this replaced, kept as a documented case study.

## Test coverage

`neon/test_migrations.py` asserts, structurally, that every `<slug>.sql` in
`neon/migrations/` has a matching `<slug>.down.sql` and vice versa, and that
every down file wraps its work in `begin;`/`commit;`. It does not run SQL
against a database (no CI database exists yet), it is a cheap guardrail
against the exact gap this runbook exists to close (main shipped one
migration with no down for seven weeks). The up/down/up verification above is
still a manual step before merging a migration.

## Verification run, 2026-09-26

Real output, against a local scratch Postgres 16 database
(`pricekeel_migration_scratch`, via the `psql` on this machine, run as the
`postgres` role):

```
$ psql -U postgres -c "create database pricekeel_migration_scratch;"
CREATE DATABASE

$ psql -U postgres -d pricekeel_migration_scratch -f neon/schema.sql
CREATE TABLE
CREATE INDEX
CREATE TABLE
CREATE INDEX
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE TABLE
CREATE TABLE
CREATE INDEX
CREATE TABLE
CREATE INDEX

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-08-01-salesforce-crm-workflow.sql
BEGIN
NOTICE:  relation "salesforce_connections" already exists, skipping
CREATE TABLE
NOTICE:  relation "salesforce_mappings" already exists, skipping
CREATE TABLE
NOTICE:  relation "salesforce_connections_status_updated_idx" already exists, skipping
CREATE INDEX
NOTICE:  relation "competitor_context_sources" already exists, skipping
CREATE TABLE
NOTICE:  relation "competitor_context_customer_verified_idx" already exists, skipping
CREATE INDEX
COMMIT
-- schema.sql already created these tables at baseline load, so this run
-- proves idempotency (IF NOT EXISTS), not first creation.

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-08-01-salesforce-crm-workflow.down.sql
BEGIN
DO
DROP TABLE
DROP TABLE
DROP TABLE
COMMIT

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-08-01-salesforce-crm-workflow.sql
BEGIN
CREATE TABLE
CREATE TABLE
CREATE INDEX
CREATE TABLE
CREATE INDEX
COMMIT
-- confirms rerunnable: up after a real down (tables actually gone this time)
-- recreates cleanly.
```

Guard check: inserted one row into `salesforce_connections`, then ran the
down-migration and confirmed it refused and rolled back everything, table and
row both intact:

```
$ psql -U postgres -d pricekeel_migration_scratch -c "insert into salesforce_connections (customer_ref, org_id, instance_url, access_token_encrypted, refresh_token_encrypted) values ('t1','org1','https://x','enc','enc');"
INSERT 0 1

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-08-01-salesforce-crm-workflow.down.sql
BEGIN
ERROR:  DOWN MIGRATION REFUSED: 1 connection row(s), 0 mapping row(s), 0 competitor context row(s) exist.
DETAIL:  Dropping these tables would destroy live Salesforce OAuth tokens, field mappings, and competitor evidence.
HINT:  Disconnect every tenant and export/delete the rows by hand first, or roll forward instead.
CONTEXT:  PL/pgSQL function inline_code_block line 18 at RAISE
ROLLBACK

$ psql -U postgres -d pricekeel_migration_scratch -c "select count(*) from salesforce_connections;"
 count
-------
     1
(1 row)
-- table and row survived; the guard aborted the whole transaction
```

Tenant-scoped indexes, up / down / up again (transcript below predates the
plain-vs-unique fix and still shows the original index name
`leads_lower_email_key`; the migration now creates `leads_lower_email_idx`
instead, with the same idempotent up/down/up behavior):

```
$ psql -U postgres -d pricekeel_migration_scratch -c "delete from salesforce_connections where customer_ref='t1';"
DELETE 1

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-09-26-tenant-scoped-indexes.sql
BEGIN
NOTICE:  relation "decision_log_tenant_kind_created_idx" already exists, skipping
CREATE INDEX
NOTICE:  relation "access_codes_lead_id_idx" already exists, skipping
CREATE INDEX
NOTICE:  relation "leads_lower_email_key" already exists, skipping
CREATE INDEX
COMMIT
-- again, schema.sql already created these; this proves idempotency

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-09-26-tenant-scoped-indexes.down.sql
BEGIN
DROP INDEX
DROP INDEX
DROP INDEX
COMMIT

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-09-26-tenant-scoped-indexes.down.sql
BEGIN
NOTICE:  index "leads_lower_email_key" does not exist, skipping
DROP INDEX
NOTICE:  index "access_codes_lead_id_idx" does not exist, skipping
DROP INDEX
NOTICE:  index "decision_log_tenant_kind_created_idx" does not exist, skipping
DROP INDEX
COMMIT
-- down is itself rerunnable

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-09-26-tenant-scoped-indexes.sql
BEGIN
CREATE INDEX
CREATE INDEX
CREATE INDEX
COMMIT
```

Unique-email failure mode this replaced (kept as a case study, not current
behavior): two leads sharing a case-insensitive email, confirmed the whole
transaction failed atomically (no partial index creation) when the index was
still UNIQUE. This is exactly why the migration was changed to a plain index
before shipping to any real database with lead data in it:

```
$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-09-26-tenant-scoped-indexes.down.sql
BEGIN
DROP INDEX
DROP INDEX
DROP INDEX
COMMIT

$ psql -U postgres -d pricekeel_migration_scratch -c "insert into leads (name, company, email, role_title, role_function) values ('A','Acme','Test@Acme.com','CEO','exec'), ('B','Acme2','test@acme.com','CFO','exec');"
INSERT 0 2

$ psql -U postgres -d pricekeel_migration_scratch -f neon/migrations/2026-09-26-tenant-scoped-indexes.sql
BEGIN
CREATE INDEX
CREATE INDEX
ERROR:  could not create unique index "leads_lower_email_key"
DETAIL:  Key (lower(email))=(test@acme.com) is duplicated.
ROLLBACK

$ psql -U postgres -d pricekeel_migration_scratch -c "\di decision_log_tenant_kind_created_idx"
Did not find any relation named "decision_log_tenant_kind_created_idx".
-- all-or-nothing confirmed: the two indexes created before the failing
-- statement did NOT survive; begin/commit rolled back the entire migration

$ psql -U postgres -d pricekeel_migration_scratch -c "delete from leads where lower(email) = 'test@acme.com';"
DELETE 2

$ psql -U postgres -c "drop database pricekeel_migration_scratch;"
DROP DATABASE
```

With today's plain (non-unique) `leads_lower_email_idx`, the two duplicate
rows inserted above would not have blocked the migration at all -- which is
the actual fix: a returning visitor resubmitting the lead-gate form was never
supposed to be able to break ingestion.

## Deploy order per migration on main / in flight

| Migration | Deploy order |
|---|---|
| `2026-08-01-salesforce-crm-workflow.sql` | No dependency: creates new tables/indexes only, safe before/during/after deploy. |
| `2026-08-01-salesforce-crm-workflow.down.sql` | AFTER the code that reads/writes these tables is rolled back. Running it first breaks the running app. |
| `2026-09-26-tenant-scoped-indexes.sql` | No dependency: additive indexes only, safe before/during/after deploy. |
| `2026-09-26-tenant-scoped-indexes.down.sql` | No dependency: dropping an index never breaks a query, only slows it. |
| `2026-11-09-source-mappings.sql` (PK-24) | BEFORE the code that reads or writes `source_mappings` (PK-28). Additive: a new table and an index on `decision_log`; the running app references neither. |
| `2026-11-09-source-mappings.down.sql` (PK-24) | AFTER rolling back the code that uses `source_mappings`. The index drop is safe at any time. |
| `2026-11-10-source-connections.sql` (PK-41) | BEFORE the code that reads or writes `source_connections` (PK-42) or `tenant_ref` (PK-43). Additive; the running app reads only the legacy tables. After the PK-42 cutover never rerun it (the backfill would resurrect disconnected rows). |
| `2026-11-10-source-connections.down.sql` (PK-41) | AFTER rolling back PK-42 and PK-43. Refuses when it would destroy credentials, confirmed config or keyed data it cannot restore. |
| `2026-11-11-leads-lead-magnet.sql` (PK-108) | BEFORE the code that writes `leads.lead_magnet` (PK-109). Additive: one column with a default and one check; the running app inserts with an explicit column list, so old code keeps working. Production application needs founder authorisation. |
| `2026-11-11-leads-lead-magnet.down.sql` (PK-108) | AFTER rolling back PK-109. Refuses when any lead has a non-empty `lead_magnet`, because the tag is stored nowhere else. |
