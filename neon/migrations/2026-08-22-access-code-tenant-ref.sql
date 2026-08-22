-- Opaque tenant key for access codes (2026-08-22).
--
-- WHY
-- web/src/lib/gate.ts customerRef() returned the verified access code itself as
-- the tenant key. That single value was doing four jobs at once:
--   1. the credential a customer signs in with (and that we email them)
--   2. the primary key in crm_connections.customer_ref
--   3. the partition key in decision_log.customer_ref
--   4. the X-Pricekeel-Customer header sent to the API tier
--
-- Three consequences:
--   - Rotating or expiring a code orphaned that customer's CRM tokens and field
--     mapping, and the runbook prescribes a 30-day expiry.
--   - A shared bearer secret sat in plaintext as a database key in two tables.
--   - Offboarding broke in the order the runbook prescribes: revoke the code,
--     then disconnect. After the revoke, isValidAccessCode fails, customerRef()
--     falls back to 'default', and disconnect targets the wrong tenant. The
--     customer's encrypted refresh token stayed in our database and stayed live
--     at the CRM, with no in-product way to revoke it.
--
-- WHAT
-- access_codes gains tenant_ref: an opaque, stable identifier that survives code
-- rotation and never travels as a credential. customerRef() returns it instead
-- of the code.
--
-- BACKFILL POLICY (this is the careful part)
--   - Codes that have been USED (used_at is not null) may already own rows in
--     crm_connections and decision_log keyed by the code. Those keep
--     tenant_ref = code so no existing data is orphaned. They gain rotation
--     safety from here on: the code can now change without moving the tenant.
--   - Codes that have NEVER been used own no data by definition, so they get a
--     fresh opaque id immediately and get the full benefit.
--
-- Idempotent and re-runnable. Run inside a single transaction.

begin;

-- 1. Add the column with no default, so existing rows are not assigned random
--    values before the backfill policy below can run.
alter table access_codes add column if not exists tenant_ref text;

-- 2. Backfill. Used codes keep their existing key; unused codes get an opaque
--    one. gen_random_uuid() is built in on PostgreSQL 13+, so no pgcrypto.
update access_codes
   set tenant_ref = code
 where tenant_ref is null
   and used_at is not null;

update access_codes
   set tenant_ref = replace(gen_random_uuid()::text, '-', '')
 where tenant_ref is null;

-- 3. New rows get an opaque id automatically, so the runbook's plain
--    `insert into access_codes (code, issued_to, expires_at)` keeps working and
--    silently does the right thing.
alter table access_codes
  alter column tenant_ref set default replace(gen_random_uuid()::text, '-', '');

alter table access_codes
  alter column tenant_ref set not null;

-- 4. Two tenants must never share a key.
create unique index if not exists access_codes_tenant_ref_key
  on access_codes (tenant_ref);

commit;
