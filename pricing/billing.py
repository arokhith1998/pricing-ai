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

Annualisation rule (usage_actuals): by whole calendar months only. A period
that is exactly N calendar months (Jan 1 to Jan 31, Jan 15 to Feb 14) counts as
N. A weekly period, a prorated stub or any other interval is NOT rounded up to a
month and is not annualised: it is left out of the figure and counted in the
reasons, and an account whose usage periods are all such intervals returns
`not_provided` with that reason. Six weekly periods of 100 therefore give
`not_provided`, never 1200. Day-based scaling was rejected because it would move
the exact PK-53 key for monthly books (a 181-day half year is not 6 months).

Shortfall and overage are summed per period and never netted across periods;
`net_vs_commit` carries the net separately. Repeats of one period with the
same amounts collapse; differing rows for a period, or overlapping periods,
are conflicts excluded from the account and disclosed by count. A negative
amount (refund) or list below invoiced plus discount plus credit is flagged
invalid_money_value and left out of realization. An absent discount_amount or
credit_amount column is "not in the file", never 0; a blank cell is excluded
per row with a count.

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

_AMOUNTS = ("invoiced_amount", "list_amount", "discount_amount", "credit_amount",
            "usage_units", "usage_amount", "committed_amount")
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


def _whole_months(start: date, end: date) -> int | None:
    """N when the period is exactly N whole calendar months, end inclusive
    (Jan 1 to Jan 31, Jan 15 to Feb 14), else None. A weekly period, a
    prorated stub or an odd interval is None and is never rounded to a month.

    The subscription's billing day is not known, so a period counts when it is
    a whole number of months for ANY billing day (anchor) from start.day to 31
    that clamps to start: a sub billed on the 31st runs Jan 31 to Feb 27, Feb
    28 to Mar 30, Mar 31 to Apr 29."""
    nxt = end + timedelta(days=1)
    n = (nxt.year - start.year) * 12 + nxt.month - start.month
    if n < 1:
        return None
    for anchor in range(start.day, 32):
        if (_clamp(start.year, start.month, anchor) == start.day
                and _clamp(nxt.year, nxt.month, anchor) == nxt.day):
            return n
    return None


def _clamp(year: int, month: int, day: int) -> int:
    """day, or the last day of the month when the month is shorter."""
    first_next = date(year + (month == 12), month % 12 + 1, 1)
    return min(day, (first_next - timedelta(days=1)).day)


def _ratio(num: Decimal, den: Decimal) -> Decimal | None:
    return (num / den).quantize(_RATIO, rounding=ROUND_HALF_UP) if den > 0 else None


def _lever(method: str, status: str, reasons: list[str] | None = None,
           values: dict | None = None) -> dict:
    return {"method": method, "status": status,
            "reasons": list(reasons or []), "values": values or {}}


# --- grain cleaning ----------------------------------------------------------

def _columns(rows: list[dict]) -> set[str]:
    return {k for r in rows for k in r}


def _fingerprint(r: dict) -> tuple:
    return tuple(r[k] for k in ("currency", "invoiced", "list", "discount", "credit",
                                "units", "usage", "committed"))


