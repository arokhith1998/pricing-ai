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
from dataclasses import dataclass, field
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

# A diagnostic needs a minimum of real closed deals to mean anything; below this
# we fail loudly rather than render a NaN dashboard.
MIN_CLOSED_DEALS = 30
_CLOSED = {Outcome.WON.value, Outcome.LOST.value}
# CSV decode cascade for the common real-world encodings. latin-1 maps every
# byte, so it never raises — it is the guaranteed last resort.
_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


@dataclass
class LoadReport:
    """What we read from a file, and what we set aside and why.

    This is the 'here is what we read from your file' artifact the diagnostic
    should surface first — the explainability posture applied to ingestion.
    Every silent-corruption trap (open deals retained, duplicates double-counted,
    a mis-decoded name) becomes a visible line here instead of a wrong number.
    """

    source: str = ""
    encoding: str = ""                # which decode succeeded (CSV only)
    sheet: str = ""                   # chosen worksheet (XLSX only)
    rows_read: int = 0                # data rows after load + blank drop
    rows_kept: int = 0                # rows that reached the metrics
    blank_rows_dropped: int = 0
    exact_duplicates_dropped: int = 0
    conflicting_ids: list[str] = field(default_factory=list)
    excluded_open: dict[str, int] = field(default_factory=dict)  # stage -> count
    above_list_deals: int = 0         # booked > list: a pricing-power signal
    currencies: list[str] = field(default_factory=list)  # symbols seen in money
    blank_booked: int = 0             # rows with no parseable booked value
    # Header-mapping provenance: which incoming column each canonical field came
    # from, and which incoming columns we left unmapped. Makes a mis-map visible.
    field_sources: dict[str, str] = field(default_factory=dict)  # field -> "header (layer)"
    unmapped_columns: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """A short, human-readable 'what we read' block for the dashboard."""
        out = [f"Read {self.rows_kept} closed deals from {self.source}."]
        if self.sheet:
            out.append(f"  worksheet: {self.sheet}")
        if self.encoding and self.encoding != "utf-8-sig":
            out.append(f"  decoded as {self.encoding}")
        if self.excluded_open:
            total = sum(self.excluded_open.values())
            detail = ", ".join(f"{k}: {v}" for k, v in self.excluded_open.items())
            out.append(f"  excluded {total} open / non-closed rows ({detail})")
        if self.exact_duplicates_dropped:
            out.append(f"  dropped {self.exact_duplicates_dropped} exact duplicate rows")
        if self.conflicting_ids:
            out.append(
                f"  WARNING: {len(self.conflicting_ids)} opportunity_id(s) with "
                "conflicting values, kept first occurrence"
            )
        if self.blank_rows_dropped:
            out.append(f"  dropped {self.blank_rows_dropped} blank / summary rows")
        if self.above_list_deals:
            out.append(
                f"  {self.above_list_deals} deal(s) closed ABOVE list "
                "(booked > list) — a pricing-power signal, not leakage"
            )
        if len(self.currencies) > 1:
            out.append(
                f"  WARNING: mixed currency symbols in money columns "
                f"({', '.join(self.currencies)}) — totals may combine currencies; "
                "verify the source uses one currency"
            )
        if self.blank_booked:
            out.append(
                f"  {self.blank_booked} deal(s) with a blank / unparseable booked "
                "value (excluded from dollar totals)"
            )
        if self.unmapped_columns:
            out.append(
                f"  ignored {len(self.unmapped_columns)} unrecognized column(s): "
                + ", ".join(self.unmapped_columns)
            )
        out.extend(f"  {n}" for n in self.notes)
        return "\n".join(out)

_NUMERIC = ["list_acv", "booked_acv", "platform_fee_acv", "usage_acv", "quantity",
            "committed_acv", "overage_rate", "ramp_year_1_acv", "ramp_year_2_acv",
            "renewal_uplift", "cogs_acv"]
_LEGAL_TOKENS = {"inc", "llc", "corp", "co", "ltd", "incorporated", "llp", "plc"}
_PUNCT = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")


# Headers eligible for the value-validated deal-type rescue (normalized form).
_TYPE_HEADERS = {"type", "opportunity type", "opp type", "deal type",
                 "record type"}


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


