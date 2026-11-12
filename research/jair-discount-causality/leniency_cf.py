"""Rep-leniency control function for discount guidance.

Idea: reps differ in how much they discount for reasons unrelated to any one
deal. If a rep's habit changes the discount and nothing else about the deal
(the exclusion restriction), comparing outcomes across lenient and strict reps
isolates what the discount itself does.

Steps
  1. Residualize discount on the quote-time covariates.
  2. Leniency z_i = mean of that residual over the SAME rep's OTHER deals
     (leave-one-out, so a deal never instruments itself).
  3. First stage: discount ~ covariates + z. The residual v is the part of the
     discount explained by neither covariates nor the rep's habit. That is
     where deal-specific private information lives.
  4. Second stage: the product's win model with v added as a feature. Holding
     v fixed, the remaining variation in discount comes from the rep's habit.
  5. Causal curve for a deal: predict at each candidate discount for a spread
     of v values and average (the average structural function).

Diagnostic: a logistic regression of the outcome on covariates, a spline in
discount, and v. The sign of v's coefficient says which way reps' private
information runs (negative: deeper discounts on weaker deals).

Assumptions this does NOT test: reps are assigned to deals as good as randomly
given covariates, and a rep's habit affects the outcome only through the
discount. Synthetic only. No customer data.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import SplineTransformer

from pricing import model as pm

CF = "cf_resid"
_CAT = ["segment", "region", "industry", "product_tier", "value_metric"]


def design(book: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Linear design of quote-time covariates (no discount, no outcome)."""
    X = pd.get_dummies(book[_CAT], drop_first=True, dtype=float)
    X["log_list"] = np.log(book["list_acv"].to_numpy())
    X["term_months"] = book["term_months"].to_numpy(dtype=float)
    X["is_quarter_end"] = book["is_quarter_end"].to_numpy(dtype=float)
    X["competitor_present"] = book["competitor_present"].to_numpy(dtype=float)
    X.insert(0, "const", 1.0)
    return X if columns is None else X.reindex(columns=columns, fill_value=0.0)


def _ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def loo_leniency(resid: np.ndarray, rep: np.ndarray) -> np.ndarray:
    """Mean residual discount over the same rep's other deals."""
    s = pd.Series(resid).groupby(rep).transform("sum").to_numpy()
    n = pd.Series(resid).groupby(rep).transform("count").to_numpy()
    if (n < 2).any():
        raise ValueError("every rep needs at least two deals for leave-one-out")
    return (s - resid) / (n - 1)


@dataclass
class FirstStage:
    leniency: np.ndarray      # z, per training deal
    resid: np.ndarray         # v, per training deal
    pi: float                 # coefficient of z
    partial_f: float          # plain (not cluster-robust) F for z
    n_reps: int


def first_stage(book: pd.DataFrame) -> FirstStage:
    X = design(book).to_numpy()
    d = book["discount_pct"].to_numpy()
    rep = book["rep_id"].to_numpy()
    r0 = d - X @ _ols(X, d)
    z = loo_leniency(r0, rep)
    Xz = np.column_stack([X, z])
    beta = _ols(Xz, d)
    v = d - Xz @ beta
    rss1, rss0 = float(v @ v), float(r0 @ r0)
    f = (rss0 - rss1) / (rss1 / (len(d) - Xz.shape[1]))
    return FirstStage(z, v, float(beta[-1]), float(f), int(len(np.unique(rep))))


def balance_p(book: pd.DataFrame, fs: FirstStage | None = None) -> float:
    """The standard examiner-design check: do reps receive different kinds of
    deals, as far as the book records? One-way ANOVA of each quote-time
    covariate across reps, Bonferroni-corrected; returns the adjusted smallest
    p-value. Small means assignment is not random with respect to recorded
    covariates. It says nothing about what the book does not record.

    (Regressing leniency on covariates would not work here: leniency is built
    from discounts already residualized on those covariates.)"""
    from scipy.stats import f_oneway
    X = design(book).iloc[:, 1:]
    rep = book["rep_id"].to_numpy()
    groups = [np.flatnonzero(rep == r) for r in np.unique(rep)]
    ps = []
    for col in X.columns:
        x = X[col].to_numpy()
        if x.std() == 0:
            continue
        ps.append(f_oneway(*[x[g] for g in groups]).pvalue)
    return float(min(1.0, len(ps) * np.nanmin(ps)))


def fit_win_model(book: pd.DataFrame, extra: dict[str, np.ndarray] | None = None,
                  constrained: bool = True):
    """The product's win model (pricing.model._PARAMS), optionally with extra
    numeric features appended. Returns (classifier, feature list)."""
    X, y, cat, _ = pm.prepare(book)
    for name, col in (extra or {}).items():
        X[name] = col
    params = dict(pm._PARAMS)
    if constrained:
        params["monotone_constraints"] = [
            1 if c == "discount_pct" else 0 for c in X.columns]
        params["monotone_constraints_method"] = "advanced"
    clf = LGBMClassifier(**params)
    clf.fit(X, y, categorical_feature=cat)
    return clf, list(X.columns)


def curve(clf, features: list[str], X: pd.DataFrame, grid: np.ndarray,
          extra_name: str | None = None,
          extra_values: np.ndarray | None = None) -> np.ndarray:
    """Predicted P(win) for each row of X at each grid discount. If an extra
    feature is named, average over `extra_values` (the structural average)."""
    g = len(grid)
    rep = X.loc[X.index.repeat(g)].reset_index(drop=True)
    rep["discount_pct"] = np.tile(grid, len(X))
    if extra_name is None:
        return clf.predict_proba(rep[features])[:, 1].reshape(len(X), g)
    out = np.zeros((len(X), g))
    for val in extra_values:
        rep[extra_name] = val
        out += clf.predict_proba(rep[features])[:, 1].reshape(len(X), g)
    return out / len(extra_values)


def spread(values: np.ndarray, k: int = 15) -> np.ndarray:
    """k evenly spaced quantiles, used to average a feature out."""
    return np.quantile(values, (np.arange(k) + 0.5) / k)


@dataclass
class Diagnostic:
    coef_per_sd: float   # logit change per one sd of v
    z: float             # plain Wald z (ignores first-stage noise and clustering)

    @property
    def verdict(self) -> str:
        if self.z <= -1.96:
            return "rescue"
        if self.z >= 1.96:
            return "whale"
        return "none detected"


def diagnostic(book: pd.DataFrame, fs: FirstStage) -> Diagnostic:
    """Sign test for private information in the discount (Rivers-Vuong style)."""
    X = design(book)
    sp = SplineTransformer(n_knots=6, degree=3, include_bias=False)
    S = sp.fit_transform(book[["discount_pct"]].to_numpy())
    v = fs.resid / fs.resid.std()
    M = np.column_stack([X.to_numpy()[:, 1:], S, v])
    M = (M - M.mean(axis=0)) / np.where(M.std(axis=0) > 0, M.std(axis=0), 1.0)
    y = book["is_won"].to_numpy().astype(int)
    lr = LogisticRegression(C=1e4, max_iter=2000).fit(M, y)
    p = lr.predict_proba(M)[:, 1]
    A = np.column_stack([np.ones(len(M)), M])
    cov = np.linalg.pinv((A * (p * (1 - p))[:, None]).T @ A)
    coef = float(lr.coef_[0][-1])
    return Diagnostic(coef, coef / float(np.sqrt(cov[-1, -1])))
