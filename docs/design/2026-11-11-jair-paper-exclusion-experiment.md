---
title: JAIR paper experiment 3, guarding against a broken instrument
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, experiment, instrument, sensitivity]
status: draft
source: research/jair-discount-causality/run_exclusion_experiment.py
---

# Experiment 3: can the method tell when it should not be trusted?

Code: `research/jair-discount-causality/exclusion.py`. Spline control function
throughout, full 0 to 40% sweep. Train and test deals share the same 12 reps.

## Answer

**Only partly, and the abstention design in the original plan does not hold
up.**

1. **The dangerous case cannot be detected.** If rep skill lines up exactly
   with leniency, the rep test sees nothing, as the theory says it must.
2. **Skill that does not line up with leniency is detected every time**, and
   its size is estimated accurately.
3. **Choosing robustly works better than abstaining.** Picking the discount
   with the smallest worst-case regret across a range of assumed direct
   effects keeps the loss under 4% in every scenario at 20,000 deals.
   Abstaining and falling back to the segment's median discount loses about
   7%, because that fallback is a poor recommendation.
4. **The insurance has a price.** When the instrument is valid, the robust
   rule loses about 3.5% where the plain method loses under 1.4%.
5. **At 2,000 deals nothing reliably beats the segment median.**

## What was built

- **Rep test.** After fitting the control function, do reps still differ in
  win rate by more than chance? Reports a p-value and tau, the spread of
  unexplained rep effects in logit units.
- **Robust recommender.** Refit assuming leniency moves the win logit directly
  by delta per standard deviation, for seven values of delta across a range.
  Recommend the discount whose worst-case regret across those fits is
  smallest.
  - *Fixed range:* delta from -0.3 to +0.3, chosen by the analyst.
  - *Calibrated range:* delta from -tau to +tau, read off the rep test. The
    assumption is that hidden, leniency-aligned skill is no larger than the
    skill differences we can see.
- **Abstention.** If a deal's best discount moves more than 5 points across
  the range, fall back to the segment's median historical discount.

## Scenarios

| Name | Rep skill | Aligned with leniency | Direct effect per sd of leniency |
|---|---|---|---|
| valid | none | | 0 |
| aligned | 0.3 | fully | -0.30, invisible |
| partial | 0.4 | 70% | -0.28, plus 0.29 visible |
| unaligned | 0.3 | not at all | 0, plus 0.30 visible |

The fixed range was set to 0.3, and the true aligned effect is 0.30 or less in
every scenario. That favours the fixed rule by construction. A book with a
larger aligned effect than the analyst assumed would not be protected.

## Results at 20,000 training deals

Regret, percent of optimal revenue, mean of 5 seeds.

| Scenario | rho | Uncorrected | Control function | Robust, calibrated | Robust, fixed 0.3 | Segment median |
|---|---|---|---|---|---|---|
| valid | -0.6 | 2.3 | 1.4 | 1.4 | 3.6 | 7.0 |
| valid | 0 | 0.2 | 0.3 | 0.3 | 3.5 | 7.1 |
| valid | +0.6 | 11.2 | 0.5 | 0.4 | 3.2 | 7.0 |
| aligned | -0.6 | 8.9 | 7.8 | 7.8 | 3.4 | 7.0 |
| aligned | 0 | 2.5 | 7.1 | 7.1 | 3.0 | 7.1 |
| aligned | +0.6 | 0.4 | 6.7 | 6.7 | 3.3 | 7.0 |
| partial | -0.6 | 8.9 | 7.1 | 3.0 | 2.4 | 7.1 |
| partial | 0 | 2.5 | 6.4 | 2.9 | 2.1 | 7.2 |
| partial | +0.6 | 0.8 | 5.8 | 2.8 | 2.2 | 7.1 |
| unaligned | -0.6 | 2.3 | 3.2 | 3.8 | 3.9 | 7.0 |
| unaligned | 0 | 0.2 | 1.0 | 3.6 | 3.7 | 7.2 |
| unaligned | +0.6 | 13.4 | 1.2 | 3.4 | 3.5 | 7.0 |
| **Worst case** | | **13.4** | **7.8** | **7.8** | **3.9** | **7.2** |

### The rep test

| Scenario | Mean tau (true visible spread) | Books flagged at p < 0.05 |
|---|---|---|
| valid | 0.01 (0) | 1 of 15 |
| aligned | 0.01 (0) | 3 of 15 |
| partial | 0.28 (0.29) | 15 of 15 |
| unaligned | 0.29 (0.30) | 15 of 15 |

### Abstention

With the fixed range, the best discount moves more than 5 points for 78 to 98%
of deals at 20,000 training deals, so the rule abstains on almost everything
and lands near the segment median's 7%. With the calibrated range it abstains
on 79 to 98% of deals in the partial and unaligned scenarios, with the same
result. At 20,000 deals, abstaining never beat the robust recommendation it
replaced. At 2,000 deals it was ahead in a few cells by under 0.3 points,
which is inside the noise.

