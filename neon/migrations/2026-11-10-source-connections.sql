-- Source-keyed connections, Salesforce backfill, opaque tenant ref (2026-11, PK-41).
--
-- File name: the board claim says 2026-11-source-connections.sql; the lead
-- decided on the YYYY-MM-DD-slug convention (neon/MIGRATIONS.md) and a date
-- after PK-24's 2026-11-09-source-mappings so the files sort in dependency order.
--
-- WHY
-- Design 2026-11-09 section 2.1: HubSpot, Stripe and Chargebee need credential
-- storage, and salesforce_connections is Salesforce-shaped (org_id, instance_url
-- and a mandatory refresh token). Section 2.3: access_codes' code is used as
-- the tenant key (customer_ref) in decision_log and the connection tables, so
-- rotating or revoking a code orphans or mis-targets a tenant's rows. Both
-- changes land in this one migration so neon/schema.sql is touched once.
--
-- WHAT
-- 1. source_connections, primary key (customer_ref, source_system), check on
--    salesforce | hubspot | stripe | chargebee. One row per tenant and source.
--    No column can hold a plaintext credential or a deal value: the two token
--    columns are text holding CIPHERTEXT ONLY, named *_encrypted, and a CHECK
--    refuses any value that is not in the versioned ciphertext format
--    (v<n>.<part>.<part>..., at least two url-safe segments after the version:
--    the v1 iv.ciphertext shape written by web/src/lib/salesforce-crypto.ts and
--    the v2 shape with a key id that PK-42 adds). A Stripe restricted key
--    (rk_...), "v1.rk_live_..." or a bare token cannot be stored. A v2 row must
--    carry a key_id. last_sync_counts is non-negative integers under an
--    allowlisted key set. scope, last_error and external_account_id are FREE
--    TEXT: keeping secrets out of them is PK-42's token-scan job, not a CHECK.
-- 2. source_connection_config, keyed the same way, composite foreign key to
--    source_connections ON DELETE CASCADE. Generalises salesforce_mappings:
--    vendor field mapping, confirmed stage map, confirmed list-price set,
--    policy threshold, default value metric. Config only, never values.
-- 3. Backfill, expand-and-contract (design 2.1): every salesforce_connections
--    row is copied to source_connections (source_system 'salesforce') and every
--    salesforce_mappings row to source_connection_config. Insert-select with
--    ON CONFLICT DO NOTHING, so a second run adds nothing and, after PK-42 has
--    moved the app, never overwrites a newer row with a stale legacy copy.
--    The legacy tables are NOT altered; PK-70 drops them after a soak.
--    Mapping from legacy columns:
--      org_id                  -> external_account_id
--      instance_url            -> instance_url
--      (constant)              -> credential_kind 'oauth_refresh'
--      access_token_encrypted  -> access_token_encrypted
--      refresh_token_encrypted -> credential_encrypted
--      (none: v1 has no key id)-> key_id '' (empty means the ciphertext carries none)
--      scope, status, last_error, last_sync_at, connected_at, updated_at: as is
--      last_sync_closed/open   -> last_sync_counts {"closed": n, "open": m}
--      token_expires_at        -> null (legacy stored issued_at only, no expiry)
--    Legacy user_id, token_type and issued_at have no section 2.1 column and are
--    not copied; they remain in the legacy table until PK-70. The app only
--    stores and echoes them, it makes no decision on them. token_type is always
--    'Bearer'.
-- 4. access_codes.tenant_ref: a stable tenant key that survives code
--    rotation. New codes get an opaque value; for codes that existed at migration
--    time it equals the access code (a bearer secret) until PK-43 re-keys, so
--    treat it as secret and never log it. Existing rows are backfilled to their
--    CURRENT CODE, so every decision_log and connection row already keyed by a
--    code still matches and no row in those tables is rewritten. New codes get
--    the column default: 'tn_' plus a random v4 UUID with dashes removed,
--    'tn_' || replace(gen_random_uuid()::text, '-', ''), 122 random bits from
--    the server CSPRNG (built in on PostgreSQL 13+, no extension). The
--    runbook's plain "insert into access_codes (code, issued_to, expires_at)"
--    keeps working and gets an opaque value. Unique index
--    access_codes_tenant_ref_key.
--
-- DEPLOY ORDER
-- Run BEFORE any code that reads or writes source_connections (PK-42) or
-- tenant_ref (PK-43). PK-24's 2026-11-09-source-mappings must already be
-- applied (it is independent of this file, but PK-41 is sequenced behind it on
-- neon/schema.sql). Purely additive: two new tables, one new column with a
-- default, one new index. The running app reads and writes only the legacy
-- tables and never selects access_codes.tenant_ref, so the intermediate state
-- (migration applied, old code running) behaves identically. Nothing is renamed
-- or dropped.
-- Intermediate-state caveat for PK-43: the app still keys tenants by code until
-- PK-43 deploys. A code issued AFTER this migration gets an opaque tenant_ref
-- different from its code; if that code is used before PK-43 deploys, its
-- decision_log rows are keyed by the code. PK-43 must reconcile those (set
-- tenant_ref = code for codes with used_at set that were created after this
-- migration) before switching customerRef(), or issue no new codes in the window.
--
-- RERUN SAFETY (read before applying twice)
-- Before the PK-42 cutover the file is idempotent: apply it as often as needed
-- (the backfill is insert ... on conflict do nothing, so a second run adds
-- nothing). AFTER the PK-42 cutover, NEVER rerun this up and NEVER run down and
-- then up again: the backfill would resurrect, from the legacy tables, a
-- Salesforce row that PK-42 disconnected or PK-43 revoked. Until PK-70 drops
-- the legacy salesforce_connections and salesforce_mappings, PK-42 disconnect
-- and PK-43 revoke must also delete the legacy rows for that tenant. The
-- backfill is a point-in-time copy: a token refreshed in the legacy table after
-- the first run is not copied by a rerun (on conflict do nothing keeps the older
-- copy), so PK-42 must do its own cutover refresh or ask tenants to reconnect.
--
-- GUARDS
-- The migration ends with checks that the legacy tables, decision_log and
-- access_codes row counts are unchanged and that every legacy row has its
-- counterpart. Locks: access_codes is taken ACCESS EXCLUSIVE up front (it is
-- ALTERed, so there is no lock-upgrade window) and the other tables in SHARE
-- mode; lock_timeout is 5s so a busy table fails the migration instead of
-- queueing behind it.

