---
title: JAIR paper design doc, discount causality in negotiated B2B pricing
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, win-model, design-doc]
status: draft
source: https://www.jair.org/index.php/jair/about/submissions
---

# JAIR paper: identification-aware discount guidance for negotiated B2B deals

Status: approved by the founder 2026-11-11. Nothing is built yet. Target
venue: JAIR, full-length article. Target submission: about 14 weeks from
approval.

**Week 1 update (2026-11-11):** the literature review is in
`2026-11-11-jair-paper-literature-review.md`. The kill criterion was not
triggered. Its section 6 supersedes parts of sections 3 to 5 below: C3 is
reframed around instrument diagnostics deciding when to abstain, C2 is
narrowed to the sign-flip regime, the baseline list changes, and the
real-covariate check must simulate rep identities because no public dataset
has them.

**Propositions (2026-11-11):** `2026-11-11-jair-paper-propositions.md` works
out C1 and C2 in a linear-Gaussian model and corrects this doc in three
places. The monotone constraint turns out to be decision-neutral (same
recommendation, different curve). The direction of the decision error depends
on where the optimum sits relative to the mean historical discount, so the
"rescue recommends too little, whale too much" wording in sections 1 and 4 is
wrong for mild confounding. Regret is a cliff in the rescue direction, not
"quadratic then linear".

## 1. One-sentence claim

When sales reps choose discounts based on information the model cannot see,
a win-probability model that predicts well still recommends the wrong
discount, the common shape-constraint fix only corrects one direction of that
error, and a recommender that uses rep discounting habits as an instrument,
and abstains when the instrument cannot identify the effect, cuts decision
regret in the regimes where it matters.

## 2. Why this is a research question and not a product note

Three facts from our own code motivate it:

