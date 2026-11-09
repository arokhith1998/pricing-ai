-- DOWN migration for 2026-11-source-mappings.sql (PK-24).
--
-- Drops exactly what the up created: the decision_log source index and the
-- source_mappings table. The table is a derived cache of customer-confirmed
-- header mappings (re-confirmable, no row data), but dropping it does delete
-- those saved mappings: run only with explicit authorization against a real
-- database. decision_log rows are never touched; the guard asserts that.
--
-- DEPLOY ORDER: run AFTER rolling back the code that uses source_mappings
-- (PK-28), otherwise that code errors on a missing table. The index drop is
-- safe at any time.
--
-- Idempotent and re-runnable.

begin;

select set_config('pk24.decision_log_before',
                  (select count(*) from decision_log)::text, true);

drop index if exists decision_log_tenant_source_idx;
drop table if exists source_mappings;

do $$
declare
  before_n bigint := current_setting('pk24.decision_log_before')::bigint;
  after_n  bigint;
begin
  select count(*) into after_n from decision_log;
  if after_n <> before_n then
    raise exception 'PK-24 guard: decision_log row count changed (% -> %)', before_n, after_n;
  end if;
end $$;

commit;
