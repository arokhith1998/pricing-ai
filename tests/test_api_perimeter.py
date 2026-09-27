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
    """Every test starts with: no API key set, no LLM keys, empty limiter.

    PRICEKEEL_ENV=dev so the default 'key unset' tests exercise the
    warn-and-allow dev path; the prod fail-closed behavior is tested
    explicitly below by setting PRICEKEEL_ENV to a prod value.
    """
    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("PRICEKEEL_ENV", "dev")
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


# --- 1b. fail-closed auth in production (Finding 2) --------------------------

def test_prod_missing_key_rejects_normal_route(client, monkeypatch):
    # Production (PRICEKEEL_ENV != 'dev') with no API key set must fail closed:
    # a misconfigured prod API is otherwise fully public.
    monkeypatch.setenv("PRICEKEEL_ENV", "production")
    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    r = client.get("/copilot/canonical")
    assert r.status_code == 503
    assert "api key not set" in r.json()["detail"].lower()


def test_prod_missing_key_still_allows_health_and_root(client, monkeypatch):
    # Render's health probe and the bare landing must keep passing.
    monkeypatch.setenv("PRICEKEEL_ENV", "production")
    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_prod_unset_env_treated_as_prod(client, monkeypatch):
    # An unset PRICEKEEL_ENV is production (matches CORS fail-closed default).
    monkeypatch.delenv("PRICEKEEL_ENV", raising=False)
    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    assert client.get("/copilot/canonical").status_code == 503


def test_dev_missing_key_allows(client, monkeypatch):
    # Dev keeps the warn-and-allow behavior for local work.
    monkeypatch.setenv("PRICEKEEL_ENV", "dev")
    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    assert client.get("/copilot/canonical").status_code == 200


def test_prod_with_key_set_uses_normal_auth(client, monkeypatch):
    # Key set in prod: existing 401/200 behavior, not 503.
    monkeypatch.setenv("PRICEKEEL_ENV", "production")
    monkeypatch.setenv("PRICEKEEL_API_KEY", KEY)
    assert client.get("/copilot/canonical").status_code == 401
    assert client.get("/copilot/canonical", headers=AUTH).status_code == 200


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


# --- 2c. /crm/* JSON body size cap (backend-engineer finding 3) --------------

def test_crm_oversize_json_body_rejected_413_before_deserialization(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 1024)
    big_records = [{"opportunity_id": "x" * 200}] * 20  # well over 1KB serialized
    r = client.post("/crm/analyze", json={"records": big_records})
    assert r.status_code == 413
    assert "too large" in r.json()["detail"].lower()


def test_crm_small_json_body_passes_size_middleware(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 1024 * 1024)
    r = client.post("/crm/analyze", json={"records": []})
    # Past the 413 middleware; fails later in pricing.crm on an empty book.
    assert r.status_code != 413


# --- 2b. docs upload per-request caps (Finding 4) ----------------------------

def test_docs_upload_rejects_too_many_files(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_DOCS_FILES_PER_REQUEST", 2)
    files = [("files", (f"f{i}.txt", io.BytesIO(b"hello world"), "text/plain"))
             for i in range(3)]
    r = client.post("/docs/upload", files=files)
    assert r.status_code == 413
    assert "too many files" in r.json()["detail"].lower()


def test_docs_upload_rejects_total_bytes_over_cap(client, monkeypatch):
    # Each file is under the single-file cap, but together they exceed the
    # per-request total-bytes cap.
    monkeypatch.setattr(main, "MAX_DOCS_FILES_PER_REQUEST", 10)
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 1024 * 1024)
    monkeypatch.setattr(main, "MAX_DOCS_TOTAL_BYTES", 1500)
    blob = b"x" * 1000  # under single-file cap
    files = [("files", (f"f{i}.txt", io.BytesIO(blob), "text/plain"))
             for i in range(3)]  # 3000 bytes total > 1500 cap
    r = client.post("/docs/upload", files=files)
    assert r.status_code == 413
    assert "total" in r.json()["detail"].lower()


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
    monkeypatch.setenv("PRICEKEEL_TRUST_PROXY", "1")
    a = {"X-Forwarded-For": "1.1.1.1"}
    b = {"X-Forwarded-For": "2.2.2.2, 10.0.0.1"}  # first value wins
    assert client.post("/summary", json={"policy": 0.15}, headers=a).status_code == 200
    assert client.post("/summary", json={"policy": 0.15}, headers=a).status_code == 429
    # A different caller is not penalised for 1.1.1.1's burn rate.
    assert client.post("/summary", json={"policy": 0.15}, headers=b).status_code == 200


