# Pricekeel backend re-eval, day after PR #69 (HEAD 00bd935)

## Verdict
The five items I flagged on 2026-09-26 are closed as claimed, verified live, not
just by reading the closure doc. The core reference-number honesty problem is
fixed. What is left is one real engine gap (UBP fields still unread by any
decision), one disclosed-but-unfixed scaling risk, and one founder judgment call
that is correctly still open rather than silently resolved. Conditional yes,
narrower conditions than last time.

## Verified closed
- **PK-16**: `business_unit_reference_table` and `product_line_reference_table`
  exist (`pricing/metrics.py:508,525`), mirror `segment_reference_table`'s
  sufficiency bar, and `_per_deal_reference` (`metrics.py:539-589`) applies them
  in precedence BU > product_line > segment > global, each gated on
  `basis == "own win point"`. `hierarchy_slice_reference` (`metrics.py:603-688`)
  labels every fallback instead of returning a bare `realization_by` frame.
- **defended_vs_investigate reconciles**: now takes `_per_deal_reference`
  (`metrics.py:838-848`), docstring states `investigate_deals` equals
  `deals_above_segment_reference` exactly. Live run confirms it shares the same
  reference basis as `leakage()`/`top_leak_deals`; global reference kept only as
  a labeled secondary (`defended_value_global`).
- **Policy union present**: `metrics.py` policy_simulations emits a fourth,
  explicitly `"non_additive": True` union row (confirmed near end of
  `policy_simulations`, matches closure doc finding 4 fix).
- **CRM body cap**: `UPLOAD_PATHS` now includes `"/crm/"` (`api/main.py:94`),
  so the Content-Length gate at `api/main.py:246-258` fires before Starlette
  deserializes the body.
- **/recommend rate limit**: `RATE_LIMITS["/recommend"] = (30, 60.0)`
  (`api/main.py:124`).
- **One reference computation per run, verified by instrumentation**: I patched
  `reference_discount` and ran `diagnostic.analyze` on `data/synthetic/deals.csv`.
  The full-dataframe call fires exactly once (`diagnostic.py:38`); 18 further
  calls are legitimate different computations, one per qualifying segment/BU/
  product-line sub-frame inside the reference tables, not redundant recomputes.

## Still weak
1. **UBP fields still dead**, confirmed by grep across `model.py`, `ingest.py`,
   `mapping.py`, `generate.py`, `diagnostic.py`, `governance.py`, `crm.py`:
   `committed_acv`, `overage_rate`, `ramp_year_1_acv`, `ramp_year_2_acv`,
   `renewal_uplift` are generated, mapped, currency-normalized
   (`schema.py:117-154`), and read by nothing that scores a deal. There IS a
   `value_metric_reference_table` (`metrics.py:482-505`, cuts by seat/
   consumption/hybrid) but it is explicitly "additive, parallel," never wired
   into `_per_deal_reference`'s precedence chain. **Smallest fix**: add
   `value_metric` as a precedence level in `_per_deal_reference`, same
   sufficiency bar, ideally crossed with a commit-size band derived from
   `committed_acv` (e.g. tertiles) so the per-deal reference becomes a
   segment-by-value-metric cell instead of segment alone. Scoped entirely to
   `metrics.py`, same pattern as PK-16, no schema change.
2. **Rate limiter is still a plain in-process dict** (`_RATE_BUCKETS`,
   `api/main.py:135`), disclosed in a comment but not fixed: "limit *
   process_count" on >1 worker. The customer-keyed fix (`_rate_limit_key`,
   `api/main.py:206-214`) solves the shared-bucket problem, not the
   multi-process problem. Needs Redis or Neon-backed counters before a second
   Render instance/worker.
3. **new_vs_renewal is a latent recompute hole**: it takes no `global_ref`
   param and calls `reference_discount(df)` unconditionally at
   `metrics.py:1190` when `deal_type` is present. Masked today only because the
   synthetic book has no `deal_type` column (confirmed: returns `(0,10)` empty
   frame). A real CRM export with Type populated would silently double the
   global bootstrap cost and, worse, reintroduce a second independently-computed
   global reference alongside the threaded one.
4. **Won't sign yet**: reference threshold at the band floor
   (`metrics.py:348`, `reference_band_median_discount` disclosed as the
   alternative). Correctly still open, founder decision, not a defect.

## One thing next week
Wire `value_metric` into `_per_deal_reference`'s precedence and thread
`global_ref`/`**_refs` through `new_vs_renewal` so the "one reference per run"
guarantee holds on real data, not just the column-absent synthetic book.
