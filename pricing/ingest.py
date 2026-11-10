"""Ingestion + identity resolution.

Loads a deals CSV (synthetic or a prospect's export), validates it against the
canonical schema, resolves account identity from messy names, and derives the
fields the metrics layer needs.

Identity resolution is deliberately simple and explainable (explainability >
accuracy in enterprise): normalize the account name to a core, then collapse
rows sharing a core or an account_id into one resolved account. This is a
heuristic, not entity-resolution-as-a-service, it is documented as such and is
the right amount of machinery for a CSV diagnostic.
"""

from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from pricing import mapping
from pricing.schema import (
    BILLING_ONLY_OUTCOME,
    DEFAULT_POLICY_THRESHOLD,
    FIELDS,
    REQUIRED_FIELDS,
    Outcome,
    PROVENANCE_DEFAULTS,
    PROVENANCE_ENUMS,
    band_for,
)

# A diagnostic needs a minimum of real closed deals to mean anything; below this
# we fail loudly rather than render a NaN dashboard.
MIN_CLOSED_DEALS = 30
_CLOSED = {Outcome.WON.value, Outcome.LOST.value}
# CSV decode cascade for the common real-world encodings. latin-1 maps every
# byte, so it never raises, it is the guaranteed last resort.
_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


@dataclass
class LoadReport:
    """What we read from a file, and what we set aside and why.

    This is the 'here is what we read from your file' artifact the diagnostic
    should surface first, the explainability posture applied to ingestion.
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
    blank_list_acv: int = 0           # rows with no usable list price
    # Header-mapping provenance: which incoming column each canonical field came
    # from, and which incoming columns we left unmapped. Makes a mis-map visible.
    field_sources: dict[str, str] = field(default_factory=dict)  # field -> "header (layer)"
    unmapped_columns: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Currency (see _detect_row_currency / CurrencyBlockedError). blockers is
    # populated the moment ingestion refuses to proceed, so the exception can
    # carry a report that still discloses what was found.
    blockers: list[str] = field(default_factory=list)
    fx_normalized: bool = False       # mixed currencies were converted to USD
    fx_rate_date: str = ""            # as-of date disclosed for that conversion
    # Source profile (layer 0, header set only) and what the cpq_line roll-up did.
    profile: str = ""                 # crm_opportunity | cpq_line | unknown
    profile_grain: str = ""
    quote_lines_read: int = 0         # raw quote lines before the roll-up
    quarantined_lines: int = 0        # lines with a blank / missing quote id
    quarantined_reason: str = ""
    quote_resolution: dict = field(default_factory=dict)  # rule + counts + ids
    # Deals whose stage no value map could place: raw stage -> {deals, id_kind,
    # ids, ids_omitted}. Never counted as lost or open, never in win rate.
    ask_user: dict[str, dict] = field(default_factory=dict)

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
        if self.profile == "cpq_line":
            out.append(f"  quote-line export: {self.quote_lines_read} lines "
                       "rolled up to one deal per quote")
        if self.quarantined_lines:
            out.append(f"  set aside {self.quarantined_lines} line(s) with a "
                       "blank or missing quote id (not counted in any deal)")
        qr = self.quote_resolution
        if qr and qr.get("quotes_superseded"):
            out.append(
                f"  {qr['quotes_superseded']} quote(s) superseded across "
                f"{qr['opportunities_with_multiple_quotes']} opportunity(ies) "
                "with several quotes; one deal each. " + qr["rule"])
        if self.ask_user:
            total = sum(v["deals"] for v in self.ask_user.values())
            detail = ", ".join(f"{k or '(blank)'}: {v['deals']}"
                               for k, v in self.ask_user.items())
            out.append(f"  set aside {total} deal(s) with an unrecognised stage "
                       f"({detail}); not counted as won, lost or open")
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
                "(booked > list): a pricing-power signal, not leakage"
            )
        if self.blockers:
            for b in self.blockers:
                out.append(f"  BLOCKED: {b}")
        elif self.fx_normalized:
            out.append(
                f"  currencies normalized to USD (rate date: "
                f"{self.fx_rate_date or 'unspecified'})"
            )
        elif len(self.currencies) > 1:
            out.append(
                f"  WARNING: mixed currency symbols in money columns "
                f"({', '.join(self.currencies)}): totals may combine currencies, "
                "verify the source uses one currency"
            )
        if self.blank_booked:
            out.append(
                f"  {self.blank_booked} deal(s) with a blank / unparseable booked "
                "value (excluded from dollar totals)"
            )
        if self.blank_list_acv:
            out.append(
                f"  {self.blank_list_acv} deal(s) with a blank or zero list price "
                "(excluded from discount, realization and leakage, but still "
                "counted in the deal total)"
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
            "renewal_uplift", "cogs_acv", "list_unit_rate", "credits_tcv"]
_LEGAL_TOKENS = {"inc", "llc", "corp", "co", "ltd", "incorporated", "llp", "plc"}
_PUNCT = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")


# Headers eligible for the value-validated deal-type rescue (normalized form).
_TYPE_HEADERS = {"type", "opportunity type", "opp type", "deal type",
                 "record type"}


class SchemaError(ValueError):
    """Raised when an input CSV is missing required columns."""


class CurrencyBlockedError(SchemaError):
    """Raised when money columns mix currencies and no fx_rates were supplied.

    Carries the partially-populated `report` (a LoadReport) so a caller can
    still show what was found, which currencies, how many rows each, even
    though ingestion refused to produce a dollar total that would silently
    combine them. See `_ingest_loaded` for the default-block / opt-in-normalize
    contract.
    """

    def __init__(self, message: str, report: "LoadReport") -> None:
        super().__init__(message)
        self.report = report


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
    mapper (synonyms + fuzzy only, no embeddings/LLM, so ingest stays offline
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
    if report is not None:
        # A mapper layer that did not run belongs in the artifact the customer
        # actually reads, alongside blank_booked and blank_list_acv, not only
        # in a response field no upload UI renders.
        report.notes.extend(result["notes"])
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


_MAX_BAD_VALUES = 5
_MAX_BAD_VALUE_LEN = 40


def validate_provenance_enums(df: pd.DataFrame, allow_erp_verified: bool = False) -> None:
    """Raise SchemaError if source_system or cost_basis holds an invalid value.

    The error names the column and the offending values (at most 5 distinct,
    each truncated to 40 characters, then "and N more"). A bad value is never
    coerced to the default. cost_basis=erp_verified is reserved for a
    Pricekeel-operated connector (ADR-006) and is rejected unless
    allow_erp_verified is True.
    """
    for col, allowed in PROVENANCE_ENUMS.items():
        if col not in df.columns:
            continue
        v = df[col].fillna("").astype(str).str.strip().str.lower()
        bad = sorted(set(v[(v != "") & ~v.isin(allowed)]))
        if bad:
            raise SchemaError(
                f"Invalid {col} value(s) {_capped(bad)}; allowed: "
                f"{sorted(allowed)}. Not coerced to the default."
            )
    if not allow_erp_verified and "cost_basis" in df.columns:
        v = df["cost_basis"].fillna("").astype(str).str.strip().str.lower()
        if (v == "erp_verified").any():
            raise SchemaError(
                "cost_basis=erp_verified may only be set by a Pricekeel-operated "
                "connector, not by an uploaded file or frame. Use crm_proxy or "
                "declared_cost."
            )


_SOURCE_SYSTEM_ALIASES = {"sfdc": "salesforce", "salesforce_crm": "salesforce",
                          "hubspot_crm": "hubspot"}


def _capped(values: list[str]) -> str:
    shown = [b if len(b) <= _MAX_BAD_VALUE_LEN else b[:_MAX_BAD_VALUE_LEN] + "..."
             for b in values[:_MAX_BAD_VALUES]]
    more = f" and {len(values) - len(shown)} more" if len(values) > len(shown) else ""
    return f"{shown}{more}"


def apply_provenance_defaults(
    df: pd.DataFrame,
    report: LoadReport,
    allow_erp_verified: bool = False,
) -> pd.DataFrame:
    """Return a copy of df with source_system and cost_basis defaulted.

    A missing column is added with its default; blank cells in a present
    column are filled with it. Values are stripped and lower-cased.
    source_system is provenance, not a trust label: known aliases (sfdc,
    salesforce_crm, hubspot_crm) are normalized, and an unknown value is
    replaced by the default and disclosed in report.notes (never rejected). Placeholders such as
    none, null, na, n/a count as blank. report is required so a replacement
    can never go undisclosed.
    cost_basis is strict (see validate_provenance_enums).
    """
    df = df.copy()
    for col, default in PROVENANCE_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default
            continue
        v = df[col].fillna("").astype(str).str.strip().str.lower()
        df[col] = v.where(~v.isin(_MISSING_STRINGS | {"n/a"}), default)
    ss = (df["source_system"].str.replace(r"[\s\-]+", "_", regex=True)
          .replace(_SOURCE_SYSTEM_ALIASES))
    bad_mask = ~ss.isin(PROVENANCE_ENUMS["source_system"])
    if bad_mask.any():
        bad = sorted(set(ss[bad_mask]))
        report.notes.append(
            f"warning: source_system held unrecognized value(s) "
            f"{_capped(bad)} in {int(bad_mask.sum())} row(s); replaced with "
            f"the default '{PROVENANCE_DEFAULTS['source_system']}'"
        )
        ss = ss.where(~bad_mask, PROVENANCE_DEFAULTS["source_system"])
    df["source_system"] = ss
    validate_provenance_enums(df, allow_erp_verified=allow_erp_verified)
    return df


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


# --- Source profiles (PK-39) -------------------------------------------------
# A file whose headers profile as cpq_line has one row per quote LINE. It is
# rolled up to one deal per quote (pricing.mapping.rollup_quote_lines) before
# anything counts a deal, and several quotes for one opportunity are resolved
# to one deal. Everything here is deterministic arithmetic on the file, no LLM.

QUOTE_RESOLUTION_RULE = (
    "One deal per opportunity. When several quotes share an opportunity id, "
    "the latest quote by sent date (else created date, when every quote of "
    "that opportunity carries one and one is strictly latest) is kept; "
    "otherwise the single quote marked primary; otherwise the highest quote "
    "id. Superseded quotes are listed here and never counted."
)
_PRIMARY_HEADERS = {"primary", "is primary", "isprimary", "primary quote",
                    "is primary quote", "primary flag", "sbqq primary"}
_SENT_HEADERS = {"sent date", "quote sent date", "date sent", "sent at",
                 "sent on", "quote sent", "sent"}
_MAX_IDS = 200                      # ids listed per disclosure, counts stay exact
_NON_CARRIED = {"outcome", "source_system", "cost_basis", "source_record_id",
                "source_quote_id"}


def _cap_ids(ids: list[str]) -> tuple[list[str], int]:
    return ids[:_MAX_IDS], max(0, len(ids) - _MAX_IDS)


def _natural_key(s: str) -> tuple:
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p)
                 for p in re.split(r"(\d+)", str(s)) if p != "")


def _blank_cell(v: object) -> bool:
    return v is None or (isinstance(v, float) and v != v) or \
        str(v).strip().lower() in _MISSING_STRINGS


def _first_by_quote(lines: pd.DataFrame, qid: pd.Series, col: str | None,
                    as_flag: bool = False) -> dict[str, object]:
    """First non-blank value of one raw column per quote id (any truthy cell
    when as_flag)."""
    out: dict[str, object] = {}
    if not col or col not in lines.columns:
        return out
    for q, v in zip(qid, lines[col]):
        if not q:
            continue
        if as_flag:
            out[q] = out.get(q, False) or (
                not _blank_cell(v) and str(v).strip().lower() in _BOOL_TRUE)
        elif q not in out and not _blank_cell(v):
            out[q] = v
    return out


def _guard_cpq_currency(lines: pd.DataFrame, roles: dict[str, str],
                        report: "LoadReport") -> str:
    """Refuse to sum lines in different currencies into one quote.

    The roll-up parses money and so drops the symbols the CRM path reads
    afterwards; mixed symbols, or one quote with two ISO codes, are checked
    here on the raw lines. Returns the single ISO code implied by a lone
    symbol ('' when none)."""
    seen: set[str] = set()
    for role in ("line_booked", "line_list", "unit_net", "unit_list"):
        col = roles.get(role)
        if col and col in lines.columns:
            s = lines[col].astype(str)
            for sym in _CURRENCY_SYMBOLS:
                if s.str.contains(sym, regex=False).any():
                    seen.add(sym)
    report.currencies = sorted(seen)
    blocker = ""
    if len(seen) > 1:
        blocker = (f"Quote lines mix currency symbols ({', '.join(sorted(seen))}). "
                   "Rolling lines up would sum different currencies into one "
                   "quote total. Split the file by currency and ingest each "
                   "separately.")
    ccol = next((c for c in lines.columns
                 if mapping._field_of(c) == "currency"), None)
    key = roles.get("quote_id")
    if not blocker and ccol and key in lines.columns:
        codes = lines[ccol].fillna("").astype(str).str.strip().str.upper()
        per_quote = (pd.DataFrame({"q": lines[key].astype(str).str.strip(),
                                   "c": codes})
                     .query("c != ''").groupby("q")["c"].nunique())
        n_bad = int((per_quote > 1).sum())
        if n_bad:
            blocker = (f"{n_bad} quote(s) carry lines in more than one "
                       "currency. Rolling lines up would sum different "
                       "currencies into one quote total.")
    if blocker:
        report.blockers.append(blocker)
        raise CurrencyBlockedError(blocker, report)
    return _CURRENCY_SYMBOLS[next(iter(seen))] if len(seen) == 1 else ""


def _pick_quote(sub: pd.DataFrame) -> tuple[object, str]:
    """Index label of the quote kept for one opportunity, and the rule used."""
    for rule, col in (("latest_sent_date", "_sent_dt"),
                      ("latest_created_date", "_created_dt")):
        d = sub[col]
        if d.notna().all():
            hit = d == d.max()
            if int(hit.sum()) == 1:
                return sub.index[hit][0], rule
    primary = sub[sub["_primary"]]
    if len(primary) == 1:
        return primary.index[0], "primary_quote"
    best = max(sub.index, key=lambda i: _natural_key(sub.at[i, "source_quote_id"]))
    return best, "highest_quote_id"


def _route_profile(df: pd.DataFrame, report: "LoadReport"
                   ) -> tuple[pd.DataFrame, dict | None]:
    """Layer-0 profile of the raw headers. A cpq_line file is rolled up to one
    deal per quote here, before the CRM pipeline (and _exclude_open) sees it.
    Returns (frame, cpq_info); cpq_info is None for every other profile, whose
    frame is returned untouched."""
    headers = [str(c).strip() for c in df.columns]
    prof = mapping.profile_source(headers)
    report.profile, report.profile_grain = prof["profile"], prof["grain"]
    if prof["profile"] != mapping.PROFILE_CPQ:
        return df, None

    lines = df.copy()
    lines.columns = headers
    roles = prof["roles"]
    iso = _guard_cpq_currency(lines, roles, report)
    try:
        deals = mapping.rollup_quote_lines(lines, roles)
    except ValueError as exc:
        raise SchemaError(f"Quote-line export cannot be rolled up: {exc}") from exc
    key = deals.attrs["join_key"]
    report.quote_lines_read = len(lines)
    quarantined = deals.attrs.get("quarantined_lines")
    report.quarantined_lines = 0 if quarantined is None else len(quarantined)
    report.quarantined_reason = deals.attrs.get("quarantined_reason", "")

    qid = lines[key].map(lambda v: "" if _blank_cell(v) else str(v).strip())
    status_col = roles.get("quote_status")
    raw_status: dict[str, str] = {}
    if status_col and status_col in lines.columns:
        seen_raw: dict[str, set[str]] = {}
        for q, v in zip(qid, lines[status_col]):
            if q:
                seen_raw.setdefault(q, set()).add("" if _blank_cell(v)
                                                  else str(v).strip())
        raw_status = {q: " | ".join(sorted(s)) for q, s in seen_raw.items()}
    deals["_stage_raw"] = deals["source_quote_id"].map(raw_status).fillna("")

    # Carry the deal-level descriptive columns the roll-up does not (product
    # tier, value metric, ...): first non-blank value per quote. Amounts and
    # outcome are never carried; the roll-up owns them.
    result = mapping.map_headers(headers, llm_fallback=False, use_embeddings=False)
    deal_fields = {f.name for f in FIELDS
                   if f.dtype in ("str", "enum", "date", "bool")} - _NON_CARRIED
    carried: list[str] = []
    for fname, header in result["mapping"].items():
        if (not header or fname not in deal_fields or fname in deals.columns
                or header in (key, status_col)):
            continue
        if fname not in REQUIRED_FIELDS and result["confidence"].get(fname) != "high":
            continue
        first = _first_by_quote(lines, qid, header)
        deals[fname] = deals["source_quote_id"].map(first)
        carried.append(fname)
    if carried:
        report.notes.append(
            "quote lines rolled up to one deal per quote; first non-blank "
            f"value per quote used for: {', '.join(sorted(carried))}")

    # Several quotes for one opportunity: one deal, by a stated rule.
    sent_hdr = next((h for h in headers if mapping.normalize(h) in _SENT_HEADERS), None)
    prim_hdr = next((h for h in headers if mapping.normalize(h) in _PRIMARY_HEADERS), None)
    sent_raw = deals["source_quote_id"].map(_first_by_quote(lines, qid, sent_hdr))
    deals["_sent_dt"] = parse_dates(sent_raw.astype(object).fillna(""))
    deals["_created_dt"] = (
        parse_dates(deals["created_date"].astype(object).fillna(""))
        if "created_date" in deals.columns
        else pd.Series(pd.NaT, index=deals.index))
    deals["_primary"] = deals["source_quote_id"].map(
        _first_by_quote(lines, qid, prim_hdr, as_flag=True)).fillna(False).astype(bool)
    opp = deals["opportunity_id"].map(
        lambda v: "" if _blank_cell(v) else str(v).strip())
    by_rule: dict[str, int] = {}
    superseded: list[str] = []
    n_multi = 0
    for _oid, sub in deals[opp != ""].groupby(opp[opp != ""], sort=False):
        if len(sub) < 2:
            continue
        n_multi += 1
        keep, rule = _pick_quote(sub)
        by_rule[rule] = by_rule.get(rule, 0) + 1
        superseded += [str(q) for i, q in sub["source_quote_id"].items() if i != keep]
    deals = deals[~deals["source_quote_id"].isin(superseded)].reset_index(drop=True)
    shown, omitted = _cap_ids(sorted(superseded, key=_natural_key))
    report.quote_resolution = {
        "rule": QUOTE_RESOLUTION_RULE,
        "opportunities_with_multiple_quotes": n_multi,
        "quotes_superseded": len(superseded),
        "by_rule": by_rule,
        "superseded_quote_ids": shown,
        "superseded_ids_omitted": omitted,
    }
    deals = deals.drop(columns=["_sent_dt", "_created_dt", "_primary"])

    # The deal key is the opportunity id; with none in the file, the quote id.
    blank_opp = deals["opportunity_id"].map(_blank_cell)
    if blank_opp.any():
        deals.loc[blank_opp, "opportunity_id"] = deals.loc[blank_opp, "source_quote_id"]
        report.notes.append(
            f"no opportunity id on {int(blank_opp.sum())} quote(s); the quote "
            "id is used as the deal key")
    n_unpriced = int(deals["unpriced_lines"].gt(0).sum())
    if n_unpriced:
        report.notes.append(
            f"{n_unpriced} quote(s) have lines with no computable booked "
            "amount; those lines add nothing to the sum")
    if "currency" not in deals.columns and iso:
        deals["currency"] = iso
    deals = deals.drop(columns=["unpriced_lines", "line_count"])

    consumed = set(roles.values()) | {h for h in (sent_hdr, prim_hdr) if h}
    consumed |= {h for h in headers if mapping._field_of(h) in
                 mapping.CPQ_ROLLUP_SPEC["first_non_blank"]}
    consumed |= {h for f, h in result["mapping"].items() if h and f in carried}
    return deals, {"headers": headers, "roles": roles, "consumed": consumed}


def _finish_cpq_report(report: "LoadReport", info: dict) -> None:
    """Provenance for a rolled-up file: what each deal field came from."""
    r = info["roles"]
    booked = r.get("line_booked") or (
        f"{r['unit_net']} x {r['quantity']}"
        if r.get("unit_net") and r.get("quantity") else "")
    listed = r.get("line_list") or (
        f"{r['unit_list']} x {r['quantity']}"
        if r.get("unit_list") and r.get("quantity") else "")
    src = {"source_quote_id": r.get("quote_id"), "booked_acv": booked,
           "list_acv": listed, "outcome": r.get("quote_status") or r.get("outcome")}
    report.field_sources = {f: f"{h} (quote-line roll-up)"
                            for f, h in src.items() if h}
    report.unmapped_columns = [h for h in info["headers"]
                               if h not in info["consumed"]]


def _canonical_outcome(series: pd.Series) -> pd.Series:
    """Every stage value through the single stage table in pricing.mapping:
    closed_won, closed_lost, open or ask_user. billing_only (a billing-sourced
    row) passes through; it is excluded with the open rows, as before."""
    def one(v: object) -> str:
        if _blank_cell(v):
            return mapping.OUTCOME_ASK_USER
        s = str(v).strip()
        if s.lower() == BILLING_ONLY_OUTCOME:
            return BILLING_ONLY_OUTCOME
        return mapping.normalize_stage(s, mapping.PROFILE_CRM)
    return series.map(one)


def _exclude_open(df: pd.DataFrame, report: LoadReport) -> pd.DataFrame:
    """Set aside every row that is not a closed outcome.

    Open pipeline (Negotiation, Sent, billing_only) is counted in
    report.excluded_open by raw stage: a CRM export full of Proposal Sent rows
    would otherwise be counted as losses and tank the win rate. A stage the
    single stage table (pricing.mapping.normalize_stage) cannot place is
    ask_user: it is never guessed into closed_lost, never counted as open, and
    never enters win rate. It is listed in report.ask_user with each raw stage
    value, its deal count and its ids. Nothing is dropped silently.
    """
    if "outcome" not in df.columns:
        return df
    raw = (df["_stage_raw"] if "_stage_raw" in df.columns
           else df["outcome"].map(lambda v: "" if _blank_cell(v) else str(v).strip()))
    is_closed = df["outcome"].isin(_CLOSED)
    is_ask = df["outcome"].eq(mapping.OUTCOME_ASK_USER)
    is_open = ~is_closed & ~is_ask
    # Casing rule for both sections below: keys are the ORIGINAL raw stage text
    # (no lowercasing), so excluded_open and ask_user read the same way.
    if is_open.any():
        report.excluded_open = {
            str(k): int(v)
            for k, v in raw[is_open].value_counts().items()
        }
    if is_ask.any():
        kind = "quote_id" if "source_quote_id" in df.columns else "opportunity_id"
        idc = "source_quote_id" if kind == "quote_id" else "opportunity_id"
        section: dict[str, dict] = {}
        for stage, sub in df[is_ask].groupby(raw[is_ask], sort=False):
            ids, omitted = _cap_ids([str(i) for i in sub[idc]])
            section[str(stage)] = {"deals": int(len(sub)), "id_kind": kind,
                                   "ids": ids, "ids_omitted": omitted}
        report.ask_user = section
    if not is_closed.all():
        df = df[is_closed].reset_index(drop=True)
    return df.drop(columns=["_stage_raw"], errors="ignore")


def _require_closed(df: pd.DataFrame, report: LoadReport) -> None:
    """_require_enough, but a file whose deals are ALL ask_user names the
    unresolved stage values instead of saying there is no closed data."""
    unresolved = _capped(sorted(report.ask_user)) if report.ask_user else ""
    n_ask = sum(v["deals"] for v in report.ask_user.values())
    if len(df) == 0 and n_ask and not report.excluded_open:
        raise SchemaError(
            f"No deal could be placed as won or lost: {n_ask} deal(s) carry "
            f"stage value(s) we do not recognise: {unresolved}. Nothing was "
            "guessed as lost. Map each stage to won or lost, or re-export "
            "with explicit Closed Won / Closed Lost stages.")
    try:
        _require_enough(df)
    except SchemaError as exc:
        if not n_ask:
            raise
        raise SchemaError(
            f"{exc} {n_ask} further deal(s) were set aside as ask_user "
            f"(unrecognised stage value(s): {unresolved}).") from exc


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

# Stage values are normalised by pricing.mapping.normalize_stage (the one
# stage table); see _canonical_outcome.

_BOOL_TRUE = {"true", "1", "yes", "y", "ja", "t", "wahr"}
_BOOL_FALSE = {"false", "0", "no", "n", "f", "nein", "falsch"}
_MISSING_STRINGS = {"", "nan", "none", "null", "na"}


def _deal_type_of(value: object) -> str:
    """Classify a raw renewal-flag / deal-Type value: 'renewal' | 'new' | ''.

    Handles both boolean renewal flags ("true"/"false") and CRM Type values
    ("Renewal", "Existing Business", "New Business"). Existing-business
    variants count as renewal-side: the disease framing is existing-customer
    discounting vs new-business discounting. Anything unrecognized maps to ''
    (unknown) rather than being guessed, never silently fillna a deal type.
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
                "assumed MM/DD/YYYY (month-first), confirm if your export is "
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


