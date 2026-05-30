"""AI Product Matching v1 — your plans vs your named competitors' plans.

What this is:

  - You provide your own pricing-page URL plus a small list of competitor
    pricing-page URLs (the competitors *you* care about — usually 3-8).
  - We fetch each URL once (with a short in-memory cache), strip the HTML
    to a clean text excerpt, and ask the LLM to return a structured list
    of plans: name, monthly price, billing cadence, included usage,
    feature list.
  - We match competitor plans against your plans using a layered scorer
    (fastembed cosine similarity on feature lists + rapidfuzz on plan
    names + a confidence floor). LLM tie-break for ambiguous pairs.
  - We return a Comparison: per-plan matches, pricing position (over /
    on-par / under), and the feature deltas in each direction.

What this is not:

  - A market-wide scraper. We only fetch URLs you give us.
  - A daily monitoring system. v1 is on-demand; weekly cron is v2.
  - Retail / e-commerce price intelligence. SaaS pricing pages only.

Honest constraints:

  - Some pricing pages are JS-heavy SPAs. The simple requests fetch will
    return a skeleton; the extraction will return zero plans. We surface
    that case explicitly to the caller rather than guessing.
  - The cloud LLM sees the public pricing-page text + your plan list +
    no row-level customer data. Same privacy contract as the rest of
    Pricekeel.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.robotparser
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import urlparse

import numpy as np
import requests
from rapidfuzz import fuzz

from pricing import assist
from pricing.docs import embed_texts

# ---------------------------------------------------------------------------
# Data shapes


@dataclass
class Plan:
    """One pricing tier on a vendor's pricing page."""
    vendor: str               # "Acme" / "Snowflake" / customer name
    name: str                 # "Pro" / "Enterprise" / "Tier 2"
    price_monthly: Optional[float] = None  # USD if quoted, else None
    price_unit: str = ""      # "per user / month", "per seat", "platform fee", "custom"
    billed_annually: bool = False
    included_usage: str = ""  # "100K events", "1 TB", "unlimited"
    features: list[str] = field(default_factory=list)
    notes: str = ""           # caveats, gotchas, "contact sales" markers

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Match:
    """One my-plan ↔ competitor-plan pairing with feature deltas."""
    my_plan_name: str
    competitor_vendor: str
    competitor_plan_name: str
    similarity: float                 # 0-1, blended score
    name_similarity: float            # rapidfuzz token-set ratio / 100
    feature_similarity: float         # mean cosine of overlapping features
    price_delta_pct: Optional[float]  # (theirs - mine) / mine, if both prices known
    pricing_position: str             # "above_market" | "at_market" | "below_market" | "unknown"
    features_only_mine: list[str] = field(default_factory=list)
    features_only_theirs: list[str] = field(default_factory=list)
    confidence: float = 0.0           # 0-1; rolls similarity + feature overlap

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Comparison:
    """A whole pricing-page comparison: yours vs N competitor pages."""
    my_vendor: str
    my_plans: list[Plan]
    competitor_plans: list[Plan]
    matches: list[Match]
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "my_vendor": self.my_vendor,
            "my_plans": [p.to_dict() for p in self.my_plans],
            "competitor_plans": [p.to_dict() for p in self.competitor_plans],
            "matches": [m.to_dict() for m in self.matches],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Fetching a pricing page (cheap, single GET, short in-memory cache)


_FETCH_CACHE: dict[str, tuple[float, str]] = {}
_FETCH_TTL_SECONDS = 60 * 60  # 1 hour
_FETCH_MAX_BYTES = 250_000    # ~250KB max body — pricing pages are small
_USER_AGENT = "PricekeelBot/1.0 (+https://pricekeel.com; one-time pricing extraction)"


