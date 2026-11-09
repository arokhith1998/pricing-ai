"""Billing-derived levers over contract_period_actuals rows (PK-54).

Deterministic, pure, no LLM, no I/O. Three levers per account and per book,
each `{"method", "status", "reasons", "values"}` with status
`scored | insufficient_data | not_provided`:

  billing_realization   invoiced against list (list_amount, confirmed by the user)
  contracted_vs_billed  committed_amount against invoiced_amount
  usage_actuals         annualised metered usage, needs MIN_USAGE_PERIODS billed periods

Win rate is always `not_provided`: billing holds paying customers only. This
module also owns the refusal by source (`partition_for_win_rate`): a deal row
whose source_system is a billing source never reaches win rate, whatever its
outcome says, and the exclusion is disclosed by count.

Money is Decimal, rounded half-up to the cent (ratios to 4 places), so the
PK-53 planted answer key is recovered exactly, not within a tolerance. An
"account" here is one subscription or contract (source_record_id): the grain
carries no end-customer identifier by design.

Only the grain's own columns are read. No cost field is read or emitted:
billing_realization is invoiced against list, a price metric, and says so.
Design: docs/design/2026-11-09-native-connectors-hubspot-stripe-chargebee.md
section 4.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable

from pricing.schema import (
    BILLING_ONLY_OUTCOME, BILLING_SOURCES, PROVENANCE_DEFAULTS,
    PROVENANCE_ENUMS, win_rate_eligible,
)

SCORED = "scored"
INSUFFICIENT = "insufficient_data"
NOT_PROVIDED = "not_provided"

# usage_acv needs at least this many billed periods (design section 4).
MIN_USAGE_PERIODS = 6

WIN_RATE_REASON = ("billing data holds paying customers only; win rate needs "
                   "closed-lost deals from a CRM")

_CENT = Decimal("0.01")
_RATIO = Decimal("0.0001")
_ZERO = Decimal("0.00")
_CLOSED = {"closed_won", "closed_lost"}
_BILLING_WORDS = {"stripe", "chargebee", "billing"}


# --- parsing ----------------------------------------------------------------

def _rows(data: Any) -> list[dict]:
    if hasattr(data, "to_dict"):
        return data.to_dict("records")
    return [dict(r) for r in data]


def _blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and v != v:
        return True
    if type(v).__name__ in {"NAType", "NaTType"}:
        return True
    return isinstance(v, str) and not v.strip()


def _num(v: Any) -> Decimal | None:
    if _blank(v):
        return None
    try:
        d = Decimal(str(v).strip())
    except Exception:
        return None
    return d if d.is_finite() else None


def _money(v: Any) -> Decimal | None:
    d = _num(v)
    return None if d is None else d.quantize(_CENT, rounding=ROUND_HALF_UP)


def _date(v: Any) -> date | None:
    if _blank(v):
        return None
    if hasattr(v, "date") and callable(v.date):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        return None


def _text(v: Any) -> str:
    v = getattr(v, "value", v)
    return "" if _blank(v) else str(v).strip()


def _months(start: date, end: date) -> int:
    """Whole calendar months a period covers (end inclusive), at least 1."""
    nxt = end + timedelta(days=1)
    return max(1, (nxt.year - start.year) * 12 + nxt.month - start.month)


def _ratio(num: Decimal, den: Decimal) -> Decimal | None:
    return (num / den).quantize(_RATIO, rounding=ROUND_HALF_UP) if den > 0 else None


def _lever(method: str, status: str, reasons: list[str] | None = None,
           values: dict | None = None) -> dict:
    return {"method": method, "status": status,
            "reasons": list(reasons or []), "values": values or {}}


# --- grain cleaning ----------------------------------------------------------

def _clean_periods(periods: Any) -> tuple[dict[str, list[dict]], dict]:
    """Group usable period rows by account. A row missing a key field, from a
    non-billing source, or duplicating an earlier (account, start, end) is
    dropped and counted, never guessed or double counted."""
    accounts: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple] = set()
    skipped = {"rows_missing_key_fields": 0, "rows_not_billing_source": 0,
               "duplicate_periods_dropped": 0}
    for raw in _rows(periods):
        source = _text(raw.get("source_system")).lower()
        if source and source not in BILLING_SOURCES:
            skipped["rows_not_billing_source"] += 1
            continue
        acct = _text(raw.get("source_record_id"))
        start, end = _date(raw.get("period_start")), _date(raw.get("period_end"))
        cur = _text(raw.get("currency")).upper()
        invoiced = _money(raw.get("invoiced_amount"))
        if not (acct and start and end and end >= start and cur and invoiced is not None):
            skipped["rows_missing_key_fields"] += 1
            continue
        k = (acct, start, end)
        if k in seen:
            skipped["duplicate_periods_dropped"] += 1
            continue
        seen.add(k)
        accounts[acct].append({
            "start": start, "end": end, "currency": cur,
            "months": _months(start, end), "invoiced": invoiced,
            "list": _money(raw.get("list_amount")),
            "discount": _money(raw.get("discount_amount")) or _ZERO,
            "credit": _money(raw.get("credit_amount")) or _ZERO,
            "units": _num(raw.get("usage_units")),
            "usage": _money(raw.get("usage_amount")),
            "committed": _money(raw.get("committed_amount")),
        })
    for rows in accounts.values():
        rows.sort(key=lambda r: r["start"])
    return accounts, skipped


def _single_currency(rows: list[dict]) -> str | None:
    cur = {r["currency"] for r in rows}
    return next(iter(cur)) if len(cur) == 1 else None


_MIXED = "one account has more than one currency; nothing is summed across currencies"


def _sum(rows: list[dict], key: str) -> Decimal:
    return sum((r[key] for r in rows), _ZERO)


# --- the three levers, one account -------------------------------------------

def _realization(rows: list[dict]) -> dict:
    m = "billing_realization"
    cur = _single_currency(rows)
    if cur is None:
        return _lever(m, NOT_PROVIDED, [_MIXED])
    used = [r for r in rows if r["list"] is not None and r["list"] > 0]
    if not used:
        return _lever(m, NOT_PROVIDED, [
            "list price is not confirmed or not derivable (for example a tiered "
            "price), so invoiced against list cannot be computed"])
    list_t, inv_t = _sum(used, "list"), _sum(used, "invoiced")
    disc_t, cred_t = _sum(used, "discount"), _sum(used, "credit")
    gap = list_t - inv_t
    reasons = []
    if len(used) < len(rows):
        reasons.append(f"{len(rows) - len(used)} period(s) without a list amount "
                       "are left out of this figure")
    return _lever(m, SCORED, reasons, {
        "currency": cur, "periods": len(used),
        "list_total": list_t, "invoiced_total": inv_t,
        # list minus invoiced, whatever caused it: coupons, credits, custom price, ramp
        "gap_total": gap,
        "discount_total": disc_t, "credit_total": cred_t,
        # custom-price overrides and ramp phases: the gap no coupon or credit explains
        "other_gap_total": gap - disc_t - cred_t,
        "realization": _ratio(inv_t, list_t),
        "basis": "invoiced against confirmed list, tax excluded; a price metric",
    })


def _committed(rows: list[dict]) -> dict:
    m = "contracted_vs_billed"
    cur = _single_currency(rows)
    if cur is None:
        return _lever(m, NOT_PROVIDED, [_MIXED])
    used = [r for r in rows if r["committed"] is not None]
    if not used:
        return _lever(m, NOT_PROVIDED, [
            "no committed amount from a source the user marked; billing has no "
            "first-class commit"])
    com_t, inv_t = _sum(used, "committed"), _sum(used, "invoiced")
    return _lever(m, SCORED, [], {
        "currency": cur, "periods": len(used),
        "committed_total": com_t, "invoiced_total": inv_t,
        "billed_vs_committed": _ratio(inv_t, com_t),
        "shortfall_total": max(com_t - inv_t, _ZERO),
        "overage_total": max(inv_t - com_t, _ZERO),
        "periods_below_commit": sum(1 for r in used if r["invoiced"] < r["committed"]),
    })


def _usage(rows: list[dict]) -> dict:
    m = "usage_actuals"
    cur = _single_currency(rows)
    if cur is None:
        return _lever(m, NOT_PROVIDED, [_MIXED])
    used = [r for r in rows if r["usage"] is not None]
    if not used:
        return _lever(m, NOT_PROVIDED, ["no metered usage billed on this account"])
    if len(used) < MIN_USAGE_PERIODS:
        return _lever(m, INSUFFICIENT, [
            f"{len(used)} billed period(s); annualised usage needs at least "
            f"{MIN_USAGE_PERIODS}"], {
            "currency": cur, "billed_periods": len(used),
            "required_periods": MIN_USAGE_PERIODS, "usage_acv": None})
    # Trailing 12 months of periods, newest first, always at least one period.
    window: list[dict] = []
    months = 0
    for r in sorted(used, key=lambda r: r["start"], reverse=True):
        if window and months + r["months"] > 12:
            break
        window.append(r)
        months += r["months"]
    total = _sum(window, "usage")
    units = [r["units"] for r in window if r["units"] is not None]
    units_total = sum(units, Decimal(0))
    return _lever(m, SCORED, [], {
        "currency": cur, "billed_periods": len(used),
        "window_periods": len(window), "window_months": months,
        "usage_total": total,
        # trailing billed usage scaled to 12 months, half-up to the cent
        "usage_acv": (total * 12 / Decimal(months)).quantize(_CENT, rounding=ROUND_HALF_UP),
        "usage_units_total": units_total if units else None,
        "usage_units_acv": (units_total * 12 / Decimal(months)
                            if units and len(units) == len(window) else None),
    })


# --- book level --------------------------------------------------------------

def _book(levers: dict[str, dict], method: str, sum_keys: tuple[str, ...],
          ratio: tuple[str, str, str] | None) -> dict:
    """Roll account levers up by currency. Only `scored` accounts contribute;
    insufficient or not provided accounts are counted, never added as zero."""
    counts = {SCORED: 0, INSUFFICIENT: 0, NOT_PROVIDED: 0}
    by_cur: dict[str, dict] = {}
    for lv in levers.values():
        counts[lv["status"]] += 1
        if lv["status"] != SCORED:
            continue
        acc = by_cur.setdefault(lv["values"]["currency"],
                                {"accounts": 0, **{k: _ZERO for k in sum_keys}})
        acc["accounts"] += 1
        for k in sum_keys:
            acc[k] += lv["values"][k]
    if ratio:
        name, num, den = ratio
        for acc in by_cur.values():
            acc[name] = _ratio(acc[num], acc[den])
    status = SCORED if counts[SCORED] else (
        INSUFFICIENT if counts[INSUFFICIENT] else NOT_PROVIDED)
    reasons = []
    if counts[INSUFFICIENT]:
        reasons.append(f"{counts[INSUFFICIENT]} account(s) have insufficient data "
                       "and are not in the book figure")
    if counts[NOT_PROVIDED]:
        reasons.append(f"{counts[NOT_PROVIDED]} account(s) not provided and are "
                       "not in the book figure")
    return {"method": method, "status": status, "reasons": reasons,
            "accounts_by_status": counts, "by_currency": by_cur}


def _lever_output(periods: Any, fn, method: str, sum_keys, ratio) -> dict:
    accounts, skipped = _clean_periods(periods)
    levers = {a: fn(rows) for a, rows in sorted(accounts.items())}
    return {"method": method, "accounts": levers,
            "book": _book(levers, method, sum_keys, ratio), "skipped": skipped}


def billing_realization(periods: Any) -> dict:
    """Invoiced against list, per account and per book (by currency)."""
    return _lever_output(
        periods, _realization, "billing_realization",
        ("list_total", "invoiced_total", "gap_total", "discount_total",
         "credit_total", "other_gap_total"),
        ("realization", "invoiced_total", "list_total"))


def contracted_vs_billed(periods: Any) -> dict:
    """Committed against invoiced, per account and per book (by currency)."""
    return _lever_output(
        periods, _committed, "contracted_vs_billed",
        ("committed_total", "invoiced_total", "shortfall_total", "overage_total"),
        ("billed_vs_committed", "invoiced_total", "committed_total"))


def usage_actuals(periods: Any) -> dict:
    """Annualised usage; fewer than MIN_USAGE_PERIODS billed periods is
    insufficient_data (never zero)."""
    return _lever_output(periods, _usage, "usage_actuals", ("usage_acv",), None)


def win_rate_lever() -> dict:
    """Win rate from billing is always not_provided."""
    return _lever("win_rate", NOT_PROVIDED, [WIN_RATE_REASON])


def analyze_billing(periods: Any, deal_records: Iterable[dict] | None = None) -> dict:
    """All three levers, the win-rate line, and the readiness disclosure."""
    periods = _rows(periods)
    return {
        "billing_realization": billing_realization(periods),
        "contracted_vs_billed": contracted_vs_billed(periods),
        "usage_actuals": usage_actuals(periods),
        "win_rate": win_rate_lever(),
        "readiness": readiness_disclosure(deal_records or [], periods),
    }


# --- refusal by source -------------------------------------------------------

def _source_of(record: dict) -> str:
    """Normalised source_system with the csv default applied first.

    A missing, blank or placeholder source reads as csv, exactly as ingest
    does (PROVENANCE_DEFAULTS), so a CSV book without the column still scores.
    """
    s = re.sub(r"[\s\-]+", "_", _text(record.get("source_system")).lower())
    if s in {"", "none", "null", "na", "n/a", "nan"}:
        return PROVENANCE_DEFAULTS["source_system"]
    return s


def _billing_sourced(source: str) -> bool:
    """A billing source by value, or an unnormalised alias that names one
    (stripe_billing, chargebee_prod): refused on the name, not left to
    win_rate_eligible's unknown-value rule."""
    return source in BILLING_SOURCES or any(
        t in _BILLING_WORDS for t in re.split(r"[_.:/]+", source))


