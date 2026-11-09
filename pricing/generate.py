"""Synthetic deal-dataset generator.

Produces a realistic CSV of closed B2B SaaS opportunities (won + lost) on
usage-based / hybrid pricing. Two jobs:

  1. De-risk the schema and power development before we have real data.
  2. Double as the outreach demo — so it must tell a *true and discoverable*
     leakage story, not random noise.

Deliberate signals baked in (the diagnostic should surface these):
  * Quarter-end discounting: discounts spike in the last ~3 weeks of a quarter.
  * Rep discipline variance: a few reps systematically over-discount.
  * Saturating win curve: win probability rises with discount then FLATTENS by
    ~a 10% discount, so deals discounted well beyond that win at about the same
    rate — the incremental discount bought no incremental win. That is leakage.
  * Governance gaps: some off-policy discounts have no recorded approver.
  * Messy identity: one account appears under several name spellings, and
    account_id is missing on a chunk of rows, forcing name-based resolution.

Reproducible via --seed. Nothing here uses customer data.

Contract-structure known answers (PK-31): generate_contract_fixture() and
generate_known_answer_cases() plant the spec section 6 cases on a separate
rng stream (seed + 3), opt-in, so generate() output is unchanged. They follow
the spec per-unit convention (quantity = committed units per year, hybrid
committed_acv includes the platform fee), which differs from generate()'s own
overage_rate and committed_acv conventions; see the comment block above
CONTRACT_FLOOR_FRAC.
"""

from __future__ import annotations

import argparse
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from pricing.schema import (
    ALL_COLUMNS, DEFAULT_POLICY_THRESHOLD, GENERATOR_COLUMNS, PROVENANCE_FIELDS,
    Outcome,
)

# --- segment economics -------------------------------------------------------
# (list_acv lognormal params in $, mix weight, base discount level)
SEGMENTS = {
    "SMB":        dict(weight=0.45, log_mean=9.4,  log_sd=0.45, base_disc=0.04),
    "MidMarket":  dict(weight=0.40, log_mean=11.0, log_sd=0.40, base_disc=0.10),
    "Enterprise": dict(weight=0.15, log_mean=12.4, log_sd=0.45, base_disc=0.17),
}
REGIONS = ["NA", "EMEA", "APAC"]
INDUSTRIES = ["DevTools", "Data/Analytics", "FinTech", "Infra/API",
              "MarTech", "Security", "Vertical SaaS"]
# Observable win-rate effects (logit offsets) — give the model real, learnable
# structure beyond the discount lever. These are deliberate signal, not noise.
INDUSTRY_WIN_EFFECT = {
    "DevTools": 0.45, "Data/Analytics": 0.20, "FinTech": -0.15,
    "Infra/API": 0.35, "MarTech": -0.30, "Security": 0.10,
    "Vertical SaaS": -0.35,
}
REGION_WIN_EFFECT = {"NA": 0.20, "EMEA": -0.05, "APAC": -0.25}
SEGMENT_WIN_EFFECT = {"SMB": 0.15, "MidMarket": 0.0, "Enterprise": -0.25}
TIERS = ["Starter", "Growth", "Scale", "Enterprise"]
# Optional hierarchy. Two levels populated (BU + line) so the diagnostic has
# something to slice; family/sku stay empty (engine skips dimensions with no
# spread).
BUSINESS_UNITS: dict[str, list[str]] = {
    "Cloud":    ["Compute", "Storage"],
    "Data":     ["Warehouse", "Streaming"],
    "Platform": ["Identity", "Observability"],
}
VALUE_METRICS = ["hybrid", "consumption", "seats"]
VALUE_METRIC_WEIGHTS = [0.55, 0.25, 0.20]  # ICP skews hybrid
LOST_REASONS = ["price", "product", "no_decision", "competitor", "timing"]

# Company-name building blocks for realistic, messy account names.
# A unique "core" identity = STEM + QUALIFIER (e.g. "Lumen Data"). Messy row
# variants only mutate case / punctuation / whitespace and append a *corporate
# form* suffix (Inc, LLC, ...). Identity resolution strips exactly those, so
# the core is recoverable — collisions are designed out, not hidden.
_NAME_STEMS = [
    "Acme", "Northwind", "Globex", "Initech", "Umbra", "Lumen", "Vertex",
    "Cobalt", "Meridian", "Halcyon", "Kestrel", "Onyx", "Pinnacle", "Aurora",
    "Catalyst", "Equinox", "Fathom", "Ironclad", "Juniper", "Lattice",
    "Monarch", "Nimbus", "Oasis", "Quartz", "Ridgeline", "Solstice",
    "Tessera", "Vantage", "Wavelength", "Zephyr",
]
_NAME_QUALIFIERS = ["", "Labs", "Data", "Technologies", "Systems",
                    "Software", "Cloud", "AI", "Networks", "Digital"]
# Corporate-form suffixes — appended at render time and stripped on ingest.
_LEGAL_SUFFIXES = ["", " Inc", " Inc.", ", Inc.", " LLC", " Corp.", " Co."]