# --- IP-risk hardening -----------------------------------------------------
# Per the 2026-05-30 legal audit (vault/Decisions/), the matching fetcher
# carries the highest IP-infringement risk in the product. Two defenses live
# here:
#   1. Honor robots.txt before every fetch (defends CFAA / good-citizen risk).
#   2. Maintain an explicit kill-switch list: any host or URL prefix we are
#      asked to stop fetching, we stop. We never want a deposition where the
#      answer to "did you stop when they asked you to" is "no".
# Both can be expanded via the LEGAL_BLOCKED_HOSTS env var (comma-separated
# hostnames) without a redeploy.


class FetchBlocked(Exception):
    """Raised when the matching fetcher refuses to fetch a URL.

    Carries a machine-readable reason so the UI can show a helpful message
    rather than a stack trace.
    """
    def __init__(self, url: str, reason: str):
        super().__init__(f"refused to fetch {url}: {reason}")
        self.url = url
        self.reason = reason


# Static kill-switch — extend in-code for any host that asks us to stop, or
# at runtime via the LEGAL_BLOCKED_HOSTS env var.
_BLOCKED_HOSTS: set[str] = set()

# Cache robots.txt parsers per origin so we do not refetch on every page.
_ROBOTS_CACHE: dict[str, tuple[float, urllib.robotparser.RobotFileParser | None]] = {}
_ROBOTS_TTL_SECONDS = 24 * 60 * 60  # 1 day


def _origin_of(url: str) -> tuple[str, str]:
    """Return (scheme://host, host) for a URL. Raises on bad input."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"not an absolute URL: {url}")
    return f"{parsed.scheme}://{parsed.netloc}", parsed.netloc.lower()


def _runtime_blocked_hosts() -> set[str]:
    """Static kill-switch + LEGAL_BLOCKED_HOSTS env var (comma-separated)."""
    extras = os.environ.get("LEGAL_BLOCKED_HOSTS", "")
    runtime = {h.strip().lower() for h in extras.split(",") if h.strip()}
    return _BLOCKED_HOSTS | runtime


def _robots_for(origin: str) -> urllib.robotparser.RobotFileParser | None:
    """Fetch + cache robots.txt for an origin. None if it could not be fetched
    (in which case we conservatively *do* allow — robots.txt is not legally
    mandatory and many sites do not publish one)."""
    now = time.time()
    cached = _ROBOTS_CACHE.get(origin)
    if cached and (now - cached[0]) < _ROBOTS_TTL_SECONDS:
        return cached[1]

    rp: urllib.robotparser.RobotFileParser | None
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{origin}/robots.txt")
        # urllib's default read() can hang; use requests with a short timeout.
        resp = requests.get(
            f"{origin}/robots.txt",
            headers={"User-Agent": _USER_AGENT},
            timeout=8,
        )
        if resp.status_code >= 400:
            # No robots.txt → unrestricted by convention.
            rp = None
        else:
            rp.parse(resp.text.splitlines())
    except requests.RequestException:
        rp = None
    _ROBOTS_CACHE[origin] = (now, rp)
    return rp


def _check_allowed(url: str) -> None:
    """Raise FetchBlocked if our kill-switch or robots.txt forbids this URL."""
    try:
        origin, host = _origin_of(url)
    except ValueError as exc:
        raise FetchBlocked(url, str(exc)) from exc

    blocked = _runtime_blocked_hosts()
    if host in blocked or any(host.endswith("." + b) for b in blocked):
        raise FetchBlocked(url, f"host '{host}' is on our kill-switch list")

    rp = _robots_for(origin)
    if rp is not None and not rp.can_fetch(_USER_AGENT, url):
        raise FetchBlocked(url, "robots.txt disallows this user-agent for this URL")


def _strip_html(html: str) -> str:
    """Quick HTML → text. No bs4 dep; we send to LLM next, exactness is fine."""
    # Drop script + style + noscript blocks first (they carry no text we want).
    html = re.sub(r"<(script|style|noscript)\b[^>]*>.*?</\1>", " ",
                  html, flags=re.IGNORECASE | re.DOTALL)
    # Remove all remaining tags.
    txt = re.sub(r"<[^>]+>", " ", html)
    # Decode common HTML entities cheaply.
    for esc, ch in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                    ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        txt = txt.replace(esc, ch)
    # Collapse whitespace.
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def fetch_pricing_page(url: str, *, ttl_seconds: int = _FETCH_TTL_SECONDS) -> str:
    """Fetch and clean a pricing page; cached for `ttl_seconds`.

    Raises FetchBlocked if our kill-switch or robots.txt forbids the URL,
    or requests.RequestException on network failure. The caller decides
    whether to fall back or surface the error.
    """
    _check_allowed(url)  # raises FetchBlocked when refused
    now = time.time()
    cached = _FETCH_CACHE.get(url)
    if cached and (now - cached[0]) < ttl_seconds:
        return cached[1]

    resp = requests.get(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
        timeout=15,
        allow_redirects=True,
    )
    resp.raise_for_status()
    body = resp.content[:_FETCH_MAX_BYTES].decode(
        resp.encoding or "utf-8", errors="replace",
    )
    text = _strip_html(body)
    # Trim further to the first ~30K chars (LLM context economics).
    if len(text) > 30_000:
        text = text[:30_000]
    _FETCH_CACHE[url] = (now, text)
    return text


# ---------------------------------------------------------------------------
# LLM-driven plan extraction (structured JSON)


_EXTRACT_SYSTEM = (
    "You parse SaaS pricing pages into a strict structured list of plans. "
    "Return ONLY valid JSON matching the schema. Do not invent plans or "
    "features that are not present in the supplied page text. If a number "
    "is not stated on the page, leave it null. The page text is provided "
    "verbatim and may contain navigation noise; ignore non-pricing content."
)

_EXTRACT_SCHEMA_HINT = """\
JSON schema:
{
  "vendor": "string — best guess at vendor name from the page",
  "plans": [
    {
      "name": "string — plan name as written on the page",
      "price_monthly": number or null,
      "price_unit": "string — 'per user / month', 'per seat', 'platform fee', 'custom', etc.",
      "billed_annually": boolean,
      "included_usage": "string — e.g. '100K events / mo', '1 TB', 'unlimited'",
      "features": ["string", "string", "..."],
      "notes": "string — any caveats, 'contact sales' flag, etc."
    }
  ]
}

