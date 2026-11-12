"""Research copy of the synthetic deal generator with a confounding dial.

Same segment, region, industry, competitor, quarter-end and rep structure and
the same win model as pricing/generate.py (constants are imported from it),
with one change: the rep's discount can depend on the latent deal quality the
win model also depends on.

    discount = base + 0.06*competitor + 0.10*quarter_end + rep_bias
               + rho * RESID_SD * quality + sqrt(1 - rho^2) * RESID_SD * noise

rho is the correlation between latent quality and the part of the discount
that covariates and rep identity do not explain. rho < 0 is "rescue" (deeper
discounts on weak deals), rho > 0 is "whale", rho = 0 is the product
generator's behaviour. The residual spread stays at RESID_SD for every rho, so
only the reason for discounting changes, not how much discounts vary.

Because the win model is known, the causal win curve P(win | do(discount), x)
and each deal's true revenue-maximizing discount are computed exactly (up to
quadrature), which is what lets regret be measured.

pricing/generate.py is not modified: the pinned dataset and model tests depend
on its RNG stream. Synthetic only. No customer data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pricing.generate import (
    INDUSTRIES, INDUSTRY_WIN_EFFECT, REGIONS, REGION_WIN_EFFECT, SEGMENTS,
    SEGMENT_WIN_EFFECT, TIERS, VALUE_METRICS, VALUE_METRIC_WEIGHTS,
)

RESID_SD = 0.035          # generator's residual discount noise
QUALITY_EFFECT = 0.55     # generator's logit weight on latent quality
N_REPS = 12

_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(40)
_GH_W = _GH_W / _GH_W.sum()


def make_book(n: int, seed: int, rho: float,
              quality_effect: float = QUALITY_EFFECT,
              skill_effect: float = 0.0) -> pd.DataFrame:
    """Draw `n` closed deals. Returns model features, the outcome, and the
    hidden columns (`quality`, `base_logit`) needed to compute the truth.

    `skill_effect` breaks the instrument on purpose: each rep gets a skill
    equal to minus their standardized discount bias (lenient reps are weaker
    sellers), and it enters the win logit with this weight. At 0 (default) a
    rep changes the discount and nothing else. It consumes no random draws,
    so books with skill_effect=0 are unchanged."""
    if not -1.0 < rho < 1.0:
        raise ValueError("rho must be strictly between -1 and 1")
    rng = np.random.default_rng(seed)
    seg_names = list(SEGMENTS)
    w = np.array([SEGMENTS[s]["weight"] for s in seg_names])
    seg = rng.choice(seg_names, size=n, p=w / w.sum())
    log_mean = np.array([SEGMENTS[s]["log_mean"] for s in seg])
    log_sd = np.array([SEGMENTS[s]["log_sd"] for s in seg])
    base_disc = np.array([SEGMENTS[s]["base_disc"] for s in seg])
    list_acv = np.clip(rng.lognormal(log_mean, log_sd), 3000, 1_200_000)

    competitor = rng.random(n) < 0.42
    # Days to quarter end uniform over a ~91-day quarter; pressure ramps over
    # the last 21 days, as in generate._quarter_end_pressure.
    days_to_qe = rng.integers(0, 91, size=n)
    qe_pressure = np.clip(1.0 - days_to_qe / 21.0, 0.0, None)
    region = rng.choice(REGIONS, size=n, p=[0.55, 0.30, 0.15])
    industry = rng.choice(INDUSTRIES, size=n)

    rep_bias = rng.normal(0.0, 0.035, size=N_REPS)
    rep_bias[1] += 0.06
    rep_bias[7] += 0.05
    rep_bias[4] -= 0.03
    rep = rng.integers(0, N_REPS, size=n)

    quality = rng.standard_normal(n)
    resid = RESID_SD * (rho * quality
                        + np.sqrt(1.0 - rho**2) * rng.standard_normal(n))
    disc = np.clip(base_disc + 0.06 * competitor + 0.10 * qe_pressure
                   + rep_bias[rep] + resid, 0.0, 0.45)

    base_logit = (-0.55 - 0.8 * competitor
                  + np.array([SEGMENT_WIN_EFFECT[s] for s in seg])
                  + np.array([REGION_WIN_EFFECT[r] for r in region])
                  + np.array([INDUSTRY_WIN_EFFECT[i] for i in industry])
                  - 0.12 * (np.log(list_acv) - 10.8))
    rep_skill = -(rep_bias - rep_bias.mean()) / rep_bias.std()
    base_logit = base_logit + skill_effect * rep_skill[rep]
    logit = base_logit + 1.3 * np.tanh(disc / 0.05) + quality_effect * quality
    won = rng.random(n) < 1.0 / (1.0 + np.exp(-logit))

    vm = rng.choice(VALUE_METRICS, size=n, p=VALUE_METRIC_WEIGHTS)
    return pd.DataFrame({
        "segment": seg, "region": region, "industry": industry,
        "product_tier": rng.choice(TIERS, size=n, p=[0.30, 0.34, 0.24, 0.12]),
        "value_metric": vm,
        "list_acv": list_acv,
        "discount_pct": disc,
        "term_months": rng.choice([12, 12, 12, 24, 36], size=n),
        "quantity": np.round(list_acv / rng.uniform(0.5, 25, size=n), 0),
        "is_quarter_end": days_to_qe <= 21,
        "competitor_present": competitor,
        "is_won": won,
        "rep_id": rep,
        # hidden from the model; used only to compute the truth
        "quality": quality,
        "base_logit": base_logit,
    })


def true_win_prob(base_logit: np.ndarray, grid: np.ndarray,
                  quality_effect: float = QUALITY_EFFECT) -> np.ndarray:
    """Causal P(win | do(discount=g), x) for every deal and grid point:
    latent quality integrated out over N(0,1). Shape (n_deals, n_grid)."""
    idx = base_logit[:, None] + 1.3 * np.tanh(grid[None, :] / 0.05)
    z = idx[:, :, None] + quality_effect * _GH_X[None, None, :]
    return (1.0 / (1.0 + np.exp(-z)) * _GH_W[None, None, :]).sum(axis=2)


def true_revenue(base_logit: np.ndarray, grid: np.ndarray,
                 quality_effect: float = QUALITY_EFFECT) -> np.ndarray:
    """Expected booked ACV per dollar of list, shape (n_deals, n_grid)."""
    return true_win_prob(base_logit, grid, quality_effect) * (1.0 - grid[None, :])
