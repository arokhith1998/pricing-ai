-- DOWN migration for 2026-11-11-leads-lead-magnet.sql (PK-108).
--
-- Drops exactly what the up created: the leads_lead_magnet_format_chk
-- constraint and the leads.lead_magnet column. Nothing else is touched; the
-- guard asserts the leads row count is unchanged.
--
-- REFUSES (aborts the whole transaction, nothing dropped) when any lead has a
-- non-empty lead_magnet: that tag exists nowhere else, and dropping the column
-- would erase which leads came from the calculator. Export or re-tag those
-- rows first (for example copy them into utm_campaign), or roll forward
-- instead. A down that cannot restore data refuses. It never only warns.
--
-- DEPLOY ORDER: run AFTER rolling back the code that writes lead_magnet
-- (PK-109). Running it first makes every calculator lead insert fail on a
-- missing column.
--
-- Idempotent and re-runnable (a second run is a no-op).

begin;

set local lock_timeout = '5s';

lock table leads in access exclusive mode;

select set_config('pk108.leads_before', (select count(*) from leads)::text, true);

do $$
declare
  n_tagged bigint := 0;
begin
  if exists (select 1 from information_schema.columns
              where table_schema = 'public' and table_name = 'leads'
                and column_name = 'lead_magnet') then
    execute 'select count(*) from leads where lead_magnet <> ''''' into n_tagged;
    if n_tagged > 0 then
      raise exception using
        errcode = 'raise_exception',
        message = format(
          'DOWN MIGRATION REFUSED: %s lead(s) carry a non-empty lead_magnet.', n_tagged),
        detail  = 'Dropping leads.lead_magnet would erase which leads came from a lead magnet; the tag is stored nowhere else.',
        hint    = 'Export or re-tag those rows first (for example into utm_campaign), or roll forward instead.';
    end if;
  end if;
end $$;

alter table leads drop constraint if exists leads_lead_magnet_format_chk;
alter table leads drop column if exists lead_magnet;

do $$
declare
  n bigint;
begin
  select count(*) into n from leads;
  if n <> current_setting('pk108.leads_before')::bigint then
    raise exception 'PK-108 guard: leads row count changed (% -> %)',
      current_setting('pk108.leads_before'), n;
  end if;
end $$;

commit;