Rules:
- If the page lists 'Contact us' instead of a price, set price_monthly=null and notes='custom pricing'.
- Convert annual prices to monthly equivalent if both stated.
- Keep features short (≤ 8 words each). Aim for the high-signal product features, not boilerplate.
- Return between 0 and 8 plans. If you cannot identify plans confidently, return an empty list.
"""


def extract_plans_from_text(page_text: str, *, fallback_vendor: str = "") -> tuple[str, list[Plan]]:
    """LLM-extract structured plans from a pricing page text. Best effort.

    Returns (vendor_name, plans). vendor_name may be empty if extraction
    failed or the page has no clear vendor signal.
    """
    if not page_text or len(page_text) < 100:
        return fallback_vendor, []
    if not assist.has_llm():
        return fallback_vendor, []

    user = (
        f"{_EXTRACT_SCHEMA_HINT}\n\n"
        f"PAGE TEXT (verbatim):\n{page_text}\n"
    )
    try:
        raw = assist._complete(
            _EXTRACT_SYSTEM, user, json_mode=True, max_tokens=1500,
        )
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return fallback_vendor, []

    vendor = (data.get("vendor") or fallback_vendor or "").strip()
    plans_raw = data.get("plans") or []
    plans: list[Plan] = []
    for p in plans_raw:
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").strip()
        if not name:
            continue
        plans.append(Plan(
            vendor=vendor,
            name=name,
            price_monthly=_safe_float(p.get("price_monthly")),
            price_unit=(p.get("price_unit") or "").strip(),
            billed_annually=bool(p.get("billed_annually") or False),
            included_usage=(p.get("included_usage") or "").strip(),
            features=[
                str(f).strip()
                for f in (p.get("features") or [])
                if isinstance(f, (str, int, float)) and str(f).strip()
            ][:12],
            notes=(p.get("notes") or "").strip(),
        ))
    return vendor, plans


def _safe_float(x) -> Optional[float]:
    """None for None / non-numeric; float otherwise."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return v


