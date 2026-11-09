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
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from pricing.schema import CONTRACT_PERIOD_COLUMNS, SourceSystem

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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--filler", type=int, default=20)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    df, _ = generate_billing(args.seed, args.filler)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"wrote {len(df)} period rows to {args.out}")


if __name__ == "__main__":
    main()
