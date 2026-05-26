"""Ingestion + identity resolution.

Loads a deals CSV (synthetic or a prospect's export), validates it against the
canonical schema, resolves account identity from messy names, and derives the
fields the metrics layer needs.

Identity resolution is deliberately simple and explainable (explainability >
accuracy in enterprise): normalize the account name to a core, then collapse
rows sharing a core or an account_id into one resolved account. This is a
heuristic, not entity-resolution-as-a-service — it is documented as such and is
the right amount of machinery for a CSV diagnostic.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from pricing.schema import (
    DEFAULT_POLICY_THRESHOLD,
    REQUIRED_FIELDS,
    Outcome,
    band_for,
)

_NUMERIC = ["list_acv", "booked_acv", "platform_fee_acv", "usage_acv", "quantity"]
_LEGAL_TOKENS = {"inc", "llc", "corp", "co", "ltd", "incorporated", "llp", "plc"}
_PUNCT = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")


class SchemaError(ValueError):
    """Raised when an input CSV is missing required columns."""


def normalize_account_name(name: str) -> str:
    """Reduce a messy CRM account name to a comparable core.

    "  ACME, Inc. " -> "acme"   |   "Lumen Data LLC" -> "lumen data"
    """
    if not isinstance(name, str):
        return ""
    s = _PUNCT.sub(" ", name.lower())
    s = _WS.sub(" ", s).strip()
    tokens = [t for t in s.split(" ") if t and t not in _LEGAL_TOKENS]
    return " ".join(tokens)


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a deals CSV as strings (we coerce types ourselves)."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def validate(df: pd.DataFrame) -> None:
    """Ensure required columns are present; raise SchemaError if not."""
    missing = [c for c in REQUIRED_FIELDS if c not in df.columns]
    if missing:
        raise SchemaError(
            f"Input is missing {len(missing)} required column(s): {missing}. "
            f"See pricing/schema.py and gtm/data-request.md."
        )


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in _NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "term_months" in df.columns:
        df["term_months"] = pd.to_numeric(df["term_months"], errors="coerce")
    for col in ("created_date", "close_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "competitor_present" in df.columns:
        df["competitor_present"] = (
            df["competitor_present"].astype(str).str.strip().str.lower()
            .isin(["true", "1", "yes", "y"])
        )
    return df


def resolve_identity(df: pd.DataFrame) -> pd.DataFrame:
    """Add `resolved_account_id` and `resolved_account_name`.

    Links rows that share a normalized name OR an explicit account_id, then
    backfills a single id and a clean display name per resolved account.
    """
    df = df.copy()
    df["_norm_name"] = df["account_name"].map(normalize_account_name)
    acct_id = df.get("account_id", pd.Series([""] * len(df))).fillna("").astype(str)

    # Most common explicit id seen for each normalized name (if any).
    has_id = acct_id.str.strip() != ""
    norm_to_id: dict[str, str] = {}
    if has_id.any():
        pairs = pd.DataFrame({"norm": df["_norm_name"][has_id], "id": acct_id[has_id]})
        norm_to_id = (
            pairs.groupby("norm")["id"]
            .agg(lambda s: s.value_counts().idxmax())
            .to_dict()
        )

    def _resolve(row_norm: str, row_id: str) -> str:
        if row_id.strip():
            return row_id.strip()
        if row_norm in norm_to_id:
            return norm_to_id[row_norm]
        return f"NAME::{row_norm}" if row_norm else "UNKNOWN"

    df["resolved_account_id"] = [
        _resolve(n, i) for n, i in zip(df["_norm_name"], acct_id)
    ]

    # Clean display name = modal raw name (trimmed) within a resolved account.
    display = (
        df.assign(_clean=df["account_name"].astype(str).str.strip())
        .groupby("resolved_account_id")["_clean"]
        .agg(lambda s: s.value_counts().idxmax())
    )
    df["resolved_account_name"] = df["resolved_account_id"].map(display)
    return df.drop(columns=["_norm_name"])


def enrich(df: pd.DataFrame, policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> pd.DataFrame:
    """Add the derived fields the metrics layer consumes."""
    df = df.copy()
    list_acv = df["list_acv"].replace(0, np.nan)
    df["price_realization"] = (df["booked_acv"] / list_acv).clip(upper=1.5)
    # round to 6dp so band assignment is deterministic at boundaries
    # (e.g. 1 - 0.8 == 0.19999999999999996 in float would mis-band a clean 20%)
    df["discount_pct"] = (1.0 - df["price_realization"]).clip(lower=0.0, upper=1.0).round(6)
    df["discount_amount"] = (df["list_acv"] - df["booked_acv"]).clip(lower=0.0)
    df["is_won"] = df["outcome"].astype(str) == Outcome.WON.value
    df["discount_band"] = df["discount_pct"].fillna(0.0).map(band_for)

    if "close_date" in df.columns:
        q = df["close_date"].dt.quarter
        df["quarter"] = (
            df["close_date"].dt.year.astype("Int64").astype(str) + "-Q" + q.astype("Int64").astype(str)
        )
        qe = df["close_date"] + pd.offsets.QuarterEnd(0)
        df["days_to_quarter_end"] = (qe - df["close_date"]).dt.days
        df["is_quarter_end"] = df["days_to_quarter_end"] <= 21
    if "created_date" in df.columns and "close_date" in df.columns:
        df["cycle_days"] = (df["close_date"] - df["created_date"]).dt.days

    approver = df.get("approved_by", pd.Series([""] * len(df))).fillna("").astype(str)
    df["off_policy"] = df["discount_pct"] > policy_threshold
    df["off_policy_unapproved"] = df["off_policy"] & (approver.str.strip() == "")
    return df


def ingest(path: str | Path,
           policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> pd.DataFrame:
    """Full pipeline: load → validate → coerce → resolve identity → enrich."""
    df = load_csv(path)
    validate(df)
    df = _coerce_types(df)
    df = resolve_identity(df)
    df = enrich(df, policy_threshold=policy_threshold)
    return df
