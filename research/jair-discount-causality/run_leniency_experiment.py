"""Experiment 2: does a rep-leniency control function fix the recommendation,
and does its diagnostic detect which way reps' private information runs?

Models compared on the same books (all LightGBM with pricing.model._PARAMS):
  product        monotone-constrained, no correction (what ships today)
  cf             control function, monotone-constrained
  cf_free        control function, no monotone constraint
  oracle         sees the hidden deal quality (not available in practice);
                 shows how much regret is estimation error, not confounding

Scored as in experiment 1: regret against the true causal curve on fresh
deals, under the full 0-40% sweep and the product's cohort-clipped sweep.

Run:  python research/jair-discount-causality/run_leniency_experiment.py
Writes results/leniency_experiment.csv and results/leniency_diagnostic.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

from pricing import model as pm  # noqa: E402
import leniency_cf as lc  # noqa: E402
from confounded_book import make_book, true_revenue  # noqa: E402

GRID = np.round(np.arange(0.0, 0.4001, 0.01), 4)
RHOS = (-0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.9)
N_TEST = 1000


def sweep_masks(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, np.ndarray]:
    seg = test["segment"].to_numpy()
    cohort = np.zeros((len(test), len(GRID)), dtype=bool)
    for s in np.unique(seg):
        g = pm._cohort_grid(train.loc[train["segment"] == s, "discount_pct"].to_numpy())
        inside = (GRID >= g[0] - 1e-9) & (GRID <= g[-1] + 1e-9)
        if not inside.any():
            inside = np.isclose(GRID, GRID[np.abs(GRID - g[0]).argmin()])
        cohort[np.ix_(seg == s, inside)] = True
    return {"full": np.ones_like(cohort), "cohort": cohort}


def one_run(n_train: int, seed: int, rho: float, quality_effect: float,
            skill_effect: float) -> tuple[list[dict], dict]:
    train = make_book(n_train, seed, rho, quality_effect, skill_effect)
    test = make_book(N_TEST, 10_000 + seed, rho, quality_effect, skill_effect)
    both, _, _, _ = pm.prepare(pd.concat([train, test], ignore_index=True))
    Xte = both.iloc[len(train):].copy()   # categories consistent with training

    fs = lc.first_stage(train)
    diag = lc.diagnostic(train, fs)
    curves = {}
    clf, f = lc.fit_win_model(train)
    curves["product"] = lc.curve(clf, f, Xte, GRID)
    for name, constrained in (("cf", True), ("cf_free", False)):
        clf, f = lc.fit_win_model(train, {lc.CF: fs.resid}, constrained)
        curves[name] = lc.curve(clf, f, Xte, GRID, lc.CF, lc.spread(fs.resid))
    q = train["quality"].to_numpy()
    clf, f = lc.fit_win_model(train, {"quality": q})
    curves["oracle"] = lc.curve(clf, f, Xte, GRID, "quality", lc.spread(q))

    # Truth for each test deal. Rep skill (if any) is part of base_logit, so
    # the truth is the curve for the rep who actually holds the deal.
    rev = true_revenue(test["base_logit"].to_numpy(), GRID, quality_effect)
    w = test["list_acv"].to_numpy()
    rows = []
    for rule, mask in sweep_masks(train, test).items():
        best = np.where(mask, rev, -np.inf).max(axis=1)
        d_true = GRID[np.where(mask, rev, -np.inf).argmax(axis=1)]
        for name, p in curves.items():
            j = np.where(mask, p * (1 - GRID[None, :]), -np.inf).argmax(axis=1)
            got = rev[np.arange(len(test)), j]
            rows.append({"rule": rule, "model": name,
                         "regret_pct": 100 * (w * (best - got)).sum() / (w * best).sum(),
                         "mean_rec": GRID[j].mean(), "mean_true_opt": d_true.mean()})
    meta = {"pi": fs.pi, "partial_f": fs.partial_f, "diag_coef": diag.coef_per_sd,
            "diag_z": diag.z, "verdict": diag.verdict}
    return rows, meta


def run(n_train: int, seeds: range, quality_effect: float = 0.55,
        skill_effect: float = 0.0, rhos=RHOS):
    res, diags = [], []
    for rho in rhos:
        for seed in seeds:
            key = {"n_train": n_train, "quality_effect": quality_effect,
                   "skill_effect": skill_effect, "rho": rho, "seed": seed}
            rows, meta = one_run(n_train, seed, rho, quality_effect, skill_effect)
            res += [{**key, **r} for r in rows]
            diags.append({**key, **meta})
    return pd.DataFrame(res), pd.DataFrame(diags)


if __name__ == "__main__":
    parts = [
        run(2_000, range(10)),                       # product-sized book
        run(20_000, range(5)),                       # larger book
        run(20_000, range(5), skill_effect=0.3,      # instrument broken on purpose
            rhos=(-0.6, 0.0, 0.6)),
    ]
    res = pd.concat([p[0] for p in parts], ignore_index=True)
    diag = pd.concat([p[1] for p in parts], ignore_index=True)
    (HERE / "results").mkdir(exist_ok=True)
    res.to_csv(HERE / "results" / "leniency_experiment.csv", index=False)
    diag.to_csv(HERE / "results" / "leniency_diagnostic.csv", index=False)
    pd.set_option("display.width", 220, "display.max_rows", 500)
    keys = ["n_train", "skill_effect", "rule", "rho"]
    print(res.pivot_table(index=keys, columns="model", values="regret_pct").round(2).to_string())
    print(diag.groupby(["n_train", "skill_effect", "rho"]).agg(
        pi=("pi", "mean"), F=("partial_f", "mean"), coef=("diag_coef", "mean"),
        z=("diag_z", "mean"),
        rescue=("verdict", lambda s: (s == "rescue").mean()),
        whale=("verdict", lambda s: (s == "whale").mean())).round(2).to_string())
