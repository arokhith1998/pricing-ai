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
    # One tolerance, shared with the dashboard verdict (model.CALIBRATION_
    # TOLERANCE, 0.05): the suite must not tolerate a bias the page would
    # warn on (mle-reviewer, 2026-09-26: this gate said 0.08 while the page
    # said 0.05). A time holdout carries its own quarter's win rate, and
    # quarterly win rates on this book swing from 0.553 to 0.654; measured
    # 2026-09-15: -0.019 on this fixture, -0.065 on the pinned one, which is
    # why this asserts on the independent draw only and the pinned book's
    # verdict is the page's warning to show.
    assert (abs(tm.metrics["mean_pred"] - tm.metrics["base_rate"])
            <= model.CALIBRATION_TOLERANCE)
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


# -- 2026-09-26 second pass: support floor, exact current, NaN, one grid -----


ENTERPRISE_11PCT = "OPP-00007"  # Enterprise, 11.2% actual, below the cohort p5


def _enterprise(df):
    cohort = df[df["segment"] == "Enterprise"]
    assert len(cohort) >= 50, "fixture drift: Enterprise no longer well supported"
    return cohort


def test_enterprise_grid_edge_optimum_is_a_support_floor_not_a_modeled_peak(
        trained_on_deals_csv):
    """mle-reviewer F1: on the synthetic Enterprise cohort the clipped sweep's
    win probability does not move at all, so the EV argmax is always the
    grid's lower edge. That is the floor of the cohort's support, not a
    modeled optimum, and it must be labeled so, expose why, and never add
    discount. Asserted on every Enterprise deal, not a sample, because the
    finding was 342 of 342."""
    df, tm = trained_on_deals_csv
    cohort = _enterprise(df)
    cohort_discounts = model.cohort_discounts_for(df, cohort.index[0])
    labels = set()
    for idx in cohort.index:
        rec = model.recommend_discount(
            tm, tm.X_all.loc[[idx]], float(df.loc[idx, "list_acv"]),
            cohort_discounts=cohort_discounts)
        labels.add(rec["method"])
        assert "at_grid_edge" in rec and "win_prob_gain" in rec
        if rec["method"] == "modeled_ev_curve":
            # Only an interior optimum with real win-probability movement
            # may carry the modeled label.
            assert not rec["at_grid_edge"]
            assert rec["win_prob_gain"] >= model.MIN_WIN_PROB_GAIN
        else:
            assert rec["method"] == "support_floor"
            assert rec["at_grid_edge"] or rec["win_prob_gain"] < model.MIN_WIN_PROB_GAIN
            assert rec["recommended_discount"] <= rec["current_discount"] + 1e-9
            assert "not a modeled optimum" in rec["caveat"]
            assert "—" not in rec["caveat"]
    # The finding itself: this cohort earns no modeled label at all today.
    # If a retrain ever gives Enterprise a real interior optimum this line is
    # the one to revisit, deliberately.
    assert labels == {"support_floor"}


def test_uplift_is_measured_at_the_deals_own_discount_not_the_nearest_grid_edge(
        trained_on_deals_csv):
    """code-reviewer major: OPP-00007 sits at 11.2% with an Enterprise grid
    of roughly 14-33%. The old code snapped 11.2% to the 14% edge and told
    the rep "14%, uplift $0", i.e. add discount at a reported zero cost.
    The current point must be scored exactly where the deal is, and a floor
    the model did not earn must never push the discount up."""
    df, tm = trained_on_deals_csv
    idx = df.index[df["opportunity_id"] == ENTERPRISE_11PCT][0]
    assert df.loc[idx, "segment"] == "Enterprise"
    current = float(df.loc[idx, "discount_pct"])
    assert current == pytest.approx(0.1116, abs=5e-4)
    list_acv = float(df.loc[idx, "list_acv"])
    rec = model.recommend_discount(
        tm, tm.X_all.loc[[idx]], list_acv,
        cohort_discounts=model.cohort_discounts_for(df, idx))
    grid = rec["curve"]["discount"].to_numpy()
    assert current < grid.min(), "fixture drift: deal is no longer below the grid"
    # Exact score at 11.2%, not the EV at the 14% edge.
    p_cur, ev_cur = model._score_at(tm, tm.X_all.loc[[idx]], list_acv, current)
    assert rec["win_prob_at_current"] == pytest.approx(p_cur)
    assert rec["expected_acv_at_current"] == pytest.approx(ev_cur)
    assert rec["expected_acv_at_current"] != pytest.approx(
        float(rec["curve"]["expected_acv"].iloc[0]))
    # Never told to add discount on a support floor: stays at 11.2%, no
    # uplift claimed.
    assert rec["method"] == "support_floor"
    assert rec["recommended_discount"] == pytest.approx(current)
    assert rec["uplift"] == pytest.approx(0.0)


