-- Pricekeel buyer-funnel storage (Supabase / Postgres).
-- Run in the Supabase SQL editor. The web app uses the service-role key
-- server-side only, so row-level security is not required for these tables;
-- keep the anon key away from them.

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

-- RLS: enabled with NO policies. The app talks to these tables exclusively
-- through the service-role key (which bypasses RLS), so enabling RLS costs
-- nothing and blocks the anon key entirely (with RLS off, the default anon
-- grants would expose both tables). Applied to prod 2026-06-11.
alter table leads enable row level security;
alter table access_codes enable row level security;

-- Issue a code (generate a random URL-safe token outside SQL, then):
--   insert into access_codes (code, issued_to, expires_at)
--   values ('PASTE-RANDOM-TOKEN', 'Acme Inc', now() + interval '30 days');
-- Revoke one:   update access_codes set revoked = true where code = '...';

-- Governance loop (2026-06-11): persistent decision log. Every copilot
-- decision and discount-exception request the API serves is appended here
-- (pricing/governance.py via PostgREST, service-role key only). This is the
-- system-of-record moat; rows are append-only and never updated.
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

-- Same RLS posture as the tables above: enabled with no policies, so only
-- the service-role key (which bypasses RLS) can touch it.
alter table decision_log enable row level security;
