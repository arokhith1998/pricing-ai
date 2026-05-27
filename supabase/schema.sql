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
