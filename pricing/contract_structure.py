"""Contract-structure lens v0 (PK-32).

Five deterministic policy-rule levers for usage-based and hybrid deals, read
from a canonical, post-ingest deal frame:

    unit_rate      effective committed unit rate and its realization vs list
    commit_share   committed annual spend as a share of booked ACV
    overage_fence  on-demand rate vs the effective committed unit rate
    ramp           ramp depth, ramp concession dollars, TCV-weighted discount
    waterfall      revenue-side pocket waterfall (list, discount, ramp, credits)

Specification: docs/design/2026-11-07-contract-structure-lens-spec.md.

Rules this module holds to, by construction:
  * Every output is labelled method "policy rule". Nothing is fitted.
  * Each lever returns scored / insufficient_data / not_provided with a reason
    code. A deal that cannot be scored never inherits a book, segment or zero
    value (no global fallback). Flags are <NA> unless their lever is scored.
  * Levers are reported separately and never blended into one score.
  * Price only. No cost input is read; nothing here is a profitability figure.
  * discount_pct, price_realization, discount_band, discount_amount and
    off_policy are read and never written. The input frame is not mutated.
  * Ratios are fractions (0 to 1), rounded to 6 dp before any threshold
    comparison; dollar outputs are rounded to 2 dp on output only.

Ratios that can be NaN in a summary (flagged_share under 15 scored deals) stay
NaN here, as the spec says; PK-33 and PK-34 convert NaN to null at the API
boundary. The decision-record concession fields and the wiring of the readout
into the diagnostic and the API belong to PK-33 and PK-34.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from pricing.schema import DEFAULT_POLICY_THRESHOLD

METHOD = "policy rule"
LENS_VERSION = "contract-structure-v0"

COMMIT_SHARE_FLOOR_DEFAULT = 0.50
# Must equal governance.EXCEPTION_MAX_PCT / 100; defined locally so this module
# does not import psycopg through governance. A test asserts the equality.
EV_GRID_MAX_FRAC = 0.40
FULL_COMMIT_TOLERANCE = 0.005
STEADY_STATE_TOLERANCE = 0.005
REALIZATION_SANITY_CAP = 1.5
CONTRACT_LENS_MIN_SCORED = 15

LEVERS = ("unit_rate", "commit_share", "overage_fence", "ramp", "waterfall")

SCORED = "scored"
INSUFFICIENT = "insufficient_data"
NOT_PROVIDED = "not_provided"

# Boolean flags each lever emits, in summary order.
LEVER_FLAGS: dict[str, tuple[str, ...]] = {
    "unit_rate": ("unit_rate_below_floor", "unit_rate_outside_ev_grid"),
    "commit_share": ("low_commit_share",),
    "overage_fence": ("overage_fence_breach", "overage_below_list_unit_rate"),
    "ramp": ("ramp_hidden_discount", "ramp_unapproved"),
    "waterfall": ("off_invoice_below_floor",),
}

LEVER_LABELS: dict[str, str] = {
    "unit_rate": ("Effective committed unit rate: committed usage spend per committed unit, "
                  "compared with the list unit rate. Method: policy rule."),
    "commit_share": ("Commit share of booked: committed annual spend as a share of booked ACV. "
                     "Method: policy rule. Below {commit_share_floor:.0%}, most of the booked "
                     "value is uncommitted forecast."),
    "overage_fence": ("Overage fence: on-demand rate against the effective committed unit rate. "
                      "Method: policy rule. An overage rate at or below the committed rate "
                      "rewards under-commitment."),
    "ramp": ("Ramp: dollars scheduled below steady-state ACV over the term, and the discount on "
             "a total-contract basis. Method: policy rule."),
    "waterfall": ("Pocket price waterfall, revenue side: list, discount, ramp concessions, "
                  "credits, annualized. Method: policy rule. Price only, no cost."),
}
UNIT_RATE_GRID_NOTE = ("The unit discount is beyond the 40 percent range the exception verdict "
                       "can score.")

_BLANK_STRINGS = {"", "nan", "none", "null", "na"}


# --- helpers ------------------------------------------------------------------------

def _num(df: pd.DataFrame, col: str) -> pd.Series:
    """Float series for `col`; all-NaN when the column is absent."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").astype("float64")
    return pd.Series(np.nan, index=df.index, dtype="float64")


