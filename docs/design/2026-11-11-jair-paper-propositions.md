---
title: JAIR paper propositions, bias direction, the monotone constraint, and regret
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, propositions]
status: draft
source: docs/design/2026-11-11-jair-paper-discount-causality.md
---

# Propositions for the discount-causality paper (draft 1)

Proof sketches, not finished proofs. Every numbered claim is checked
numerically by `research/jair-discount-causality/verify_propositions.py`
(all assertions pass, seed 7). A human needs to check the algebra before any
of this goes into a manuscript.

**Headline: working these out changed three things the design doc said.**
1. The monotone constraint does not change the recommended discount at all in
   this model. It only changes the curve that is shown.
2. The direction of the decision error is not "rescue means too little
   discount, whale means too much". It depends on where the optimum sits
   relative to the average historical discount.
3. Regret is not "quadratic, then linear". It is small for mild confounding in
   either direction, then falls off a cliff in the rescue direction.

## Setup

One cohort, observed covariates suppressed (everything below holds
conditional on them).

- Latent deal quality $q \sim N(0,1)$, seen by the rep, not by the model.
- Discount: $d = m + \gamma q + \eta$, with $\eta \sim N(0,\sigma^2)$
  independent of $q$. Write $\sigma_d^2 = \gamma^2 + \sigma^2$ and
  $\rho = \mathrm{corr}(d,q) = \gamma/\sigma_d$.
- Outcome: $Y = 1\{\alpha + \theta d + \beta q + \varepsilon > 0\}$,
  $\varepsilon \sim N(0,1)$, with $\theta > 0$ (discount helps) and
  $\beta > 0$ (quality helps).
- **Rescue** confounding is $\rho < 0$: deeper discounts on weak deals.
  **Whale** confounding is $\rho > 0$: deeper discounts on strong deals.
- The seller picks $d \in [d_{lo}, d_{hi}] \subset [0,1)$ to maximize expected
  booked ACV per dollar of list, $R(d) = (1-d)\,p(d)$.

The causal win curve is

$$p^*(d) = P(Y=1 \mid do(d)) = \Phi(a^* + b^* d),\quad
a^* = \frac{\alpha}{\sqrt{1+\beta^2}},\ b^* = \frac{\theta}{\sqrt{1+\beta^2}}.$$

## Proposition 1 (what a predictive model learns)

The observational win curve is also a probit in $d$:

$$P(Y=1 \mid d) = \Phi(a_{obs} + b_{obs} d),\qquad
b_{obs} = \frac{\theta + \beta\rho/\sigma_d}{\sqrt{1+\beta^2(1-\rho^2)}}.$$

Consequences:

1. **Whale always steepens.** If $\rho > 0$ then $b_{obs} > b^*$.
2. **Rescue flattens for mild confounding, and can reverse the sign.**
   $b_{obs} < 0$ exactly when $\rho < -\theta\sigma_d/\beta$.
3. **Rescue does not always flatten.** The denominator shrinks as $|\rho|$
   grows, because conditioning on $d$ explains part of $q$. When the true
   effect is very large relative to the quality effect
   ($\theta\sigma_d \gg \beta$), $b_{obs} > b^*$ is possible with $\rho < 0$.
   The first-order effect in $\rho$ always has the sign of $\rho$.
4. **The naive curve pivots at the mean discount.** At $d = m$ the
   confounding term vanishes, so the naive and causal curves agree there up to
   the scale factor. Confounding rotates the curve around the historical mean.

*Sketch.* $q \mid d$ is normal with mean $(\rho/\sigma_d)(d-m)$ and variance
$1-\rho^2$. Substitute into the outcome equation and integrate out the normal
residual.

*Check.* Fitted probit slopes on 400,000 simulated deals match the formula
within 0.09 at eight values of $\rho$.

## Proposition 2 (what the monotone constraint does)

Let the constrained model be the population log-loss minimizer over all
functions of $d$ that are non-decreasing.

1. If $b_{obs} \ge 0$, the constraint is inactive. The constrained and
   unconstrained fits are the same function.