# --- Currency (per-row column + block-or-normalize on a mix) ----------------
# _scan_currencies (above) only asks "is there more than one symbol". These
# turn that into a per-row ISO code and a decision: block by default, or
# normalize to USD when the caller opts in with fx_rates.

_CURRENCY_SYMBOLS: dict[str, str] = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
DEFAULT_CURRENCY = "USD"
# Money columns that are true currency amounts. quantity is units, not money;
# renewal_uplift is a fraction (0.07 = 7%), not money, neither is converted.
_FX_MONEY_COLS = [c for c in _NUMERIC if c not in ("quantity", "renewal_uplift")]


def _detect_row_currency(df: pd.DataFrame) -> pd.Series:
    """Per-row ISO currency code inferred from the symbol on the raw money
    string. list_acv wins when both money columns carry a symbol; a row with
    no symbol on either defaults to DEFAULT_CURRENCY (the common case for a
    US-only CRM export, which never prints '$')."""
    out = pd.Series([""] * len(df), index=df.index, dtype=object)
    for col in ("booked_acv", "list_acv"):  # list_acv applied last, so it wins
        if col not in df.columns:
            continue
        sym = df[col].astype(str).map(
            lambda s: next((c for c in _CURRENCY_SYMBOLS if c in s), "")
        )
        out = sym.where(sym != "", out)
    return out.map(lambda s: _CURRENCY_SYMBOLS.get(s, DEFAULT_CURRENCY))


