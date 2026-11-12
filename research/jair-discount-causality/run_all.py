"""Run every experiment at paper scale, in parallel.

  constraint  experiment 1 (tree model, with and without the constraint)   30 seeds
  spline      experiment 2b (spline model, with and without the correction) 30 seeds
  reps        the same correction with 6, 12, 25 and 50 reps                30 seeds
  exclusion   experiment 3 (broken instrument, robust rules)                30 seeds
  capacity    tree model at five capacities, with and without constraint   10 seeds

Run:  python research/jair-discount-causality/run_all.py [kind ...]
Writes results/<kind>_full.csv. One process per CPU; every run is seeded, so
results do not depend on the order in which workers finish.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")

RHOS = (-0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.9)
GRID = np.round(np.arange(0.0, 0.4001, 0.01), 4)
CAPACITIES = {
    "product_50x7": {},
    "200x7": dict(n_estimators=200),
    "500x7_child50": dict(n_estimators=500, min_child_samples=50),
    "500x15_child50": dict(n_estimators=500, num_leaves=15, min_child_samples=50),
    "500x15_lr10_child20": dict(n_estimators=500, num_leaves=15, learning_rate=0.1,
                                min_child_samples=20, colsample_bytree=1.0),
}


def specs(kind: str) -> list[tuple]:
    if kind == "constraint":
        return [(kind, n, s, r, 0.55) for n in (2_000, 20_000) for r in RHOS for s in range(30)]
    if kind == "spline":
        return [(kind, n, s, r) for n in (2_000, 20_000) for r in RHOS for s in range(30)]
    if kind == "reps":
        return [(kind, n, s, r, k) for n in (2_000, 20_000) for k in (6, 12, 25, 50)
                for r in (-0.6, 0.0, 0.6) for s in range(30)]
    if kind == "exclusion":
        return [(kind, n, s, r, sc) for n in (2_000, 20_000)
                for sc in ("valid", "aligned", "partial", "unaligned")
                for r in (-0.6, 0.0, 0.6) for s in range(30)]
    if kind == "capacity":
        return [(kind, n, s, r) for n in (2_000, 20_000)
                for r in (-0.6, 0.0, 0.6) for s in range(10)]
    raise ValueError(kind)


def _regret(rev, w, j):
    best = rev.max(axis=1)
    return 100 * (w * (best - rev[np.arange(len(j)), j])).sum() / (w * best).sum()


def work(spec: tuple) -> list[dict]:
    warnings.filterwarnings("ignore")
    from confounded_book import make_book, true_revenue
    kind = spec[0]

    if kind == "constraint":
        import run_constraint_experiment as rce
        _, n, seed, rho, qe = spec
        train, test = make_book(n, seed, rho, qe), make_book(2000, 10_000 + seed, rho, qe)
        return [{"n_train": n, "seed": seed, "rho": rho, **r}
                for r in rce.evaluate(train, test, qe)]

    if kind == "spline":
        import run_spline_experiment as rse
        _, n, seed, rho = spec
        return [{"n_train": n, "seed": seed, "rho": rho, **r}
                for r in rse.one_run(n, seed, rho, 0.55, 0.0)]

    if kind == "exclusion":
        import run_exclusion_experiment as ree
        _, n, seed, rho, scenario = spec
        return ree.one_run(n, seed, rho, scenario)

    if kind == "reps":
        import leniency_cf as lc
        from run_spline_experiment import SplineWinModel
        _, n, seed, rho, k = spec
        book = make_book(n + 1000, seed, rho, n_reps=k)
        train = book.iloc[:n].reset_index(drop=True)
        test = book.iloc[n:].reset_index(drop=True)
        fs = lc.first_stage(train)
        diag = lc.diagnostic(train, fs)
        rev = true_revenue(test["base_logit"].to_numpy(), GRID)
        w = test["list_acv"].to_numpy()
        base = {"n_train": n, "seed": seed, "rho": rho, "n_reps": k,
                "diag_z": diag.z, "verdict": diag.verdict, "partial_f": fs.partial_f}
        out = []
        for name, p in (("spline", SplineWinModel(train).curve(test, GRID)),
                        ("spline_cf", SplineWinModel(train, fs.resid).curve(
                            test, GRID, lc.spread(fs.resid, 41)))):
            j = (p * (1 - GRID)[None, :]).argmax(axis=1)
            out.append({**base, "model": name, "regret_pct": _regret(rev, w, j),
                        "mean_rec": GRID[j].mean()})
        return out

    if kind == "capacity":
        from lightgbm import LGBMClassifier
        from pricing import model as pm
        import leniency_cf as lc
        _, n, seed, rho = spec
        train, test = make_book(n, seed, rho), make_book(1000, 10_000 + seed, rho)
        both, _, cat, _ = pm.prepare(pd.concat([train, test], ignore_index=True))
        Xtr, Xte = both.iloc[:n], both.iloc[n:].copy()
        y = train["is_won"].astype(int)
        rev = true_revenue(test["base_logit"].to_numpy(), GRID)
        w = test["list_acv"].to_numpy()
        out = []
        for cap, override in CAPACITIES.items():
            for constrained in (True, False):
                params = dict(pm._PARAMS, **override)
                if constrained:
                    params["monotone_constraints"] = [
                        1 if c == "discount_pct" else 0 for c in Xtr.columns]
                    params["monotone_constraints_method"] = "advanced"
                clf = LGBMClassifier(**params).fit(Xtr, y, categorical_feature=cat)
                p = lc.curve(clf, list(Xtr.columns), Xte, GRID)
                j = (p * (1 - GRID)[None, :]).argmax(axis=1)
                out.append({"n_train": n, "seed": seed, "rho": rho, "capacity": cap,
                            "constrained": constrained,
                            "regret_pct": _regret(rev, w, j), "mean_rec": GRID[j].mean()})
        return out

    raise ValueError(kind)


if __name__ == "__main__":
    kinds = sys.argv[1:] or ["constraint", "spline", "reps", "exclusion", "capacity"]
    (HERE / "results").mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1)) as pool:
        for kind in kinds:
            t0 = time.time()
            todo = specs(kind)
            rows = [r for chunk in pool.map(work, todo, chunksize=4) for r in chunk]
            pd.DataFrame(rows).to_csv(HERE / "results" / f"{kind}_full.csv", index=False)
            print(f"{kind}: {len(todo)} runs, {len(rows)} rows, "
                  f"{(time.time() - t0) / 60:.1f} min", flush=True)
