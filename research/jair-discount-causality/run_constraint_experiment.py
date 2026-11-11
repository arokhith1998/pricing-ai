"""Does the monotone constraint change the recommendation or the regret on the
real generator and the product's win-model configuration?

For each confounding strength rho, train two LightGBM win models on the same
book with the product's exact parameters (pricing.model._PARAMS): one with the
+1 monotone constraint on discount_pct (the product), one without. Recommend a
discount for fresh deals from the same process by maximizing predicted
expected ACV, then score each recommendation against the TRUE causal curve.

Two sweep rules:
  full    0-40% grid for every deal (the setting of the propositions)
  cohort  grid clipped to the segment's 5th-95th observed percentile
          (range from pricing.model._cohort_grid, the product's guardrail,
          snapped to the 1-point lattice)

This does not call pricing.model.recommend_discount: it reproduces the argmax
only, without the method labels or the never-add-discount rule.

Run:  python research/jair-discount-causality/run_constraint_experiment.py
Writes results/constraint_experiment.csv next to this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

from pricing import model as pm  # noqa: E402
from confounded_book import make_book, true_revenue  # noqa: E402

FULL_GRID = np.round(np.arange(0.0, 0.4001, 0.01), 4)
RHOS = (-0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.9)
N_TEST = 2000


def fit(book: pd.DataFrame, constrained: bool) -> tuple[LGBMClassifier, list[str]]:
    X, y, cat, _ = pm.prepare(book)
    params = dict(pm._PARAMS)
    if constrained:  # exactly what pricing.model.train does
        params["monotone_constraints"] = [
            1 if c == "discount_pct" else 0 for c in X.columns]
        params["monotone_constraints_method"] = "advanced"
    clf = LGBMClassifier(**params)
    clf.fit(X, y, categorical_feature=cat)
    return clf, list(X.columns)


def predicted_curve(clf, features, X: pd.DataFrame, grid: np.ndarray) -> np.ndarray:
    g = len(grid)
    rep = X.loc[X.index.repeat(g)].reset_index(drop=True)
    rep["discount_pct"] = np.tile(grid, len(X))
    return clf.predict_proba(rep[features])[:, 1].reshape(len(X), g)


def evaluate(train: pd.DataFrame, test: pd.DataFrame, quality_effect: float) -> list[dict]:
    """Score both models under both sweep rules on the test deals."""
    Xte, _, _, _ = pm.prepare(pd.concat([train, test], ignore_index=True))
    Xte = Xte.iloc[len(train):]          # categories consistent with training
    models = {name: fit(train, name == "constrained")
              for name in ("constrained", "unconstrained")}
    curves = {name: predicted_curve(clf, feats, Xte, FULL_GRID)
              for name, (clf, feats) in models.items()}
    rev_true = true_revenue(test["base_logit"].to_numpy(), FULL_GRID, quality_effect)
    list_acv = test["list_acv"].to_numpy()
    seg = test["segment"].to_numpy()

    # Allowed grid points per deal under each rule.
    allowed = {"full": np.ones_like(rev_true, dtype=bool)}
    cohort = np.zeros_like(rev_true, dtype=bool)
    for s in np.unique(seg):
        g = pm._cohort_grid(train.loc[train["segment"] == s, "discount_pct"].to_numpy())
        # The product's grid starts at the cohort's 5th percentile, which is
        # not on the 1-point lattice; keep the lattice points inside its range.
        inside = (FULL_GRID >= g[0] - 1e-9) & (FULL_GRID <= g[-1] + 1e-9)
        if not inside.any():
            inside = np.isclose(FULL_GRID, FULL_GRID[np.abs(FULL_GRID - g[0]).argmin()])
        cohort[np.ix_(seg == s, inside)] = True
    allowed["cohort"] = cohort

    rows, picks = [], {}
    for rule, mask in allowed.items():
        best_true = np.where(mask, rev_true, -np.inf).max(axis=1)
        d_true = FULL_GRID[np.where(mask, rev_true, -np.inf).argmax(axis=1)]
        for name, p in curves.items():
            ev = np.where(mask, p * (1.0 - FULL_GRID[None, :]), -np.inf)
            j = ev.argmax(axis=1)
            got = rev_true[np.arange(len(test)), j]
            picks[(rule, name)] = FULL_GRID[j]
            # Share of deals whose predicted curve falls by more than a point
            # anywhere across the full grid (a visibly "discounts hurt" curve).
            falls = (np.maximum.accumulate(p, axis=1) - p).max(axis=1) > 0.01
            rows.append({
                "rule": rule, "model": name,
                "regret_pct": 100 * (list_acv * (best_true - got)).sum()
                / (list_acv * best_true).sum(),
                "mean_rec": picks[(rule, name)].mean(),
                "mean_true_opt": d_true.mean(),
                "curve_falls_share": falls.mean(),
            })
        same = np.abs(picks[(rule, "constrained")] - picks[(rule, "unconstrained")]) < 0.0101
        for r in rows[-2:]:
            r["same_rec_share"] = same.mean()
    return rows


def run(n_train: int, seeds: range, quality_effect: float) -> pd.DataFrame:
    out = []
    for rho in RHOS:
        for seed in seeds:
            train = make_book(n_train, seed, rho, quality_effect)
            test = make_book(N_TEST, 10_000 + seed, rho, quality_effect)
            for r in evaluate(train, test, quality_effect):
                out.append({"n_train": n_train, "quality_effect": quality_effect,
                            "rho": rho, "seed": seed, **r,
                            "mean_hist_disc": train["discount_pct"].mean()})
    return pd.DataFrame(out)


if __name__ == "__main__":
    frames = [
        run(2_000, range(10), 0.55),    # product-sized book, generator's truth
        run(20_000, range(5), 0.55),    # closer to the population result
        run(20_000, range(5), 1.5),     # stronger hidden quality
    ]
    res = pd.concat(frames, ignore_index=True)
    (HERE / "results").mkdir(exist_ok=True)
    res.to_csv(HERE / "results" / "constraint_experiment.csv", index=False)
    keys = ["n_train", "quality_effect", "rule", "rho", "model"]
    summary = (res.groupby(keys)[["regret_pct", "mean_rec", "mean_true_opt",
                                  "curve_falls_share", "same_rec_share"]]
               .mean().round(3))
    pd.set_option("display.width", 200, "display.max_rows", 500)
    print(summary.to_string())
