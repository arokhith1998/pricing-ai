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
--   2. any Salesforce source_connections row has no salesforce_connections row
--      with the same customer_ref (created after cutover, for example by PK-42):
--      the legacy table cannot hold it, so its tokens would be lost. Likewise
--      any source_connection_config row with no salesforce_mappings match.
--   3. any source_connection_config row carries a non-default stage_map or
--      list_price_set: the legacy salesforce_mappings table has no such columns,
--      so a person's confirmed choices would be destroyed. Export them, or roll
--      forward instead.
--   4. any access_codes row has a tenant_ref different from its code AND that
--      tenant_ref appears as customer_ref in ANY public base table that has a
--      customer_ref column (found from information_schema.columns, so a table
--      added later is covered): data keyed by the opaque ref would be stranded,
--      and decision_log is append-only. A drifted tenant_ref that keys no data
--      (a routinely issued, unused code) does not block the rollback. Roll
--      forward instead.
-- A down that cannot restore data refuses. It never only warns.
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

set local lock_timeout = '5s';

-- access_codes is ALTERed below, so take the strongest lock first.
lock table access_codes in access exclusive mode;
lock table decision_log, salesforce_connections, salesforce_mappings
  in share mode;

select set_config('pk41.decision_log_before', (select count(*) from decision_log)::text, true);
select set_config('pk41.access_codes_before', (select count(*) from access_codes)::text, true);
select set_config('pk41.sf_conn_before', (select count(*) from salesforce_connections)::text, true);
select set_config('pk41.sf_map_before', (select count(*) from salesforce_mappings)::text, true);

do $$
declare
  n_other   bigint := 0;
  n_orphan  bigint := 0;
  n_cfg     bigint := 0;
  n_drifted bigint := 0;
  n_tbl     bigint := 0;
  tbl       text;
  where_used text := '';
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

  if to_regclass('public.source_connections') is not null then
    execute 'select count(*) from source_connections s where s.source_system = ''salesforce'' '
         || 'and not exists (select 1 from salesforce_connections l where l.customer_ref = s.customer_ref)'
      into n_orphan;
    if n_orphan > 0 then
      raise exception using
        errcode = 'raise_exception',
        message = format(
          'DOWN MIGRATION REFUSED: %s salesforce source_connections row(s) have no legacy salesforce_connections match.',
          n_orphan),
        detail  = 'The legacy table cannot hold them, so their tokens and settings would be destroyed.',
        hint    = 'Disconnect those tenants (they reconnect after rollback), or roll forward instead.';
    end if;
  end if;

  if to_regclass('public.source_connection_config') is not null then
    execute 'select count(*) from source_connection_config c where not exists '
         || '(select 1 from salesforce_mappings m where m.customer_ref = c.customer_ref '
         || 'and c.source_system = ''salesforce'')'
      into n_orphan;
    if n_orphan > 0 then
      raise exception using
        errcode = 'raise_exception',
        message = format(
          'DOWN MIGRATION REFUSED: %s source_connection_config row(s) have no legacy salesforce_mappings match.',
          n_orphan),
        detail  = 'Mapping, threshold and value metric live nowhere else once this table is dropped.',
        hint    = 'Export or re-enter that config after rollback, or roll forward instead.';
    end if;
    execute 'select count(*) from source_connection_config '
         || 'where stage_map <> ''{}''::jsonb or list_price_set <> ''[]''::jsonb'
      into n_cfg;
    if n_cfg > 0 then
      raise exception using
        errcode = 'raise_exception',
        message = format(
          'DOWN MIGRATION REFUSED: %s source_connection_config row(s) carry a confirmed stage_map or list_price_set.',
          n_cfg),
        detail  = 'salesforce_mappings has no such columns, so dropping source_connection_config would destroy choices a person confirmed.',
        hint    = 'Export those values and clear them (set stage_map to {} and list_price_set to []) once preserved, or roll forward instead.';
    end if;
  end if;

  if exists (select 1 from information_schema.columns
              where table_schema = 'public' and table_name = 'access_codes'
                and column_name = 'tenant_ref') then
    for tbl in
      select c.table_name
        from information_schema.columns c
        join information_schema.tables t
          on t.table_schema = c.table_schema and t.table_name = c.table_name
       where c.table_schema = 'public' and c.column_name = 'customer_ref'
         and t.table_type = 'BASE TABLE'
       order by c.table_name
    loop
      begin
        execute format(
          'select count(*) from access_codes a where a.tenant_ref is distinct from a.code '
          || 'and exists (select 1 from %I t where t.customer_ref = a.tenant_ref)', tbl)
          into n_tbl;
        n_drifted := n_drifted + n_tbl;
        if n_tbl > 0 then
          where_used := where_used || format(' %s(%s)', tbl, n_tbl);
        end if;
      end;
    end loop;
    if n_drifted > 0 then
      raise exception using
        errcode = 'raise_exception',
        message = format(
          'DOWN MIGRATION REFUSED: %s drifted tenant_ref value(s) key data in:%s.',
          n_drifted, where_used),
        detail  = 'Dropping tenant_ref would strand rows keyed by the opaque ref rather than by the access code.',
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