def _text(df: pd.DataFrame, col: str) -> pd.Series:
    """Lower-cased, stripped string series; blank-like values become ''."""
    if col not in df.columns:
        return pd.Series("", index=df.index, dtype="object")
    s = df[col].astype("object").where(df[col].notna(), "")
    s = s.astype(str).str.strip().str.lower()
    return s.where(~s.isin(_BLANK_STRINGS), "")


class _Decide:
    """First-match status/reason assignment, evaluated in the listed order."""

    def __init__(self, index: pd.Index) -> None:
        self.status = pd.Series("", index=index, dtype="object")
        self.reason = pd.Series("", index=index, dtype="object")
        self.done = pd.Series(False, index=index)

    def add(self, mask: pd.Series, status: str, reason: str) -> "_Decide":
        m = mask.fillna(False).astype(bool) & ~self.done
        self.status[m] = status
        self.reason[m] = reason
        self.done |= m
        return self

    def finish(self) -> tuple[pd.Series, pd.Series, pd.Series]:
        rest = ~self.done
        self.status[rest] = SCORED
        scored = self.status == SCORED
        return self.status, self.reason, scored


def _bool(values: pd.Series | np.ndarray, valid: pd.Series) -> pd.Series:
    """Nullable boolean: the value where `valid`, <NA> elsewhere."""
    v = pd.Series(values, index=valid.index).astype("boolean")
    return v.where(valid, pd.NA).astype("boolean")


def _f(values: pd.Series, valid: pd.Series, dp: int | None) -> pd.Series:
    out = pd.Series(values, index=valid.index, dtype="float64").where(valid, np.nan)
    return out.round(dp) if dp is not None else out


# --- per-deal lens ----------------------------------------------------------------

