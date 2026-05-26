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
  * Explainability via LightGBM's NATIVE SHAP contributions
    (`predict(pred_contrib=True)`) — no extra `shap` dependency, exact for the
    tree, and the foundation for per-deal "why" in enterprise (explainability >
    accuracy).
  * Discount guidance maximizes expected ACV = P(win | discount) x list x
    (1 - discount). Because the win curve saturates, the optimum sits where the
    marginal win gain stops covering the marginal price given away.

CLI:  python -m pricing.model data/synthetic/deals.csv
"""

from __future__ import annotations

import argparse
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

from pricing.ingest import ingest

# Features available at quote time. Categorical first, then numeric.
CATEGORICAL = ["segment", "region", "industry", "product_tier", "value_metric"]
NUMERIC = ["list_acv", "discount_pct", "term_months", "quantity",
           "is_quarter_end", "competitor_present"]
TARGET = "is_won"

# Regularized: shallow leaves + large leaf minimum + L2 keep the model off
# high-cardinality numeric noise (list_acv, quantity) and improve holdout AUC.
_PARAMS = dict(
    n_estimators=250, learning_rate=0.05, num_leaves=15,
    min_child_samples=50, subsample=0.8, colsample_bytree=0.7,
    reg_lambda=1.0, random_state=7, n_jobs=-1, verbosity=-1,
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


def train(df: pd.DataFrame, test_size: float = 0.25, seed: int = 7) -> TrainedModel:
    """Train the win-probability model and evaluate on a stratified holdout."""
    X, y, cat, _num = prepare(df)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y)

    clf = LGBMClassifier(**_PARAMS)
    clf.fit(X_tr, y_tr, categorical_feature=cat)

    p_te = clf.predict_proba(X_te)[:, 1]
    metrics = {
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "auc": float(roc_auc_score(y_te, p_te)),
        "avg_precision": float(average_precision_score(y_te, p_te)),
        "brier": float(brier_score_loss(y_te, p_te)),
        "base_rate": float(y_te.mean()),
        # calibration: mean predicted vs actual win rate on holdout
        "mean_pred": float(p_te.mean()),
    }
    return TrainedModel(model=clf, features=list(X.columns),
                        categorical=cat, metrics=metrics, X_all=X)


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


def recommend_discount(tm: TrainedModel, X_row: pd.DataFrame, list_acv: float,
                       grid: np.ndarray | None = None) -> dict:
    """Sweep discount and return the level that maximizes expected booked ACV.

    `X_row` is a single-row feature frame (categories consistent with training);
    we vary only `discount_pct`. Expected ACV = P(win) x list x (1 - discount).
    """
    if grid is None:
        grid = np.round(np.arange(0.0, 0.4001, 0.01), 4)
    sweep = pd.concat([X_row] * len(grid), ignore_index=True)
    sweep["discount_pct"] = grid
    p = tm.model.predict_proba(sweep[tm.features])[:, 1]
    expected_acv = p * list_acv * (1.0 - grid)
    best = int(np.argmax(expected_acv))

    current = float(X_row["discount_pct"].iloc[0])
    cur_i = int(np.argmin(np.abs(grid - current)))
    return {
        "recommended_discount": float(grid[best]),
        "expected_acv_at_rec": float(expected_acv[best]),
        "win_prob_at_rec": float(p[best]),
        "current_discount": current,
        "expected_acv_at_current": float(expected_acv[cur_i]),
        "uplift": float(expected_acv[best] - expected_acv[cur_i]),
        "curve": pd.DataFrame({"discount": grid, "win_prob": p,
                               "expected_acv": expected_acv}),
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


if __name__ == "__main__":
    main()
