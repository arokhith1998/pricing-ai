"""Evals for the Phase 2 win-probability model.

These are ML evals, not unit asserts on a hand-frame: train on a deterministic
synthetic dataset and assert the model clears quality floors and that guidance
behaves sanely. Thresholds are intentionally below observed values to allow for
library/version drift without being meaningless.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pricing import model
from pricing.generate import generate
from pricing.ingest import ingest

ROOT = Path(__file__).resolve().parents[1]
DEALS_CSV = ROOT / "data" / "synthetic" / "deals.csv"


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    csv = tmp_path_factory.mktemp("data") / "deals.csv"
    generate(n=2000, seed=7).to_csv(csv, index=False)
    df = ingest(csv)
    return df, model.train(df)


@pytest.fixture(scope="module")
def trained_on_deals_csv():
    """Train once on the real synthetic deals fixture (not the generator),
    so the monotone-constraint evals below run against the exact data the
    2026-09-11 measurement (100% declining curves, about 150 of 300 inverted
    recs, 149 to 151 across retrains because n_jobs=-1 is nondeterministic)
    was taken on.
    """
    df = ingest(DEALS_CSV)
    return df, model.train(df)


@pytest.fixture(scope="module")
def sample_300(trained_on_deals_csv):
    df, tm = trained_on_deals_csv
    sample = df.sample(n=min(300, len(df)), random_state=7)
    return df, tm, sample


def test_auc_clears_floor(trained):
    _df, tm = trained
    # Baseline measured 2026-09-11 on data/synthetic/deals.csv: 0.640
    # unconstrained, 0.619 with the discount_pct monotone constraint (see
    # test_holdout_auc_within_floor_with_constraint below). This floor stays
    # well under both so ordinary drift does not flake the suite.
    assert tm.metrics["auc"] > 0.60


def test_model_is_calibrated(trained):
    _df, tm = trained
    # mean predicted win prob should track the actual holdout base rate
    assert abs(tm.metrics["mean_pred"] - tm.metrics["base_rate"]) < 0.05
    assert tm.metrics["brier"] < 0.26


def test_predictions_in_unit_interval(trained):
    df, tm = trained
    p = model.predict_win_prob(tm, tm.X_all)
    assert p.min() >= 0.0 and p.max() <= 1.0
    assert len(p) == len(df)


def test_no_leakage_features(trained):
    _df, tm = trained
    # outcome-adjacent / post-quote fields must never be model inputs
    forbidden = {"booked_acv", "price_realization", "discount_amount",
                 "off_policy", "off_policy_unapproved", "cycle_days",
                 "is_won", "outcome", "lost_reason"}
    assert forbidden.isdisjoint(set(tm.features))
    assert "discount_pct" in tm.features  # the lever must be present


def test_explanations_reconcile_with_prediction(trained):
    _df, tm = trained
    row = tm.X_all.iloc[[0]]
    contribs = model.explain(tm, row)
    raw = contribs["contribution"].sum()  # log-odds incl. base
    prob_from_contribs = 1.0 / (1.0 + np.exp(-raw))
    prob_direct = model.predict_win_prob(tm, row)[0]
    assert prob_from_contribs == pytest.approx(prob_direct, abs=1e-6)


def test_leakage_vs_model_is_sane(trained):
    df, tm = trained
    ml = model.leakage_vs_model(tm, df)
    assert ml["deals"] > 0
    assert 0.0 <= ml["mean_justified_discount"] <= 0.40
    assert ml["model_excess_won"] >= 0.0
    assert 0.0 <= ml["model_excess_pct_of_booked"] < 1.0
    # the synthetic data has real over-discounting → some model excess exists
    assert ml["model_excess_won"] > 0.0


def test_comparable_deals_are_relevant(trained):
    df, _tm = trained
    idx = df.index[0]
    comps = model.comparable_deals(df, idx, k=5)
    assert len(comps) == 5
    # never returns the deal itself
    assert df.loc[idx, "opportunity_id"] not in set(comps["opportunity_id"])
    # large cohort → all neighbours share the segment
    assert (comps["segment"] == df.loc[idx, "segment"]).all()
    # carries the outcome so won AND lost comparables are representable
    assert comps["is_won"].dtype == bool


def test_band_context_matches_segment_cohort(trained):
    from pricing.schema import DISCOUNT_BANDS, band_for

    df, _tm = trained
    idx = df.index[0]
    seg = str(df.loc[idx, "segment"])
    ctx = model.band_context(df, idx, recommended_discount=0.03)

    assert ctx["segment"] == seg
    assert ctx["cohort_deals"] == int((df["segment"] == seg).sum())
    labels = {label for *_rest, label in DISCOUNT_BANDS}
    assert {b["band"] for b in ctx["bands"]}.issubset(labels)
    assert all(0.0 <= b["win_rate"] <= 1.0 for b in ctx["bands"])
    # every deal lands in exactly one band, so band counts partition the cohort
    assert sum(b["deals"] for b in ctx["bands"]) == ctx["cohort_deals"]
    assert ctx["recommended_band"] == band_for(0.03)
    assert ctx["current_band"] == band_for(float(df.loc[idx, "discount_pct"]))


def test_recommend_discount_maximizes_expected_acv(trained):
    df, tm = trained
    # pick a clearly over-discounted won deal
    won = df[df["is_won"] & (df["discount_pct"] > 0.25)]
    idx = won["list_acv"].idxmax()
    rec = model.recommend_discount(tm, tm.X_all.loc[[idx]],
                                   float(df.loc[idx, "list_acv"]))
    assert 0.0 <= rec["recommended_discount"] <= 0.40
    # the recommended point is the argmax over the grid, so it must beat both
    # the current discount and the maximum-discount endpoint
    assert rec["uplift"] >= 0.0
    curve = rec["curve"]
    assert rec["expected_acv_at_rec"] >= curve["expected_acv"].iloc[-1] - 1e-6
    assert rec["expected_acv_at_rec"] == pytest.approx(curve["expected_acv"].max())


# -- PK-15: discount_pct monotone constraint -------------------------------
#
# Finding (measured 2026-09-11, 300-deal sample of data/synthetic/deals.csv,
# unconstrained model): 100% of /recommend win-probability curves decline
# somewhere, 90% swing more than 30 points peak-to-trough, and about 150 of
# 300 (149 to 151 across retrains, since n_jobs=-1 is nondeterministic) of
# recommendations lowered the discount while claiming win probability rose
# by more than 2 points (e.g. OPP-00280: 40% -> 11%, P(win) 31% -> 74%). Root
# cause: discount is endogenous (reps discount more on deals already in
# trouble), so an unconstrained tree reads the marker as the cause.
#
# Fix: monotone_constraints=+1 on discount_pct (0 elsewhere),
# monotone_constraints_method="advanced". With the constraint: 0 declining
# curves, 0 inverted recommendations, holdout AUC moves 0.640 -> 0.619, and
# OPP-00280 becomes 40% -> 10% with P(win) 42% -> 40%, the true leakage story.


def test_recommend_curves_are_non_decreasing_in_discount(sample_300):
    """Every /recommend win-probability curve must never fall as discount
    rises. Tolerance 1e-9 allows float roundoff only, not a real decline."""
    df, tm, sample = sample_300
    for idx in sample.index:
        X_row = tm.X_all.loc[[idx]]
        rec = model.recommend_discount(tm, X_row, float(df.loc[idx, "list_acv"]))
        win_prob = rec["curve"]["win_prob"].to_numpy()
        diffs = np.diff(win_prob)
        assert diffs.min() >= -1e-9, (
            f"{df.loc[idx, 'opportunity_id']}: win_prob declined by "
            f"{-diffs.min():.4f} somewhere on the discount grid"
        )


def test_no_recommendation_lowers_discount_while_raising_win_prob(sample_300):
    """Zero recommendations may lower the discount by more than 0.5 points
    while claiming win_prob_at_rec beats the curve's win prob at the
    deal's current discount by more than 2 points (0.02). That inversion is
    exactly the leakage-flavored guidance PK-15 exists to kill.

    This restates the non-decreasing invariant already asserted by
    test_recommend_curves_are_non_decreasing_in_discount, but in the
    product-facing language of the acceptance criterion (discount lowered,
    win_prob claimed to rise), not as an independent probe of the model.
    """
    df, tm, sample = sample_300
    violations = []
    for idx in sample.index:
        X_row = tm.X_all.loc[[idx]]
        rec = model.recommend_discount(tm, X_row, float(df.loc[idx, "list_acv"]))
        curve = rec["curve"]
        cur_i = int(np.argmin(np.abs(curve["discount"].to_numpy() - rec["current_discount"])))
        win_prob_at_current = float(curve["win_prob"].iloc[cur_i])
        lowered_by = rec["current_discount"] - rec["recommended_discount"]
        raised_by = rec["win_prob_at_rec"] - win_prob_at_current
        if lowered_by > 0.005 and raised_by > 0.02:
            violations.append((df.loc[idx, "opportunity_id"], lowered_by, raised_by))
    assert violations == []


def test_holdout_auc_within_floor_with_constraint(trained_on_deals_csv):
    """AUC floor on the real deals.csv split, not a pin. Baseline measured
    2026-09-11: 0.640 unconstrained, 0.619 with the discount_pct monotone
    constraint (advanced method). The floor is 0.61: the 0.640 unconstrained
    baseline minus the 0.03 acceptance band, so a real regression beyond the
    accepted AUC cost still fails while routine library or data drift does
    not flake this suite."""
    _df, tm = trained_on_deals_csv
    assert tm.metrics["auc"] >= 0.61


def test_booster_carries_discount_pct_monotone_constraint(trained_on_deals_csv):
    """The trained booster's own params, not just the Python call site, carry
    +1 on discount_pct and 0 everywhere else, using the position derived from
    the prepared feature order (never a hardcoded index)."""
    _df, tm = trained_on_deals_csv
    params = tm.model.booster_.params
    assert params.get("monotone_constraints_method") == "advanced"
    constraints = params.get("monotone_constraints")
    assert constraints is not None
    assert len(constraints) == len(tm.features)
    expected = [1 if f == "discount_pct" else 0 for f in tm.features]
    assert constraints == expected
    assert constraints[tm.features.index("discount_pct")] == 1
    assert sum(constraints) == 1
