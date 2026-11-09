"""Structural guardrail for the non-negotiable migration rule: every migration
is additive, transactional, and reversible, which means every plain
<slug>.sql in neon/migrations/ ships beside a matching <slug>.down.sql.

This does not run SQL against a database (no CI database exists yet, see
neon/MIGRATIONS.md for the manual up/down/up verification against a scratch
Postgres). It is a cheap, always-on check against exactly the gap that let
2026-08-01-salesforce-crm-workflow.sql sit with no down file on main for
seven weeks: a missing pairing now fails the suite instead of waiting for a
review to notice.
"""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_DOWN_SUFFIX = ".down.sql"


def _all_sql_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _up_files() -> list[Path]:
    return [p for p in _all_sql_files() if not p.name.endswith(_DOWN_SUFFIX)]


def _down_files() -> list[Path]:
    return [p for p in _all_sql_files() if p.name.endswith(_DOWN_SUFFIX)]


def test_migrations_directory_is_not_empty():
    # A passing-but-vacuous test (zero files -> zero missing pairs) would hide
    # the exact failure mode this file exists to catch.
    assert _up_files(), f"no migrations found in {MIGRATIONS_DIR}"


def test_every_up_migration_has_a_down_file():
    downs = {p.name for p in _down_files()}
    missing = [
        p.name for p in _up_files()
        if p.name[: -len(".sql")] + _DOWN_SUFFIX not in downs
    ]
    assert not missing, f"migration(s) with no down file: {missing}"


def test_every_down_file_has_a_matching_up_migration():
    ups = {p.name for p in _up_files()}
    orphaned = [
        p.name for p in _down_files()
        if p.name[: -len(_DOWN_SUFFIX)] + ".sql" not in ups
    ]
    assert not orphaned, f"down file(s) with no matching up migration: {orphaned}"


def test_down_migrations_are_wrapped_in_a_transaction():
    """Additive, transactional, reversible: transactional means begin/commit,
    every time, so a failure (e.g. the destructive-data guard firing) rolls
    back everything instead of leaving a half-applied schema."""
    for p in _down_files():
        text = p.read_text(encoding="utf-8").lower()
        assert "begin;" in text, f"{p.name} missing 'begin;'"
        assert "commit;" in text, f"{p.name} missing 'commit;'"


def test_up_migrations_are_wrapped_in_a_transaction():
    for p in _up_files():
        text = p.read_text(encoding="utf-8").lower()
        assert "begin;" in text, f"{p.name} missing 'begin;'"
        assert "commit;" in text, f"{p.name} missing 'commit;'"


# --- leads_lower_email_idx must never be a uniqueness constraint ------------
# (code-review fix, 2026-09-26: `leads.email` was never unique, and lead
# capture has no ON CONFLICT handling, so a UNIQUE index here can both fail
# this migration outright against a prod database with an existing duplicate
# email, and afterwards 500 every returning visitor who resubmits the
# lead-gate form. A plain index gives the same lookup speed-up without that
# failure mode.)

def _tenant_scoped_index_migration() -> Path:
    matches = [p for p in _up_files() if "tenant-scoped-indexes" in p.name]
    assert matches, "expected a tenant-scoped-indexes migration to exist"
    return matches[0]


def test_leads_email_index_is_not_unique_in_the_migration():
    text = _tenant_scoped_index_migration().read_text(encoding="utf-8").lower()
    assert "leads_lower_email_idx" in text
    assert "create unique index" not in text


def test_leads_email_index_is_not_unique_in_schema_sql():
    schema = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8").lower()
    assert "leads_lower_email_idx" in schema
    assert "create unique index" not in schema.replace(
        "create unique index if not exists access_codes_tenant_ref_key", ""
    )


# --- PK-41: source_connections, Salesforce backfill, opaque tenant ref ------
# Structural checks only (no database in CI). The scratch-cluster run in the
# PR body is the behavioural proof: up, up, down, down, up, backfill counts,
# down refusal, schema dump identity.

SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"
PK41_UP = MIGRATIONS_DIR / "2026-11-10-source-connections.sql"
PK41_DOWN = MIGRATIONS_DIR / "2026-11-10-source-connections.down.sql"


