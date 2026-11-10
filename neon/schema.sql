-- Pricekeel storage (Neon / Postgres).
-- Run once in the Neon SQL editor (or psql) against your project's database.
--
-- Access is gated by the connection string (DATABASE_URL), which the web app
-- (Vercel) and API (Render) hold server-side only. There is no public/anon
-- HTTP surface in front of these tables, so row-level security is not needed
-- the way it was under Supabase's PostgREST anon role. Keep DATABASE_URL secret.

create table if not exists leads (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  company       text not null,
  email         text not null,
  role_title    text not null,
  role_function text not null,
  -- Qualifying + attribution (launch-readiness):
  revenue_range  text not null default '',
  pricing_model  text not null default '',
  utm_source     text not null default '',
  utm_medium     text not null default '',
  utm_campaign   text not null default '',
  consent       boolean not null default false,  -- agreed to the privacy policy
  created_at    timestamptz not null default now()
);

-- Case-insensitive lookup support on email. PLAIN index, not a uniqueness
-- constraint: email was never unique on this table, and lead capture
-- (web/src/lib/store.ts's saveLead) has no ON CONFLICT clause, so a UNIQUE
-- index would fail on any existing duplicate email and would then 500 every
-- returning visitor who resubmits the lead-gate form. See
-- neon/migrations/2026-09-26-tenant-scoped-indexes.sql for the full
-- reasoning. Added by that migration.
create index if not exists leads_lower_email_idx
  on leads (lower(email));

create table if not exists access_codes (
  code        text primary key,
  issued_to   text,                       -- prospect / company the code is for
  lead_id     uuid references leads(id),  -- optional link to the lead
  expires_at  timestamptz,                -- null = no expiry
  used_at     timestamptz,                -- set on first successful use
  revoked     boolean not null default false,
  created_at  timestamptz not null default now(),
  -- Tenant key (2026-11-10-source-connections.sql, PK-41). Rows that existed at
  -- migration time were backfilled to their code (a bearer secret, never log
  -- it) until PK-43 re-keys; new codes get an opaque 'tn_' plus random UUID.
  tenant_ref  text not null default 'tn_' || replace(gen_random_uuid()::text, '-', '')
);

create unique index if not exists access_codes_tenant_ref_key
  on access_codes (tenant_ref);

comment on column access_codes.tenant_ref is
  'Tenant key. For codes that existed at migration time it EQUALS THE ACCESS CODE, which is a bearer secret, until PK-43 re-keys: treat it as secret and never log it. New codes default to tn_ plus a random UUID without dashes, which is opaque.';

-- Supports the leads -> access_codes lookup. Added by
-- 2026-09-26-tenant-scoped-indexes.sql.
create index if not exists access_codes_lead_id_idx
  on access_codes (lead_id);

-- Issue a code (generate a random URL-safe token outside SQL, then):
--   insert into access_codes (code, issued_to, expires_at)
--   values ('PASTE-RANDOM-TOKEN', 'Acme Inc', now() + interval '30 days');
-- Revoke one:   update access_codes set revoked = true where code = '...';

-- Governance loop: persistent decision log. Every copilot decision and
-- discount-exception request the API serves is appended here (pricing/
-- governance.py via psycopg, DATABASE_URL only). This is the system-of-record
-- moat; rows are append-only and never updated.
create table if not exists decision_log (
  id uuid primary key default gen_random_uuid(),
  customer_ref text not null default 'default',
  kind text not null check (kind in ('copilot','exception')),
  deal_id text not null default '',
  payload jsonb not null default '{}'::jsonb,
  decision text not null default '',
  justification text not null default '',
  requested_by text not null default '',
  created_at timestamptz not null default now()
);

-- Read paths: GET /exceptions filters kind + orders by created_at desc;
-- /digest reads everything in the last 7 days.
create index if not exists decision_log_kind_created_at_idx
  on decision_log (kind, created_at desc);

-- Every tenant-scoped read filters on customer_ref first (see
-- pricing/governance.py); without this, that scan grows with total rows
-- across every tenant. Added by 2026-09-26-tenant-scoped-indexes.sql. Kept
-- alongside decision_log_kind_created_at_idx above, which /digest still needs
-- for its cross-tenant 7-day read.
create index if not exists decision_log_tenant_kind_created_idx
  on decision_log (customer_ref, kind, created_at desc);

-- Salesforce CRM workflow (2026-08-01). Raw Opportunity rows are never
-- persisted here: the connector queries Salesforce on demand, sends a bounded
-- in-memory payload to FastAPI, and stores only connection/config/sync metadata
-- plus the append-only decision_log above.
create table if not exists salesforce_connections (
  customer_ref            text primary key,
  org_id                  text not null,
  user_id                 text not null default '',
  instance_url            text not null,
  access_token_encrypted  text not null,
  refresh_token_encrypted text not null,
  token_type              text not null default 'Bearer',
  scope                   text not null default '',
  issued_at               text not null default '',
  status                  text not null default 'connected'
    check (status in ('connected','reauth_required','error')),
  last_error              text not null default '',
  last_sync_at            timestamptz,
  last_sync_closed        integer not null default 0,
  last_sync_open          integer not null default 0,
  connected_at            timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

create table if not exists salesforce_mappings (
  customer_ref          text primary key references salesforce_connections(customer_ref)
                         on delete cascade,
  mapping               jsonb not null default '{}'::jsonb,
  policy_threshold_pct  double precision not null default 15.0,
  default_value_metric  text not null default 'hybrid',
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create index if not exists salesforce_connections_status_updated_idx
  on salesforce_connections (status, updated_at desc);

-- Customer-selected, public competitor evidence. Claims remain qualitative
-- context and are never an input to the numerical discount guardrail.
create table if not exists competitor_context_sources (
  id               uuid primary key default gen_random_uuid(),
  customer_ref     text not null,
  competitor_name  text not null,
  source_url       text not null,
  source_type      text not null,
  summary          text not null default '',
  claims           jsonb not null default '[]'::jsonb,
  confidence       text not null default 'medium'
    check (confidence in ('high','medium','low')),
  captured_at      timestamptz not null default now(),
  last_verified_at timestamptz not null default now(),
  unique (customer_ref, source_url)
);

create index if not exists competitor_context_customer_verified_idx
  on competitor_context_sources (customer_ref, last_verified_at desc);

-- Saved source mappings (2026-11-09-source-mappings.sql, PK-24). One confirmed
-- column mapping per tenant, source system and header fingerprint, so the same
-- headers skip confirmation. Header strings and canonical field names only,
-- never row values; shape enforced by the CHECKs. No FK to
-- salesforce_connections: CSV tenants have no connection.
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

-- Tenant-scoped source filter on decision_log, matching governance's
-- lower(trim(payload->>'source')) predicate (customer_ref equality plus source
-- equality or = any(...)). created_at desc serves the created_at range
-- condition, not an ORDER BY (= any(...) plans sort regardless). Added by 2026-11-09-source-mappings.sql.
create index if not exists decision_log_tenant_source_idx
  on decision_log (customer_ref, (lower(trim(payload->>'source'))), created_at desc);

-- Source-keyed connections (2026-11-10-source-connections.sql, PK-41). One row
-- per tenant and source system. Ciphertext credentials only (CHECKed to the
-- versioned format), never plaintext, never a deal value. The legacy
-- salesforce_connections and salesforce_mappings above stay until PK-70 drops
-- them; the migration backfills Salesforce rows into these tables.
create table if not exists source_connections (
  customer_ref           text not null check (length(customer_ref) > 0),
  source_system          text not null
    check (source_system in ('salesforce','hubspot','stripe','chargebee')),
  external_account_id    text not null default '',
  instance_url           text,
  credential_kind        text not null
    check (credential_kind in ('oauth_refresh','restricted_key','api_key')),
  access_token_encrypted text
    check (access_token_encrypted is null
           or access_token_encrypted ~ '^v[0-9]+(\.[A-Za-z0-9_-]+){2,}$'),
  credential_encrypted   text not null
    check (credential_encrypted ~ '^v[0-9]+(\.[A-Za-z0-9_-]+){2,}$'),
  key_id                 text not null default '',
  scope                  text not null default '',
  token_expires_at       timestamptz,
  status                 text not null default 'connected'
    check (status in ('connected','reauth_required','error','revoked')),
  last_error             text not null default '',
  last_sync_at           timestamptz,
  last_sync_counts       jsonb not null default '{}'::jsonb
    check (jsonb_typeof(last_sync_counts) = 'object'
           and last_sync_counts - array['closed','open','deals_fetched','mappings'] = '{}'::jsonb
           and not jsonb_path_exists(last_sync_counts,
                 'strict $.* ? (@.type() != "number" || @ < 0 || @.floor() != @)')),
  connected_at           timestamptz not null default now(),
  updated_at             timestamptz not null default now(),
  primary key (customer_ref, source_system),
  constraint source_connections_instance_url_sf_only
    check (instance_url is null or source_system = 'salesforce'),
  constraint source_connections_sf_has_instance_url
    check (source_system <> 'salesforce' or instance_url is not null),
  constraint source_connections_v2_has_key_id
    check (key_id <> ''
           or (credential_encrypted like 'v1.%'
               and (access_token_encrypted is null or access_token_encrypted like 'v1.%')))
);

comment on table source_connections is
  'One connected source per tenant and source system. Holds ciphertext credentials, identifiers, status and sync counts only. No plaintext credential and no deal, invoice or account value is ever stored here; row data is processed in memory and discarded.';
comment on column source_connections.access_token_encrypted is
  'CIPHERTEXT ONLY: versioned AES-GCM output (v<n>.part.part, enforced by CHECK). Never a plaintext token. Null for credentials with no access token (Stripe restricted key, Chargebee API key).';
comment on column source_connections.credential_encrypted is
  'CIPHERTEXT ONLY: versioned AES-GCM output (v<n>.part.part, enforced by CHECK) of the long-lived credential: OAuth refresh token, Stripe restricted key or Chargebee API key. Never plaintext.';
comment on column source_connections.key_id is
  'Id of the encryption key that produced the ciphertext. Empty for v1 ciphertexts, which carry none.';
comment on column source_connections.last_sync_counts is
  'jsonb object of non-negative integer counts from the last sync, under an allowlisted key set (closed, open, deals_fetched, mappings), enforced by CHECK. salesforce-store.ts writes closed and open; the other two are reserved for HubSpot and later connectors. Counts only, never records or amounts.';
comment on column source_connections.external_account_id is
  'Vendor account identifier: Salesforce org id, HubSpot portal id, Stripe account id, Chargebee site name.';

create table if not exists source_connection_config (
  customer_ref         text not null,
  source_system        text not null,
  mapping              jsonb not null default '{}'::jsonb
    check (jsonb_typeof(mapping) = 'object'
           and not jsonb_path_exists(mapping, 'strict $.* ? (@.type() != "string")')),
  stage_map            jsonb not null default '{}'::jsonb
    check (jsonb_typeof(stage_map) = 'object'
           and not jsonb_path_exists(stage_map, 'strict $.* ? (@.type() != "string")')),
  list_price_set       jsonb not null default '[]'::jsonb
    check (jsonb_typeof(list_price_set) = 'array'
           and not jsonb_path_exists(list_price_set, 'strict $[*] ? (@.type() != "string")')),
  policy_threshold_pct double precision not null default 15.0,
  default_value_metric text not null default 'hybrid',
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  primary key (customer_ref, source_system),
  constraint source_connection_config_connection_fkey
    foreign key (customer_ref, source_system)
    references source_connections (customer_ref, source_system)
    on delete cascade
);

comment on table source_connection_config is
  'Per-connection configuration, generalising salesforce_mappings. Config only, never values: field names, stage identifiers, price identifiers, thresholds. Cascades from source_connections.';
comment on column source_connection_config.mapping is
  'jsonb object of canonical field to vendor field name, string values only (CHECK). Names only; that they are not row values is enforced by the app.';
comment on column source_connection_config.stage_map is
  'jsonb object of vendor stage identifier to canonical outcome, string to string, confirmed by a person.';
comment on column source_connection_config.list_price_set is
  'jsonb array of vendor price or property identifiers confirmed as list price (strings, shape enforced by CHECK). That they are identifiers and not amounts is enforced by the app, not the database.';

create index if not exists source_connections_status_updated_idx
  on source_connections (status, updated_at desc);
