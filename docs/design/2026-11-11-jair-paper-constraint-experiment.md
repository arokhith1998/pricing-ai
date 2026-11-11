---
title: JAIR paper experiment 1, the monotone constraint on the real generator
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, experiment, win-model]
status: draft
source: research/jair-discount-causality/run_constraint_experiment.py
---

# Experiment 1: does the monotone constraint change the recommendation?

Tests Corollary 2.1 of `2026-11-11-jair-paper-propositions.md` (the constraint
is decision-neutral) outside the simplified model: on the generator's
saturating win curve, with covariates, finite samples, and the product's exact
LightGBM settings.

## Answer

**The corollary holds only where the recommendation has already collapsed. In
between, the constraint makes the recommendation worse, not the same.**

- When reps discount weak deals harder (rescue), the constrained model loses
  6 to 11 more points of revenue than the unconstrained one on an unrestricted
  0 to 40% sweep.
- With the product's cohort-clipped sweep the penalty shrinks to about 0.3 to
  1.1 points. The clip, not the constraint, is what protects the product.
- When strong deals get the deeper discounts (whale), the two models are
  within about a point of each other, and the constraint is slightly ahead at
  the strongest setting.
- The constraint does what it was added for: it removes falling win curves.
  Under rescue confounding the unconstrained model shows a falling curve on 97
  to 100% of deals, the constrained one on none.

So the constraint buys a defensible-looking curve and pays for it in
recommendation quality whenever rescue confounding is present.

## Setup

- **Data:** `research/jair-discount-causality/confounded_book.py`. Same
  structure and win model as `pricing/generate.py` (constants imported), plus
  a dial `rho`: the correlation between hidden deal quality and the part of
  the discount that covariates and rep identity do not explain. The spread of
  discounts is the same at every `rho`. At `rho = 0` it matches the product
  generator's win rate (58%) and discount spread; the mean discount differs by
  about 1.6 points because the rep biases are different random draws.
- **Models:** two LightGBM classifiers per book with `pricing.model._PARAMS`
  and the product's features. One has the +1 monotone constraint on
  `discount_pct`, as `pricing.model.train` does. One does not.
- **Decision:** the discount that maximizes predicted win probability times
  (1 minus discount), for 2,000 fresh deals per run.
- **Scoring:** regret against the true causal curve, as a share of the
  revenue the true best discount would earn, weighted by list ACV.
- **Sweeps:** `full` is 0 to 40% for every deal. `cohort` is the segment's 5th
  to 95th percentile range from `pricing.model._cohort_grid`, snapped to
  1-point steps.
- **Not reproduced:** `recommend_discount`'s method labels and its rule that a
  floor never adds discount. This experiment scores the argmax only.
- **Runs:** 10 seeds at 2,000 training deals; 5 seeds at 20,000; 5 seeds at
  20,000 with the hidden quality effect raised from 0.55 to 1.5.

## Results

Regret in percent of optimal revenue, mean over seeds. "Diff" is constrained
minus unconstrained, with its standard error across seeds.

### 20,000 training deals, generator's quality effect (0.55)

| rho | Full: constrained | Full: unconstrained | Diff (se) | Cohort: constrained | Cohort: unconstrained | Diff (se) |
|---|---|---|---|---|---|---|
| -0.9 | 32.4 | 21.0 | +11.4 (2.4) | 4.2 | 3.7 | +0.6 (0.1) |
| -0.6 | 23.0 | 13.6 | +9.3 (1.0) | 3.3 | 2.8 | +0.6 (0.2) |
| -0.3 | 16.5 | 10.2 | +6.3 (0.9) | 2.3 | 2.1 | +0.3 (0.1) |
| 0 | 9.7 | 9.3 | +0.4 (0.5) | 1.7 | 1.6 | 0.0 (0.1) |
| +0.3 | 4.3 | 3.9 | +0.4 (0.4) | 0.9 | 0.9 | -0.1 (0.0) |
| +0.6 | 2.1 | 2.4 | -0.3 (0.1) | 0.6 | 0.6 | +0.1 (0.1) |
| +0.9 | 1.8 | 2.9 | -1.1 (0.6) | 0.5 | 1.1 | -0.7 (0.2) |

### 2,000 training deals (product-sized book), quality effect 0.55

