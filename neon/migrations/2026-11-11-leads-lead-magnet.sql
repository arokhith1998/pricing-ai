-- leads.lead_magnet: which lead magnet a lead came from (2026-11, PK-108).
--
-- WHY
-- Design 2026-11-10-ai-margin-audit-calculator section 5: the margin audit
-- calculator reuses POST /api/lead, and the founder needs to tell a calculator
-- lead from a sample-gate lead. The design doc names the column `source`; the
-- board claim (PK-108) and the founder gate F7 name it `lead_magnet`, which is
-- also less ambiguous next to utm_source. This file follows the board claim.
--
-- WHAT
-- leads.lead_magnet text not null default ''. Empty means the lead came from
-- the existing sample gate (every row that exists today, and every insert that
-- does not name the column). A calculator lead carries 'margin_audit'. A CHECK,
-- leads_lead_magnet_format_chk, allows '' or a short snake_case tag
-- (^[a-z][a-z0-9_]{0,31}$): not an allowlist, so a later lead magnet needs no
-- migration, but it cannot hold an email, a number or free text. The typed
-- calculator inputs are never stored in the database (design section 5); this
-- column holds a tag only.
-- ADD COLUMN with a constant default is a metadata-only change on PostgreSQL 11+
-- (no table rewrite). Existing rows read '' without being touched.
--
-- DEPLOY ORDER
-- Run BEFORE the code deploy that writes the column (PK-109, /api/lead and
-- saveLead). Purely additive: one column with a default, one check. The running
-- app inserts into leads with an explicit column list and never selects the new
-- column, so the intermediate state (migration applied, old code running) is
-- identical in behaviour. Nothing is renamed or dropped. PK-109 must not deploy
-- before this is applied to production Neon, or every lead insert fails.
-- PRODUCTION APPLICATION NEEDS FOUNDER AUTHORISATION; no agent applies it.
--
-- RERUN SAFETY
-- Idempotent: add column if not exists, and the constraint is added only when
-- no constraint of that name exists on leads. A second run changes nothing.
-- Locks: leads is taken ACCESS EXCLUSIVE up front (it is ALTERed, so there is no
-- lock-upgrade window); lock_timeout is 5s so a busy table fails the migration
-- instead of queueing behind it. The check scans leads once; the table is small.
-- A row-count guard at the end asserts the migration touched no rows.

begin;

set local lock_timeout = '5s';

lock table leads in access exclusive mode;

select set_config('pk108.leads_before', (select count(*) from leads)::text, true);

alter table leads add column if not exists lead_magnet text not null default '';

do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.leads'::regclass
       and conname = 'leads_lead_magnet_format_chk'
  ) then
    alter table leads
      add constraint leads_lead_magnet_format_chk
      check (lead_magnet = '' or lead_magnet ~ '^[a-z][a-z0-9_]{0,31}$');
  end if;
end $$;

comment on column leads.lead_magnet is
  'Which lead magnet the lead came from. Empty = the sample gate (the original path). margin_audit = the AI pricing and margin audit calculator. A short snake_case tag only (CHECK); never typed inputs, which are not stored in the database.';

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
