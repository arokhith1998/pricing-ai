"""Numerical checks for Propositions 4 and 5 in
docs/design/2026-11-11-jair-paper-propositions.md.

Proposition 4: with a concave (saturating) discount effect and rescue
confounding, the observational win curve is a hump; the monotone-constrained
fit follows it up to a point t and is flat afterwards; the constrained
recommendation is never above the unconstrained one; and it has weakly higher
regret whenever the unconstrained recommendation is at or below the true
optimum.

Proposition 5: rep skill that is a linear function of rep leniency generates
exactly the same data as a model with no rep skill and a different discount
effect, so no test on the deal book can tell them apart, while the two models
recommend different discounts.

Run:  python research/jair-discount-causality/verify_propositions_2.py
Every check is an assertion. Synthetic only.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm
from sklearn.isotonic import IsotonicRegression

GRID = np.linspace(0.0, 0.40, 2001)
M, SD_D = 0.12, 0.05


def g(d, height=1.3, scale=0.05):
    """Concave, saturating discount effect (the generator's shape)."""
    return height * np.tanh(d / scale)


def structural_curve(alpha, beta, **kw):
    return norm.cdf((alpha + g(GRID, **kw)) / np.sqrt(1 + beta**2))


def observational_curve(rho, alpha, beta, **kw):
    lam = rho / SD_D
    return norm.cdf((alpha + g(GRID, **kw) + beta * lam * (GRID - M))
                    / np.sqrt(1 + beta**2 * (1 - rho**2)))


def monotone_fit(curve, weights):
    return IsotonicRegression(increasing=True).fit(GRID, curve, sample_weight=weights).predict(GRID)


def first_argmax(values):
    return int(np.flatnonzero(values >= values.max() - 1e-12)[0])


def check_prop4():
    w = norm.pdf(GRID, M, SD_D)              # where the historical discounts are
    print(" alpha beta   rho   hump  t      d_unc  d_con  d*     regret_unc regret_con")
    n_hump = n_strict = 0
    for alpha in (-1.0, -0.5, 0.0):
        for beta in (0.55, 1.5):
            p_true = structural_curve(alpha, beta)
            rev = (1 - GRID) * p_true
            j_star = first_argmax(rev)
            for rho in (-0.9, -0.7, -0.5, -0.3, -0.1, 0.1, 0.5, 0.9):
                pi = observational_curve(rho, alpha, beta)
                fit = monotone_fit(pi, w)
                peak = int(pi.argmax())
                rises_then_falls = (np.all(np.diff(pi[:peak + 1]) >= -1e-12)
                                    and np.all(np.diff(pi[peak:]) <= 1e-12))
                hump = rises_then_falls and 0 < peak < len(GRID) - 1
                # (a) with a concave effect the curve is single-peaked
                assert rises_then_falls or np.all(np.diff(pi) >= -1e-12)
                # (b) shape of the constrained fit: the curve itself, then flat
                flat = np.flatnonzero(np.abs(fit - pi) > 1e-6)
                t = flat[0] - 1 if len(flat) else len(GRID) - 1
                j_u = first_argmax((1 - GRID) * pi)
                j_c = first_argmax((1 - GRID) * fit)
                if hump:
                    n_hump += 1
                    assert t <= peak
                    assert np.allclose(fit[:t + 1], pi[:t + 1], atol=1e-6)
                    assert np.ptp(fit[t + 1:]) < 1e-9
                    if t >= 0:
                        assert abs(fit[-1] - pi[t + 1]) < 5e-3   # level = pi(t)
                    else:      # the whole curve is pooled: flat from the floor
                        assert fit[-1] <= pi[0] + 1e-9 and j_c == 0
                # (c) the constraint never raises the recommendation
                assert j_c <= j_u
                # (d) if the unconstrained pick is at or below the optimum,
                #     the constraint cannot reduce regret
                reg_u, reg_c = rev[j_star] - rev[j_u], rev[j_star] - rev[j_c]
                if j_u <= j_star:
                    assert reg_c >= reg_u - 1e-12
                # (e) with whale confounding the curve rises, so nothing changes
                if rho > 0:
                    assert j_c == j_u and np.allclose(fit, pi, atol=1e-6)
                n_strict += j_c < j_u
                if alpha == -0.5:
                    print(f"{alpha:6.1f} {beta:4.2f} {rho:5.1f}  {str(hump):5s} {GRID[max(t, 0)]:.3f}  "
                          f"{GRID[j_u]:.3f}  {GRID[j_c]:.3f}  {GRID[j_star]:.3f}  "
                          f"{reg_u / rev[j_star]:9.2%} {reg_c / rev[j_star]:9.2%}")
    assert n_hump > 0 and n_strict > 0
    print(f"humps: {n_hump}; cases where the constraint strictly lowers the pick: {n_strict}")

    # Outside the single-peaked case the ordering can fail: a dip between two
    # high regions lets the constrained fit prefer the far side of the dip.
    pi = np.where(GRID < 0.05, 0.60, np.where(GRID < 0.10, 0.30, 0.64))
    fit = monotone_fit(pi, np.ones_like(GRID))
    j_u, j_c = first_argmax((1 - GRID) * pi), first_argmax((1 - GRID) * fit)
    assert j_c > j_u
    print(f"non-single-peaked counterexample: unconstrained {GRID[j_u]:.2f}, "
          f"constrained {GRID[j_c]:.2f}")


def check_prop5(rng):
    n, n_reps = 200_000, 12
    alpha, beta, rho = -0.5, 0.55, 0.0
    bias = rng.normal(0, 0.045, n_reps)
    bias -= bias.mean()
    kappa_delta = -0.3 / bias.std()          # skill = -0.3 per sd of leniency
    rep = rng.integers(0, n_reps, n)
    q = rng.standard_normal(n)
    v = 0.035 * (rho * q + np.sqrt(1 - rho**2) * rng.standard_normal(n))
    eps = rng.standard_normal(n)
    d = M + bias[rep] + v

    # World T: reps differ in skill, in step with their leniency.
    y_t = alpha + g(d) + beta * q + kappa_delta * bias[rep] + eps > 0
    # World A: no rep skill at all. A different discount effect and a
    # different unobservable, which is still independent of the rep.
    g_alt = g(d) + kappa_delta * d
    u_alt = beta * q - kappa_delta * v + eps
    y_a = (alpha - kappa_delta * M) + g_alt + u_alt > 0
    assert np.array_equal(y_t, y_a)
    assert abs(np.corrcoef(u_alt, bias[rep])[0, 1]) < 0.01
    print(f"identical outcomes in both worlds for all {n:,} deals")

    # The two worlds disagree about what a discount does.
    p_t = np.mean([norm.cdf((alpha + g(GRID) + kappa_delta * b) / np.sqrt(1 + beta**2))
                   for b in bias], axis=0)
    p_a = norm.cdf((alpha - kappa_delta * M + g(GRID) + kappa_delta * GRID) / u_alt.std())
    d_t = GRID[first_argmax((1 - GRID) * p_t)]
    d_a = GRID[first_argmax((1 - GRID) * p_a)]
    rev_t = (1 - GRID) * p_t
    loss = 1 - rev_t[first_argmax((1 - GRID) * p_a)] / rev_t.max()
    print(f"best discount if reps differ in skill (true): {d_t:.3f}; "
          f"if they do not (same data): {d_a:.3f}; regret of the latter: {loss:.1%}")
    assert abs(d_t - d_a) > 0.01
    peak = GRID[int(p_a.argmax())]
    print(f"in the no-skill world the causal curve peaks at {peak:.3f} and then falls")
    assert 0 < peak < GRID[-1]


if __name__ == "__main__":
    print("== Proposition 4: saturating response"); check_prop4()
    print("\n== Proposition 5: undetectable rep skill"); check_prop5(np.random.default_rng(7))
    print("\nAll checks passed.")
