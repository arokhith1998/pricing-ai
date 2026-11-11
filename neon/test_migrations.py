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
    assert "no legacy salesforce_connections match" in down
    assert "stage_map <> ''{}''::jsonb or list_price_set <> ''[]''::jsonb" in down
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
    assert "credential_encrypted like 'v1.%'" in conn
    assert "access_token_encrypted is null or access_token_encrypted like 'v1.%'" in conn


def test_pk41_lock_timeout_and_access_exclusive_up_front():
    for p in (PK41_UP, PK41_DOWN):
        code = _code(p.read_text(encoding="utf-8").lower())
        assert "set local lock_timeout = '5s';" in code
        assert code.index("lock_timeout") < code.index("lock table access_codes in access exclusive mode;")
        assert code.index("access exclusive") < code.index("share mode")


def test_pk41_down_drift_refusal_is_narrowed_to_keyed_data():
    down = PK41_DOWN.read_text(encoding="utf-8").lower()
    # tables are enumerated from information_schema, not hardcoded
    assert "information_schema.columns" in down
    assert "c.column_name = 'customer_ref'" in down
    assert "foreach tbl in array" not in down
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


# ---------------------------------------------------------------------------
# Executed against a real Postgres (skipped when no URL is configured).
# ---------------------------------------------------------------------------

import os
import uuid
from urllib.parse import urlsplit, urlunsplit

import pytest

_CTRL = "pk41-ctrl"
_CT = "v1.aGVsbG8.d29ybGQ"      # synthetic ciphertext shape, not a real secret
_CT2 = "v2.k1.aGVsbG8.d29ybGQ"


_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def _test_url() -> str | None:
    # Deliberately NOT DATABASE_URL: that is the variable the app reads for
    # production, and this test creates and drops databases on the server.
    return os.environ.get("PRICEKEEL_TEST_DATABASE_URL")


def _skip_reason(url: str | None) -> str | None:
    """None when the URL is safe to run against, else the reason to skip."""
    if not url:
        return "PRICEKEEL_TEST_DATABASE_URL not set: real-Postgres migration test skipped"
    host = urlsplit(url).hostname or ""
    if host not in _LOOPBACK_HOSTS:
        return f"refusing non-loopback host {host!r}: point PRICEKEEL_TEST_DATABASE_URL at a local scratch Postgres"
    return None


def test_pk41_scratch_url_skip_logic():
    assert "not set" in _skip_reason(None)
    assert "not set" in _skip_reason("")
    assert _skip_reason("postgresql://u:p@ep-x-123.us-east-2.aws.neon.tech/db") is not None
    assert _skip_reason("postgresql://u:p@db.example.com:5432/db") is not None
    assert _skip_reason("postgresql://u:p@10.0.0.5/db") is not None
    for ok in ("postgresql://u@127.0.0.1:5432/postgres",
               "postgresql://u@localhost/postgres",
               "postgresql://u@[::1]:5432/postgres"):
        assert _skip_reason(ok) is None


def test_pk41_database_url_is_never_used(monkeypatch):
    monkeypatch.delenv("PRICEKEEL_TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u@localhost/postgres")
    assert _test_url() is None


@pytest.fixture()
def scratch():
    """A throwaway database created on the configured server and dropped after.
    Refuses a Neon host so this can never touch production."""
    url = _test_url()
    reason = _skip_reason(url)
    if reason:
        pytest.skip(reason)
    psycopg = pytest.importorskip("psycopg")
    parts = urlsplit(url)
    name = "pk41_" + uuid.uuid4().hex[:12]
    admin = psycopg.connect(url, autocommit=True)
    try:
        admin.execute(f'create database "{name}"')
        conn = psycopg.connect(urlunsplit(parts._replace(path="/" + name)), autocommit=True)
    except Exception:
        admin.close()
        raise
    try:
        yield conn
    finally:
        conn.close()
        admin.execute(f'drop database if exists "{name}" with (force)')
        admin.close()


def _run(conn, path: Path):
    conn.execute(path.read_text(encoding="utf-8"))