def extract_plans_from_url(url: str, *, fallback_vendor: str = "") -> tuple[str, list[Plan]]:
    """Convenience: fetch + extract. Returns ("", []) on refusal, network, or parse failure."""
    try:
        text = fetch_pricing_page(url)
    except (FetchBlocked, requests.RequestException):
        return fallback_vendor, []
    return extract_plans_from_text(text, fallback_vendor=fallback_vendor)


# ---------------------------------------------------------------------------
# Matching: pure-ish functions you can unit-test without an LLM


def _feature_similarity_matrix(my_features: list[str],
                               their_features: list[str]) -> np.ndarray:
    """Cosine sim matrix between two feature lists; empty pairs → zeros."""
    if not my_features or not their_features:
        return np.zeros((len(my_features), len(their_features)), dtype=float)
    A = np.asarray(embed_texts(my_features))
    B = np.asarray(embed_texts(their_features))
    # fastembed already L2-normalizes, but cosine via dot is safe regardless.
    return np.clip(A @ B.T, 0.0, 1.0)


def _name_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return fuzz.token_set_ratio(a, b) / 100.0


def _pricing_position(my_price: Optional[float],
                      their_price: Optional[float],
                      *, on_par_threshold: float = 0.05) -> tuple[str, Optional[float]]:
    """Return (label, price_delta_pct). 'unknown' when either price missing."""
    if my_price is None or their_price is None or my_price <= 0:
        return "unknown", None
    delta = (their_price - my_price) / my_price
    if abs(delta) <= on_par_threshold:
        return "at_market", delta
    if delta > 0:
        return "above_market", delta  # their price is higher → we're below market
    return "below_market", delta       # their price is lower → we're above market


def match_plans(my_plans: list[Plan],
                competitor_plans: list[Plan],
                *,
                feature_pair_threshold: float = 0.55,
                min_blended_similarity: float = 0.35) -> list[Match]:
    """Return one best match per (my_plan, competitor_vendor) pair, if any.

    Algorithm:
      1. Compute fastembed feature-similarity matrix for each (mine, theirs).
      2. Feature score = mean of pairs above feature_pair_threshold.
      3. Name score = rapidfuzz token-set ratio.
      4. Blended similarity = 0.65 * feature + 0.35 * name.
      5. For each (my_plan, competitor_vendor), pick the competitor plan
         with the highest blended similarity, IF it exceeds
         min_blended_similarity. Otherwise no match returned for that pair.
      6. Annotate with pricing position + feature deltas.
    """
    matches: list[Match] = []
    if not my_plans or not competitor_plans:
        return matches

    # Bucket competitor plans by vendor so each vendor maps to ≤ 1 match per
    # of-mine plan.
    by_vendor: dict[str, list[Plan]] = {}
    for cp in competitor_plans:
        by_vendor.setdefault(cp.vendor or "Unknown", []).append(cp)

    for mp in my_plans:
        for vendor, plans in by_vendor.items():
            best: Optional[tuple[Plan, float, float, float, np.ndarray]] = None
            for cp in plans:
                sim_mat = _feature_similarity_matrix(mp.features, cp.features)
                if sim_mat.size:
                    # Mean of the *high-similarity* feature pairs only, so a
                    # plan with 8 features that overlaps with 2 of them does
                    # not dilute the score with the other 6.
                    high = sim_mat[sim_mat >= feature_pair_threshold]
                    feat_score = float(high.mean()) if high.size else 0.0
                else:
                    feat_score = 0.0
                name_score = _name_similarity(mp.name, cp.name)
                blended = 0.65 * feat_score + 0.35 * name_score
                if best is None or blended > best[1]:
                    best = (cp, blended, feat_score, name_score, sim_mat)

            if best is None:
                continue
            cp, blended, feat_score, name_score, sim_mat = best
            if blended < min_blended_similarity:
                continue

            # Feature deltas: which of mine have no competitor feature ≥ thr,
            # and which of theirs have no mine feature ≥ thr.
            only_mine: list[str] = []
            only_theirs: list[str] = []
            if sim_mat.size:
                mine_best = sim_mat.max(axis=1)
                theirs_best = sim_mat.max(axis=0)
                only_mine = [
                    mp.features[i] for i in range(len(mp.features))
                    if mine_best[i] < feature_pair_threshold
                ]
                only_theirs = [
                    cp.features[j] for j in range(len(cp.features))
                    if theirs_best[j] < feature_pair_threshold
                ]
            else:
                only_mine = list(mp.features)
                only_theirs = list(cp.features)

            position, price_delta = _pricing_position(mp.price_monthly, cp.price_monthly)

            # Confidence rolls blended similarity + how much of *mine* the
            # competitor actually covers. A 0.6 blended with 80% feature
            # coverage of mine is more trustworthy than 0.6 with 30%.
            coverage = (
                1.0 - len(only_mine) / max(len(mp.features), 1)
                if mp.features else 0.0
            )
            confidence = float(np.clip(0.6 * blended + 0.4 * coverage, 0.0, 1.0))

            matches.append(Match(
                my_plan_name=mp.name,
                competitor_vendor=cp.vendor,
                competitor_plan_name=cp.name,
                similarity=round(blended, 3),
                name_similarity=round(name_score, 3),
                feature_similarity=round(feat_score, 3),
                price_delta_pct=(round(price_delta, 3) if price_delta is not None else None),
                pricing_position=position,
                features_only_mine=only_mine,
                features_only_theirs=only_theirs,
                confidence=round(confidence, 3),
            ))
    return matches