def _quarter_end(d: date) -> date:
    q_end_month = ((d.month - 1) // 3) * 3 + 3
    if q_end_month == 12:
        return date(d.year, 12, 31)
    first_of_next = date(d.year, q_end_month + 1, 1)
    return first_of_next - timedelta(days=1)


def _quarter_end_pressure(close: date) -> float:
    """0..1 ramp over the final ~21 days of the quarter."""
    days_to_qe = (_quarter_end(close) - close).days
    if days_to_qe < 0:
        return 0.0
    return float(max(0.0, 1.0 - days_to_qe / 21.0))


def _build_account_cores(rng: np.random.Generator, n_accounts: int) -> list[str]:
    """Return `n_accounts` unique canonical account names (stem + qualifier)."""
    combos = [f"{s} {q}".strip() for s in _NAME_STEMS for q in _NAME_QUALIFIERS]
    rng.shuffle(combos)
    return combos[:n_accounts]


def _messy_name(rng: np.random.Generator, core: str) -> str:
    """Render one messy CRM-style variant of an account's canonical core."""
    name = core + rng.choice(_LEGAL_SUFFIXES)
    roll = rng.random()
    if roll < 0.12:
        name = name.upper()
    elif roll < 0.20:
        name = name.lower()
    if rng.random() < 0.10:  # stray whitespace
        name = "  " + name + " "
    return name


def _add_ubp_cost_columns(df: pd.DataFrame, seed: int) -> None:
    """Populate the OPTIONAL UBP-structure + cost columns, in place.

    Drawn from an INDEPENDENT rng stream (seed + 2) so these never perturb the
    main generator sequence — same rule as the hierarchy fields, so the pinned
    dataset / model tests stay stable. These add expressible UBP shape and a
    cost column, not new leakage signal; the diagnostic does not read them yet.
    Applicability mirrors the value metric: commit/overage only where there is
    usage, ramp only on multi-year deals.
    """
    rng = np.random.default_rng(seed + 2)
    n = len(df)
    booked = df["booked_acv"].to_numpy(dtype=float)
    usage = df["usage_acv"].to_numpy(dtype=float)
    qty = df["quantity"].to_numpy(dtype=float)
    vm = df["value_metric"].to_numpy()
    term = df["term_months"].to_numpy(dtype=float)

    is_usage = np.isin(vm, ["consumption", "hybrid"])
    has_usage = is_usage & (usage > 0) & (qty > 0)
    multiyear = term >= 24

    # Committed annual spend floor (usage-based & hybrid only).
    commit = np.round(booked * rng.uniform(0.55, 0.90, n), 2)
    committed_acv = np.where(is_usage, commit, np.nan)

    # Overage = the effective committed unit rate, marked up for on-demand.
    unit_rate = np.divide(usage, qty, out=np.zeros(n), where=qty > 0)
    overage = np.round(unit_rate * rng.uniform(1.1, 1.6, n), 2)
    overage_rate = np.where(has_usage, overage, np.nan)

    # Two-year ramp on multi-year deals, climbing TO the steady-state booked
    # figure (schema.py documents year 3+ == booked_acv): year 1 well below,
    # year 2 closer but still at or under it, never above (2026-09-27 fix --
    # year 2 used to draw 1.00-1.25x booked, contradicting that convention).
    # [0.60, 0.80) and [0.80, 1.00] are disjoint except at the shared
    # boundary, so year 1 < year 2 <= booked_acv holds on every draw. Same
    # two rng.uniform(..., n) calls in the same order as before, so no other
    # draw in this stream shifts.
    y1 = np.round(booked * rng.uniform(0.60, 0.80, n), 2)
    y2 = np.round(booked * rng.uniform(0.80, 1.00, n), 2)
    ramp_year_1_acv = np.where(multiyear, y1, np.nan)
    ramp_year_2_acv = np.where(multiyear, y2, np.nan)

    # ~22% renewals, each with a modest uplift over the prior term.
    renewal = rng.random(n) < 0.22
    uplift = np.round(rng.uniform(0.03, 0.12, n), 3)
    renewal_uplift = np.where(renewal, uplift, np.nan)

    # COGS share is highest for consumption (infra cost), lowest for seats.
    cogs_frac = np.select(
        [vm == "consumption", vm == "hybrid"],
        [rng.uniform(0.22, 0.38, n), rng.uniform(0.15, 0.28, n)],
        default=rng.uniform(0.08, 0.18, n),  # seats
    )
    cogs_acv = np.round(booked * cogs_frac, 2)

    df["committed_acv"] = committed_acv
    df["overage_rate"] = overage_rate
    df["ramp_year_1_acv"] = ramp_year_1_acv
    df["ramp_year_2_acv"] = ramp_year_2_acv
    df["is_renewal"] = np.where(renewal, "true", "false")
    df["renewal_uplift"] = renewal_uplift
    df["cogs_acv"] = cogs_acv


def generate(n: int = 2000, seed: int = 7,
             start: date = date(2024, 7, 1),
             end: date = date(2025, 6, 30)) -> pd.DataFrame:
    """Generate `n` closed opportunities between `start` and `end`."""
    rng = np.random.default_rng(seed)
    # Independent stream for OPTIONAL hierarchy fields so adding/removing them
    # never shifts the main RNG sequence (keeps the pinned dataset + model
    # tests stable).
    rng_hier = np.random.default_rng(seed + 1)

    # A pool of accounts (fewer than deals → repeat business → identity work).
    max_cores = len(_NAME_STEMS) * len(_NAME_QUALIFIERS)
    n_accounts = min(max(40, n // 6), max_cores)
    acct_cores = _build_account_cores(rng, n_accounts)
    acct_ids = [f"ACC-{i:04d}" for i in range(n_accounts)]
    # Each account keeps ONE canonical id, but rows render the name messily and
    # drop the id ~35% of the time.
    acct_for_deal = rng.integers(0, n_accounts, size=n)

    # Reps, with per-rep discount discipline (positive = over-discounts).
    n_reps = 12
    rep_ids = [f"REP-{i:02d}" for i in range(n_reps)]
    rep_bias = rng.normal(0.0, 0.035, size=n_reps)
    rep_bias[1] += 0.06   # two reps are notably loose
    rep_bias[7] += 0.05
    rep_bias[4] -= 0.03   # one is disciplined
    rep_for_deal = rng.integers(0, n_reps, size=n)

    seg_names = list(SEGMENTS)
    seg_weights = np.array([SEGMENTS[s]["weight"] for s in seg_names])
    seg_weights /= seg_weights.sum()

    span_days = (end - start).days
    rows = []
    for i in range(n):
        seg = rng.choice(seg_names, p=seg_weights)
        s = SEGMENTS[seg]

        close = start + timedelta(days=int(rng.integers(0, span_days + 1)))
        cycle = int(np.clip(rng.normal(55 if seg != "Enterprise" else 95, 25), 7, 240))
        created = close - timedelta(days=cycle)

        list_acv = float(np.round(rng.lognormal(s["log_mean"], s["log_sd"]), 2))
        list_acv = float(np.clip(list_acv, 3000, 1_200_000))

        competitor = bool(rng.random() < 0.42)
        qe = _quarter_end_pressure(close)
        rep_idx = rep_for_deal[i]
        region = rng.choice(REGIONS, p=[0.55, 0.30, 0.15])
        industry = rng.choice(INDUSTRIES)

        # --- discount model ------------------------------------------------
        disc = (s["base_disc"]
                + 0.06 * competitor
                + 0.10 * qe                       # quarter-end leakage driver
                + rep_bias[rep_idx]
                + rng.normal(0, 0.035))
        disc = float(np.clip(disc, 0.0, 0.45))

        # --- win model: SATURATING in discount ----------------------------
        # Observable structure (segment/region/industry) + competitor drag +
        # discount with sharply diminishing returns + a smaller latent
        # "quality" term (irreducible noise). The discount lift is ~maxed by a
        # ~10% discount, so deals discounted beyond that win at about the same
        # rate — extra discount bought ~no incremental p(win). That is leakage.
        quality = rng.normal(0, 1)
        disc_lift = 1.3 * np.tanh(disc / 0.05)     # ~saturated by ~0.10
        logit = (-0.55
                 + 0.55 * quality                  # latent, unobserved noise
                 - 0.8 * competitor
                 + disc_lift
                 + SEGMENT_WIN_EFFECT[seg]
                 + REGION_WIN_EFFECT[region]
                 + INDUSTRY_WIN_EFFECT[industry]
                 - 0.12 * (np.log(list_acv) - 10.8))  # bigger deals slightly harder
        p_win = 1.0 / (1.0 + np.exp(-logit))
        won = bool(rng.random() < p_win)

        booked_acv = float(np.round(list_acv * (1.0 - disc), 2))

        vm = rng.choice(VALUE_METRICS, p=VALUE_METRIC_WEIGHTS)
        if vm == "hybrid":
            plat_share = float(np.clip(rng.normal(0.45, 0.12), 0.15, 0.8))
            platform_fee = round(booked_acv * plat_share, 2)
            usage = round(booked_acv - platform_fee, 2)
        elif vm == "consumption":
            platform_fee, usage = 0.0, booked_acv
        else:  # seats
            platform_fee, usage = booked_acv, 0.0

        # quantity: seats vs usage units
        if vm == "seats":
            quantity = float(int(np.clip(list_acv / rng.uniform(800, 2500), 1, 5000)))
        else:
            quantity = float(np.round(list_acv / rng.uniform(0.5, 25), 0))

        # governance: approver recorded for most off-policy discounts, but a
        # deliberate ~25% gap (off-policy with no approval = leakage signal).
        approved_by = ""
        if disc > DEFAULT_POLICY_THRESHOLD and rng.random() < 0.75:
            approved_by = f"MGR-{rng.integers(0, 5):02d}"

        # lost_reason: "price" more likely when discount was low
        lost_reason = ""
        if not won:
            if disc < 0.10:
                probs = [0.45, 0.18, 0.15, 0.14, 0.08]
            else:
                probs = [0.18, 0.27, 0.20, 0.22, 0.13]
            lost_reason = rng.choice(LOST_REASONS, p=probs)

        acct = acct_for_deal[i]
        account_id = acct_ids[acct] if rng.random() > 0.35 else ""

        bu = rng_hier.choice(list(BUSINESS_UNITS))
        line = rng_hier.choice(BUSINESS_UNITS[bu])

        rows.append({
            "opportunity_id": f"OPP-{i:05d}",
            "account_id": account_id,
            "account_name": _messy_name(rng, acct_cores[acct]),
            "outcome": (Outcome.WON if won else Outcome.LOST).value,
            "created_date": created.isoformat(),
            "close_date": close.isoformat(),
            "segment": seg,
            "region": region,
            "industry": industry,
            "business_unit": bu,
            "product_line": line,
            "product_family": "",
            "product_tier": rng.choice(TIERS, p=[0.30, 0.34, 0.24, 0.12]),
            "sku": "",
            "value_metric": vm,
            "list_acv": list_acv,
            "booked_acv": booked_acv,
            "platform_fee_acv": platform_fee,
            "usage_acv": usage,
            "term_months": int(rng.choice([12, 12, 12, 24, 36])),
            "quantity": quantity,
            "rep_id": rep_ids[rep_idx],
            "approved_by": approved_by,
            "competitor_present": str(competitor).lower(),
            "lost_reason": lost_reason,
        })

    df = pd.DataFrame(rows, columns=GENERATOR_COLUMNS)
    # Synthetic deals are all USD; a constant assignment consumes no RNG draws
    # so it cannot perturb the main sequence (same rule as the optional
    # hierarchy/UBP columns above).
    df["currency"] = "USD"
    _add_ubp_cost_columns(df, seed)
    return df


# =============================================================================
# Contract-structure planted stream (PK-31)
# =============================================================================
# Spec: docs/design/2026-11-07-contract-structure-lens-spec.md, sections 2, 3, 6.
#
# NOTHING below is called by generate(). The planted population lives on its
# own stream, np.random.default_rng(seed + 3), and is opt-in, so
# generate(n=2000, seed=7) stays byte-identical (mechanism (a) in the task).
#
# Convention difference, on purpose. generate() predates the contract-structure
# lens and uses these conventions, which the spec does not:
#   * overage_rate = (usage_acv / quantity) * U(1.1, 1.6), where quantity is
#     list_acv / U(0.5, 25) and is NOT a committed-unit count;
#   * committed_acv = booked_acv * U(0.55, 0.90), a share of a booked figure
#     that includes the platform fee on hybrid deals, with no check that the
#     commitment exceeds the fee (committed usage can be <= 0);
#   * no list_unit_rate and no credits_tcv (they are not in GENERATOR_COLUMNS).
# The planted stream follows the spec per-unit convention instead: quantity is
# committed units per year, committed_acv on a hybrid deal includes the
# platform fee, effective_committed_unit_rate = (committed_acv - platform_fee)
# / quantity, overage_rate is priced in the same unit, and list_unit_rate is
# the list price per that unit. The existing streams are not touched.
#
# No cost input is read or written: cogs_acv is emitted blank on planted deals.

CONTRACT_FLOOR_FRAC = DEFAULT_POLICY_THRESHOLD
CONTRACT_COMMIT_SHARE_FLOOR = 0.50
CONTRACT_FULL_COMMIT_TOLERANCE = 0.005
CONTRACT_STEADY_STATE_TOLERANCE = 0.005
CONTRACT_REALIZATION_SANITY_CAP = 1.5
CONTRACT_EV_GRID_MAX_FRAC = 0.40

# (field, kind) per lever, kind: d = dollars (2 dp), r = ratio or unit rate
# (6 dp), s = string, b = boolean. Order is the order of the key columns.
LEVER_OUTPUTS: dict[str, list[tuple[str, str]]] = {
    "unit_rate": [
        ("committed_usage_acv", "d"), ("effective_committed_unit_rate", "r"),
        ("list_unit_rate_used", "r"), ("list_unit_rate_basis", "s"),
        ("unit_rate_realization", "r"), ("unit_rate_discount", "r"),
        ("unit_rate_floor", "r"), ("unit_rate_below_floor", "b"),
        ("unit_rate_gap_to_floor_acv", "d"), ("unit_rate_outside_ev_grid", "b"),
    ],
    "commit_share": [
        ("commit_share_of_booked", "r"), ("uncommitted_booked_acv", "d"),
        ("low_commit_share", "b"),
    ],
    "overage_fence": [
        ("overage_premium", "r"), ("overage_fence_breach", "b"),
        ("overage_below_list_unit_rate", "b"),
    ],
    "ramp": [
        ("ramp_depth_year_1", "r"), ("ramp_depth_year_2", "r"),
        ("ramp_concession_tcv", "d"), ("ramp_concession_pct_of_booked_tcv", "r"),
        ("contracted_tcv", "d"), ("list_tcv", "d"),
        ("tcv_weighted_effective_discount", "r"),
        ("ramp_discount_increment", "r"), ("ramp_hidden_discount", "b"),
        ("ramp_unapproved", "b"),
    ],
    "waterfall": [
        ("wf_list_acv", "d"), ("wf_discount_acv", "d"),
        ("wf_ramp_concession_acv", "d"), ("wf_credits_acv", "d"),
        ("pocket_acv", "d"), ("pocket_realization", "r"),
        ("wf_ramp_step_status", "s"), ("wf_credits_step_status", "s"),
        ("off_invoice_below_floor", "b"),
    ],
}
LEVERS = list(LEVER_OUTPUTS)
KEY_COLUMNS: list[str] = (
    ["case_id", "opportunity_id", "won", "lever", "state", "reason"]
    + [f for lv in LEVERS for f, _ in LEVER_OUTPUTS[lv]]
)
# Flag name -> (lever, output field). Used to build the bulk answer key.
CONTRACT_FLAGS: dict[str, tuple[str, str]] = {
    "unit_rate_below_floor": ("unit_rate", "unit_rate_below_floor"),
    "unit_rate_outside_ev_grid": ("unit_rate", "unit_rate_outside_ev_grid"),
    "low_commit_share": ("commit_share", "low_commit_share"),
    "overage_fence_breach": ("overage_fence", "overage_fence_breach"),
    "overage_below_list_unit_rate": ("overage_fence", "overage_below_list_unit_rate"),
    "ramp_hidden_discount": ("ramp", "ramp_hidden_discount"),
    "ramp_unapproved": ("ramp", "ramp_unapproved"),
    "off_invoice_below_floor": ("waterfall", "off_invoice_below_floor"),
}

# Every field the planted frames carry: the canonical order, minus provenance
# (not generated) and including list_unit_rate and credits_tcv.
CONTRACT_COLUMNS: list[str] = [c for c in ALL_COLUMNS if c not in PROVENANCE_FIELDS]


def _blank(x) -> bool:
    if x is None:
        return True
    if isinstance(x, str):
        return x.strip().lower() in ("", "nan", "none", "null", "na")
    try:
        return bool(pd.isna(x))   # NaN, None, pd.NA, NaT
    except (TypeError, ValueError):
        return False


def _num(x):
    return None if _blank(x) else float(x)


def _r6(x: float) -> float:
    return round(x, 6)


def _contract_expected_levers(
    row: dict, *, floor_frac: float = CONTRACT_FLOOR_FRAC,
    commit_share_floor: float = CONTRACT_COMMIT_SHARE_FLOOR,
    ramp_columns_present: bool = True,
) -> dict[str, dict]:
    """The reference answer for one deal: spec section 3, written out directly.

    FIXTURE ORACLE ONLY. This is the oracle behind the known-answer key. It is
    NOT the lens (that is PK-32, pricing/contract_structure.py) and the lens
    must never import it or pricing.generate: a lens that borrowed its own
    answer key would test nothing. It is an independent, scalar
    transcription of the spec formulas so the key is derived from the planted
    inputs rather than from design intent. Returns, per lever, a dict with
    `status`, `reason` and the lever's output fields (None where the spec says
    NaN or NA).
    """
    vm = None if _blank(row.get("value_metric")) else str(row["value_metric"]).strip().lower()
    list_acv, booked = _num(row.get("list_acv")), _num(row.get("booked_acv"))
    committed, qty = _num(row.get("committed_acv")), _num(row.get("quantity"))
    fee, lu = _num(row.get("platform_fee_acv")), _num(row.get("list_unit_rate"))
    ovg, term = _num(row.get("overage_rate")), _num(row.get("term_months"))
    y1, y2 = _num(row.get("ramp_year_1_acv")), _num(row.get("ramp_year_2_acv"))
    credits = _num(row.get("credits_tcv"))
    approved = not _blank(row.get("approved_by"))
    tol = CONTRACT_STEADY_STATE_TOLERANCE
    cap = CONTRACT_REALIZATION_SANITY_CAP
    floor_real = _r6(1 - floor_frac)

    discount_pct = price_real = None
    if list_acv and list_acv > 0 and booked is not None:
        discount_pct = _r6(1 - booked / list_acv)
        price_real = _r6(booked / list_acv)

    def blank_out(lever: str) -> dict:
        d = {f: None for f, _ in LEVER_OUTPUTS[lever]}
        d.update(status="", reason="")
        return d

    def fail(lever: str, status: str, reason: str) -> dict:
        d = blank_out(lever)
        d.update(status=status, reason=reason)
        return d

    def commit_checks():
        if vm == "seats":
            return "not_provided", "value_metric_seats"
        if committed is None:
            return "not_provided", "committed_acv_blank"
        if vm not in ("consumption", "hybrid"):
            return "insufficient_data", "value_metric_unknown"
        if committed < 0 or booked is None or booked <= 0:
            return "insufficient_data", "invalid_money_value"
        if committed > booked * (1 + tol):
            return "insufficient_data", "commit_exceeds_booked"
        return None

    # Shared derived values: only when commit_checks and rate_checks pass.
    cc = commit_checks()
    rc = None
    cu = eff = None
    if cc is None:
        if qty is None or qty <= 0:
            rc = ("insufficient_data", "quantity_missing_or_zero")
        elif vm == "hybrid" and fee is None:
            rc = ("insufficient_data", "platform_fee_missing_for_hybrid")
        else:
            cu = committed - fee if vm == "hybrid" else committed
            if cu <= 0:
                rc = ("insufficient_data", "usage_commit_not_positive")
                cu = None
            else:
                eff = cu / qty

    # List unit rate used (lever 1 and the lever 3 list flag).
    list_used, basis = None, "unavailable"
    if lu is not None and lu > 0:
        list_used, basis = lu, "supplied"
    elif (vm == "consumption" and committed is not None and booked is not None
          and qty is not None and qty > 0 and list_acv is not None
          and list_acv > 0
          and abs(committed - booked) <= CONTRACT_FULL_COMMIT_TOLERANCE * booked):
        list_used, basis = list_acv / qty, "derived"

    out: dict[str, dict] = {}

    # --- lever 1: unit rate ---------------------------------------------------
    # list_unit_rate_used and its basis are populated whenever the rate is
    # supplied or derivable, regardless of status; basis is never blank.
    if cc is not None or rc is not None:
        d = fail("unit_rate", *(cc or rc))
        d.update(list_unit_rate_used=list_used, list_unit_rate_basis=basis)
        out["unit_rate"] = d
    else:
        d = blank_out("unit_rate")
        d.update(committed_usage_acv=cu, effective_committed_unit_rate=eff,
                 list_unit_rate_basis=basis, list_unit_rate_used=list_used)
        if list_used is None:
            d.update(status="insufficient_data", reason="list_unit_rate_unavailable")
        else:
            real = _r6(eff / list_used)
            if real > cap:
                d.update(status="insufficient_data",
                         reason="unit_rate_realization_out_of_bounds")
            else:
                floor_rate = list_used * (1 - floor_frac)
                d.update(
                    status="scored", reason="", unit_rate_realization=real,
                    unit_rate_discount=_r6(1 - real), unit_rate_floor=floor_rate,
                    unit_rate_below_floor=real < floor_real,
                    unit_rate_gap_to_floor_acv=max(floor_rate - eff, 0.0) * qty,
                    unit_rate_outside_ev_grid=_r6(1 - real) > CONTRACT_EV_GRID_MAX_FRAC)
        out["unit_rate"] = d

    # --- lever 2: commit share ------------------------------------------------
    if cc is not None:
        out["commit_share"] = fail("commit_share", *cc)
    else:
        share = _r6(committed / booked)
        d = blank_out("commit_share")
        d.update(status="scored", reason="", commit_share_of_booked=share,
                 uncommitted_booked_acv=booked - committed,
                 low_commit_share=share < commit_share_floor)
        out["commit_share"] = d

    # --- lever 3: overage fence -----------------------------------------------
    if vm == "seats":
        out["overage_fence"] = fail("overage_fence", "not_provided", "value_metric_seats")
    elif ovg is None:
        out["overage_fence"] = fail("overage_fence", "not_provided", "overage_rate_blank")
    elif committed is None:
        out["overage_fence"] = fail("overage_fence", "not_provided", "no_commitment")
    elif ovg < 0:
        out["overage_fence"] = fail("overage_fence", "insufficient_data", "invalid_money_value")
    elif cc is not None:
        out["overage_fence"] = fail("overage_fence", *cc)
    elif rc is not None:
        out["overage_fence"] = fail("overage_fence", *rc)
    else:
        prem = _r6(ovg / eff - 1)
        d = blank_out("overage_fence")
        d.update(status="scored", reason="", overage_premium=prem,
                 overage_fence_breach=prem <= 0,
                 overage_below_list_unit_rate=(
                     ovg < list_used if basis != "unavailable" else None))
        out["overage_fence"] = d

    # --- lever 4: ramp ----------------------------------------------------------
    ramp_acv = None
    ramp_scored = False
    if y1 is None and y2 is None:
        out["ramp"] = fail("ramp", "not_provided", "no_ramp_recorded")
    elif list_acv is None or booked is None or list_acv <= 0 or booked <= 0:
        out["ramp"] = fail("ramp", "insufficient_data", "invalid_money_value")
    elif term is None or term <= 0:
        out["ramp"] = fail("ramp", "insufficient_data", "term_months_missing")
    elif term <= 12:
        out["ramp"] = fail("ramp", "insufficient_data", "ramp_on_single_year_term")
    elif y1 is None:
        out["ramp"] = fail("ramp", "insufficient_data", "ramp_year_1_missing")
    elif y2 is None:
        out["ramp"] = fail("ramp", "insufficient_data", "ramp_year_2_missing")
    elif y1 < 0 or y2 < 0:
        out["ramp"] = fail("ramp", "insufficient_data", "invalid_money_value")
    elif max(y1, y2) > booked * (1 + tol):
        out["ramp"] = fail("ramp", "insufficient_data", "ramp_above_steady_state")
    else:
        ty = term / 12
        w1 = min(term, 12) / 12
        w2 = min(max(term - 12, 0), 12) / 12
        concession = w1 * (booked - y1) + w2 * (booked - y2)
        steady = booked * ty
        contracted = steady - concession
        list_tcv = list_acv * ty
        eff_disc = _r6(1 - contracted / list_tcv)
        hidden = (discount_pct <= floor_frac) and (eff_disc > floor_frac)
        d = blank_out("ramp")
        d.update(
            status="scored", reason="",
            ramp_depth_year_1=_r6(1 - y1 / booked),
            ramp_depth_year_2=_r6(1 - y2 / booked),
            ramp_concession_tcv=concession,
            ramp_concession_pct_of_booked_tcv=_r6(concession / steady),
            contracted_tcv=contracted, list_tcv=list_tcv,
            tcv_weighted_effective_discount=eff_disc,
            ramp_discount_increment=_r6(eff_disc - discount_pct),
            ramp_hidden_discount=hidden,
            ramp_unapproved=hidden and not approved)
        out["ramp"] = d
        ramp_scored = True
        ramp_acv = concession / ty

    # --- lever 5: waterfall -----------------------------------------------------
    ramp_state = out["ramp"]["status"]
    if list_acv is None or booked is None or list_acv <= 0:
        out["waterfall"] = fail("waterfall", "insufficient_data", "invalid_money_value")
    elif ramp_state == "insufficient_data":
        out["waterfall"] = fail("waterfall", "insufficient_data", "ramp_step_insufficient")
    elif credits is not None and credits < 0:
        out["waterfall"] = fail("waterfall", "insufficient_data", "invalid_money_value")
    elif credits is not None and (term is None or term <= 0):
        out["waterfall"] = fail("waterfall", "insufficient_data", "term_months_missing")
    elif ramp_state == "not_provided" and credits is None:
        out["waterfall"] = fail("waterfall", "not_provided", "no_off_invoice_steps")
    else:
        credits_acv = credits / (term / 12) if credits is not None else None
        if ramp_scored:
            ramp_step, ramp_status = ramp_acv, "scored"
        elif ramp_columns_present:
            ramp_step, ramp_status = 0.0, "scored"
        else:
            ramp_step, ramp_status = None, "not_provided"
        pocket = booked - (ramp_step or 0.0) - (credits_acv or 0.0)
        pocket_real = _r6(pocket / list_acv)
        d = blank_out("waterfall")
        if pocket_real > cap:
            d.update(status="insufficient_data", reason="pocket_realization_out_of_bounds")
        else:
            d.update(
                status="scored", reason="", wf_list_acv=list_acv,
                wf_discount_acv=list_acv - booked, wf_ramp_concession_acv=ramp_step,
                wf_credits_acv=credits_acv, pocket_acv=pocket,
                pocket_realization=pocket_real, wf_ramp_step_status=ramp_status,
                wf_credits_step_status="scored" if credits is not None else "not_provided",
                off_invoice_below_floor=(price_real >= floor_real
                                         and pocket_real < floor_real))
        out["waterfall"] = d
    return out


def _fmt(value, kind: str) -> str:
    if value is None:
        return ""
    if kind == "b":
        return "true" if value else "false"
    if kind == "d":
        return f"{float(value) + 0.0:.2f}"
    if kind == "r":
        return f"{float(value) + 0.0:.6f}"
    return str(value)


def known_answer_key(deals: pd.DataFrame, case_ids: dict[str, str] | None = None,
                     *, ramp_columns_present: bool = True) -> pd.DataFrame:
    """Long-form answer key: one row per (deal, lever), all text.

    Dollars are formatted at 2 dp and ratios at 6 dp (the spec rounding), flags
    as true / false, and NA or NaN as an empty string. `case_ids` maps
    opportunity_id to its spec case id (KA-nn); other deals get an empty one.
    """
    case_ids = case_ids or {}
    rows = []
    for rec in deals.to_dict("records"):
        res = _contract_expected_levers(rec, ramp_columns_present=ramp_columns_present)
        won = str(rec["outcome"]) == Outcome.WON.value
        for lever in LEVERS:
            r = res[lever]
            row = {c: "" for c in KEY_COLUMNS}
            row.update(case_id=case_ids.get(rec["opportunity_id"], ""),
                       opportunity_id=rec["opportunity_id"],
                       won="true" if won else "false", lever=lever,
                       state=r["status"], reason=r["reason"])
            for f, kind in LEVER_OUTPUTS[lever]:
                row[f] = _fmt(r[f], kind)
            rows.append(row)
    return pd.DataFrame(rows, columns=KEY_COLUMNS)


# --- hand-built known-answer cases (spec section 6.1) -------------------------
# (id, value_metric, outcome, list_acv, booked_acv, committed_acv, quantity,
#  platform_fee_acv, list_unit_rate, overage_rate, term_months, ramp_y1,
#  ramp_y2, credits_tcv). None is a blank cell. The spec table has no KA-15,
# KA-16 or KA-23; the numbering is kept so ids match the spec.
_W, _L = Outcome.WON.value, Outcome.LOST.value
KNOWN_ANSWER_CASES: list[tuple] = [
    ("KA-01", "consumption", _W, 100000, 85000, 85000, 100000, None, None, 1.10, 12, None, None, None),
    ("KA-02", "consumption", _W, 200000, 160000, 120000, 200000, None, 1.00, 0.70, 12, None, None, None),
    ("KA-03", "consumption", _W, 100000, 90000, 60000, 75000, None, 1.00, 0.80, 12, None, None, None),
    ("KA-04", "consumption", _W, 120000, 102000, 90000, 100000, None, None, 0.75, 12, None, None, None),
    ("KA-05", "consumption", _W, 100000, 80000, 30000, 40000, None, 1.00, 1.20, 12, None, None, None),
    ("KA-06", "consumption", _W, 100000, 90000, 90000, 0, None, None, 1.00, 12, None, None, None),
    ("KA-07", "hybrid", _W, 150000, 120000, 100000, 100000, 50000, 0.80, 0.40, 12, None, None, None),
    ("KA-08", "hybrid", _W, 150000, 120000, 100000, 100000, None, 0.80, 0.40, 12, None, None, None),
    ("KA-09", "seats", _W, 100000, 90000, None, 100, None, None, None, 12, None, None, None),
    ("KA-10", "seats", _W, 100000, 90000, None, 100, None, None, None, 36, 60000, 80000, None),
    ("KA-11", "seats", _W, 100000, 88000, None, 100, None, None, None, 36, 88000, 88000, None),
    ("KA-12", "seats", _W, 100000, 90000, None, 100, None, None, None, 36, 70000, None, None),
    ("KA-13", "seats", _W, 100000, 100000, None, 100, None, None, None, 18, 50000, 90000, None),
    ("KA-14", "seats", _W, 100000, 90000, None, 100, None, None, None, 24, None, None, 20000),
    ("KA-17", "consumption", _W, 100000, 60000, 50000, 50000, None, 2.00, None, 12, None, None, None),
    ("KA-18", "consumption", _W, 105000, 110000, 110000, 100000, None, 1.00, 1.30, 12, None, None, None),
    ("KA-19", "consumption", _W, 50000, 50000, 50000, 50000, None, None, 0, 12, None, None, None),
    ("KA-20", "consumption", _W, 100000, 90000, None, 100000, None, None, 1.20, 12, None, None, None),
    ("KA-21", "consumption", _W, 100000, 100000, 110000, 100000, None, None, 1.20, 12, None, None, None),
    ("KA-22", "consumption", _L, 120000, 102000, 90000, 100000, None, None, 0.75, 12, None, None, None),
    ("KA-24", "seats", _W, 100000, 90000, None, 100, None, None, None, 36, 95000, 90000, None),
    ("KA-25", "seats", _W, 100000, 90000, None, 100, None, None, None, 12, 70000, 80000, None),
    ("KA-26", "seats", _W, 100000, 90000, None, 100, None, None, None, None, None, None, 5000),
]


def _nan_if_none(x):
    return np.nan if x is None else x


def _finish_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=CONTRACT_COLUMNS)
    df["term_months"] = df["term_months"].astype("Int64")
    return df


def generate_known_answer_cases() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The 23 hand-built spec section 6.1 cases as (deals, answer key).

    Deterministic, no RNG. Every case is MidMarket, USD, with the ramp columns
    present in the frame. opportunity_id is the spec case id.
    """
    rows = []
    for i, (cid, vm, outcome, lst, bkd, com, qty, fee, lu, ovg, term,
            y1, y2, cr) in enumerate(KNOWN_ANSWER_CASES):
        r = {c: "" for c in CONTRACT_COLUMNS}
        for c in ("usage_acv", "renewal_uplift", "cogs_acv"):
            r[c] = np.nan
        close = date(2025, 1, 6) + timedelta(days=i)
        r.update(
            opportunity_id=cid, account_id=f"ACC-KA{i:02d}",
            account_name=f"Known Answer {_NAME_STEMS[i]} Labs", outcome=outcome,
            created_date=(close - timedelta(days=45)).isoformat(),
            close_date=close.isoformat(), segment="MidMarket", region="NA",
            industry="DevTools", product_tier="Growth", value_metric=vm,
            list_acv=lst, booked_acv=bkd, platform_fee_acv=_nan_if_none(fee),
            term_months=_nan_if_none(term), quantity=qty, rep_id="REP-00",
            approved_by="", competitor_present="false",
            lost_reason="price" if outcome == _L else "", currency="USD",
            committed_acv=_nan_if_none(com), overage_rate=_nan_if_none(ovg),
            ramp_year_1_acv=_nan_if_none(y1), ramp_year_2_acv=_nan_if_none(y2),
            list_unit_rate=_nan_if_none(lu), credits_tcv=_nan_if_none(cr),
            is_renewal="false")
        rows.append(r)
    deals = _finish_frame(rows)
    ids = {cid: cid for cid, *_ in KNOWN_ANSWER_CASES}
    return deals, known_answer_key(deals, ids)


# --- planted bulk population (spec section 6.2) ---------------------------------
_CORES = [f"{s} {q}".strip() for s in _NAME_STEMS for q in _NAME_QUALIFIERS]

# (kind, count, vm pattern, won). Pattern: alt = consumption/hybrid
# alternating, cycle = seats/consumption/hybrid, or one fixed value metric.
_PLANTED_KINDS: list[tuple[str, int, str, bool]] = [
    ("overage_equal", 20, "alt", True),
    ("overage_below", 20, "alt", True),
    ("unit_floor", 25, "alt", True),
    ("low_commit", 20, "alt", True),
    ("ramp_hidden", 30, "cycle", True),
    ("credits_only", 15, "cycle", True),
    ("quantity_missing_or_zero", 10, "alt", True),
    ("platform_fee_missing_for_hybrid", 10, "hybrid", True),
    ("list_unit_rate_unavailable", 10, "alt", True),
    ("commit_exceeds_booked", 10, "alt", True),
    ("ramp_year_2_missing", 10, "cycle", True),
    ("ramp_above_steady_state", 10, "cycle", True),
    ("decoy_equal", 10, "alt", False),
    ("decoy_below", 10, "alt", False),
]
_VM_PATTERNS = {"alt": ["consumption", "hybrid"],
                "cycle": ["seats", "consumption", "hybrid"]}


def _plant_row(rng: np.random.Generator, opp_id: str, kind: str, vm: str,
               won: bool, aux: dict) -> dict:
    acct = int(rng.integers(0, len(_CORES)))
    seg = str(rng.choice(list(SEGMENTS), p=[0.45, 0.40, 0.15]))
    close = date(2024, 7, 1) + timedelta(days=int(rng.integers(0, 365)))
    created = close - timedelta(days=int(rng.integers(14, 120)))
    region = str(rng.choice(REGIONS, p=[0.55, 0.30, 0.15]))
    industry = str(rng.choice(INDUSTRIES))
    tier = str(rng.choice(TIERS))
    rep = f"REP-{int(rng.integers(0, 12)):02d}"
    competitor = bool(rng.random() < 0.42)
    lost_reason = "" if won else str(rng.choice(LOST_REASONS))

    # Per-kind draw ranges. Every deal sits at least 2 points clear of each
    # threshold other than the one it is planted on (spec 6.2).
    if kind in ("ramp_hidden", "credits_only"):
        disc = float(rng.uniform(0.0, 0.13))
    else:
        disc = float(rng.uniform(0.02, 0.13))
    share = (float(rng.uniform(0.20, 0.48)) if kind == "low_commit"
             else float(rng.uniform(0.60, 0.95)))
    if kind == "unit_floor":
        # 5 deals sit past the 40 percent EV grid edge (realization < 0.60);
        # the rest stay inside it. Nothing lands within 2 points of 0.60.
        real = (float(rng.uniform(0.55, 0.58)) if aux["grid"]
                else float(rng.uniform(0.62, 0.83)))
    elif kind in ("overage_equal", "overage_below", "decoy_equal", "decoy_below"):
        # realization below 1 makes overage <= effective rate also sit below
        # the list unit rate, by at least 2 points.
        real = float(rng.uniform(0.89, 0.97))
    else:
        real = float(rng.uniform(0.89, 1.10))
    if kind == "ramp_hidden":
        term = 36
    elif kind in ("ramp_year_2_missing", "ramp_above_steady_state"):
        term = int(rng.choice([24, 36]))
    elif kind == "credits_only":
        term = int(rng.choice([12, 24, 36]))
    else:
        term = int(rng.choice([12, 12, 12, 24, 36]))

    if vm == "seats":
        list_acv = float(np.clip(np.round(rng.lognormal(11.0, 0.4), 2), 5000, 600000))
        booked = round(list_acv * (1 - disc), 2)
        fee, usage = booked, 0.0
        quantity = float(int(np.clip(list_acv / rng.uniform(800, 2500), 1, 5000)))
        committed = overage = list_unit = np.nan
    else:
        q = int(rng.integers(50000, 500000))
        eff = round(float(rng.uniform(0.20, 3.00)), 2)   # 2 dp: exact cents
        cu = round(eff * q, 2)
        if vm == "hybrid":
            fee = round(cu * float(rng.uniform(0.3, 0.9)), 2)
            committed = round(cu + fee, 2)
        else:
            fee, committed = 0.0, cu
        booked = round(committed / share, 2)
        list_acv = round(booked / (1 - disc), 2)
        usage = round(booked - fee, 2)
        quantity = float(q)
        list_unit = round(eff / real, 6)
        if kind in ("overage_equal", "decoy_equal"):
            overage = eff                                   # premium exactly 0
        elif kind in ("overage_below", "decoy_below"):
            overage = round(eff * float(rng.uniform(0.60, 0.95)), 6)
        else:  # clean: premium >= 10 percent and at least 5 percent over list
            overage = round(max(eff * float(rng.uniform(1.1, 1.6)),
                                list_unit * 1.05 * float(rng.uniform(1.0, 1.2))), 6)

    approved, y1, y2, credits = "", np.nan, np.nan, np.nan
    d_act = 1 - booked / list_acv
    if kind == "ramp_hidden":
        target = float(rng.uniform(0.17, 0.30))
        total = 3 * (1 - target) / (1 - d_act) - 1          # f1 + f2
        lo, hi = max(0.5, total - 0.98), total / 2
        f1 = float(rng.uniform(lo, hi))
        y1, y2 = round(booked * f1, 2), round(booked * (total - f1), 2)
        if not aux["unapproved"]:
            approved = f"MGR-{int(rng.integers(0, 5)):02d}"
    elif kind == "credits_only":
        pocket_real = float(rng.uniform(0.70, 0.83))
        credits = round((booked - pocket_real * list_acv) * (term / 12), 2)
    elif kind == "quantity_missing_or_zero":
        quantity = 0.0 if aux["zero"] else np.nan
    elif kind == "platform_fee_missing_for_hybrid":
        fee = np.nan
    elif kind == "list_unit_rate_unavailable":
        list_unit = np.nan
    elif kind == "commit_exceeds_booked":
        committed = round(booked * float(rng.uniform(1.05, 1.30)), 2)
    elif kind == "ramp_year_2_missing":
        y1 = round(booked * float(rng.uniform(0.60, 0.80)), 2)
    elif kind == "ramp_above_steady_state":
        y1 = round(booked * float(rng.uniform(1.05, 1.25)), 2)
        y2 = round(booked * float(rng.uniform(0.80, 1.00)), 2)

    r = {c: np.nan for c in CONTRACT_COLUMNS}
    r.update(
        opportunity_id=opp_id, account_id=f"ACC-P{acct:03d}",
        account_name=_CORES[acct], outcome=(Outcome.WON if won else Outcome.LOST).value,
        created_date=created.isoformat(), close_date=close.isoformat(),
        segment=seg, region=region, industry=industry, business_unit="",
        product_line="", product_family="", product_tier=tier, sku="",
        value_metric=vm, list_acv=list_acv, booked_acv=booked,
        platform_fee_acv=fee, usage_acv=usage, term_months=term,
        quantity=quantity, rep_id=rep, approved_by=approved,
        competitor_present=str(competitor).lower(), lost_reason=lost_reason,
        currency="USD", committed_acv=committed, overage_rate=overage,
        ramp_year_1_acv=y1, ramp_year_2_acv=y2, list_unit_rate=list_unit,
        credits_tcv=credits, is_renewal="false", renewal_uplift=np.nan,
        cogs_acv=np.nan)
    return r


def generate_contract_fixture(n: int = 600, seed: int = 7) -> tuple[pd.DataFrame, dict]:
    """Planted contract-structure population plus its answer key (spec 6.2).

    Own stream, np.random.default_rng(seed + 3); never touches the streams
    generate() uses. n >= 300 (the planted sets need 210 deals). A third of
    the deals are consumption, a third hybrid, a third seats; 70 percent are
    closed_won (exactly 420 of 600); 20 closed_lost decoys are built like the
    fence-breach rows.

    Returns (deals, key). The key is
        {"flags":   {flag name: sorted won opportunity_id list},
         "reasons": {reason code: sorted won opportunity_id list},
         "lost_decoys": sorted opportunity_id list}
    and is derived by running every deal through _contract_expected_levers. The
    flag sets are then checked against the designed sets, so a deal that drifts
    onto a boundary fails loudly here instead of landing as noise in the key.
    """
    if n < 300:
        raise ValueError("generate_contract_fixture needs n >= 300")
    rng = np.random.default_rng(seed + 3)
    won_total = round(0.7 * n)

    slots: list[dict] = []
    for kind, count, pattern, won in _PLANTED_KINDS:
        for j in range(count):
            vm = (_VM_PATTERNS[pattern][j % len(_VM_PATTERNS[pattern])]
                  if pattern in _VM_PATTERNS else pattern)
            slots.append(dict(
                kind=kind, vm=vm, won=won,
                aux=dict(grid=(kind == "unit_floor" and j < 5),
                         unapproved=(kind == "ramp_hidden" and j < 10),
                         zero=(kind == "quantity_missing_or_zero" and j < 5))))
    planted_won = sum(1 for s in slots if s["won"])
    n_clean = n - len(slots)
    clean_won = won_total - planted_won
    quota = {"consumption": n // 3 + (1 if n % 3 > 0 else 0),
             "hybrid": n // 3 + (1 if n % 3 > 1 else 0), "seats": n // 3}
    for s in slots:
        quota[s["vm"]] -= 1
    if clean_won < 0 or min(quota.values()) < 0:
        raise ValueError("n too small for the planted sets")
    clean_vms = [vm for vm, k in quota.items() for _ in range(k)]
    clean_vms = [clean_vms[i] for i in rng.permutation(n_clean)]
    for j in range(n_clean):
        slots.append(dict(kind="clean", vm=clean_vms[j], won=j < clean_won, aux={}))

    order = rng.permutation(len(slots))
    rows, kind_ids = [], {}
    for pos, si in enumerate(order):
        s = slots[int(si)]
        opp = f"CS-{pos:05d}"
        rows.append(_plant_row(rng, opp, s["kind"], s["vm"], s["won"], s["aux"]))
        kind_ids.setdefault(s["kind"], set()).add(opp)
        if s["aux"].get("grid"):
            kind_ids.setdefault("unit_floor_grid", set()).add(opp)
        if s["aux"].get("unapproved"):
            kind_ids.setdefault("ramp_unapproved", set()).add(opp)
    deals = _finish_frame(rows)

    flags: dict[str, list[str]] = {f: [] for f in CONTRACT_FLAGS}
    reasons: dict[str, set[str]] = {}
    for rec in deals.to_dict("records"):
        if rec["outcome"] != Outcome.WON.value:
            continue
        res = _contract_expected_levers(rec)
        for f, (lever, field) in CONTRACT_FLAGS.items():
            if res[lever][field] is True:
                flags[f].append(rec["opportunity_id"])
        for lever in LEVERS:
            if res[lever]["reason"]:
                reasons.setdefault(res[lever]["reason"], set()).add(rec["opportunity_id"])
    key = {
        "flags": {f: sorted(v) for f, v in flags.items()},
        "reasons": {c: sorted(v) for c, v in sorted(reasons.items())},
        "lost_decoys": sorted(kind_ids["decoy_equal"] | kind_ids["decoy_below"]),
    }

    k = kind_ids
    designed = {
        "unit_rate_below_floor": k["unit_floor"],
        "unit_rate_outside_ev_grid": k["unit_floor_grid"],
        "low_commit_share": k["low_commit"],
        "overage_fence_breach": k["overage_equal"] | k["overage_below"],
        "overage_below_list_unit_rate": k["overage_equal"] | k["overage_below"],
        "ramp_hidden_discount": k["ramp_hidden"],
        "ramp_unapproved": k["ramp_unapproved"],
        "off_invoice_below_floor": k["ramp_hidden"] | k["credits_only"],
    }
    for f, want in designed.items():
        if set(key["flags"][f]) != want:
            raise RuntimeError(
                f"planted flag {f} drifted from its designed set: "
                f"{len(want)} designed, {len(key['flags'][f])} flagged")
    return deals, key


def write_contract_fixtures(out_dir: Path) -> tuple[Path, Path]:
    """Write the known-answer key and the case inputs to `out_dir`.

    The 23 KA inputs alone are below pricing.ingest.MIN_CLOSED_DEALS (30), so
    ingest raises SchemaError on them; concatenate them with the planted
    population (generate_contract_fixture) before ingesting.

    known_answers.csv is the long-form key (KEY_COLUMNS); known_answer_deals.csv
    is the matching hand-built input rows, loadable through pricing.ingest.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    deals, key = generate_known_answer_cases()
    key_path = out_dir / "known_answers.csv"
    deals_path = out_dir / "known_answer_deals.csv"
    key.to_csv(key_path, index=False, lineterminator="\n")
    deals.to_csv(deals_path, index=False, lineterminator="\n")
    return key_path, deals_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic deal data.")
    ap.add_argument("-n", "--num", type=int, default=2000,
                    help="number of opportunities (default 2000)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("-o", "--out", type=Path,
                    default=Path("data/synthetic/deals.csv"))
    ap.add_argument("--contract-fixture-dir", type=Path, default=None,
                    help="write the contract-structure known-answer key "
                         "(known_answers.csv) and its input rows "
                         "(known_answer_deals.csv) to this directory, e.g. "
                         "tests/fixtures/contract_structure, then exit "
                         "without touching the deals CSV")
    args = ap.parse_args()

    if args.contract_fixture_dir is not None:
        key_path, deals_path = write_contract_fixtures(args.contract_fixture_dir)
        print(f"Wrote known-answer key to {key_path}")
        print(f"Wrote known-answer input rows to {deals_path}")
        return

    df = generate(n=args.num, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)

    won = (df["outcome"] == Outcome.WON.value).sum()
    print(f"Wrote {len(df):,} opportunities to {args.out}")
    print(f"  won: {won:,} ({won/len(df):.0%})  |  lost: {len(df)-won:,}")
    print(f"  accounts (distinct id): {df['account_id'].replace('', pd.NA).nunique()}")


if __name__ == "__main__":
    main()