def test_current_inside_the_sweep_is_a_candidate_so_uplift_is_never_negative(
        trained_on_deals_csv):
    """With the current discount scored exactly, a deal sitting between two
    grid points could otherwise beat both neighbours and be handed a negative
    uplift. Inside the swept range the current point competes, so uplift is
    never below zero on any deal of the two well-supported segments."""
    df, tm = trained_on_deals_csv
    for seg in ("SMB", "MidMarket"):
        cohort = df[df["segment"] == seg]
        cohort_discounts = model.cohort_discounts_for(df, cohort.index[0])
        grid = model._cohort_grid(cohort_discounts)
        inside = cohort[(cohort["discount_pct"] >= grid.min())
                        & (cohort["discount_pct"] <= grid.max())]
        for idx in inside.sample(n=min(60, len(inside)), random_state=3).index:
            rec = model.recommend_discount(
                tm, tm.X_all.loc[[idx]], float(df.loc[idx, "list_acv"]),
                cohort_discounts=cohort_discounts)
            assert rec["uplift"] >= -1e-6, df.loc[idx, "opportunity_id"]


def test_nan_in_cohort_is_dropped_instead_of_raising(trained_on_deals_csv):
    """mle-reviewer F2: one blank list price leaves one discount_pct NaN and
    ingest keeps the row; np.percentile over the raw column raised and
    /recommend returned 500 for every deal in the segment."""
    df, tm = trained_on_deals_csv
    idx = df.index[0]
    cohort = model.cohort_discounts_for(df, idx)
    poisoned = np.concatenate([cohort, [np.nan, np.inf]])
    rec = model.recommend_discount(
        tm, tm.X_all.loc[[idx]], float(df.loc[idx, "list_acv"]),
        cohort_discounts=poisoned)
    assert rec["method"] in ("modeled_ev_curve", "support_floor")
    assert rec["cohort_deals"] == len(cohort)  # the two junk values are gone
    assert np.isfinite(rec["curve"]["discount"]).all()
    # cohort_discounts_for itself drops them at the source.
    dirty = df.copy()
    dirty.loc[idx, "discount_pct"] = np.nan
    assert len(model.cohort_discounts_for(dirty, idx)) == len(cohort) - 1


def test_nan_current_discount_returns_no_discount_on_record(trained_on_deals_csv):
    df, tm = trained_on_deals_csv
    idx = df.index[0]
    row = tm.X_all.loc[[idx]].copy()
    row["discount_pct"] = np.nan
    rec = model.recommend_discount(
        tm, row, float(df.loc[idx, "list_acv"]),
        cohort_discounts=model.cohort_discounts_for(df, idx))
    assert rec["method"] == "no_discount_on_record"
    for key in ("recommended_discount", "uplift", "expected_acv_at_current",
                "expected_acv_at_rec", "win_prob_at_rec", "win_prob_at_current",
                "current_discount"):
        assert rec[key] is None, key
    assert rec["curve"].empty
    assert "no discount on record" in rec["caveat"]
    # band_context files nothing under a band when there is no discount.
    dirty = df.copy()
    dirty.loc[idx, "discount_pct"] = np.nan
    ctx = model.band_context(dirty, idx, rec["recommended_discount"])
    assert ctx["current_band"] is None and ctx["recommended_band"] is None


def test_recommend_endpoint_survives_a_blank_discount_in_the_segment(monkeypatch):
    """The same finding at the API boundary: one NaN discount in a segment
    must not 500 the other deals in it, and the NaN deal itself must come
    back labeled, with no uplift, rather than as a number."""
    from fastapi.testclient import TestClient

    from api import main as api_main
    from api.routers import model as model_router

    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    monkeypatch.setenv("PRICEKEEL_ENV", "dev")
    api_main._rate_state_reset()
    import dataclasses

    df, tm = model_router.engine()
    dirty = df.copy()
    ent = dirty[dirty["segment"] == "Enterprise"]
    blank_idx, other_idx = ent.index[0], ent.index[1]
    dirty.loc[blank_idx, "discount_pct"] = np.nan
    # A blank list price leaves the feature frame NaN too (prepare coerces),
    # so the model's own row for the deal must carry it, not just df.
    X_dirty = tm.X_all.copy()
    X_dirty.loc[blank_idx, "discount_pct"] = np.nan
    tm_dirty = dataclasses.replace(tm, X_all=X_dirty)
    monkeypatch.setattr(model_router, "engine", lambda: (dirty, tm_dirty))
    client = TestClient(api_main.app)

    ok = client.post("/recommend", json={
        "opportunity_id": str(dirty.loc[other_idx, "opportunity_id"])})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["method"] in ("modeled_ev_curve", "support_floor")
    assert body["confidence"]["cohort_deals"] == len(ent) - 1

    blank = client.post("/recommend", json={
        "opportunity_id": str(dirty.loc[blank_idx, "opportunity_id"])})
    assert blank.status_code == 200, blank.text
    b = blank.json()
    assert b["method"] == "no_discount_on_record"
    assert b["uplift"] is None and b["recommended_discount"] is None
    assert b["top_factors_at_recommended"] == []
    assert b["band_context"]["current_band"] is None
    api_main._rate_state_reset()


