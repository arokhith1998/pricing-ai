-- Pricekeel Salesforce CRM workflow storage.
-- Additive and safe to rerun. Raw Salesforce Opportunity rows are never
-- persisted: only connection/config/sync metadata and selected public
-- competitor context live here.

begin;

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

commit;
