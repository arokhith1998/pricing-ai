---
title: JAIR paper experiment 5, reps not assigned at random
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, experiment, instrument]
status: draft
source: research/jair-discount-causality/run_assignment_experiment.py
---

# Experiment 5: what if reps are not assigned to deals at random?

1,260 books, 30 seeds per cell, spline model, full 0 to 40% sweep. Regret is
mean (standard error) in percent of the revenue from the best discount given
a deal's covariates and its rep.

## Answer

**The prediction held. Assignment on things the book records is caught and
costs little. Assignment on hidden deal quality passes the standard check and
makes the leniency correction far worse than no correction.**

1. **Territories** (reps specialize by segment): the balance test flags every
   book. The correction loses about 1 to 3 points more than under random
   assignment and still beats the uncorrected model by 12 points when strong
   deals get the discounts.
2. **Sorting on hidden quality**: the balance test flags 3 to 7% of books, the
   same as random assignment. When strong deals are routed to lenient reps the
   corrected model loses 12 to 19% at a routing correlation of only 0.3, and
   about 20% at 0.6.
3. **The rep test catches sorting only on large books**: 29 to 86% of books at
   20,000 deals, 4 to 33% at 2,000.
4. **The direction diagnostic is wrong under sorting.** With no confounding
   and strong deals routed to lenient reps, it reports "rescue" in 30 of 30
   books.
5. **The robust rule helps and is not enough** when the sorting is stronger
   than the range it assumes.

## Mechanisms

| Name | What happens | Recorded in the book? |
|---|---|---|
| random | Any rep gets any deal | |
| territory 0.8, 1.0 | That share of deals goes to a rep whose home segment matches | Yes |
| sorting +0.3, +0.6 | Strong deals go to lenient reps, at that correlation between deal quality and the rep's leniency rank | No |
| sorting -0.3, -0.6 | Weak deals go to lenient reps | No |

Sorting at 0.3 gives a correlation of 0.29 between a deal's hidden quality and
its rep's leniency. At 0.6 it is 0.56.

## Results at 20,000 deals

| Mechanism | rho | Uncorrected | Corrected | Robust, calibrated | Robust, fixed 0.3 |
|---|---|---|---|---|---|
| random | -0.6 | 2.2 (0.2) | 2.9 (0.9) | 2.9 (0.9) | 4.0 (0.1) |
| random | 0 | 0.2 (0.1) | 1.3 (0.5) | 1.3 (0.5) | 3.7 (0.1) |
| random | +0.6 | 13.8 (0.9) | 1.4 (0.7) | 1.4 (0.7) | 3.4 (0.2) |
| territory 1.0 | -0.6 | 2.3 (0.4) | 4.1 (1.3) | 4.2 (1.3) | 4.6 (0.3) |
| territory 1.0 | 0 | 0.8 (0.4) | 3.4 (1.2) | 3.3 (1.2) | 4.2 (0.3) |
| territory 1.0 | +0.6 | 16.5 (0.7) | 4.0 (1.3) | 4.0 (1.3) | 5.0 (0.8) |
| sorting +0.3 | -0.6 | 1.2 (0.2) | 18.6 (0.8) | 18.0 (0.8) | 7.4 (0.3) |
| sorting +0.3 | 0 | 5.3 (0.8) | 15.7 (0.9) | 15.3 (0.9) | 7.1 (0.2) |
| sorting +0.3 | +0.6 | 17.1 (0.6) | 12.4 (1.0) | 12.3 (1.0) | 6.7 (0.3) |
| sorting +0.6 | -0.6 | 1.4 (0.3) | 21.2 (0.3) | 20.8 (0.3) | 13.7 (0.6) |
| sorting +0.6 | 0 | 14.2 (0.6) | 21.1 (0.3) | 20.8 (0.4) | 13.3 (0.6) |
| sorting +0.6 | +0.6 | 18.8 (0.4) | 19.5 (0.5) | 19.2 (0.5) | 11.7 (0.5) |
| sorting -0.3 | -0.6 | 3.8 (0.3) | 1.6 (0.2) | 1.6 (0.2) | 0.8 (0.1) |
| sorting -0.3 | 0 | 0.9 (0.1) | 2.8 (0.3) | 2.7 (0.3) | 1.0 (0.1) |
| sorting -0.3 | +0.6 | 7.3 (1.3) | 3.8 (0.3) | 3.6 (0.3) | 1.2 (0.2) |
| sorting -0.6 | -0.6 | 5.2 (0.3) | 5.8 (0.5) | 5.6 (0.4) | 3.0 (0.2) |
| sorting -0.6 | 0 | 2.5 (0.2) | 9.4 (0.7) | 8.7 (0.6) | 4.2 (0.2) |
| sorting -0.6 | +0.6 | 2.2 (0.7) | 15.2 (1.4) | 11.6 (0.8) | 4.5 (0.3) |

