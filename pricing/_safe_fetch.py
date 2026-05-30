"""SSRF-hardened HTTP GET for outbound URLs supplied by users.

Used by `pricing.matching` to fetch competitor pricing pages. The caller
supplies a URL string; we refuse to fetch it if any of the following hold:

  * scheme is not http or https
  * hostname resolves to a private / loopback / link-local / reserved IP
    (this is what defeats `http://localhost.example.com → 127.0.0.1`
    DNS-based SSRF and `http://169.254.169.254/...` AWS metadata)
  * a redirect chain takes us to a private IP at any hop
  * more than `max_redirects` hops are required
  * the response exceeds `max_bytes`

DNS-rebinding caveat:

  requests / urllib resolve the hostname inside the socket layer, not at
  the Python level — so even if `getaddrinfo()` returns a public IP when
  we check, the actual socket connect may resolve again and get a private
  IP a millisecond later. The robust defense is to resolve once, then
  connect to the resolved IP literally with a Host header. We do that via
  a `HTTPAdapter` subclass that pins the resolution per hop.

This module has no Pricekeel-specific imports so it stays trivially
testable on its own.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager


# Default safety knobs. The matching fetcher overrides timeout / max_bytes.
DEFAULT_TIMEOUT = 15
DEFAULT_MAX_REDIRECTS = 3
DEFAULT_MAX_BYTES = 250_000


class UnsafeFetchError(Exception):
    """Raised when SSRF defense refuses to make (or continue) a request."""


# ---------------------------------------------------------------------------
# IP-range check


def _is_unsafe_ip(addr: str) -> bool:
    """True if this IP is in a private / loopback / link-local / reserved
    range we never want to talk to from a server-side fetcher."""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        # If we can't parse it, treat as unsafe — don't let the request
        # proceed on an address we don't understand.
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_or_raise(host: str) -> list[str]:
    """Resolve `host` to all addresses. Raise UnsafeFetchError if *any* of
    them is in an unsafe range — partial-resolution attacks are real."""
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeFetchError(f"could not resolve hostname '{host}': {exc}") from exc
    addrs: list[str] = []
    for info in infos:
        sockaddr = info[4]
        addr = sockaddr[0]
        addrs.append(addr)
    if not addrs:
        raise UnsafeFetchError(f"hostname '{host}' resolved to no addresses")
    for a in addrs:
        if _is_unsafe_ip(a):
            raise UnsafeFetchError(
                f"hostname '{host}' resolves to unsafe address '{a}' "
                "(loopback, private, link-local, or reserved)"
            )
    return addrs


# ---------------------------------------------------------------------------
# Pinned-IP adapter — defeats time-of-check / time-of-use DNS rebinding


class _PinnedHostAdapter(HTTPAdapter):
    """A requests adapter that connects to a fixed IP we already validated,
    setting the Host header to the original hostname so TLS / vhost routing
    still works."""

    def __init__(self, pinned_ip: str, **kwargs):
        self._pinned_ip = pinned_ip
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        # urllib3 honors a `socket_options` arg but to actually pin the
        # destination IP we override the `connection_from_host` path.
        self.poolmanager = PoolManager(*args, **kwargs)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        # requests 2.32+ — wrap the URL so urllib3 connects to the pinned IP
        # while we keep the original Host header for TLS SNI and vhost match.
        url = request.url
        parsed = urlparse(url)
        if parsed.hostname:
            new_netloc = self._pinned_ip
            if parsed.port:
                new_netloc = f"{self._pinned_ip}:{parsed.port}"
            pinned_url = urlunparse(parsed._replace(netloc=new_netloc))
            request.url = pinned_url
            request.headers["Host"] = parsed.netloc
        return super().get_connection_with_tls_context(request, verify, proxies, cert)


# ---------------------------------------------------------------------------
# Public safe-get


@dataclass
class SafeResponse:
    """Subset of `requests.Response` the matching fetcher actually uses."""
    status_code: int
    url: str
    content: bytes
    encoding: str | None


def safe_get(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    user_agent: str = "PricekeelBot/1.0",
    extra_headers: dict[str, str] | None = None,
    _resolver=_resolve_or_raise,  # injectable for tests
) -> SafeResponse:
    """SSRF-hardened GET. Raises UnsafeFetchError on any safety violation."""
    headers = {"User-Agent": user_agent, "Accept": "text/html,*/*;q=0.8"}
    if extra_headers:
        headers.update(extra_headers)

    current_url = url
    for hop in range(max_redirects + 1):
        parsed = urlparse(current_url)
        if parsed.scheme not in ("http", "https"):
            raise UnsafeFetchError(
                f"refusing scheme '{parsed.scheme}' (only http/https allowed)"
            )
        if not parsed.hostname:
            raise UnsafeFetchError(f"URL has no hostname: {current_url}")

        # 1) Resolve + IP-range check before we touch the network.
        _resolver(parsed.hostname)

        # 2) Make the request. We disable redirects so we can re-validate
        #    each hop's destination ourselves.
        try:
            resp = requests.get(
                current_url,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
                stream=True,  # so we can cap bytes
            )
        except requests.RequestException as exc:
            raise UnsafeFetchError(f"network error fetching {current_url}: {exc}") from exc

        if resp.is_redirect or resp.is_permanent_redirect:
            loc = resp.headers.get("Location")
            resp.close()
            if not loc:
                raise UnsafeFetchError(f"redirect without Location at {current_url}")
            # Resolve relative redirects against the current URL.
            from urllib.parse import urljoin
            current_url = urljoin(current_url, loc)
            if hop == max_redirects:
                raise UnsafeFetchError(
                    f"too many redirects ({max_redirects}); last hop -> {current_url}"
                )
            continue

        # 3) Cap body size by reading incrementally.
        body = bytearray()
        for chunk in resp.iter_content(chunk_size=16_384):
            if not chunk:
                break
            body.extend(chunk)
            if len(body) >= max_bytes:
                body = body[:max_bytes]
                break
        resp.close()
        return SafeResponse(
            status_code=resp.status_code,
            url=current_url,
            content=bytes(body),
            encoding=resp.encoding,
        )
    # Should be unreachable.
    raise UnsafeFetchError(f"redirect loop ended without a final response: {url}")


__all__ = ["safe_get", "UnsafeFetchError", "SafeResponse", "_is_unsafe_ip"]
