"""Synthetic billing generator for the contract_period_actuals grain (PK-53).

Opt-in and separate from pricing/generate.py: the default deal generator and
its pinned output are untouched. This module draws from its OWN seeded RNG
stream (a SeedSequence keyed on the seed and a fixed spawn key), so it never
shares state with the deal generator's seed, seed + 1 or seed + 2 streams.

It plants a known answer key so the billing derivations (PK-54, PK-55, PK-63)
and the end-to-end checks (PK-60, PK-67) can recover exact figures:

  * list versus contracted gaps (10 percent, 25 percent, none, and one EUR),
  * a 100-percent-off coupon for three periods, and a 20-percent coupon,
  * a three-year ramp schedule billed annually,
  * a 6-billed-period metered account (usage derivable) and a 5-billed-period
    one (insufficient_data),
  * a tiered metered price (list and overage unit rates not provided).

Discount semantics: discount_amount holds coupon and discount objects only.
Custom-price overrides (the gap cases) and ramp phases leave it 0, so the gap
is list_amount minus invoiced_amount. Free months from a 100-percent-off
coupon are credit_amount, never also discount_amount, so the key books the
coupon once. list_amount >= invoiced_amount + discount_amount + credit_amount.

The planted accounts are fixed amounts, independent of the seed. Only the
filler accounts draw from the RNG. Money is built in integer cents and the
answer key is Decimal, so there is no float drift. No real customer data, no
contact fields, no cost field. Subscription ids are synthetic.

    python -m pricing.generate_billing --seed 7 --filler 20 --out <path.csv>
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

from pricing.schema import (
    CONTRACT_PERIOD_COLUMNS, COST_KEY_MAP_COLUMNS, COST_PERIOD_FILE_COLUMNS, SourceSystem,
)

# Spawn key that keeps this stream disjoint from the deal generator's
# np.random.default_rng(seed + k) streams.
_SPAWN_KEY = (53,)
_START = date(2025, 1, 1)
# usage_acv needs at least this many billed periods (design section 4).
MIN_USAGE_PERIODS = 6


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(entropy=seed, spawn_key=_SPAWN_KEY))


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    return date(d.year + y, m + 1, 1)


def _month_window(index: int) -> tuple[date, date]:
    start = _add_months(_START, index)
    return start, _add_months(start, 1) - timedelta(days=1)


def _year_window(index: int) -> tuple[date, date]:
    start = _add_months(_START, 12 * index)
    return start, _add_months(start, 12) - timedelta(days=1)


def _usd(cents: int | None) -> float | None:
    return None if cents is None else round(cents / 100, 2)


def _dec(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def _annualise(total_cents: int, periods: int) -> Decimal:
    """Trailing billed total scaled to 12 monthly periods, in dollars, half-up."""
    return (Decimal(total_cents) * 12 / Decimal(periods) / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)


def _row(source: str, sub: str, idx: int, window: tuple[date, date], currency: str,
         *, list_c: int | None, invoiced_c: int, discount_c: int = 0,
         credit_c: int = 0, units: int | None = None, usage_c: int | None = None,
         committed_c: int | None = None) -> dict:
    return {
        "source_system": source, "source_record_id": sub, "period_index": idx,
        "period_start": window[0].isoformat(), "period_end": window[1].isoformat(),
        "currency": currency, "list_amount": _usd(list_c),
        "invoiced_amount": _usd(invoiced_c), "discount_amount": _usd(discount_c),
        "credit_amount": _usd(credit_c),
        "usage_units": None if units is None else float(units),
        "usage_amount": _usd(usage_c), "committed_amount": _usd(committed_c),
    }


def _tiered_cents(units: int) -> int:
    """Graduated tiers: first 10,000 at $1.00, next 40,000 at $0.80, rest $0.60."""
    first = min(units, 10_000)
    second = min(max(units - 10_000, 0), 40_000)
    third = max(units - 50_000, 0)
    return first * 100 + second * 80 + third * 60


def _planted() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    key: dict = {}
    stripe, cb = SourceSystem.STRIPE.value, SourceSystem.CHARGEBEE.value

    def licensed(sub, source, currency, list_c, invoiced_c, periods=12):
        for i in range(periods):
            rows.append(_row(source, sub, i + 1, _month_window(i), currency,
                             list_c=list_c, invoiced_c=invoiced_c))
        key[sub] = {
            "source_system": source, "currency": currency,
            "billed_periods": periods,
            "list_total": _dec(list_c * periods),
            "invoiced_total": _dec(invoiced_c * periods),
            "discount_total": Decimal("0.00"),  # custom price, not a discount object
            "gap_total": _dec((list_c - invoiced_c) * periods),  # list minus invoiced
            "realization": (Decimal(invoiced_c) / Decimal(list_c)).quantize(Decimal("0.0001")),
        }

    # List versus contracted gaps.
    licensed("SUB-GAP-10", stripe, "USD", 1_000_000, 900_000)   # 10,000 list, 9,000 billed
    licensed("SUB-GAP-25", cb, "USD", 800_000, 600_000)         # 8,000 list, 6,000 billed
    licensed("SUB-AT-LIST", cb, "USD", 500_000, 500_000)        # no gap
    licensed("SUB-GAP-EUR", cb, "EUR", 400_000, 360_000)        # 10 percent, EUR

    # 100-percent-off coupon for the first three monthly periods.
    sub = "SUB-COUPON-100"
    for i in range(12):
        free = i < 3
        rows.append(_row(stripe, sub, i + 1, _month_window(i), "USD", list_c=200_000,
                         invoiced_c=0 if free else 200_000,
                         credit_c=200_000 if free else 0))
    key[sub] = {
        "source_system": stripe, "currency": "USD", "billed_periods": 12,
        "list_total": _dec(2_400_000), "invoiced_total": _dec(1_800_000),
        # A 100-percent-off coupon period maps to credit_amount only, never
        # also to discount_amount, so the coupon is booked once.
        "discount_total": Decimal("0.00"), "credit_total": _dec(600_000),
        "zero_invoice_periods": 3, "credits_tcv": _dec(600_000),
    }

    # A real percentage-off coupon object: 20 percent off a 5,000 monthly list.
    sub = "SUB-COUPON-PCT"
    for i in range(12):
        rows.append(_row(stripe, sub, i + 1, _month_window(i), "USD", list_c=500_000,
                         invoiced_c=400_000, discount_c=100_000))
    key[sub] = {
        "source_system": stripe, "currency": "USD", "billed_periods": 12,
        "list_total": _dec(6_000_000), "invoiced_total": _dec(4_800_000),
        "discount_total": _dec(1_200_000), "credit_total": Decimal("0.00"),
    }

    # Three-year ramp billed annually: 60k, 80k, 100k against 100k list.
    sub = "SUB-RAMP"
    for i, billed in enumerate((6_000_000, 8_000_000, 10_000_000)):
        rows.append(_row(stripe, sub, i + 1, _year_window(i), "USD", list_c=10_000_000,
                         invoiced_c=billed))
    key[sub] = {
        "source_system": stripe, "currency": "USD", "billed_periods": 3,
        "list_total": _dec(30_000_000), "invoiced_total": _dec(24_000_000),
        "discount_total": Decimal("0.00"),  # ramp phases are not discounts
        "gap_total": _dec(6_000_000), "term_months": 36,
        "ramp_year_1_acv": _dec(6_000_000), "ramp_year_2_acv": _dec(8_000_000),
        "booked_acv": _dec(10_000_000),
    }

    # Hybrid metered accounts: $1,000 platform fee plus $0.50 per unit, flat.
    def metered(sub, source, periods, unit_counts):
        usage_total = units_total = 0
        for i in range(periods):
            u = unit_counts[i]
            usage_c = u * 50
            usage_total += usage_c
            units_total += u
            rows.append(_row(source, sub, i + 1, _month_window(i), "USD",
                             list_c=100_000 + usage_c, invoiced_c=100_000 + usage_c,
                             units=u, usage_c=usage_c, committed_c=150_000))
        enough = periods >= MIN_USAGE_PERIODS
        key[sub] = {
            "source_system": source, "currency": "USD", "billed_periods": periods,
            "usage_total": _dec(usage_total), "usage_units_total": units_total,
            "usage_acv": _annualise(usage_total, periods) if enough else None,
            "committed_amount_per_period": _dec(150_000),
            "committed_total": _dec(150_000 * periods),
            "usage_acv_status": "scored" if enough else "insufficient_data",
            "list_unit_rate": Decimal("0.50"),
        }

    metered("SUB-USAGE-6", stripe, 6, [20_000, 22_000, 24_000, 21_000, 25_000, 23_000])
    metered("SUB-USAGE-5", cb, 5, [20_000, 22_000, 24_000, 21_000, 25_000])

    # Tiered metered price: list and overage unit rates are not provided.
    sub = "SUB-TIERED"
    units = [8_000, 30_000, 60_000, 12_000, 55_000, 45_000]
    usage_total = 0
    for i, u in enumerate(units):
        usage_c = _tiered_cents(u)
        usage_total += usage_c
        rows.append(_row(cb, sub, i + 1, _month_window(i), "USD", list_c=None,
                         invoiced_c=200_000 + usage_c, units=u, usage_c=usage_c))
    key[sub] = {
        "source_system": cb, "currency": "USD", "billed_periods": 6,
        "usage_total": _dec(usage_total), "usage_units_total": sum(units),
        "usage_acv": _annualise(usage_total, 6), "usage_acv_status": "scored",
        "tiered": True, "list_unit_rate": None, "overage_rate": None,
    }
    return rows, key


def _filler(rng: np.random.Generator, n: int) -> list[dict]:
    rows: list[dict] = []
    for k in range(n):
        source = (SourceSystem.STRIPE if rng.random() < 0.5 else SourceSystem.CHARGEBEE).value
        list_c = int(rng.integers(100, 5_000)) * 100
        disc = float(rng.choice([0.0, 0.05, 0.10, 0.15, 0.20, 0.30]))
        invoiced_c = int(round(list_c * (1 - disc)))
        periods = int(rng.integers(3, 13))
        sub = f"SUB-F{k:04d}"
        for i in range(periods):
            rows.append(_row(source, sub, i + 1, _month_window(i), "USD", list_c=list_c,
                             invoiced_c=invoiced_c))
    return rows


def generate_billing(seed: int = 7, filler: int = 0) -> tuple[pd.DataFrame, dict]:
    """Return (periods, answer_key).

    `periods` has exactly CONTRACT_PERIOD_COLUMNS. `answer_key` maps each
    planted subscription id to its exact Decimal figures. Filler accounts
    (drawn from the module's own RNG stream) are not in the key.
    """
    planted, key = _planted()
    rows = planted + _filler(_rng(seed), filler)
    df = pd.DataFrame(rows, columns=CONTRACT_PERIOD_COLUMNS)
    return df, key




# ---------------------------------------------------------------------------
# PK-99: the customer cost grain and the planted margin-health answer key.
#
# generate_cost_fixture() builds a billing book and a cost export that join
# through a customer-declared key map, and records the exact answer a correct
# margin-health engine must recover (design doc section 7.1, MA-01 to MA-15).
# It draws from its OWN stream, SeedSequence(entropy=seed, spawn_key=(0x4D48,)),
# a key no other generator uses, so nothing above (generate_billing, PK-53's
# key, the deal generator) moves. Planted accounts are fixed amounts,
# independent of the seed; only the filler accounts draw from the stream.
# Money is integer cents, the key is Decimal, no float drift. No end-customer
# name, email or contact field exists on either grain. All ids are synthetic.
#
# Each cost row is tagged at construction with what a correct engine must do
# with it; the tag never reaches the CSV. Key totals come from the tags, and
# tests/test_schema_cost_period.py re-derives the clean-path figures from the
# CSV bytes, so the key and the fixture check each other.
#
#     python -m pricing.generate_billing --cost-dir data/synthetic/cost-export
# ---------------------------------------------------------------------------
COST_SPAWN_KEY = (0x4D48,)
COST_YEAR = 2026
COST_PRICE_POLICIES = ("cost_plus", "held")
# Generated cost files omit cost_basis (an upload that makes no claim) and the
# derived attribution column.
COST_FILE_COLUMNS = [c for c in COST_PERIOD_FILE_COLUMNS if c != "cost_basis"]
# Cost rows that count toward book cost totals: valid after row hygiene.
_BOOK_TAGS = {"ok", "currency", "outside", "straddle", "shared"}
_P4 = Decimal("0.0001")
# Filler economics: cost per credit starts at 0.004 and falls 50 percent across
# the twelve months; cost_plus prices at 2.5 times cost, held stays at 0.01.
_C0_MICRO = 4000            # 0.004 dollars per credit, in micro-dollars
_HELD_PRICE_MICRO = 10_000  # 0.01 dollars per credit


def _cost_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(entropy=seed, spawn_key=COST_SPAWN_KEY))


def _cmonth(i: int) -> tuple[date, date]:
    start = _add_months(date(COST_YEAR, 1, 1), i)
    return start, _add_months(start, 1) - timedelta(days=1)


def _amt(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100}.{abs(cents) % 100:02d}"


def _half_up(x: Decimal) -> int:
    return int(x.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _c_micro(m: int) -> int:
    """Filler cost per credit in micro-dollars for month index m: 4000 falling 50 percent."""
    return _half_up(Decimal(_C0_MICRO) * (22 - m) / 22)


def _price_micro_x2(policy: str, m: int) -> int:
    """Filler price per credit in half micro-dollars (cost_plus is 2.5 times cost)."""
    return 5 * _c_micro(m) if policy == "cost_plus" else 2 * _HELD_PRICE_MICRO


def _ratio(num: Decimal, den: Decimal) -> Decimal:
    return (num / den).quantize(_P4, rounding=ROUND_HALF_UP)


def _crow(vendor, cat, line, key, ktype, start, end, cur, cents, tag, sub=None, text=None):
    if text is None and cents is not None:
        text = _amt(cents)
    return {
        "cost_vendor": vendor, "cost_category": cat, "cost_line": line,
        "customer_key": key, "customer_key_type": ktype,
        "cost_start": start.isoformat(), "cost_end": end.isoformat(),
        "cost_currency": cur, "cost_amount": text,
        "_cents": cents, "_tag": tag, "_sub": sub,
        "_month": start.month - 1 if start.year == COST_YEAR else None,
    }


def _split_days(cents: int, days: int) -> list[int]:
    base, extra = divmod(cents, days)
    return [base + (1 if d < extra else 0) for d in range(days)]


def _allocate(total: int, drivers: dict[str, int]) -> dict[str, int]:
    """Split integer cents by driver: floor shares, then the leftover cents one
    at a time to the largest fractional remainders, ties by id ascending."""
    den = sum(drivers.values())
    if den <= 0:
        return {}
    exact = {k: Fraction(total * v, den) for k, v in drivers.items()}
    out = {k: int(f) for k, f in exact.items()}
    left = total - sum(out.values())
    for k in sorted(drivers, key=lambda k: (-(exact[k] - out[k]), k))[:left]:
        out[k] += 1
    return out


def _break_even(r: int, v: int, u: int, c: int) -> dict:
    """Per month: u* = F / (c_unit - p_unit) when cost per unit exceeds price per unit."""
    f = Decimal(r - v)
    p, cu = Decimal(v) / u, Decimal(c) / u  # cents per unit
    out = {"price_per_unit": (p / 100).quantize(_P4), "cost_per_unit": (cu / 100).quantize(_P4)}
    if cu > p:
        star = f / (cu - p)
        out["break_even_units"] = int(star)
        out["headroom"] = _ratio(star, Decimal(u))
    else:
        out["break_even_units"] = None
        out["headroom"] = None
        out["price_above_cost"] = True
    return out


def _planted_cost_book():
    """Fixed accounts MA-01 to MA-11. Returns (billing, cost, accounts, aligned, keymap).

    aligned[month][sub] = units for every aligned account-period, the driver
    set of the allocation variant."""
    stripe, cb = SourceSystem.STRIPE.value, SourceSystem.CHARGEBEE.value
    bill: list[dict] = []
    cost: list[dict] = []
    accts: dict[str, dict] = {}
    aligned: dict[int, dict[str, int]] = {m: {} for m in range(12)}
    keymap: list[dict] = []

    def month_rows(sub, src, key, ktype, *, R, V, U, C, credit=None, months=range(12),
                   cur="USD", cost_cur="USD", daily=False, tags=None,
                   conflict_month=None, lower_month=None):
        """Monthly billing plus monthly (or daily) inference cost for one account."""
        tags = tags or {}
        scored = []
        for i in months:
            win = _cmonth(i)
            r = R[i] if isinstance(R, list) else R
            cr = (credit or {}).get(i, 0)
            bill.append(_row(src, sub, i + 1, win, cur, list_c=r + cr, invoiced_c=r,
                             credit_c=cr, units=U, usage_c=V))
            if i == conflict_month:
                bill.append(_row(src, sub, i + 1, win, cur, list_c=r + 10_000,
                                 invoiced_c=r + 10_000, units=U, usage_c=V))
            tag = tags.get(i, "ok")
            cc = "usd" if i == lower_month else cost_cur
            if daily:
                for d, part in enumerate(_split_days(C, (win[1] - win[0]).days + 1)):
                    day = win[0] + timedelta(days=d)
                    cost.append(_crow("anthropic", "inference", "claude-large", key, ktype,
                                      day, day, cc, part, tag, sub))
            else:
                cost.append(_crow("anthropic", "inference", "claude-large", key, ktype,
                                  win[0], win[1], cc, C, tag, sub))
            if tag == "ok":
                scored.append((r, V, U, C))
                aligned[i][sub] = U
        keymap.append({"customer_key_type": ktype, "customer_key": key, "source_record_id": sub})
        return scored

    def entry(scored, **extra):
        rev = sum(s[0] for s in scored)
        cst = sum(s[3] for s in scored)
        res = [s[0] - s[3] for s in scored]
        e = {"status": "scored", "scored_periods": len(scored),
             "revenue_total": _dec(rev), "cost_total": _dec(cst), "result_total": _dec(rev - cst),
             "result_by_period": [_dec(x) for x in res],
             "negative_periods": sum(1 for x in res if x < 0),
             "result_pct_by_period": [None if s[0] == 0 else _ratio(Decimal(s[0] - s[3]), Decimal(s[0]))
                                      for s in scored]}
        e.update(extra)
        return e

    # MA-01 to MA-05: heavy and thin users.
    s = month_rows("sub_heavy_1", stripe, "ws_heavy_1", "workspace_id", R=300_000, V=0,
                   U=2_000_000, C=800_000, daily=True)
    accts["sub_heavy_1"] = entry(s, id="MA-01", **_break_even(300_000, 0, 2_000_000, 800_000),
                                 persistent=True, near=False, negative=True)
    s = month_rows("sub_heavy_2", stripe, "ws_heavy_2", "workspace_id", R=500_000, V=0,
                   U=1_500_000, C=600_000, lower_month=5)
    accts["sub_heavy_2"] = entry(s, id="MA-02", **_break_even(500_000, 0, 1_500_000, 600_000),
                                 persistent=True, near=False, negative=True)
    s = month_rows("sub_thin", cb, "key_thin", "api_key_id", R=100_000, V=60_000,
                   U=100_000, C=80_000)
    accts["sub_thin"] = entry(s, id="MA-03", **_break_even(100_000, 60_000, 100_000, 80_000),
                              persistent=False, near=False, negative=False)
    s = month_rows("sub_near", cb, "key_near", "api_key_id", R=300_000, V=0,
                   U=700_000, C=280_000)
    accts["sub_near"] = entry(s, id="MA-04", **_break_even(300_000, 0, 700_000, 280_000),
                              persistent=False, near=True, negative=False)
    s = month_rows("sub_hybrid_ok", stripe, "proj_ok", "project_id", R=200_000, V=100_000,
                   U=100_000, C=40_000)
    accts["sub_hybrid_ok"] = entry(s, id="MA-05", **_break_even(200_000, 100_000, 100_000, 40_000),
                                   persistent=False, near=False, negative=False)
    # MA-06: free Jan to Mar by a 100-percent coupon (credit), paid from April.
    s = month_rows("sub_free", stripe, "tag_free", "customer_tag",
                   R=[0, 0, 0] + [100_000] * 9, V=0, U=100_000, C=40_000,
                   credit={0: 100_000, 1: 100_000, 2: 100_000})
    accts["sub_free"] = entry(s, id="MA-06", zero_revenue_periods=3,
                              persistent=False, near=False, negative=False)
    # MA-07: billed all year, no cost line anywhere.
    for i in range(12):
        bill.append(_row(cb, "sub_nocost", i + 1, _cmonth(i), "USD", list_c=100_000,
                         invoiced_c=100_000, units=50_000, usage_c=0))
    accts["sub_nocost"] = {"id": "MA-07", "status": "not_provided", "reason": "cost_not_in_file",
                           "billed_periods": 12, "revenue_total": _dec(1_200_000)}
    # MA-08: billed in EUR, cost in USD, never converted.
    month_rows("sub_eur", cb, "ws_eur", "workspace_id", R=100_000, V=0, U=50_000, C=30_000,
               cur="EUR", tags={i: "currency" for i in range(12)})
    accts["sub_eur"] = {"id": "MA-08", "status": "excluded", "reason": "period_currency_mismatch",
                        "excluded_periods": 12, "revenue_total": _dec(1_200_000),
                        "revenue_currency": "EUR", "cost_total": _dec(360_000), "cost_currency": "USD"}
    # MA-09: eight weekly billing periods, never rounded to a month.
    for w in range(8):
        a = date(COST_YEAR, 1, 5) + timedelta(days=7 * w)
        bill.append(_row(cb, "sub_weekly", w + 1, (a, a + timedelta(days=6)), "USD",
                         list_c=25_000, invoiced_c=25_000, units=12_500, usage_c=0))
    for i in (0, 1):
        win = _cmonth(i)
        cost.append(_crow("anthropic", "inference", "claude-large", "proj_weekly", "project_id",
                          win[0], win[1], "USD", 10_000, "outside", "sub_weekly"))
    keymap.append({"customer_key_type": "project_id", "customer_key": "proj_weekly",
                   "source_record_id": "sub_weekly"})
    accts["sub_weekly"] = {"id": "MA-09", "status": "excluded", "reason": "period_not_whole_months",
                           "excluded_periods": 8, "revenue_total": _dec(200_000)}
    # MA-10: two differing billing rows for March; its cost row is outside every aligned period.
    s = month_rows("sub_conflict", stripe, "key_conflict", "api_key_id", R=100_000, V=50_000,
                   U=50_000, C=20_000, conflict_month=2, tags={2: "outside"})
    accts["sub_conflict"] = entry(s, id="MA-10", conflict_periods=1,
                                  conflict_reason="period_billing_conflict",
                                  persistent=False, near=False, negative=False)
    # MA-11: zero usage in three months, with cost.
    s = month_rows("sub_zero_usage", cb, "key_zero", "api_key_id", R=100_000, V=0, U=0,
                   C=15_000, months=range(3))
    accts["sub_zero_usage"] = entry(s, id="MA-11", break_even_status="insufficient_data",
                                    break_even_reason="zero_usage_units", cost_per_unit="not_given",
                                    persistent=False, near=False, negative=False)
    return bill, cost, accts, aligned, keymap


def generate_cost_fixture(seed: int = 7, filler: int = 20,
                          price_policy: str = "cost_plus") -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (billing_periods, cost_lines, answer_key).

    billing_periods has exactly CONTRACT_PERIOD_COLUMNS; cost_lines has exactly
    COST_FILE_COLUMNS, every amount a string at source precision (a blank cell
    is empty). price_policy is cost_plus (filler price is 2.5 times cost each
    month) or held (filler price stays 0.01). Only the billing frame depends on
    the policy; the cost frame and the answer key do not.
    """
    if price_policy not in COST_PRICE_POLICIES:
        raise ValueError(f"price_policy must be one of {COST_PRICE_POLICIES}")
    bill, cost, accts, aligned, keymap = _planted_cost_book()

    # MA-13: an inference project nobody mapped, 25.00 a day for March.
    for d in range(31):
        day = date(COST_YEAR, 3, 1) + timedelta(days=d)
        cost.append(_crow("anthropic", "inference", "claude-large", "proj_unmapped", "project_id",
                          day, day, "USD", 2_500, "shared"))
    # MA-12: a shared compute line with no key, 1,200.00 a month.
    for i in range(12):
        a, b = _cmonth(i)
        cost.append(_crow("aws", "compute", "shared-compute", None, None, a, b, "USD", 120_000, "shared"))

    # Hygiene rows, each with a known count and amount in the key. All sit on
    # the proj_ok key, whose own account result they must not move.
    k5, t5, s5 = "proj_ok", "project_id", "sub_hybrid_ok"
    cost.append(_crow("aws", "compute", "gpu-reservation", k5, t5, date(COST_YEAR, 5, 15),
                      date(COST_YEAR, 6, 14), "USD", 50_000, "straddle", s5))
    cost.append(_crow("aws", "compute", "gpu-reservation", k5, t5, date(COST_YEAR - 1, 12, 1),
                      date(COST_YEAR - 1, 12, 31), "USD", 25_000, "outside", s5))
    d = date(COST_YEAR, 8, 10)
    for c in (4_000, 5_500):
        cost.append(_crow("anthropic", "inference", "claude-large-batch", k5, t5, d, d, "USD", c,
                          "conflict", s5))
    for j in range(3):
        d = date(COST_YEAR, 1, 5 + j)
        cost.append(_crow("anthropic", "inference", "claude-large-batch", k5, t5, d, d, "USD",
                          None, "blank", s5))
    for j, t in enumerate(("1,200", "$100")):
        d = date(COST_YEAR, 2, 5 + j)
        cost.append(_crow("anthropic", "inference", "claude-large-batch", k5, t5, d, d, "USD",
                          None, "unparseable", s5, text=t))
    d = date(COST_YEAR, 3, 10)
    cost.append(_crow("anthropic", "inference", "vendor-credit", k5, t5, d, d, "USD", -7_500,
                      "negative", s5))
    # A second pull of Feb 1 to 7 for sub_heavy_1: identical rows, collapse to one.
    feb = [r for r in cost if r["customer_key"] == "ws_heavy_1"
           and "2026-02-01" <= r["cost_start"] <= "2026-02-07"]
    assert len(feb) == 7
    for r in feb:
        cost.append({**r, "_tag": "dup"})

    # Filler: ordinary hybrid accounts, drawn from the module's own stream.
    rng = _cost_rng(seed)
    fil_bill = {p: [] for p in COST_PRICE_POLICIES}
    fil_key: dict[str, dict] = {}
    for k in range(filler):
        src = (SourceSystem.STRIPE if rng.random() < 0.5 else SourceSystem.CHARGEBEE).value
        vendor = "anthropic" if rng.random() < 0.5 else "openai"
        units = [int(u) for u in rng.integers(50_000, 150_001, size=12)]
        sub = f"sub_f{k:03d}"
        tot = {p: [0, 0] for p in COST_PRICE_POLICIES}
        for m in range(12):
            win = _cmonth(m)
            c_c = _half_up(Decimal(units[m]) * _c_micro(m) / 10_000)
            cost.append(_crow(vendor, "inference", "model-standard", sub, "source_record_id",
                              win[0], win[1], "USD", c_c, "ok", sub))
            aligned[m][sub] = units[m]
            for p in COST_PRICE_POLICIES:
                v_c = _half_up(Decimal(units[m]) * _price_micro_x2(p, m) / 20_000)
                fil_bill[p].append(_row(src, sub, m + 1, win, "USD", list_c=100_000 + v_c,
                                        invoiced_c=100_000 + v_c, units=units[m], usage_c=v_c))
                tot[p][0] += 100_000 + v_c
                tot[p][1] += c_c
        fil_key[sub] = {p: {"revenue_total": _dec(t[0]), "cost_total": _dec(t[1]),
                            "result_total": _dec(t[0] - t[1])} for p, t in tot.items()}

    # MA-14: shared storage, derived month by month from that month's non-storage
    # cents (rows that survive cost hygiene, by calendar month of cost_start), so
    # the planted share rises linearly from 10 percent (Jan) to 40 percent (Dec).
    trend = []
    for m in range(12):
        ns = sum(r["_cents"] for r in cost if r["_tag"] in _BOOK_TAGS
                 and r["cost_category"] != "storage" and r["_month"] == m)
        share = Decimal(10) + Decimal(30) * m / 11  # percent
        st = _half_up(Decimal(ns) * share / (100 - share))
        a, b = _cmonth(m)
        cost.append(_crow("aws", "storage", "object-storage", None, None, a, b, "USD", st, "shared"))
        trend.append({"month": a.strftime("%Y-%m"), "non_storage_cents": ns, "storage_cents": st,
                      "planted_share_percent": share.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                      "realized_share": _ratio(Decimal(st), Decimal(st + ns))})

    # The allocation variant: the storage pool by proportional_to_usage_units.
    alloc = []
    for m in range(12):
        shares = _allocate(trend[m]["storage_cents"], aligned[m])
        assert sum(shares.values()) == trend[m]["storage_cents"]
        alloc.append({"month": trend[m]["month"], "pool_cents": trend[m]["storage_cents"],
                      "driver_units_total": sum(aligned[m].values()),
                      "allocated_cents": {k: shares[k] for k in sorted(shares)}})

    bill_df = pd.DataFrame(bill + fil_bill[price_policy], columns=CONTRACT_PERIOD_COLUMNS)
    cost_df = pd.DataFrame([{c: r[c] for c in COST_FILE_COLUMNS} for r in cost],
                           columns=COST_FILE_COLUMNS).astype(object)

    # Row ledger, from the tags.
    ledger = {}
    for reason, tag in (("cost_straddles_periods", "straddle"), ("cost_outside_billing_periods", "outside"),
                        ("cost_duplicate_collapsed", "dup"), ("cost_conflict", "conflict"),
                        ("cost_blank_amount", "blank"), ("cost_unparseable_amount", "unparseable"),
                        ("cost_negative_amount", "negative")):
        rows = [r for r in cost if r["_tag"] == tag]
        ledger[reason] = {"count": len(rows), "noun": "rows",
                          "amount": None if tag in ("blank", "unparseable")
                          else _dec(sum(r["_cents"] for r in rows))}
    book = [r for r in cost if r["_tag"] in _BOOK_TAGS]
    book_c = sum(r["_cents"] for r in book)
    direct = [r for r in book if r["_sub"]]
    unattr = [r for r in book if not r["_sub"]]
    unattr_c = sum(r["_cents"] for r in unattr)
    share = _ratio(Decimal(unattr_c), Decimal(book_c))
    unmapped = [r for r in cost if r["customer_key"] == "proj_unmapped"]
    parseable = [r for r in cost if r["_tag"] not in ("blank", "unparseable")]

    key = {
        "meta": {"seed": seed, "filler": filler, "calendar": "2026-01 to 2026-12", "currency": "USD",
                 "value_metric_unit": "credit", "spawn_key": list(COST_SPAWN_KEY),
                 "design": "PK-99, cost-period design doc section 7.1"},
        "accounts": accts,
        "negative_accounts": sorted(k for k, a in accts.items()
                                    if a["status"] == "scored" and a["result_total"] < 0),
        "near_break_even_accounts": sorted(k for k, a in accts.items() if a.get("near")),
        "key_map": sorted(keymap, key=lambda r: (r["customer_key_type"], r["customer_key"])),
        "attribution": {
            "direct": {"rows": len(direct), "amount": _dec(sum(r["_cents"] for r in direct))},
            "not_attributable": {"rows": len(unattr), "amount": _dec(unattr_c), "share": share},
            "upper_bound": share > Decimal("0.20"),
            "pools": {
                "shared_compute": {"rows": 12, "amount": _dec(120_000 * 12)},
                "unmapped_project": {"key": "proj_unmapped", "rows": len(unmapped),
                                     "amount": _dec(sum(r["_cents"] for r in unmapped))},
                "shared_storage": {"rows": 12, "amount": _dec(sum(t["storage_cents"] for t in trend))},
            },
        },
        "book_cost": {"rows": len(book), "amount": _dec(book_c)},
        "exclusions": {
            "cost_rows": ledger,
            "account_periods": {
                "period_currency_mismatch": {"count": 12, "noun": "account_periods", "revenue": _dec(1_200_000),
                                             "revenue_currency": "EUR", "cost": _dec(360_000),
                                             "cost_currency": "USD"},
                "period_not_whole_months": {"count": 8, "noun": "account_periods", "revenue": _dec(200_000)},
                "period_billing_conflict": {"count": 1, "noun": "account_periods"},
            },
            "accounts": {"cost_not_in_file": {"count": 1, "noun": "accounts", "revenue": _dec(1_200_000)}},
            "lowercase_currency_rows": sum(1 for r in cost if r["cost_currency"] == "usd"),
        },
        "storage_trend": {
            "basis": "non-storage rows that survive cost hygiene, by calendar month of cost_start",
            "months": trend, "direction": "up",
            "first_share": trend[0]["realized_share"], "last_share": trend[-1]["realized_share"]},
        "allocation_variant": {
            "pool": {"cost_category": "storage"}, "rule": "proportional_to_usage_units",
            "driver": "usage_units of aligned account-periods in the same month",
            "split": "floor shares, leftover cents to largest fractional remainders, ties by id ascending",
            "months": alloc},
        "price_policy": {
            "cost_per_credit_by_month": [(Decimal(_c_micro(m)) / 1_000_000).quantize(Decimal("0.000001"))
                                         for m in range(12)],
            "cost_fall": Decimal("0.5"),
            "supplied_index": [{"period": _cmonth(m)[0].strftime("%Y-%m"),
                                "index": (Decimal(100) * (22 - m) / 22).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)}
                               for m in range(12)],
            "policies": {p: {
                "expected_label": "cost_plus_pattern" if p == "cost_plus" else "markup_expanding",
                "pass_through": Decimal("1.0000") if p == "cost_plus" else None,
                "filler_price_per_credit_by_month": [
                    (Decimal(_price_micro_x2(p, m)) / 2_000_000).quantize(Decimal("0.0000001"))
                    for m in range(12)]} for p in COST_PRICE_POLICIES}},
        "filler_accounts": fil_key,
        # Anthropic's cost report states cents. cost-anthropic-cents.csv holds the
        # same book with every parseable amount x100; the factor is exact.
        "unit_scale": {
            "cents_file": "cost-anthropic-cents.csv", "scale": Decimal("0.01"), "factor": 100,
            "parseable_rows": len(parseable),
            "parseable_amount_total_dollars": _dec(sum(r["_cents"] for r in parseable))},
    }
    return bill_df, cost_df, key


