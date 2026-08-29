"""Product Matching v1 component: /matching/competitor, /matching/compare,
/matching/context.

Customer enters their own pricing-page URL plus up to ~8 competitor URLs. We
fetch each page once (cached), extract structured plans via the LLM in
JSON-mode, and match competitor plans to the customer's plans with an
embedding+fuzzy scorer. This is NOT a market-wide scraper, only the
customer's own named competitors.

`matching_mod` is re-exported as `api.main.matching_mod` (see api/main.py)
purely so tests/test_api_perimeter.py's `monkeypatch.setattr(main.matching_mod,
"compare", ...)` keeps working: it patches the shared pricing.matching module
object, which is the same object this file calls through, so the patch is
visible here regardless of which file the route handler lives in.
"""

from __future__ import annotations

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pricing import matching as matching_mod

router = APIRouter()

# /matching/compare fans out one LLM call per URL (my_url + each competitor).
# Cap the total so a large list can't turn one request into an unbounded
# fetch+LLM bill; "usually 3-8" per the module docstring above.
MAX_COMPARE_URLS = 8


class CompareReq(BaseModel):
    my_url: str
    competitor_urls: list[str] = []


class CompetitorContextReq(BaseModel):
    url: str
    competitor_name: str = ""
    source_type: str = "other"


@router.post("/matching/competitor")
def matching_competitor(req: dict) -> dict:
    """Extract structured plans from a single competitor pricing URL.

    Useful as a one-shot probe so the UI can show 'we found 3 plans on
    this URL' before the user commits to a full comparison.
    """
    url = (req.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    vendor, plans = matching_mod.extract_plans_from_url(url)
    return {
        "url": url,
        "vendor": vendor,
        "plans": [p.to_dict() for p in plans],
    }


@router.post("/matching/compare")
def matching_compare(req: CompareReq) -> dict:
    """End-to-end comparison: customer's pricing page vs N competitor pages."""
    if not req.my_url.strip():
        raise HTTPException(status_code=400, detail="Missing my_url")
    competitor_urls = [u.strip() for u in req.competitor_urls if u and u.strip()]
    # Reject BEFORE any fetch/LLM call: my_url + competitor_urls together
    # drive N+1 page fetches and N+1 LLM extraction calls.
    total_urls = 1 + len(competitor_urls)
    if total_urls > MAX_COMPARE_URLS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Too many URLs ({total_urls}): my_url plus competitor_urls "
                f"must total at most {MAX_COMPARE_URLS}."
            ),
        )
    comp = matching_mod.compare(req.my_url.strip(), competitor_urls)
    return comp.to_dict()


@router.post("/matching/context")
def matching_context(req: CompetitorContextReq) -> dict:
    """Sourced qualitative context from one customer-named public URL.

    The result carries the source URL and never feeds numerical CRM guidance.
    """
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    allowed_types = {
        "pricing", "documentation", "release_notes", "case_study",
        "funding", "executive_interview", "investor_material", "other",
    }
    source_type = req.source_type.strip().lower()
    if source_type not in allowed_types:
        raise HTTPException(status_code=422, detail="Unsupported source_type")
    try:
        return matching_mod.extract_competitor_context(
            url,
            competitor_name=req.competitor_name,
            source_type=source_type,
        )
    except matching_mod.FetchBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except (ValueError, requests.RequestException) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