def _refused(conn, path: Path, fragment: str):
    psycopg = pytest.importorskip("psycopg")
    with pytest.raises(psycopg.errors.RaiseException) as exc:
        _run(conn, path)
    assert "DOWN MIGRATION REFUSED" in str(exc.value)
    assert fragment in str(exc.value)
    conn.execute("rollback")  # the script opened begin; and aborted before commit
    # refusal rolled everything back: nothing dropped
    assert conn.execute("select to_regclass('public.source_connections')").fetchone()[0] is not None
    assert conn.execute(
        "select count(*) from information_schema.columns where table_name='access_codes' and column_name='tenant_ref'"
    ).fetchone()[0] == 1


def _seed_legacy(conn):
    conn.execute(
        "insert into salesforce_connections (customer_ref, org_id, instance_url, access_token_encrypted,"
        " refresh_token_encrypted, last_sync_closed, last_sync_open) values (%s,'00Dxx','https://x.example',%s,%s,3,2)",
        (_CTRL, _CT, _CT),
    )
    conn.execute("insert into salesforce_mappings (customer_ref, mapping) values (%s, '{\"amount\":\"Amount\"}')", (_CTRL,))
    conn.execute("insert into access_codes (code) values ('code-one')")


def _counts(conn):
    return [conn.execute(f"select count(*) from {t}").fetchone()[0]
            for t in ("source_connections", "source_connection_config")]


def test_pk41_up_down_up_on_real_postgres(scratch):
    conn = scratch
    conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    _run(conn, PK41_DOWN)  # strip PK-41 objects: baseline is the pre-PK-41 shape
    assert conn.execute("select to_regclass('public.source_connections')").fetchone()[0] is None
    _seed_legacy(conn)

    _run(conn, PK41_UP)
    first = _counts(conn)
    assert first == [1, 1]
    _run(conn, PK41_UP)  # idempotent
    assert _counts(conn) == first
    assert conn.execute("select tenant_ref from access_codes where code='code-one'").fetchone()[0] == "code-one"
    conn.execute("insert into access_codes (code) values ('code-two')")
    ref = conn.execute("select tenant_ref from access_codes where code='code-two'").fetchone()[0]
    assert re.fullmatch(r"tn_[0-9a-f]{32}", ref)
    assert conn.execute(
        "select last_sync_counts from source_connections where customer_ref=%s", (_CTRL,)
    ).fetchone()[0] == {"closed": 3, "open": 2}

    # the key_id nit: v2 ciphertext (credential or access token) needs a key_id
    psycopg = pytest.importorskip("psycopg")
    ins = ("insert into source_connections (customer_ref, source_system, credential_kind,"
           " access_token_encrypted, credential_encrypted, key_id, instance_url)"
           " values (%s,'salesforce','oauth_refresh',%s,%s,%s,'https://y.example')")
    for tok, cred, key in ((_CT, _CT2, ""), (_CT2, _CT, ""), (_CT2, _CT2, "")):
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(ins, ("bad", tok, cred, key))
    conn.execute(ins, ("good", _CT2, _CT2, "k1"))
    conn.execute("delete from source_connections where customer_ref='good'")

    # refusal 1: a drifted tenant_ref keys data (including competitor_context_sources)
    conn.execute("insert into competitor_context_sources (customer_ref, competitor_name, source_url, source_type) values (%s,'Rival','https://c.example','web')", (ref,))
    _refused(conn, PK41_DOWN, "competitor_context_sources")
    conn.execute("delete from competitor_context_sources where customer_ref=%s", (ref,))

    # refusal 2: non-Salesforce row
    conn.execute(
        "insert into source_connections (customer_ref, source_system, credential_kind, credential_encrypted)"
        " values ('hs','hubspot','oauth_refresh',%s)", (_CT,))
    _refused(conn, PK41_DOWN, "other than salesforce")
    conn.execute("delete from source_connections where customer_ref='hs'")

    # refusal 3: Salesforce row with no legacy match (blocker finding)
    conn.execute(
        "insert into source_connections (customer_ref, source_system, credential_kind, credential_encrypted,"
        " instance_url) values ('post-cutover','salesforce','oauth_refresh',%s,'https://z.example')", (_CT,))
    conn.execute(
        "insert into source_connection_config (customer_ref, source_system, stage_map)"
        " values ('post-cutover','salesforce','{\"Closed Won\":\"won\"}')")
    _refused(conn, PK41_DOWN, "no legacy salesforce_connections match")
    conn.execute("delete from source_connections where customer_ref='post-cutover'")  # cascades config

    # refusal 4: confirmed stage_map / list_price_set on a matched row
    conn.execute("update source_connection_config set stage_map='{\"Closed Won\":\"won\"}' where customer_ref=%s", (_CTRL,))
    _refused(conn, PK41_DOWN, "stage_map or list_price_set")
    conn.execute("update source_connection_config set stage_map='{}', list_price_set='[\"p1\"]' where customer_ref=%s", (_CTRL,))
    _refused(conn, PK41_DOWN, "stage_map or list_price_set")
    conn.execute("update source_connection_config set list_price_set='[]' where customer_ref=%s", (_CTRL,))

    # clean state: down succeeds, legacy data intact, then up again restores
    _run(conn, PK41_DOWN)
    assert conn.execute("select to_regclass('public.source_connections')").fetchone()[0] is None
    assert conn.execute("select count(*) from salesforce_connections").fetchone()[0] == 1
    assert conn.execute("select count(*) from access_codes").fetchone()[0] == 2
    _run(conn, PK41_DOWN)  # rerunnable
    _run(conn, PK41_UP)
    assert _counts(conn) == [1, 1]


