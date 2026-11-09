"""Source-neutral deterministic guardrail for discount exceptions.

Takes canonical deals (closed history plus open deals) and returns the
guardrail verdict. It runs the same tested discount metrics as the file path,
never calls an LLM and never persists input rows.

Nothing in this module knows which system a deal came from. A source adapter
(see DealSourceAdapter) turns a raw record into a canonical one and supplies
the words used in refusal messages (SourceLabels); the engine only ever sees
deals, records and a source. Every guidance row names its method, thin data
returns "insufficient data" as an error rather than a manufactured number, and
nothing here calls a cost proxy a margin.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Protocol, runtime_checkable

import pandas as pd

from pricing import diagnostic, metrics
from pricing.ingest import ingest_frame_verbose
from pricing.schema import (
    DEFAULT_POLICY_THRESHOLD,
    FIELDS,
    SourceSystem,
    band_for,
)

MAX_RECORDS = 10_000
MIN_CLOSED_DEALS = 30

# The canonical column that identifies one deal. Read from the schema (its
# first, required string field) so this module stays vocabulary-neutral.
DEAL_ID_FIELD = FIELDS[0].name


class DealDataError(ValueError):
    """The payload cannot support a defensible analysis."""


# --- source adapters ----------------------------------------------------------

@dataclass(frozen=True)
class SourceLabels:
    """The words an adapter lends to the engine's refusal messages.

    `system` is the display name of the source, `records` and `record` the
    plural and singular noun for one of its deals, and `list_field_hint` the
    sentence telling an operator how to supply a real pre-discount list value.
    """

    system: str = "source"
    records: str = "deals"
    record: str = "deal"
    list_field_hint: str = (
        "Map a pre-discount list value column so discount and leakage are real"
    )


@runtime_checkable
class DealSourceAdapter(Protocol):
    """Turns a raw source record into a canonical deal. Pure, no network.

    `system` is a pricing.schema.SourceSystem value. `to_canonical` returns a
    new dict carrying the canonical fields plus the source_* provenance
    fields; it must not mutate its input. Network access (auth, queries,
    write-back) stays in the web tier, so the protocol has no fetch method.
    """

    system: str
    labels: SourceLabels

    def to_canonical(self, record: dict) -> dict: ...


class CsvAdapter:
    """Pass-through for rows that already arrive in canonical shape (a file
    or a pasted frame). Stamps source_system=csv when the row does not say."""

    system = SourceSystem.CSV.value
    labels = SourceLabels(system="CSV", records="deals", record="deal")

    def to_canonical(self, record: dict) -> dict:
        row = dict(record)
        if not str(row.get("source_system") or "").strip():
            row["source_system"] = self.system
        return row


def canonical_records(adapter: DealSourceAdapter, records: Iterable[dict]) -> list[dict]:
    return [adapter.to_canonical(row) for row in records]


# --- engine -------------------------------------------------------------------

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


def _currency_guard(records: list[dict], labels: SourceLabels) -> list[str]:
    currencies = sorted({
        str(row.get("currency_iso") or "").strip().upper()
        for row in records
        if str(row.get("currency_iso") or "").strip()
    })
    if len(currencies) > 1:
        raise DealDataError(
            f"V1 will not combine multiple {labels.system} currencies: "
            + ", ".join(currencies)
        )
    return currencies


def _ingest_closed(records: list[dict], policy_threshold: float,
                   labels: SourceLabels):
    return ingest_frame_verbose(
        pd.DataFrame(records),
        source=f"live {labels.system} {labels.records}",
        policy_threshold=policy_threshold,
    )


# When nearly every closed deal shows zero discount, the mapped list value is
# almost certainly the net booked amount (a default mapping that leaves the
# list field blank and falls back to the booked amount). The whole diagnostic
# then reads leakage as invisible, so we refuse rather than show a confident
# zero. A disciplined seller still has band spread; only a mapping error
# collapses the entire book onto ~0, so the 90 percent floor does not fire on
# honest low discounting.
_DEGENERATE_LIST_SHARE = 0.90
_ZERO_DISCOUNT_EPS = 0.0005


def _guard_degenerate_list(df: pd.DataFrame, *, list_field_mapped: bool = False,
                           labels: SourceLabels | None = None) -> None:
    # A customer who has explicitly mapped a real pre-discount list field
    # told us, out of band, that a near-zero-discount book is honest
    # discipline rather than the default-mapping failure this guard exists
    # to catch. Skip the heuristic rather than blocking an honest book.
    if list_field_mapped:
        return
    if "discount_pct" not in df.columns or df.empty:
        return
    labels = labels or SourceLabels()
    near_zero = float((df["discount_pct"].abs() <= _ZERO_DISCOUNT_EPS).mean())
    if near_zero >= _DEGENERATE_LIST_SHARE:
        raise DealDataError(
            "List and booked values are near-identical across the book "
            f"({near_zero * 100:.0f} percent of closed deals show no discount). "
            f"{labels.list_field_hint}, so discount and leakage are real."
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


def _reference_for_segment(df: pd.DataFrame, segment: str, *,
                           global_ref: dict | None = None,
                           segment_table: list[dict] | None = None,
                           ) -> tuple[float, str | None, str]:
    """Reference discount for one open deal's segment.

    `global_ref` / `segment_table` let a caller with several open deals in
    the same book (analyze_deals) pass in the values it already computed
    once, instead of this function re-running metrics.reference_discount's
    500-sample bootstrap and metrics.segment_reference_table per open deal on
    an unchanged `df` (perf finding: a dozen-open-deal book otherwise repeats
    both a dozen times). Recomputes when not supplied, so this stays a
    correct standalone call.

    2026-09-26 blocker fix: when the segment did not earn its own reference
    AND the global reference is itself insufficient, there is nothing
    defensible to fall back to. Returns `(nan, None, "insufficient data")`
    rather than the global's manufactured 0.0 threshold; the caller
    (guidance_for_open_deal) must refuse rather than recommend against it.
    """
    global_ref = global_ref if global_ref is not None else metrics.reference_discount(df)
    table = segment_table if segment_table is not None else metrics.segment_reference_table(
        df, global_ref=global_ref)
    for row in table:
        if str(row["segment"]).strip() == segment.strip():
            return (
                float(row["reference_threshold"]),
                row["reference_band"],
                str(row["basis"]),
            )
    if global_ref.get("sufficient", True):
        return (
            float(global_ref["reference_threshold"]),
            global_ref["reference_band"],
            "global fallback (segment not found)",
        )
    return (float("nan"), None, "insufficient data")


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
        DEAL_ID_FIELD, "resolved_account_name", "segment", "industry",
        "list_acv", "booked_acv", "discount_pct", "is_won",
    ]
    cols = [column for column in cols if column in work.columns]
    rows = work.sort_values("_score").head(limit)[cols].to_dict(orient="records")
    return [
        {("deal_id" if key == DEAL_ID_FIELD else key): value
         for key, value in row.items()}
        for row in rows
    ]


def guidance_for_open_deal(df: pd.DataFrame, deal: dict,
                           policy_threshold: float = DEFAULT_POLICY_THRESHOLD,
                           *, global_ref: dict | None = None,
                           segment_table: list[dict] | None = None,
                           labels: SourceLabels | None = None) -> dict:
    """Deterministic guardrail for one open deal.

    We never recommend adding discount. Above the supported reference, the
    reference becomes the recommendation; at or below it, the current request
    stays in place. Historical band win rates are evidence, not causal scores.

    `global_ref` / `segment_table`: see _reference_for_segment. Optional;
    recomputed from `df` when not supplied, so a direct call stays correct.

    2026-09-26 blocker fix: when neither the deal's segment nor the pooled
    global book can support a defensible reference discount, this raises
    DealDataError (the API maps it to 422) instead of returning
    `reference_discount=0.0`, which used to read as "recommend 0% / claw back
    the whole discount" for a live override on a thin pilot book.
    """
    labels = labels or SourceLabels()
    if not _usable(deal):
        raise DealDataError("Open deal is missing a positive list value or quoted value.")
    list_value = float(deal["list_acv"])
    booked_value = float(deal["booked_acv"])
    current = max(-0.5, min(1.0, 1.0 - booked_value / list_value))
    segment = str(deal.get("segment") or "Unknown")
    global_ref = global_ref if global_ref is not None else metrics.reference_discount(df)
    reference, reference_band, basis = _reference_for_segment(
        df, segment, global_ref=global_ref, segment_table=segment_table,
    )
    if not math.isfinite(reference):
        band_counts = global_ref.get("band_counts", {})
        raise DealDataError(
            "Insufficient closed-deal data for a defensible reference "
            f"discount (segment '{segment}'): no {metrics.SEGMENT_REF_MIN_BANDS} "
            "real discount bands each clear 15 closed deals. Band counts: "
            + ", ".join(f"{k}={v}" for k, v in sorted(band_counts.items()))
            + f". Collect more closed {labels.system} {labels.records} before "
              "quoting a guardrail on this deal."
        )
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
        "deal_id": str(deal.get(DEAL_ID_FIELD) or ""),
        "account": str(deal.get("account_name") or ""),
        # This guidance is a correlational band guardrail, not the modeled EV
        # curve the demo runs. It is labeled so the workspace can show the
        # buyer which engine produced the number (Gap 2 honesty).
        "evidence_source": "band_guardrail",
        "segment": segment,
        "product_tier": str(deal.get("product_tier") or "Unknown"),
        "rep_id": str(deal.get("rep_id") or ""),
        "close_date": str(deal.get("close_date") or ""),
        "currency_iso": str(deal.get("currency_iso") or ""),
        "source_url": str(deal.get("source_url") or ""),
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


def analyze_deals(records: list[dict], policy_threshold_pct: float = 15.0,
                  *, list_field_mapped: bool = False,
                  labels: SourceLabels | None = None,
                  max_records: int = MAX_RECORDS) -> dict:
    """Closed-history diagnostic plus guidance for every usable open deal.

    `records` are canonical deals (an adapter has already run). The result is
    `{"analysis", "guidance", "readiness"}`.
    """
    labels = labels or SourceLabels()
    if not records:
        raise DealDataError(f"No {labels.system} {labels.records} were supplied.")
    if len(records) > max_records:
        raise DealDataError(f"CRM payload exceeds the {max_records} record limit.")
    if not (0.0 <= float(policy_threshold_pct) <= 40.0):
        raise DealDataError("Policy threshold must be between 0 and 40 percent.")
    currencies = _currency_guard(records, labels)
    policy = float(policy_threshold_pct) / 100.0
    closed_all = [row for row in records if row.get("outcome") in {
        "closed_won", "closed_lost",
    }]
    open_all = [row for row in records if row.get("outcome") == "open"]
    closed = [row for row in closed_all if _usable(row)]
    open_usable = [row for row in open_all if _usable(row)]
    if len(closed) < MIN_CLOSED_DEALS:
        raise DealDataError(
            f"Only {len(closed)} usable closed {labels.records} were supplied; "
            f"at least {MIN_CLOSED_DEALS} are required."
        )
    df, report = _ingest_closed(closed, policy, labels)
    _guard_degenerate_list(df, list_field_mapped=list_field_mapped, labels=labels)
    analysis = diagnostic.analyze(df, report, policy_threshold=policy)
    # 2026-09-27 fix: diagnostic.analyze already computed the global reference
    # and the segment reference table for this exact `df` (they are pure
    # functions of `df` alone); analysis["reference_discount"] and
    # analysis["leakage"]["segment_references"] ARE those values. Reuse them
    # instead of re-running metrics.reference_discount's 500-sample bootstrap
    # and metrics.segment_reference_table a second time on identical input.
    global_ref = analysis["reference_discount"]
    segment_table = analysis["leakage"]["segment_references"]
    readiness = {
        "records_received": len(records),
        "closed_received": len(closed_all),
        "closed_usable": len(closed),
        "closed_excluded_missing_value": len(closed_all) - len(closed),
        "open_received": len(open_all),
        "open_usable": len(open_usable),
        "open_excluded_missing_value": len(open_all) - len(open_usable),
        "currencies": currencies,
    }
    if not global_ref.get("sufficient", True):
        # 2026-09-26's blocker fix made guidance_for_open_deal raise when
        # neither the deal's segment nor the pooled global book supports a
        # defensible reference. Readiness passes at 30 closed deals while the
        # engine needs 3 real discount bands at 15 deals each (up to 45+), so
        # a 30-44 deal book used to blow up on the FIRST open deal instead of
        # returning a 200 that names the blocker (silent-failure-hunter
        # finding, 2026-09-27). A segment is always a subset of the pooled
        # book, so if the global reference cannot clear the sufficiency bar,
        # no segment can either: skip guidance entirely rather than raise, and
        # disclose why in readiness.
        band_counts = global_ref.get("band_counts", {})
        readiness["reference_blocker"] = (
            "Insufficient closed-deal data for a defensible reference "
            f"discount: no {metrics.SEGMENT_REF_MIN_BANDS} real discount "
            "bands each clear 15 closed deals. Band counts: "
            + ", ".join(f"{k}={v}" for k, v in sorted(band_counts.items()))
            + f". Collect more closed {labels.system} {labels.records} before "
              "open-deal guidance can be shown."
        )
        return {"analysis": analysis, "guidance": [], "readiness": readiness}
    guidance = [
        guidance_for_open_deal(df, deal, policy, global_ref=global_ref,
                               segment_table=segment_table, labels=labels)
        for deal in open_usable
    ]
    # Rank by the risk-adjusted expected_acv_delta, not the gross price_to_retain.
    # price_to_retain is a full list-price delta that assumes the deal still
    # closes at the higher price; expected_acv_delta already discounts that
    # delta by the win-rate drop the higher band actually carries (asking for
    # more money lowers close probability). price_to_retain stays in the
    # payload for the rep to see, but it must not drive priority.
    guidance.sort(key=lambda row: (
        not bool(row["below_guardrail"]),
        float(row["expected_acv_delta"]),
    ), reverse=True)
    return {"analysis": analysis, "guidance": guidance, "readiness": readiness}


def selected_deal_guidance(records: list[dict], deal_id: str,
                           policy_threshold_pct: float = 15.0,
                           *, list_field_mapped: bool = False,
                           labels: SourceLabels | None = None,
                           max_records: int = MAX_RECORDS) -> dict:
    labels = labels or SourceLabels()
    result = analyze_deals(records, policy_threshold_pct,
                           list_field_mapped=list_field_mapped,
                           labels=labels, max_records=max_records)
    for row in result["guidance"]:
        if row["deal_id"] == deal_id:
            return row
    # 2026-09-27 fix: when the book-wide reference is insufficient,
    # analyze_deals returns an empty guidance list with the reason in
    # readiness["reference_blocker"] instead of raising. A single-deal caller
    # has no readiness surface of its own to show that disclosure on, so
    # surface it here as the 422 detail rather than the generic, misleading
    # "not usable".
    blocker = result["readiness"].get("reference_blocker")
    if blocker:
        raise DealDataError(blocker)
    raise DealDataError(
        f"The selected open {labels.system} {labels.record} is not usable."
    )
