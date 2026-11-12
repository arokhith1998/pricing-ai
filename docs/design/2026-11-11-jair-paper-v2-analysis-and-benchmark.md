---
title: JAIR paper design v2, analysis and benchmark (discount causality)
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, design-doc]
status: active
source: https://www.jair.org/index.php/jair/about/submissions
---

# JAIR paper, version 2: an analysis and benchmark paper

Supersedes `2026-11-11-jair-paper-discount-causality.md` (the method-paper
plan). Decision to reposition: founder, 2026-11-11, after experiments 1 to 3.

Working title: **When does causal correction help discount recommendation?
Confounded discounts in negotiated pricing.**

## 1. The question and the answer we can defend

**Question.** A seller learns a win-probability model from past negotiated
deals and uses it to recommend discounts. The reps who set those discounts
knew things the model does not. When does that confounding change the
recommendation, when does correcting for it help, and when does correcting
hurt?

**Answer in one paragraph.** Mild confounding barely moves the recommendation.
Strong confounding can collapse it, and which direction is dangerous depends
on the win model, not only on the data. A monotone constraint, the standard
fix, repairs the curve that is displayed without repairing the decision, and
on a saturating response it makes the decision worse. A rep-leniency
instrument recovers near-optimal recommendations when the book is large and
the win model can represent the response, and does net harm when lenient reps
are also weaker sellers, a failure that no test on the deal book can detect.
A sensitivity range calibrated to visible rep differences bounds the damage in
most cases but not that one.

## 2. Contributions

**A. Theory (the methodological core; this is what keeps it out of
"application of known techniques").**

| # | Result | Status |
|---|---|---|
| A1 | Observational win curve under rep-driven confounding: closed form, pivot at the mean discount, sign-flip threshold | Proposition 1, sketched and simulated |
| A2 | A monotone constraint is inactive when the naive slope is positive and flat when it is negative; decision-neutral in the linear model | Proposition 2 and Corollary 2.1, sketched and simulated |
| A3 | Under a saturating response and rescue confounding, the constrained recommendation is weakly lower than the unconstrained one, so the constraint costs regret | Proposition 4, sketched and simulated. Holds for a concave response; the regret part needs the unconstrained pick to be at or below the optimum |
| A4 | The direction of the decision error depends on the optimum's position relative to the mean historical discount | Lemma 3.1, sketched and simulated |
| A5 | Regret is bounded, quadratic near zero error, and constant once the floor binds, which happens before the slope changes sign | Proposition 3, sketched and simulated |
| A6 | Leniency-aligned rep skill is observationally equivalent to a different discount effect: no test on (covariates, rep, discount, outcome) can detect it | Proposition 5, sketched and simulated. Exact in the additive model; a monotonicity belief gives partial leverage when lenient reps are weaker |

**B. Benchmark.** An open, seeded, semi-synthetic generator with a known
causal curve and these dials: confounding direction and strength, hidden
quality strength, sample size, rep skill and how closely it tracks leniency.
Scored by revenue regret against the truth, always reported next to the
zero-confounding baseline at the same sample size. Still to add: number of
reps, non-random rep assignment, response shape, share of zero-discount deals.

**C. Empirical findings.** Re-run at 30 seeds on 2026-11-11; see
`2026-11-11-jair-paper-results-full-scale.md`, which supersedes the wording
below where they differ. All six survive. C1 now depends on capacity, C3 is
traced to too few boosting rounds, the number of reps turns out not to
matter under random assignment, and the constraint also costs regret under
whale confounding at high capacity.

Original list:
1. The monotone constraint removes every falling curve and costs 6 to 11
   points of regret under rescue confounding on an unrestricted sweep.
2. Restricting recommendations to the cohort's observed range does most of
   the protective work.
3. Win-model capacity matters more than confounding at realistic sizes.
4. The harmful direction of confounding flips between an under-fitting and a
   well-fitting win model.
5. The leniency control function is near-oracle at 20,000 deals with a spline
   model, not useful at 2,000, and worse than no correction under aligned
   skill.
6. Robust choice over a sensitivity range dominates abstention.

**D. Tools** (studied, not headlined): the direction diagnostic, the rep
heterogeneity test, and the calibrated sensitivity range.

**Not claimed:** a new estimator; any result on customer data; that real books
show a particular direction or strength of confounding; anything about
Pricekeel's commercial outcomes.

## 3. Why this fits JAIR, and the desk-rejection risk

JAIR rejects "applications of known techniques without methodological
insight" and work "better suited to a specialized venue". Our defence:

- The insight generalizes beyond pricing: prescriptive models trained on
  logged human decisions, where a shape constraint is used to make the model
  look causal. That is a decision-focused-learning and causal-decision-making
  question, which JAIR publishes (Mandi et al. 2024; Ge et al. 2026).
- The paper leads with propositions A1 to A6. The benchmark supports them.
- Pricing is the worked setting, stated as such in the first paragraph.

If two outside readers still say it reads as a pricing application, fallback
venues in order: INFORMS Journal on Data Science, Transactions on Machine
Learning Research, Manufacturing and Service Operations Management.