def _clean_periods(periods: Any) -> tuple[dict[str, dict], dict, set[str]]:
    """Group usable period rows by account.

    A row missing a key field or from a non-billing source is dropped and
    counted. Identical repeats of a period (same account, dates and amounts)
    collapse to one. Rows that differ on the same period, or whose periods
    overlap without being identical, are conflicts: every row in the conflict
    is excluded from the account's metrics and counted with a reason. Nothing
    is first-row-wins and nothing is double counted.

    Returns {account: {"rows", "dq"}}, the load report, and the file's columns.
    """
    raws = _rows(periods)
    cols = _columns(raws)
    grouped: dict[str, list[dict]] = defaultdict(list)
    report = {"rows_missing_key_fields": 0, "rows_unparseable_amount": 0, "rows_not_billing_source": 0,
              "duplicate_periods_dropped": 0, "conflicting_period_rows": 0,
              "accounts_with_conflicts": 0}
    for raw in raws:
        source = _text(raw.get("source_system")).lower()
        if source and source not in BILLING_SOURCES:
            report["rows_not_billing_source"] += 1
            continue
        acct = _text(raw.get("source_record_id"))
        start, end = _date(raw.get("period_start")), _date(raw.get("period_end"))
        cur = _text(raw.get("currency")).upper()
        if any(not _blank(raw.get(f)) and _num(raw.get(f)) is None for f in _AMOUNTS):
            # "1,200" or "$100": present but not a number, never read as blank
            report["rows_unparseable_amount"] += 1
            continue
        invoiced = _money(raw.get("invoiced_amount"))
        if not (acct and start and end and end >= start and cur and invoiced is not None):
            report["rows_missing_key_fields"] += 1
            continue
        grouped[acct].append({
            "start": start, "end": end, "currency": cur,
            "months": _whole_months(start, end), "invoiced": invoiced,
            "list": _money(raw.get("list_amount")),
            "discount": _money(raw.get("discount_amount")),
            "credit": _money(raw.get("credit_amount")),
            "units": _num(raw.get("usage_units")),
            "usage": _money(raw.get("usage_amount")),
            "committed": _money(raw.get("committed_amount")),
        })
    accounts: dict[str, dict] = {}
    for acct, rows in grouped.items():
        uniq: list[dict] = []
        seen: set[tuple] = set()
        dq = {"duplicate_rows_dropped": 0, "conflict_rows_excluded": 0,
              "conflict_reasons": []}
        for r in rows:
            k = (r["start"], r["end"]) + _fingerprint(r)
            if k in seen:
                dq["duplicate_rows_dropped"] += 1
                continue
            seen.add(k)
            uniq.append(r)
        bad: set[int] = set()
        same = overlap = 0
        for i, a in enumerate(uniq):
            for j in range(i + 1, len(uniq)):
                b = uniq[j]
                if a["start"] <= b["end"] and b["start"] <= a["end"]:
                    bad.update((i, j))
                    if (a["start"], a["end"]) == (b["start"], b["end"]):
                        same += 1
                    else:
                        overlap += 1
        if bad:
            dq["conflict_rows_excluded"] = len(bad)
            if same:
                dq["conflict_reasons"].append(
                    f"{same} pair(s) of rows for the same period disagree on amounts")
            if overlap:
                dq["conflict_reasons"].append(
                    f"{overlap} pair(s) of non-identical periods overlap")
            report["accounts_with_conflicts"] += 1
        report["duplicate_periods_dropped"] += dq["duplicate_rows_dropped"]
        report["conflicting_period_rows"] += len(bad)
        kept = [r for i, r in enumerate(uniq) if i not in bad]
        kept.sort(key=lambda r: r["start"])
        accounts[acct] = {"rows": kept, "dq": dq}
    return accounts, report, cols


def _single_currency(rows: list[dict]) -> str | None:
    cur = {r["currency"] for r in rows}
    return next(iter(cur)) if len(cur) == 1 else None


_MIXED = "one account has more than one currency; nothing is summed across currencies"


def _sum(rows: list[dict], key: str) -> Decimal:
    return sum((r[key] for r in rows), _ZERO)


def _invalid_money(r: dict) -> bool:
    """A refund or credit-note row (negative amount), or one where list is
    below invoiced plus discount plus credit. Such a row is not a price."""
    parts = [r["invoiced"], r["discount"] or _ZERO, r["credit"] or _ZERO]
    if any(p < 0 for p in parts) or (r["list"] is not None and r["list"] < 0):
        return True
    return r["list"] is not None and r["list"] < sum(parts, _ZERO)


# --- the three levers, one account -------------------------------------------

