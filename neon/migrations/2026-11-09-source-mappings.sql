-- Saved source mappings and decision-log source index (2026-11, PK-24).
--
-- WHY
-- Design 2026-11-06 section 3.1: once a customer confirms the column mapping
-- for a CSV or export from a given source system, the mapping persists per
-- tenant and source so the same headers skip confirmation next time. The
-- existing salesforce_mappings table is keyed by the Salesforce connection and
-- cannot hold CSV or other-source mappings. governance reads filter
-- decision_log on lower(trim(payload->>'source')) within a tenant, which no
-- current index supports.
--
-- WHAT
-- 1. source_mappings: one row per (customer_ref, source_system,
--    header_fingerprint). Stores header STRINGS and canonical field NAMES only,
--    never row values. The shape is enforced by CHECK constraints (jsonb_typeof
--    plus jsonb_path_exists in strict mode, so nested arrays are not unwrapped), no trigger: headers must be a jsonb array whose
--    elements are all strings, mapping must be a jsonb object whose values are
--    all strings. Nested objects, arrays, numbers and nulls are rejected.
--    No foreign key to salesforce_connections: CSV tenants have no connection.
--    source_system is lower-cased trimmed plain text with no enum CHECK, so the
--    SourceSystem set can grow (and PK-41 can generalise connections) without
--    altering this table. headers is capped at 500 entries (widest real export
--    in view is a Salesforce Opportunity field list, a few hundred columns) to
--    bound a buggy caller; CHECKs are shape only, content is enforced by
--    pricing/mapping_store.py (PK-28).
-- 2. decision_log_tenant_source_idx: expression index on
--    (customer_ref, lower(trim(payload->>'source')), created_at desc). Serves
--    tenant-scoped source equality or = any(...) filters; created_at desc serves
--    the created_at range condition, not an ORDER BY (= any plans sort anyway).
--    No rows are rewritten.
--
-- DEPLOY ORDER
-- Run BEFORE the code deploy that reads/writes source_mappings (PK-28). Purely
-- additive: a new table and a new index, nothing renamed or dropped. Running
-- code does not reference either, so the intermediate state (migration applied,
-- old code running) is identical in behaviour; the index only speeds reads.
-- The index build takes a brief write lock on decision_log (plain CREATE INDEX
-- inside a transaction; CONCURRENTLY cannot run in one). Acceptable at current
-- volume; revisit if decision_log is large.
--
-- Idempotent and re-runnable. Ends with a guard that decision_log's row count
-- is unchanged.

begin;

-- Block concurrent writes so an app insert cannot trip the row-count guard.
lock table decision_log in share mode;

select set_config('pk24.decision_log_before',
                  (select count(*) from decision_log)::text, true);

create table if not exists source_mappings (
  id                 uuid primary key default gen_random_uuid(),
  customer_ref       text not null check (length(customer_ref) > 0),
  source_system      text not null
    check (source_system = lower(btrim(source_system)) and length(source_system) > 0),
  header_fingerprint text not null check (length(btrim(header_fingerprint)) > 0),
  headers            jsonb not null
    check (jsonb_typeof(headers) = 'array'
           and jsonb_array_length(headers) between 1 and 500
           and not jsonb_path_exists(headers, 'strict $[*] ? (@.type() != "string")')),
  mapping            jsonb not null default '{}'::jsonb
    check (jsonb_typeof(mapping) = 'object'
           and not jsonb_path_exists(mapping, 'strict $.* ? (@.type() != "string")')),
  confirmed_by       text not null default '',
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  constraint source_mappings_tenant_source_fp_key
    unique (customer_ref, source_system, header_fingerprint)
);

comment on table source_mappings is
  'Confirmed column mappings per tenant and source system. Holds header strings and canonical field names only, never row values. Shape only; content is enforced by pricing/mapping_store.py, PK-28. CHECKs bound shape (string array of 1 to 500 headers, string-to-string mapping) and normalise keys.';
comment on column source_mappings.headers is
  'jsonb array of header strings only, as they appeared in the export. Never row values.';
comment on column source_mappings.mapping is
  'jsonb object of header string to canonical field name (string to string only). Never row values.';
comment on column source_mappings.header_fingerprint is
  'Stable fingerprint of the normalised header list; same headers, same fingerprint, so confirmation is skipped.';

create index if not exists decision_log_tenant_source_idx
  on decision_log (customer_ref, (lower(trim(payload->>'source'))), created_at desc);

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