| rho | Full: constrained | Full: unconstrained | Diff (se) | Cohort: constrained | Cohort: unconstrained | Diff (se) |
|---|---|---|---|---|---|---|
| -0.9 | 39.2 | 30.3 | +8.9 (3.5) | 5.1 | 4.0 | +1.1 (0.4) |
| -0.6 | 30.8 | 22.6 | +8.2 (2.3) | 4.1 | 3.6 | +0.5 (0.2) |
| -0.3 | 23.1 | 17.1 | +6.1 (1.4) | 3.1 | 2.8 | +0.3 (0.2) |
| 0 | 17.1 | 16.9 | +0.3 (1.0) | 3.1 | 3.1 | 0.0 (0.1) |
| +0.3 | 11.6 | 11.5 | +0.1 (0.5) | 2.3 | 2.5 | -0.2 (0.2) |
| +0.6 | 8.8 | 8.1 | +0.7 (0.5) | 2.1 | 2.0 | 0.0 (0.1) |
| +0.9 | 6.4 | 6.8 | -0.4 (0.3) | 3.0 | 2.5 | +0.5 (0.3) |

### 20,000 training deals, strong hidden quality (1.5), full sweep

| rho | Constrained | Unconstrained | Same recommendation (share of deals) |
|---|---|---|---|
| -0.9 | 32.2 | 32.2 | 100% |
| -0.6 | 32.2 | 32.2 | 100% |
| -0.3 | 28.6 | 19.4 | 66% |
| 0 | 8.7 | 8.4 | 88% |
| +0.3 | 1.5 | 1.8 | 75% |
| +0.6 | 4.1 | 4.5 | 81% |
| +0.9 | 9.0 | 9.0 | 86% |

## What the propositions got right and wrong

**Confirmed**
- *The collapse regime.* With strong hidden quality and rescue at -0.6 or
  beyond, both models recommend a 0% discount for every deal and lose the same
  32.2%. That is Corollary 2.1 and the floor plateau of Proposition 3.
- *Direction (Lemma 3.1).* The true best discount here (about 9%) sits below
  the historical mean (about 13%), which is the case where rescue should lower
  the recommendation and whale should raise it. It does: the mean
  recommendation moves from 1.3% at -0.9 to 8.8% at +0.9, and with strong
  quality the whale case overshoots to 15.8%.
- *The constraint is cosmetic for the curve.* It removes every falling curve.
  Without it, even an unconfounded 2,000-deal book shows a falling curve on
  77% of deals, from noise alone.
- *The clip limits the damage.* The worst rescue case costs 32% on the full
  sweep and 4% inside the cohort range.

**Wrong**
- *Decision-neutrality between the extremes.* The true curve rises steeply and
  then flattens. Under rescue confounding the observed curve is a hump: it
  rises, then falls. The unconstrained model finds the peak. The constrained
  model has to average the falling part into the rise, so its curve levels off
  earlier and lower, and it gives up discount that was worth giving. The
  simplified model has a straight-line effect, so it has no hump and missed
  this.
- *The cliff.* At the generator's quality effect, regret climbs steadily with
  rescue confounding (10, 16, 23, 32% for the constrained model). It is a
  cliff only when hidden quality is strong.

**New**
- *Estimation error is as large as confounding at product scale.* With no
  confounding at all, the full-sweep regret is 17% at 2,000 deals and 10% at
  20,000. The model is heavily regularized and under-reads the steep early
  part of the curve, so it recommends about 4 to 5% where 9% is best. Any
  claim about confounding has to be made against that baseline.
- *Mild whale confounding helps.* Regret falls as rho goes from 0 to +0.6,
  because the steepening offsets the model's under-reading. It is an accident
  of two errors cancelling, not a benefit.

## What this means

**For the paper**
- C1 becomes: a monotone constraint repairs the displayed curve and, on a
  saturating response under rescue confounding, worsens the decision. That is
  a stronger and more specific claim than neutrality, and it has a mechanism.
  The proposition needs restating for a concave or saturating effect.
- The benchmark must report regret against the zero-confounding baseline at
  the same sample size, not against zero.
- Sample size is a first-class dial. At 2,000 deals the constrained and
  unconstrained models differ by less than the seed-to-seed noise outside the
  rescue cases.

**For the product (a ticket, not a change today)**
- The cohort clip is doing the protective work. The monotone constraint costs
  up to about a point of regret under rescue confounding inside the clip, and
  nothing measurable otherwise.
- Removing the constraint is not the obvious fix: without it, most deals show
  a falling curve, which the model's own design notes call indefensible.
- The synthetic book has no confounding, so none of this shows up in the
  current tests.

## Limits

- Five to ten seeds per cell. The rescue-side differences are about 5 to 9 standard
  errors on the full sweep at 20,000 deals; several other cells are within
  noise.
- One generator, one model configuration, one family of confounding.
- The argmax is scored without the product's labels and never-add-discount
  rule, so product regret is not exactly the cohort column.
- Regret is on fresh deals from the same process. No drift, no time split.

## Reproduce

```bash
python research/jair-discount-causality/run_constraint_experiment.py
```

Writes `research/jair-discount-causality/results/constraint_experiment.csv`
(one row per book, model and sweep rule).
