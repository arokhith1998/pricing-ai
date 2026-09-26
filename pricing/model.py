"""Phase 2 — win-probability model + SHAP explanations + discount guidance.

"Predict the next deal." A LightGBM classifier estimates P(win) from features
known *at quote time*, including the proposed discount. From that we derive the
wedge's forward-looking output: the discount that maximizes expected booked
ACV for a given deal.

Design choices:
  * Leakage-free features only. We include `discount_pct` (the lever) but
    exclude its algebraic twins (booked_acv, price_realization, discount_amount,
    off_policy) and anything that encodes the outcome or the close date
    (cycle_days). Training on booked_acv would let the model cheat.
    One deliberate exception: `is_quarter_end` is derived from close_date
    (pricing/ingest.py), so strictly it is known only at close. At quote time a
    rep knows the expected close date, which is why it stays, but on a real
    book whether a deal actually lands in the quarter-end window is partly
    determined by whether it closes at all. Treat it as a known quote-time
    approximation, not as a clean quote-time feature.
  * Explainability via LightGBM's NATIVE SHAP contributions
    (`predict(pred_contrib=True)`) — no extra `shap` dependency, exact for the
    tree, and the foundation for per-deal "why" in enterprise (explainability >
    accuracy).
  * `discount_pct` carries a monotone constraint of +1 (0 on every other
    feature), with `monotone_constraints_method="advanced"`. Discount is
    endogenous: reps discount harder on deals already in trouble, so an
    unconstrained tree learns "high discount" as a marker of a losing deal and
    reports P(win) falling as discount rises, for every deal, on every curve.
    That is a correlation read as a cause. The constraint forces the model to
    treat a larger discount as never hurting the deal's own odds, which is the
    only causally defensible direction here. On the random holdout PK-15
    measured (2026-09-11, data/synthetic/deals.csv) it cost AUC, 0.640 to
    0.619. On the time-ordered holdout at the capacity set below it costs
    0.007 (0.621 unconstrained vs 0.614 constrained, 2026-09-15), inside the
    noise of a holdout whose 95% CI is about 0.10 wide. Cheap, not free.
  * The holdout is the latest 25% of closes, not a random sample. Deals are
    time-ordered and the model scores deals that have not closed yet, so a
    random split lets it learn from deals that closed after the ones it is
    graded on and overstates how well it ranks. On the synthetic book the two
    splits land within noise of each other (random-split AUC across 20 seeds
    ranged 0.551 to 0.670 at the pre-2026-09-15 capacity) because the
    generator has no drift: here the time split validates the pipeline rather
    than demonstrating drift robustness. Real books drift, which is exactly
    when a random split would flatter. A book with no
    usable close dates falls back to a random stratified holdout, logged and
    recorded in metrics["split"].
  * Discount guidance maximizes expected ACV = P(win | discount) x list x
    (1 - discount). Because the win curve saturates, the optimum sits where the
    marginal win gain stops covering the marginal price given away: with the
    constraint, that gain is always non-negative, so the optimum is the
    smallest discount whose win-probability gain still buys back more revenue
    than the price given away, not an artifact of a curve that dips and
    recovers.
  * The sweep is clipped to the deal's cohort when `recommend_discount` is
    given `cohort_discounts`: a 0-40% grid run against every deal regardless
    of support pulls the EV optimum into whatever region has no data, since
    the monotone constraint guarantees the win curve keeps rising as discount
    falls. Clipped to roughly the cohort's 5th-95th observed percentile, and
    below about 50 comparable deals the sweep does not run at all: a
    band-guardrail fallback (method "band_guardrail") is returned instead of
    a curve optimum (mle-reviewer F3, 2026-09-26).
  * `metrics` records brier_skill (against the training book's own win rate,
    not just Brier in isolation), calibration by predicted band and by
    segment, and seed/params/features/data_hash so a claimed number can be
    reproduced or disproven (mle-reviewer F2, F6).

CLI:  python -m pricing.model data/synthetic/deals.csv
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from pricing import metrics
from pricing.ingest import ingest
from pricing.schema import band_for

logger = logging.getLogger("pricekeel.model")

# Features available at quote time. Categorical first, then numeric.
CATEGORICAL = ["segment", "region", "industry", "product_tier", "value_metric"]
NUMERIC = ["list_acv", "discount_pct", "term_months", "quantity",
           "is_quarter_end", "competitor_present"]
TARGET = "is_won"

# Capacity is set by forward-fold skill, not by holdout AUC. The previous
# 250 trees / 15 leaves / min_child 50 was tuned against a random holdout,
# which is tuning against the test set, and it overfit this book: across 5
# expanding forward folds it scored AUC 0.604 with a Brier SKILL of -0.020,
# meaning its probabilities lost to simply quoting the training win rate.
# Measured 2026-09-15 on data/synthetic/deals.csv, same folds throughout:
#   250/15/50   AUC 0.604 (se 0.023)  Brier 0.2430  skill -0.020
#   100/7/150   AUC 0.643 (se 0.018)  Brier 0.2242  skill +0.059
#   50/7/150    AUC 0.651 (se 0.018)  Brier 0.2244  skill +0.059
#   50/5/200    AUC 0.649 (se 0.013)  Brier 0.2259  skill +0.053
# The smaller model both ranks better and earns its probabilities. Tune this
# against folds, never against the single holdout the tests gate on.
# n_jobs=1, not -1 (mle-reviewer F6): with more than one thread LightGBM's
# histogram reduction order is nondeterministic, so a fixed random_state alone
# does not make a run reproducible. A Head of Pricing rerunning the same book
# must see the same numbers. Single-threaded costs latency, not correctness,
# and this book (2,000 rows, 50 trees) trains in well under a second either way.
_PARAMS = dict(
    n_estimators=50, learning_rate=0.05, num_leaves=7,
    min_child_samples=150, subsample=0.8, colsample_bytree=0.7,
    reg_lambda=1.0, random_state=7, n_jobs=1, verbosity=-1,
)


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str], list[str]]:
    """Build the quote-time feature matrix X and target y from enriched deals.

    Degrades gracefully: only uses feature columns actually present.
    """
    cat = [c for c in CATEGORICAL if c in df.columns]
    num = [c for c in NUMERIC if c in df.columns]
    X = pd.DataFrame(index=df.index)
    for c in cat:
        X[c] = df[c].astype("category")
    for c in num:
        col = df[c]
        if col.dtype == bool:
            col = col.astype(int)
        X[c] = pd.to_numeric(col, errors="coerce")
    y = df[TARGET].astype(int)
    return X, y, cat, num


@dataclass
class TrainedModel:
    model: LGBMClassifier
    features: list[str]
    categorical: list[str]
    metrics: dict
    X_all: pd.DataFrame  # full feature frame (for category-consistent scoring)
    # Row mask over the training frame: True for deals scored in the holdout.
    holdout: np.ndarray | None = None


def _holdout_mask(df: pd.DataFrame, y: pd.Series, test_size: float,
                  seed: int) -> tuple[np.ndarray, str, str | None]:
    """Choose the evaluation holdout. Returns (mask, split, test_from).

    Time split when close dates allow it: every deal closed on or after the
    cutoff is scored, everything earlier trains. The ordering guarantee covers
    dated rows: an undated row trains by choice, since dropping it would throw
    away signal, and metrics["n_undated_train"] counts them so the guarantee is
    never overstated. Ties at the cutoff all land in the holdout, so a single
    day never straddles the boundary.

    If the latest slice holds a single outcome class (AUC is undefined there)
    the cutoff walks earlier rather than abandoning time order, and only a book
    where no cutoff works at all falls back to a random stratified split,
    loudly. That fallback reintroduces exactly the leakage this function
    exists to prevent, so it is always visible in metrics["split"].

    Deliberately not grouped by account: 241 of 300 accounts appear on both
    sides of the split, but no account-derived field is a feature, and when
    scoring a live quote you do know that account's closed history. Grouping
    would measure a colder start than the product actually has.
    """
    n = len(df)
    reason = "no close_date column"
    if "close_date" in df.columns:
        dates = pd.to_datetime(df["close_date"], errors="coerce")
        dated = dates.dropna().sort_values(kind="mergesort")
        if len(dated):
            undated = n - len(dated)
            pos = min(max(int(n * (1.0 - test_size)) - undated, 0), len(dated) - 1)
            yv = y.to_numpy()
            # Walk the cutoff earlier while a side is single-class: a bigger
            # holdout still beats giving up the ordering guarantee. Stop once
            # the holdout would pass half the book, which is no longer a
            # holdout.
            for p in range(pos, -1, -1):
                cutoff = dated.iloc[p]
                mask = (dates >= cutoff).to_numpy()
                if mask.sum() > n * 0.5:
                    break
                if (0 < mask.sum() < n and len(np.unique(yv[mask])) == 2
                        and len(np.unique(yv[~mask])) == 2):
                    share = mask.sum() / n
                    if abs(share - test_size) > 0.10:
                        # Usually means undated rows crowded out the holdout.
                        logger.warning(
                            "model: time holdout is %.0f%% of the book, not the "
                            "requested %.0f%% (%d undated rows train)",
                            share * 100, test_size * 100, undated)
                    return mask, "time", cutoff.date().isoformat()
            reason = "no time cutoff leaves both outcomes on both sides"
        else:
            reason = "close_date has no parseable dates"
    logger.warning("model: %s, falling back to a random stratified holdout", reason)
    _tr, te = train_test_split(np.arange(n), test_size=test_size,
                               random_state=seed, stratify=y)
    mask = np.zeros(n, dtype=bool)
    mask[te] = True
    return mask, "random_stratified", None


def _calibration_rows(p: np.ndarray, y: np.ndarray, keys: np.ndarray,
                      key_name: str) -> list[dict]:
    """Mean predicted vs actual win rate, grouped by `keys` (a predicted-band
    label or a segment name). One shared implementation for both breakdowns:
    a global mean can look calibrated while every band or segment underneath
    it is biased in opposite directions (mle-reviewer F2 measured exactly
    this: predicted-0.30 actually wins 0.55, predicted-0.85 actually wins
    0.69, Enterprise predicted 0.489 vs actual 0.556)."""
    rows = []
    for k in pd.unique(keys):
        mask = keys == k
        if not mask.any():
            continue
        rows.append({
            key_name: str(k),
            "n": int(mask.sum()),
            "mean_pred": float(p[mask].mean()),
            "actual_win_rate": float(y[mask].mean()),
        })
    return sorted(rows, key=lambda r: r[key_name])


def _data_hash(df: pd.DataFrame) -> str:
    """Short, stable fingerprint of the training frame. Lets two runs claiming
    the same metrics prove they trained on the same data (mle-reviewer F6)."""
    try:
        h = pd.util.hash_pandas_object(df, index=True).to_numpy()
        return hashlib.sha256(h.tobytes()).hexdigest()[:16]
    except TypeError:
        # A column pandas cannot hash (e.g. an embedded list/dict) falls back
        # to a coarser but still deterministic fingerprint rather than raising.
        fallback = f"{df.shape}|{list(df.columns)}".encode()
        return hashlib.sha256(fallback).hexdigest()[:16]


def train(df: pd.DataFrame, test_size: float = 0.25, seed: int = 7) -> TrainedModel:
    """Train the win-probability model and evaluate on the latest closes."""
    X, y, cat, _num = prepare(df)
    holdout, split, test_from = _holdout_mask(df, y, test_size, seed)
    X_tr, X_te = X[~holdout], X[holdout]
    y_tr, y_te = y[~holdout], y[holdout]

    # +1 on discount_pct, 0 elsewhere, derived from the actual prepared column
    # order so the constraint never drifts out of sync with the feature list.
    monotone = [1 if col == "discount_pct" else 0 for col in X.columns]
    params = dict(_PARAMS, monotone_constraints=monotone,
                  monotone_constraints_method="advanced")
    clf = LGBMClassifier(**params)
    clf.fit(X_tr, y_tr, categorical_feature=cat)

    p_te = clf.predict_proba(X_te)[:, 1]
    metrics = {
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "auc": float(roc_auc_score(y_te, p_te)),
        "avg_precision": float(average_precision_score(y_te, p_te)),
        "brier": float(brier_score_loss(y_te, p_te)),
        # The only baseline that matters for a quoted probability: predicting
        # the training book's win rate for every deal. A model whose Brier is
        # worse than this one has probabilities that are not worth quoting,
        # however good its ranking is.
        "brier_constant": float(brier_score_loss(
            y_te, np.full(len(y_te), float(y_tr.mean())))),
        "base_rate": float(y_te.mean()),
        # calibration: mean predicted vs actual win rate on holdout
        "mean_pred": float(p_te.mean()),
        # "time" (latest closes held out) or "random_stratified" (fallback)
        "split": split,
        "test_from": test_from,
        "test_share": float(holdout.sum() / len(holdout)),
        # Rows the time split could not order, which therefore train unordered.
        "n_undated_train": int(
            pd.to_datetime(df["close_date"], errors="coerce").isna().sum()
        ) if split == "time" and "close_date" in df.columns else 0,
    }
    # Positive means the probabilities beat the constant; negative means they
    # lose to it. Reported, not just asserted, because it is the number that
    # decides whether a per-deal win probability may be shown at all.
    metrics["brier_skill"] = float(
        1.0 - metrics["brier"] / metrics["brier_constant"]
    ) if metrics["brier_constant"] else 0.0

    # Calibration by predicted-probability band and by segment (mle-reviewer
    # F2): the mean-only check above (mean_pred vs base_rate) can pass while
    # every band or segment underneath disagrees in opposite directions.
    band_labels = pd.cut(
        p_te, bins=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0001], right=False,
        labels=["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"],
    ).astype(str).to_numpy()
    y_te_arr = y_te.to_numpy()
    metrics["calibration_by_band"] = _calibration_rows(
        p_te, y_te_arr, band_labels, "band")
    if "segment" in df.columns:
        seg_labels = df.loc[X_te.index, "segment"].astype(str).to_numpy()
        metrics["calibration_by_segment"] = _calibration_rows(
            p_te, y_te_arr, seg_labels, "segment")
    else:
        metrics["calibration_by_segment"] = []

    # Stamped so two runs claiming the same numbers can prove it, and so a
    # regression can be traced to a capacity or data change instead of
    # guessed at (mle-reviewer F6).
    metrics["seed"] = seed
    metrics["params"] = {k: v for k, v in params.items()}
    metrics["features"] = list(X.columns)
    metrics["data_hash"] = _data_hash(df)

    return TrainedModel(model=clf, features=list(X.columns),
                        categorical=cat, metrics=metrics, X_all=X,
                        holdout=holdout)


def predict_win_prob(tm: TrainedModel, X: pd.DataFrame) -> np.ndarray:
    return tm.model.predict_proba(X[tm.features])[:, 1]


def feature_importance(tm: TrainedModel) -> pd.DataFrame:
    return (pd.DataFrame({"feature": tm.features,
                          "gain": tm.model.booster_.feature_importance("gain")})
            .sort_values("gain", ascending=False)
            .reset_index(drop=True))


def explain(tm: TrainedModel, X_row: pd.DataFrame) -> pd.DataFrame:
    """Per-feature SHAP contributions for a single deal (LightGBM native).

    `pred_contrib=True` returns one column per feature plus a trailing base
    value; contributions are in log-odds and sum to the raw model score.
    """
    contrib = tm.model.booster_.predict(X_row[tm.features], pred_contrib=True)[0]
    rows = [{"feature": f, "contribution": float(c)}
            for f, c in zip(tm.features, contrib[:-1])]
    rows.append({"feature": "<base>", "contribution": float(contrib[-1])})
    out = pd.DataFrame(rows)
    out["abs"] = out["contribution"].abs()
    return out.sort_values("abs", ascending=False).drop(columns="abs").reset_index(drop=True)


def _band_guardrail_recommendation(tm: TrainedModel, X_row: pd.DataFrame,
                                   list_acv: float, current: float,
                                   cohort_discounts: np.ndarray) -> dict:
    """Fallback when a cohort has too little support to trust an EV-curve
    optimum (mle-reviewer F3): fewer than ~50 comparable deals means the grid
    sweep is extrapolating past what this segment has ever actually done, and
    the monotone constraint pulls the optimum toward exactly that empty
    region. Mirrors the live-CRM guardrail (`crm.guidance_for_open_deal`):
    never recommend adding discount, and cap at the cohort's own observed
    median when the deal sits above it. Still reports the model's P(win) at
    both points for context, but does not claim an EV-optimal answer.
    """
    reference = float(np.median(cohort_discounts)) if len(cohort_discounts) else current
    recommended = min(current, reference)

    row_cur, row_rec = X_row.copy(), X_row.copy()
    row_cur["discount_pct"], row_rec["discount_pct"] = current, recommended
    p_cur = float(tm.model.predict_proba(row_cur[tm.features])[:, 1][0])
    p_rec = float(tm.model.predict_proba(row_rec[tm.features])[:, 1][0])
    ev_cur = p_cur * list_acv * (1.0 - current)
    ev_rec = p_rec * list_acv * (1.0 - recommended)
    curve = (
        pd.DataFrame({"discount": [current, recommended],
                     "win_prob": [p_cur, p_rec],
                     "expected_acv": [ev_cur, ev_rec]})
        .drop_duplicates(subset="discount")
        .sort_values("discount")
        .reset_index(drop=True)
    )
    return {
        "method": "band_guardrail",
        "recommended_discount": recommended,
        "expected_acv_at_rec": ev_rec,
        "win_prob_at_rec": p_rec,
        "current_discount": current,
        "expected_acv_at_current": ev_cur,
        "uplift": ev_rec - ev_cur,
        "curve": curve,
        "cohort_deals": int(len(cohort_discounts)),
    }


def recommend_discount(tm: TrainedModel, X_row: pd.DataFrame, list_acv: float,
                       grid: np.ndarray | None = None, *,
                       cohort_discounts: np.ndarray | None = None,
                       min_cohort_deals: int = 50) -> dict:
    """Sweep discount and return the level that maximizes expected booked ACV.

    `X_row` is a single-row feature frame (categories consistent with training);
    we vary only `discount_pct`. Expected ACV = P(win) x list x (1 - discount).

    `cohort_discounts` (mle-reviewer F3), when given, is the array of
    discounts actually observed in this deal's cohort (typically its
    segment). Two guardrails follow from it:
      * Fewer than `min_cohort_deals` deals: the curve optimum would be
        extrapolating past this cohort's real support, so this returns
        `_band_guardrail_recommendation` instead (method "band_guardrail")
        and never runs the sweep at all.
      * Otherwise, and only when `grid` was not supplied explicitly, the
        default 0-40% sweep is clipped to roughly the cohort's 5th-95th
        percentile, so the recommendation stays inside discounts this
        cohort has actually given rather than the full unconditional range.
    Callers that omit `cohort_discounts` get the prior unclipped behavior
    unchanged.
    """
    current = float(X_row["discount_pct"].iloc[0])

    if cohort_discounts is not None and len(cohort_discounts) < min_cohort_deals:
        return _band_guardrail_recommendation(
            tm, X_row, list_acv, current, cohort_discounts)

    if grid is None:
        if cohort_discounts is not None and len(cohort_discounts) >= min_cohort_deals:
            lo = float(np.clip(np.percentile(cohort_discounts, 5), 0.0, 0.39))
            hi = float(np.clip(np.percentile(cohort_discounts, 95), lo + 0.01, 0.40))
            grid = np.round(np.arange(lo, hi + 0.0001, 0.01), 4)
        else:
            grid = np.round(np.arange(0.0, 0.4001, 0.01), 4)
    sweep = pd.concat([X_row] * len(grid), ignore_index=True)
    sweep["discount_pct"] = grid
    p = tm.model.predict_proba(sweep[tm.features])[:, 1]
    expected_acv = p * list_acv * (1.0 - grid)
    best = int(np.argmax(expected_acv))

    cur_i = int(np.argmin(np.abs(grid - current)))
    return {
        "method": "modeled_ev_curve",
        "recommended_discount": float(grid[best]),
        "expected_acv_at_rec": float(expected_acv[best]),
        "win_prob_at_rec": float(p[best]),
        "current_discount": current,
        "expected_acv_at_current": float(expected_acv[cur_i]),
        "uplift": float(expected_acv[best] - expected_acv[cur_i]),
        "curve": pd.DataFrame({"discount": grid, "win_prob": p,
                               "expected_acv": expected_acv}),
        "cohort_deals": int(len(cohort_discounts)) if cohort_discounts is not None else None,
    }


def comparable_deals(df: pd.DataFrame, idx, k: int = 5) -> pd.DataFrame:
    """The k closed deals most similar to deal `idx` — the evidence behind a
    recommendation (explainability > accuracy: a transparent rule, not a
    black-box neighbour search).

    Similarity is deliberately simple and defensible in a pricing committee:
    prefer the same segment, then rank by closeness in deal size (log list ACV)
    and discount given. Returns won AND lost deals so the user sees how similar
    deals fared at similar discounts, not a cherry-picked set.
    """
    if idx not in df.index:
        return df.iloc[0:0]
    this = df.loc[idx]
    pool = df[df.index != idx]
    same_seg = pool[pool["segment"] == this["segment"]]
    base = same_seg if len(same_seg) >= k else pool
    this_log = float(np.log(max(float(this["list_acv"]), 1.0)))
    d_size = (np.log(base["list_acv"].clip(lower=1.0)) - this_log).abs()
    d_disc = (base["discount_pct"] - float(this["discount_pct"])).abs()
    # discount lives in [0,1]; log-size distance is O(1). Weight discount up so
    # "similar discount" counts as much as "similar size".
    score = d_size + 3.0 * d_disc
    chosen = base.assign(_score=score).sort_values("_score").head(k)
    cols = [c for c in ["opportunity_id", "resolved_account_name", "segment",
                        "industry", "list_acv", "discount_pct", "is_won"]
            if c in chosen.columns]
    return chosen[cols].reset_index(drop=True)


def band_context(df: pd.DataFrame, idx, recommended_discount: float) -> dict:
    """The win-rate-by-discount-band curve segment this recommendation came from.

    Computes the empirical win rate per discount band among deals in the same
    segment (the cohort the model reasons over), and names the band the current
    and recommended discounts fall in. This is the observed saturation that the
    recommendation rides on, shown so a reviewer can see it for themselves.
    """
    seg = str(df.loc[idx, "segment"])
    cohort = df[df["segment"] == seg]
    bands = metrics.win_rate_by_band(cohort)
    return {
        "segment": seg,
        "cohort_deals": int(len(cohort)),
        "bands": [
            {"band": str(r.discount_band), "deals": int(r.deals),
             "win_rate": float(r.win_rate)}
            for r in bands.itertuples()
        ],
        "current_band": band_for(float(df.loc[idx, "discount_pct"])),
        "recommended_band": band_for(float(recommended_discount)),
    }


def leakage_vs_model(tm: TrainedModel, df: pd.DataFrame,
                     grid: np.ndarray | None = None) -> dict:
    """Model-conditioned leakage: each won deal's EV-optimal ("justified")
    discount from its own predicted win curve, and the $ given away above it.

    Unifies Phase 1 (leakage) and Phase 2 (win model): instead of a single
    global reference discount, every deal gets a justified discount conditioned
    on its attributes (the cross-model review's top recommendation). Still a
    decision-support signal, not a refund figure.
    """
    if grid is None:
        grid = np.round(np.arange(0.0, 0.4001, 0.01), 4)
    won = df[df["is_won"]]
    if won.empty:
        return {"deals": 0, "mean_justified_discount": 0.0, "mean_actual_discount": 0.0,
                "model_excess_won": 0.0, "deals_over_justified": 0,
                "model_excess_pct_of_booked": 0.0}

    g = len(grid)
    X = tm.X_all.loc[won.index, tm.features]
    rep = X.loc[X.index.repeat(g)].reset_index(drop=True)
    rep["discount_pct"] = np.tile(grid, len(X))
    p = tm.model.predict_proba(rep[tm.features])[:, 1].reshape(len(X), g)

    list_acv = won["list_acv"].to_numpy()
    ev = p * list_acv[:, None] * (1.0 - grid[None, :])
    justified = grid[ev.argmax(axis=1)]
    actual = won["discount_pct"].to_numpy()
    excess = np.clip(actual - justified, 0.0, None) * list_acv
    booked = float(won["booked_acv"].sum())
    return {
        "deals": int(len(won)),
        "mean_justified_discount": float(justified.mean()),
        "mean_actual_discount": float(actual.mean()),
        "model_excess_won": float(excess.sum()),
        "deals_over_justified": int((excess > 0).sum()),
        "model_excess_pct_of_booked": float(excess.sum() / booked) if booked else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Train the win-probability model.")
    ap.add_argument("path", type=Path, help="path to a deals CSV")
    args = ap.parse_args()

    df = ingest(args.path)
    tm = train(df)
    m = tm.metrics
    print("=" * 60)
    print("  WIN-PROBABILITY MODEL")
    print("=" * 60)
    print(f"train/test      : {m['n_train']:,} / {m['n_test']:,}")
    print(f"holdout         : {m['split']}"
          + (f", closes from {m['test_from']}" if m["test_from"] else ""))
    print(f"ROC AUC         : {m['auc']:.3f}")
    print(f"avg precision   : {m['avg_precision']:.3f}  (base rate {m['base_rate']:.3f})")
    print(f"Brier score     : {m['brier']:.4f}  (lower is better)")
    print(f"calibration     : mean pred {m['mean_pred']:.3f} vs actual {m['base_rate']:.3f}")

    print("\n-- Feature importance (gain) " + "-" * 31)
    print(feature_importance(tm).to_string(index=False))

    # Sample guidance on the largest won deals.
    won = df[df["is_won"]].sort_values("list_acv", ascending=False).head(3)
    print("\n-- Discount guidance (sample large deals) " + "-" * 18)
    for idx in won.index:
        X_row = tm.X_all.loc[[idx]]
        rec = recommend_discount(tm, X_row, float(df.loc[idx, "list_acv"]))
        print(f"{df.loc[idx, 'opportunity_id']}  list ${df.loc[idx,'list_acv']:,.0f}  "
              f"| gave {rec['current_discount']:.0%} -> recommend "
              f"{rec['recommended_discount']:.0%}  "
              f"(P(win) {rec['win_prob_at_rec']:.0%}, "
              f"E[ACV] uplift ${rec['uplift']:,.0f})")
    print("\n(Guidance maximizes expected ACV on a saturating win curve; it is")
    print(" decision support for humans in the loop, not an autopilot.)")

    ml = leakage_vs_model(tm, df)
    print("\n-- Model-conditioned leakage (won deals) " + "-" * 19)
    print(f"Mean justified discount {ml['mean_justified_discount']:.1%} vs actual "
          f"{ml['mean_actual_discount']:.1%}. "
          f"${ml['model_excess_won']:,.0f} given above each deal's justified "
          f"discount across {ml['deals_over_justified']:,} deals "
          f"({ml['model_excess_pct_of_booked']:.1%} of booked ACV).")


if __name__ == "__main__":
    main()