begin;

set local lock_timeout = '5s';

-- Block concurrent writes so an app insert cannot trip the row-count guards.
-- access_codes is ALTERed below, so take the strongest lock first.
lock table access_codes in access exclusive mode;
lock table decision_log, salesforce_connections, salesforce_mappings
  in share mode;

select set_config('pk41.decision_log_before', (select count(*) from decision_log)::text, true);
select set_config('pk41.access_codes_before', (select count(*) from access_codes)::text, true);
select set_config('pk41.sf_conn_before', (select count(*) from salesforce_connections)::text, true);
select set_config('pk41.sf_map_before', (select count(*) from salesforce_mappings)::text, true);

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
    check (key_id <> '' or credential_encrypted like 'v1.%')
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

-- Backfill Salesforce. Connections first: config has a foreign key to them.
insert into source_connections
  (customer_ref, source_system, external_account_id, instance_url,
   credential_kind, access_token_encrypted, credential_encrypted, key_id, scope,
   token_expires_at, status, last_error, last_sync_at, last_sync_counts,
   connected_at, updated_at)
select c.customer_ref, 'salesforce', c.org_id, c.instance_url,
       'oauth_refresh', c.access_token_encrypted, c.refresh_token_encrypted, '', c.scope,
       null, c.status, c.last_error, c.last_sync_at,
       jsonb_build_object('closed', c.last_sync_closed, 'open', c.last_sync_open),
       c.connected_at, c.updated_at
  from salesforce_connections c
on conflict (customer_ref, source_system) do nothing;

insert into source_connection_config
  (customer_ref, source_system, mapping, policy_threshold_pct,
   default_value_metric, created_at, updated_at)
select m.customer_ref, 'salesforce', m.mapping, m.policy_threshold_pct,
       m.default_value_metric, m.created_at, m.updated_at
  from salesforce_mappings m
on conflict (customer_ref, source_system) do nothing;

-- Opaque tenant ref. Order matters: add with NO default so existing rows are
-- not given random values, backfill to the current code, then set the default
-- for new rows, then NOT NULL and uniqueness.
alter table access_codes add column if not exists tenant_ref text;

update access_codes set tenant_ref = code where tenant_ref is null;

alter table access_codes
  alter column tenant_ref set default 'tn_' || replace(gen_random_uuid()::text, '-', '');
alter table access_codes
  alter column tenant_ref set not null;

create unique index if not exists access_codes_tenant_ref_key
  on access_codes (tenant_ref);

comment on column access_codes.tenant_ref is
  'Tenant key. For codes that existed at migration time it EQUALS THE ACCESS CODE, which is a bearer secret, until PK-43 re-keys: treat it as secret and never log it. New codes default to tn_ plus a random UUID without dashes, which is opaque.';

do $$
declare
  n bigint;
begin
  select count(*) into n from decision_log;
  if n <> current_setting('pk41.decision_log_before')::bigint then
    raise exception 'PK-41 guard: decision_log row count changed (% -> %)',
      current_setting('pk41.decision_log_before'), n;
  end if;
  select count(*) into n from access_codes;
  if n <> current_setting('pk41.access_codes_before')::bigint then
    raise exception 'PK-41 guard: access_codes row count changed (% -> %)',
      current_setting('pk41.access_codes_before'), n;
  end if;
  select count(*) into n from salesforce_connections;
  if n <> current_setting('pk41.sf_conn_before')::bigint then
    raise exception 'PK-41 guard: salesforce_connections row count changed (% -> %)',
      current_setting('pk41.sf_conn_before'), n;
  end if;
  select count(*) into n from salesforce_mappings;
  if n <> current_setting('pk41.sf_map_before')::bigint then
    raise exception 'PK-41 guard: salesforce_mappings row count changed (% -> %)',
      current_setting('pk41.sf_map_before'), n;
  end if;
  select count(*) into n from salesforce_connections c
   where not exists (select 1 from source_connections s
                      where s.customer_ref = c.customer_ref and s.source_system = 'salesforce');
  if n <> 0 then
    raise exception 'PK-41 guard: % salesforce_connections row(s) have no source_connections copy', n;
  end if;
  select count(*) into n from salesforce_mappings m
   where not exists (select 1 from source_connection_config s
                      where s.customer_ref = m.customer_ref and s.source_system = 'salesforce');
  if n <> 0 then
    raise exception 'PK-41 guard: % salesforce_mappings row(s) have no source_connection_config copy', n;
  end if;
  select count(*) into n from access_codes where tenant_ref is null;
  if n <> 0 then
    raise exception 'PK-41 guard: % access_codes row(s) have no tenant_ref', n;
  end if;
end $$;

commit;
