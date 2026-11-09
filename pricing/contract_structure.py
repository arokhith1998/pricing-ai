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

The readout lists and the decision-record concession fields belong to PK-33.
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

    if "discount_pct" in df.columns:
        disc = _num(df, "discount_pct")
        pr = _num(df, "price_realization")
    else:  # direct-frame callers that skipped enrich: same formula, never written back
        pr = (booked / list_acv.replace(0, np.nan)).clip(upper=REALIZATION_SANITY_CAP)
        disc = (1.0 - pr).clip(upper=1.0).round(6)

    # --- shared checks --------------------------------------------------------
    def commit_checks(d: _Decide, *, with_c1_c2: bool) -> None:
        if with_c1_c2:
            d.add(is_seats, NOT_PROVIDED, "value_metric_seats")
            d.add(committed.isna(), NOT_PROVIDED, "committed_acv_blank")
        d.add(~vm_ok, INSUFFICIENT, "value_metric_unknown")
        d.add((committed < 0) | booked.isna() | (booked <= 0), INSUFFICIENT, "invalid_money_value")
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
    supplied = lur > 0
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
    commit_checks(d2, with_c1_c2=True)
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
    d5.add(list_acv.isna() | booked.isna() | (list_acv <= 0), INSUFFICIENT, "invalid_money_value")
    d5.add(s4 == INSUFFICIENT, INSUFFICIENT, "ramp_step_insufficient")
    d5.add(credits < 0, INSUFFICIENT, "invalid_money_value")
    d5.add(credits_present & (term.isna() | (term <= 0)), INSUFFICIENT, "term_months_missing")
    d5.add((s4 == NOT_PROVIDED) & ~credits_present, NOT_PROVIDED, "no_off_invoice_steps")
    d5.add(pocket_real > REALIZATION_SANITY_CAP, INSUFFICIENT, "pocket_realization_out_of_bounds")
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
    }
    return out


# --- book-level summary -----------------------------------------------------------

def _won_mask(deals: pd.DataFrame) -> pd.Series:
    if "is_won" in deals.columns:
        return deals["is_won"].fillna(False).astype(bool)
    if "outcome" in deals.columns:
        return deals["outcome"].astype(str) == "closed_won"
    return pd.Series(True, index=deals.index)


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
            "dollars": _lever_dollars(deals, lever, scored),
        }
    return result


def _lever_dollars(deals: pd.DataFrame, lever: str, scored: pd.Series) -> dict[str, float]:
    def flag(col: str) -> pd.Series:
        return scored & deals[col].fillna(False).astype(bool)

    if lever == "unit_rate":
        m = flag("unit_rate_below_floor")
        return {"unit_rate_gap_to_floor_acv": _sum(deals, "unit_rate_gap_to_floor_acv", m),
                "n_deals": int(m.sum())}
    if lever == "commit_share":
        m = flag("low_commit_share")
        return {"uncommitted_booked_acv": _sum(deals, "uncommitted_booked_acv", m),
                "n_deals": int(m.sum())}
    if lever == "overage_fence":
        # committed usage exposed to the fence breach, not a loss figure
        m = flag("overage_fence_breach")
        return {"committed_usage_acv_exposed": _sum(deals, "committed_usage_acv", m),
                "n_deals": int(m.sum())}
    if lever == "ramp":
        m = flag("ramp_hidden_discount")
        return {"ramp_concession_tcv_all_scored": _sum(deals, "ramp_concession_tcv", scored),
                "n_scored_deals": int(scored.sum()),
                "ramp_concession_tcv_hidden_discount": _sum(deals, "ramp_concession_tcv", m),
                "n_hidden_discount_deals": int(m.sum())}
    m = flag("off_invoice_below_floor")
    gap = (pd.to_numeric(deals.loc[m, "booked_acv"], errors="coerce")
           - pd.to_numeric(deals.loc[m, "pocket_acv"], errors="coerce")).sum()
    return {"wf_list_acv": _sum(deals, "wf_list_acv", scored),
            "wf_discount_acv": _sum(deals, "wf_discount_acv", scored),
            "wf_ramp_concession_acv": _sum(deals, "wf_ramp_concession_acv", scored),
            "wf_credits_acv": _sum(deals, "wf_credits_acv", scored),
            "n_scored_deals": int(scored.sum()),
            "booked_minus_pocket_acv_off_invoice_below_floor": round(float(gap), 2),
            "n_off_invoice_below_floor_deals": int(m.sum())}