Territory 0.8 is within a point of territory 1.0 everywhere.

At 2,000 deals the pattern is the same with more noise: under sorting +0.3
the corrected model loses 14 to 18%, the fixed robust rule 9 to 10%.

## The checks

Share of books flagged at p < 0.05 (90 books per row).

| Mechanism | Balance test | Rep test, 20,000 deals | Rep test, 2,000 deals |
|---|---|---|---|
| random | 3% | 6% | 7% |
| territory 0.8 | 100% | 17% | 1% |
| territory 1.0 | 100% | 1% | 4% |
| sorting +0.3 | 3 to 7% | 29% | 4% |
| sorting -0.3 | 7% | 44% | 9% |
| sorting +0.6 | 3 to 7% | 79% | 17% |
| sorting -0.6 | 7% | 86% | 33% |

Direction diagnostic, 30 books per cell, 20,000 deals:

| Mechanism | True confounding | Says rescue | Says whale | Says none |
|---|---|---|---|---|
| random | none | 1 | 1 | 28 |
| sorting +0.3 | none | 30 | 0 | 0 |
| sorting -0.3 | none | 0 | 30 | 0 |
| sorting -0.6 | rescue | 0 | 9 | 21 |
| sorting +0.6 | whale | 9 | 1 | 20 |

## Reading it

- **This is Proposition 5 again.** Routing strong deals to lenient reps makes
  lenient reps win more for a reason unrelated to discount, exactly like
  leniency-aligned skill. The correction credits the discount, concludes
  discounts work better than they do, and over-discounts.
- **The two directions are not equally bad.** Strong deals to lenient reps
  costs 12 to 21%. Weak deals to lenient reps costs 2 to 15%.
- **The rep test has some power here that it lacked in experiment 3.** Sorting
  by rank is not an exactly linear function of leniency, and the additive
  spline model cannot absorb the difference. That power comes from the
  functional form, so it should not be relied on.
- **The balance test is uninformative about the case that matters**: it fires
  on the mechanism that is nearly harmless and stays quiet on the one that is
  not.
- **The uncorrected model is often the best rule under sorting.** In 9 of the
  12 sorting cells it beats the corrected model, in several by more than 10
  points.

## What this means for the paper

- The examiner-design literature leans on institutional random assignment
  (court rotas, call-centre queues). Sales organizations route deals
  deliberately, and a routing correlation of 0.3 with hidden quality is enough
  to make the correction harmful. The paper should say plainly that the
  leniency instrument is usable only where assignment is known to be
  rule-based: round-robin lead routing, inbound queues, or territory rules
  that the book records.
- The standard validity checks (balance, first-stage strength) pass in the
  failing case. First-stage strength is in fact slightly higher under
  sorting.
- This strengthens the analysis-paper framing: the result worth reporting is
  when correction hurts and that the usual checks do not warn of it.

## Limits

- One sorting mechanism (rank-based routing on a noisy read of quality).
- The fixed robust range (0.3) is too narrow for sorting at 0.6 by
  construction; a wider range would protect more and cost more.
- Territory assignment was tested with home segments unrelated to leniency.
- Regret is against the best discount given covariates and rep, so the
  figures for random assignment differ slightly from experiment 3's.

## Reproduce

```bash
python research/jair-discount-causality/run_assignment_experiment.py
```
