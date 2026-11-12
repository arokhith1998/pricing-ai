"""Experiment 2b: the same control function with a second stage that can
represent a smooth discount curve.

Experiment 2 found that the control function did not improve the product's
tree model, and that even a tree model shown the hidden deal quality did
badly. That points at the win model's capacity, not at the instrument. This
script swaps the second stage for a logistic regression with a cubic spline in
discount:

  spline         covariates + spline(discount)                 (no correction)
  spline_cf      covariates + spline(discount) + v, averaged over v
  spline_oracle  covariates + spline(discount) + hidden quality, averaged

Same books, test deals, sweeps and regret definition as experiment 2.

Run:  python research/jair-discount-causality/run_spline_experiment.py
Writes results/spline_experiment.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import SplineTransformer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import leniency_cf as lc  # noqa: E402
from confounded_book import make_book, true_revenue  # noqa: E402
from run_leniency_experiment import GRID, N_TEST, RHOS, sweep_masks  # noqa: E402


class SplineWinModel:
    """Logistic win model, additive in covariates, a cubic spline in discount,
    and (optionally) one extra numeric term."""

    def __init__(self, train: pd.DataFrame, extra: np.ndarray | None = None):
        X = lc.design(train)
        self.cols = list(X.columns)
        self.sp = SplineTransformer(n_knots=6, degree=3, include_bias=False,
                                    extrapolation="constant")
        S = self.sp.fit_transform(train[["discount_pct"]].to_numpy())
        parts = [X.to_numpy()[:, 1:], S]
        if extra is not None:
            parts.append(extra[:, None])
        M = np.column_stack(parts)
        self.mu, self.sd = M.mean(axis=0), np.where(M.std(axis=0) > 0, M.std(axis=0), 1.0)
        self.lr = LogisticRegression(C=1e4, max_iter=3000).fit(
            (M - self.mu) / self.sd, train["is_won"].to_numpy().astype(int))
        self.has_extra = extra is not None

    def curve(self, test: pd.DataFrame, grid: np.ndarray,
              extra_values: np.ndarray | None = None) -> np.ndarray:
        b = self.lr.coef_[0] / self.sd
        b0 = float(self.lr.intercept_[0] - (self.mu * b).sum())
        nx = len(self.cols) - 1
        X = lc.design(test, self.cols).to_numpy()[:, 1:]
        S = self.sp.transform(grid[:, None])
        k = S.shape[1]
        idx = b0 + (X @ b[:nx])[:, None] + (S @ b[nx:nx + k])[None, :]
        if not self.has_extra:
            return 1 / (1 + np.exp(-idx))
        z = idx[:, :, None] + b[-1] * extra_values[None, None, :]
        return (1 / (1 + np.exp(-z))).mean(axis=2)


def one_run(n_train, seed, rho, quality_effect, skill_effect):
    train = make_book(n_train, seed, rho, quality_effect, skill_effect)
    test = make_book(N_TEST, 10_000 + seed, rho, quality_effect, skill_effect)
    fs = lc.first_stage(train)
    q = train["quality"].to_numpy()
    curves = {
        "spline": SplineWinModel(train).curve(test, GRID),
        "spline_cf": SplineWinModel(train, fs.resid).curve(
            test, GRID, lc.spread(fs.resid, 41)),
        "spline_oracle": SplineWinModel(train, q).curve(test, GRID, lc.spread(q, 41)),
    }
    rev = true_revenue(test["base_logit"].to_numpy(), GRID, quality_effect)
    w = test["list_acv"].to_numpy()
    rows = []
    for rule, mask in sweep_masks(train, test).items():
        best = np.where(mask, rev, -np.inf).max(axis=1)
        for name, p in curves.items():
            j = np.where(mask, p * (1 - GRID[None, :]), -np.inf).argmax(axis=1)
            got = rev[np.arange(len(test)), j]
            rows.append({"rule": rule, "model": name,
                         "regret_pct": 100 * (w * (best - got)).sum() / (w * best).sum(),
                         "mean_rec": GRID[j].mean()})
    return rows


def run(n_train, seeds, quality_effect=0.55, skill_effect=0.0, rhos=RHOS):
    out = []
    for rho in rhos:
        for seed in seeds:
            for r in one_run(n_train, seed, rho, quality_effect, skill_effect):
                out.append({"n_train": n_train, "quality_effect": quality_effect,
                            "skill_effect": skill_effect, "rho": rho, "seed": seed, **r})
    return pd.DataFrame(out)


if __name__ == "__main__":
    res = pd.concat([
        run(2_000, range(10)),
        run(20_000, range(5)),
        run(20_000, range(5), quality_effect=1.5),
        run(20_000, range(5), skill_effect=0.3, rhos=(-0.6, 0.0, 0.6)),
    ], ignore_index=True)
    (HERE / "results").mkdir(exist_ok=True)
    res.to_csv(HERE / "results" / "spline_experiment.csv", index=False)
    pd.set_option("display.width", 220, "display.max_rows", 500)
    keys = ["n_train", "quality_effect", "skill_effect", "rule", "rho"]
    print(res.pivot_table(index=keys, columns="model",
                          values=["regret_pct", "mean_rec"]).round(3).to_string())
    g = res.pivot_table(index=keys + ["seed"], columns="model", values="regret_pct")
    d = (g["spline_cf"] - g["spline"]).groupby(level=keys).agg(["mean", "sem"]).round(2)
    print("\nspline_cf minus spline (regret points):\n", d.to_string())
