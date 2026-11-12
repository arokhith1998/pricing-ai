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
              skill_effect: float = 0.0,
              skill_corr: float = 1.0,
              n_reps: int = N_REPS,
              assign_segment: float = 0.0,
              assign_quality: float = 0.0) -> pd.DataFrame:
    """Draw `n` closed deals. Returns model features, the outcome, and the
    hidden columns (`quality`, `base_logit`) needed to compute the truth.

    `skill_effect` breaks the instrument on purpose: each rep gets a skill
    equal to minus their standardized discount bias (lenient reps are weaker
    sellers), and it enters the win logit with this weight. At 0 (default) a
    rep changes the discount and nothing else. It consumes no random draws,
    so books with skill_effect=0 are unchanged.
    `skill_corr` is how closely skill tracks leniency: at 1.0 (default)
    skill is exactly minus the standardized bias; below that, the rest is a
    rep-level component unrelated to leniency, drawn from a separate random
    stream so nothing else shifts.
    `n_reps` is the number of reps. At the default (12) the three named
    reps of the product generator keep their offsets. At any other count
    rep biases are drawn with the same overall spread (sd 0.045) and no
    named offsets.
    `assign_segment` (0 to 1) is the share of deals routed to a rep whose
    home segment matches the deal's segment (territories). Home segments
    are unrelated to leniency.
    `assign_quality` (-1 to 1) routes deals on the hidden quality: the
    correlation between a deal's quality and the leniency rank of the rep
    it goes to. Positive sends strong deals to lenient reps. Both default
    to 0 (random assignment) and use a separate random stream."""
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

    if n_reps == N_REPS:
        rep_bias = rng.normal(0.0, 0.035, size=N_REPS)
        rep_bias[1] += 0.06
        rep_bias[7] += 0.05
        rep_bias[4] -= 0.03
    else:
        rep_bias = rng.normal(0.0, 0.045, size=n_reps)
    rep = rng.integers(0, n_reps, size=n)

    quality = rng.standard_normal(n)
    if assign_segment or assign_quality:
        rep = _assign_reps(seed, seg, quality, rep_bias, rep, seg_names, w,
                           assign_segment, assign_quality)
    resid = RESID_SD * (rho * quality
                        + np.sqrt(1.0 - rho**2) * rng.standard_normal(n))
    disc = np.clip(base_disc + 0.06 * competitor + 0.10 * qe_pressure
                   + rep_bias[rep] + resid, 0.0, 0.45)

    base_logit = (-0.55 - 0.8 * competitor
                  + np.array([SEGMENT_WIN_EFFECT[s] for s in seg])
                  + np.array([REGION_WIN_EFFECT[r] for r in region])
                  + np.array([INDUSTRY_WIN_EFFECT[i] for i in industry])
                  - 0.12 * (np.log(list_acv) - 10.8))
    aligned = -(rep_bias - rep_bias.mean()) / rep_bias.std()
    rep_skill = aligned
    if skill_corr < 1.0:
        e = np.random.default_rng(seed + 5).standard_normal(n_reps)
        e = e - e.mean()
        e = e - (e @ aligned) / (aligned @ aligned) * aligned   # unrelated part
        e = e / e.std()
        rep_skill = skill_corr * aligned + np.sqrt(1.0 - skill_corr**2) * e
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


def _assign_reps(seed, seg, quality, rep_bias, rep, seg_names, weights,
                 assign_segment, assign_quality):
    """Non-random rep assignment (see make_book)."""
    if assign_segment and assign_quality:
        raise ValueError("set only one of assign_segment and assign_quality")
    arng = np.random.default_rng(seed + 9)
    n, n_reps = len(seg), len(rep_bias)
    if assign_quality:
        a = assign_quality
        u = a * quality + np.sqrt(1.0 - a**2) * arng.standard_normal(n)
        rank = np.argsort(np.argsort(u))
        return np.argsort(rep_bias)[(rank * n_reps) // n]
    counts = np.maximum(1, np.round(weights / weights.sum() * n_reps).astype(int))
    while counts.sum() > n_reps:
        counts[counts.argmax()] -= 1
    while counts.sum() < n_reps:
        counts[counts.argmax()] += 1
    home = np.repeat(np.arange(len(seg_names)), counts)[arng.permutation(n_reps)]
    out = rep.copy()
    routed = arng.random(n) < assign_segment
    for k, name in enumerate(seg_names):
        pick = routed & (seg == name)
        out[pick] = arng.choice(np.flatnonzero(home == k), size=int(pick.sum()))
    return out


def true_revenue_given_rep(test: pd.DataFrame, book: pd.DataFrame, grid: np.ndarray,
                           quality_effect: float = QUALITY_EFFECT) -> np.ndarray:
    """Expected booked ACV per dollar of list for each test deal, given
    its covariates AND its rep: hidden quality is averaged over the
    quality of the deals that rep actually receives. Equals true_revenue
    when reps are assigned at random."""
    probs = (np.arange(41) + 0.5) / 41
    out = np.zeros((len(test), len(grid)))
    base = test["base_logit"].to_numpy()
    for r in np.unique(test["rep_id"]):
        q = np.quantile(book.loc[book["rep_id"] == r, "quality"], probs)
        rows = np.flatnonzero(test["rep_id"].to_numpy() == r)
        idx = base[rows, None] + 1.3 * np.tanh(grid[None, :] / 0.05)
        z = idx[:, :, None] + quality_effect * q[None, None, :]
        out[rows] = (1.0 / (1.0 + np.exp(-z))).mean(axis=2) * (1.0 - grid[None, :])
    return out


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
