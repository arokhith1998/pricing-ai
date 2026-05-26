"""Evals for the Phase 2 win-probability model.

These are ML evals, not unit asserts on a hand-frame: train on a deterministic
synthetic dataset and assert the model clears quality floors and that guidance
behaves sanely. Thresholds are intentionally below observed values to allow for
library/version drift without being meaningless.
"""

from __future__ import annotations

import numpy as np
import pytest

from pricing import model
from pricing.generate import generate
from pricing.ingest import ingest


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    csv = tmp_path_factory.mktemp("data") / "deals.csv"
    generate(n=2000, seed=7).to_csv(csv, index=False)
    df = ingest(csv)
    return df, model.train(df)


def test_auc_clears_floor(trained):
    _df, tm = trained
    # observed ~0.64; floor well below to tolerate drift but reject a coin flip
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