def _header_row(raw: pd.DataFrame) -> int | None:
    """Index of the first row with >3 non-empty cells (the real header, skipping
    a title/banner above it). None if no row qualifies."""
    return next((i for i, r in raw.iterrows() if r.notna().sum() > 3), None)


def _frame_from_header(raw: pd.DataFrame, hdr: int) -> pd.DataFrame:
    """Slice a header-less sheet/frame into a typed-as-string DataFrame from the
    detected header row, dropping all-blank rows and a trailing TOTAL row."""
    df = raw.iloc[hdr + 1:].copy()
    df.columns = [str(c) for c in raw.iloc[hdr]]
    df = df.dropna(how="all")
    first_cell = df.iloc[:, 0].astype(str).str.strip().str.upper()
    df = df[first_cell != "TOTAL"]
    return df.fillna("").astype(str).reset_index(drop=True)


def _load_excel(path: Path, report: LoadReport | None) -> pd.DataFrame:
    """Pick the worksheet whose header resolves the most required fields, so a
    summary/pivot sheet sitting before the real data does not win."""
    xls = pd.ExcelFile(path)
    best = None  # (score, sheet, raw, hdr)
    for sheet in xls.sheet_names:
        raw = pd.read_excel(xls, sheet_name=sheet, header=None, dtype=str)
        if raw.empty:
            continue
        hdr = _header_row(raw)
        if hdr is None:
            continue
        cols = [str(c).strip() for c in raw.iloc[hdr] if pd.notna(c)]
        mapped = mapping.map_headers(cols, llm_fallback=False,
                                     use_embeddings=False)["mapping"]
        score = sum(1 for f in REQUIRED_FIELDS if mapped.get(f))
        if best is None or score > best[0]:
            best = (score, sheet, raw, hdr)
    if best is None:  # no sheet had a usable header; fall back to the first
        raw = pd.read_excel(xls, sheet_name=0, header=None, dtype=str)
        best = (0, xls.sheet_names[0], raw, _header_row(raw) or 0)
    _score, sheet, raw, hdr = best
    if report is not None:
        report.sheet = sheet
        if len(xls.sheet_names) > 1:
            report.notes.append(
                f"chose worksheet '{sheet}' of {len(xls.sheet_names)} by required-field coverage"
            )
    return _frame_from_header(raw, hdr)


def load_any(path: str | Path, report: LoadReport | None = None) -> pd.DataFrame:
    """Tolerant raw read of a deals export, returning all-string columns.

    Handles the shapes real exports arrive in (type coercion happens later):
      * .xlsx with a banner row above the header, a TOTAL row, and possibly a
        summary sheet before the data sheet,
      * semicolon-delimited CSV (EU ERP exports),
      * UTF-8 BOM, and Windows-1252 / latin-1 encodings (decode cascade).
    """
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        return _load_excel(path, report)

    raw = path.read_bytes()
    text = None
    for enc in _ENCODINGS:
        try:
            text = raw.decode(enc)
            if report is not None:
                report.encoding = enc
            break
        except UnicodeDecodeError:
            continue
    if text is None:  # latin-1 cannot reach here, but stay defensive
        text = raw.decode("latin-1", errors="replace")
        if report is not None:
            report.encoding = "latin-1 (lossy)"

    lines = text.splitlines()
    first = lines[0] if lines else ""
    sep = ";" if first.count(";") > first.count(",") else ","
    return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, sep=sep)


def load_csv(path: str | Path) -> pd.DataFrame:
    """Back-compat alias. Now tolerant of CSV and XLSX exports (see load_any)."""
    return load_any(path)