def contract_structure_deals(df: pd.DataFrame, *,
                             floor_frac: float = DEFAULT_POLICY_THRESHOLD,
                             commit_share_floor: float = COMMIT_SHARE_FLOOR_DEFAULT,
                             columns_present: Iterable[str] | None = None) -> pd.DataFrame:
    """Return a copy of `df` with the contract-structure columns appended.

    `columns_present` is the set of columns that existed in the uploaded file
    before ingest. It decides whether a blank ramp field means "not ramped"
    (columns in the file) or "not in the file" (lever 5 ramp step). Default
    None means df.columns.
    """
    missing = [c for c in ("discount_pct", "price_realization") if c not in df.columns]
    if missing:
        raise ValueError(
            f"contract_structure_deals needs the enriched columns {missing}; run the frame "
            "through pricing.ingest (ingest_frame_verbose or enrich) first.")
    present = set(df.columns if columns_present is None else columns_present)
    out = df.copy()
    idx = df.index
    new: dict[str, pd.Series] = {}

    vm = _text(df, "value_metric")
    is_seats = vm == "seats"
    vm_ok = vm.isin(["consumption", "hybrid"])
    is_hybrid = vm == "hybrid"
    is_cons = vm == "consumption"

    list_acv = _num(df, "list_acv")
    booked = _num(df, "booked_acv")
    fee = _num(df, "platform_fee_acv")
    committed = _num(df, "committed_acv")
    qty = _num(df, "quantity")
    ovr = _num(df, "overage_rate")
    lur = _num(df, "list_unit_rate")
    credits = _num(df, "credits_tcv")
    term = _num(df, "term_months")
    y1 = _num(df, "ramp_year_1_acv")
    y2 = _num(df, "ramp_year_2_acv")
    approver = _text(df, "approved_by")

    disc = _num(df, "discount_pct")
    # round before any threshold comparison, like every other ratio here (spec 7a.1):
    # a cent-denominated 15 percent deal sits at 0.8499999974 unrounded
    pr = _num(df, "price_realization").round(6)

    # --- shared checks --------------------------------------------------------
    def commit_checks(d: _Decide, *, with_c1_c2: bool, fee_check: bool = True) -> None:
        if with_c1_c2:
            d.add(is_seats, NOT_PROVIDED, "value_metric_seats")
            d.add(committed.isna(), NOT_PROVIDED, "committed_acv_blank")
        d.add(~vm_ok, INSUFFICIENT, "value_metric_unknown")
        bad_money = (committed < 0) | booked.isna() | (booked <= 0)
        if fee_check:  # a negative platform fee must never inflate committed usage (spec 7a.2)
            bad_money = bad_money | (is_hybrid & (fee < 0))
        d.add(bad_money, INSUFFICIENT, "invalid_money_value")
        d.add(committed > booked * (1 + STEADY_STATE_TOLERANCE), INSUFFICIENT, "commit_exceeds_booked")

    def rate_checks(d: _Decide) -> None:
        d.add(qty.isna() | (qty <= 0), INSUFFICIENT, "quantity_missing_or_zero")
        d.add(is_hybrid & fee.isna(), INSUFFICIENT, "platform_fee_missing_for_hybrid")
        d.add(usage <= 0, INSUFFICIENT, "usage_commit_not_positive")

    usage = pd.Series(np.where(is_hybrid, committed - fee, committed), index=idx)
    usage = usage.where(vm_ok, np.nan)

    # populated whenever commit_checks and rate_checks pass, NaN otherwise
    d0 = _Decide(idx)
    commit_checks(d0, with_c1_c2=True)
    rate_checks(d0)
    rate_ok = ~d0.done
    new["committed_usage_acv"] = _f(usage, rate_ok, 2)
    eff = (usage / qty).where(rate_ok, np.nan)
    new["effective_committed_unit_rate"] = eff.astype("float64")

    # --- lever 1: unit rate -----------------------------------------------------
    supplied = np.isfinite(lur) & (lur > 0)
    full_commit = (committed - booked).abs() <= FULL_COMMIT_TOLERANCE * booked
    derivable = is_cons & full_commit & (list_acv > 0) & (qty > 0) & ~supplied
    lur_used = pd.Series(np.nan, index=idx, dtype="float64")
    lur_used[supplied] = lur[supplied]
    lur_used[derivable] = (list_acv / qty)[derivable]
    basis = pd.Series("unavailable", index=idx, dtype="object")
    basis[derivable] = "derived"
    basis[supplied] = "supplied"
    new["list_unit_rate_used"] = lur_used
    new["list_unit_rate_basis"] = basis

    real = (eff / lur_used).round(6)
    d1 = _Decide(idx)
    commit_checks(d1, with_c1_c2=True)
    rate_checks(d1)
    d1.add(basis == "unavailable", INSUFFICIENT, "list_unit_rate_unavailable")
    d1.add(real > REALIZATION_SANITY_CAP, INSUFFICIENT, "unit_rate_realization_out_of_bounds")
    s1, r1, ok1 = d1.finish()
    floor_cmp = round(1 - floor_frac, 6)
    urd = (1 - real).round(6)
    ur_floor = lur_used * (1 - floor_frac)
    below = real < floor_cmp
    gap = (ur_floor - eff).clip(lower=0) * qty
    new["unit_rate_status"], new["unit_rate_reason"] = s1, r1
    new["unit_rate_realization"] = _f(real, ok1, 6)
    new["unit_rate_discount"] = _f(urd, ok1, 6)
    new["unit_rate_floor"] = _f(ur_floor, ok1, 6)
    new["unit_rate_below_floor"] = _bool(below, ok1)
    new["unit_rate_gap_to_floor_acv"] = _f(gap.where(below, 0.0), ok1, 2)
    new["unit_rate_outside_ev_grid"] = _bool(urd > EV_GRID_MAX_FRAC, ok1)

    # --- lever 2: commit share --------------------------------------------------
    d2 = _Decide(idx)
    commit_checks(d2, with_c1_c2=True, fee_check=False)
    s2, r2, ok2 = d2.finish()
    share = (committed / booked).round(6)
    new["commit_share_status"], new["commit_share_reason"] = s2, r2
    new["commit_share_of_booked"] = _f(share, ok2, 6)
    new["uncommitted_booked_acv"] = _f(booked - committed, ok2, 2)
    new["low_commit_share"] = _bool(share < commit_share_floor, ok2)

    # --- lever 3: overage fence -------------------------------------------------
    d3 = _Decide(idx)
    d3.add(is_seats, NOT_PROVIDED, "value_metric_seats")
    d3.add(ovr.isna(), NOT_PROVIDED, "overage_rate_blank")
    d3.add(committed.isna(), NOT_PROVIDED, "no_commitment")
    d3.add(ovr < 0, INSUFFICIENT, "invalid_money_value")
    commit_checks(d3, with_c1_c2=False)
    rate_checks(d3)
    s3, r3, ok3 = d3.finish()
    prem = (ovr / eff - 1).round(6)
    new["overage_fence_status"], new["overage_fence_reason"] = s3, r3
    new["overage_premium"] = _f(prem, ok3, 6)
    new["overage_fence_breach"] = _bool(prem <= 0, ok3)
    has_list = basis != "unavailable"
    ovr_below_list = _bool(ovr < lur_used, ok3 & has_list)
    new["overage_below_list_unit_rate"] = ovr_below_list

    # --- lever 4: ramp ----------------------------------------------------------
    term_years = term / 12
    w1 = term.clip(upper=12) / 12
    w2 = (term - 12).clip(lower=0, upper=12) / 12
    d4 = _Decide(idx)
    d4.add(y1.isna() & y2.isna(), NOT_PROVIDED, "no_ramp_recorded")
    d4.add(list_acv.isna() | booked.isna() | (list_acv <= 0) | (booked <= 0),
           INSUFFICIENT, "invalid_money_value")
    d4.add(term.isna() | (term <= 0), INSUFFICIENT, "term_months_missing")
    d4.add(term <= 12, INSUFFICIENT, "ramp_on_single_year_term")
    d4.add(y1.isna(), INSUFFICIENT, "ramp_year_1_missing")
    d4.add(y2.isna(), INSUFFICIENT, "ramp_year_2_missing")
    d4.add((y1 < 0) | (y2 < 0), INSUFFICIENT, "invalid_money_value")
    cap = booked * (1 + STEADY_STATE_TOLERANCE)
    d4.add((y1 > cap) | (y2 > cap), INSUFFICIENT, "ramp_above_steady_state")
    s4, r4, ok4 = d4.finish()

    concession = w1 * (booked - y1) + w2 * (booked - y2)
    steady_tcv = booked * term_years
    contracted = steady_tcv - concession
    list_tcv = list_acv * term_years
    twed = (1 - contracted / list_tcv).round(6)
    hidden = (disc <= floor_frac) & (twed > floor_frac)
    new["ramp_status"], new["ramp_reason"] = s4, r4
    new["ramp_depth_year_1"] = _f((1 - y1 / booked).round(6), ok4, 6)
    new["ramp_depth_year_2"] = _f((1 - y2 / booked).round(6), ok4, 6)
    new["ramp_concession_tcv"] = _f(concession, ok4, 2)
    new["ramp_concession_pct_of_booked_tcv"] = _f((concession / steady_tcv).round(6), ok4, 6)
    new["contracted_tcv"] = _f(contracted, ok4, 2)
    new["list_tcv"] = _f(list_tcv, ok4, 2)
    new["tcv_weighted_effective_discount"] = _f(twed, ok4, 6)
    new["ramp_discount_increment"] = _f((twed - disc).round(6), ok4, 6)
    new["ramp_hidden_discount"] = _bool(hidden, ok4)
    new["ramp_unapproved"] = _bool(hidden & (approver == ""), ok4)

    # --- lever 5: waterfall -----------------------------------------------------
    ramp_cols_in_file = bool({"ramp_year_1_acv", "ramp_year_2_acv"} & present)
    credits_present = credits.notna()
    ramp_scored = s4 == SCORED
    wf_ramp = pd.Series(np.nan, index=idx, dtype="float64")
    if ramp_cols_in_file:
        wf_ramp[:] = 0.0
    wf_ramp[ramp_scored] = (concession / term_years)[ramp_scored]
    wf_credits = (credits / term_years).where(credits_present, np.nan)
    pocket = booked - wf_ramp.fillna(0.0) - wf_credits.fillna(0.0)
    pocket_real = (pocket / list_acv).round(6)

    d5 = _Decide(idx)
    d5.add(list_acv.isna() | booked.isna() | (list_acv <= 0) | (booked <= 0),
           INSUFFICIENT, "invalid_money_value")
    d5.add(s4 == INSUFFICIENT, INSUFFICIENT, "ramp_step_insufficient")
    d5.add(credits < 0, INSUFFICIENT, "invalid_money_value")
    d5.add(credits_present & (term.isna() | (term <= 0)), INSUFFICIENT, "term_months_missing")
    d5.add((s4 == NOT_PROVIDED) & ~credits_present, NOT_PROVIDED, "no_off_invoice_steps")
    d5.add((pocket_real > REALIZATION_SANITY_CAP) | (pocket_real < 0),
           INSUFFICIENT, "pocket_realization_out_of_bounds")
    s5, r5, ok5 = d5.finish()
    new["waterfall_status"], new["waterfall_reason"] = s5, r5
    new["wf_list_acv"] = _f(list_acv, ok5, 2)
    new["wf_discount_acv"] = _f(list_acv - booked, ok5, 2)
    new["wf_ramp_concession_acv"] = _f(wf_ramp, ok5, 2)
    new["wf_credits_acv"] = _f(wf_credits, ok5, 2)
    new["pocket_acv"] = _f(pocket, ok5, 2)
    new["pocket_realization"] = _f(pocket_real, ok5, 6)
    ramp_step = pd.Series(np.where(wf_ramp.notna(), SCORED, NOT_PROVIDED), index=idx, dtype="object")
    cred_step = pd.Series(np.where(credits_present, SCORED, NOT_PROVIDED), index=idx, dtype="object")
    new["wf_ramp_step_status"] = ramp_step.where(ok5, "")
    new["wf_credits_step_status"] = cred_step.where(ok5, "")
    new["off_invoice_below_floor"] = _bool(
        (pr >= floor_cmp) & (pocket_real < floor_cmp), ok5)

    for lever in LEVERS:
        new[f"{lever}_method"] = pd.Series(METHOD, index=idx, dtype="object")
    new["contract_structure_method"] = pd.Series(METHOD, index=idx, dtype="object")

    for k, v in new.items():
        out[k] = v
    out.attrs["contract_structure"] = {
        "lens_version": LENS_VERSION, "method": METHOD,
        "floor_frac": floor_frac, "commit_share_floor": commit_share_floor,
        "ramp_columns_in_file": ramp_cols_in_file,
        "credits_column_in_file": "credits_tcv" in present,
    }
    return out


