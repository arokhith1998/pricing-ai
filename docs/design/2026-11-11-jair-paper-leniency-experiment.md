---
title: JAIR paper experiment 2, the rep-leniency control function
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, experiment, instrument]
status: draft
source: research/jair-discount-causality/run_leniency_experiment.py
---

# Experiment 2: does the rep-leniency method fix the recommendation?

Method: `research/jair-discount-causality/leniency_cf.py`. Runs:
`run_leniency_experiment.py` (the product's tree model) and
`run_spline_experiment.py` (a spline logistic model). Same books, test deals,
sweeps and regret definition as experiment 1.

## Answer

**Yes with enough data and a win model that can represent the curve. No with
the product's tree model, no on a 2,000-deal book when weak deals get the
discounts, and it fails silently when the instrument is invalid.**

1. **Bolted onto the product's tree model, the control function does not
   help.** It is no better than removing the monotone constraint, and it is
   much worse when strong deals get the discounts. Even a tree model that is
   shown the hidden deal quality loses 13 to 20%. The tree configuration, not
   the confounding, is the binding problem.
2. **With a spline logistic win model at 20,000 deals, it works.** Regret
   falls from as much as 20% to under 0.4% for every setting except the
   strongest rescue case (2.3%).
3. **At 2,000 deals it is one-sided.** It removes almost all the loss when
   strong deals get the discounts and does not help when weak deals do.
4. **The direction diagnostic is accurate when the instrument is valid** and
   wrong when it is not.
5. **If lenient reps are also weaker sellers, the method is worse than doing
   nothing**, and nothing in its output says so.

## The method in one paragraph

Each rep's leniency is the average unexplained discount on their other deals.
The part of a deal's discount that neither its covariates nor its rep's
leniency explains is where the rep's private read of the deal lives. Adding
that leftover as a feature lets the win model separate "this deal got more
discount because the rep is generous" (informative about what discount does)
from "this deal got more discount because the rep saw something" (not).
The causal curve is the model's prediction averaged over the leftover.

## Result 1: on the product's tree model

Regret, full sweep, 20,000 training deals, percent of optimal revenue.

| rho | Product (constrained) | Control function, constrained | Control function, unconstrained | Sees hidden quality |
|---|---|---|---|---|
| -0.9 | 32.4 | 27.9 | 26.6 | 19.5 |
| -0.6 | 22.5 | 20.6 | 16.8 | 18.0 |
| -0.3 | 15.8 | 16.4 | 10.8 | 16.4 |
| 0 | 9.5 | 11.6 | 10.0 | 15.4 |
| +0.3 | 4.1 | 11.3 | 11.3 | 16.2 |
| +0.6 | 2.0 | 10.6 | 9.9 | 13.9 |
| +0.9 | 1.7 | 11.4 | 10.4 | 13.0 |

Reading it:
- The control function brings every setting to roughly the 10 to 11% the tree
  model loses with no confounding at all. It removes the confounding and
  leaves the estimation error.
- That makes it worse than the product when strong deals get the discounts,
  because there the confounding was cancelling the model's under-reading
  (experiment 1).
- The model that sees hidden quality is worse than the product at rho = 0.
  With 50 shallow trees, a strong extra feature takes splits away from
  discount, so the discount curve gets flatter. It is not a real upper bound.

## Result 2: with a spline logistic win model

Regret, full sweep, percent of optimal revenue. "Diff" is control function
minus uncorrected, with its standard error across seeds.

### 20,000 training deals

| rho | Uncorrected | Control function | Diff (se) | Sees hidden quality |
|---|---|---|---|---|
| -0.9 | 6.2 | 2.3 | -3.9 (2.0) | 0.2 |
| -0.6 | 2.0 | 0.6 | -1.4 (0.4) | 0.1 |
| -0.3 | 0.6 | 0.2 | -0.3 (0.3) | 0.1 |
| 0 | 0.1 | 0.1 | +0.1 (0.0) | 0.1 |
| +0.3 | 4.1 | 0.1 | -3.9 (1.2) | 0.1 |
| +0.6 | 14.3 | 0.2 | -14.1 (1.6) | 0.1 |
| +0.9 | 19.7 | 0.4 | -19.4 (0.6) | 0.2 |

### 20,000 training deals, strong hidden quality (1.5)

| rho | Uncorrected | Control function | Diff (se) |
|---|---|---|---|
| -0.9 | 32.1 | 10.0 | -22.1 (4.6) |
| -0.6 | 28.9 | 5.2 | -23.7 (5.8) |
| -0.3 | 3.7 | 0.4 | -3.3 (0.7) |
| 0 | 0.2 | 0.3 | +0.1 (0.1) |
| +0.3 | 19.3 | 0.2 | -19.1 (0.8) |
| +0.9 | 22.6 | 0.7 | -21.9 (0.4) |

### 2,000 training deals (product-sized book)

| rho | Uncorrected | Control function | Diff (se) |
|---|---|---|---|
| -0.9 | 7.9 | 8.3 | +0.3 (3.0) |
| -0.6 | 3.6 | 8.5 | +4.9 (2.3) |
| -0.3 | 4.2 | 6.8 | +2.6 (1.4) |
| 0 | 6.1 | 4.8 | -1.4 (0.8) |
| +0.3 | 13.1 | 3.0 | -10.1 (1.5) |
| +0.6 | 17.1 | 2.3 | -14.8 (1.6) |
| +0.9 | 18.8 | 2.6 | -16.2 (1.0) |

Reading it:
- **The win model matters more than the correction.** With no confounding and
  20,000 deals, the spline model loses 0.1% where the product's tree model
  loses 9.5%. At 2,000 deals it is 6.1% against 17.1%.
- **The harmful direction flips with the model.** For the tree model, strong
  deals getting the discounts was harmless. For a model that fits the curve
  well, it is the worse direction: the model over-discounts (about 20 to 24%
  recommended where about 9% is best).
- **At 2,000 deals the method is not reliable on the rescue side.** It
  recommends about 14% where about 9% is best. The whole curve is identified
  from 12 reps' habits, which is thin.
- Inside the product's cohort-clipped sweep the pattern is the same at smaller
  scale: at 20,000 deals the control function is under 0.25% everywhere, and
  the uncorrected model reaches 14% at rho = +0.9.

## Result 3: the direction diagnostic

Share of books flagged, and the average test statistic. The statistic ignores
first-stage noise and rep clustering, so treat the thresholds as rough.

| Training deals | rho | Flagged rescue | Flagged whale | Mean z |
|---|---|---|---|---|
| 2,000 | -0.9 | 100% | 0% | -5.8 |
| 2,000 | -0.6 | 100% | 0% | -3.6 |
| 2,000 | -0.3 | 30% | 0% | -1.4 |
| 2,000 | 0 | 0% | 0% | 0.6 |
| 2,000 | +0.3 | 0% | 80% | 2.7 |
| 2,000 | +0.6 | 0% | 100% | 4.6 |
| 2,000 | +0.9 | 0% | 100% | 6.4 |
| 20,000 | every nonzero rho | 100% in the right direction | | 6.5 to 20 in size |
| 20,000 | 0 | 0% | 0% | -0.3 |

No book was flagged in the wrong direction, and none was flagged at
rho = 0, out of 10 books at 2,000 deals and 5 at 20,000.

## Result 4: breaking the instrument on purpose

Lenient reps are made weaker sellers (rep skill enters the win model with
weight 0.3, perfectly negatively related to the rep's discount bias). Spline
model, 20,000 deals, full sweep.

| rho | Uncorrected | Control function | Diagnostic says |
|---|---|---|---|
| -0.6 | 10.3 | 10.0 | "none detected" in 4 of 5 books |
| 0 | 2.1 | 8.3 | "whale" in 5 of 5 books (false alarm) |
| +0.6 | 0.4 | 7.7 | "whale" in 5 of 5 books |

The method attributes the lenient reps' lower win rate to the discount,
concludes that discounts work less well than they do, and under-discounts.
The first stage looks perfect throughout. This is the Chan, Gentzkow and Yu
(2022) critique, and it lands.

## What this means

**For the paper**
- The method claim survives in a narrower form: with a second stage that can
  represent the response and enough deals per rep, a rep-leniency control
  function recovers near-oracle recommendations in both directions. That is
  now shown on semi-synthetic data, not assumed.
- Three conditions have to be part of the claim, not footnotes: the win
  model's capacity, the amount of data per rep, and exclusion.
- **Abstention needs an exclusion check that we do not have.** The direction
  diagnostic cannot serve as one, since it fails in exactly the case that
  matters. Candidates from the literature review: the Frandsen, Lefgren and
  Leslie (2023) test, sensitivity bounds in the style of Conley, Hansen and
  Rossi (2012), or a rep-level check that leniency does not predict win rates
  on deals with no discount. This is the next thing to build.
- Experiment 1's finding (the monotone constraint costs regret) is specific
  to the tree model. The spline model has no constraint and a different
  failure direction.

**For the product (tickets, not changes today)**
- The largest regret found in any experiment so far is not from confounding.
  It is the win model's configuration under-reading the first few points of
  discount: 9.5% lost on an unconfounded 20,000-deal book where a spline
  logistic model loses 0.1%. Caveat: the generator's curve is smooth and
  additive, which suits a spline model, and the product's capacity was tuned
  on forward-fold skill, not regret.
- The direction diagnostic is cheap and could tell a customer which way their
  reps' discounting is confounded. It should not ship without the exclusion
  caveat.

## Limits

- Five to ten seeds per cell; several differences at 2,000 deals are within
  two standard errors.
- One generator. Reps are assigned at random and number 12 in every book.
  Non-random assignment and the number of reps are not yet varied.
- The spline model is close to the generator's true functional form (additive
  in covariates). A real book may not be.
- The diagnostic's z statistic is not cluster-robust.
- The cohort-clipped numbers score the argmax only, without the product's
  labels or its never-add-discount rule.

## Reproduce

```bash
python research/jair-discount-causality/run_leniency_experiment.py
```

```bash
python research/jair-discount-causality/run_spline_experiment.py
```

The first takes about 20 minutes. Results land in
`research/jair-discount-causality/results/`.
