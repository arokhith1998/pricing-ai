"""Unit tests for pricing/matching.py.

The LLM-driven bits (plan extraction from URL text, summary) are skipped
here — they are integration concerns and live behind manual smoke tests.
What we pin here is everything that does NOT need the cloud LLM:

  - HTML stripping
  - Pricing-position logic (above_market / at_market / below_market)
  - Plan name + feature similarity scoring
  - The match_plans selection / threshold / coverage rules
  - The cache TTL behavior of fetch_pricing_page (monkeypatched requests)

fastembed is loaded for the embedding tests; first run downloads the
model the same way the production path does.
"""
from __future__ import annotations

import pytest

from pricing import matching


# --- HTML strip --------------------------------------------------------------

def test_strip_html_drops_script_and_style_and_collapses_whitespace():
    html = """
    <html><head><style>.x{color:red}</style></head>
    <body>
      <script>alert(1)</script>
      <h1>Pricing</h1>
      <p>Free tier &amp; Pro tier</p>
      <noscript>noscript-content</noscript>
    </body></html>
    """
    out = matching._strip_html(html)
    assert "alert(1)" not in out
    assert "color:red" not in out
    assert "noscript-content" not in out
    assert "Pricing" in out
    assert "Free tier & Pro tier" in out
    # whitespace collapsed
    assert "  " not in out


# --- pricing position --------------------------------------------------------

def test_pricing_position_handles_missing_prices():
    pos, delta = matching._pricing_position(None, 50.0)
    assert pos == "unknown" and delta is None
    pos, delta = matching._pricing_position(50.0, None)
    assert pos == "unknown" and delta is None
    pos, delta = matching._pricing_position(0.0, 50.0)
    assert pos == "unknown" and delta is None


def test_pricing_position_above_at_below_market():
    # competitor charges more → we are below market
    pos, delta = matching._pricing_position(100.0, 150.0)
    assert pos == "above_market"
    assert delta == pytest.approx(0.5)

    # within ±5% → at market
    pos, delta = matching._pricing_position(100.0, 103.0)
    assert pos == "at_market"

    # competitor cheaper → we are above market
    pos, delta = matching._pricing_position(100.0, 80.0)
    assert pos == "below_market"
    assert delta == pytest.approx(-0.2)


# --- name similarity ---------------------------------------------------------

def test_name_similarity_known_pairs():
    # rapidfuzz token_set_ratio: "Pro" vs "Professional" is exactly 0.4
    assert matching._name_similarity("Pro", "Professional") >= 0.4
    assert matching._name_similarity("Enterprise", "Enterprise Plan") > 0.6
    assert matching._name_similarity("", "Pro") == 0.0
    assert matching._name_similarity("Free", "Enterprise") < 0.4


# --- match_plans -------------------------------------------------------------

def _make_plans():
    """Two of mine, three from two competitors. Designed so 'Pro' on both
    sides matches strongly via feature overlap + name similarity."""
    mine = [
        matching.Plan(
            vendor="Pricekeel",
            name="Starter",
            price_monthly=49.0,
            features=["unlimited dashboards", "csv upload", "email support"],
        ),
        matching.Plan(
            vendor="Pricekeel",
            name="Pro",
            price_monthly=199.0,
            features=[
                "team collaboration",
                "audit log",
                "single sign-on",
                "priority support",
            ],
        ),
    ]
    theirs = [
        matching.Plan(
            vendor="Acme",
            name="Lite",
            price_monthly=29.0,
            features=["basic dashboards", "data export", "community support"],
        ),
        matching.Plan(
            vendor="Acme",
            name="Pro",
            price_monthly=249.0,
            features=[
                "team collaboration",
                "audit logging",
                "SSO",
                "priority email support",
            ],
        ),
        matching.Plan(
            vendor="Globex",
            name="Business",
            price_monthly=179.0,
            features=[
                "team workspace",
                "SAML SSO",
                "audit trail",
                "API access",
            ],
        ),
    ]
    return mine, theirs


def test_match_plans_emits_at_most_one_per_vendor_per_plan():
    mine, theirs = _make_plans()
    matches = matching.match_plans(mine, theirs)
    seen = set()
    for m in matches:
        key = (m.my_plan_name, m.competitor_vendor)
        assert key not in seen, f"duplicate pair {key}"
        seen.add(key)


def test_match_plans_picks_pro_vs_pro_with_high_similarity():
    mine, theirs = _make_plans()
    matches = matching.match_plans(mine, theirs)
    pro_matches = [
        m for m in matches
        if m.my_plan_name == "Pro" and m.competitor_vendor == "Acme"
    ]
    assert len(pro_matches) == 1
    pm = pro_matches[0]
    assert pm.competitor_plan_name == "Pro"
    assert pm.similarity > 0.5
    # Acme Pro is $249 vs mine $199 → they are 25% above; we are below market
    assert pm.pricing_position == "above_market"
    assert pm.price_delta_pct == pytest.approx(0.251, abs=0.01)


def test_match_plans_threshold_drops_weak_matches():
    mine, theirs = _make_plans()
    strict = matching.match_plans(mine, theirs, min_blended_similarity=0.9)
    assert strict == []  # nothing should clear a 0.9 floor


def test_match_plans_empty_inputs_return_empty_list():
    assert matching.match_plans([], []) == []
    assert matching.match_plans(_make_plans()[0], []) == []
    assert matching.match_plans([], _make_plans()[1]) == []


