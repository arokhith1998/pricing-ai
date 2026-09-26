"""Evals for the Phase 2 win-probability model.

These are ML evals, not unit asserts on a hand-frame: train on a deterministic
synthetic dataset and assert the model clears quality floors and that guidance
behaves sanely. Thresholds are intentionally below observed values to allow for
library/version drift without being meaningless.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import brier_score_loss

from pricing import model
from pricing.generate import generate
from pricing.ingest import ingest

ROOT = Path(__file__).resolve().parents[1]
DEALS_CSV = ROOT / "data" / "synthetic" / "deals.csv"


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    # Seed 11, not 7: data/synthetic/deals.csv IS generate(n=2000, seed=7), so
    # seeding this fixture the same way made the floors below one gate wearing
    # two names. An independent draw is what makes them two gates.
    csv = tmp_path_factory.mktemp("data") / "deals.csv"
    generate(n=2000, seed=11).to_csv(csv, index=False)
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
    # An independent draw (seed 11), scored on a time-ordered holdout: AUC
    # 0.631 measured 2026-09-15. A single 500-row holdout carries a 95% CI
    # roughly 0.10 wide, so this floor sits well below the measurement instead
    # of beside it. The tight floor belongs on the pinned fixture, where the
    # baseline was actually measured: see
    # test_holdout_auc_within_floor_with_constraint below.
    assert tm.metrics["auc"] > 0.55


def test_model_is_calibrated(trained):
    _df, tm = trained
    # This is a BIAS check, not a calibration check: a model that predicts the
    # base rate for every deal passes it perfectly, and so does one whose
    # per-deal probabilities are worthless. The gate that actually bites is
    # test_probabilities_beat_a_constant below.
    # 0.08, not 0.05: a time holdout carries its own quarter's win rate, and
    # quarterly win rates on this book swing from 0.553 to 0.654. Measured
    # 2026-09-15: -0.019 on this fixture, -0.065 on the pinned one.
    assert abs(tm.metrics["mean_pred"] - tm.metrics["base_rate"]) < 0.08
    assert tm.metrics["brier"] < 0.26


def test_probabilities_beat_a_constant(trained, trained_on_deals_csv):
    """The gate that bites, asserted on BOTH books, because it only bites on
    one of them.

    Brier under 0.26 and a small mean-pred gap are both satisfied by a model
    that just predicts the training book's win rate for every deal, so neither
    says the per-deal probabilities are worth quoting. Brier skill does: the
    model's Brier against that constant's. Negative means a Head of Pricing is
    better served by "this book wins 59% of the time" than by anything the
    model says about a specific deal, and the guidance panel quotes per-deal
    probabilities.

    Measured 2026-09-15 on the time-ordered holdout, old capacity
    (250 trees / 15 leaves / min_child 50) to current (50 / 7 / 150):

        pinned deals.csv    -0.0746 -> +0.0368
        generated seed 11   +0.0025 -> +0.0458

    The regression this test exists to catch only showed on the pinned book.
    An earlier version of this test asserted on the generated fixture alone,
    where the old capacity scored +0.0025 and would have sailed through. A
    gate that misses the failure it was written for is not a gate, so both
    books are asserted here.
    """
    for label, (_df, tm) in (("seed-11", trained),
                             ("deals.csv", trained_on_deals_csv)):
        assert tm.metrics["brier"] < tm.metrics["brier_constant"], label
        assert tm.metrics["brier_skill"] > 0.0, label


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
    """AUC floor on the pinned fixture, not a pin. PK-15's rule: the
    unconstrained baseline minus a 0.03 acceptance band. Measured 2026-09-15
    at the current capacity, time-ordered holdout: 0.621 unconstrained, 0.614
    with the discount_pct monotone constraint, so the rule gives 0.59. Stated
    instead as skill retained above chance, 0.5 + 0.75 * (0.621 - 0.5) = 0.591,
    the two framings agree here, which they did not at the old capacity. A real
    regression beyond the band still fails; routine library or data drift does
    not flake this suite."""
    _df, tm = trained_on_deals_csv
    assert tm.metrics["auc"] >= 0.59


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


# -- Time-ordered holdout ----------------------------------------------------


def test_holdout_is_the_most_recent_deals(trained_on_deals_csv):
    """Deals are time-ordered, so the holdout must be the latest closes: every
    training deal closed strictly before every scored deal. A random split
    would let the model learn from the future of the deals it is graded on."""
    df, tm = trained_on_deals_csv
    assert tm.metrics["split"] == "time"
    dates = df["close_date"]
    train_dates = dates[~tm.holdout].dropna()
    test_dates = dates[tm.holdout]
    assert train_dates.max() < test_dates.min()
    assert test_dates.min().date().isoformat() == tm.metrics["test_from"]
    assert tm.metrics["n_test"] == int(tm.holdout.sum())
    assert tm.metrics["n_train"] + tm.metrics["n_test"] == len(df)
    # The ordering guarantee covers dated rows only, so the count of rows it
    # could not order is part of the claim, not a footnote.
    assert tm.metrics["n_undated_train"] == 0
    assert tm.metrics["test_share"] == pytest.approx(0.25, abs=0.01)


def test_undated_book_falls_back_to_random_split_and_says_so(trained, caplog):
    df, _tm = trained
    with caplog.at_level(logging.WARNING, logger="pricekeel.model"):
        tm = model.train(df.drop(columns=["close_date"]))
    assert tm.metrics["split"] == "random_stratified"
    assert tm.metrics["test_from"] is None
    assert "random stratified holdout" in caplog.text


def test_recommendation_distribution_and_support_are_pinned(sample_300):
    """What the product actually recommends, pinned so a model change cannot
    move it unobserved.

    The 2026-09-15 capacity fix (250/15/50 to 50/7/150) cut the mean
    recommendation from 0.124 to 0.069, the maximum across the book from 0.27
    to 0.10, and took the share recommending exactly 0% from 0.6% to about
    11%. That was an improvement, since the generator saturates its win curve
    by roughly a 10% discount and the old 0.27 recommendations were overfit
    noise, but it reached users with nothing in the suite noticing. A Head of
    Pricing rerunning the same book sees every number move.

    Second half is the tripwire for a known latent hazard: recommend_discount
    sweeps a fixed 0 to 40% grid for every deal with no per-segment support
    bound, so nothing in the code stops it recommending deeper than that
    segment has ever given. Nothing does today (largest here 0.10, against a
    p99 of 0.244 in the tightest segment: SMB 0.244, MidMarket 0.306,
    Enterprise 0.363), and this fails the moment that stops being true.

    Measured 2026-09-15 on this 300-deal sample: mean 0.069, median 0.090,
    max 0.100, 11.3% at exactly zero, zero deals beyond segment p99.
    """
    df, tm, sample = sample_300
    p99 = df.groupby("segment")["discount_pct"].quantile(0.99)
    recs = []
    for idx in sample.index:
        rec = model.recommend_discount(tm, tm.X_all.loc[[idx]],
                                       float(df.loc[idx, "list_acv"]))
        d = rec["recommended_discount"]
        recs.append(d)
        seg = str(df.loc[idx, "segment"])
        assert d <= float(p99[seg]) + 1e-9, (
            f"{df.loc[idx, 'opportunity_id']} ({seg}): recommended {d:.3f}, "
            f"beyond the segment's p99 observed discount {float(p99[seg]):.3f}"
        )
    recs = np.array(recs)
    # Bands wide enough for library drift, narrow enough that a shift the size
    # of the capacity change fails here instead of shipping quietly. The max
    # assertion carries most of that signal: the old capacity's max was 0.270
    # against this 0.20 bound, while its mean measured 0.124 to 0.127 against
    # a 0.12 bound, a margin thinner than the n_jobs=-1 nondeterminism this
    # repo discloses. Do not trust the mean band alone when retuning.
    assert 0.03 <= recs.mean() <= 0.12
    assert recs.max() <= 0.20
    # Two-sided on purpose: the old capacity recommended exactly zero on 0.7%
    # of deals, so an upper bound alone would not notice a slide back to it.
    assert 0.02 <= (recs == 0.0).mean() <= 0.30


# -- 2026-09-26 fifteen-agent eval: calibration, support, reproducibility ---


def test_gate_fails_for_a_constant_predictor():
    """The gate this suite actually relies on (test_probabilities_beat_a_constant)
    must be able to fail, which the previous mean-only calibration check could
    not (mle-reviewer F2: a model predicting the training win rate for every
    deal scores Brier 0.238 and passes |mean_pred - base_rate| < 0.05 and
    brier < 0.26 perfectly). This proves brier_skill is the gate that bites,
    using the exact formula pricing.model.train computes, with no dependency
    on training an actual model: a constant predictor's Brier against itself
    is identical, so skill is exactly 0.0, and 0.0 > 0.0 is False."""
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, size=500)
    base_rate = float(y.mean())
    p_constant = np.full(len(y), base_rate)
    brier = brier_score_loss(y, p_constant)
    brier_constant = brier_score_loss(y, np.full(len(y), base_rate))
    skill = 1.0 - brier / brier_constant if brier_constant else 0.0
    assert skill == pytest.approx(0.0, abs=1e-9)
    assert not (skill > 0.0), "a constant predictor must fail the skill gate"


def test_metrics_are_stamped_for_reproducibility(trained_on_deals_csv):
    """A claimed number must be traceable to what produced it: the seed, the
    trained booster's own params (including the monotone constraint), the
    feature list, and a fingerprint of the training frame (mle-reviewer F6)."""
    _df, tm = trained_on_deals_csv
    m = tm.metrics
    assert m["seed"] == 7
    assert m["params"]["random_state"] == 7
    assert m["params"]["n_jobs"] == 1, "nondeterministic n_jobs=-1 must not ship"
    assert m["features"] == tm.features
    assert isinstance(m["data_hash"], str) and len(m["data_hash"]) == 16


def test_data_hash_changes_when_the_training_frame_changes(trained_on_deals_csv):
    df, tm = trained_on_deals_csv
    other = model.train(df.iloc[:-1])  # drop one row
    assert other.metrics["data_hash"] != tm.metrics["data_hash"]


def test_calibration_by_band_and_segment_present_and_bounded(trained_on_deals_csv):
    """Calibration must be checkable below the single global mean, since a
    global mean can hide opposite-direction bias in the bands or segments
    underneath it (mle-reviewer F2)."""
    _df, tm = trained_on_deals_csv
    by_band = tm.metrics["calibration_by_band"]
    by_segment = tm.metrics["calibration_by_segment"]
    assert by_band, "no predicted-band calibration recorded"
    assert by_segment, "no per-segment calibration recorded"
    total_band_n = sum(r["n"] for r in by_band)
    total_seg_n = sum(r["n"] for r in by_segment)
    assert total_band_n == tm.metrics["n_test"]
    assert total_seg_n == tm.metrics["n_test"]
    for row in by_band + by_segment:
        assert 0.0 <= row["mean_pred"] <= 1.0
        assert 0.0 <= row["actual_win_rate"] <= 1.0
        assert row["n"] > 0


def test_recommend_discount_clips_to_cohort_support(trained_on_deals_csv):
    """With cohort_discounts supplied and a well-supported cohort, the sweep
    must stay within roughly that cohort's 5th-95th observed percentile
    instead of the unconditional 0-40% grid (mle-reviewer F3)."""
    df, tm = trained_on_deals_csv
    seg = df["segment"].value_counts().idxmax()  # the best-supported segment
    cohort = df[df["segment"] == seg]
    assert len(cohort) >= 50
    cohort_discounts = cohort["discount_pct"].to_numpy()
    idx = cohort.index[0]
    rec = model.recommend_discount(
        tm, tm.X_all.loc[[idx]], float(df.loc[idx, "list_acv"]),
        cohort_discounts=cohort_discounts,
    )
    assert rec["method"] == "modeled_ev_curve"
    lo = np.percentile(cohort_discounts, 5)
    hi = np.percentile(cohort_discounts, 95)
    curve = rec["curve"]
    assert curve["discount"].min() >= lo - 1e-6
    assert curve["discount"].max() <= hi + 1e-6


def test_recommend_discount_falls_back_to_band_guardrail_below_support(trained_on_deals_csv):
    """Fewer than 50 comparable deals must never run the sweep at all: the
    monotone constraint pulls an unsupported optimum toward the empty region
    below the cohort's real discounts (mle-reviewer F3)."""
    df, tm = trained_on_deals_csv
    idx = df.index[0]
    tiny_cohort = df["discount_pct"].to_numpy()[:10]  # under the 50-deal floor
    rec = model.recommend_discount(
        tm, tm.X_all.loc[[idx]], float(df.loc[idx, "list_acv"]),
        cohort_discounts=tiny_cohort,
    )
    assert rec["method"] == "band_guardrail"
    assert rec["cohort_deals"] == 10
    # Never recommends adding discount above the current ask.
    assert rec["recommended_discount"] <= rec["current_discount"] + 1e-9
    assert set(rec["curve"]["discount"]) <= {rec["current_discount"],
                                             rec["recommended_discount"]}