def _table_body(sql: str, table: str) -> str:
    """Text between 'create table if not exists <table> (' and the matching
    close paren at line start, with -- comments removed."""
    start = sql.index(f"create table if not exists {table} (")
    end = sql.index("\n);", start)
    body = sql[start:end]
    return "\n".join(line.split("--")[0] for line in body.splitlines())


def _column_names(body: str) -> list[str]:
    names = []
    for line in body.splitlines()[1:]:
        m = re.match(r"^  ([a-z_]+)\s+(text|jsonb|timestamptz|double|integer|boolean|uuid)", line)
        if m:
            names.append(m.group(1))
    return names


def test_pk41_pair_exists_and_sorts_after_source_mappings():
    assert PK41_UP.exists() and PK41_DOWN.exists()
    names = [p.name for p in _up_files()]
    assert names == sorted(names)
    assert names.index(PK41_UP.name) > names.index("2026-11-09-source-mappings.sql")


def test_pk41_source_connections_key_and_system_check():
    up = PK41_UP.read_text(encoding="utf-8").lower()
    body = _table_body(up, "source_connections")
    assert "primary key (customer_ref, source_system)" in body
    assert "source_system in ('salesforce','hubspot','stripe','chargebee')" in body
    assert "'revoked'" in body
    for col in (
        "external_account_id", "instance_url", "credential_kind",
        "access_token_encrypted", "credential_encrypted", "key_id", "scope",
        "token_expires_at", "status", "last_error", "last_sync_at",
        "last_sync_counts", "connected_at", "updated_at",
    ):
        assert col in _column_names(body), f"source_connections missing {col}"


def test_pk41_no_column_can_hold_a_plaintext_credential_or_deal_value():
    up = PK41_UP.read_text(encoding="utf-8").lower()
    for table in ("source_connections", "source_connection_config"):
        for col in _column_names(_table_body(up, table)):
            secretish = re.search(r"token|secret|key|credential|password", col)
            if secretish and col not in ("key_id", "token_expires_at", "credential_kind"):
                assert col.endswith("_encrypted"), f"{table}.{col} could hold plaintext"
            assert not re.search(r"amount|price_value|revenue|acv|arr|deal_value|booked|list_value", col), (
                f"{table}.{col} could hold a deal value"
            )
    body = _table_body(up, "source_connections")
    # Ciphertext format is enforced, so a bare token or an rk_ key cannot be stored.
    fmt = r"~ '^v[0-9]+(\.[a-za-z0-9_-]+){2,}$'"
    assert f"credential_encrypted {fmt}" in body
    assert f"access_token_encrypted {fmt}" in body
    assert "ciphertext only" in up


def test_pk41_config_cascades_from_connections():
    up = PK41_UP.read_text(encoding="utf-8").lower()
    body = _table_body(up, "source_connection_config")
    assert "references source_connections (customer_ref, source_system)" in body
    assert "on delete cascade" in body


def test_pk41_up_leaves_legacy_tables_untouched_and_backfills_idempotently():
    up = PK41_UP.read_text(encoding="utf-8").lower()
    for table in ("salesforce_connections", "salesforce_mappings"):
        for verb in ("alter table", "drop table", "delete from", "truncate", "update"):
            assert f"{verb} {table}" not in up, f"up must not {verb} {table}"
    assert up.count("on conflict (customer_ref, source_system) do nothing") == 2
    assert "from salesforce_connections" in up and "from salesforce_mappings" in up
    assert "lock table" in up and "share mode" in up
    code_only = "\n".join(line.split("--")[0] for line in up.splitlines())
    assert "drop table" not in code_only and "truncate" not in code_only


def test_pk41_tenant_ref_backfills_to_code_then_defaults_to_random():
    up = PK41_UP.read_text(encoding="utf-8").lower()
    add = up.index("add column if not exists tenant_ref text;")
    backfill = up.index("update access_codes set tenant_ref = code where tenant_ref is null;")
    default = up.index("set default 'tn_' || replace(gen_random_uuid()::text, '-', '')")
    not_null = up.index("alter column tenant_ref set not null")
    assert add < backfill < default < not_null  # default must come after the backfill
    assert "create unique index if not exists access_codes_tenant_ref_key" in up