2. If $b_{obs} < 0$, the constrained fit is the constant $P(Y=1)$: the model
   reports that discount has no effect on winning.

So the constraint never moves the slope toward $b^*$ when the naive slope is
positive. That covers every whale case and every mild rescue case. When it
does act, it replaces a wrong negative slope with a wrong zero slope.

*Sketch.* The minimizer is the isotonic regression of the observational curve
under the distribution of $d$ (isotonic regression minimizes log loss as well
as squared loss; Robertson, Wright and Dykstra 1988, citation from memory, to
confirm). A non-decreasing target is its own isotonic regression. The isotonic
regression of a strictly decreasing target is its mean.

*Check.* Isotonic fits on simulated data: flat to three decimals at
$\rho=-0.8$; within 0.016 of the naive curve at $\rho=-0.3$ and $\rho=0.5$.

### Corollary 2.1 (the constraint is decision-neutral)

> **Tested 2026-11-11, see `2026-11-11-jair-paper-constraint-experiment.md`.**
> On the generator's saturating curve this holds only once the recommendation
> has collapsed to the floor. Under moderate rescue confounding the
> constrained model is worse than the unconstrained one by 6 to 11 points of
> regret on a full sweep, because the observed curve is a hump and the
> constraint flattens its rising side. The corollary is correct for the
> linear model below and should not be read as a general result.

In this model the constrained and unconstrained models recommend the same
discount for every $\rho$.

*Sketch.* If $b_{obs} \ge 0$ the two models are identical. If $b_{obs} < 0$,
the unconstrained model believes winning gets less likely as discount rises
and the constrained model believes it is unaffected. Under either belief,
$(1-d)\hat p(d)$ is strictly decreasing, so both pick $d_{lo}$.

What the constraint does change is the curve and the explanation shown to a
user. It turns a visibly wrong answer (discounts hurt) into a plausible one
(discounts do nothing) with the same recommendation and the same regret.

## Proposition 3 (regret)

Let a model believe $\hat p(d) = \Phi(\hat a + \hat b d)$ and recommend
$\hat d = \arg\max (1-d)\hat p(d)$. Regret is $R(d^*) - R(\hat d)$ under the
causal curve.

1. **Bounded.** $R$ is single-peaked, so regret never exceeds
   $\max\{R(d^*)-R(d_{lo}),\ R(d^*)-R(d_{hi})\}$.
2. **Quadratic for small errors.** For interior $d^*$,
   regret $= \tfrac12 |R''(d^*)|(\hat d - d^*)^2 + o((\hat d-d^*)^2)$, and
   $\hat d - d^*$ is locally linear in $(\hat a - a^*, \hat b - b^*)$.
3. **The floor binds before the sign flips.** $\hat d = d_{lo}$ exactly when
   $(1-d_{lo})\,\hat b\, r(\hat a + \hat b d_{lo}) \le 1$, where
   $r = \phi/\Phi$. That holds for small positive $\hat b$. From there on
   regret is the constant $R(d^*) - R(d_{lo})$, however negative the slope
   becomes.

*Sketch.* $\Phi$ is log-concave, so $\log R$ and $\log \hat R$ are concave on
$[0,1)$: single-peaked, and the corner condition is the first-order condition
at $d_{lo}$. Part 2 is a Taylor expansion plus the implicit function theorem.

### Lemma 3.1 (which way the recommendation errs)

Hold the naive curve's value at the pivot $m$ fixed and vary its slope
$\hat b$. Then, at an interior optimum with $z = \hat a + \hat b \hat d$,

$$\mathrm{sign}\,\frac{\partial \hat d}{\partial \hat b}
 = \mathrm{sign}\big(1 - \hat b(\hat d - m)(z + r(z))\big).$$

- If the optimum is at or below the mean historical discount, a flatter curve
  (mild rescue) lowers the recommendation and a steeper one (whale) raises it.
