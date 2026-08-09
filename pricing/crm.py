"""CRM-native pricing analysis and deal-workflow guidance.

Salesforce authentication and SOQL stay in the Next.js server tier. This
module receives a bounded list of canonical records, runs the same tested
discount metrics as the CSV path, and returns deterministic open-deal guidance.
It never calls an LLM and never persists input rows.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from pricing import diagnostic, metrics
from pricing.ingest import ingest_frame_verbose
from pricing.schema import DEFAULT_POLICY_THRESHOLD, band_for

MAX_CRM_RECORDS = 10_000


class CRMDataError(ValueError):
    """The live CRM payload cannot support a defensible analysis."""


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _usable(row: dict) -> bool:
    list_value = _number(row.get("list_acv"))
    booked_value = _number(row.get("booked_acv"))
    return bool(list_value is not None and list_value > 0
                and booked_value is not None and booked_value >= 0)


def _currency_guard(records: list[dict]) -> list[str]:
    currencies = sorted({
        str(row.get("currency_iso") or "").strip().upper()
        for row in records
        if str(row.get("currency_iso") or "").strip()
    })
    if len(currencies) > 1:
        raise CRMDataError(
            "V1 will not combine multiple Salesforce currencies: "
            + ", ".join(currencies)
        )
    return currencies


def _ingest_closed(records: list[dict], policy_threshold: float):
    return ingest_frame_verbose(
        pd.DataFrame(records),
        source="live Salesforce opportunities",
        policy_threshold=policy_threshold,
    )


# When nearly every closed deal shows zero discount, the mapped list value is
# almost certainly the net booked amount (the default Salesforce mapping leaves
# the list field blank and falls back to Amount). The whole diagnostic then
# reads leakage as invisible, so we refuse rather than show a confident zero.
# A disciplined seller still has band spread; only a mapping error collapses the
# entire book onto ~0, so the 90 percent floor does not fire on honest low
# discounting.
_DEGENERATE_LIST_SHARE = 0.90
_ZERO_DISCOUNT_EPS = 0.0005


def _guard_degenerate_list(df: pd.DataFrame) -> None:
    if "discount_pct" not in df.columns or df.empty:
        return
    near_zero = float((df["discount_pct"].abs() <= _ZERO_DISCOUNT_EPS).mean())
    if near_zero >= _DEGENERATE_LIST_SHARE:
        raise CRMDataError(
            "List and booked values are near-identical across the book "
            f"({near_zero * 100:.0f} percent of closed deals show no discount). "
            "Map a pre-discount Salesforce list field, or add Opportunity "
            "Products with true list prices, so discount and leakage are real."
        )


def _band_stats(df: pd.DataFrame) -> dict[str, dict]:
    rows = metrics.win_rate_by_band(df)
    return {
        str(row.discount_band): {
            "deals": int(row.deals),
            "won": int(row.won),
            "win_rate": float(row.win_rate),
        }
        for row in rows.itertuples()
    }


def _reference_for_segment(df: pd.DataFrame, segment: str) -> tuple[float, str, str]:
    global_ref = metrics.reference_discount(df)
    for row in metrics.segment_reference_table(df):
        if str(row["segment"]).strip() == segment.strip():
            return (
                float(row["reference_threshold"]),
                str(row["reference_band"]),
                str(row["basis"]),
            )
    return (
        float(global_ref["reference_threshold"]),
        str(global_ref["reference_band"]),
        "global fallback (segment not found)",
    )


def _comparables(df: pd.DataFrame, deal: dict, limit: int = 5) -> list[dict]:
    target_list = max(_number(deal.get("list_acv")) or 1.0, 1.0)
    target_segment = str(deal.get("segment") or "").strip()
    target_industry = str(deal.get("industry") or "").strip()
    work = df.copy()
    industries = (
        work["industry"].astype(str).str.strip()
        if "industry" in work.columns
        else pd.Series("", index=work.index)
    )
    work["_score"] = (
        (work["segment"].astype(str).str.strip() != target_segment).astype(float) * 1.5
        + (industries != target_industry).astype(float) * 0.5
        + (work["list_acv"].clip(lower=1).map(math.log) - math.log(target_list)).abs()
    )
    cols = [
        "opportunity_id", "resolved_account_name", "segment", "industry",
        "list_acv", "booked_acv", "discount_pct", "is_won",
    ]
    cols = [column for column in cols if column in work.columns]
    return work.sort_values("_score").head(limit)[cols].to_dict(orient="records")


def guidance_for_open_deal(df: pd.DataFrame, deal: dict,
                           policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> dict:
    """Deterministic guardrail for one open deal.

    We never recommend adding discount. Above the supported reference, the
    reference becomes the recommendation; at or below it, the current request
    stays in place. Historical band win rates are evidence, not causal scores.
    """
    if not _usable(deal):
        raise CRMDataError("Open deal is missing a positive list value or quoted value.")
    list_value = float(deal["list_acv"])
    booked_value = float(deal["booked_acv"])
    current = max(-0.5, min(1.0, 1.0 - booked_value / list_value))
    segment = str(deal.get("segment") or "Unknown")
    reference, reference_band, basis = _reference_for_segment(df, segment)
    recommended = min(current, reference)
    current_band = band_for(current)
    recommended_band = band_for(recommended)
    stats = _band_stats(df)
    base_rate = float(df["is_won"].mean()) if len(df) else 0.0
    current_stats = stats.get(current_band, {})
    recommended_stats = stats.get(recommended_band, {})
    win_current = float(current_stats.get("win_rate", base_rate))
    win_recommended = float(recommended_stats.get("win_rate", base_rate))
    expected_current = list_value * (1.0 - current) * win_current
    expected_recommended = list_value * (1.0 - recommended) * win_recommended
    return {
        "opportunity_id": str(deal.get("opportunity_id") or ""),
        "account": str(deal.get("account_name") or ""),
        # This live-CRM guidance is a correlational band guardrail, not the
        # modeled EV curve the demo runs. It is labeled so the workspace can
        # show the buyer which engine produced the number (Gap 2 honesty).
        "evidence_source": "band_guardrail",
        "segment": segment,
        "product_tier": str(deal.get("product_tier") or "Unknown"),
        "rep_id": str(deal.get("rep_id") or ""),
        "close_date": str(deal.get("close_date") or ""),
        "currency_iso": str(deal.get("currency_iso") or ""),
        "salesforce_url": str(deal.get("salesforce_url") or ""),
        "list_acv": list_value,
        "quoted_acv": booked_value,
        "current_discount": current,
        "recommended_discount": recommended,
        "policy_threshold": float(policy_threshold),
        "reference_discount": reference,
        "reference_band": reference_band,
        "reference_basis": basis,
        "below_guardrail": current <= reference,
        "price_to_retain": max(0.0, (current - recommended) * list_value),
        "win_rate_at_current_band": win_current,
        "win_rate_at_recommended_band": win_recommended,
        "expected_acv_at_current": expected_current,
        "expected_acv_at_recommended": expected_recommended,
        "expected_acv_delta": expected_recommended - expected_current,
        "current_band": current_band,
        "recommended_band": recommended_band,
        "current_band_deals": int(current_stats.get("deals", 0)),
        "recommended_band_deals": int(recommended_stats.get("deals", 0)),
        "competitor_present": bool(deal.get("competitor_present", False)),
        "comparables": _comparables(df, deal),
        "caveat": (
            "Historical discount-band outcomes are correlational. Deal mix, "
            "competitive pressure, and product differences can explain part "
            "of the observed relationship."
        ),
    }


def analyze_records(records: list[dict], policy_threshold_pct: float = 15.0) -> dict:
    if not records:
        raise CRMDataError("No Salesforce opportunities were supplied.")
    if len(records) > MAX_CRM_RECORDS:
        raise CRMDataError(f"CRM payload exceeds the {MAX_CRM_RECORDS} record limit.")
    if not (0.0 <= float(policy_threshold_pct) <= 40.0):
        raise CRMDataError("Policy threshold must be between 0 and 40 percent.")
    currencies = _currency_guard(records)
    policy = float(policy_threshold_pct) / 100.0
    closed_all = [row for row in records if row.get("outcome") in {
        "closed_won", "closed_lost",
    }]
    open_all = [row for row in records if row.get("outcome") == "open"]
    closed = [row for row in closed_all if _usable(row)]
    open_usable = [row for row in open_all if _usable(row)]
    if len(closed) < 30:
        raise CRMDataError(
            f"Only {len(closed)} usable closed opportunities were supplied; "
            "at least 30 are required."
        )
    df, report = _ingest_closed(closed, policy)
    _guard_degenerate_list(df)
    analysis = diagnostic.analyze(df, report, policy_threshold=policy)
    guidance = [guidance_for_open_deal(df, deal, policy) for deal in open_usable]
    guidance.sort(key=lambda row: (
        not bool(row["below_guardrail"]),
        float(row["price_to_retain"]),
    ), reverse=True)
    return {
        "analysis": analysis,
        "guidance": guidance,
        "readiness": {
            "records_received": len(records),
            "closed_received": len(closed_all),
            "closed_usable": len(closed),
            "closed_excluded_missing_value": len(closed_all) - len(closed),
            "open_received": len(open_all),
            "open_usable": len(open_usable),
            "open_excluded_missing_value": len(open_all) - len(open_usable),
            "currencies": currencies,
        },
    }


def selected_guidance(records: list[dict], deal_id: str,
                      policy_threshold_pct: float = 15.0) -> dict:
    result = analyze_records(records, policy_threshold_pct)
    for row in result["guidance"]:
        if row["opportunity_id"] == deal_id:
            return row
    raise CRMDataError("The selected open Salesforce opportunity is not usable.")