## Results at 2,000 training deals

Mean of 10 seeds.

| Scenario | rho | Uncorrected | Control function | Robust, calibrated | Robust, fixed 0.3 | Segment median |
|---|---|---|---|---|---|---|
| valid | -0.6 | 4.6 | 8.7 | 8.3 | 7.6 | 7.0 |
| valid | 0 | 6.2 | 7.1 | 6.8 | 6.0 | 7.0 |
| valid | +0.6 | 16.2 | 8.6 | 8.5 | 7.5 | 7.1 |
| aligned | -0.6 | 18.3 | 18.2 | 17.8 | 7.5 | 7.1 |
| aligned | 0 | 8.4 | 13.5 | 13.1 | 5.2 | 7.1 |
| aligned | +0.6 | 6.4 | 12.1 | 11.9 | 5.8 | 7.1 |
| partial | -0.6 | 13.1 | 12.8 | 6.3 | 6.6 | 7.2 |
| partial | 0 | 7.9 | 12.3 | 7.7 | 5.2 | 7.2 |
| partial | +0.6 | 6.0 | 11.0 | 5.9 | 4.4 | 7.2 |
| unaligned | -0.6 | 4.8 | 7.0 | 7.6 | 7.6 | 7.1 |
| unaligned | 0 | 5.1 | 6.1 | 5.7 | 5.8 | 7.1 |
| unaligned | +0.6 | 15.8 | 6.5 | 7.5 | 7.5 | 7.2 |
| **Worst case** | | **18.3** | **18.2** | **17.8** | **7.6** | **7.2** |

At this size the rep test still flags the partial and unaligned scenarios in
every book. The recommendations are the problem: the best any rule does is
roughly match recommending each segment's median historical discount.

## Reading it

- **Recommendations are fragile to the exclusion assumption.** A direct effect
  of 0.3 logit per standard deviation of leniency, which is a modest skill
  difference, moves the best discount by more than 5 points for most deals.
- **The calibrated range is the useful new idea, with a hole.** It costs
  nothing when the instrument is valid (tau is about zero, so it reduces to
  the plain method), and it works when some skill is visible. It gives no
  protection in the fully aligned case, because there is nothing to calibrate
  from.
- **The uncorrected model is sometimes the best rule.** In the aligned
  scenario at rho of 0 or +0.6 it loses 0.4 to 2.5% while the control function
  loses about 7%. A method that removes confounding can do net harm when its
  own assumption fails.
- **No rule wins everywhere.** The fixed robust rule has the best worst case
  and is never the best in any single scenario.

## Where the paper stands after four experiments

The original plan was a method paper: an instrumented recommender that
abstains when identification fails (C3). The evidence now says:

| Planned claim | Status |
|---|---|
| C1, monotone constraint | **Holds, sharper than planned.** Repairs the displayed curve; neutral at the floor; costs regret on a saturating curve under rescue confounding (experiment 1) |
| C2, regret cliff | **Holds in the simplified model, weaker on the generator.** A cliff only with strong hidden quality |
| C3, instrument plus abstention | **Mostly does not hold as planned.** The instrument works at 20,000 deals with a suitable win model. Abstention is dominated by robust choice. The key failure cannot be detected. Nothing helps at 2,000 deals |
| C4, benchmark | **Holds and has grown.** Dials for confounding direction and strength, hidden-quality strength, sample size, rep skill and its alignment, with regret against a known truth |

Findings that were not in the plan and may be the strongest material:
- The win model's capacity matters more than confounding at realistic sizes.
- Which direction of confounding hurts depends on the win model.
- Aligned rep skill is undetectable and makes correction worse than none.

**Recommendation:** reposition from "a new method" to "an analysis and
benchmark": when does causal correction change discount recommendations, when
does it help, and when does it hurt. The control function and the calibrated
sensitivity range become the tools studied, not the headline. That is a more
honest paper and, given how much of C3 is prior art, probably a more
defensible one at JAIR. It is the founder's call.

## Limits

- Five seeds at 20,000 deals, ten at 2,000. Twelve reps, randomly assigned.
- The rep test is approximate: it ignores the estimation of the other
  coefficients and of the first stage. Its false-alarm rate here (4 of 30
  books with no visible skill at 20,000 deals, 6 of 60 at 2,000) is above the
  nominal 5%.
- The fixed range contains the truth in every scenario by construction.
- The spline model is close to the generator's true form.
- Experiment 2's broken-instrument rows drew test deals from a different book,
  so their reps were unrelated to the training reps. Here they are shared.
  The conclusion is the same; the numbers differ slightly.

## Reproduce

```bash
python research/jair-discount-causality/run_exclusion_experiment.py
```

Takes about 15 minutes. Writes
`research/jair-discount-causality/results/exclusion_experiment.csv`.
