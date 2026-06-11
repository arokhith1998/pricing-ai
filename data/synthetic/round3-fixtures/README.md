# Round-3 fixtures — judgment traps (2026-06-10)

Rounds 1–2 covered naming/format variety and silent corruption. Round 3 tests
cases where correctness requires a judgment call: pass = defensible call made
OR assumption disclosed in the LoadReport. A right number with hidden judgment
fails.

    PYTHONPATH=. python tools/make_round3_fixtures.py
    PYTHONPATH=. python tools/check_round3_fixtures.py

## Results (2026-06-10) — 5/6 pass

```
conflicting_dupes  PASS  rows=300, conflict flagged=True
ambiguous_dates    PASS  assumption disclosed in report
mixed_currency     PASS  mixed currencies flagged
uplift_deals       FAIL  rows=300, negative-discount deals=0 (want 15)
blank_booked_lost  PASS  won-total drift 0.00%, blanks reported=True
big_injection      PASS  rows=30000, formula-as-text=True, 0.8s
```

## The one remaining fix

**uplift_deals.** `pricing/ingest.py:424` clamps discount:

    df["discount_pct"] = (1.0 - df["price_realization"]).clip(lower=0.0, upper=1.0)

Deals booked **above** list (expansion, CPI indexation, scarcity pricing) are
legitimate and analytically valuable — they're evidence of pricing power, the
opposite signal from leakage. Clamping erases them: 15 above-list deals read
as 0% discount and vanish from every analysis.

Fix:
1. Drop `lower=0.0` — allow negative discount_pct (keep an upper sanity bound).
2. Add an "above list" band to `DISCOUNT_BANDS` handling discount_pct < 0 so
   `band_for` doesn't mislabel them into "0-5%".
3. Count above-list deals in the LoadReport and surface them in the diagnostic
   as a *positive* finding ("N deals closed above list — pricing-power signal").
4. Audit downstream consumers (metrics, model features, dashboard charts) for
   [0,1] discount assumptions.
5. Promote these 6 cases into `tests/test_round3_fixtures.py` when green.

## Status — RESOLVED (2026-06-10)

- [x] Fix 1–5 implemented; `check_round3_fixtures.py` reports **6/6**.
- [x] Promoted into `tests/test_round3_fixtures.py` (CI-gating), each asserting
      the DataFrame **and** the LoadReport disclosure.

Implementation notes:
- enrich: dropped the `lower=0.0` clamp on `discount_pct` (realization cap at
  1.5x is the sanity bound); above-list deals now survive as negative discount.
- schema: added the `above list` band (-1.01..0.00); `metrics.reference_discount`
  excludes it from the peak/reference search so its threshold can't go negative.
- LoadReport now also discloses (so the other five pass for real reasons, not a
  filename coincidence in the old checker): `above_list_deals`, mixed `currencies`,
  `blank_booked` count, and an ambiguous-date month-first assumption note.
- `check_round3_fixtures.py` removed (superseded by the test).
