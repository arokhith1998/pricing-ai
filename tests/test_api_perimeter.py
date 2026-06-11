"""API perimeter tests (CTO security review, 2026-06-11).

Covers the four perimeter controls in api/main.py:
  1. shared-secret auth (X-Pricekeel-Key) with /health and / exempt
  2. upload size cap (Content-Length middleware check + byte-read backstop)
  3. per-IP sliding-window rate limiting with Retry-After
  4. load_report shipped through the /diagnostic payload

All offline and deterministic: LLM keys are stripped so nothing calls a
provider, and limiter state is reset around every test.
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

from api import main

ROOT = Path(__file__).resolve().parents[1]
DEMO_CSV = ROOT / "data" / "synthetic" / "deals.csv"

KEY = "test-secret-key"
AUTH = {"X-Pricekeel-Key": KEY}


@pytest.fixture(autouse=True)
def _clean_perimeter(monkeypatch):
    """Every test starts with: no API key set, no LLM keys, empty limiter."""
    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    main._rate_state_reset()
    yield
    main._rate_state_reset()


@pytest.fixture()
def client():
    return TestClient(main.app)


# --- 1. shared-secret auth ---------------------------------------------------

def test_open_when_key_unset(client):
    assert client.get("/copilot/canonical").status_code == 200


def test_auth_rejects_missing_header(client, monkeypatch):
    monkeypatch.setenv("PRICEKEEL_API_KEY", KEY)
    r = client.get("/copilot/canonical")
    assert r.status_code == 401


def test_auth_rejects_wrong_key(client, monkeypatch):
    monkeypatch.setenv("PRICEKEEL_API_KEY", KEY)
    r = client.get("/copilot/canonical", headers={"X-Pricekeel-Key": "nope"})
    assert r.status_code == 401


def test_auth_accepts_correct_key(client, monkeypatch):
    monkeypatch.setenv("PRICEKEEL_API_KEY", KEY)
    r = client.get("/copilot/canonical", headers=AUTH)
    assert r.status_code == 200
    assert "questions" in r.json()


def test_health_and_root_exempt_from_auth(client, monkeypatch):
    monkeypatch.setenv("PRICEKEEL_API_KEY", KEY)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_auth_applies_to_post_endpoints(client, monkeypatch):
    monkeypatch.setenv("PRICEKEEL_API_KEY", KEY)
    assert client.post("/summary", json={"policy": 0.15}).status_code == 401
    r = client.post("/summary", json={"policy": 0.15}, headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"enabled": False, "summary": None}  # no LLM keys


# --- 2. upload size cap --------------------------------------------------------

def test_oversize_upload_rejected_413(client, monkeypatch):
    # Shrink the cap so the test does not ship 25MB through the stack.
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 1024)
    body = b"a,b,c\n" * 1000  # ~6KB multipart body, over the 1KB cap
    r = client.post(
        "/diagnostic",
        files={"file": ("deals.csv", io.BytesIO(body), "text/csv")},
    )
    assert r.status_code == 413
    assert "too large" in r.json()["detail"].lower()


def test_small_upload_passes_size_middleware(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 1024 * 1024)
    # Tiny but schema-less file: must get past the 413 middleware and fail
    # later in ingest/validation (i.e. NOT with 413).
    r = client.post(
        "/map-headers",
        files={"file": ("t.csv", io.BytesIO(b"a,b,c\n1,2,3\n"), "text/csv")},
    )
    assert r.status_code != 413


def test_read_capped_backstop_rejects_lying_content_length(monkeypatch):
    # The backstop fires on actual bytes even if Content-Length lied/missing.
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 100)
    up = UploadFile(file=io.BytesIO(b"x" * 200), filename="big.csv")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main._read_capped(up))
    assert exc.value.status_code == 413

    up_ok = UploadFile(file=io.BytesIO(b"x" * 50), filename="small.csv")
    assert asyncio.run(main._read_capped(up_ok)) == b"x" * 50


# --- 3. rate limiting ----------------------------------------------------------

def test_rate_limit_429_with_retry_after(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMITS", {"/summary": (2, 60.0)})
    for _ in range(2):
        assert client.post("/summary", json={"policy": 0.15}).status_code == 200
    r = client.post("/summary", json={"policy": 0.15})
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1


def test_rate_limit_is_per_ip_via_x_forwarded_for(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMITS", {"/summary": (1, 60.0)})
    a = {"X-Forwarded-For": "1.1.1.1"}
    b = {"X-Forwarded-For": "2.2.2.2, 10.0.0.1"}  # first value wins
    assert client.post("/summary", json={"policy": 0.15}, headers=a).status_code == 200
    assert client.post("/summary", json={"policy": 0.15}, headers=a).status_code == 429
    # A different caller is not penalised for 1.1.1.1's burn rate.
    assert client.post("/summary", json={"policy": 0.15}, headers=b).status_code == 200


def test_rate_limit_window_slides(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMITS", {"/summary": (1, 60.0)})
    assert client.post("/summary", json={"policy": 0.15}).status_code == 200
    assert client.post("/summary", json={"policy": 0.15}).status_code == 429
    # Age the recorded timestamp past the window: limiter must allow again.
    for bucket in main._RATE_BUCKETS.values():
        for i in range(len(bucket)):
            bucket[i] -= 61.0
    assert client.post("/summary", json={"policy": 0.15}).status_code == 200


def test_unlimited_endpoints_not_rate_limited(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMITS", {"/summary": (1, 60.0)})
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_matching_prefix_rule_matches_subpaths():
    assert main._rate_rule_for("/matching/compare") is not None
    assert main._rate_rule_for("/matching/competitor") is not None
    assert main._rate_rule_for("/recommend") is None


# --- 4. load_report in the diagnostic payload ----------------------------------

def test_diagnostic_payload_contains_load_report(client):
    with open(DEMO_CSV, "rb") as fh:
        r = client.post(
            "/diagnostic",
            files={"file": ("deals.csv", fh, "text/csv")},
            data={"policy": "0.15"},
        )
    assert r.status_code == 200
    payload = r.json()
    assert "load_report" in payload
    rep = payload["load_report"]
    assert rep["rows_kept"] > 0
    assert isinstance(rep["summary"], str) and "closed deals" in rep["summary"]
    # Must round-trip as plain JSON (no numpy leftovers): already proven by
    # r.json(), but assert the disclosure fields the dashboard renders.
    for field in ("rows_read", "excluded_open", "exact_duplicates_dropped",
                  "unmapped_columns", "notes"):
        assert field in rep