def partition_for_win_rate(records: Iterable[dict]) -> dict:
    """Split deal records for any win-rate computation, by source.

    Returns `eligible` (closed_won or closed_lost from a recognised non-billing
    source), `excluded_billing` (source is a billing source, whatever the
    outcome), `excluded_unrecognised` (source not a known SourceSystem), and
    `not_closed` (open or other outcomes from a good source, passed through
    for callers that score open deals). Kept records are copies with the csv
    default applied; inputs are never mutated. `disclosure` counts every
    exclusion, including billing rows mislabelled closed_won or closed_lost.
    """
    eligible: list[dict] = []
    billing: list[dict] = []
    unknown: list[dict] = []
    other: list[dict] = []
    by_source: dict[str, int] = defaultdict(int)
    mislabelled = marker = 0
    for rec in records:
        source = _source_of(rec)
        outcome = _text(rec.get("outcome")).lower()
        out = dict(rec)
        out["source_system"] = source
        if _billing_sourced(source):
            billing.append(out)
            by_source[source] += 1
            if outcome in _CLOSED:
                mislabelled += 1
            elif outcome == BILLING_ONLY_OUTCOME:
                marker += 1
        elif source not in PROVENANCE_ENUMS["source_system"]:
            unknown.append(out)
        elif win_rate_eligible(source, outcome):
            eligible.append(out)
        else:
            other.append(out)
    return {
        "eligible": eligible, "excluded_billing": billing,
        "excluded_unrecognised": unknown, "not_closed": other,
        "disclosure": {
            "billing_sourced_rows": len(billing),
            "billing_sourced_by_source": dict(sorted(by_source.items())),
            "billing_rows_labelled_closed": mislabelled,
            "billing_only_marker_rows": marker,
            "unrecognised_source_rows": len(unknown),
            "reason": WIN_RATE_REASON if billing else None,
        },
    }


def readiness_disclosure(deal_records: Iterable[dict] = (), periods: Any = ()) -> dict:
    """Billing-sourced row counts for a readiness surface: deal rows refused
    from win rate by source, and contract-period rows held, each by count."""
    split = partition_for_win_rate(deal_records)
    d = dict(split["disclosure"])
    d["contract_period_rows"] = len(_rows(periods))
    d["excluded_from_win_rate"] = (len(split["excluded_billing"])
                                   + len(split["excluded_unrecognised"]))
    d["note"] = ("billing-sourced rows are counted here and never enter win "
                 "rate; they show realization, contracted against billed, and "
                 "usage actuals only")
    return d
