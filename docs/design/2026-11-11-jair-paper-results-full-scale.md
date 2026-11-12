---
title: JAIR paper results at full scale (30 seeds, rep count, capacity sweep)
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, experiment, results]
status: draft
source: research/jair-discount-causality/run_all.py
---

# Full-scale results: which findings survive

2,340 simulated books. 30 seeds per cell for experiments 1 to 4, 10 for the
capacity sweep. Every number below is mean (standard error across seeds) of
regret in percent of optimal revenue, full 0 to 40% sweep unless stated.
Tables come from `research/jair-discount-causality/summarize.py`. These
numbers supersede the 5-to-10-seed figures in the three experiment notes.

## Verdict

| # | Finding | Verdict at full scale |
|---|---|---|
| C1 | The monotone constraint costs regret under rescue confounding | **Survives, with a condition.** Clear at 50 to 200 trees. Not distinguishable from noise at the two largest capacities |
| C2 | The cohort clip does most of the protecting | **Survives** |
| C3 | Win-model capacity matters more than confounding | **Survives and is now explained:** too few boosting rounds |
| C4 | The harmful direction flips with the model | **Survives, and holds inside tree models too** |
| C5 | The leniency correction works at 20,000 deals, not at 2,000, and backfires under aligned skill | **Survives.** At 2,000 it tracks the oracle; the uncorrected model is better there by cancellation |
| C6 | Robust choice beats abstention | **Survives strongly** |
| new | The number of reps barely matters; the number of deals does | **New** |
| new | With more capacity the constraint also costs regret under whale confounding | **New, and not predicted by Proposition 4** |

Two earlier statements are corrected:
- The rep test's false-alarm rate is near its nominal 5% (5 of 90 and 6 of 90
  books with a valid instrument). The earlier "above nominal" was small-sample
  noise.
- At 2,000 deals the fixed robust rule is modestly better than the segment
  median in most cells (4.0 to 6.7 against about 7.0), not merely equal.

## 1. Monotone constraint, product tree model

Constrained minus unconstrained regret, in points.

| rho | 20,000 deals, full | 20,000, cohort clip | 2,000 deals, full | 2,000, cohort clip |
|---|---|---|---|---|
| -0.9 | +11.0 (1.0) | +0.9 (0.1) | +10.1 (1.8) | +1.3 (0.2) |
| -0.6 | +8.2 (0.6) | +0.7 (0.1) | +7.8 (1.3) | +0.7 (0.2) |
| -0.3 | +4.3 (0.5) | +0.3 (0.1) | +5.2 (0.9) | +0.4 (0.1) |
| 0 | +0.6 (0.3) | 0.0 (0.0) | +2.2 (0.7) | +0.1 (0.1) |
| +0.3 | -0.1 (0.3) | -0.1 (0.0) | +0.9 (0.4) | +0.1 (0.1) |
| +0.6 | -0.4 (0.2) | -0.1 (0.1) | +0.2 (0.2) | 0.0 (0.1) |
| +0.9 | -0.7 (0.2) | -0.4 (0.1) | -0.4 (0.2) | 0.0 (0.1) |

Levels at 20,000 deals, full sweep, constrained: 30.5, 22.1, 15.9, 9.3, 4.2,
1.8, 1.4 from rho = -0.9 to +0.9. Inside the cohort clip the worst case is
5.2.

## 2. Spline model, with and without the leniency correction

| rho | 20,000: uncorrected | 20,000: corrected | 20,000: sees quality | 2,000: uncorrected | 2,000: corrected | 2,000: sees quality |
|---|---|---|---|---|---|---|
| -0.9 | 6.0 (0.5) | 1.2 (0.4) | 0.3 (0.1) | 8.6 (1.5) | 7.4 (1.5) | 7.0 (1.5) |
| -0.6 | 2.3 (0.2) | 0.5 (0.1) | 0.2 (0.0) | 4.2 (0.8) | 8.1 (1.4) | 6.9 (1.3) |
| -0.3 | 0.6 (0.1) | 0.3 (0.1) | 0.2 (0.0) | 3.6 (0.9) | 6.5 (1.2) | 5.3 (1.2) |
| 0 | 0.2 (0.0) | 0.3 (0.0) | 0.2 (0.0) | 4.2 (1.1) | 4.3 (1.0) | 4.8 (1.1) |
| +0.3 | 4.7 (0.6) | 0.3 (0.0) | 0.2 (0.1) | 11.4 (1.1) | 4.1 (1.0) | 3.8 (1.0) |
| +0.6 | 13.7 (0.7) | 0.4 (0.1) | 0.3 (0.1) | 17.2 (0.8) | 3.3 (0.8) | 3.1 (0.8) |
| +0.9 | 18.4 (0.5) | 0.5 (0.1) | 0.3 (0.0) | 18.8 (0.5) | 3.3 (0.8) | 3.8 (1.0) |

