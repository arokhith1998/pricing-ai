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
    assert "create unique index" not in schema