- If the optimum is well above the mean, the directions reverse: mild rescue
  **over**-discounts and whale **under**-discounts. A steeper curve makes the
  model think the win is already secured just past the pivot.

*Sketch.* Differentiate the first-order condition
$(1-d)\hat b\, r(z) = 1$ in $\hat b$, using $r' = -r(z+r)$.

*Check.* With $d^*=0.311$: at $m=0.05$ the naive discounts are 0.336 (mild
rescue) and 0.287 (mild whale). At $m=0.38$ they are 0.269 and 0.336. The
switch happens near $m=0.20$, where the lemma's expression is about 1.

## One worked example

Parameters: $\alpha=-1,\ \theta=8,\ \beta=0.8,\ m=0.12,\ \sigma_d=0.05$,
discounts allowed from 0 to 40%. The causal optimum is a 31.1% discount. The
sign flips at $\rho=-0.50$. This is one parameterization, chosen for
illustration. It is not calibrated to any real book.

| $\rho$ | Naive slope / true slope | Recommended discount | Regret (% of optimal revenue) |
|---|---|---|---|
| +0.9 | 3.4 | 21.4% | 7.5% |
| +0.6 | 2.4 | 24.1% | 3.9% |
| +0.3 | 1.6 | 27.2% | 1.1% |
| 0 | 1.0 | 31.1% | 0 |
| -0.1 | 0.80 | 32.2% | 0.1% |
| -0.3 | 0.41 | 29.4% | 0.2% |
| -0.36 | 0.29 | 21.6% | 7.2% |
| -0.40 | 0.21 | 8.6% | 39.1% |
| -0.415 and below | 0.18 and below | 0% (floor) | 64.0% |

At $\rho=-0.3$ the model has the slope wrong by 59% and loses 0.2% of revenue.
A slightly stronger confounding, $\rho=-0.415$, loses 64%. The naive slope is
still positive there, so nothing in the fitted curve looks broken.

## What this means for the paper

- **C1 gets sharper.** The claim is no longer "the constraint fixes one
  direction". It is "in the linear-Gaussian model the constraint is
  decision-neutral: it repairs the explanation and leaves the recommendation
  and the regret unchanged". Whether that survives a saturating curve,
  covariates, finite samples and tree ensembles is an empirical question for
  the benchmark.
- **The design doc's direction claim was wrong** for mild confounding and is
  replaced by Lemma 3.1.
- **C2 becomes the cliff.** Mild confounding in either direction costs little,
  which agrees with Fernandez-Loria and Provost (2022). The loss is
  concentrated in a narrow band of rescue confounding where the recommendation
  collapses to the floor while the fitted curve still slopes the right way.
- **C3 has a clearer job.** The recommender does not need an accurate slope
  everywhere. It needs to tell whether the book is near the cliff, and abstain
  if it cannot. That is a detection problem, which is easier to do with few
  reps than precise estimation.
- **Asymmetry.** In the example, the worst rescue case costs 64% and the worst
  whale case 7.5%. That ordering depends on the floor and cap regrets, so it
  is a property of the example, not a theorem.

## What is not shown

- Covariates and heterogeneous effects. Decision-neutrality can fail when the
  constraint binds for some deals and not others inside one fitted model.
