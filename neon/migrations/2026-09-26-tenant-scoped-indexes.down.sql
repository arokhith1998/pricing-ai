-- DOWN migration for 2026-09-26-tenant-scoped-indexes.sql
--
-- Drops the three indexes. Indexes hold no data of their own; dropping one
-- costs query-plan speed, never rows. No destructive-data guard is needed
-- here, unlike a down that drops a column or a table.
--
-- DEPLOY ORDER: additive-only reversal, safe to run at any point relative to
-- the code deploy.
--
-- Idempotent and re-runnable.

begin;

drop index if exists leads_lower_email_key;
drop index if exists access_codes_lead_id_idx;
drop index if exists decision_log_tenant_kind_created_idx;

commit;
