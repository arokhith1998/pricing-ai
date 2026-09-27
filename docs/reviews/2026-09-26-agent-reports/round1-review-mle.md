# MLE review: fix/agent-eval-findings vs origin/main (read-only)

## Verdict
Five of six findings closed with evidence; F3 half closed. The clip pins every Enterprise recommendation to the cohort floor, `leakage_vs_model` still sweeps 0 to 40%, and two new reachable failures (NaN cohort raises, sparse-book CRM guardrail recommends 0%) need fixing before merge.

## Closed-findings checklist (data/synthetic/deals.csv, this branch)
- F1 time split, forward-fold tuning: closed. `split=time`, AUC 0.614. My 5 expanding folds: current params AUC 0.638 (se 0.022), skill +0.053; old 250/15/50 AUC 0.605, skill -0.012.
- F2 skill gate: closed. Skill +0.037, bootstrap 95% CI +0.001 to +0.070. `test_gate_fails_for_a_constant_predictor` shows a constant scores exactly 0 and fails `> 0`.
- F2 per-band and per-segment calibration: recorded, not gated. Holdout under-predicts everywhere (40-60% band 0.52 vs 0.61 actual, SMB 0.61 vs 0.71, mean 0.593 vs 0.658); the page shows the warning verdict.
- F3 clip and guardrail: partial. Enterprise below cohort minimum: 41.5% before, 0% now. Under 50 deals returns `band_guardrail` (tested).
- F4 explanation of the recommended row: closed on router and page.
- F6 reproducibility: closed. Seed, params, features, data_hash stamped, n_jobs=1; two retrains give max |dp| = 0.0.

## New findings, ranked
1. major, `pricing/model.py:425-434`: the clip makes the optimum a boundary, not a model output. 342/342 Enterprise recommendations sit exactly at the grid's lower edge (14.01%, the p5). Win-prob gain across the grid is 0.000 for every deal, so EV is strictly decreasing and the argmax is always the floor, yet `/recommend` labels it `modeled_ev_curve` and claims mean uplift $11.5k on 94% of deals. Fix: when `best == 0` or total win-prob gain is under 0.01, set `method="support_floor"` (or use `_band_guardrail_recommendation`) and expose `at_grid_edge`.
2. major, `pricing/model.py:419-426`: NaN in `cohort_discounts` raises `ValueError` from `np.arange`. Reachable: one blank list price leaves `discount_pct` NaN (ingest keeps the row) and `api/routers/model.py:145` passes the raw column, so `/recommend` 500s for every deal in that segment; the NaN deal itself returns `current=nan`, uplift $5,167. Fix: drop non-finite values at entry; a `no_discount_on_record` method when `current` is NaN.
3. major, `pricing/crm.py:119-131`, `api/routers/crm.py:298`: the sufficiency gate never reaches the CRM guardrail. On a 40-deal book `reference_discount` returns `sufficient=False, threshold 0.0`; every segment inherits 0.0, `guidance_for_open_deal` recommends 0% with `price_to_retain` $50,000, and `/crm/exceptions` writes `guardrail_pct=0`. `analyze_records` accepts 30 deals, so this is a first pilot's book. `top_leak_deals` (`metrics.py:851`) and `hierarchy_slice_reference` (`metrics.py:582`) read the same unchecked 0.0. Fix: in `_reference_for_segment`, when the global ref is insufficient and the segment has none, return `reference=current`, basis "insufficient data"; add the check to both metrics callers.
4. major, `pricing/model.py:514-515`, `app/pages/2_Win_model_and_guidance.py:70-78`: `leakage_vs_model` still sweeps 0 to 40%. Enterprise justified discounts: 100% below p5, 32.8% below the lowest observed; headline $9.38M, still called "more dependable". The same deal reads "justified 7%" here and "recommend 14%" in the panel. Fix: per-row segment p5/p95 grid; drop the dependability sentence.
5. minor, `tests/test_model.py:76` vs `app/_app_lib.py:158`: 0.08 test tolerance, 0.05 page tolerance. One constant.
6. minor, `pricing/model.py:99-110`: tuning folds span the 25% the gated holdout scores. State it, or tune inside the first 75%.

## calibration_verdict brier_skill optionality
`app/_app_lib.py:161-163` defaults `brier_skill=None` so the four `tests/test_app_lib.py` calls pass, but the None path awards "dependable" on the bias check alone, which is F2 itself. Tighten: keyword-only and required; update the four tests (they pass `tol=` by keyword, nothing positional broke).

Primary risk: the cohort clip converts an extrapolated optimum into a fixed floor for the segment that matters most, still labeled a modeled optimum, beside a leakage figure that uses the unclipped grid.

Checks run: branch diff on the six named files plus metrics.py, crm.py, governance.py, copilot.py; two scratchpad probes in the repo venv. No repo file modified; suite not run.