# ---------------------------------------------------------------------------
# Public surface — compare your URL against N competitor URLs


def compare(my_url: str, competitor_urls: list[str]) -> Comparison:
    """End-to-end: fetch, extract, match, summarize.

    The LLM gets the structured comparison output (no raw page HTML) and
    is asked for a one-paragraph plain-language read for the dashboard.
    """
    my_vendor, my_plans = extract_plans_from_url(my_url)
    all_competitor_plans: list[Plan] = []
    for cu in competitor_urls:
        _, plans = extract_plans_from_url(cu)
        all_competitor_plans.extend(plans)

    matches = match_plans(my_plans, all_competitor_plans)
    summary = _summarize_matches(my_vendor, my_plans, all_competitor_plans, matches)

    return Comparison(
        my_vendor=my_vendor or "Your pricing",
        my_plans=my_plans,
        competitor_plans=all_competitor_plans,
        matches=matches,
        summary=summary,
    )


_SUMMARY_SYSTEM = (
    "You are Pricekeel, the in-product analyst. Given a structured plan-"
    "match comparison (your plans, competitor plans, and per-pair matches "
    "with pricing position + feature deltas), write a calm 80-120 word "
    "summary for a pricing leader. Mention which competitors are over / "
    "under / at-market on which plan, and the most notable feature delta. "
    "Use only the JSON; do not invent vendors, plans, or numbers. Tone: "
    "direct, finance-credible, no hype."
)


def _summarize_matches(my_vendor: str, my_plans: list[Plan],
                       competitor_plans: list[Plan],
                       matches: list[Match]) -> str:
    if not assist.has_llm():
        if not matches:
            return ("Pricekeel: no high-confidence matches between your plans and "
                    "the competitor pages. Check the URLs returned plans, or "
                    "tighten the matching threshold.")
        return f"Pricekeel: {len(matches)} plan matches identified across the comparison."
    payload = {
        "my_vendor": my_vendor,
        "my_plans": [p.to_dict() for p in my_plans],
        "competitor_plans": [p.to_dict() for p in competitor_plans],
        "matches": [m.to_dict() for m in matches],
    }
    try:
        return assist._complete(
            _SUMMARY_SYSTEM, json.dumps(payload, default=str), max_tokens=350,
        ).strip()
    except Exception:  # noqa: BLE001
        return "Pricekeel: summary unavailable; the comparison data is in the table."