def _currency_row_counts(currency_codes: pd.Series) -> str:
    """'EUR (45 row(s)), USD (255 row(s))', used in blocker/disclosure text."""
    counts = currency_codes.value_counts().to_dict()
    return ", ".join(f"{code} ({n} row(s))" for code, n in sorted(counts.items()))


def _env_fx_rates() -> tuple[dict[str, float] | None, str | None]:
    """Opt-in FX rates from PRICEKEEL_FX_RATES, a JSON object shaped
    {"rates": {"EUR": 1.08, "GBP": 1.27}, "as_of": "2026-09-01"}. Rates are USD
    per one unit of that currency. Malformed/absent env returns (None, None),
    which keeps the default block behavior."""
    raw = os.environ.get("PRICEKEEL_FX_RATES", "").strip()
    if not raw:
        return None, None
    try:
        obj = json.loads(raw)
        rates = {str(k).upper(): float(v) for k, v in obj.get("rates", {}).items()}
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None, None
    return (rates or None), obj.get("as_of")


def _normalize_currency(df: pd.DataFrame, currency_codes: pd.Series,
                        fx_rates: dict[str, float]) -> pd.DataFrame:
    """Multiply every money column by its row's USD rate. USD rows are
    untouched (rate 1.0); renewal_uplift and quantity are never touched."""
    df = df.copy()
    rates = {str(k).upper(): float(v) for k, v in fx_rates.items()}
    rates.setdefault("USD", 1.0)
    rate = currency_codes.map(lambda c: rates.get(c, 1.0)).astype(float)
    for col in _FX_MONEY_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") * rate
    return df


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in _NUMERIC + _NUMERIC_NONMONEY:
        if col in df.columns:
            df[col] = parse_money(df[col])
    for col in ("created_date", "close_date"):
        if col in df.columns:
            df[col] = parse_dates(df[col])
    if "outcome" in df.columns:
        if "_stage_raw" not in df.columns:
            df["_stage_raw"] = df["outcome"].map(
                lambda v: "" if _blank_cell(v) else str(v).strip())
        df["outcome"] = _canonical_outcome(df["outcome"])
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
    # not at 1.0, deals booked ABOVE list (expansion, CPI indexation, scarcity)
    # are legitimate pricing-power signals, the opposite of leakage.
    df["price_realization"] = (df["booked_acv"] / list_acv).clip(upper=1.5)
    # round to 6dp so band assignment is deterministic at boundaries
    # (e.g. 1 - 0.8 == 0.19999999999999996 in float would mis-band a clean 20%).
    # NOTE: no lower clamp, discount_pct may be negative (above-list deals); the
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
    fx_rates: dict[str, float] | None = None,
    fx_rates_date: str | None = None,
    allow_erp_verified: bool = False,
) -> tuple[pd.DataFrame, LoadReport]:
    """Run the canonical pipeline on an already-loaded frame.

    Currency: fx_rates is opt-in (explicit param, else PRICEKEEL_FX_RATES).
    When the file mixes currencies (report.currencies has more than one
    symbol) and no fx_rates were supplied, this raises CurrencyBlockedError
    rather than silently summing EUR and USD as one number, see
    _detect_row_currency / _normalize_currency.
    """
    if fx_rates is None:
        fx_rates, env_date = _env_fx_rates()
        fx_rates_date = fx_rates_date or env_date

    df, cpq = _route_profile(df, report)       # cpq_line: roll lines up to deals
    if cpq is None:
        df = apply_header_mapping(df, report)
    else:
        _finish_cpq_report(report, cpq)

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
    currency_codes = _detect_row_currency(df)   # raw-string symbol scan
    # A Salesforce CurrencyIsoCode export (or any explicit currency column)
    # can carry more than one ISO code with no currency SYMBOL anywhere in the
    # money columns; report.currencies (the symbol scan above) then shows 0 or
    # 1 symbols and the mix would slip through entirely. Fold the explicit
    # column in before deciding "mixed" so an ISO-code-only mix is blocked
    # exactly like a symbol-only mix (2026-09-26 fix); the explicit code wins
    # per row, matching the final `df["currency"]` assignment below.
    if "currency" in df.columns:
        # astype(str) turns a None cell into the literal string "None" and a
        # NaN cell into "nan", so an explicit currency column with blank rows
        # (a Salesforce export with CurrencyIsoCode set on some Opportunities
        # and not others) used to read as its own currency code and block the
        # whole book as "mixed: NONE, USD" (2026-09-27 fix). Blank cells must
        # not compete as a currency; treat them the same as _MISSING_STRINGS.
        # pandas 3 keeps NaN through astype(str); fill first so blanks compare equal to "".
        explicit_currency = df["currency"].fillna("").astype(str).str.strip().str.upper()
        explicit_currency = explicit_currency.mask(
            explicit_currency.str.lower().isin(_MISSING_STRINGS), "",
        )
        currency_codes = currency_codes.mask(explicit_currency != "", explicit_currency)
    mixed = len(report.currencies) > 1 or currency_codes.nunique() > 1
    if mixed:
        detail = _currency_row_counts(currency_codes)
        codes_seen = sorted(currency_codes.unique())
        if fx_rates is None:
            blocker = (
                f"Mixed currencies in money columns: {', '.join(codes_seen)} "
                f"({detail}). Ingestion blocked by default: summing different "
                "currencies as one number would silently corrupt every dollar "
                "total. Pass fx_rates (ISO code -> USD value) and a rate date, "
                "or set PRICEKEEL_FX_RATES, to normalize to USD; or split the "
                "file by currency and ingest each separately."
            )
            report.blockers.append(blocker)
            raise CurrencyBlockedError(blocker, report)
        missing = sorted(c for c in currency_codes.unique()
                         if c != "USD" and c not in {k.upper() for k in fx_rates})
        if missing:
            blocker = (
                f"Cannot normalize: no fx rate supplied for {', '.join(missing)} "
                f"({detail}). Add rates for every non-USD currency present."
            )
            report.blockers.append(blocker)
            raise CurrencyBlockedError(blocker, report)
    date_note = _ambiguous_date_note(df)
    if date_note:
        report.notes.append(date_note)
    df = _coerce_types(df)             # money / dates / outcome / booleans
    df = apply_provenance_defaults(df, report,
                                    allow_erp_verified=allow_erp_verified)
    if mixed:
        detail = _currency_row_counts(currency_codes)
        df = _normalize_currency(df, currency_codes, fx_rates)  # type: ignore[arg-type]
        report.fx_normalized = True
        report.fx_rate_date = fx_rates_date or "unspecified"
        report.notes.append(
            f"normalized mixed currencies to USD ({detail}) using supplied "
            f"fx_rates, rate date: {report.fx_rate_date}"
        )
        df["currency"] = DEFAULT_CURRENCY
    elif "currency" in df.columns:
        # Same blank-cell fix as above: a None/NaN cell must fall back to the
        # row's detected currency code, not the literal string "NONE"/"NAN".
        supplied = df["currency"].fillna("").astype(str).str.strip().str.upper()
        supplied = supplied.mask(supplied.str.lower().isin(_MISSING_STRINGS), "")
        df["currency"] = supplied.where(supplied != "", currency_codes)
    else:
        df["currency"] = currency_codes
    if "booked_acv" in df.columns:
        report.blank_booked = int(df["booked_acv"].isna().sum())
    if "list_acv" in df.columns:
        # Blank or zero list price leaves realization, discount_pct and band
        # NaN in enrich(), so the row silently leaves every band and leakage
        # metric while still counting in overview's deal count. Disclose it
        # the way blank_booked is disclosed.
        list_acv = pd.to_numeric(df["list_acv"], errors="coerce")
        report.blank_list_acv = int((list_acv.isna() | (list_acv == 0)).sum())
    df = _exclude_open(df, report)     # non-closed pipeline rows
    _require_closed(df, report)        # ≥1 row, ≥ MIN_CLOSED_DEALS closed

    df = resolve_identity(df)
    df = enrich(df, policy_threshold=policy_threshold)
    report.rows_kept = len(df)
    report.above_list_deals = int((df["discount_pct"] < 0).sum())
    return df, report


