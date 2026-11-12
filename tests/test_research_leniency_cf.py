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
