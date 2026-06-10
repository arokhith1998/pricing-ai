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

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd

from pricing import mapping
from pricing.schema import (
    DEFAULT_POLICY_THRESHOLD,
    REQUIRED_FIELDS,
    Outcome,
    band_for,
)

_NUMERIC = ["list_acv", "booked_acv", "platform_fee_acv", "usage_acv", "quantity",
            "committed_acv", "overage_rate", "ramp_year_1_acv", "ramp_year_2_acv",
            "renewal_uplift", "cogs_acv"]
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


def load_any(path: str | Path) -> pd.DataFrame:
    """Tolerant raw read of a deals export, returning all-string columns.

    Handles the shapes real exports arrive in (type coercion happens later):
      * .xlsx with a title/banner row above the real header and a TOTAL row
        at the bottom (Finance's Excel),
      * semicolon-delimited CSV (EU ERP/CRM exports),
      * a UTF-8 BOM (hand-maintained CRM exports).
    """
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        raw = pd.read_excel(path, header=None, dtype=str)
        # Header row = first row with >3 non-empty cells; skips a title/blank
        # banner sitting above the real header.
        hdr = next((i for i, r in raw.iterrows() if r.notna().sum() > 3), 0)
        df = raw.iloc[hdr + 1:].copy()
        df.columns = [str(c) for c in raw.iloc[hdr]]
        df = df.dropna(how="all")
        # Drop a trailing summary row whose first cell is "TOTAL".
        first_cell = df.iloc[:, 0].astype(str).str.strip().str.upper()
        df = df[first_cell != "TOTAL"]
        return df.fillna("").astype(str).reset_index(drop=True)

    text = path.read_bytes().decode("utf-8-sig")  # utf-8-sig strips a BOM
    lines = text.splitlines()
    first = lines[0] if lines else ""
    sep = ";" if first.count(";") > first.count(",") else ","
    return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, sep=sep)


def load_csv(path: str | Path) -> pd.DataFrame:
    """Back-compat alias. Now tolerant of CSV and XLSX exports (see load_any)."""
    return load_any(path)


def apply_header_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Rename incoming headers to canonical schema names via the deterministic
    mapper (synonyms + fuzzy only — no embeddings/LLM, so ingest stays offline
    and reproducible). Unmapped columns keep their original names.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    result = mapping.map_headers(list(df.columns), llm_fallback=False,
                                 use_embeddings=False)
    rename = {header: field for field, header in result["mapping"].items() if header}
    return df.rename(columns=rename)


def validate(df: pd.DataFrame) -> None:
    """Ensure required columns are present; raise SchemaError if not."""
    missing = [c for c in REQUIRED_FIELDS if c not in df.columns]
    if missing:
        raise SchemaError(
            f"Input is missing {len(missing)} required column(s): {missing}. "
            f"See pricing/schema.py and gtm/data-request.md."
        )


# --- Value normalization (real-world export formats) ------------------------
# The same deal exported by Salesforce, an EU ERP, or Finance's Excel carries
# the same numbers dressed differently. Normalize them here so a $-weighted
# total is identical whatever the source. Silent money corruption (a comma
# misread) is the worst failure class, so the money parser is deliberate.

OUTCOME_ALIASES = {
    "closed won": "closed_won", "closedwon": "closed_won", "won": "closed_won",
    "w": "closed_won", "closed-won": "closed_won", "closed_won": "closed_won",
    "closed lost": "closed_lost", "closedlost": "closed_lost",
    "lost": "closed_lost", "l": "closed_lost", "closed-lost": "closed_lost",
    "closed_lost": "closed_lost",
}

_BOOL_TRUE = {"true", "1", "yes", "y", "ja", "t", "wahr"}
_MONEY_STRIP = re.compile(r"[€$£¥\s]")
_DATE_RE = re.compile(r"^\s*(\d{1,2})[./-](\d{1,2})[./-]\d{2,4}")
_NUMERIC_NONMONEY = ["quantity", "term_months"]


def _money_to_float(v: object) -> float:
    """Parse one money string. Tolerant of currency symbols, US thousands
    ("96,000.00"), bare US thousands ("96,000"), EU decimals ("1.234,56"), and
    accounting negatives ("(1,234)"). Returns NaN on anything unparseable."""
    s = _MONEY_STRIP.sub("", str(v)).strip()
    if s.lower() in ("", "nan", "none", "null", "na", "-"):
        return np.nan
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        # The rightmost separator is the decimal point.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")   # EU 1.234,56
        else:
            s = s.replace(",", "")                      # US 1,234.56
    elif has_comma:
        tail = s.split(",")[-1]
        if s.count(",") == 1 and len(tail) in (1, 2):
            s = s.replace(",", ".")                      # decimal comma 12,5
        else:
            s = s.replace(",", "")                       # thousands 96,000
    elif has_dot and s.count(".") > 1:
        s = s.replace(".", "")                           # EU thousands 1.234.567
    try:
        f = float(s)
    except ValueError:
        return np.nan
    return -f if neg else f


def parse_money(s: pd.Series) -> pd.Series:
    """Vectorized tolerant money parse (see _money_to_float)."""
    return s.map(_money_to_float).astype("float64")


def _detect_dayfirst(s: pd.Series) -> bool:
    """Infer day/month order from any value whose first or second component
    exceeds 12. Defaults to month-first (US) when unambiguous or ISO."""
    first_gt12 = second_gt12 = False
    for v in s.astype(str):
        m = _DATE_RE.match(v)
        if not m:
            continue
        if int(m.group(1)) > 12:
            first_gt12 = True
        if int(m.group(2)) > 12:
            second_gt12 = True
    return bool(first_gt12 and not second_gt12)


def parse_dates(s: pd.Series) -> pd.Series:
    """Parse a date column with explicit day/month-order detection per column,
    rather than trusting pandas defaults (which silently swap day and month
    below the 13th)."""
    return pd.to_datetime(s, errors="coerce", dayfirst=_detect_dayfirst(s),
                          format="mixed")


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in _NUMERIC + _NUMERIC_NONMONEY:
        if col in df.columns:
            df[col] = parse_money(df[col])
    for col in ("created_date", "close_date"):
        if col in df.columns:
            df[col] = parse_dates(df[col])
    if "outcome" in df.columns:
        low = df["outcome"].astype(str).str.strip().str.lower()
        df["outcome"] = low.map(OUTCOME_ALIASES).fillna(low)
    for boolcol in ("competitor_present", "is_renewal"):
        if boolcol in df.columns:
            df[boolcol] = (
                df[boolcol].astype(str).str.strip().str.lower().isin(_BOOL_TRUE)
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
    """Full pipeline: load → map headers → validate → coerce → resolve → enrich.

    The header-mapping step (deterministic synonyms + fuzzy) is what lets a raw
    Salesforce / HubSpot / EU / warehouse / Excel export ingest without a manual
    rename pass — see data/synthetic/format-fixtures/.
    """
    df = load_any(path)
    df = apply_header_mapping(df)
    # Drop blank and summary rows that carry no opportunity id (Excel TOTAL
    # rows, injected blank separators) so they never reach the metrics.
    if "opportunity_id" in df.columns:
        oid = df["opportunity_id"].astype(str).str.strip()
        df = df[oid != ""].reset_index(drop=True)
    validate(df)
    df = _coerce_types(df)
    df = resolve_identity(df)
    df = enrich(df, policy_threshold=policy_threshold)
    return df