def test_x_forwarded_for_ignored_without_trust_proxy(client, monkeypatch):
    # Without PRICEKEEL_TRUST_PROXY, any caller can set X-Forwarded-For to
    # dodge its own bucket; it must be ignored and the socket peer used
    # instead, so both "callers" below (same test-client socket) share one
    # bucket.
    monkeypatch.delenv("PRICEKEEL_TRUST_PROXY", raising=False)
    monkeypatch.setattr(main, "RATE_LIMITS", {"/summary": (1, 60.0)})
    a = {"X-Forwarded-For": "1.1.1.1"}
    b = {"X-Forwarded-For": "2.2.2.2"}
    assert client.post("/summary", json={"policy": 0.15}, headers=a).status_code == 200
    assert client.post("/summary", json={"policy": 0.15}, headers=b).status_code == 429


def test_rate_limit_keys_on_customer_header_before_ip(client, monkeypatch):
    # Two different IPs, same X-Pricekeel-Customer: one shared bucket.
    monkeypatch.setenv("PRICEKEEL_TRUST_PROXY", "1")
    monkeypatch.setattr(main, "RATE_LIMITS", {"/summary": (1, 60.0)})
    same_customer_a = {"X-Pricekeel-Customer": "acme",
                       "X-Forwarded-For": "1.1.1.1"}
    same_customer_b = {"X-Pricekeel-Customer": "acme",
                       "X-Forwarded-For": "9.9.9.9"}
    other_customer = {"X-Pricekeel-Customer": "globex",
                      "X-Forwarded-For": "1.1.1.1"}
    assert client.post("/summary", json={"policy": 0.15},
                       headers=same_customer_a).status_code == 200
    assert client.post("/summary", json={"policy": 0.15},
                       headers=same_customer_b).status_code == 429
    # A different tenant sharing an IP is not starved by acme's burn rate.
    assert client.post("/summary", json={"policy": 0.15},
                       headers=other_customer).status_code == 200


def test_recommend_rate_limited_same_as_exceptions():
    _, rec_limit, rec_window = main._rate_rule_for("/recommend")
    _, exc_limit, exc_window = main._rate_rule_for("/exceptions")
    assert (rec_limit, rec_window) == (exc_limit, exc_window)


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
    # /recommend gained a rate limit (backend-engineer finding 4); an
    # unrelated, genuinely unmetered path stays None.
    assert main._rate_rule_for("/recommend") is not None
    assert main._rate_rule_for("/deals") is None


def test_llm_backed_routes_have_rate_limits():
    # Audit P2 #2: /copilot/canonical (POST) and /map-columns are LLM-backed
    # like /ask, /summary, and /matching/, but were missing from RATE_LIMITS.
    assert main._rate_rule_for("/copilot/canonical") is not None
    assert main._rate_rule_for("/map-columns") is not None


# --- 3b. /matching/compare URL cap (audit P2 #1) ------------------------------

def test_compare_rejects_too_many_urls_without_calling_engine(client, monkeypatch):
    def _must_not_be_called(*_args, **_kwargs):
        raise AssertionError("matching_mod.compare must not run past the URL cap")

    monkeypatch.setattr(main.matching_mod, "compare", _must_not_be_called)
    urls = [f"https://competitor{i}.example/pricing" for i in range(9)]
    r = client.post(
        "/matching/compare",
        json={"my_url": "https://mine.example/pricing", "competitor_urls": urls},
    )
    assert r.status_code == 422