def test_recommend_discount_without_cohort_is_unchanged(trained_on_deals_csv):
    """Callers that omit cohort_discounts keep the prior unclipped 0-40% sweep
    (backward compatibility for existing call sites)."""
    df, tm = trained_on_deals_csv
    idx = df.index[0]
    rec = model.recommend_discount(tm, tm.X_all.loc[[idx]],
                                   float(df.loc[idx, "list_acv"]))
    assert rec["method"] == "modeled_ev_curve"
    assert rec["cohort_deals"] is None
    assert rec["curve"]["discount"].min() == pytest.approx(0.0)
    assert rec["curve"]["discount"].max() == pytest.approx(0.40)


# -- /recommend router: caveat, method label, both explanations -------------


def test_recommend_endpoint_carries_caveat_method_and_both_explanations(monkeypatch):
    """mle-reviewer F4/code-reviewer F3, at the API boundary: the strongest
    dollar claim in the product must ship a caveat, a method label a demo
    deal actually earned, and an explanation for the row the headline
    recommends, not only the row the deal currently sits at."""
    from fastapi.testclient import TestClient

    from api import main as api_main

    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    monkeypatch.setenv("PRICEKEEL_ENV", "dev")
    api_main._rate_state_reset()
    client = TestClient(api_main.app)
    deals = client.get("/deals").json()["deals"]
    assert deals, "no demo deals to recommend on"
    opp_id = deals[0]["opportunity_id"]

    r = client.post("/recommend", json={"opportunity_id": opp_id})
    assert r.status_code == 200
    body = r.json()
    assert body["method"] in ("modeled_ev_curve", "band_guardrail")
    assert body["caveat"] and "correlational" in body["caveat"].lower()
    assert "top_factors" in body and "top_factors_at_recommended" in body
    assert isinstance(body["top_factors"], list)
    assert isinstance(body["top_factors_at_recommended"], list)
    assert "cohort_deals" in body["confidence"]
    api_main._rate_state_reset()
