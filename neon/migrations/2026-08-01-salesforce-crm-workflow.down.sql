-- DOWN migration for 2026-08-01-salesforce-crm-workflow.sql
--
-- Reverses the Salesforce CRM workflow tables: drops
-- competitor_context_sources, salesforce_mappings, and salesforce_connections,
-- and the one index on the up-migration that is not dropped implicitly by the
-- table drop (postgres drops a table's own indexes automatically; the guard
-- below is what actually protects data, not the index drops).
--
-- WHY THIS EXISTS
-- This is the reference-fix identified in the 2026-09-26 data-layer review:
-- the only migration on main had no down file at all. The pattern below
-- follows the guarded, idempotent style already proven on
-- origin/fix/tenant-key-opaque (2026-08-22-access-code-tenant-ref.down.sql)
-- and origin/feat/crm-provider-schema
-- (2026-08-18-crm-provider-generalization.down.sql): refuse and abort the
-- transaction rather than destroy data, and document deploy order.
--
-- SAFETY GUARD (read before running)
-- These three tables hold live Salesforce OAuth tokens, per-tenant field
-- mappings, and captured competitor evidence. Dropping them always destroys
-- data once any tenant has connected Salesforce or any competitor context has
-- been captured. Step 0 refuses and aborts the whole transaction if ANY row
-- exists in any of the three tables. There is no way to reverse this
-- migration without losing that data, so we refuse rather than guess.
--
-- If the guard fires: disconnect every tenant (which should revoke their
-- Salesforce tokens at the CRM side too) and export/delete the rows by hand
-- first, or roll forward instead.
--
-- DEPLOY ORDER
-- Run this AFTER the application code that reads/writes salesforce_connections,
-- salesforce_mappings, and competitor_context_sources has been rolled back or
-- undeployed. Running the down-migration first, while the old code is still
-- serving, breaks every live Salesforce connection, sync, and competitor-
-- context read with a "relation does not exist" error — a production
-- incident, not a migration. The up-migration has no such ordering constraint
-- (it only creates tables/indexes, so it is safe before, during, or after the
-- code deploy); this down-migration is the one that must come after.
--
-- Idempotent and re-runnable. Run inside a single transaction.

begin;

-- 0. Refuse if any row exists in any of the three tables. Aborts the
--    transaction (raise inside a DO block propagates and rolls back the
--    enclosing BEGIN/COMMIT).
do $$
declare
  n_conn int := 0;
  n_map  int := 0;
  n_ctx  int := 0;
begin
  if to_regclass('public.salesforce_connections') is not null then
    execute 'select count(*) from salesforce_connections' into n_conn;
  end if;
  if to_regclass('public.salesforce_mappings') is not null then
    execute 'select count(*) from salesforce_mappings' into n_map;
  end if;
  if to_regclass('public.competitor_context_sources') is not null then
    execute 'select count(*) from competitor_context_sources' into n_ctx;
  end if;

  if n_conn > 0 or n_map > 0 or n_ctx > 0 then
    raise exception using
      errcode = 'raise_exception',
      message = format(
        'DOWN MIGRATION REFUSED: %s connection row(s), %s mapping row(s), '
        '%s competitor context row(s) exist.',
        n_conn, n_map, n_ctx),
      detail  = 'Dropping these tables would destroy live Salesforce OAuth '
                'tokens, field mappings, and competitor evidence.',
      hint    = 'Disconnect every tenant and export/delete the rows by hand '
                'first, or roll forward instead.';
  end if;
end $$;

-- 1. Drop the dependent table first (its FK references salesforce_connections).
drop table if exists salesforce_mappings;

-- 2. Drop the remaining two tables. Postgres drops each table's own indexes
--    automatically, so no separate DROP INDEX is needed for
--    salesforce_connections_status_updated_idx or
--    competitor_context_customer_verified_idx.
drop table if exists salesforce_connections;
drop table if exists competitor_context_sources;

commit;