def apply_header_mapping(df: pd.DataFrame,
                         report: "LoadReport | None" = None) -> pd.DataFrame:
    """Rename incoming headers to canonical schema names via the deterministic
    mapper (synonyms + fuzzy only — no embeddings/LLM, so ingest stays offline
    and reproducible). Unmapped columns keep their original names.

    Optional fields are claimed only on HIGH confidence (a synonym or near-exact
    fuzzy match). A merely-plausible fuzzy guess must never silently relabel an
    extra column into an optional field (the "Forecast Category -> product_family"
    credibility bug). Required fields take the best available match. Provenance
    (which column each field came from) and the ignored columns go to the
    LoadReport so a reviewer can audit every mapping.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)
    result = mapping.map_headers(cols, llm_fallback=False, use_embeddings=False)
    mapped, confidence, used = result["mapping"], result["confidence"], result["used"]
    required = set(REQUIRED_FIELDS)

    rename: dict[str, str] = {}
    sources: dict[str, str] = {}
    for fieldname, header in mapped.items():
        if not header:
            continue
        conf = confidence.get(fieldname, "none")
        if fieldname not in required and conf != "high":
            continue  # too weak to claim an optional field
        rename[header] = fieldname
        sources[fieldname] = f"{header} ({used.get(header, '?')}, {conf})"

    # Salesforce-style "Type" column rescue (2026-06-10 dry-run, wishlist 4).
    # The bare header is far too generic to claim by name alone (the "Forecast
    # Category" lesson), so it is claimed only when the VALUES check out: at
    # least 80% of non-blank values must classify as new/renewal deal types.
    if "is_renewal" not in rename.values():
        for col in cols:
            if col in rename or mapping.normalize(col) not in _TYPE_HEADERS:
                continue
            vals = df[col].astype(str).str.strip()
            vals = vals[~vals.str.lower().isin(_MISSING_STRINGS)]
            if len(vals) and vals.map(_deal_type_of).ne("").mean() >= 0.8:
                rename[col] = "is_renewal"
                sources["is_renewal"] = f"{col} (value-scan, high)"
                if report is not None:
                    report.notes.append(
                        f"mapped '{col}' to the new-vs-renewal deal type by "
                        "value scan (values look like deal types)"
                    )
                break

    if report is not None:
        report.field_sources = sources
        report.unmapped_columns = [c for c in cols if c not in rename]
    return df.rename(columns=rename)


def validate(df: pd.DataFrame) -> None:
    """Ensure required columns are present; raise SchemaError if not."""
    missing = [c for c in REQUIRED_FIELDS if c not in df.columns]
    if missing:
        raise SchemaError(
            f"Input is missing {len(missing)} required column(s): {missing}. "
            f"See pricing/schema.py and gtm/data-request.md."
        )


def _dedupe(df: pd.DataFrame, report: LoadReport) -> pd.DataFrame:
    """Drop exact re-export duplicates; flag same-id-different-values conflicts.

    A re-export that appends the same rows twice would otherwise double-count
    booked ACV. Exact-row duplicates drop silently into the report. Rows sharing
    an opportunity_id but disagreeing on values are a data-quality error: we keep
    the first and surface a warning rather than guess which is right.
    """
    if "opportunity_id" not in df.columns:
        return df
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    report.exact_duplicates_dropped = before - len(df)
    conflict_mask = df["opportunity_id"].duplicated(keep=False)
    if conflict_mask.any():
        report.conflicting_ids = sorted(
            df.loc[conflict_mask, "opportunity_id"].astype(str).unique().tolist()
        )
        df = df.drop_duplicates(subset="opportunity_id", keep="first").reset_index(drop=True)
    return df


def _exclude_open(df: pd.DataFrame, report: LoadReport) -> pd.DataFrame:
    """Drop rows whose stage is not a closed outcome (open pipeline deals).

    A CRM export full of Negotiation / Proposal Sent rows would otherwise be
    counted as losses and silently tank the win rate. Excluded counts go to the
    report by stage, so the exclusion is visible, never silent.
    """
    if "outcome" not in df.columns:
        return df
    is_closed = df["outcome"].isin(_CLOSED)
    if not is_closed.all():
        report.excluded_open = {
            str(k): int(v)
            for k, v in df.loc[~is_closed, "outcome"].value_counts().items()
        }
        df = df[is_closed].reset_index(drop=True)
    return df


def _require_enough(df: pd.DataFrame) -> None:
    """Fail loudly when there is not enough closed data for a real diagnostic."""
    if len(df) == 0:
        raise SchemaError(
            "No deals to analyze: the file parsed but has no closed (won or "
            "lost) data rows. Check that it is a deals export, not a header-only "
            "or summary file."
        )
    if len(df) < MIN_CLOSED_DEALS:
        raise SchemaError(
            f"Only {len(df)} closed deal(s) found; the diagnostic needs at least "
            f"{MIN_CLOSED_DEALS} closed (won or lost) deals to be meaningful."
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
_BOOL_FALSE = {"false", "0", "no", "n", "f", "nein", "falsch"}
_MISSING_STRINGS = {"", "nan", "none", "null", "na"}


def _deal_type_of(value: object) -> str:
    """Classify a raw renewal-flag / deal-Type value: 'renewal' | 'new' | ''.

    Handles both boolean renewal flags ("true"/"false") and CRM Type values
    ("Renewal", "Existing Business", "New Business"). Existing-business
    variants count as renewal-side: the disease framing is existing-customer
    discounting vs new-business discounting. Anything unrecognized maps to ''
    (unknown) rather than being guessed — never silently fillna a deal type.
    Order matters: "renewal" contains the substring "new".
    """
    s = str(value).strip().lower()
    if s in _MISSING_STRINGS:
        return ""
    if s in _BOOL_TRUE or "renew" in s or "existing" in s:
        return "renewal"
    if s in _BOOL_FALSE or "new" in s:
        return "new"
    return ""
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


def _ambiguous_date_note(df: pd.DataFrame) -> str | None:
    """Disclose when a slash/dot date column's day/month order can't be inferred
    (every day <= 12), so the month-first assumption is visible, not silent."""
    if "close_date" not in df.columns:
        return None
    saw = first_gt12 = second_gt12 = False
    for v in df["close_date"].astype(str):
        m = _DATE_RE.match(v)
        if not m:
            continue
        saw = True
        if int(m.group(1)) > 12:
            first_gt12 = True
        if int(m.group(2)) > 12:
            second_gt12 = True
    if saw and not first_gt12 and not second_gt12:
        return ("close_date day/month order is ambiguous (every day <= 12); "
                "assumed MM/DD/YYYY (month-first) — confirm if your export is "
                "day-first")
    return None


def _scan_currencies(df: pd.DataFrame) -> list[str]:
    """Currency symbols present across the money columns. More than one means a
    naive symbol-strip would sum different currencies into one total."""
    found: set[str] = set()
    for col in ("booked_acv", "list_acv"):
        if col in df.columns:
            s = df[col].astype(str)
            for sym in ("$", "€", "£", "¥"):
                if s.str.contains(re.escape(sym)).any():
                    found.add(sym)
    return sorted(found)


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
    if "competitor_present" in df.columns:
        df["competitor_present"] = (
            df["competitor_present"].astype(str).str.strip().str.lower().isin(_BOOL_TRUE)
        )
    if "is_renewal" in df.columns:
        # Derive the canonical three-state deal_type ('new' / 'renewal' / '')
        # BEFORE collapsing is_renewal to bool, so unknowns stay unknown
        # instead of silently becoming "new". Recognizes boolean flags and
        # CRM Type values ("Renewal", "New Business") alike.
        df["deal_type"] = df["is_renewal"].map(_deal_type_of)
        df["is_renewal"] = df["deal_type"].eq("renewal")
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
    # Cap realization at 1.5 (booked up to 1.5x list) as a data-sanity bound,
    # not at 1.0 — deals booked ABOVE list (expansion, CPI indexation, scarcity)
    # are legitimate pricing-power signals, the opposite of leakage.
    df["price_realization"] = (df["booked_acv"] / list_acv).clip(upper=1.5)
    # round to 6dp so band assignment is deterministic at boundaries
    # (e.g. 1 - 0.8 == 0.19999999999999996 in float would mis-band a clean 20%).
    # NOTE: no lower clamp — discount_pct may be negative (above-list deals); the
    # realization cap above is the sanity bound. Clamping here erased them.
    df["discount_pct"] = (1.0 - df["price_realization"]).clip(upper=1.0).round(6)
    # discount_amount is "discount given", so it floors at 0 (an above-list deal
    # gave no discount; its premium is not negative leakage).
    df["discount_amount"] = (df["list_acv"] - df["booked_acv"]).clip(lower=0.0)
    df["is_won"] = df["outcome"].astype(str) == Outcome.WON.value
    # A blank/unparseable booked value leaves discount_pct NaN. Never fillna(0):
    # that would bin those rows into "0-5%" and depress the low-band win rate,
    # which moves the reference discount and the headline leakage number. NaN
    # band rows are excluded from win_rate_by_band and reference_discount (they
    # are already counted in the LoadReport's blank_booked).
    df["discount_band"] = df["discount_pct"].map(
        lambda x: band_for(x) if pd.notna(x) else None
    )

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

    # Canonical deal_type for the New-vs-Renewal split. The CSV path derives
    # it in _coerce_types (three-state, before the bool collapse); this covers
    # direct-frame callers (tests, notebooks) that pass is_renewal natively.
    if "deal_type" not in df.columns and "is_renewal" in df.columns:
        if df["is_renewal"].dtype == bool:
            df["deal_type"] = np.where(df["is_renewal"], "renewal", "new")
        else:
            df["deal_type"] = df["is_renewal"].map(_deal_type_of)

    approver = df.get("approved_by", pd.Series([""] * len(df))).fillna("").astype(str)
    df["off_policy"] = df["discount_pct"] > policy_threshold
    df["off_policy_unapproved"] = df["off_policy"] & (approver.str.strip() == "")
    return df


def _ingest_loaded(
    df: pd.DataFrame,
    report: LoadReport,
    policy_threshold: float,
) -> tuple[pd.DataFrame, LoadReport]:
    """Run the canonical pipeline on an already-loaded frame."""
    df = apply_header_mapping(df, report)

    # Drop blank / summary rows that carry no opportunity id.
    if "opportunity_id" in df.columns:
        oid = df["opportunity_id"].astype(str).str.strip()
        before = len(df)
        df = df[oid != ""].reset_index(drop=True)
        report.blank_rows_dropped = before - len(df)
    report.rows_read = len(df)

    validate(df)                       # required columns present
    df = _dedupe(df, report)           # exact re-export dupes + id conflicts
    # Disclose assumptions BEFORE coercion strips the evidence (currency symbols,
    # date order). These are surfaced in the report, not silently resolved.
    report.currencies = _scan_currencies(df)
    date_note = _ambiguous_date_note(df)
    if date_note:
        report.notes.append(date_note)
    df = _coerce_types(df)             # money / dates / outcome / booleans
    if "booked_acv" in df.columns:
        report.blank_booked = int(df["booked_acv"].isna().sum())
    df = _exclude_open(df, report)     # non-closed pipeline rows
    _require_enough(df)                # ≥1 row, ≥ MIN_CLOSED_DEALS closed

    df = resolve_identity(df)
    df = enrich(df, policy_threshold=policy_threshold)
    report.rows_kept = len(df)
    report.above_list_deals = int((df["discount_pct"] < 0).sum())
    return df, report


def ingest_frame_verbose(
    frame: pd.DataFrame,
    source: str = "in-memory records",
    policy_threshold: float = DEFAULT_POLICY_THRESHOLD,
) -> tuple[pd.DataFrame, LoadReport]:
    """In-memory counterpart to ingest_verbose.

    CRM connectors use this path so live opportunity rows never need a
    temporary file. The validation, disclosure, and enrichment behavior is
    otherwise identical to a CSV/XLSX diagnostic.
    """
    report = LoadReport(source=source)
    return _ingest_loaded(frame.copy(), report, policy_threshold)


def ingest_verbose(
    path: str | Path,
    policy_threshold: float = DEFAULT_POLICY_THRESHOLD,
) -> tuple[pd.DataFrame, LoadReport]:
    """Full pipeline returning the enriched deals AND a LoadReport of what was
    read, excluded, deduped, decoded, and inferred.

    Pipeline: load → map headers → drop blanks → validate columns → coerce →
    dedupe → exclude open deals → require enough closed data → resolve → enrich.
    The report is the customer-facing 'here is what we read from your file'
    artifact; see data/synthetic/adversarial-fixtures/ for the traps it closes.
    """
    report = LoadReport(source=Path(path).name)
    df = load_any(path, report)
    return _ingest_loaded(df, report, policy_threshold)


def ingest(path: str | Path,
           policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> pd.DataFrame:
    """Backward-compatible entry point: the enriched deals only.

    Use ingest_verbose() when you also want the LoadReport (what was read /
    excluded / deduped / decoded), e.g. to show it in the dashboard.
    """
    df, _report = ingest_verbose(path, policy_threshold=policy_threshold)
    return df
