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

create table if not exists access_codes (
  code        text primary key,
  issued_to   text,                       -- prospect / company the code is for
  lead_id     uuid references leads(id),  -- optional link to the lead
  expires_at  timestamptz,                -- null = no expiry
  used_at     timestamptz,                -- set on first successful use
  revoked     boolean not null default false,
  created_at  timestamptz not null default now()
);

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

-- CRM workflow (Salesforce 2026-08-01, generalized to any provider
-- 2026-08-18). Raw CRM records are never persisted here: the connector queries
-- the CRM on demand, sends a bounded in-memory payload to FastAPI, and stores
-- only connection/config/sync metadata plus the append-only decision_log above.
--
-- Two generic slots carry provider-specific identity, so a second CRM needs no
-- new columns:
--   org_id       Salesforce org ID       | HubSpot portal ID
--   instance_url Salesforce instance URL | HubSpot API base
create table if not exists crm_connections (
  customer_ref            text not null,
  provider                text not null default 'salesforce'
    check (provider in ('salesforce','hubspot')),
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
  updated_at              timestamptz not null default now(),
  primary key (customer_ref, provider)
);

create table if not exists crm_mappings (
  customer_ref          text not null,
  provider              text not null default 'salesforce'
    check (provider in ('salesforce','hubspot')),
  mapping               jsonb not null default '{}'::jsonb,
  policy_threshold_pct  double precision not null default 15.0,
  default_value_metric  text not null default 'hybrid',
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  primary key (customer_ref, provider),
  constraint crm_mappings_connection_fkey
    foreign key (customer_ref, provider)
    references crm_connections (customer_ref, provider) on delete cascade
);

create index if not exists crm_connections_status_updated_idx
  on crm_connections (status, updated_at desc);

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