def test_recommend_endpoint_exposes_edge_and_gain_and_method_caveat(monkeypatch):
    from fastapi.testclient import TestClient

    from api import main as api_main

    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    monkeypatch.setenv("PRICEKEEL_ENV", "dev")
    api_main._rate_state_reset()
    client = TestClient(api_main.app)
    r = client.post("/recommend", json={"opportunity_id": ENTERPRISE_11PCT})
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "support_floor"
    assert isinstance(body["at_grid_edge"], bool)
    assert body["win_prob_gain"] is not None and body["win_prob_gain"] >= 0.0
    assert "not a modeled optimum" in body["caveat"]
    assert "correlational" in body["caveat"]
    assert body["win_prob_at_current"] == pytest.approx(
        body["win_prob_at_rec"])  # recommended == current on this deal
    api_main._rate_state_reset()


def test_justified_discount_sits_on_the_deals_own_cohort_grid(trained_on_deals_csv):
    """mle-reviewer F4: leakage_vs_model swept 0-40% for every deal while
    /recommend was clipped, so one Enterprise deal read "justified 7%" on the
    page and "recommend 14%" in the panel. Every well-supported cohort's
    justified discounts must now lie on that cohort's own grid, the same
    one recommend_discount sweeps."""
    df, tm = trained_on_deals_csv
    justified = model.justified_discounts(tm, df)
    won = df[df["is_won"]]
    assert justified.index.equals(won.index)
    assert justified.notna().all()
    for seg in ("SMB", "MidMarket", "Enterprise"):
        cohort_discounts = model.cohort_discounts_for(
            df, df.index[df["segment"] == seg][0])
        grid = model._cohort_grid(cohort_discounts)
        j = justified[won["segment"] == seg].to_numpy()
        assert (j >= grid.min() - 1e-9).all(), seg
        assert (j <= grid.max() + 1e-9).all(), seg
        assert np.isin(np.round(j, 4), np.round(grid, 4)).all(), seg
    # And the two surfaces agree on the deal the finding named: the
    # justified discount is the grid point /recommend's sweep peaks at.
    idx = df.index[df["opportunity_id"] == ENTERPRISE_11PCT][0]
    rec = model.recommend_discount(
        tm, tm.X_all.loc[[idx]], float(df.loc[idx, "list_acv"]),
        cohort_discounts=model.cohort_discounts_for(df, idx))
    peak = float(rec["curve"]["discount"].iloc[
        int(rec["curve"]["expected_acv"].to_numpy().argmax())])
    assert float(justified.loc[idx]) == pytest.approx(peak)
    # The headline still holds together after the change.
    ml = model.leakage_vs_model(tm, df)
    assert ml["deals"] == int(justified.notna().sum())
    assert ml["mean_justified_discount"] >= float(
        model._cohort_grid(model.cohort_discounts_for(
            df, df.index[df["segment"] == "SMB"][0])).min())


def test_leakage_vs_model_excludes_deals_with_no_discount_on_record(
        trained_on_deals_csv):
    df, tm = trained_on_deals_csv
    dirty = df.copy()
    won_idx = dirty.index[dirty["is_won"]][:3]
    dirty.loc[won_idx, "discount_pct"] = np.nan
    ml = model.leakage_vs_model(tm, dirty)
    assert ml["deals"] == int(df["is_won"].sum()) - 3
    assert np.isfinite(ml["model_excess_won"])


def test_prepare_counts_values_coerced_to_nan(trained_on_deals_csv):
    """A numeric feature the parser could not read trains as missing. That is
    fine, but it must be counted, not silent (code-reviewer, 2026-09-26)."""
    df, tm = trained_on_deals_csv
    assert tm.metrics["n_coerced_to_nan"] == 0
    assert set(tm.metrics["coerced_to_nan_by_feature"]) <= set(model.NUMERIC)
    dirty = df.copy()
    dirty["term_months"] = dirty["term_months"].astype(object)
    dirty.loc[dirty.index[:2], "term_months"] = "twelve"
    other = model.train(dirty)
    assert other.metrics["coerced_to_nan_by_feature"]["term_months"] == 2
    assert other.metrics["n_coerced_to_nan"] == 2


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
    assert body["method"] in ("modeled_ev_curve", "support_floor",
                              "band_guardrail")
    assert body["caveat"] and "correlational" in body["caveat"].lower()
    assert "top_factors" in body and "top_factors_at_recommended" in body
    assert isinstance(body["top_factors"], list)
    assert isinstance(body["top_factors_at_recommended"], list)
    assert "cohort_deals" in body["confidence"]
    api_main._rate_state_reset()