def test_compare_allows_urls_at_the_cap(client, monkeypatch):
    calls = {"n": 0}

    def _fake_compare(my_url, competitor_urls):
        calls["n"] += 1
        return type("R", (), {"to_dict": lambda self: {"ok": True}})()

    monkeypatch.setattr(main.matching_mod, "compare", _fake_compare)
    # my_url (1) + 7 competitors = 8, exactly MAX_COMPARE_URLS.
    urls = [f"https://competitor{i}.example/pricing" for i in range(7)]
    r = client.post(
        "/matching/compare",
        json={"my_url": "https://mine.example/pricing", "competitor_urls": urls},
    )
    assert r.status_code == 200
    assert calls["n"] == 1


# --- 4. load_report in the diagnostic payload ----------------------------------

# --- 5. mixed-currency book: 422 with the blocker text, not a bare 500 -------
# (silent-failure-hunter finding 2, 2026-09-26: CurrencyBlockedError reached
# no exception handler in api/main.py, so this used to be a 500 with the
# per-currency row counts lost.)

def _mixed_currency_csv_body(n_usd: int = 20, n_eur: int = 15) -> bytes:
    rows = ["opportunity_id,account_name,outcome,created_date,close_date,"
            "segment,product_tier,value_metric,list_acv,booked_acv"]
    for i in range(n_usd):
        rows.append(f"OPP-U{i:03d},Acct {i},closed_won,2025-01-01,2025-02-15,"
                    f"SMB,Pro,hybrid,$100000,$90000")
    for i in range(n_eur):
        rows.append(f"OPP-E{i:03d},Acct {100 + i},closed_won,2025-01-01,"
                    f"2025-02-15,SMB,Pro,hybrid,€100000,€90000")
    return ("\n".join(rows)).encode("utf-8")


def test_diagnostic_mixed_currency_returns_422_not_500(client):
    r = client.post(
        "/diagnostic",
        files={"file": ("mixed.csv", io.BytesIO(_mixed_currency_csv_body()), "text/csv")},
        data={"policy": "0.15"},
    )
    assert r.status_code == 422
    body = r.json()
    assert "USD" in body["detail"] and "EUR" in body["detail"]
    # per-currency row counts survive onto the wire (not lost to a bare 500).
    assert "20 row" in body["detail"] and "15 row" in body["detail"]
    assert any("USD" in b and "EUR" in b for b in body.get("blockers", []))


def _iso_only_mixed_currency_csv_body(n_usd: int = 20, n_eur: int = 15) -> bytes:
    """A Salesforce CurrencyIsoCode-style export: an explicit ISO currency
    column, no $/€ symbols anywhere."""
    rows = ["opportunity_id,account_name,outcome,created_date,close_date,"
            "segment,product_tier,value_metric,list_acv,booked_acv,currency"]
    for i in range(n_usd):
        rows.append(f"OPP-U{i:03d},Acct {i},closed_won,2025-01-01,2025-02-15,"
                    f"SMB,Pro,hybrid,100000,90000,USD")
    for i in range(n_eur):
        rows.append(f"OPP-E{i:03d},Acct {100 + i},closed_won,2025-01-01,"
                    f"2025-02-15,SMB,Pro,hybrid,100000,90000,EUR")
    return ("\n".join(rows)).encode("utf-8")


def test_diagnostic_mixed_currency_iso_column_only_returns_422(client):
    """No currency symbols anywhere, just an explicit ISO code column: must
    be blocked exactly like a symbol-based mix, not silently summed."""
    r = client.post(
        "/diagnostic",
        files={"file": ("iso-only.csv",
                        io.BytesIO(_iso_only_mixed_currency_csv_body()),
                        "text/csv")},
        data={"policy": "0.15"},
    )
    assert r.status_code == 422
    body = r.json()
    assert "USD" in body["detail"] and "EUR" in body["detail"]


def test_diagnostic_missing_required_columns_returns_422_not_500(client):
    """Any other SchemaError (not just CurrencyBlockedError) must reach the
    ingest_mod.SchemaError handler as a 422, not fall through to a bare 500."""
    body = b"a,b,c\n1,2,3\n"
    r = client.post(
        "/diagnostic",
        files={"file": ("bad.csv", io.BytesIO(body), "text/csv")},
        data={"policy": "0.15"},
    )
    assert r.status_code == 422
    assert "missing" in r.json()["detail"].lower()


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