- At 20,000 deals the correction is within a point of the model that sees
  hidden quality at every setting.
- At 2,000 deals the correction also tracks that model. It is worse than the
  uncorrected model under rescue confounding (+4.0 (1.2) at -0.6, +2.9 (0.8)
  at -0.3) because the uncorrected model's bias happens to offset its
  small-sample tendency to over-discount. The correction is working; the
  uncorrected model is lucky.

## 3. Number of reps

Corrected minus uncorrected regret, spline model.

| Reps | 20,000 deals: rho -0.6 | rho 0 | rho +0.6 | 2,000 deals: rho -0.6 | rho 0 | rho +0.6 |
|---|---|---|---|---|---|---|
| 6 | -0.8 (0.7) | 0.0 (0.0) | -14.1 (0.7) | +4.8 (1.5) | +0.5 (0.8) | -9.8 (0.9) |
| 12 | +0.2 (0.9) | +0.3 (0.2) | -13.2 (0.9) | +0.7 (1.2) | +0.3 (0.7) | -10.3 (0.9) |
| 25 | -0.1 (0.7) | +0.1 (0.1) | -12.6 (0.6) | +4.0 (1.0) | +0.7 (0.6) | -10.8 (0.9) |
| 50 | -1.0 (0.4) | +0.1 (0.0) | -11.0 (0.5) | +2.2 (1.1) | 0.0 (0.5) | -11.5 (0.8) |

- Six reps do about as well as fifty. With reps assigned at random, the
  number of deals limits the method, not the number of reps.
- The direction diagnostic never pointed the wrong way in 720 books. It read
  the right direction in 93 to 100% of confounded books, and raised a false
  alarm on 0 to 13% of unconfounded ones.
- This does not test non-random assignment, which is where few reps should
  hurt.

## 4. Broken instrument (20,000 deals)

| Scenario | rho | Uncorrected | Corrected | Robust, calibrated | Robust, fixed 0.3 | Segment median |
|---|---|---|---|---|---|---|
| valid | -0.6 | 2.2 (0.2) | 2.9 (0.9) | 2.9 (0.9) | 4.0 (0.1) | 6.9 (0.2) |
| valid | 0 | 0.2 (0.1) | 1.3 (0.5) | 1.3 (0.5) | 3.7 (0.1) | 6.8 (0.2) |
| valid | +0.6 | 13.8 (0.9) | 1.4 (0.7) | 1.4 (0.7) | 3.4 (0.2) | 6.8 (0.1) |
| aligned | -0.6 | 9.5 (0.5) | 9.5 (0.9) | 9.4 (0.9) | 3.2 (0.2) | 6.9 (0.2) |
| aligned | 0 | 2.1 (0.2) | 8.0 (0.6) | 7.9 (0.6) | 3.1 (0.2) | 6.9 (0.2) |
| aligned | +0.6 | 1.4 (0.5) | 7.6 (0.5) | 7.6 (0.5) | 3.6 (0.2) | 6.9 (0.1) |
| partial | -0.6 | 8.6 (0.5) | 8.2 (0.9) | 2.8 (0.2) | 2.3 (0.2) | 7.0 (0.2) |
| partial | 0 | 1.8 (0.2) | 7.0 (0.6) | 2.9 (0.2) | 2.3 (0.1) | 7.0 (0.2) |
| partial | +0.6 | 1.9 (0.7) | 6.6 (0.5) | 3.2 (0.2) | 2.7 (0.2) | 7.0 (0.1) |
| unaligned | -0.6 | 2.3 (0.2) | 2.8 (0.7) | 4.0 (0.1) | 4.0 (0.1) | 6.9 (0.2) |
| unaligned | 0 | 0.2 (0.0) | 0.8 (0.3) | 3.7 (0.1) | 3.8 (0.1) | 6.9 (0.2) |
| unaligned | +0.6 | 14.3 (0.9) | 0.6 (0.2) | 3.4 (0.2) | 3.5 (0.2) | 6.9 (0.1) |
| **Worst case** | | **14.3** | **9.5** | **9.4** | **4.0** | **7.0** |

- Worst case at 2,000 deals: uncorrected 15.2, corrected 16.5, calibrated
  15.5, fixed 6.7, segment median 7.1.
- Abstaining and falling back to the segment median is worse than the robust
  recommendation it replaces by 3.2 to 4.4 points (se about 0.1) at 20,000
  deals and 1.6 to 2.7 points at 2,000.