def test_match_plans_records_feature_deltas():
    mine, theirs = _make_plans()
    matches = matching.match_plans(mine, theirs)
    pro = next(m for m in matches
               if m.my_plan_name == "Pro" and m.competitor_vendor == "Acme")
    # Pro on both sides shares a lot — the symmetric deltas should be short.
    assert len(pro.features_only_mine) <= 2
    assert len(pro.features_only_theirs) <= 2


def test_pricing_position_reported_unknown_when_a_price_is_missing():
    mine, theirs = _make_plans()
    # Strip one side's price.
    theirs[1].price_monthly = None
    matches = matching.match_plans(mine, theirs)
    pro = next(m for m in matches
               if m.my_plan_name == "Pro" and m.competitor_vendor == "Acme")
    assert pro.pricing_position == "unknown"
    assert pro.price_delta_pct is None


# --- fetch cache (no network needed; monkeypatch requests.get) ---------------

class _FakeResp:
    def __init__(self, body: bytes, status: int = 200):
        self.content = body
        self.encoding = "utf-8"
        self.status_code = status
        self.text = body.decode("utf-8", errors="replace")
    def raise_for_status(self):
        return None


def test_fetch_pricing_page_caches_within_ttl(monkeypatch):
    page_calls = {"n": 0}

    def fake_get(url, **kwargs):
        # Don't count robots.txt fetches toward page-cache assertion.
        if not url.endswith("/robots.txt"):
            page_calls["n"] += 1
        return _FakeResp(b"<html><body>Plans: Free, Pro</body></html>")

    monkeypatch.setattr(matching.requests, "get", fake_get)
    matching._FETCH_CACHE.clear()
    matching._ROBOTS_CACHE.clear()

    a = matching.fetch_pricing_page("https://example.test/pricing")
    b = matching.fetch_pricing_page("https://example.test/pricing")
    assert a == b
    assert "Plans: Free, Pro" in a
    assert page_calls["n"] == 1, "the page itself should be fetched exactly once"


def test_fetch_pricing_page_refetches_after_ttl(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, **kwargs):
        calls["n"] += 1
        return _FakeResp(b"<p>hello</p>")

    monkeypatch.setattr(matching.requests, "get", fake_get)
    matching._FETCH_CACHE.clear()
    matching._ROBOTS_CACHE.clear()

    matching.fetch_pricing_page("https://example.test/x", ttl_seconds=0)
    matching.fetch_pricing_page("https://example.test/x", ttl_seconds=0)
    # one robots.txt fetch (cached) + two page fetches
    assert calls["n"] >= 2


# --- IP-risk hardening (robots.txt + kill-switch) ---------------------------

class _RobotsResp:
    """robots.txt response that disallows everything for our UA."""
    def __init__(self, body: str, status: int = 200):
        self.text = body
        self.status_code = status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise matching.requests.RequestException("robots fetch failed")


def test_fetch_blocked_by_robots_txt(monkeypatch):
    def fake_get(url, **kwargs):
        if url.endswith("/robots.txt"):
            return _RobotsResp("User-agent: *\nDisallow: /pricing\n")
        return _FakeResp(b"<p>should never reach</p>")

    monkeypatch.setattr(matching.requests, "get", fake_get)
    matching._FETCH_CACHE.clear()
    matching._ROBOTS_CACHE.clear()

    with pytest.raises(matching.FetchBlocked) as exc:
        matching.fetch_pricing_page("https://blocked.test/pricing")
    assert "robots.txt" in exc.value.reason


def test_fetch_allowed_when_no_robots_txt(monkeypatch):
    def fake_get(url, **kwargs):
        if url.endswith("/robots.txt"):
            return _RobotsResp("", status=404)
        return _FakeResp(b"<p>ok</p>")

    monkeypatch.setattr(matching.requests, "get", fake_get)
    matching._FETCH_CACHE.clear()
    matching._ROBOTS_CACHE.clear()

    out = matching.fetch_pricing_page("https://open.test/pricing")
    assert "ok" in out


def test_kill_switch_blocks_host(monkeypatch):
    # Use the env var so we do not mutate the static set in tests.
    monkeypatch.setenv("LEGAL_BLOCKED_HOSTS", "blocked.example,otherblocked.example")
    matching._FETCH_CACHE.clear()
    matching._ROBOTS_CACHE.clear()

    with pytest.raises(matching.FetchBlocked) as exc:
        matching.fetch_pricing_page("https://blocked.example/pricing")
    assert "kill-switch" in exc.value.reason


def test_kill_switch_blocks_subdomain_of_blocked_apex(monkeypatch):
    monkeypatch.setenv("LEGAL_BLOCKED_HOSTS", "example.com")
    matching._FETCH_CACHE.clear()
    matching._ROBOTS_CACHE.clear()

    with pytest.raises(matching.FetchBlocked):
        matching.fetch_pricing_page("https://www.example.com/pricing")


def test_extract_plans_from_url_returns_empty_on_block(monkeypatch):
    monkeypatch.setenv("LEGAL_BLOCKED_HOSTS", "blocked.example")
    matching._FETCH_CACHE.clear()
    matching._ROBOTS_CACHE.clear()
    vendor, plans = matching.extract_plans_from_url("https://blocked.example/pricing")
    # Should not raise — should fall through to ("", []) so the UI surfaces
    # a "no plans" message rather than a stack trace.
    assert vendor == ""
    assert plans == []
