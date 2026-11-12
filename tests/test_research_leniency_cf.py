"""Sanity tests for the research-only rep-leniency control function
(research/jair-discount-causality). Synthetic data only."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "research" / "jair-discount-causality"))

import leniency_cf as lc  # noqa: E402
from confounded_book import make_book  # noqa: E402


def test_loo_leniency_excludes_own_deal():
    resid = np.array([1.0, 2.0, 3.0, 10.0, 20.0])
    rep = np.array([0, 0, 0, 1, 1])
    z = lc.loo_leniency(resid, rep)
    assert np.allclose(z, [2.5, 2.0, 1.5, 20.0, 10.0])


def test_first_stage_residual_is_orthogonal_to_leniency():
    book = make_book(3000, seed=1, rho=-0.6)
    fs = lc.first_stage(book)
    assert abs(np.corrcoef(fs.resid, fs.leniency)[0, 1]) < 1e-8
    assert fs.n_reps == 12 and fs.partial_f > 10


def test_diagnostic_reads_the_direction():
    for rho, verdict in ((-0.9, "rescue"), (0.9, "whale")):
        book = make_book(3000, seed=2, rho=rho)
        assert lc.diagnostic(book, lc.first_stage(book)).verdict == verdict


def test_skill_dial_off_leaves_the_book_unchanged():
    a = make_book(500, seed=3, rho=0.3)
    b = make_book(500, seed=3, rho=0.3, skill_effect=0.0)
    assert a.equals(b)
    c = make_book(500, seed=3, rho=0.3, skill_effect=0.3)
    assert np.allclose(a["discount_pct"], c["discount_pct"])
    assert not np.allclose(a["base_logit"], c["base_logit"])


# --- exclusion guard (research/jair-discount-causality/exclusion.py) ---------
import exclusion as ex  # noqa: E402


def test_offset_logit_matches_a_known_model():
    rng = np.random.default_rng(0)
    x = rng.standard_normal(20000)
    off = 0.7 * rng.standard_normal(20000)
    y = (rng.random(20000) < 1 / (1 + np.exp(-(0.4 + 1.2 * x + off)))).astype(float)
    b = ex._fit_logit(np.column_stack([np.ones_like(x), x]), y, off)
    assert abs(b[0] - 0.4) < 0.06 and abs(b[1] - 1.2) < 0.06


def test_rep_test_sees_unaligned_skill_but_not_aligned_skill():
    def tau(skill, corr):
        book = make_book(20000, seed=4, rho=0.0, skill_effect=skill, skill_corr=corr)
        return ex.SensitivityCF(book, lc.first_stage(book)).rep_heterogeneity()
    assert tau(0.0, 1.0).tau < 0.08
    unaligned = tau(0.3, 0.0)
    assert unaligned.p_value < 0.01 and 0.2 < unaligned.tau < 0.4
    # Skill that lines up exactly with leniency is invisible to the test.
    assert tau(0.3, 1.0).tau < 0.08


def test_robust_choice_picks_the_smallest_worst_case_regret():
    grid = np.array([0.0, 0.1, 0.2])
    # Two assumed worlds for one deal: one wants 0%, the other wants 20%.
    curves = np.array([[[0.50, 0.50, 0.50]], [[0.20, 0.45, 0.60]]])
    j, width = ex.robust_choice(curves, grid, np.ones((1, 3), bool))
    assert grid[j[0]] == 0.1 and np.isclose(width[0], 0.2)


# --- rep assignment dials (experiment 5) --------------------------------------
def test_assignment_dials_default_to_random_and_do_what_they_say():
    base = make_book(4000, seed=6, rho=0.0)
    assert base.equals(make_book(4000, seed=6, rho=0.0, assign_segment=0.0,
                                 assign_quality=0.0))
    terr = make_book(4000, seed=6, rho=0.0, assign_segment=1.0)
    assert (terr.groupby("rep_id")["segment"].nunique() == 1).all()
    assert lc.balance_p(terr) < 0.001 and lc.balance_p(base) > 0.01

    sort = make_book(4000, seed=6, rho=0.0, assign_quality=0.6)
    by_rep = sort.groupby("rep_id").agg(q=("quality", "mean"), d=("discount_pct", "mean"))
    assert np.corrcoef(by_rep.q, by_rep.d)[0, 1] > 0.8     # strong deals, lenient reps
    assert lc.balance_p(sort) > 0.01                       # and the book cannot see it
