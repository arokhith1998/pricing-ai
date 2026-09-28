---
title: CFO re-evaluation of Pricekeel, one day after PR #69
created: 2026-09-27
updated: 2026-09-27
tags: [cfo, unit-economics, market-sizing, review, pricekeel]
status: draft
---

# CFO re-evaluation, 2026-09-27

## 1. Does the readout tie out? Yes, verified.

- `pricing/metrics.py:848` `defended_vs_investigate` now builds its threshold from
  `_per_deal_reference(...)`, the same call `top_leak_deals` makes at `:966` and
  `trend_by_quarter` at `:1022`. One reference across the readout. F2 closed.
- Insufficient-data state is real and propagates: `:335-338` returns
  `sufficient: False` with a 0.0 threshold and basis "insufficient data";
  consumers gate on it at `:729` (leakage), `:841` (defended), `:960`
  (top_leak_deals returns an empty frame, not a manufactured list), `:1019`
  (trend), `:1104-1113` (policy sims mark `non_computable` with a disclosure,
  not a silent $0). That last distinction is the one a CFO cares about.
- Non-additive union: `:1128-1131` takes a per-deal max, `:1150-1152` labels it
  `non_additive: true`, `diagnostic.py:359-366` prints "these three do not sum".
- Public surfaces re-pointed: `web/src/app/sample/page.tsx:150,298` and
  `UploadClient.tsx:129` headline `excess_vs_segment_reference_won` with the
  global figure demoted to a labeled secondary ("overstates by design", `:305`,
  `:136`). On the bundled sample that is $8.95M, not $11.22M
  (`sample-fallback.json:63,92`): the 25% lead-gate overstatement is gone.

Residual: the threshold is still the band floor (`:356`), with the alternative
disclosed at `:365` as `reference_band_median_discount`. And the quarter-end
dollar is still an unstratified mean comparison (`:884`), so the weakest number
still sits in the section a CFO will quote. Both are founder calls.

## 2. SOM re-derivation: sound, still draft

Arithmetic in `vault/Decisions/2026-09-26-som-re-derived-against-tier-a-pool.md`
reproduces: 8-12% x 415 = 33-50 accounts; x $45K = $1.5-2.3M; span 28x$30K to
58x$60K = $0.8-3.5M; Tier B 8-12% of 130-190 at $45K = $0.5-1.0M; expansion
33-50 x $90-135K = $3.0-6.8M. The ACV band is reconciled to one number ($30-60K)
in the panel note `:75-79`, which is now `status: superseded`. It labels every
ARR figure a hypothesis and says out loud that the wedge cannot fund a Series B.
That is the right answer. It is `status: draft` and nothing has moved to the
deck, so F1 is diagnosed, not closed.

## 3. Pilot revenue recognition insert: correct, with one caveat

`gtm/llama-ventures/pilot-revenue-recognition-insert.md:39-47` ties: $15K + $30K
- $7.5K = $37.5K; $15K + $60K - $7.5K = $67.5K; 7.5/45 = 16.7%; 7.5/75 = 10.0%.
Bookings-not-ARR and the 80%+ software line are right. Caveat: ASC 606 allocates
the $15K by relative standalone selling price, where the material right's SSP is
the credit times probability of exercise. Deferring the full $7.5K assumes 100%
exercise. Fine as a conservative planning convention, say so in one clause.
Not yet pasted: `pitch-base.md:222` still defends "roughly 60 percent".

## 4. What remains

`web/src/app/pricing/page.tsx:25,187,340,395`: still no price, diagnostic still
free, "low five figures". `:159` still asserts "1 to 2 deals per quarter, 3 to 5
extra points at $250K ACV = $30K to $50K": the low end computes (1 x 4 x 3% x
$250K = $30K), the high end is $100K (2 x 4 x 5% x $250K), and $250K is not a
deal size in a $10-100M ARR book. The table understates its own claim while
being unverifiable, the worst of both.

## 5. Verdict and the one thing next week

Upgraded: the engine now ties out, and the commercial model is diagnosed
correctly but not published. The gap moved from "the numbers disagree" to "the
corrections sit in draft notes behind an unmerged PR."

One thing next week: put $15K on the pricing page, 100% credited to the pilot,
publish the $30-60K band, and delete the ROI threshold table rather than fix it.
A company whose thesis is that list price is fiction has no list price and
anchors every buyer at zero.

## 6. Three claims the landing page must make to a CFO buyer

- **A number with a basis.** "X points of realization, measured against your own
  segment win curves, on your last four quarters" with the insufficient-data
  state visible. The disclosure is the differentiator, not the dollar.
- **A price and a payback.** $15K diagnostic credited to a $30-60K annual, next
  to the recovered dollars. Recovered leakage must exceed the fee in quarter one
  or there is no sale.
- **Two weeks to first recommendation.** Against incumbent 6-12 month
  implementations, that is the only claim a CFO cannot get elsewhere.

Drop: "system of record", the free diagnostic, "low five figures", the invented
ROI threshold table, and any usage-based language until the UBP fields
(`pricing/schema.py:121-140`) drive a decision.
