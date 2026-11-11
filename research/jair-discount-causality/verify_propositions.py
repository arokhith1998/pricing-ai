"""Numerical checks for the propositions in
docs/design/2026-11-11-jair-paper-propositions.md.

Stylized model (covariates suppressed):
    q ~ N(0,1)                      latent deal quality, unobserved
    d = m + gamma*q + eta           discount; eta ~ N(0, sigma^2)
    Y = 1{alpha + theta*d + beta*q + eps > 0},  eps ~ N(0,1)

rho = corr(d, q). rho < 0 is "rescue" (deeper discounts on weak deals),
rho > 0 is "whale" (deeper discounts on strong deals). sd(d) is held fixed
while rho varies, so only the reason for discounting changes.

Run:  python research/jair-discount-causality/verify_propositions.py
Every check is an assertion; the script exits non-zero if one fails.
Synthetic only. No customer data.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from sklearn.isotonic import IsotonicRegression

ALPHA, THETA, BETA = -1.0, 8.0, 0.8
M, SD_D = 0.12, 0.05
D_LO, D_HI = 0.0, 0.40
GRID = np.linspace(D_LO, D_HI, 4001)


# --- closed forms -----------------------------------------------------------
def structural(alpha=ALPHA, theta=THETA, beta=BETA):
    """(a*, b*): P(Y=1 | do(d)) = Phi(a* + b* d)."""
    s = np.sqrt(1 + beta**2)
    return alpha / s, theta / s


def observational(rho, alpha=ALPHA, theta=THETA, beta=BETA, m=M, sd_d=SD_D):
    """(a_obs, b_obs): P(Y=1 | d) = Phi(a_obs + b_obs d)."""
    lam = rho / sd_d
    s = np.sqrt(1 + beta**2 * (1 - rho**2))
    return (alpha - beta * lam * m) / s, (theta + beta * lam) / s


def revenue(d, a, b):
    """Expected booked ACV per dollar of list at discount d."""
    return (1 - d) * norm.cdf(a + b * d)


def best_discount(a, b):
    return GRID[np.argmax(revenue(GRID, a, b))]


# --- simulation -------------------------------------------------------------
def simulate(rho, n, rng):
    q = rng.standard_normal(n)
    gamma = rho * SD_D
    sigma = SD_D * np.sqrt(1 - rho**2)
    d = M + gamma * q + sigma * rng.standard_normal(n)
    y = (ALPHA + THETA * d + BETA * q + rng.standard_normal(n) > 0).astype(float)
    return d, y


def fit_probit(d, y):
    def nll(p):
        z = p[0] + p[1] * d
        return -(y * norm.logcdf(z) + (1 - y) * norm.logcdf(-z)).sum()
    return minimize(nll, x0=np.zeros(2), method="BFGS").x


def check_prop1(rng):
    """Naive probit slope matches the closed form; sign and direction."""
    a_s, b_s = structural()
    flip = -THETA * SD_D / BETA
    print(f"structural slope b* = {b_s:.3f}; sign flips below rho = {flip:.2f}")
    print(" rho   b_obs(formula)  b_obs(fitted)  b_obs/b*")
    for rho in (-0.8, -0.6, -0.3, -0.1, 0.0, 0.1, 0.3, 0.6):
        d, y = simulate(rho, 400_000, rng)
        _, b_fit = fit_probit(d, y)
        _, b_obs = observational(rho)
        print(f"{rho:5.1f}  {b_obs:13.3f}  {b_fit:13.3f}  {b_obs / b_s:8.2f}")
        assert abs(b_fit - b_obs) < 0.15, (rho, b_fit, b_obs)
        if rho > 0:
            assert b_obs > b_s            # whale: always steeper
        assert (b_obs < 0) == (rho < flip)  # sign-flip threshold
    # Rescue need not attenuate when the true effect dominates (scale term).
    _, b_s2 = structural(theta=600.0, beta=3.0)
    _, b_o2 = observational(-0.5, theta=600.0, beta=3.0)
    assert b_o2 > b_s2
    print(f"counterexample (theta=600, beta=3, rho=-0.5): b_obs/b* = {b_o2 / b_s2:.3f} > 1")


def check_prop2(rng):
    """Monotone fit: equals the naive curve when it rises, flat when it falls."""
    for rho in (-0.8, -0.3, 0.5):
        d, y = simulate(rho, 400_000, rng)
        iso = IsotonicRegression(increasing=True, out_of_bounds="clip").fit(d, y)
        lo, hi = np.quantile(d, [0.05, 0.95])
        xs = np.linspace(lo, hi, 50)
        fit = iso.predict(xs)
        a_o, b_o = observational(rho)
        gap = np.abs(fit - norm.cdf(a_o + b_o * xs)).max()
        spread = fit.max() - fit.min()
        print(f"rho={rho:5.1f}  b_obs={b_o:6.2f}  monotone fit spread={spread:.3f}  "
              f"max gap to naive curve={gap:.3f}  mean(y)={y.mean():.3f}")
        if b_o < 0:
            assert spread < 0.02 and abs(fit.mean() - y.mean()) < 0.02
        else:
            assert gap < 0.03


def check_prop3():
    """Regret: quadratic near zero confounding, flat once the floor binds."""
    a_s, b_s = structural()
    d_star = best_discount(a_s, b_s)
    r_star = revenue(d_star, a_s, b_s)
    assert D_LO < d_star < D_HI
    floor_regret = r_star - revenue(D_LO, a_s, b_s)
    cap_regret = r_star - revenue(D_HI, a_s, b_s)
    h = 1e-3
    curv = (revenue(d_star + h, a_s, b_s) - 2 * r_star
            + revenue(d_star - h, a_s, b_s)) / h**2
    print(f"d* = {d_star:.3f}; regret at floor = {floor_regret / r_star:.1%} of optimum, "
          f"at cap = {cap_regret / r_star:.1%}")
    print("  rho   d_naive  d_monotone  regret(% of optimum)")
    rows = []
    for rho in np.round(np.arange(-0.9, 0.91, 0.1), 1):
        a_o, b_o = observational(rho)
        d_naive = best_discount(a_o, b_o)
        # Monotone-constrained population fit: the naive curve if it rises,
        # a constant if it falls (Proposition 2).
        d_mono = d_naive if b_o >= 0 else best_discount(0.0, 0.0)
        reg = r_star - revenue(d_naive, a_s, b_s)
        rows.append((rho, b_o, d_naive, reg))
        print(f"{rho:5.1f}  {d_naive:7.3f}  {d_mono:10.3f}  {reg / r_star:8.2%}")
        assert d_mono == d_naive          # decision equivalence
        assert reg <= max(floor_regret, cap_regret) + 1e-12
        if b_o <= 0:
            assert d_naive == D_LO and abs(reg - floor_regret) < 1e-12
    # Quadratic regime: regret ~ 0.5*|R''|*(d_hat - d*)^2 for small errors.
    for rho, _, d_naive, reg in rows:
        if 0 < abs(rho) <= 0.1:
            approx = 0.5 * abs(curv) * (d_naive - d_star) ** 2
            assert abs(reg - approx) <= 0.25 * approx + 1e-9, (rho, reg, approx)
    # The floor binds before the slope reaches zero (fine grid near the flip).
    early = [rho for rho in np.arange(-0.499, -0.40, 0.001)
             if observational(rho)[1] > 0 and best_discount(*observational(rho)) == D_LO]
    assert early, "expected the floor to bind while the naive slope is still positive"
    print(f"floor binds for rho <= {max(early):.3f}, where the naive slope is still "
          f"{observational(max(early))[1]:.2f} > 0 (sign flips at -0.500)")


def check_direction():
    """Which way the naive discount errs depends on where the optimum sits
    relative to the mean historical discount m (the pivot of the naive curve)."""
    a_s, b_s = structural()
    d_star = best_discount(a_s, b_s)
    print(f"d* = {d_star:.3f} (does not depend on m)")
    print("    m   d_naive(rho=-0.1)  d_naive(rho=+0.1)")
    out = {}
    for m in (0.05, 0.12, 0.20, 0.30, 0.38):
        lo = best_discount(*observational(-0.1, m=m))
        hi = best_discount(*observational(+0.1, m=m))
        out[m] = (lo, hi)
        print(f"{m:5.2f}  {lo:17.3f}  {hi:17.3f}")
    # Optimum well above the historical mean: mild rescue OVER-discounts,
    # mild whale UNDER-discounts.
    assert out[0.05][0] > d_star > out[0.05][1]
    # Optimum below the historical mean: the textbook direction.
    assert out[0.38][0] < d_star < out[0.38][1]


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    print("== Proposition 1: direction of the bias"); check_prop1(rng)
    print("\n== Proposition 2: what the monotone constraint does"); check_prop2(rng)
    print("\n== Proposition 3: regret"); check_prop3()
    print("\n== Direction of the decision error"); check_direction()
    print("\nAll checks passed.")
