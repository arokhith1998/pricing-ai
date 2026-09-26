-- Tenant-scoped indexes (2026-09-26).
--
-- WHY
-- Every tenant-scoped read in pricing/governance.py filters on customer_ref
-- first (clauses = ["customer_ref = %s", ...]) before kind/date, but
-- decision_log's only index is (kind, created_at desc) — a full scan grows
-- with total rows across every tenant, not just the one being read.
-- access_codes.lead_id has no supporting index for the leads -> access_codes
-- join done on issue/lookup. leads.email has no uniqueness at all, so a
-- resubmitted lead-gate form (network retry, double-click) silently creates a
-- second full lead row instead of colliding, unlike pricing/ingest.py's
-- careful duplicate/conflict handling on deal CSVs.
--
-- WHAT
-- Three additive indexes. None of them replace or narrow an existing index:
-- decision_log_kind_created_at_idx stays, because /digest reads across every
-- tenant in the last 7 days and does not filter on customer_ref.
--
-- DEPLOY ORDER
-- Additive only: new indexes, no column/table changes, nothing renamed or
-- dropped. Safe to run before, during, or after the code deploy — no running
-- code depends on these indexes existing, they only make existing queries
-- faster. The one exception is the unique index on lower(email): see the
-- CAVEAT below.
--
-- CAVEAT (read before running against a real database)
-- If any two existing leads rows already share the same case-insensitive
-- email, CREATE UNIQUE INDEX fails and the whole transaction rolls back
-- (nothing partially applies). Before running this against a database with
-- real rows, check first:
--   select lower(email), count(*) from leads group by 1 having count(*) > 1;
-- If that returns rows, resolve the duplicates (merge or delete) before
-- re-running this migration. See neon/MIGRATIONS.md for the full runbook.
--
-- Idempotent and re-runnable.

begin;

create index if not exists decision_log_tenant_kind_created_idx
  on decision_log (customer_ref, kind, created_at desc);

create index if not exists access_codes_lead_id_idx
  on access_codes (lead_id);

create unique index if not exists leads_lower_email_key
  on leads (lower(email));

commit;