def test_pk41_down_refuses_non_salesforce_rows_and_drops_exactly_the_up():
    down = PK41_DOWN.read_text(encoding="utf-8").lower()
    assert "do $$" in down
    assert "source_system <> ''salesforce''" in down
    assert "down migration refused" in down
    refuse = down.index("down migration refused")
    first_drop = down.index("drop table if exists source_connection_config")
    assert refuse < first_drop  # the guard runs before anything is dropped
    code_only = "\n".join(line.split("--")[0] for line in down.splitlines())
    dropped = set(re.findall(r"drop (?:table|index) if exists (\w+)", code_only))
    assert dropped == {"source_connection_config", "source_connections", "access_codes_tenant_ref_key"}
    assert "alter table access_codes drop column if exists tenant_ref" in code_only
    for legacy in ("salesforce_connections", "salesforce_mappings", "decision_log"):
        assert f"drop table if exists {legacy}" not in code_only
        assert f"delete from {legacy}" not in code_only


def test_pk41_header_states_deploy_order():
    for p in (PK41_UP, PK41_DOWN):
        assert "DEPLOY ORDER" in p.read_text(encoding="utf-8")


def test_pk41_schema_sql_matches_migration_ddl():
    schema = SCHEMA_SQL.read_text(encoding="utf-8")
    up = PK41_UP.read_text(encoding="utf-8")
    for table in ("source_connections", "source_connection_config"):
        assert _table_body(schema, table) == _table_body(up, table), (
            f"schema.sql {table} drifted from the migration"
        )
    low = schema.lower()
    assert "tenant_ref  text not null default 'tn_' || replace(gen_random_uuid()::text, '-', '')" in low
    assert "create unique index if not exists access_codes_tenant_ref_key" in low
    assert "create index if not exists source_connections_status_updated_idx" in low
    # Legacy tables stay in schema.sql until PK-70 drops them.
    assert "create table if not exists salesforce_connections" in low


def _code(text: str) -> str:
    return "\n".join(line.split("--")[0] for line in text.splitlines())


def test_pk41_last_sync_counts_is_allowlisted_non_negative_integers():
    body = _table_body(PK41_UP.read_text(encoding="utf-8").lower(), "source_connections")
    assert "last_sync_counts - array['closed','open','deals_fetched','mappings'] = '{}'::jsonb" in body
    assert "jsonb_path_exists(last_sync_counts" in body
    assert 'strict $.* ? (@.type() != "number" || @ < 0 || @.floor() != @)' in body


def test_pk41_mapping_values_are_strings_only_and_sf_needs_instance_url():
    up = PK41_UP.read_text(encoding="utf-8").lower()
    cfg = _table_body(up, "source_connection_config")
    mapping = cfg[cfg.index("mapping "):cfg.index("stage_map")]
    assert "jsonb_path_exists(mapping, 'strict $.* ? (@.type() != \"string\")')" in mapping
    conn = _table_body(up, "source_connections")
    assert "check (source_system <> 'salesforce' or instance_url is not null)" in conn
    assert "check (key_id <> '' or credential_encrypted like 'v1.%')" in conn


def test_pk41_lock_timeout_and_access_exclusive_up_front():
    for p in (PK41_UP, PK41_DOWN):
        code = _code(p.read_text(encoding="utf-8").lower())
        assert "set local lock_timeout = '5s';" in code
        assert code.index("lock_timeout") < code.index("lock table access_codes in access exclusive mode;")
        assert code.index("access exclusive") < code.index("share mode")


def test_pk41_down_drift_refusal_is_narrowed_to_keyed_data():
    down = PK41_DOWN.read_text(encoding="utf-8").lower()
    for table in ("decision_log", "source_mappings", "source_connections",
                  "salesforce_connections", "salesforce_mappings"):
        assert f"'{table}'" in down
    assert "t.customer_ref = a.tenant_ref" in down
    # the old blanket refusal (any drifted row) is gone
    assert "select count(*) from access_codes where tenant_ref is distinct from code'" not in down


def test_pk41_header_rerun_safety_and_tenant_ref_secret_wording():
    up = PK41_UP.read_text(encoding="utf-8")
    assert "RERUN SAFETY" in up
    assert "NEVER rerun this up and NEVER run down" in up
    assert "must re-run this file" not in up
    assert "PK-43 revoke must also delete the legacy rows" in up
    assert "bearer secret" in up and "never log it" in up
    schema = SCHEMA_SQL.read_text(encoding="utf-8")
    assert "EQUALS THE ACCESS CODE" in schema and "EQUALS THE ACCESS CODE" in up