## 4. Outline

1. Introduction: the three-way question; the monotone-constraint puzzle.
2. Setting and related work (customized pricing, examiner designs,
   decision-focused learning, deferral under hidden confounding).
3. Theory: A1, A2, A4, A5 in the linear-Gaussian model.
4. Beyond the linear model: A3 (saturating response).
5. Correcting with a rep-leniency instrument; A6 and what it rules out.
6. Benchmark design.
7. Experiments.
8. Guidance for practitioners: a decision table by book size, model class and
   what is known about reps.
9. Limitations (synthetic outcomes, one generator family, author's conflict
   of interest).
Appendix: proofs, reproducibility checklist, extra tables.

## 5. Work remaining

**Theory**
- A3 and A6 are now stated with proof sketches (Propositions 4 and 5).
  Turn all six sketches into full proofs.
- A human checks every proof. The sketches were machine-drafted.

**Experiments**
- Done 2026-11-11: 30 seeds per cell, the rep-count dial, the capacity sweep.
- Still open: 30 seeds and cohort-clipped scoring for the capacity sweep.
- Dials not yet run: number of reps (8, 12, 25, 50); non-random assignment;
  response shape (linear, threshold); zero-discount share.
- Capacity sweep for the tree model: is the under-reading capacity, or trees?
  This decides how finding C3 is worded, and it is also a product question.
- Comparators a reviewer will expect: linear IV with weak-instrument-robust
  intervals, the GRF instrumental forest, Kallus and Zhou's robust policy.
  Miao et al. if code exists.
- Cluster-robust version of the direction diagnostic and the rep test (the
  current false-alarm rate is above nominal).
- Real-covariate check on the Columbia CPRM auto-lending data if it can still
  be downloaded, with simulated reps and outcomes.

**Reading (by the founder, before the related-work section)**
The eight papers in section 7 of the literature review, plus Fernandez-Loria
and Provost (2022).

## 6. Plan

| Weeks | Work | Gate |
|---|---|---|
| 1 (done) | Literature review, propositions, experiments 1 to 3, repositioning | Founder decision made |
| 2 to 3 | A3 and A6 statements and proofs; human proof check; reading | Proofs hold, or the claims are cut |
| 3 to 5 | Remaining dials, capacity sweep, 30 seeds, robust diagnostics | Findings C1 to C6 survive, or are reworded |
| 5 to 6 | Comparators; real-covariate check | |
| 6 to 9 | Draft in the JAIR template; structured abstract | Full draft |
| 9 to 10 | Second-model critique (`tools/oai_review.py`), mle-reviewer, one outside academic read | Venue-fit verdict from two readers |
| 11 | Reproducibility checklist, code release form, three required answers | Founder approval to submit |

**Stop conditions**
- A3 or A6 fails as a general statement and cannot be rescued with a clear
  condition: cut that claim. If both fail, drop to a JAIR research note.
- Findings C1 or C3 disappear at 30 seeds or under the capacity sweep: the
  paper loses its two most surprising results. Stop and reassess.

## 7. JAIR's required answers (first drafts, to be rewritten by the author)

**Why it matters to AI researchers (limit 150 words).**
Models trained on logged human decisions are increasingly used to recommend
those same decisions. When the humans acted on information the model lacks,
predictive accuracy stops implying decision quality. We study this in
negotiated pricing, where a known ground truth lets us measure regret. We show
analytically when confounding changes the recommended action, that a
monotonicity constraint, widely used to make such models look causal, repairs
the fitted curve but not the decision, and that an instrument built from
decision-maker leniency can fail undetectably. We release a benchmark with
dials for the strength and direction of confounding, sample size, and
instrument validity. Researchers can use the results to decide when a causal
correction is worth its variance, and the benchmark to test decision-focused
and causal policy-learning methods under controlled violations of their
assumptions.

**Closest JAIR papers (limit 150 words).** To be written after reading all
three in full: Ge et al. (2026), a survey of causal decision making, where we
contribute new analytical results and a benchmark; Mandi et al. (2024), which
benchmarks decision-focused learning assuming the training data sample the
decision environment faithfully, where ours do not; Kube, Das and Fowler
(2023), counterfactual prediction for allocation under selection on
observables, where we assume hidden confounding.

**Prior publication.** No.

## 8. Standing rules for this paper

- Synthetic and public data only. No customer data, ever.
- Every number in the paper is regenerated by a committed script from a fixed
  seed list.
- Disclose the author's role at Pricekeel.
- JAIR's AI-use policy: AI tools assisted with literature search, simulation
  code and drafting. The core contributions and every citation are the
  author's responsibility. Keep a log of where AI tools were used.
- Citations tagged [A], [S] or [M] in the literature review are not usable
  until checked against the source.
- This is a credibility asset. ADR-008 Phase 1 work comes first.

## 9. Open founder decisions

1. Co-author: an academic in causal inference or marketing science would help
   most with A3, A6 and venue fit. Approach one now, or after a draft?
2. Weekly time budget, mainly for the proof check and the reading.
3. Whether the two product findings (monotone constraint, model capacity)
   become board tickets now or after the capacity sweep.