def _realization(rows: list[dict], cols: set[str]) -> dict:
    m = "billing_realization"
    cur = _single_currency(rows)
    if cur is None:
        return _lever(m, NOT_PROVIDED, [_MIXED])
    invalid = [r for r in rows if _invalid_money(r)]
    valid = [r for r in rows if not _invalid_money(r)]
    reasons = []
    if invalid:
        reasons.append(
            f"{len(invalid)} period(s) flagged invalid_money_value (negative amount "
            "such as a refund, or list below invoiced plus discount plus credit) "
            "are excluded; a refund is never scored as negative realization")
    used = [r for r in valid if r["list"] is not None and r["list"] > 0]
    if not used:
        return _lever(m, NOT_PROVIDED, reasons + [
            "list price is not confirmed or not derivable (for example a tiered "
            "price), so invoiced against list cannot be computed"],
            {"invalid_money_value_rows": len(invalid)} if invalid else None)
    list_t, inv_t = _sum(used, "list"), _sum(used, "invoiced")
    gap = list_t - inv_t
    if len(used) < len(valid):
        reasons.append(f"{len(valid) - len(used)} period(s) without a list amount "
                       "are left out of this figure")
    out = {
        "currency": cur, "periods": len(used),
        "list_total": list_t, "invoiced_total": inv_t,
        # list minus invoiced, whatever caused it: coupons, credits, custom price, ramp
        "gap_total": gap,
        "discount_total": None, "credit_total": None, "other_gap_total": None,
        "invalid_money_value_rows": len(invalid),
        "realization": _ratio(inv_t, list_t),
        "basis": "invoiced against confirmed list, tax excluded; a price metric",
    }
    # An absent column is never read as 0; a blank cell in a present column
    # leaves that row out of the explanation, counted.
    has_d, has_c = "discount_amount" in cols, "credit_amount" in cols
    d_rows = [r for r in used if r["discount"] is not None] if has_d else []
    c_rows = [r for r in used if r["credit"] is not None] if has_c else []
    if d_rows:
        out["discount_total"] = _sum(d_rows, "discount")
    if c_rows:
        out["credit_total"] = _sum(c_rows, "credit")
    for col, present, got in (("discount_amount", has_d, d_rows),
                              ("credit_amount", has_c, c_rows)):
        if not present:
            reasons.append(f"{col} column is not in the file; the related figures "
                           "are not provided, not zero")
        elif len(got) < len(used):
            reasons.append(f"{len(used) - len(got)} period(s) have a blank {col} "
                           "and are excluded from the related figures, not read as 0")
    out["discount_blank_rows"] = (len(used) - len(d_rows)) if has_d else None
    out["credit_blank_rows"] = (len(used) - len(c_rows)) if has_c else None
    if has_d and has_c:
        both = [r for r in used if r["discount"] is not None and r["credit"] is not None]
        if both:
            # custom-price overrides and ramp phases: the gap no coupon or credit explains
            out["other_gap_total"] = (_sum(both, "list") - _sum(both, "invoiced")
                                      - _sum(both, "discount") - _sum(both, "credit"))
            if len(both) < len(used):
                reasons.append(f"other_gap_total covers {len(both)} of {len(used)} "
                               "periods (the rest lack a discount or credit value)")
    return _lever(m, SCORED, reasons, out)


def _committed(rows: list[dict], cols: set[str]) -> dict:
    m = "contracted_vs_billed"
    cur = _single_currency(rows)
    if cur is None:
        return _lever(m, NOT_PROVIDED, [_MIXED])
    invalid = [r for r in rows if _invalid_money(r)]
    used = [r for r in rows if r["committed"] is not None and not _invalid_money(r)]
    inv_note = ([f"{len(invalid)} period(s) flagged invalid_money_value (negative "
                 "amount such as a refund) are excluded"] if invalid else [])
    if not used:
        return _lever(m, NOT_PROVIDED, inv_note + [
            "no committed amount from a source the user marked; billing has no "
            "first-class commit"])
    com_t, inv_t = _sum(used, "committed"), _sum(used, "invoiced")
    # Per period, never netted: an over period does not cancel an under one.
    short = sum((max(r["committed"] - r["invoiced"], _ZERO) for r in used), _ZERO)
    over = sum((max(r["invoiced"] - r["committed"], _ZERO) for r in used), _ZERO)
    return _lever(m, SCORED, inv_note, {
        "currency": cur, "periods": len(used),
        "committed_total": com_t, "invoiced_total": inv_t,
        "billed_vs_committed": _ratio(inv_t, com_t),
        "shortfall_total": short,
        "overage_total": over,
        # the whole-account net, kept apart on purpose: invoiced minus committed
        "net_vs_commit": inv_t - com_t,
        "periods_below_commit": sum(1 for r in used if r["invoiced"] < r["committed"]),
    })