# --- book-level summary -----------------------------------------------------------

def _won_mask(deals: pd.DataFrame) -> pd.Series:
    if "is_won" in deals.columns:
        return deals["is_won"].fillna(False).astype(bool)
    if "outcome" in deals.columns:
        return deals["outcome"].astype(str) == "closed_won"
    raise ValueError("contract_structure needs is_won or outcome to tell won deals apart; "
                     "run the frame through pricing.ingest first.")


def _sum(deals: pd.DataFrame, col: str, mask: pd.Series) -> float:
    return round(float(pd.to_numeric(deals.loc[mask, col], errors="coerce").sum()), 2)


def contract_structure_summary(deals: pd.DataFrame) -> dict:
    """One dict per lever, won deals only. No cross-lever total exists."""
    params = deals.attrs.get("contract_structure", {})
    cs_floor = params.get("commit_share_floor", COMMIT_SHARE_FLOOR_DEFAULT)
    won = _won_mask(deals)
    result: dict[str, dict] = {}
    for lever in LEVERS:
        st = deals[f"{lever}_status"]
        scored = won & (st == SCORED)
        dollars, dollars_n = _lever_dollars(deals, lever, scored)
        n_scored = int(scored.sum())
        shares_ok = n_scored >= CONTRACT_LENS_MIN_SCORED
        n_flagged = {f: int((deals[f].fillna(False).astype(bool) & scored).sum())
                     for f in LEVER_FLAGS[lever]}
        reasons = (deals.loc[won & (st != SCORED), f"{lever}_reason"].value_counts().to_dict())
        result[lever] = {
            "lever": lever,
            "method": METHOD,
            "label": LEVER_LABELS[lever].format(commit_share_floor=cs_floor),
            "n_won": int(won.sum()),
            "n_scored": n_scored,
            "n_insufficient_data": int((won & (st == INSUFFICIENT)).sum()),
            "n_not_provided": int((won & (st == NOT_PROVIDED)).sum()),
            "reasons": {str(k): int(v) for k, v in sorted(reasons.items())},
            "n_flagged": n_flagged,
            "flagged_share": {f: (round(n / n_scored, 6) if shares_ok else float("nan"))
                              for f, n in n_flagged.items()},
            "share_status": SCORED if shares_ok else INSUFFICIENT,
            "dollars": dollars,
            "dollars_n": dollars_n,
        }
    return result


