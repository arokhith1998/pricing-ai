# Pricekeel re-evaluation, pricing-strategist lens, 2026-09-27

## Verification

**Sparse books return insufficient data everywhere. Closed.** The gate is
`pricing/metrics.py:327-339`: fewer than `SEGMENT_REF_MIN_BANDS` real bands at
15 deals returns `sufficient=False`, basis "insufficient data", and
`band_counts`. The relaxation to `_band_stats(1)` is gone. Every consumer
honors it: `leakage()` at `metrics.py:729-739`, `defended_vs_investigate` at
`:841-844`, `top_leak_deals` at `:960-962` (empty frame, not a named list),
`trend_by_quarter` at `:1019-1020`, `hierarchy_slice_reference` at `:670-676`
(NaN threshold, 0 excess), `crm.py:135-141` returns `(nan, None,
"insufficient data")` so open-deal guidance refuses, and `diagnostic.py:166`,
`:218-226`, `:321` print the refusal. F1 is genuinely closed.

**One per-deal reference. Closed.** `_per_deal_reference`
(`metrics.py:568-589`, BU then product line then segment then global) is now
the single basis at `:668`, `:848`, `:966`, `:1022`. The CFO reconciliation
failure is gone; the global lens survives only as a labeled secondary
(`excess_won_global`, `defended_value_global`). Web headlines the segment-aware
figure: `sample/page.tsx:150`, `UploadClient.tsx:129`, `LeakageBars.tsx:12`.

**Band floor still in place.** `metrics.py:356` `reference_threshold =
float(edges[reference_band])`. The median is computed at `:353-354` and
returned at `:365`, but grep finds no consumer outside `tests/test_metrics.py`.
It is not in diagnostic.py, the API payload, or web. That is a disclosure
nobody can see, which under Simon-Kucher is not a disclosure.

**support_floor labeling. Closed.** `model.py:632-638` demotes to
`support_floor` on a flat curve or a non-physical grid edge and never adds
discount; `METHOD_CAVEATS` at `:170-178` states plainly it is not a modeled
optimum; rendered at `GuidanceClient.tsx:184,387-390`.

**Usage-based fields still unread.** `committed_acv`, `overage_rate`,
`ramp_year_*` appear only in `schema.py:130-148`, `mapping.py:131-146`,
`ingest.py:137`, `generate.py:144-174`, tests. Zero references in metrics.py,
model.py, crm.py, governance.py, copilot.py.

## Band-floor recommendation

Split the threshold in two. Nagle: a reference price is a level, not an open
interval beneath it. Charging the full band width as excess on every won deal
inside the winning band biases the headline up by up to 5 points of list on the
whole won book, and the first thing a sales VP does in committee is produce one
defended in-band deal you called leakage. Headline the **observed median of the
reference band**. Keep the **floor as the review trigger** for
`top_leak_deals` and the investigate bucket: naming a deal for retrospective
review is cheap, asserting a dollar is not. Publish both as a range, "at least
X, at most Y." Surface `reference_band_median_discount` in diagnostic.py, the
API leakage payload, and the web basis line. Cost: one day. It is the last
thing standing between the readout and committee-defensible.

## Verdict against the four frameworks

- **Simon-Kucher, discount governance:** pass, and the best lens on the tool.
  Sufficiency gate, method labels, single basis, non-additive union. Residual:
  band floor, dead median disclosure.
- **Nagle:** partial. Segmentation and per-deal reference are right. EVC is
  still absent; the reference is a win-rate saturation point, not a buyer
  anchor, and list price remains an unvalidated denominator for every
  realization number.
- **Campbell:** fail. `value_metric_reference_table` exists and feeds neither
  `leakage()` nor `_per_deal_reference`, so seat and consumption discounts
  still pool inside one segment. WTP is never estimated.
- **Poyar:** fail. No commit, ramp, or overage branch in any verdict. Hybrid
  is the market default and the engine cannot speak it.

Cold start is now honest, which is the bigger win. Cross-customer benchmarking
remains unbuilt and remains the actual moat.

## The one thing next week

Land the band-floor decision as a two-number readout and surface the median on
every surface. Then re-run the sample and update deck and landing figures. The
one after: make the per-deal reference a segment-by-value-metric cell and give
`exception_verdict` a structure branch (commit step-up, ramp, overage) so the
UBP claim becomes true rather than retracted.

## Landing page, three claims and one drop

- **Claim the reference, not the dollar.** "Every exception priced against the
  reference your own won deals support, segment by segment, with the deal-level
  receipts." That is what `_per_deal_reference` plus the receipts functions
  actually deliver, and it survives committee.
- **Claim the refusal.** "Too thin a book, and Pricekeel says insufficient data
  instead of a number." No competitor ships that. It is the honest answer to a
  $20-100M ARR company with hundreds of deals, and it converts the cold-start
  weakness into the credibility pitch. Pair it with the fit gate already on
  `page.tsx:48`, stated as the engine's real bar: three discount bands with 15+
  closed deals each.
- **Claim the method label.** "Every recommendation says whether it is a modeled
  optimum or a support floor." `METHOD_CAVEATS` makes this true today.
- **Drop:** "usage or hybrid SaaS" in the ICP line (`page.tsx:53`) until the
  fields are read. The disclaimer at `:57` sits below the claim, and a claim
  plus a footnote is still a claim. Restate as "governs discount on committed
  ACV; commit, ramp, and overage captured, not yet scored." Also drop any
  single-point excess dollar as the hook until the band-floor range ships.
