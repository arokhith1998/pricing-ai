-- DOWN migration for 2026-08-18-crm-provider-generalization.sql
--
-- Reverses the provider generalization:
--   crm_connections -> salesforce_connections, primary key (customer_ref)
--   crm_mappings    -> salesforce_mappings,    primary key (customer_ref)
--   provider column and its check constraint dropped
--
-- WHY THIS EXISTS
-- The up-migration renames tables that deployed code queries by name. Deployed
-- `main` reads salesforce_connections / salesforce_mappings; the CRM branch reads
-- crm_connections / crm_mappings. Applying the up-migration while `main` is still
-- serving breaks every live Salesforce connection read, write, and disconnect.
-- This file is the way back. Correct deploy order is documented in
-- docs/ops/salesforce-integration-runbook.md.
--
-- SAFETY GUARD (read before running)
-- This migration collapses the composite key (customer_ref, provider) back to a
-- single-column key on customer_ref. If ANY customer holds connections for more
-- than one provider, that collapse would destroy rows. So step 0 aborts the whole
-- transaction if a non-Salesforce row exists. There is no way to reverse the
-- generalization without losing HubSpot data, so we refuse rather than guess.
--
-- If the guard fires, your options are: (a) roll forward instead, (b) export the
-- HubSpot rows, delete them, re-run this, and re-onboard those portals later.
--
-- Idempotent and re-runnable. Run inside a single transaction.

begin;

-- 0. Refuse if any non-Salesforce provider rows exist. Aborts the transaction.
do $$
declare
  n_conn int := 0;
  n_map  int := 0;
begin
  if to_regclass('public.crm_connections') is not null then
    execute 'select count(*) from crm_connections where provider is distinct from ''salesforce'''
      into n_conn;
  end if;
  if to_regclass('public.crm_mappings') is not null then
    execute 'select count(*) from crm_mappings where provider is distinct from ''salesforce'''
      into n_map;
  end if;
  if n_conn > 0 or n_map > 0 then
    raise exception using
      errcode = 'raise_exception',
      message = format(
        'DOWN MIGRATION REFUSED: %s non-salesforce connection row(s) and %s mapping row(s) exist.',
        n_conn, n_map),
      detail  = 'Collapsing (customer_ref, provider) to (customer_ref) would destroy these rows.',
      hint    = 'Roll forward instead, or export and delete the non-salesforce rows first.';
  end if;
end $$;

-- 1. Drop the composite foreign key before touching either primary key.
do $$
declare
  fk_name text;
begin
  if to_regclass('public.crm_mappings') is null then
    return;
  end if;
  select c.conname into fk_name
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
   where t.relname = 'crm_mappings' and c.contype = 'f'
   limit 1;
  if fk_name is not null then
    execute format('alter table crm_mappings drop constraint %I', fk_name);
  end if;
end $$;

-- 2. Drop both composite primary keys. We do NOT re-add them yet: a primary key
--    added while the table is still named crm_* would be auto-named
--    crm_connections_pkey and survive the rename, leaving exactly the constraint
--    drift the up-migration warns about. Rename first, add the key after.
do $$
declare
  pk_name text;
  t       text;
begin
  foreach t in array array['crm_connections','crm_mappings'] loop
    if to_regclass('public.'||t) is not null then
      select c.conname into pk_name
        from pg_constraint c
        join pg_class k on k.oid = c.conrelid
       where k.relname = t and c.contype = 'p' and array_length(c.conkey, 1) = 2;
      if pk_name is not null then
        execute format('alter table %I drop constraint %I', t, pk_name);
      end if;
      pk_name := null;
    end if;
  end loop;
end $$;

-- 3. Drop the provider check constraints, then the provider columns.
alter table if exists crm_connections drop constraint if exists crm_connections_provider_check;
alter table if exists crm_mappings    drop constraint if exists crm_mappings_provider_check;
alter table if exists crm_connections drop column if exists provider;
alter table if exists crm_mappings    drop column if exists provider;

-- 4. Rename the tables back BEFORE rebuilding keys, so Postgres auto-names the
--    new constraints salesforce_*_pkey rather than crm_*_pkey.
do $$
begin
  if to_regclass('public.crm_connections') is not null
     and to_regclass('public.salesforce_connections') is null then
    alter table crm_connections rename to salesforce_connections;
  end if;
  if to_regclass('public.crm_mappings') is not null
     and to_regclass('public.salesforce_mappings') is null then
    alter table crm_mappings rename to salesforce_mappings;
  end if;
end $$;

-- 5. Rebuild the single-column primary keys under the restored table names.
do $$
declare
  t text;
begin
  foreach t in array array['salesforce_connections','salesforce_mappings'] loop
    if to_regclass('public.'||t) is not null
       and not exists (
         select 1 from pg_constraint c
           join pg_class k on k.oid = c.conrelid
          where k.relname = t and c.contype = 'p'
       ) then
      execute format('alter table %I add primary key (customer_ref)', t);
    end if;
  end loop;
end $$;

-- 5b. Restore the original single-column cascade foreign key.
do $$
begin
  if to_regclass('public.salesforce_mappings') is null then
    return;
  end if;
  if not exists (
    select 1 from pg_constraint c
      join pg_class t on t.oid = c.conrelid
     where t.relname = 'salesforce_mappings' and c.contype = 'f'
  ) then
    alter table salesforce_mappings
      add constraint salesforce_mappings_customer_ref_fkey
      foreign key (customer_ref)
      references salesforce_connections (customer_ref)
      on delete cascade;
  end if;
end $$;

-- 6. Restore the index under its original name.
drop index if exists crm_connections_status_updated_idx;
create index if not exists salesforce_connections_status_updated_idx
  on salesforce_connections (status, updated_at desc);

commit;