def _lever_dollars(deals: pd.DataFrame, lever: str,
                   scored: pd.Series) -> tuple[dict[str, float], dict[str, int]]:
    """(dollar sums, the deal counts behind them). Dollars hold floats only."""
    def flag(col: str) -> pd.Series:
        return scored & deals[col].fillna(False).astype(bool)

    if lever == "unit_rate":
        m = flag("unit_rate_below_floor")
        return ({"unit_rate_gap_to_floor_acv": _sum(deals, "unit_rate_gap_to_floor_acv", m)},
                {"unit_rate_below_floor": int(m.sum())})
    if lever == "commit_share":
        m = flag("low_commit_share")
        return ({"uncommitted_booked_acv": _sum(deals, "uncommitted_booked_acv", m)},
                {"low_commit_share": int(m.sum())})
    if lever == "overage_fence":
        # committed usage exposed to the fence breach, not a loss figure
        m = flag("overage_fence_breach")
        return ({"committed_usage_acv_exposed": _sum(deals, "committed_usage_acv", m)},
                {"overage_fence_breach": int(m.sum())})
    if lever == "ramp":
        m = flag("ramp_hidden_discount")
        return ({"ramp_concession_tcv_all_scored": _sum(deals, "ramp_concession_tcv", scored),
                 "ramp_concession_tcv_hidden_discount": _sum(deals, "ramp_concession_tcv", m)},
                {"scored": int(scored.sum()), "ramp_hidden_discount": int(m.sum())})
    m = flag("off_invoice_below_floor")
    gap = (pd.to_numeric(deals.loc[m, "booked_acv"], errors="coerce")
           - pd.to_numeric(deals.loc[m, "pocket_acv"], errors="coerce")).sum()
    return ({"wf_list_acv": _sum(deals, "wf_list_acv", scored),
             "wf_discount_acv": _sum(deals, "wf_discount_acv", scored),
             "wf_ramp_concession_acv": _sum(deals, "wf_ramp_concession_acv", scored),
             "wf_credits_acv": _sum(deals, "wf_credits_acv", scored),
             "booked_minus_pocket_acv_off_invoice_below_floor": round(float(gap), 2)},
            {"scored": int(scored.sum()), "off_invoice_below_floor": int(m.sum())})


