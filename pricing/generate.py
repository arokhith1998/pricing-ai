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
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from pricing.schema import ALL_COLUMNS, DEFAULT_POLICY_THRESHOLD, Outcome

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

    df = pd.DataFrame(rows, columns=ALL_COLUMNS)
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic deal data.")
    ap.add_argument("-n", "--num", type=int, default=2000,
                    help="number of opportunities (default 2000)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("-o", "--out", type=Path,
                    default=Path("data/synthetic/deals.csv"))
    args = ap.parse_args()

    df = generate(n=args.num, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)

    won = (df["outcome"] == Outcome.WON.value).sum()
    print(f"Wrote {len(df):,} opportunities to {args.out}")
    print(f"  won: {won:,} ({won/len(df):.0%})  |  lost: {len(df)-won:,}")
    print(f"  accounts (distinct id): {df['account_id'].replace('', pd.NA).nunique()}")


if __name__ == "__main__":
    main()