def cost_frame_in_cents(cost_df: pd.DataFrame) -> pd.DataFrame:
    """The same cost export with every parseable amount in cents, as the
    Anthropic cost report states it. Blank and unparseable cells are untouched
    so the hygiene counts match the dollar file exactly."""
    out = cost_df.copy()

    def conv(v):
        if not isinstance(v, str):
            return v
        try:
            return str(int((Decimal(v) * 100).to_integral_value()))
        except ArithmeticError:
            return v
    out["cost_amount"] = out["cost_amount"].map(conv)
    return out


def cost_key_map_frame(key: dict) -> pd.DataFrame:
    return pd.DataFrame(key["key_map"], columns=COST_KEY_MAP_COLUMNS)


def cost_key_json(key: dict) -> str:
    return json.dumps(key, default=str, sort_keys=True, indent=1) + chr(10)


def write_cost_fixture(out_dir: Path, seed: int = 7, filler: int = 20) -> list[Path]:
    """Write the committed fixture set (LF line endings, per .gitattributes)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = {}
    for policy in COST_PRICE_POLICIES:
        b, c, key = generate_cost_fixture(seed, filler, policy)
        frames[f"billing-{policy.replace('_', '-')}.csv"] = b
    frames["cost.csv"] = c
    frames["cost-anthropic-cents.csv"] = cost_frame_in_cents(c)
    frames["key-map.csv"] = cost_key_map_frame(key)
    paths = []
    for name, df in frames.items():
        p = out_dir / name
        df.to_csv(p, index=False, lineterminator=chr(10))
        paths.append(p)
    p = out_dir / "answer-key.json"
    p.write_text(cost_key_json(key), encoding="utf-8", newline="")
    return paths + [p]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--filler", type=int, default=20)
    ap.add_argument("--out", type=Path, help="write the PK-53 billing periods CSV")
    ap.add_argument("--cost-dir", type=Path,
                    help="write the PK-99 cost fixture set (billing, cost, key map, answer key)")
    args = ap.parse_args()
    if args.out is None and args.cost_dir is None:
        ap.error("give --out, --cost-dir, or both")
    if args.out is not None:
        df, _ = generate_billing(args.seed, args.filler)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.out, index=False)
        print(f"wrote {len(df)} period rows to {args.out}")
    if args.cost_dir is not None:
        for p in write_cost_fixture(args.cost_dir, args.seed, args.filler):
            print(f"wrote {p}")


if __name__ == "__main__":
    main()