def ingest_frame_verbose(
    frame: pd.DataFrame,
    source: str = "in-memory records",
    policy_threshold: float = DEFAULT_POLICY_THRESHOLD,
    fx_rates: dict[str, float] | None = None,
    fx_rates_date: str | None = None,
    allow_erp_verified: bool = False,
) -> tuple[pd.DataFrame, LoadReport]:
    """In-memory counterpart to ingest_verbose.

    CRM connectors use this path so live opportunity rows never need a
    temporary file. The validation, disclosure, and enrichment behavior is
    otherwise identical to a CSV/XLSX diagnostic.

    allow_erp_verified is for a Pricekeel-operated connector only: it lets
    cost_basis=erp_verified through. Customer upload paths leave it False.
    """
    report = LoadReport(source=source)
    return _ingest_loaded(frame.copy(), report, policy_threshold,
                          fx_rates=fx_rates, fx_rates_date=fx_rates_date,
                          allow_erp_verified=allow_erp_verified)


def ingest_verbose(
    path: str | Path,
    policy_threshold: float = DEFAULT_POLICY_THRESHOLD,
    fx_rates: dict[str, float] | None = None,
    fx_rates_date: str | None = None,
) -> tuple[pd.DataFrame, LoadReport]:
    """Full pipeline returning the enriched deals AND a LoadReport of what was
    read, excluded, deduped, decoded, and inferred.

    Pipeline: load → map headers → drop blanks → validate columns → coerce →
    dedupe → exclude open deals → require enough closed data → resolve → enrich.
    The report is the customer-facing 'here is what we read from your file'
    artifact; see data/synthetic/adversarial-fixtures/ for the traps it closes.

    fx_rates: optional {"EUR": 1.08, ...} (USD per one unit of that currency).
    When the file mixes currencies and fx_rates is not supplied here (or via
    PRICEKEEL_FX_RATES), ingestion raises CurrencyBlockedError rather than
    summing currencies. fx_rates_date documents the as-of date for the rates,
    disclosed in the returned LoadReport.
    """
    report = LoadReport(source=Path(path).name)
    df = load_any(path, report)
    return _ingest_loaded(df, report, policy_threshold,
                          fx_rates=fx_rates, fx_rates_date=fx_rates_date)


def ingest(path: str | Path,
           policy_threshold: float = DEFAULT_POLICY_THRESHOLD,
           fx_rates: dict[str, float] | None = None,
           fx_rates_date: str | None = None) -> pd.DataFrame:
    """Backward-compatible entry point: the enriched deals only.

    Use ingest_verbose() when you also want the LoadReport (what was read /
    excluded / deduped / decoded), e.g. to show it in the dashboard.
    """
    df, _report = ingest_verbose(path, policy_threshold=policy_threshold,
                                 fx_rates=fx_rates, fx_rates_date=fx_rates_date)
    return df
