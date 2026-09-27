-- Tenant-scoped indexes (2026-09-26).
--
-- WHY
-- Every tenant-scoped read in pricing/governance.py filters on customer_ref
-- first (clauses = ["customer_ref = %s", ...]) before kind/date, but
-- decision_log's only index is (kind, created_at desc), a full scan grows
-- with total rows across every tenant, not just the one being read.
-- access_codes.lead_id has no supporting index for the leads -> access_codes
-- join done on issue/lookup. leads.email has no supporting index for the
-- case-insensitive lookup the lead-gate form would want to dedupe on.
--
-- WHAT
-- Three additive indexes. None of them replace or narrow an existing index:
-- decision_log_kind_created_at_idx stays, because /digest reads across every
-- tenant in the last 7 days and does not filter on customer_ref.
--
-- leads_lower_email_idx is a PLAIN (non-unique) index, not a uniqueness
-- constraint (2026-09-26 code-review fix, same day as the original cut of
-- this file): email was never unique on `leads`, and lead capture
-- (web/src/lib/store.ts's saveLead) does a plain INSERT with no
-- ON CONFLICT clause and no pre-check. A UNIQUE index here would (a) fail
-- this whole migration outright if any two existing rows already share a
-- case-insensitive email, and (b) after that, permanently 500 every
-- returning visitor who resubmits the lead-gate form (a normal retry /
-- double-click), since the app has no conflict handling to catch the
-- constraint violation. A plain index gives the same query speed-up for a
-- future case-insensitive lookup without introducing a write-time failure
-- mode the app was not built to handle. Deduping leads by email, if ever
-- wanted, needs an ON CONFLICT-aware write path shipped first.
--
-- DEPLOY ORDER
-- Additive only: new indexes, no column/table changes, nothing renamed or
-- dropped. Safe to run before, during, or after the code deploy, no running
-- code depends on these indexes existing, they only make existing queries
-- faster, and none of them can fail on existing data (no uniqueness
-- constraint is being added).
--
-- Idempotent and re-runnable.

begin;

create index if not exists decision_log_tenant_kind_created_idx
  on decision_log (customer_ref, kind, created_at desc);

create index if not exists access_codes_lead_id_idx
  on access_codes (lead_id);

create index if not exists leads_lower_email_idx
  on leads (lower(email));

commit;