def _usage(rows: list[dict], cols: set[str]) -> dict:
    m = "usage_actuals"
    cur = _single_currency(rows)
    if cur is None:
        return _lever(m, NOT_PROVIDED, [_MIXED])
    if "usage_amount" not in cols:
        return _lever(m, NOT_PROVIDED, ["usage_amount column is not in the file"])
    used = [r for r in rows if r["usage"] is not None]
    if not used:
        return _lever(m, NOT_PROVIDED, [
            "usage_amount is blank on every period of this account"])
    regular = [r for r in used if r["months"] is not None]
    odd = len(used) - len(regular)
    note = ([f"{odd} period(s) are not whole calendar months (weekly, prorated "
             "stub or odd interval) and are not annualised, never rounded up "
             "to a month"] if odd else [])
    if not regular:
        return _lever(m, NOT_PROVIDED, note + [
            "no period is a whole number of calendar months, so usage is not "
            "annualised"], {"currency": cur, "billed_periods": len(used),
                            "usage_acv": None})
    if len(regular) < MIN_USAGE_PERIODS:
        return _lever(m, INSUFFICIENT, note + [
            f"{len(regular)} billed period(s); annualised usage needs at least "
            f"{MIN_USAGE_PERIODS}"], {
            "currency": cur, "billed_periods": len(regular),
            "required_periods": MIN_USAGE_PERIODS, "usage_acv": None})
    # Trailing 12 months of whole-month periods, newest first, at least one.
    window: list[dict] = []
    months = 0
    for r in sorted(regular, key=lambda r: r["start"], reverse=True):
        if window and months + r["months"] > 12:
            break
        window.append(r)
        months += r["months"]
    total = _sum(window, "usage")
    units = [r["units"] for r in window if r["units"] is not None]
    units_total = sum(units, Decimal(0))
    return _lever(m, SCORED, note, {
        "currency": cur, "billed_periods": len(regular),
        "window_periods": len(window), "window_months": months,
        "usage_total": total,
        # trailing billed usage scaled to 12 months, half-up to the cent
        "usage_acv": (total * 12 / Decimal(months)).quantize(_CENT, rounding=ROUND_HALF_UP),
        "usage_units_total": units_total if units else None,
        "usage_units_acv": ((units_total * 12 / Decimal(months)).quantize(
                                _CENT, rounding=ROUND_HALF_UP)
                            if units and len(units) == len(window) else None),
    })


# --- book level --------------------------------------------------------------

def _book(levers: dict[str, dict], method: str, sum_keys: tuple[str, ...],
          ratio: tuple[str, str, str] | None) -> dict:
    """Roll account levers up by currency. Only `scored` accounts contribute;
    insufficient or not provided accounts are counted, never added as zero. A
    figure an account does not provide (None) is skipped and the book figure
    says how many accounts lacked it."""
    counts = {SCORED: 0, INSUFFICIENT: 0, NOT_PROVIDED: 0}
    by_cur: dict[str, dict] = {}
    for lv in levers.values():
        counts[lv["status"]] += 1
        if lv["status"] != SCORED:
            continue
        acc = by_cur.setdefault(lv["values"]["currency"],
                                {"accounts": 0, **{k: None for k in sum_keys}})
        acc["accounts"] += 1
        for k in sum_keys:
            v = lv["values"][k]
            if v is None:
                acc[f"{k}_accounts_missing"] = acc.get(f"{k}_accounts_missing", 0) + 1
            else:
                acc[k] = (acc[k] or _ZERO) + v
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
    accounts, skipped, cols = _clean_periods(periods)
    levers = {}
    for a, info in sorted(accounts.items()):
        dq = info["dq"]
        if info["rows"]:
            lv = fn(info["rows"], cols)
        else:
            lv = _lever(method, NOT_PROVIDED, [
                "every period row of this account is in conflict and excluded"])
        if dq["conflict_rows_excluded"]:
            lv["reasons"].append(
                f"{dq['conflict_rows_excluded']} period row(s) in conflict are "
                "excluded from this account: " + "; ".join(dq["conflict_reasons"]))
        lv["data_quality"] = dict(dq)
        levers[a] = lv
    book = _book(levers, method, sum_keys, ratio)
    if skipped["conflicting_period_rows"]:
        book["reasons"].append(
            f"{skipped['conflicting_period_rows']} conflicting period row(s) across "
            f"{skipped['accounts_with_conflicts']} account(s) are excluded")
    return {"method": method, "accounts": levers, "book": book, "skipped": skipped}


def billing_realization(periods: Any) -> dict:
    """Invoiced against list, per account and per book (by currency)."""
    out = _lever_output(
        periods, _realization, "billing_realization",
        ("list_total", "invoiced_total", "gap_total", "discount_total",
         "credit_total", "other_gap_total"),
        ("realization", "invoiced_total", "list_total"))
    bad = sum(lv["values"].get("invalid_money_value_rows", 0)
              for lv in out["accounts"].values())
    out["skipped"]["invalid_money_value_rows"] = bad
    if bad:
        out["book"]["reasons"].append(
            f"{bad} period row(s) flagged invalid_money_value are excluded")
    return out


def contracted_vs_billed(periods: Any) -> dict:
    """Committed against invoiced, per account and per book (by currency).
    Shortfall and overage are summed per period; net_vs_commit is the net."""
    return _lever_output(
        periods, _committed, "contracted_vs_billed",
        ("committed_total", "invoiced_total", "shortfall_total", "overage_total",
         "net_vs_commit"),
        ("billed_vs_committed", "invoiced_total", "committed_total"))


def usage_actuals(periods: Any) -> dict:
    """Annualised usage over whole-month periods; fewer than MIN_USAGE_PERIODS
    billed periods is insufficient_data (never zero)."""
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
