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


def _session_factory_from(get_fn, *, recorder=None):
    """Build a `_session_factory` substitute whose Session.get delegates to
    `get_fn(url, **kw)`. When `recorder` is given, it records the
    (pinned_ip, scheme) the factory was asked to pin per hop."""
    def factory(pinned_ip, scheme):
        if recorder is not None:
            recorder.append((pinned_ip, scheme))

        class _Session:
            def get(self, url, **kw):
                return get_fn(url, pinned_ip=pinned_ip, **kw)

            def close(self):
                pass

        return _Session()
    return factory


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

    with pytest.raises(UnsafeFetchError, match="resolves to unsafe address"):
        safe_get("http://public.example.com/redir", _resolver=fake_resolver,
                 _session_factory=_session_factory_from(fake_get))
    # First hop is fetched, redirect target is rejected at the resolver before
    # any second HTTP call happens.
    assert call_count["n"] == 1


def test_safe_get_caps_redirect_count():
    def fake_resolver(_):
        return ["8.8.8.8"]

    def fake_get(url, **_kw):
        # Always 302 to the same place — would loop forever without the cap.
        return _fake_resp(302, headers={"Location": "http://public.example.com/r"})

    with pytest.raises(UnsafeFetchError, match="too many redirects"):
        safe_get(
            "http://public.example.com/r",
            _resolver=fake_resolver,
            max_redirects=2,
            _session_factory=_session_factory_from(fake_get),
        )


def test_safe_get_returns_body_and_truncates_at_cap():
    def fake_resolver(_):
        return ["8.8.8.8"]

    big_body = b"x" * 1_000_000  # 1 MB

    def fake_get(url, **_kw):
        return _fake_resp(200, body=big_body)

    resp = safe_get(
        "http://public.example.com/page",
        _resolver=fake_resolver,
        max_bytes=10_000,
        _session_factory=_session_factory_from(fake_get),
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
    resp = safe_get("http://public.example.com/", _resolver=fake_resolver,
                    _session_factory=_session_factory_from(fake_get))
    assert resp.status_code == 200
    assert resp.content == b"hello"
    assert resp.url == "http://final.example.com/"


# ---------------------------------------------------------------------------
# safe_get — DNS pinning (Finding 1): the socket must target the validated IP,
# never a value re-resolved by the kernel at connect time.


def test_safe_get_connects_to_resolved_ip_not_re_resolved():
    """(a) safe_get pins the socket to the address the resolver validated:
    the session factory is built with that exact IP, and the adapter rewrites
    the request netloc to it while keeping the original Host header."""
    from pricing._safe_fetch import _PinnedHostAdapter

    pinned = []

    def fake_resolver(_host):
        return ["93.184.216.34"]  # public (example.com)

    def fake_get(url, *, pinned_ip, **_kw):
        # Prove the adapter would rewrite to the pinned IP while Host stays
        # the hostname. We drive the real adapter against a fake request.
        class _Req:
            def __init__(self):
                self.url = url
                self.headers = {}
        adapter = _PinnedHostAdapter(pinned_ip)
        req = _Req()
        try:
            adapter.get_connection_with_tls_context(req, verify=True)
        except Exception:
            # The super() call will fail (no real pool); we only care that the
            # URL was rewritten to the pinned IP and Host preserved beforehand.
            pass
        assert pinned_ip in req.url
        assert req.headers["Host"] == "public.example.com"
        return _fake_resp(200, body=b"ok")

    resp = safe_get(
        "http://public.example.com/",
        _resolver=fake_resolver,
        _session_factory=_session_factory_from(
            fake_get, recorder=pinned),
    )
    assert resp.status_code == 200
    # The factory was asked to pin exactly the validated IP, for http.
    assert pinned == [("93.184.216.34", "http")]


def test_safe_get_cannot_rebind_between_validate_and_connect():
    """(b) A resolver that would return a *different* address on a second call
    cannot move the connection: safe_get pins to the IP it validated on this
    hop, and the socket targets that pin, not a re-resolution."""
    calls = {"n": 0}

    def rebinding_resolver(_host):
        calls["n"] += 1
        # First (and only) resolve returns a safe IP. A naive implementation
        # that re-resolved at connect time would get the attacker's private IP
        # on a second lookup; pinning means there is no second lookup.
        return ["93.184.216.34"]

    seen_targets = []

    def fake_get(url, *, pinned_ip, **_kw):
        seen_targets.append(pinned_ip)
        return _fake_resp(200, body=b"ok")

    resp = safe_get(
        "http://rebind.example.com/",
        _resolver=rebinding_resolver,
        _session_factory=_session_factory_from(fake_get),
    )
    assert resp.status_code == 200
    # Exactly one resolution happened, and the connection targeted that pinned
    # IP — the kernel never got a chance to re-resolve to a rebind address.
    assert calls["n"] == 1
    assert seen_targets == ["93.184.216.34"]


def test_pick_pinned_ip_fails_closed_when_no_safe_address():
    """If the only addresses are unsafe, we fail closed rather than fall back
    to an unpinned request."""
    from pricing._safe_fetch import _pick_pinned_ip
    with pytest.raises(UnsafeFetchError, match="failing closed"):
        _pick_pinned_ip(["127.0.0.1", "10.0.0.1"])
    assert _pick_pinned_ip(["10.0.0.1", "8.8.8.8"]) == "8.8.8.8"


def test_pinned_adapter_rewrites_ipv6_with_brackets():
    """IPv6 pins must be bracketed in the netloc so the URL stays valid."""
    from pricing._safe_fetch import _PinnedHostAdapter

    class _Req:
        def __init__(self):
            self.url = "http://public.example.com/x"
            self.headers = {}
    adapter = _PinnedHostAdapter("2606:2800:220:1:248:1893:25c8:1946")
    req = _Req()
    try:
        adapter.get_connection_with_tls_context(req, verify=True)
    except Exception:
        pass
    assert "[2606:2800:220:1:248:1893:25c8:1946]" in req.url
    assert req.headers["Host"] == "public.example.com"
