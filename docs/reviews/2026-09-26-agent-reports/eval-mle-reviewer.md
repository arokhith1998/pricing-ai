# ML surface review, Pricekeel (read-only)

Reviewed state: `main` @ a977dd0 (includes PK-15 / PR #68). The checked-out tree
`feat/agent-engineering-org` predates PK-15 and PK-1, so the working copy of
`pricing/model.py` has no monotone constraint and there is no `api/routers/`.
All line numbers below are `main`.

## 1. Verdict

The pipeline is disciplined where most early-stage pricing ML is sloppy:
`prepare` excludes the algebraic twins of the outcome, `X_all` gives scoring the
training category encoding, explanations are exact tree SHAP that reconcile with
the prediction, and PK-15's monotone constraint on `discount_pct` is the right
call for an endogenous lever, argued causally rather than by AUC. What is not
yet true is the part the product actually sells: the numbers. Evaluation is a
random stratified split on time-ordered deals, capacity was tuned against that
same split, and the only calibration check is a global mean. On a time split the
model ranks at AUC 0.564 and has a negative Brier skill of -0.075, meaning its
probabilities are worse than quoting the training win rate, and it is those
probabilities, not the ranking, that set every recommended discount and every
model-conditioned leakage dollar. Nothing here is fatal to the idea, and none of
it has touched a customer, but the guidance surface claims more precision than
the evidence supports.

## 2. Findings

**1. blocker, random split on time-ordered deals, and capacity tuned on it.**
`pricing/model.py:105` uses `train_test_split(..., stratify=y)`; deals carry
`close_date`. Measured in TEMP on `data/synthetic/deals.csv`, same params and
constraint: random holdout AUC 0.619, Brier skill +0.006; time holdout (latest
25% of closes) AUC 0.564, Brier skill -0.075. The `_PARAMS` comment at
`model.py:67-68` says the regularization was chosen because it "improves holdout
AUC", which is tuning against the test set. Fix: split on `close_date`, keep the
random path only as a logged fallback, tune capacity on expanding forward folds.
The in-flight branch `agent/ai-engineer/fix-time-split-silent-failures` already
does this and retunes to 50/7/150; land it.

**2. blocker, no calibration gate, and the one that exists cannot fail.**
`model.py:122-125` records `brier` and `mean_pred` only.
`tests/test_model.py:59-63` asserts `|mean_pred - base_rate| < 0.05` and
`brier < 0.26`; a constant base-rate predictor scores Brier 0.238 and passes
both. On the time holdout the real shape is flat: the predicted-0.30 band
actually wins 0.55 and the predicted-0.85 band actually wins 0.69; by segment,
Enterprise predicted 0.489 versus actual 0.556. `recommend_discount` takes the
argmax of p x list x (1-d), so a compressed probability curve moves the optimum
directly. Fix: record Brier skill against the base rate plus calibration by
probability band and by segment, and gate on skill > 0, not on raw Brier.
`app/_app_lib.py:161-177` should stop awarding "well calibrated, guidance below
dependable" on a mean-only test.

**3. major, recommendations extrapolate past the data, hardest where it matters
most.** `model.py:165` sweeps 0.00 to 0.40 for every deal regardless of support.
On the full book, 85% of Enterprise recommendations sit below the 5th percentile
of observed Enterprise discounts and 34% sit below the lowest Enterprise
discount ever recorded (8.1%). The monotone constraint guarantees the win curve
keeps rising as discount falls, so the EV optimum is pulled into exactly the
region with no data. A Head of Pricing gets told to quote 9% on an Enterprise
deal where nothing in the book closed under 8.1%. Fix: clip the grid per cohort
to roughly the 5th to 95th percentile of that segment's observed discounts, and
when the cohort is under about 50 deals return the band guardrail instead of a
curve optimum.

**4. major, the "why" panel explains a different number than the headline.**
`api/routers/model.py:135` calls `_explain_factors(tm, df, idx)`, which at line
72 runs `model.explain(tm, tm.X_all.loc[[idx]])`, that is SHAP at the deal's
current discount, while the headline is the recommended discount. Over a
200-deal sample the `discount_pct` contribution flips sign between current and
recommended for 36% of deals and the top-ranked factor changes for 14%. The
panel can read "Discount 40%, pushed win chance up" beside "recommend 11%".
Fix: compute the explanation on the recommended row, or show both, labeled.

**5. major, every number the demo shows is in-sample.** `engine()` trains on the
whole book, and `/recommend`, `/model`, `leakage_vs_model` (`model.py:239-256`)
and `governance.exception_verdict` all score rows that were in training.
In-sample AUC on that book is 0.87 against a 0.619 random holdout and a 0.564
time holdout, and `/recommend` ships `confidence.auc` from the holdout next to
an in-sample probability. `app/pages/2_Win_model_and_guidance.py:52-60` then
says those wins "needed about X% discount to win" and calls the figure "more
dependable than the single companywide number". Fix: score demo deals from a
model that did not train on them, and drop the dependability comparison until a
forward fold supports it.

**6. minor, the recorded PK-15 AUC cost is inside split noise, and runs are not
reproducible.** The docstring at `model.py:24-27`, and the test comments in
`tests/test_model.py`, pin "0.640 unconstrained to 0.619 constrained" as the
price of the constraint. Random-split AUC across 20 seeds ranges 0.551 to 0.670
(sd 0.026), so that 0.021 gap is under one standard deviation of split choice;
on a time split the two are 0.564 and 0.561, indistinguishable. Separately,
`n_jobs=-1` at `model.py:70` is nondeterministic and `metrics` records no seed,
params, feature list, or data hash. Fix: state the cost as a fold-averaged delta
with a standard error, and stamp `metrics` with seed, params, features, and the
input hash. Good news for PK-15: the constraint costs much less than advertised.

## 3. Three genuinely good things

1. PK-15 is the right fix for the right reason. Constraining an endogenous lever
   on causal grounds, paying AUC for it knowingly, and testing the booster's own
   params rather than the call site
   (`test_booster_carries_discount_pct_monotone_constraint`) is better judgment
   than most teams show here.
2. Leakage-feature discipline is real and tested.
   `tests/test_model.py::test_no_leakage_features` asserts the forbidden set
   directly, `cycle_days` is excluded on purpose, and
   `test_explanations_reconcile_with_prediction` proves the explanation is the
   model, not a story about it.
3. The evidence architecture around a recommendation: `comparable_deals`
   returning wins and losses, `band_context` showing the empirical cohort curve,
   the `modeled_ev_curve` method label that separates this from the
   correlational Salesforce band path, and copilot's `_RECOVERABLE_CAVEAT`.
   That is what survives a pricing committee.

## 4. The one thing to fix next week

Land the time split and forward-fold retune sitting on
`agent/ai-engineer/fix-time-split-silent-failures`, and add a Brier-skill gate
plus per-band and per-segment calibration to `metrics`. That single change turns
the headline from a number that flatters itself into one you can show a design
partner, and it is a prerequisite for trusting finding 3's fix, since a
recalibrated model moves the EV optimum anyway.

Primary risk: the recommended discount is the argmax of a probability curve that
is miscalibrated, in-sample, and extrapolated past its support, so the one
number a Head of Pricing acts on is the least validated thing in the system.

Checks run: read `pricing/model.py` (branch and main), `generate.py`,
`copilot.py`, `diagnostic.py`, `metrics.py`, `governance.py`,
`api/routers/model.py`, `app/pages/2_Win_model_and_guidance.py`,
`app/_app_lib.py`, `tests/test_model.py`; diffed branch, main, and the in-flight
worktree; ran two probe scripts in TEMP against the repo venv measuring random
versus time-split AUC and Brier skill, calibration by band and by segment,
20-seed split variance, recommendation support per segment, in-sample AUC, and
SHAP agreement between the current and recommended discount. No repo file,
index, or board state was modified, and the test suite was not run.
