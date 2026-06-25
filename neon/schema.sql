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