1. `pricing/model.py` says discount is endogenous ("reps discount harder on
   deals already in trouble") and fixes it with a +1 monotone constraint on
   `discount_pct`. That fix forces the sign. It does not correct the size of
   the slope, and it assumes the bias always runs in one direction.
2. `pricing/generate.py` does not actually encode that endogeneity. Discount
   depends on segment, competitor, quarter-end pressure and rep bias, all
   observed. The latent `quality` term enters the win logit only. So the
   synthetic book never tests the problem the constraint was added for. This
   is worth knowing for the product too.
3. In the generator, rep bias moves the discount and does not enter the win
   logit. That is exactly the exclusion structure an instrument needs, and it
   mirrors the judge-leniency designs used in economics. Real books have the
   same shape: a few dozen reps with stable, different discounting habits.

The general lesson for AI researchers: in prescriptive ML on logged human
decisions, predictive accuracy and decision quality can disagree, and the
direction of the disagreement depends on why the human chose the action.

## 3. Prior work we must beat or differentiate from (week 1 to verify)

| Work | What it does | How we differ |
|---|---|---|
| Karlinsky-Shichor and Netzer, "Automating the B2B Salesperson Pricing Decisions" (Marketing Science) | Empirical B2B salesperson pricing, IV probit, human-machine hybrid | We contribute a method plus identification analysis plus abstention, evaluated by regret against known ground truth |
| Bockel-Rickermann et al. 2023, arXiv 2309.03730 | Selection bias in bid-response functions, semi-synthetic mortgage data, causal ML | Consumer lending with posted-style rates and no instrument. We study unobserved confounding with a rep instrument in negotiated deals |
| Phillips, Simsek, van Ryzin 2015 (Management Science), field price discretion | Shows that sales discretion carries information | Motivates the confounding; does not give a recommender |
| Hartford et al. 2017 DeepIV; Singh et al. 2019 Kernel IV; Xu et al. 2021 DFIV | Nonparametric IV, with a simulated airline pricing demo in DeepIV | Baselines for us. They assume strong instruments and many clusters, judge on prediction error not decision regret, and never abstain |
| Athey, Tibshirani, Wager 2019, generalized random forests (IV forest) | Local IV effects | Baseline |
| Miao et al. 2023, arXiv 2302.12670, personalized pricing with invalid IVs | Identification under invalid instruments | Closest on the theory side; we must read it in full and either use or contrast its bounds |
| Gupta and Kamble 2026, "Causal Multi-Task Demand Learning", arXiv 2602.09969 | Multi-task demand learning under confounding; shows a sign reversal driven by pricing behaviour | Posted-price retail, linear response, no instrument, no constraint analysis |
| Chernozhukov et al. 2018, double ML | Debiased effects under no unobserved confounding | Baseline that fails by design here, which is part of the point |

Open question for week 1: the JAIR submission form asks for the 1 to 3
closest JAIR papers. We have not found any JAIR paper on this yet. Candidates
to search: JAIR causal inference, off-policy learning, and preference or
mechanism papers.

**Kill criterion:** if week 1 or 2 turns up a paper that already does an
instrumented recommender plus decision-regret evaluation plus shape-constraint
analysis for negotiated quotes, we drop to a research note or switch to the
survey (Topic 3).

## 4. Contributions (what the paper will claim)

C1. **Sign result.** Under "rescue" confounding (reps discount harder on weak
deals), naive and monotone-constrained models flatten the win curve and
recommend too little discount. Under "whale" confounding (reps discount
harder on must-win strong deals), they steepen it and recommend too much.
The monotone constraint helps only in the first case. Stated as a
proposition with a proof sketch for a single-index logit model, then shown
empirically.

C2. **Regret is roughly quadratic in slope error near the optimum and linear
once the error flips the sign of the marginal effect.** Small biases are
cheap and sign errors are expensive. This tells practitioners when a
correction is worth its variance.

C3. **Method.** A control-function recommender. First stage: leave-one-out
rep leniency (as in judge designs), conditional on segment and territory.
Second stage: a flexible win model with the control residual added. Paired
with **partial-identification bounds** when the first stage is weak (few
reps) or the exclusion restriction is doubtful (rep skill affects wins). The
recommender then returns a robust discount (max-min expected booked ACV over
the identified set) or abstains to the existing band guardrail.

C4. **Benchmark.** An open, seeded, semi-synthetic generator with dials for
confounding strength and direction, number of reps, instrument strength,
exclusion violation, curve shape and sample size, plus regret computed against
the true data-generating process.

Non-claims: no claim of results on customer data, no claim that real books
show any particular confounding direction, and no claim about Pricekeel
commercial outcomes.

## 5. Experimental design

**Data-generating process.** A research copy of the generator under
`research/jair-discount-causality/`, not edits to `pricing/generate.py`,
because the pinned dataset and model tests depend on its RNG stream. Dials:

| Dial | Values |
|---|---|
| Confounding direction | none, rescue, whale |
| Confounding strength gamma | 0, 0.01, 0.02, 0.04 (discount points per SD of latent quality) |
| Number of reps R | 8, 12, 25, 50 |
| Rep bias SD (instrument strength) | 0.01, 0.035, 0.06 |
| Exclusion violation delta (rep skill in win logit) | 0, 0.1, 0.3 |
| Rep assignment | random, territory (rep correlated with segment) |
| True discount effect | saturating tanh (current), linear, threshold |
| n deals | 500, 2,000, 10,000 |
| Seeds | 30 per cell |

**Methods.** B1 logistic regression. B2 LightGBM unconstrained. B3 LightGBM
with the monotone constraint (current product). B4 double ML. B5 DeepIV or
DFIV. B6 IV forest. M1 control function. M2 control function with bounds and
abstention (ours).

**Metrics.** Primary: decision regret, meaning true expected booked ACV at
the optimal discount minus at the recommended one, as a percent of list.
Secondary: discount error in points, coverage of bounds, the regret versus
abstention-rate curve, and AUC and Brier score (reported to show they
disagree with regret).

**Real-covariate check.** A semi-synthetic run on a public negotiated-price
dataset with simulated outcomes. Candidate: the Columbia CPRM / Nomis
auto-loan quote data used in the customized-pricing literature (availability
and licence to verify in week 1). No Pricekeel customer data is used, ever.

**Reproducibility.** Every figure is regenerated by one command from a fixed
seed list. Code is released under a permissive licence with the JAIR source
code release form. The JAIR reproducibility checklist is filled in as we go,
not at the end.

## 6. Plan

| Week | Work | Gate |
|---|---|---|
| 1 to 2 | Literature: read the table in section 3 in full, search for JAIR comparators, check dataset access | Kill criterion check |
| 2 | Write C1 and C2 as propositions with proof sketches | Founder plus one outside reviewer read |
| 3 to 5 | Research generator, method code, tests on the generator itself (true optimum recovered when gamma is 0) | Tests green, committed |
| 5 to 8 | Full sweep, figures | Results reviewed by the mle-reviewer agent and a second model via `tools/oai_review.py` |
| 8 to 9 | Real-covariate check | |
| 9 to 12 | Write-up in the JAIR LaTeX template, structured abstract, limitations | Full draft |
| 12 to 13 | External read (ideally an academic co-author), revise | |
| 14 | Checklist, the three required answers, code release, submit | Founder approval to submit |

Time budget assumed: 5 to 6 hours a week from the founder, the rest
delegated. If that drops, the plan stretches. It does not get cut.

## 7. Risks

- **Novelty.** "IV beats naive under confounding" is known. The paper lives
  or dies on C1, C2 and the abstention design. If those do not hold up in
  week 2, stop.
- **Weak instruments.** With 8 to 12 reps the first stage is thin. That is a
  feature for the paper (it motivates the bounds) but it can make M2 abstain
  so often that it is useless. We report that honestly.
- **Synthetic-only results.** Reviewers may push for real data. The
  ground-truth argument (regret can only be measured when the true curve is
  known) is our answer, along with the real-covariate check.
- **Conflict of interest.** The author founded a company that sells discount
  guidance. Disclose it in the paper.
- **AI-use policy.** JAIR allows AI help with analysis and editing, but the
  core contributions must be the authors'. Keep a log of where AI tools were
  used and review every citation by hand.
- **Focus.** ADR-008 Phase 1 (pitching to 10) comes first. This is a
  credibility asset, not a substitute.

## 8. Founder decisions needed

1. Approve the claim in section 1 and the contributions in section 4.
2. Co-author: go solo, or approach an academic (operations research or
   marketing science) now.
3. Time budget per week.
4. Product follow-up: if the paper confirms C1, the win model's monotone
   constraint needs revisiting. That is a separate ticket after the results,
   not part of the paper.

## 9. Product finding surfaced while writing this

`pricing/generate.py` has no unobserved confounding, so the synthetic book
cannot show whether the monotone constraint in `pricing/model.py` helps or
hurts. Worth a board ticket independent of the paper.
