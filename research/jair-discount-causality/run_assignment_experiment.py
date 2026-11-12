"""Experiment 5: reps who are not assigned to deals at random.

Mechanisms
  random        any rep gets any deal
  territory     80% or 100% of deals go to a rep whose home segment matches
                (assignment on something the book records)
  sorting       deals are routed on hidden quality: strong deals to lenient
                reps (+) or weak deals to lenient reps (-), at correlation
                0.3 or 0.6 (assignment on something the book does not record)

Rules (spline model): uncorrected, the leniency control function, and the
robust rule over a fixed (0.3) or calibrated sensitivity range.

Checks recorded per book: the balance test (do covariates predict the rep's
leniency?), the rep heterogeneity test, and the direction diagnostic.

Regret is measured against the best discount given the deal's covariates and
its rep, because under sorting the rep is informative about the deal.

Run:  python research/jair-discount-causality/run_assignment_experiment.py
Writes results/assignment_full.csv. 30 seeds, one process per CPU.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")

GRID = np.round(np.arange(0.0, 0.4001, 0.01), 4)
N_TEST = 1000
MECHANISMS = {
    "random": {},
    "territory_0.8": {"assign_segment": 0.8},
    "territory_1.0": {"assign_segment": 1.0},
    "sorting_+0.3": {"assign_quality": 0.3},
    "sorting_-0.3": {"assign_quality": -0.3},
    "sorting_+0.6": {"assign_quality": 0.6},
    "sorting_-0.6": {"assign_quality": -0.6},
}


def one_run(spec: tuple) -> list[dict]:
    warnings.filterwarnings("ignore")
    import leniency_cf as lc
    from confounded_book import make_book, true_revenue_given_rep
    from exclusion import SensitivityCF, robust_choice
    from run_spline_experiment import SplineWinModel

    n_train, seed, rho, mech = spec
    book = make_book(n_train + N_TEST, seed, rho, **MECHANISMS[mech])
    train = book.iloc[:n_train].reset_index(drop=True)
    test = book.iloc[n_train:].reset_index(drop=True)
    fs = lc.first_stage(train)
    m = SensitivityCF(train, fs)
    het = m.rep_heterogeneity()
    diag = lc.diagnostic(train, fs)

    rev = true_revenue_given_rep(test, book, GRID)
    w = test["list_acv"].to_numpy()
    best = rev.max(axis=1)
    mask = np.ones_like(rev, dtype=bool)

    def regret(j):
        return 100 * (w * (best - rev[np.arange(len(test)), j])).sum() / (w * best).sum()

    picks = {
        "uncorrected": (SplineWinModel(train).curve(test, GRID) * (1 - GRID)[None, :]).argmax(axis=1),
        "cf": (m.curve(test, GRID, 0.0) * (1 - GRID)[None, :]).argmax(axis=1),
    }
    for name, half in (("robust_fixed", 0.3), ("robust_cal", het.tau)):
        deltas = np.linspace(-half, half, 7) if half > 0 else np.array([0.0])
        curves = np.stack([m.curve(test, GRID, float(d)) for d in deltas])
        picks[name] = robust_choice(curves, GRID, mask)[0]

    base = {"n_train": n_train, "seed": seed, "rho": rho, "mechanism": mech,
            "balance_p": lc.balance_p(train, fs), "rep_test_p": het.p_value,
            "tau": het.tau, "verdict": diag.verdict, "partial_f": fs.partial_f,
            "leniency_quality_corr": float(np.corrcoef(fs.leniency, train["quality"])[0, 1])}
    return [{**base, "rule": name, "regret_pct": regret(j), "mean_rec": GRID[j].mean(),
             "mean_best": GRID[rev.argmax(axis=1)].mean()} for name, j in picks.items()]


if __name__ == "__main__":
    todo = [(n, s, r, mech) for n in (2_000, 20_000) for mech in MECHANISMS
            for r in (-0.6, 0.0, 0.6) for s in range(30)]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1)) as pool:
        rows = [r for chunk in pool.map(one_run, todo, chunksize=4) for r in chunk]
    res = pd.DataFrame(rows)
    (HERE / "results").mkdir(exist_ok=True)
    res.to_csv(HERE / "results" / "assignment_full.csv", index=False)

    pd.set_option("display.width", 250, "display.max_rows", 500)
    keys = ["n_train", "mechanism", "rho"]
    g = res.groupby(keys + ["rule"]).regret_pct.agg(["mean", "sem"])
    print(g.apply(lambda r: f"{r['mean']:.1f} ({r['sem']:.1f})", axis=1).unstack("rule").to_string())
    one = res[res.rule == "cf"]
    print(one.groupby(["n_train", "mechanism"]).agg(
        balance_flag=("balance_p", lambda p: (p < 0.05).mean()),
        rep_test_flag=("rep_test_p", lambda p: (p < 0.05).mean()),
        tau=("tau", "mean"), len_q_corr=("leniency_quality_corr", "mean"),
        first_stage_f=("partial_f", "mean")).round(3).to_string())
    print(pd.crosstab([one.n_train, one.mechanism, one.rho], one.verdict).to_string())