# ---------------------------------------------------------------------------
# PK-108: leads.lead_magnet
# ---------------------------------------------------------------------------

PK108_UP = MIGRATIONS_DIR / "2026-11-11-leads-lead-magnet.sql"
PK108_DOWN = MIGRATIONS_DIR / "2026-11-11-leads-lead-magnet.down.sql"
_PK108_CHECK = "check (lead_magnet = '' or lead_magnet ~ '^[a-z][a-z0-9_]{0,31}$')"


def test_pk108_pair_exists_and_sorts_after_source_connections():
    assert PK108_UP.exists() and PK108_DOWN.exists()
    names = [p.name for p in _up_files()]
    assert names == sorted(names)
    assert names.index(PK108_UP.name) > names.index(PK41_UP.name)


def test_pk108_up_adds_one_guarded_column_and_a_named_check():
    code = _code(PK108_UP.read_text(encoding="utf-8").lower())
    assert "add column if not exists lead_magnet text not null default ''" in code
    assert "constraint leads_lead_magnet_format_chk" in code
    assert "conname = 'leads_lead_magnet_format_chk'" in code  # guarded add
    assert _PK108_CHECK in code
    for verb in ("drop ", "truncate", "delete from", "update leads"):
        assert verb not in code, f"up must not use {verb.strip()}"
    assert code.count("add column") == 1


def test_pk108_down_refuses_tagged_leads_before_dropping_exactly_the_up():
    down = PK108_DOWN.read_text(encoding="utf-8").lower()
    assert "down migration refused" in down
    assert "lead_magnet <> ''''" in down
    code = _code(down)
    assert code.index("down migration refused") < code.index("drop constraint")
    assert "alter table leads drop constraint if exists leads_lead_magnet_format_chk;" in code
    assert "alter table leads drop column if exists lead_magnet;" in code
    assert code.count("drop ") == 2
    for forbidden in ("drop table", "truncate", "delete from", "update leads"):
        assert forbidden not in code


def test_pk108_lock_timeout_precedes_lock_and_headers_state_deploy_order():
    for p in (PK108_UP, PK108_DOWN):
        text = p.read_text(encoding="utf-8")
        assert "DEPLOY ORDER" in text
        code = _code(text.lower())
        assert "set local lock_timeout = '5s';" in code
        assert code.index("lock_timeout") < code.index("lock table leads in access exclusive mode;")
    up = PK108_UP.read_text(encoding="utf-8")
    assert "BEFORE the code deploy" in up and "FOUNDER AUTHORISATION" in up


