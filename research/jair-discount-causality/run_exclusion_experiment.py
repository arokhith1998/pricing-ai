"""Experiment 3: can the rep-leniency method tell when it should not be
trusted, and does a sensitivity range protect the recommendation?

Scenarios (rep skill enters the win model; see confounded_book.make_book):
  valid      skill 0                 the instrument is valid
  aligned    skill 0.3, corr 1.0     skill is exactly minus leniency
  partial    skill 0.4, corr 0.7     about 0.28 aligned, 0.29 unaligned
  unaligned  skill 0.3, corr 0.0     skill unrelated to leniency

Rules compared (spline control function throughout):
  cf           assumes no direct effect of leniency (experiment 2b)
  robust_fixed minimax regret over direct effects in [-0.3, +0.3]
  robust_cal   minimax regret over [-tau, +tau], tau from the rep test
  *_abstain    the same, but a deal whose best discount moves more than
               5 points across the range falls back to its segment's median
               historical discount
  uncorrected  spline model with no control function

Train and test deals come from ONE book so they share the same reps.

Run:  python research/jair-discount-causality/run_exclusion_experiment.py
Writes results/exclusion_experiment.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import leniency_cf as lc  # noqa: E402
from confounded_book import make_book, true_revenue  # noqa: E402
from exclusion import SensitivityCF, robust_choice  # noqa: E402
from run_spline_experiment import SplineWinModel  # noqa: E402

GRID = np.round(np.arange(0.0, 0.4001, 0.01), 4)
N_TEST = 1000
FIXED_RANGE = 0.3
ABSTAIN_WIDTH = 0.05
SCENARIOS = {"valid": (0.0, 1.0), "aligned": (0.3, 1.0),
             "partial": (0.4, 0.7), "unaligned": (0.3, 0.0)}


def one_run(n_train: int, seed: int, rho: float, scenario: str) -> list[dict]:
    skill, corr = SCENARIOS[scenario]
    book = make_book(n_train + N_TEST, seed, rho, skill_effect=skill, skill_corr=corr)
    train = book.iloc[:n_train].reset_index(drop=True)
    test = book.iloc[n_train:].reset_index(drop=True)
    fs = lc.first_stage(train)
    m = SensitivityCF(train, fs)
    het = m.rep_heterogeneity()

    rev = true_revenue(test["base_logit"].to_numpy(), GRID)
    w = test["list_acv"].to_numpy()
    mask = np.ones_like(rev, dtype=bool)
    best = rev.max(axis=1)
    rows_idx = np.arange(len(test))
    med = train.groupby("segment")["discount_pct"].median()
    fallback = np.abs(GRID[None, :] - test["segment"].map(med).to_numpy()[:, None]).argmin(axis=1)

    def regret(j, keep=None):
        keep = np.ones(len(test), bool) if keep is None else keep
        if not keep.any():
            return np.nan
        got = rev[rows_idx, j]
        return 100 * (w * (best - got))[keep].sum() / (w * best)[keep].sum()

    out = {}
    out["uncorrected"] = (SplineWinModel(train).curve(test, GRID)
                          * (1 - GRID)[None, :]).argmax(axis=1), None
    out["cf"] = (m.curve(test, GRID, 0.0) * (1 - GRID)[None, :]).argmax(axis=1), None
    for name, half in (("robust_fixed", FIXED_RANGE), ("robust_cal", het.tau)):
        deltas = np.linspace(-half, half, 7) if half > 0 else np.array([0.0])
        curves = np.stack([m.curve(test, GRID, float(d)) for d in deltas])
        j, width = robust_choice(curves, GRID, mask)
        out[name] = j, width

    base = {"n_train": n_train, "seed": seed, "rho": rho, "scenario": scenario,
            "tau": het.tau, "rep_test_p": het.p_value, "pi": fs.pi}
    rows = []
    for name, (j, width) in out.items():
        rows.append({**base, "rule": name, "regret_pct": regret(j),
                     "mean_rec": GRID[j].mean(), "coverage": 1.0,
                     "regret_covered": regret(j)})
        if width is not None:
            keep = width <= ABSTAIN_WIDTH + 1e-9
            jj = np.where(keep, j, fallback)
            rows.append({**base, "rule": name + "_abstain", "regret_pct": regret(jj),
                         "mean_rec": GRID[jj].mean(), "coverage": keep.mean(),
                         "regret_covered": regret(j, keep)})
    rows.append({**base, "rule": "segment_median", "regret_pct": regret(fallback),
                 "mean_rec": GRID[fallback].mean(), "coverage": 1.0,
                 "regret_covered": regret(fallback)})
    return rows


if __name__ == "__main__":
    rows = []
    for n_train, seeds in ((20_000, range(5)), (2_000, range(10))):
        for scenario in SCENARIOS:
            for rho in (-0.6, 0.0, 0.6):
                for seed in seeds:
                    rows += one_run(n_train, seed, rho, scenario)
    res = pd.DataFrame(rows)
    (HERE / "results").mkdir(exist_ok=True)
    res.to_csv(HERE / "results" / "exclusion_experiment.csv", index=False)
    pd.set_option("display.width", 250, "display.max_rows", 500)
    keys = ["n_train", "scenario", "rho"]
    print(res.pivot_table(index=keys, columns="rule", values="regret_pct").round(2).to_string())
    print(res.pivot_table(index=keys, columns="rule", values="coverage").round(2)
          [["robust_fixed_abstain", "robust_cal_abstain"]].to_string())
    one = res[res.rule == "cf"]
    print(one.groupby(keys).agg(tau=("tau", "mean"),
                                flagged=("rep_test_p", lambda p: (p < 0.05).mean())).round(3).to_string())