# --- readout ------------------------------------------------------------------------

_COMMON = ("opportunity_id", "resolved_account_name", "segment", "value_metric")
_RAMP_COLS = ("term_months", "ramp_year_1_acv", "ramp_year_2_acv", "booked_acv", "discount_pct",
              "tcv_weighted_effective_discount", "ramp_concession_tcv", "approved_by")

# flag -> (lever, columns after the common ones)
_FLAG_SPECS: dict[str, tuple[str, tuple[str, ...]]] = {
    "unit_rate_below_floor": ("unit_rate", (
        "effective_committed_unit_rate", "list_unit_rate_used", "list_unit_rate_basis",
        "unit_rate_realization", "unit_rate_gap_to_floor_acv", "unit_rate_outside_ev_grid",
        "discount_pct")),
    "low_commit_share": ("commit_share", (
        "committed_acv", "booked_acv", "commit_share_of_booked", "uncommitted_booked_acv")),
    "overage_fence_breach": ("overage_fence", (
        "effective_committed_unit_rate", "overage_rate", "overage_premium", "committed_usage_acv")),
    "overage_below_list_unit_rate": ("overage_fence", (
        "overage_rate", "list_unit_rate_used", "list_unit_rate_basis")),
    "ramp_hidden_discount": ("ramp", _RAMP_COLS),
    "ramp_unapproved": ("ramp", _RAMP_COLS),
    "off_invoice_below_floor": ("waterfall", (
        "price_realization", "pocket_realization", "wf_ramp_concession_acv", "wf_credits_acv")),
}

SHARE_INSUFFICIENT_SENTENCE = ("Fewer than 15 scored won deals on this lever, so no share is "
                               "reported. The deals are listed below.")


def _py(v):
    """Plain python value; NaN and NA become None so rows serialize cleanly."""
    if v is None or v is pd.NA:
        return None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else float(v)
    return v


