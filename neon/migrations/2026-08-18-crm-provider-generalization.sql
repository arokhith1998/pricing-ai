-- CRM provider generalization (2026-08-18).
--
-- Slice 1 of docs/design/hubspot-crm-integration.md. Pure refactor: no new
-- capability, no HubSpot code. Generalizes the Salesforce-only connection and
-- mapping tables so a second CRM can land without a parallel table pair.
--
-- Changes:
--   salesforce_connections -> crm_connections, primary key (customer_ref, provider)
--   salesforce_mappings    -> crm_mappings,    primary key (customer_ref, provider)
--   provider column added, defaulting to 'salesforce' so existing rows keep working.
--
-- The generic slots absorb both providers without new columns:
--   org_id       Salesforce org ID          | HubSpot portal ID
--   instance_url Salesforce instance URL    | HubSpot API base
--
-- Idempotent and re-runnable. Constraint names are resolved dynamically because
-- ALTER TABLE ... RENAME TO does not rename a table's constraints or indexes,
-- so a renamed table still carries salesforce_*_pkey until we repoint it.

-- 1. Rename the tables if they still carry the Salesforce-only names.
do $$
begin
  if to_regclass('public.salesforce_connections') is not null
     and to_regclass('public.crm_connections') is null then
    alter table salesforce_connections rename to crm_connections;
  end if;
  if to_regclass('public.salesforce_mappings') is not null
     and to_regclass('public.crm_mappings') is null then
    alter table salesforce_mappings rename to crm_mappings;
  end if;
end $$;

-- 2. Create from scratch when this is a fresh database with no Salesforce past.
create table if not exists crm_connections (
  customer_ref            text not null,
  provider                text not null default 'salesforce',
  org_id                  text not null,
  user_id                 text not null default '',
  instance_url            text not null,
  access_token_encrypted  text not null,
  refresh_token_encrypted text not null,
  token_type              text not null default 'Bearer',
  scope                   text not null default '',
  issued_at               text not null default '',
  status                  text not null default 'connected'
    check (status in ('connected','reauth_required','error')),
  last_error              text not null default '',
  last_sync_at            timestamptz,
  last_sync_closed        integer not null default 0,
  last_sync_open          integer not null default 0,
  connected_at            timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  primary key (customer_ref, provider)
);

create table if not exists crm_mappings (
  customer_ref          text not null,
  provider              text not null default 'salesforce',
  mapping               jsonb not null default '{}'::jsonb,
  policy_threshold_pct  double precision not null default 15.0,
  default_value_metric  text not null default 'hybrid',
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  primary key (customer_ref, provider)
);

-- 3. Add the provider column to tables that predate it.
alter table crm_connections
  add column if not exists provider text not null default 'salesforce';
alter table crm_mappings
  add column if not exists provider text not null default 'salesforce';

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'crm_connections_provider_check'
  ) then
    alter table crm_connections
      add constraint crm_connections_provider_check
      check (provider in ('salesforce','hubspot'));
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'crm_mappings_provider_check'
  ) then
    alter table crm_mappings
      add constraint crm_mappings_provider_check
      check (provider in ('salesforce','hubspot'));
  end if;
end $$;

-- 4. Drop the mappings foreign key before touching either primary key.
--    Resolved by lookup: after a table rename it is still named
--    salesforce_mappings_customer_ref_fkey.
do $$
declare
  fk_name text;
begin
  select c.conname into fk_name
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
   where t.relname = 'crm_mappings' and c.contype = 'f'
   limit 1;
  if fk_name is not null then
    execute format('alter table crm_mappings drop constraint %I', fk_name);
  end if;
end $$;

-- 5. Repoint both primary keys to (customer_ref, provider) when they are still
--    single-column. Skipped entirely on a freshly created table.
do $$
declare
  pk_name text;
begin
  select c.conname into pk_name
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
   where t.relname = 'crm_connections'
     and c.contype = 'p'
     and array_length(c.conkey, 1) = 1;
  if pk_name is not null then
    execute format('alter table crm_connections drop constraint %I', pk_name);
    alter table crm_connections add primary key (customer_ref, provider);
  end if;

  select c.conname into pk_name
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
   where t.relname = 'crm_mappings'
     and c.contype = 'p'
     and array_length(c.conkey, 1) = 1;
  if pk_name is not null then
    execute format('alter table crm_mappings drop constraint %I', pk_name);
    alter table crm_mappings add primary key (customer_ref, provider);
  end if;
end $$;

-- 6. Restore the cascade on the composite key.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'crm_mappings_connection_fkey'
  ) then
    alter table crm_mappings
      add constraint crm_mappings_connection_fkey
      foreign key (customer_ref, provider)
      references crm_connections (customer_ref, provider)
      on delete cascade;
  end if;
end $$;

-- 7. Index rename is best-effort; recreate under the new name either way.
drop index if exists salesforce_connections_status_updated_idx;
create index if not exists crm_connections_status_updated_idx
  on crm_connections (status, updated_at desc);
