-- DOWN migration for 2026-08-22-access-code-tenant-ref.sql
--
-- Drops access_codes.tenant_ref and its unique index, returning customerRef()
-- to using the raw access code as the tenant key.
--
-- SAFETY GUARD (read before running)
-- Reverting is only safe while every tenant_ref still equals its code. Once a
-- code has been rotated away from its tenant_ref, or an unused code was issued
-- with an opaque ref and has since accumulated rows in crm_connections or
-- decision_log, dropping the column strands that data: the app would go back to
-- keying on the code, which no longer matches the stored customer_ref.
--
-- Step 0 therefore aborts if any row has tenant_ref <> code. If it fires, roll
-- forward instead. Recovering by hand means updating crm_connections.customer_ref
-- and decision_log.customer_ref back to the code for each affected tenant, and
-- decision_log is append-only, so that is not a change to make casually.
--
-- Idempotent and re-runnable. Run inside a single transaction.

begin;

do $$
declare
  n_drifted int := 0;
begin
  if to_regclass('public.access_codes') is null then
    return;
  end if;
  if not exists (
    select 1 from information_schema.columns
     where table_name = 'access_codes' and column_name = 'tenant_ref'
  ) then
    return;  -- already reverted
  end if;

  execute 'select count(*) from access_codes where tenant_ref is distinct from code'
    into n_drifted;

  if n_drifted > 0 then
    raise exception using
      errcode = 'raise_exception',
      message = format(
        'DOWN MIGRATION REFUSED: %s access code(s) have tenant_ref different from code.',
        n_drifted),
      detail  = 'Dropping tenant_ref would strand rows in crm_connections and decision_log '
                'that are keyed by the opaque ref rather than by the code.',
      hint    = 'Roll forward instead. Reverting requires re-keying those tables by hand, '
                'and decision_log is append-only.';
  end if;
end $$;

drop index if exists access_codes_tenant_ref_key;
alter table access_codes drop column if exists tenant_ref;

commit;