def _basis_clause(bases: set[str]) -> str:
    derived = "derived from list ACV over quantity on a fully committed deal"
    if bases == {"supplied"}:
        return "List unit rate supplied."
    if bases == {"derived"}:
        return f"List unit rate {derived}."
    return f"List unit rate supplied or {derived}."


def _deal_label(flag: str, row: pd.Series, ramp_in_file: bool = True,
                credits_in_file: bool = True) -> str | None:
    """Per-deal label, built only from that deal's own lens outputs."""
    if flag == "unit_rate_below_floor":
        text = LEVER_LABELS["unit_rate"] + " " + _basis_clause({str(row["list_unit_rate_basis"])})
        if bool(row["unit_rate_outside_ev_grid"]):
            text += " " + UNIT_RATE_GRID_NOTE
        return text
    if flag in ("ramp_hidden_discount", "ramp_unapproved"):
        return ("Ramp: dollars scheduled below steady-state ACV over the term, and the discount "
                "on a total-contract basis. Method: policy rule. "
                f"The steady-state discount is {float(row['discount_pct']):.1%}; counting the "
                f"ramp, it is {float(row['tcv_weighted_effective_discount']):.1%}.")
    if flag == "off_invoice_below_floor":
        text = LEVER_LABELS["waterfall"]
        # only a column absent from the file is excluded; a blank in a present column
        # is not_provided for the deal and gets no sentence (spec 7a.6)
        for name, present in (("ramp", ramp_in_file), ("credits", credits_in_file)):
            if not present:
                text += f" Excludes {name}: not in the file."
        return text
    if flag == "overage_below_list_unit_rate":
        return "Overage rate below the list unit rate. Method: policy rule."
    return None


