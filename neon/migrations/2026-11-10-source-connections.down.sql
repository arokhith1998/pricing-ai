-- DOWN migration for 2026-11-10-source-connections.sql (PK-41).
--
-- Drops exactly what the up created: source_connection_config, then
-- source_connections (with their indexes and constraints), then
-- access_codes_tenant_ref_key and access_codes.tenant_ref. The legacy
-- salesforce_connections and salesforce_mappings tables and decision_log are
-- never touched; the guard asserts their row counts.
--
-- REFUSES (aborts the whole transaction, nothing dropped) when:
--   1. any source_connections row has a source_system other than 'salesforce':
--      those HubSpot, Stripe or Chargebee credentials exist nowhere else and
--      dropping the table would destroy them. Disconnect those tenants (and
--      have Stripe and Chargebee customers roll their keys) first, or roll
--      forward instead.
--   2. any access_codes row has tenant_ref different from its code: data keyed
--      by the opaque ref in decision_log or the connection tables would be
--      stranded, and decision_log is append-only. Roll forward instead.
-- Salesforce rows in source_connections are backfilled copies of the legacy
-- table; after PK-42 has cut over they hold the newest tokens, so a down after
-- cutover loses refreshes made since: roll back PK-42 first, and expect those
-- tenants to reconnect.
--
-- DEPLOY ORDER: run AFTER rolling back the code that uses source_connections
-- (PK-42) and tenant_ref (PK-43). Running it first breaks that code.
--
-- Idempotent and re-runnable (a second run is a no-op).

begin;

lock table decision_log, access_codes, salesforce_connections, salesforce_mappings
  in share mode;

select set_config('pk41.decision_log_before', (select count(*) from decision_log)::text, true);
select set_config('pk41.access_codes_before', (select count(*) from access_codes)::text, true);
select set_config('pk41.sf_conn_before', (select count(*) from salesforce_connections)::text, true);
select set_config('pk41.sf_map_before', (select count(*) from salesforce_mappings)::text, true);

do $$
declare
  n_other   bigint := 0;
  n_drifted bigint := 0;
begin
  if to_regclass('public.source_connections') is not null then
    execute 'select count(*) from source_connections where source_system <> ''salesforce'''
      into n_other;
    if n_other > 0 then
      raise exception using
        errcode = 'raise_exception',
        message = format(
          'DOWN MIGRATION REFUSED: %s source_connections row(s) have a source_system other than salesforce.',
          n_other),
        detail  = 'Dropping source_connections would destroy HubSpot, Stripe or Chargebee credentials that are stored nowhere else.',
        hint    = 'Disconnect those tenants first (Stripe and Chargebee customers must roll their own keys), or roll forward instead.';
    end if;
  end if;

  if exists (select 1 from information_schema.columns
              where table_schema = 'public' and table_name = 'access_codes'
                and column_name = 'tenant_ref') then
    execute 'select count(*) from access_codes where tenant_ref is distinct from code'
      into n_drifted;
    if n_drifted > 0 then
      raise exception using
        errcode = 'raise_exception',
        message = format(
          'DOWN MIGRATION REFUSED: %s access code(s) have tenant_ref different from code.',
          n_drifted),
        detail  = 'Dropping tenant_ref would strand decision_log and connection rows keyed by the opaque ref.',
        hint    = 'Roll forward instead. Reverting means re-keying those tables by hand, and decision_log is append-only.';
    end if;
  end if;
end $$;

drop table if exists source_connection_config;
drop table if exists source_connections;
drop index if exists access_codes_tenant_ref_key;
alter table access_codes drop column if exists tenant_ref;

do $$
declare
  n bigint;
begin
  select count(*) into n from decision_log;
  if n <> current_setting('pk41.decision_log_before')::bigint then
    raise exception 'PK-41 guard: decision_log row count changed (% -> %)',
      current_setting('pk41.decision_log_before'), n;
  end if;
  select count(*) into n from access_codes;
  if n <> current_setting('pk41.access_codes_before')::bigint then
    raise exception 'PK-41 guard: access_codes row count changed (% -> %)',
      current_setting('pk41.access_codes_before'), n;
  end if;
  select count(*) into n from salesforce_connections;
  if n <> current_setting('pk41.sf_conn_before')::bigint then
    raise exception 'PK-41 guard: salesforce_connections row count changed (% -> %)',
      current_setting('pk41.sf_conn_before'), n;
  end if;
  select count(*) into n from salesforce_mappings;
  if n <> current_setting('pk41.sf_map_before')::bigint then
    raise exception 'PK-41 guard: salesforce_mappings row count changed (% -> %)',
      current_setting('pk41.sf_map_before'), n;
  end if;
end $$;

commit;
