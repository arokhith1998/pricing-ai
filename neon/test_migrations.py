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