def contract_structure_readout(deals: pd.DataFrame, *, n: int = 25,
                               policy_threshold: float = DEFAULT_POLICY_THRESHOLD) -> dict:
    """Won-deal readout: per-flag lists, trade check, coverage, deterministic sentences.

    The floor and ramp sentences format the floor_frac the flags were computed
    with (frame attrs); policy_threshold is used by the trade check only.
    Every entry carries method "policy rule". Lists are sorted as spec section 5
    states, ties broken by opportunity_id ascending. No LLM runs here.
    """
    params = deals.attrs.get("contract_structure", {})
    summary = contract_structure_summary(deals)
    won = _won_mask(deals)
    floor = float(params.get("floor_frac", DEFAULT_POLICY_THRESHOLD))
    # without attrs, infer column presence from the data: a scored step means its column exists
    ramp_in_file = bool(params["ramp_columns_in_file"]) if "ramp_columns_in_file" in params         else bool((deals["wf_ramp_step_status"] == SCORED).any())
    credits_in_file = bool(params["credits_column_in_file"]) if "credits_column_in_file" in params         else bool((deals["wf_credits_step_status"] == SCORED).any())

    def col(name: str) -> pd.Series:
        return deals[name] if name in deals.columns else pd.Series(np.nan, index=deals.index)

    def rows(mask: pd.Series, cols: tuple[str, ...], sort_key: pd.Series, ascending: bool,
             flag: str | None) -> tuple[int, list[dict]]:
        sub = deals.loc[mask].copy()
        sub["_k"] = pd.to_numeric(sort_key.loc[mask], errors="coerce")
        sub = sub.sort_values(["_k", "opportunity_id"], ascending=[ascending, True],
                              na_position="last", kind="mergesort")
        out = []
        for _, r in sub.head(n).iterrows():
            d = {c: (_py(r[c]) if c in sub.columns else None) for c in (*_COMMON, *cols)}
            if flag is not None:
                lab = _deal_label(flag, r, ramp_in_file, credits_in_file)
                if lab:
                    d["label"] = lab
            if flag == "off_invoice_below_floor":
                d["steps_contributing"] = [
                    s for s, c in (("ramp", "wf_ramp_concession_acv"), ("credits", "wf_credits_acv"))
                    if pd.notna(r[c]) and r[c] != 0]
            out.append(d)
        return int(mask.sum()), out

    sorts = {
        "unit_rate_below_floor": (col("unit_rate_gap_to_floor_acv"), False),
        "low_commit_share": (col("uncommitted_booked_acv"), False),
        "overage_fence_breach": (col("overage_premium"), True),
        "overage_below_list_unit_rate": (col("overage_rate") / col("list_unit_rate_used"), True),
        "ramp_hidden_discount": (col("ramp_concession_tcv"), False),
        "ramp_unapproved": (col("ramp_concession_tcv"), False),
        "off_invoice_below_floor": (col("booked_acv") - col("pocket_acv"), False),
    }
    flags = []
    for flag, (lever, cols) in _FLAG_SPECS.items():
        mask = won & deals[flag].fillna(False).astype(bool)
        key, asc = sorts[flag]
        total, lst = rows(mask, cols, key, asc, flag)
        label = LEVER_LABELS[lever].format(
            commit_share_floor=params.get("commit_share_floor", COMMIT_SHARE_FLOOR_DEFAULT))
        if flag == "unit_rate_below_floor":
            bases = set(deals.loc[mask, "list_unit_rate_basis"]) or {"supplied", "derived"}
            label += " " + _basis_clause(bases)
            if (mask & deals["unit_rate_outside_ev_grid"].fillna(False).astype(bool)).any():
                label += " " + UNIT_RATE_GRID_NOTE
        elif flag == "overage_below_list_unit_rate":
            label = "Overage rate below the list unit rate. Method: policy rule."
        elif flag == "off_invoice_below_floor":
            for step, present in (("ramp", ramp_in_file), ("credits", credits_in_file)):
                if not present:
                    label += f" Excludes {step}: not in the file."
        entry = {"flag": flag, "lever": lever, "method": METHOD, "label": label,
                 "total_flagged": total, "deals": lst, "truncated": total > len(lst)}
        sentence = _sentence(flag, summary, deals, mask, floor, total)
        if sentence:
            entry["sentence"] = sentence
        if summary[lever]["share_status"] == INSUFFICIENT:
            entry["share_note"] = SHARE_INSUFFICIENT_SENTENCE
        flags.append(entry)

    coverage = {}
    for lever in LEVERS:
        st = deals[f"{lever}_status"]
        by_reason = {}
        insuff = won & (st == INSUFFICIENT)
        for reason in sorted(deals.loc[insuff, f"{lever}_reason"].unique()):
            ids = deals.loc[insuff & (deals[f"{lever}_reason"] == reason), "opportunity_id"]
            by_reason[reason] = sorted(ids.astype(str))[:n]
        coverage[lever] = {
            "method": METHOD,
            "counts": {s: int((won & (st == s)).sum()) for s in (SCORED, INSUFFICIENT, NOT_PROVIDED)},
            "insufficient_data_ids": by_reason,
        }

    tmask = (won & (col("discount_pct") > policy_threshold)
             & deals["low_commit_share"].fillna(False).astype(bool))
    total, lst = rows(tmask, ("discount_pct", "discount_amount", "commit_share_of_booked",
                              "uncommitted_booked_acv"), col("discount_amount"), False, None)
    trade = {"flag": "trade_check", "method": METHOD,
             "label": ("Discount given without commitment bought: won deals over the policy "
                       "discount line with a commit share below the floor. Method: policy rule."),
             "total_flagged": total, "deals": lst, "truncated": total > len(lst)}
    return {"method": METHOD, "summary": summary, "flags": flags, "coverage": coverage,
            "trade_check": trade}


def _sentence(flag: str, summary: dict, deals: pd.DataFrame, mask: pd.Series,
              floor: float, total: int) -> str | None:
    if flag == "unit_rate_below_floor":
        d = summary["unit_rate"]
        return (f"{total} of {d['n_scored']} scored won usage deals sit below the "
                f"{floor:.0%} unit-rate floor, "
                f"${d['dollars']['unit_rate_gap_to_floor_acv']:,.0f} below floor in total. "
                "Method: policy rule.")
    if flag == "overage_fence_breach":
        return (f"{total} won deals carry an overage rate at or below their effective committed "
                "unit rate. Method: policy rule.")
    if flag == "ramp_hidden_discount":
        unapproved = int((mask & deals["ramp_unapproved"].fillna(False).astype(bool)).sum())
        return (f"{total} won deals pass the {floor:.0%} discount line at steady state "
                f"but exceed it once the ramp is counted; {unapproved} of them have no recorded "
                "approver. Method: policy rule.")
    return None
