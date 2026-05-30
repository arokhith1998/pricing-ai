"""Tests for the SSRF-hardened HTTP GET used by pricing.matching.

These cover the actual attacks the launch-readiness review flagged:
  * Direct IP literals in the unsafe ranges (loopback, link-local AWS
    metadata, RFC1918, IPv6 ::1).
  * Hostnames that resolve to private IPs (e.g. localhost.example.com).
  * Redirect chains that hop from a public host to a private IP.
  * Redirect-loop / over-cap.
  * Non-http schemes.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from pricing._safe_fetch import (
    UnsafeFetchError,
    _is_unsafe_ip,
    safe_get,
)


# ---------------------------------------------------------------------------
# _is_unsafe_ip


@pytest.mark.parametrize("addr", [
    "127.0.0.1",          # IPv4 loopback
    "127.5.5.5",          # IPv4 loopback range
    "10.0.0.1",           # RFC1918
    "172.16.0.1",         # RFC1918
    "192.168.1.1",        # RFC1918
    "169.254.169.254",    # AWS / GCP metadata (link-local)
    "::1",                # IPv6 loopback
    "fc00::1",            # IPv6 ULA (private)
    "fe80::1",            # IPv6 link-local
    "0.0.0.0",            # unspecified
    "224.0.0.1",          # multicast
])
def test_is_unsafe_ip_rejects(addr):
    assert _is_unsafe_ip(addr) is True


@pytest.mark.parametrize("addr", [
    "8.8.8.8",            # public
    "1.1.1.1",            # public
    "151.101.0.0",        # public CDN
])
def test_is_unsafe_ip_allows_public(addr):
    assert _is_unsafe_ip(addr) is False


def test_is_unsafe_ip_rejects_garbage():
    # Anything we can't parse is treated as unsafe — don't let the request
    # proceed on an address we don't understand.
    assert _is_unsafe_ip("not-an-ip") is True
    assert _is_unsafe_ip("") is True


# ---------------------------------------------------------------------------
# safe_get — scheme + hostname + IP-range guards


def test_safe_get_refuses_non_http_scheme():
    with pytest.raises(UnsafeFetchError, match="refusing scheme"):
        safe_get("file:///etc/passwd")
    with pytest.raises(UnsafeFetchError, match="refusing scheme"):
        safe_get("ftp://example.com/")


def test_safe_get_refuses_hostname_that_resolves_to_private_ip():
    # Simulate a hostname that DNS-resolves to 127.0.0.1 (the canonical
    # DNS-rebinding / localhost-attack pattern).
    def fake_resolver(host):
        if host == "localhost.example.com":
            raise UnsafeFetchError(
                "hostname 'localhost.example.com' resolves to unsafe address '127.0.0.1'"
            )
        return ["8.8.8.8"]

    with pytest.raises(UnsafeFetchError, match="resolves to unsafe address"):
        safe_get("http://localhost.example.com/x", _resolver=fake_resolver)


def test_safe_get_refuses_aws_metadata_url():
    # Direct IP literal — _is_unsafe_ip catches link-local.
    def fake_resolver(host):
        # IP literal still gets resolved by getaddrinfo; emulate that.
        if host == "169.254.169.254":
            raise UnsafeFetchError(
                "hostname '169.254.169.254' resolves to unsafe address '169.254.169.254'"
            )
        return ["8.8.8.8"]
    with pytest.raises(UnsafeFetchError):
        safe_get(
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            _resolver=fake_resolver,
        )


# ---------------------------------------------------------------------------
# safe_get — redirect handling


def _fake_resp(status, headers=None, body=b""):
    """Minimal stand-in for a requests.Response we read in tests."""
    class _Resp:
        status_code = status
        is_redirect = 300 <= status < 400 and "Location" in (headers or {})
        is_permanent_redirect = status in (301, 308)
        encoding = "utf-8"
        def __init__(self):
            self.headers = headers or {}
            self._body = body
        def iter_content(self, chunk_size=16384):
            yield self._body
        def close(self):
            pass
    return _Resp()


def test_safe_get_blocks_redirect_to_private_ip():
    # A public host that 302s to localhost — the second-hop resolver check
    # must catch it.
    resolved_for = {"public.example.com": False, "localhost.example.com": True}

    def fake_resolver(host):
        if resolved_for.get(host, False):
            raise UnsafeFetchError(f"hostname '{host}' resolves to unsafe address")
        return ["8.8.8.8"]

    call_count = {"n": 0}

    def fake_get(url, **_kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_resp(302, headers={"Location": "http://localhost.example.com/"})
        return _fake_resp(200, body=b"should never reach here")

    with patch("pricing._safe_fetch.requests.get", side_effect=fake_get):
        with pytest.raises(UnsafeFetchError, match="resolves to unsafe address"):
            safe_get("http://public.example.com/redir", _resolver=fake_resolver)
    # First hop is fetched, redirect target is rejected at the resolver before
    # any second HTTP call happens.
    assert call_count["n"] == 1


def test_safe_get_caps_redirect_count():
    def fake_resolver(_):
        return ["8.8.8.8"]

    def fake_get(url, **_kw):
        # Always 302 to the same place — would loop forever without the cap.
        return _fake_resp(302, headers={"Location": "http://public.example.com/r"})

    with patch("pricing._safe_fetch.requests.get", side_effect=fake_get):
        with pytest.raises(UnsafeFetchError, match="too many redirects"):
            safe_get(
                "http://public.example.com/r",
                _resolver=fake_resolver,
                max_redirects=2,
            )


def test_safe_get_returns_body_and_truncates_at_cap():
    def fake_resolver(_):
        return ["8.8.8.8"]

    big_body = b"x" * 1_000_000  # 1 MB

    def fake_get(url, **_kw):
        return _fake_resp(200, body=big_body)

    with patch("pricing._safe_fetch.requests.get", side_effect=fake_get):
        resp = safe_get(
            "http://public.example.com/page",
            _resolver=fake_resolver,
            max_bytes=10_000,
        )
    assert resp.status_code == 200
    assert len(resp.content) == 10_000


def test_safe_get_returns_through_one_redirect_to_public():
    def fake_resolver(_):
        return ["8.8.8.8"]
    seq = iter([
        _fake_resp(302, headers={"Location": "http://final.example.com/"}),
        _fake_resp(200, body=b"hello"),
    ])
    def fake_get(url, **_kw):
        return next(seq)
    with patch("pricing._safe_fetch.requests.get", side_effect=fake_get):
        resp = safe_get("http://public.example.com/", _resolver=fake_resolver)
    assert resp.status_code == 200
    assert resp.content == b"hello"
    assert resp.url == "http://final.example.com/"
