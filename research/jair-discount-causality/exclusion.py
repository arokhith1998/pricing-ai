"""Guarding the rep-leniency method against a broken exclusion restriction.

The instrument assumes a rep's leniency changes the outcome only through the
discount. If lenient reps are also weaker (or stronger) sellers, that fails.

What can and cannot be checked from a deal book alone:

  * A skill difference that lines up exactly with leniency is NOT detectable.
    "Lenient reps win less because they are weaker" and "discounts work less
    well than we think" predict the same data. No test on (discount, outcome,
    rep) can separate them.
  * Skill differences that do NOT line up with leniency ARE visible: reps
    differ in win rate by more than discount, covariates and chance explain.

So this module does two things:

  1. `rep_heterogeneity`: tests whether reps differ in win rate beyond what
     the model explains, and estimates the size of that spread (tau, in logit
     units). It is a warning light, not proof either way.
  2. `SensitivityCF`: refits the control function assuming leniency has a
     direct effect `delta` on the win logit, for a range of deltas, and
     recommends the discount with the smallest worst-case regret across the
     range (Conley, Hansen and Rossi 2012 in spirit; minimax regret after
     Manski). A deal whose best discount moves a lot across the range is one
     the method should abstain on.

The range can be fixed by the analyst, or calibrated to tau: "leniency-aligned
skill is assumed no larger than the unaligned skill we can see".

Synthetic only. No customer data.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.preprocessing import SplineTransformer

import leniency_cf as lc


def _fit_logit(A: np.ndarray, y: np.ndarray, offset: np.ndarray,
               ridge: float = 1e-4, iters: int = 30) -> np.ndarray:
    """Newton logistic regression with a fixed offset. A includes a constant
    in column 0, which is not penalized."""
    b = np.zeros(A.shape[1])
    pen = np.full(A.shape[1], ridge)
    pen[0] = 0.0
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-(A @ b + offset)))
        w = p * (1.0 - p)
        step = np.linalg.solve((A * w[:, None]).T @ A + np.diag(pen),
                               A.T @ (y - p) - pen * b)
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


@dataclass
class RepHeterogeneity:
    chi2: float
    df: int
    p_value: float
    tau: float      # sd of unexplained rep effects, logit units, noise-corrected


class SensitivityCF:
    """Spline control-function win model with an assumed direct effect of rep
    leniency: logit = covariates + spline(discount) + c*v + delta*leniency_sd."""

    def __init__(self, train: pd.DataFrame, fs: lc.FirstStage):
        X = lc.design(train)
        self.cols = list(X.columns)
        self.sp = SplineTransformer(n_knots=6, degree=3, include_bias=False,
                                    extrapolation="constant")
        S = self.sp.fit_transform(train[["discount_pct"]].to_numpy())
        M = np.column_stack([X.to_numpy()[:, 1:], S, fs.resid])
        self.mu = M.mean(axis=0)
        self.sd = np.where(M.std(axis=0) > 0, M.std(axis=0), 1.0)
        self.A = np.column_stack([np.ones(len(M)), (M - self.mu) / self.sd])
        self.y = train["is_won"].to_numpy().astype(float)
        self.rep = train["rep_id"].to_numpy()
        self.z = (fs.leniency - fs.leniency.mean()) / fs.leniency.std()
        self.rep_z = pd.Series(self.z).groupby(self.rep).mean()
        self.v_values = lc.spread(fs.resid, 41)
        self.nx, self.k = X.shape[1] - 1, S.shape[1]
        self._fits: dict[float, np.ndarray] = {}

    def coef(self, delta: float) -> np.ndarray:
        if delta not in self._fits:
            self._fits[delta] = _fit_logit(self.A, self.y, delta * self.z)
        return self._fits[delta]

    def rep_heterogeneity(self) -> RepHeterogeneity:
        """Score test for rep effects in the delta=0 model. Approximate: it
        ignores the estimation of the other coefficients and of v."""
        p = 1.0 / (1.0 + np.exp(-(self.A @ self.coef(0.0))))
        g = pd.DataFrame({"r": self.y - p, "i": p * (1 - p)}).groupby(self.rep).sum()
        stat = float((g["r"] ** 2 / g["i"]).sum())
        df = len(g) - 2       # the constant and the leniency direction are absorbed
        eff = g["r"] / g["i"]
        tau2 = float(eff.var(ddof=1) - (1.0 / g["i"]).mean())
        return RepHeterogeneity(stat, df, float(chi2.sf(stat, df)),
                                float(np.sqrt(max(tau2, 0.0))))

    def curve(self, test: pd.DataFrame, grid: np.ndarray, delta: float) -> np.ndarray:
        """P(win) for each test deal at each grid discount, averaged over v,
        including the assumed direct effect for the deal's own rep."""
        b = self.coef(delta)
        beta = b[1:] / self.sd
        b0 = b[0] - (self.mu * beta).sum()
        X = lc.design(test, self.cols).to_numpy()[:, 1:]
        S = self.sp.transform(grid[:, None])
        z = test["rep_id"].map(self.rep_z).fillna(0.0).to_numpy()
        idx = (b0 + X @ beta[:self.nx] + delta * z)[:, None] \
            + (S @ beta[self.nx:self.nx + self.k])[None, :]
        zz = idx[:, :, None] + beta[-1] * self.v_values[None, None, :]
        return (1.0 / (1.0 + np.exp(-zz))).mean(axis=2)


def robust_choice(curves: np.ndarray, grid: np.ndarray,
                  mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Minimax-regret discount per deal.

    curves: (n_delta, n_deals, n_grid) win probabilities, one slice per assumed
    direct effect. mask: (n_deals, n_grid) allowed discounts.
    Returns (index of the chosen grid point, width): width is the spread, in
    discount points, of the best discount across the assumed effects.
    """
    ev = np.where(mask[None], curves * (1.0 - grid)[None, None, :], -np.inf)
    best = ev.max(axis=2, keepdims=True)
    regret = np.where(mask[None], (best - ev) / best, np.inf)
    choice = regret.max(axis=0).argmin(axis=1)
    opt = grid[ev.argmax(axis=2)]                 # (n_delta, n_deals)
    return choice, opt.max(axis=0) - opt.min(axis=0)