def test_pk108_schema_sql_matches_migration_ddl():
    schema = SCHEMA_SQL.read_text(encoding="utf-8").lower()
    body = _table_body(schema, "leads")
    assert "lead_magnet   text not null default ''" in body
    assert "constraint leads_lead_magnet_format_chk" in body
    assert _PK108_CHECK in body
    cols = _column_names(body)
    # last column, so a migrated database and a fresh schema.sql dump agree
    assert cols[-1] == "lead_magnet" and cols.count("lead_magnet") == 1
    pat = r"comment on column leads\.lead_magnet is\s+('[^']*');"
    up = PK108_UP.read_text(encoding="utf-8").lower()
    assert re.search(pat, schema).group(1) == re.search(pat, up).group(1)


def _pg_dump_schema(url: str, dbname: str) -> str | None:
    import shutil
    import subprocess
    exe = shutil.which("pg_dump")
    if not exe:
        return None
    target = urlunsplit(urlsplit(url)._replace(path="/" + dbname))
    out = subprocess.run([exe, "--schema-only", "--no-owner", "--no-privileges", target],
                         capture_output=True, text=True, check=True).stdout
    return "\n".join(l for l in out.splitlines() if not l.startswith(("--", "\\")) and l.strip())


def test_pk108_up_down_up_on_real_postgres(scratch):
    conn = scratch
    psycopg = pytest.importorskip("psycopg")
    conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    dbname = conn.execute("select current_database()").fetchone()[0]
    fresh_dump = _pg_dump_schema(_test_url(), dbname)

    _run(conn, PK108_DOWN)  # strip PK-108: baseline is the pre-PK-108 shape
    cols = lambda: [r[0] for r in conn.execute(
        "select column_name from information_schema.columns where table_name='leads' order by ordinal_position")]
    assert "lead_magnet" not in cols()
    cols_ins = "(name, company, email, role_title, role_function"
    base = f"insert into leads {cols_ins}) values ('', 'acme.example', %s, '', '')"
    tagged = f"insert into leads {cols_ins}, lead_magnet) values ('', 'x', 'bad@x.example', '', '', %s)"
    conn.execute(base, ("old@acme.example",))

    _run(conn, PK108_UP)
    assert cols()[-1] == "lead_magnet"
    _run(conn, PK108_UP)  # idempotent
    assert cols().count("lead_magnet") == 1
    assert conn.execute("select lead_magnet from leads").fetchall() == [("",)]  # existing row reads ''
    conn.execute(base, ("new@acme.example",))  # old-style insert still works
    conn.execute(tagged, ("margin_audit",))
    assert conn.execute("select count(*) from pg_constraint where conname='leads_lead_magnet_format_chk'"
                        ).fetchone()[0] == 1
    for bad in ("Margin Audit", "a@b.co", "1abc", "x" * 33, "margin-audit"):
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(tagged, (bad,))

    if fresh_dump is not None:  # migrated shape == schema.sql shape, byte for byte
        assert _pg_dump_schema(_test_url(), dbname) == fresh_dump

    # refusal: a tagged lead exists, down must abort and drop nothing
    with pytest.raises(psycopg.errors.RaiseException) as exc:
        _run(conn, PK108_DOWN)
    assert "DOWN MIGRATION REFUSED" in str(exc.value)
    conn.execute("rollback")
    assert "lead_magnet" in cols()
    assert conn.execute("select count(*) from leads").fetchone()[0] == 3

    # once the tag is cleared the down succeeds, loses no rows, and reruns
    conn.execute("update leads set lead_magnet = '' where lead_magnet <> ''")
    _run(conn, PK108_DOWN)
    assert "lead_magnet" not in cols()
    assert conn.execute("select count(*) from leads").fetchone()[0] == 3
    _run(conn, PK108_DOWN)  # rerunnable
    _run(conn, PK108_UP)
    assert cols()[-1] == "lead_magnet"
