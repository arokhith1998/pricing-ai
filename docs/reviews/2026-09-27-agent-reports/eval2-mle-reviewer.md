# MLE re-review, day after PR #69 (working tree 00bd935, read-only)

## Re-measured, data/synthetic/deals.csv

- Time split (closes from 2025-04-03, 500 held out): AUC 0.614, CI 0.560 to 0.665. Brier skill +0.037, CI +0.001 to +0.070, P(skill <= 0) = 2.1%. Five forward folds: AUC 0.638, skill +0.051. In-sample AUC 0.713 (was 0.87).
- Calibration: under-predicts everywhere. 40-60% band 0.520 vs 0.606 actual; SMB 0.611 vs 0.706; mean 0.593 vs 0.658, past CALIBRATION_TOLERANCE, so the page warns on the demo book. Recalibration slope 0.954, intercept +0.31: a level shift from quarterly win rates of 0.602, 0.620, 0.553, 0.654. An intercept fitted on the last 300 training closes drops skill to +0.001. Base-rate drift, not a model defect.
- support_floor share: Enterprise 342 of 342; MidMarket 26%; SMB 10%. Enterprise win_prob_gain across its 14-32% grid is 0.000 on every deal.
- modeled_ev_curve at a grid edge: 0 of 1,365.
- OPP-00007 (Enterprise, list $264,729, discount 11.16%, below the 14.01% floor): recommend 11.16%, uplift $0, support_floor. Correct.
- /exceptions vs /recommend: 0 of 300 disagree at the deal's own discount.
- Two retrains: max |dp| = 0.0, identical metrics and 100 of 100 recommendations.

## Findings

1. major, `pricing/model.py:633-648`, `web/src/components/GuidanceClient.tsx:379-383`, `app/pages/2_Win_model_and_guidance.py:127`. A support floor still ships a dollar headline. 617 of 635 support_floor recommendations cut discount, mean 11.6 points, and "Expected value gain" sums to $4.81M across them, where the model measured zero discount effect. The caveat says so; the stat does not. Fix: for support_floor return `price_retained`, not `uplift`, and label it that way.

2. major, `pricing/model.py:726-804`. The $6.18M model-conditioned leakage (9.2% of booked) is 61% Enterprise ($3.78M), where every justified discount is the p5 floor, not a model output, and the page calls it "judged deal by deal". Fix: split `leakage_vs_model` into modeled and floor-based components; headline only the modeled $2.4M.

3. minor, `pricing/model.py:170-178, 616-637`. OPP-00007 sits below the grid yet returns `at_grid_edge=True` and a caveat calling the recommendation "the floor of that range". Add a below-support branch.

4. minor, `api/shared.py:26-32`. The demo still scores rows it trained on (22 of the top-40 /deals). Mitigated by capacity, not design.

5. nit, `web/src/lib/api.ts:344-347`: comment calls support_floor "live CRM guidance with no curve"; it is the model path's edge case.

## Design-partner answer

Yes, with the warning banner up and on the partner's own book. The reporting is honest now: time split, a skill gate that can fail, calibration by band and segment recorded, method labels and caveats everywhere, endpoints that agree, bit-exact retrains. The model is weak (skill barely clears zero) but no longer overstates itself. Findings 1 and 2 are the exceptions: neither number is a model output, and both read as one.

## Next model improvement

Not calibration and not capacity: LGBM at min_child 50 or 20, or 100 trees, leaves the Enterprise discount effect at 0.001 to 0.009. A partially pooled logistic (pooled discount slope plus shrunken segment deviations) matches LightGBM on the same folds (AUC 0.635, skill +0.057 vs 0.638, +0.051; gated holdout 0.618, +0.039 vs 0.614, +0.037) and gives every segment a slope with a standard error. Unshrunk per-segment slopes flip sign between C=1 and C=0.1 on 342 Enterprise deals, so shrinkage is required. Gate the uplift claim on that slope clearing zero: "cut to 14%, keep $7.6k" becomes "no measurable discount response in Enterprise on this book".

Primary risk: a labeled floor carrying an unlabeled dollar figure, on the segment with the largest deals and zero measured discount effect.

Checks run: read model.py, governance.py, both routers, api/shared.py, the Streamlit page, GuidanceClient.tsx, api.ts, test gates; two scratchpad probes in the venv. Nothing in the repo modified; suite not run.