- Rep test: flags visible skill in 98 to 100% of books and estimates its size
  at 0.27 to 0.29 against a true 0.29 to 0.30. Flags aligned skill in 4 to 9%
  of books, the same as a valid instrument (6 to 7%).
- The fixed range still contains the truth by construction.

## 5. Tree capacity (10 seeds)

Label is trees x leaves; "child" is the minimum deals per leaf. Constrained
model. The true best discount averages about 8.6%.

| Capacity | 20,000 deals: rho -0.6 | rho 0 | rho +0.6 | Mean recommendation at rho 0 | 2,000 deals: rho 0 |
|---|---|---|---|---|---|
| Product: 50 x 7, child 150 | 22.6 (1.2) | 9.0 (0.7) | 1.4 (0.3) | 5.0% | 17.1 (2.6) |
| 200 x 7, child 150 | 11.9 (0.8) | 1.8 (0.4) | 6.7 (0.5) | 7.3% | 8.2 (1.5) |
| 500 x 7, child 50 | 11.0 (0.9) | 1.8 (0.2) | 11.0 (0.7) | 8.2% | 7.4 (1.1) |
| 500 x 15, child 50 | 10.3 (1.0) | 2.7 (0.3) | 12.2 (0.6) | 8.9% | 9.3 (0.9) |
| 500 x 15, faster learning, child 20 | 11.9 (0.9) | 4.9 (0.7) | 12.8 (0.6) | 10.3% | 11.5 (0.6) |

Constrained minus unconstrained, 20,000 deals:

| Capacity | rho -0.6 | rho 0 | rho +0.6 |
|---|---|---|---|
| Product: 50 x 7 | +7.9 (0.8) | +0.7 (0.4) | -0.5 (0.2) |
| 200 x 7 | +4.2 (0.5) | 0.0 (0.2) | +0.3 (0.2) |
| 500 x 7, child 50 | +3.0 (1.3) | -0.9 (0.4) | +1.0 (0.4) |
| 500 x 15, child 50 | +0.1 (2.1) | -0.9 (0.4) | +2.4 (0.3) |
| 500 x 15, faster learning | -1.5 (1.9) | -1.2 (0.5) | +2.3 (0.3) |

- **The under-reading is too few boosting rounds.** Going from 50 to 200 trees
  with nothing else changed cuts the unconfounded loss from 9.0% to 1.8% at
  20,000 deals and from 17.1% to 8.2% at 2,000. The spline model is at 0.2%
  and 4.2%.
- **More capacity moves the risk to the other side.** The product's small
  model is safe under whale confounding (1.4%) and exposed under rescue
  (22.6%). At 500 trees it loses 11 to 13% under whale confounding, by
  over-discounting to 18 to 20%.
- **The constraint's cost under rescue confounding shrinks with capacity**,
  from +7.9 to +3.0, and is inside the noise at the two largest settings.
- **At higher capacity the constraint costs regret under whale confounding**
  (+1.0 to +2.4 at 20,000 deals, +3.5 to +4.6 at 2,000). Proposition 4 says
  the constraint is inactive there in the population, so this is a
  finite-sample effect: it removes the noisy dips that would otherwise stop
  the model from recommending still more discount.

## What changes in the paper

- C1 is reworded: the constraint costs regret under rescue confounding at
  low to moderate capacity, and under whale confounding at high capacity. It
  never clearly helps. Proposition 4 covers the first; the second needs
  either a finite-sample argument or to be reported as an empirical finding.
- C3 is reworded: under-fitting from too few boosting rounds, not tree models
  as such.
- The practitioner table in the paper should be indexed by capacity as well
  as sample size and what is known about reps.
- The rep-count result weakens the "few reps" motivation for abstention. The
  open instrument question is now non-random assignment.

## Product notes (tickets, not changes)

- The shipped configuration (50 trees) recommends about 5% where about 8.6%
  is best on an unconfounded synthetic book. Two hundred trees recommends
  7.3%. Caveats: this is the full sweep, not the cohort-clipped rule the
  product uses; the capacity was tuned on forward-fold probability skill on a
  2,000-deal book, which is a different target; and more capacity raises the
  loss if strong deals get the deeper discounts.
- The direction diagnostic would tell a customer which of those two risks
  their book carries. That is the one piece of this work with an obvious
  product use.

## Limits

- One generator family, random rep assignment, a response that saturates.
- The capacity sweep has 10 seeds and no cohort-clipped scoring.
- The 2,000-deal rep-count cells use a different split from experiment 2, and
  the 12-rep cell differs from it (+0.7 against +4.0), which shows how much
  these small-book numbers move.

## Reproduce

```bash
python research/jair-discount-causality/run_all.py
```

```bash
python research/jair-discount-causality/summarize.py
```