- A saturating true curve (the generator's tanh), where the naive curve can
  rise then fall and the constraint flattens only part of it.
- Finite samples and tree ensembles, where the constraint also regularizes.
- Non-Gaussian quality, logit links, and reps who discount on several signals.
- The product clips the discount sweep to the cohort's observed range, so its
  floor is the cohort's 5th percentile, not zero. That limits the cliff's
  depth in practice. It does not remove it.

## Product note (separate from the paper)

If Corollary 2.1 holds up on the synthetic book, the monotone constraint in
`pricing/model.py` is making the win curve look defensible without changing
what is recommended. That is worth a board ticket once the benchmark exists.
It is not a reason to change the model today.

---

# Propositions 4 and 5 (added 2026-11-11, after experiments 1 to 3)

These are results A3 and A6 of the v2 design. Checked numerically by
`research/jair-discount-causality/verify_propositions_2.py` (all assertions
pass). Proof sketches only; a human check is still required.

## Proposition 4 (a saturating response: the constraint lowers the recommendation)

Keep the setup above, but let the discount effect be any increasing concave
function $g$ in place of $\theta d$:
$Y = 1\{\alpha + g(d) + \beta q + \varepsilon > 0\}$. Let $\pi(d)$ be the
observational win curve on $[d_{lo}, d_{hi}]$, $\tilde\pi$ its monotone
(non-decreasing) fit, and $d_u$, $d_c$ the discounts that maximize
$(1-d)\pi(d)$ and $(1-d)\tilde\pi(d)$ (smallest maximizer if tied).

1. **The observational curve is single-peaked.**
   $\pi(d) = \Phi\big((\alpha + g(d) + \beta\rho(d-m)/\sigma_d)/\sqrt{1+\beta^2(1-\rho^2)}\big)$.
   Under whale confounding it is increasing. Under rescue confounding it rises
   while $g'(d) > \beta|\rho|/\sigma_d$ and falls afterwards: a hump whenever
   that threshold is crossed inside the range.
2. **The constrained fit follows the curve, then goes flat.** There is a point
   $t$, at or before the peak, with $\tilde\pi = \pi$ on $[d_{lo}, t]$ and
   $\tilde\pi$ constant on $(t, d_{hi}]$. If $t > d_{lo}$ the constant is
   $\pi(t)$. If the falling side is heavy enough, $t = d_{lo}$ and the whole
   fit is flat.
3. **The constraint never raises the recommendation:** $d_c \le d_u$, and
   $d_c \le t$. Under whale confounding $d_c = d_u$.
4. **It cannot reduce regret when the unconstrained model already
   under-discounts.** If $d_u \le d^*$ then
   regret$(d_c) \ge$ regret$(d_u)$, strictly when $d_c < d_u$.

*Sketch.* (1) $q \mid d$ is normal with mean linear in $d$ whatever $g$ is, so
the index is $g(d)$ plus a linear term with slope $\beta\rho/\sigma_d$;
concavity of $g$ makes its derivative cross zero at most once, from above.
(2) The monotone fit of a function that rises then falls pools the falling
side together with enough of the rising side to make the pooled average equal
the value of the curve at the pooling point (the pool-adjacent-violators
solution; Barlow et al. 1972, citation from memory, to confirm). (3) On the
flat part $(1-d)\tilde\pi(d)$ strictly falls, so $d_c \le t$. Left of $t$ the
two objectives are the same function. If $d_u \le t$ the two picks coincide;
if $d_u > t$ then $d_c \le t < d_u$. (4) True revenue is single-peaked
(Proposition 3), hence increasing below $d^*$.

*What is not claimed.* Part 4 needs $d_u \le d^*$. Lemma 3.1 shows mild rescue
confounding can push $d_u$ above $d^*$, and then a lower $d_c$ may help. Part 3
is specific to a single-peaked curve: with a dip between two high regions the
constrained pick can be higher (the script has a counterexample).

*Check.* 48 parameter settings; 27 produce a hump; in 22 the constrained pick
is strictly lower. With $\alpha=-0.5$, $\beta=0.55$, mean discount 12%:

| $\rho$ | Flat from | Unconstrained pick | Constrained pick | True best | Regret, unconstrained | Regret, constrained |
|---|---|---|---|---|---|---|
| -0.9 | 0% | 4.1% | 0% | 8.9% | 10.5% | 50.8% |
| -0.7 | 1.5% | 4.9% | 1.5% | 8.9% | 6.5% | 33.0% |
| -0.5 | 3.1% | 5.7% | 3.1% | 8.9% | 3.6% | 17.1% |
| -0.3 | 5.0% | 6.7% | 5.1% | 8.9% | 1.5% | 5.7% |
| -0.1 | 8.6% | 8.0% | 8.0% | 8.9% | 0.2% | 0.2% |
| +0.5 | never | 19.8% | 19.8% | 8.9% | 9.6% | 9.6% |

These are population values. They are larger than the tree-model gaps in
experiment 1 (6 to 11 points), as expected: a shallow tree ensemble
approximates both curves coarsely.

**Reading.** In every strict case the constrained model recommends the point
where its curve goes flat. The constraint turns "the data say discount stops
helping here" into a hard stop, and under rescue confounding the data say
that too early.

## Proposition 5 (leniency-aligned rep skill cannot be detected)

Let reps differ in leniency $b_r$ and in skill $s_r$:

$$d = f(x) + b_r + v, \qquad
Y = 1\{h(x) + g(d) + \delta s_r + \beta q + \varepsilon > 0\},$$

with $(v, q, \varepsilon)$ independent of the covariates and of the rep.
Exclusion holds when $\delta = 0$.

1. **Linear case.** If $s_r = \kappa b_r$, the data are generated identically,
   deal by deal, by a model with no rep skill:
   $$Y = 1\{\tilde h(x) + \tilde g(d) + \tilde u > 0\},\quad
   \tilde g(d) = g(d) + \delta\kappa d,\ \
   \tilde h(x) = h(x) - \delta\kappa f(x),\ \
   \tilde u = \beta q - \delta\kappa v + \varepsilon.$$
   Here $\tilde u$ is independent of the covariates and the rep, so this
   second model satisfies every assumption of the instrument. No test on
   (covariates, rep, discount, outcome) can distinguish the two.
2. **They disagree about the discount.** The causal effect of discount on the
   index is $g'(d)$ in the first model and $g'(d) + \delta\kappa$ in the
   second. A control function fitted to the data recovers the second.
3. **General case.** If skill is any function of leniency, $s_r = s(b_r)$,
   then because $b_r = d - f(x) - v$, the outcome is independent of the
   identity of the rep given $(x, d, v)$. Tests of whether reps differ beyond
   what discount explains have power equal to their size.
4. **What is detectable.** Write $s_r = \kappa b_r + e_r$ with $e_r$ unrelated
   to leniency. The $e_r$ part breaks the conditional independence in 3 and is
   visible as unexplained rep differences. The $\kappa b_r$ part is not.

*Sketch.* Substitute $b_r = d - f(x) - v$ into $\delta\kappa b_r$ and collect
terms. For 3, $b_r$ is a deterministic function of $(x, d, v)$, so conditioning
on them fixes the skill.

*Check.* 200,000 simulated deals, 12 reps, skill worth 0.3 logit per standard
deviation of leniency (lenient reps weaker): the two models produce the same
outcome for every deal. The true best discount is 8.8%. The no-skill model
that fits the same data says 3.9%, and acting on it loses 11.0%. Experiment 3
confirms the test side: the rep test flagged aligned skill no more often than
it flagged a valid instrument.

**One piece of leverage.** In that example the causal curve of the no-skill
model peaks at a 5.1% discount and then falls: it says larger discounts reduce
the chance of winning. An analyst who believes discounts never hurt can reject
it on that ground. This only works when lenient reps are weaker
($\delta\kappa < 0$) and the response saturates. When lenient reps are
stronger, the alternative curve is steeper and still monotone, and nothing
rules it out.

**Consequences.**
- Abstention cannot be triggered by a test for this failure. It needs outside
  information (an outcome discounts cannot affect, such as progression before
  a quote is issued) or a stated sensitivity range.
- A monotonicity belief about the causal curve, the same belief the product
  constraint encodes, is useful here as a falsification check on the
  corrected curve even though it is harmful as a constraint on the
  uncorrected one. That contrast may be the cleanest single message of the
  paper.

## What is still not shown (updated)

- Propositions 4 and 5 are population statements for one cohort. Covariates
  enter only through "conditional on x".
- Proposition 4 assumes normal quality and a linear first stage. The
  single-peaked shape may fail otherwise.
- The linear case of Proposition 5 needs an additive first stage. Clipping
  discounts at zero breaks it slightly.
- Nothing here addresses finite samples or few reps.
