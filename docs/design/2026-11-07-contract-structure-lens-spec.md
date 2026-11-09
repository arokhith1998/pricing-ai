---
title: Contract-structure lens v0, specification
created: 2026-11-07
updated: 2026-11-07
status: draft
tags: [design, spec, ubp, contract-structure, deal-guidance, governance, pk-30]
source: "PK-30, drafted by the pricing-strategist agent for founder approval"
related:
  - "[[2026-11-06-platform-agnostic-intake-and-usage-native-guidance]]"
  - "[[pricing-strategist]]"
  - "[[2026-08-08-crm-honesty-and-ubp-math]]"
  - "[[nagle-strategy-and-tactics-of-pricing]]"
  - "[[simon-kucher-discount-governance]]"
  - "[[poyar-usage-based-pricing]]"
  - "[[campbell-willingness-to-pay]]"
---

# Contract-structure lens v0, specification

Design doc: `docs/design/2026-11-06-platform-agnostic-intake-and-usage-native-guidance.md` section 3.5. Strategist report: `docs/reviews/2026-11-06-product-direction/pricing-strategist.md` sections 2 and 4. Implementers: data-engineer (PK-31), backend-engineer (PK-32, PK-33). The founder approves this spec before PK-31 starts.

## 1. Purpose and scope

The engine today scores one lever: `discount_pct = 1 - booked_acv / list_acv` on annualized ACV (`pricing/ingest.py` `enrich`). Usage-based and hybrid deals leak price through contract structure that this number cannot see: a cheap committed unit, a soft commit, an on-demand rate that undercuts the commitment, a ramp that gives back year-one dollars, credits. The schema already captures most of these fields (`pricing/schema.py`); nothing scores them.

This lens adds five deterministic levers, each reported on its own:

1. Effective committed unit rate and its realization against the list unit rate.
2. Commit share of booked.
3. Overage fence.
4. Ramp depth, ramp concession dollars and the TCV-weighted effective discount.
5. Revenue-side pocket waterfall.

Scope rules, all binding on PK-31 to PK-33:

- **CSV path only.** Input is the enriched frame from `ingest.ingest()` / `ingest_frame_verbose`. No connector, no live CRM path, no change to `pricing/crm.py`.
- **No model change.** `pricing/model.py`, `governance.exception_verdict` and the 0 to 40 percent EV grid are untouched. No lever becomes a model feature in v0.
- **No cost input.** No lever reads `cogs_acv` or any cost figure.
- **Every output is labeled `method: "policy rule"`.** Per deal, per lever, per book-level summary, per readout list. The literal string is `policy rule`.
- **Three states per lever, per deal:** `scored`, `insufficient_data`, `not_provided`. No global fallback: a deal that cannot be scored on a lever never inherits a book-level value, a segment value or a zero.
- **No re-basing.** The lens reads `discount_pct` and `price_realization` and never writes them, nor `discount_band`, `discount_amount`, `off_policy` or `off_policy_unapproved`. Every existing metric, test and the pinned dataset stay identical.
- **Policy rules, not estimates.** The lens applies fixed, named rules to each deal. It does not fit, estimate or update anything from the data, which is why it works on a book of a few hundred deals.

Positioning check: this lens is the substance behind the form line in the strategist report, "Explainable approval for usage-based deal terms." It does not change the wedge.

New module: `pricing/contract_structure.py` (PK-32). Public functions:

```python
def contract_structure_deals(df, *, floor_frac=DEFAULT_POLICY_THRESHOLD,
                             commit_share_floor=COMMIT_SHARE_FLOOR_DEFAULT,
                             columns_present=None) -> pd.DataFrame
def contract_structure_summary(deals: pd.DataFrame) -> dict
def contract_structure_readout(deals: pd.DataFrame, *, n: int = 25,
                               policy_threshold=DEFAULT_POLICY_THRESHOLD) -> dict
```

`contract_structure_deals` returns a copy of `df` with the lens columns of section 3 appended; it never mutates `df`. `columns_present` is the set of columns that existed in the uploaded file before ingest (PK-32 reads it from the `LoadReport` or from `df.columns` before coercion); it decides whether a blank ramp field means "not ramped" or "not in the file" (lever 5). Default `None` means "use `df.columns`".

Constants, defined in `pricing/contract_structure.py`:

| Constant | Value | Source |
|---|---|---|
| `floor_frac` default | `DEFAULT_POLICY_THRESHOLD` (0.15) | `pricing/schema.py`; same line as `governance.FLOOR_PCT_DEFAULT` (15.0 percent) |
| `COMMIT_SHARE_FLOOR_DEFAULT` | 0.50 | lever 2 reasoning |
| `EV_GRID_MAX_FRAC` | 0.40 | must equal `governance.EXCEPTION_MAX_PCT / 100`; a test asserts it (defined locally so the module does not import psycopg via governance) |
| `FULL_COMMIT_TOLERANCE` | 0.005 | lever 1 derivation |
| `STEADY_STATE_TOLERANCE` | 0.005 | commit and ramp sanity checks |
| `REALIZATION_SANITY_CAP` | 1.5 | mirrors the `price_realization` cap in `ingest.enrich` |
| `CONTRACT_LENS_MIN_SCORED` | 15 | book-level shares; mirrors the 15-deal band floor in `metrics.reference_discount` |

Conventions:

- **Fractions, not percent.** All ratios are 0 to 1 fractions, like `metrics.py`. Conversion to percent 0 to 100 happens at the API boundary, as `governance.py` does. A caller passing `floor_pct` (percent) converts with `floor_frac = floor_pct / 100`.
- **Rounding.** Ratios are rounded to 6 decimal places before any threshold comparison, the same rule `enrich` applies to `discount_pct`. Dollar outputs are computed in float64 and rounded to 2 places only on output.
- **Blank** means NaN after ingest coercion (or, before coercion, empty string, "nan", "none", "null", "na", case-insensitive), the same set `metrics.py` treats as blank.
- **Flags** are pandas nullable `boolean` dtype. A flag is `<NA>` whenever its lever is not `scored`. A flag is never `False` on an unscored deal, because that would be a silent pass.
- **Won only for aggregates.** Per-deal values are computed for every deal. Book-level summaries and readout lists use won deals only (`is_won`), the same convention as `metrics.leakage`.

## 2. Inputs

### 2.1 Existing schema fields, quoted exactly from `pricing/schema.py`

| Field | dtype | Unit and convention used by the lens | Used by levers |
|---|---|---|---|
| `opportunity_id` | str | deal key in every readout | all |
| `outcome` | enum | via derived `is_won` | aggregates |
| `value_metric` | enum | `seats`, `consumption`, `hybrid` | 1, 2, 3 |
| `list_acv` | float | annualized list value, deal currency | 1 (derivation), 4, 5 |
| `booked_acv` | float | annualized steady-state booked value, deal currency | 1, 2, 4, 5 |
| `platform_fee_acv` | float | fixed annual fee inside `booked_acv` (hybrid) | 1, 3 |
| `usage_acv` | float | not used in v0 formulas; shown in readout context only | none |
| `term_months` | int | contract term in months | 4, 5 |
| `quantity` | float | committed usage units per year, the unit `overage_rate` is priced in | 1, 3 |
| `approved_by` | str | blank means no approval recorded | 4 (flag), readout |
| `committed_acv` | float | committed annual spend, steady state, deal currency; for hybrid it includes `platform_fee_acv` (section 8, Q1) | 1, 2, 3 |
| `overage_rate` | float | price per usage unit beyond the commitment, deal currency | 3 |
| `ramp_year_1_acv` | float | scheduled year-1 ACV, at or below `booked_acv` | 4, 5 |
| `ramp_year_2_acv` | float | scheduled year-2 ACV, at or below `booked_acv` | 4, 5 |
| `currency` | str | single currency per book, enforced by ingest | all money |

Derived columns from `ingest.enrich`, read and never written: `discount_pct`, `price_realization`, `is_won`. From `ingest`: `resolved_account_name` (readout display only).

Not used: `cogs_acv` (no cost input), `renewal_uplift`, `is_renewal`, `usage_acv` (formula use), `competitor_present`.

### 2.2 New fields (marked new; schema change owned by data-engineer)

| Field | dtype | required | Unit and meaning | Used by |
|---|---|---|---|---|
| `list_unit_rate` (new) | float | False | list price per usage unit, same unit as `quantity` and `overage_rate`, deal currency. Typically from a CPQ rate card | 1, 3 |
| `credits_tcv` (new) | float | False | total value over the whole term of service credits, free months and other off-invoice price concessions, deal currency | 5 |

Ripple for the two new fields (approved 2026-11-07, rides on PK-23, section 8): add to `FIELDS` in `pricing/schema.py` after `ramp_year_2_acv`; add to `_NUMERIC` in `pricing/ingest.py`; both are money and belong in `_FX_MONEY_COLS` (`list_unit_rate` is a per-unit price exactly like `overage_rate`, which is already there); add synonyms in `pricing/mapping.py` `SYNONYMS`, exact-match only for these two fields, never fuzzy subset matching, and never a bare word: for `list_unit_rate` "list unit price", "unit list price", "rate card unit price", "list rate per unit"; for `credits_tcv` "service credits value", "credits tcv", "free months value", "off-invoice credits". The bare synonyms "credits" and "unit price" are banned: in a credit-based usage book "credits" is a unit count, and Salesforce `UnitPrice` is the net sales price, not list (PR 73 review, 2026-11-07); add to `gtm/data-request.md` as optional. Both optional, so every existing CSV still loads and the pinned dataset stays byte-identical.

### 2.3 Required fields per lever

| Lever | Required for `scored` | Optional, changes output |
|---|---|---|
| 1 Unit rate | `value_metric` in {consumption, hybrid}, `committed_acv`, `booked_acv`, `quantity` > 0, `platform_fee_acv` (hybrid only), and a list unit rate (`list_unit_rate` (new), or the derivation in 3.1) | none |
| 2 Commit share | `value_metric` in {consumption, hybrid}, `committed_acv`, `booked_acv` | none |
| 3 Overage fence | everything lever 1 needs except the list unit rate, plus `overage_rate` | `list_unit_rate` (new) enables the list-floor flag |
| 4 Ramp | `list_acv`, `booked_acv`, `term_months` > 12, `ramp_year_1_acv`, `ramp_year_2_acv` | `approved_by` |
| 5 Waterfall | `list_acv`, `booked_acv`, and at least one off-invoice step (lever 4 not `not_provided`, or `credits_tcv` (new) present); `term_months` > 0 when `credits_tcv` (new) is present | ramp columns |

### 2.4 How annualization interacts

- `booked_acv` is the annualized steady-state figure. Per `vault/Decisions/2026-08-08-crm-honesty-and-ubp-math.md`, that makes `discount_pct` already ramp-correct as a steady-state price measure, and re-basing it on `ramp_year_1_acv` would corrupt correct numbers. The lens therefore leaves `discount_pct` alone and reports the ramp as a separate TCV view (lever 4).
- Year schedule, per the `ramp_year_2_acv` description in `schema.py`: year 1 = `ramp_year_1_acv`, year 2 = `ramp_year_2_acv`, year 3 and later = `booked_acv`.
- Partial years are weighted by months: `w1 = min(term_months, 12) / 12`, `w2 = min(max(term_months - 12, 0), 12) / 12`, `term_years = term_months / 12`.
- `committed_acv` and `quantity` are read as annual, steady-state figures, the same convention as `booked_acv` (section 8, Q2 and Q3). The lens does not ramp the commitment.
- `credits_tcv` (new) is a whole-term figure and is annualized inside lever 5 only, by dividing by `term_years`.
- TCV figures exist only inside levers 4 and 5. No TCV figure is written back to any ACV column.

## 3. Levers

Every lever emits, per deal, `<lever>_status` (str: `scored`, `insufficient_data`, `not_provided`) and `<lever>_reason` (str: a reason code from the lists below, empty string when `scored`). Status conditions are evaluated in the listed order; the first condition that matches decides the status and reason. Lever ids: `unit_rate`, `commit_share`, `overage_fence`, `ramp`, `waterfall`.

Shared derived value, computed once and used by levers 1 and 3:

```
committed_usage_acv (new, derived) =
    committed_acv                          if value_metric == "consumption"
    committed_acv - platform_fee_acv       if value_metric == "hybrid"
effective_committed_unit_rate (new, derived) = committed_usage_acv / quantity
```

Shared pre-checks, called `commit_checks` below, in order:

| # | Condition | Status | Reason |
|---|---|---|---|
| C1 | `value_metric == "seats"` | not_provided | `value_metric_seats` |
| C2 | `committed_acv` blank | not_provided | `committed_acv_blank` |
| C3 | `value_metric` blank or not in {consumption, hybrid} | insufficient_data | `value_metric_unknown` |
| C4 | `committed_acv < 0`, or `booked_acv` blank or `<= 0` | insufficient_data | `invalid_money_value` |
| C5 | `committed_acv > booked_acv * (1 + STEADY_STATE_TOLERANCE)` | insufficient_data | `commit_exceeds_booked` |

Unit-rate checks, called `rate_checks`, applied after `commit_checks`:

| # | Condition | Status | Reason |
|---|---|---|---|
| R1 | `quantity` blank or `<= 0` | insufficient_data | `quantity_missing_or_zero` |
| R2 | `value_metric == "hybrid"` and `platform_fee_acv` blank | insufficient_data | `platform_fee_missing_for_hybrid` |
| R3 | `committed_usage_acv <= 0` | insufficient_data | `usage_commit_not_positive` |

`effective_committed_unit_rate` is populated whenever `commit_checks` and `rate_checks` pass, even if lever 1 later ends `insufficient_data` on the list unit rate. It is NaN otherwise.

### 3.1 Lever 1: effective committed unit rate and its realization

**What it answers.** What the buyer actually pays per committed unit, against the list price per unit. For a consumption deal this is the price lever; `discount_pct` stays reported beside it and is not replaced in v0.

**Formulas.**

```
list_unit_rate_used =
    list_unit_rate (new)                   if present and > 0           basis "supplied"
    list_acv / quantity                    if value_metric == "consumption"
                                           and abs(committed_acv - booked_acv)
                                               <= FULL_COMMIT_TOLERANCE * booked_acv
                                           and list_acv > 0              basis "derived"
    NaN                                    otherwise                     basis "unavailable"
unit_rate_realization = round(effective_committed_unit_rate / list_unit_rate_used, 6)
unit_rate_discount    = round(1 - unit_rate_realization, 6)
unit_rate_floor       = list_unit_rate_used * (1 - floor_frac)
unit_rate_below_floor = unit_rate_realization < round(1 - floor_frac, 6)
unit_rate_gap_to_floor_acv = max(unit_rate_floor - effective_committed_unit_rate, 0) * quantity
unit_rate_outside_ev_grid  = unit_rate_discount > EV_GRID_MAX_FRAC
```

Why the derivation is restricted. `list_acv` prices the booked scope, and `quantity` is committed units. They describe the same scope only when the deal is fully committed (commit equals booked). On any other deal, `list_acv / quantity` would mix commit depth into the unit price and report a deeper unit discount than was given, a confident wrong number. On a fully committed consumption deal the derived realization equals `price_realization` exactly; that is a consistency check, not new information. The lever adds information when `list_unit_rate` (new) is supplied.

**Output fields.**

| Field | Type |
|---|---|
| `unit_rate_status` | str |
| `unit_rate_reason` | str |
| `committed_usage_acv` (new, derived) | float, NaN when not computable |
| `effective_committed_unit_rate` (new, derived) | float, NaN when not computable |
| `list_unit_rate_used` | float, NaN when unavailable. Populated whenever the rate is supplied or derivable (derivation requires `quantity` > 0), regardless of the lever status, so a deal that fails a commit or rate check still shows the list rate it was judged against (clarified 2026-11-09 after the PR 79 review, KA-08 is the case) |
| `list_unit_rate_basis` | str: `supplied`, `derived`, `unavailable`. Never blank; `unavailable` when the rate is neither supplied nor derivable |
| `unit_rate_realization` | float, NaN unless scored |
| `unit_rate_discount` | float, NaN unless scored |
| `unit_rate_floor` | float, NaN unless scored |
| `unit_rate_below_floor` | boolean, NA unless scored |
| `unit_rate_gap_to_floor_acv` | float, NaN unless scored, 0.0 when not below floor |
| `unit_rate_outside_ev_grid` | boolean, NA unless scored |

**Label text.** "Effective committed unit rate: committed usage spend per committed unit, compared with the list unit rate. Method: policy rule. List unit rate {supplied | derived from list ACV over quantity on a fully committed deal}." When `unit_rate_outside_ev_grid` is true, append: "The unit discount is beyond the 40 percent range the exception verdict can score."

**Thresholds and reasoning.**

- Floor: `unit_rate_realization < 1 - floor_frac`, default 0.85. The unit-rate floor reuses the same policy line as `governance.FLOOR_PCT_DEFAULT` and `ingest.enrich`'s `off_policy`, so a deal desk has one floor whether the concession is taken on the ACV or on the unit. Simon-Kucher: authority must be explicit, and a second, different floor for the same concession invites forum shopping (`vault/simon-kucher-discount-governance.md`). This is the "price floors expressed as an effective unit rate" item from the strategist report.
- At exactly the floor (realization equal to 0.85 after rounding) the deal is not flagged, the same strict inequality `off_policy` uses (`discount_pct > policy_threshold`).
- EV grid: `unit_rate_discount > 0.40` is informational. `exception_verdict` cannot score a request outside its 0 to 40 percent grid, so the readout says so instead of implying a verdict exists.
- Above list (`unit_rate_realization > 1`) is scored and not flagged: pricing power, the same treatment as the "above list" band in `schema.DISCOUNT_BANDS`.

**States.**

| Order | Condition | Status | Reason |
|---|---|---|---|
| 1 | `commit_checks` C1 to C5 | per table | per table |
| 2 | `rate_checks` R1 to R3 | insufficient_data | per table |
| 3 | `list_unit_rate_basis == "unavailable"` | insufficient_data | `list_unit_rate_unavailable` |
| 4 | `unit_rate_realization > REALIZATION_SANITY_CAP` | insufficient_data | `unit_rate_realization_out_of_bounds` |
| 5 | otherwise | scored | empty |

**Worked examples** (floor_frac 0.15; full rows in section 6).

- KA-01, exactly at the floor, derived list rate. Consumption, `list_acv` 100,000, `booked_acv` 85,000, `committed_acv` 85,000, `quantity` 100,000. Fully committed, so `list_unit_rate_used` = 1.00, basis `derived`. Effective rate 0.85, realization 0.85, not below floor, gap 0.00. Realization equals `price_realization` 0.85.
- KA-02, supplied list rate, at the EV-grid edge. `list_unit_rate` 1.00, `committed_acv` 120,000, `quantity` 200,000. Effective rate 0.60, realization 0.60, discount 0.40, below floor, gap (0.85 - 0.60) * 200,000 = 50,000.00, outside EV grid false (0.40 is not above 0.40). `discount_pct` on the same deal is 0.20: the ACV view understates the unit concession.
- KA-07, hybrid. `committed_acv` 100,000, `platform_fee_acv` 50,000, `quantity` 100,000, `list_unit_rate` 0.80. Committed usage 50,000, effective rate 0.50, realization 0.625, floor 0.68, gap 18,000.00.
- KA-04, list rate unavailable. Consumption, commit 90,000 against booked 102,000 (not fully committed), no `list_unit_rate`. Effective rate 0.90 is populated; lever status `insufficient_data`, reason `list_unit_rate_unavailable`.
- KA-06, zero quantity. `quantity` 0: status `insufficient_data`, reason `quantity_missing_or_zero`; effective rate NaN.
- KA-08, hybrid without platform fee: `insufficient_data`, `platform_fee_missing_for_hybrid`.
- KA-17, outside the grid. `list_unit_rate` 2.00, commit 50,000, quantity 50,000: effective rate 1.00, realization 0.50, discount 0.50, below floor, gap (1.70 - 1.00) * 50,000 = 35,000.00, outside EV grid true.
- KA-18, supplied beats derived, above list. Fully committed consumption, `list_acv` 105,000, booked and commit 110,000, quantity 100,000, `list_unit_rate` 1.00. Basis `supplied` (derived would have been 1.05). Realization 1.10, scored, not flagged.

### 3.2 Lever 2: commit share of booked

**What it answers.** How much of the booked ACV the customer is contractually bound to pay. A low share means `booked_acv` is mostly forecast usage, and any discount was given without buying commitment depth.

**Formulas.**

```
commit_share_of_booked = round(committed_acv / booked_acv, 6)
uncommitted_booked_acv = booked_acv - committed_acv
low_commit_share       = commit_share_of_booked < commit_share_floor      (default 0.50)
```

For hybrid deals both numerator and denominator include the platform fee, so the share is like for like.

**Output fields.** `commit_share_status` (str), `commit_share_reason` (str), `commit_share_of_booked` (float, NaN unless scored), `uncommitted_booked_acv` (float, NaN unless scored), `low_commit_share` (boolean, NA unless scored).

**Label text.** "Commit share of booked: committed annual spend as a share of booked ACV. Method: policy rule. Below {commit_share_floor:.0%}, most of the booked value is uncommitted forecast."

**Thresholds and reasoning.**

- `commit_share_floor` 0.50, tenant-configurable. Below half, the majority of the booked figure is not contracted, so booked ACV overstates committed revenue. Poyar's case for hybrid as the default rests on the commitment giving finance predictability (`vault/poyar-usage-based-pricing.md`); a commitment under half of booked delivers little of it. Simon-Kucher's "trade, never give": commitment depth is one of the named things a discount should buy back (`vault/simon-kucher-discount-governance.md`).
- 0.50 is a policy starting point, not an estimate from data. Simon-Kucher's own watch-out applies: calibrate thresholds against the partner's book rather than setting them maximally strict. Section 8 Q5.
- `committed_acv == 0` is scored with share 0.0 and flagged.

**States.**

| Order | Condition | Status | Reason |
|---|---|---|---|
| 1 | `commit_checks` C1 to C5 | per table | per table |
| 2 | otherwise | scored | empty |

Lever 2 does not need `quantity` or `platform_fee_acv`: a zero-quantity deal is still scored here.

**Worked examples.**

- KA-05, soft commit. Booked 80,000, commit 30,000: share 0.375, flagged, uncommitted 50,000.00.
- KA-07, hybrid. Commit 100,000 on booked 120,000: share 0.833333, not flagged.
- KA-06, zero quantity. Commit 90,000 on booked 90,000: share 1.0, scored, not flagged (levers 1 and 3 are insufficient on the same deal).
- KA-21, commit exceeds booked. Commit 110,000 on booked 100,000: `insufficient_data`, `commit_exceeds_booked`.
- KA-20, pay as you go. `committed_acv` blank: `not_provided`, `committed_acv_blank`.

### 3.3 Lever 3: overage fence

**What it answers.** Whether the on-demand rate is dearer than the committed unit. If it is not, the buyer is better off committing low and paying overage, so the commitment fence leaks.

**Formulas.**

```
overage_premium      = round(overage_rate / effective_committed_unit_rate - 1, 6)
overage_fence_breach = overage_premium <= 0
overage_below_list_unit_rate =
    overage_rate < list_unit_rate_used     if list_unit_rate_basis != "unavailable"
    NA                                     otherwise
```

**Output fields.** `overage_fence_status` (str), `overage_fence_reason` (str), `overage_premium` (float, NaN unless scored), `overage_fence_breach` (boolean, NA unless scored), `overage_below_list_unit_rate` (boolean, NA unless scored and a list unit rate is available).

**Label text.** "Overage fence: on-demand rate against the effective committed unit rate. Method: policy rule. An overage rate at or below the committed rate rewards under-commitment." For the list flag: "Overage rate below the list unit rate."

**Thresholds and reasoning.**

- Breach at `overage_premium <= 0`, so equality is a breach ("at or below" in the design doc). Nagle: segmentation fences must hold without arbitrage between segments (`vault/nagle-strategy-and-tactics-of-pricing.md`). Commitment is the fence here; when the uncommitted unit costs the same or less, a rational buyer arbitrages across it. Zero premium is the point at which arbitrage costs the buyer nothing, so it is the threshold, not a tuned number.
- Campbell: the value metric must scale with delivered value (`vault/campbell-willingness-to-pay.md`). A cheaper unit past the commitment makes the price per unit fall as usage grows, which runs against that.
- `overage_below_list_unit_rate` is a second, independent flag. Nagle's reference-price point: a discount on the on-demand rate resets the anchor for every future unit the customer consumes. No premium threshold above zero is set in v0; any positive premium passes the fence. Section 7 names the trigger for a premium band.
- `overage_rate == 0` is scored, premium -1.0, breach true (free overage).

**States.**

| Order | Condition | Status | Reason |
|---|---|---|---|
| 1 | `value_metric == "seats"` | not_provided | `value_metric_seats` |
| 2 | `overage_rate` blank | not_provided | `overage_rate_blank` |
| 3 | `committed_acv` blank | not_provided | `no_commitment` |
| 4 | `overage_rate < 0` | insufficient_data | `invalid_money_value` |
| 5 | `commit_checks` C3 to C5, then `rate_checks` R1 to R3 | insufficient_data | per table |
| 6 | otherwise | scored | empty |

The fence does not need a list unit rate. It does need `effective_committed_unit_rate`.

**Worked examples.**

- KA-03, overage equal to the committed rate. Commit 60,000, quantity 75,000: effective rate 0.80. `overage_rate` 0.80. Premium 0.0, breach true.
- KA-04, overage below. Effective rate 0.90, `overage_rate` 0.75: premium -0.166667, breach true; list flag NA (no list unit rate).
- KA-07, hybrid. Effective rate 0.50, `overage_rate` 0.40: premium -0.2, breach true; list flag true (0.40 below 0.80).
- KA-02, passes the fence, fails the list. Effective 0.60, overage 0.70: premium 0.166667, no breach; list flag true (0.70 below 1.00).
- KA-01, clean. Effective 0.85, overage 1.10: premium 0.294118, no breach; list flag false (1.10 not below the derived 1.00).
- KA-06, zero quantity: `insufficient_data`, `quantity_missing_or_zero`.
- KA-19, free overage: premium -1.0, breach true.
- KA-20, pay as you go (`overage_rate` 1.20, no commit): `not_provided`, `no_commitment`.

### 3.4 Lever 4: ramp depth, ramp concession dollars, TCV-weighted effective discount

**What it answers.** How many dollars the ramp gives back below steady state over the term, and what the discount looks like once those dollars are counted. `discount_pct` measures the steady-state price, so a ramp concession is invisible to it by construction.

**Formulas.**

```
term_years  = term_months / 12
w1 = min(term_months, 12) / 12
w2 = min(max(term_months - 12, 0), 12) / 12
ramp_depth_year_1 = round(1 - ramp_year_1_acv / booked_acv, 6)
ramp_depth_year_2 = round(1 - ramp_year_2_acv / booked_acv, 6)
ramp_concession_tcv = w1 * (booked_acv - ramp_year_1_acv) + w2 * (booked_acv - ramp_year_2_acv)
booked_steady_tcv   = booked_acv * term_years
contracted_tcv      = booked_steady_tcv - ramp_concession_tcv
list_tcv            = list_acv * term_years
ramp_concession_pct_of_booked_tcv = round(ramp_concession_tcv / booked_steady_tcv, 6)
tcv_weighted_effective_discount   = round(1 - contracted_tcv / list_tcv, 6)
ramp_discount_increment           = round(tcv_weighted_effective_discount - discount_pct, 6)
ramp_hidden_discount = (discount_pct <= floor_frac) and (tcv_weighted_effective_discount > floor_frac)
ramp_unapproved      = ramp_hidden_discount and approved_by is blank
```

This is the backend report's `1 - sum(year_acv) / (list_annual * term_years)` (backend-engineer.md s2b) written out with the schema's year-3 convention and month weights.

Properties PK-32 must test:

- **Flat ramp equals flat discount.** If `ramp_year_1_acv == ramp_year_2_acv == booked_acv`, then `ramp_concession_tcv == 0` and `tcv_weighted_effective_discount == discount_pct`.
- **Bounded.** `tcv_weighted_effective_discount` lies between the smallest and largest annual discount in the schedule (`1 - acv_k / list_acv`), because it is their month-weighted mean.
- **No re-basing.** `discount_pct` on every row is identical before and after the lens runs.

**Output fields.** `ramp_status` (str), `ramp_reason` (str), `ramp_depth_year_1` (float), `ramp_depth_year_2` (float), `ramp_concession_tcv` (float), `ramp_concession_pct_of_booked_tcv` (float), `contracted_tcv` (float), `list_tcv` (float), `tcv_weighted_effective_discount` (float), `ramp_discount_increment` (float), `ramp_hidden_discount` (boolean), `ramp_unapproved` (boolean). All floats NaN and both flags NA unless scored.

**Label text.** "Ramp: dollars scheduled below steady-state ACV over the term, and the discount on a total-contract basis. Method: policy rule. The steady-state discount is {discount_pct:.1%}; counting the ramp, it is {tcv_weighted_effective_discount:.1%}."

**Thresholds and reasoning.**

- `ramp_hidden_discount`: the deal is within the policy line on `discount_pct` but over it on the TCV view. That is the governance gap a ramp opens: the approval rule sees only the steady-state number. Simon-Kucher: govern the waterfall and trade every concession (`vault/simon-kucher-discount-governance.md`). The floor is the same `floor_frac` as lever 1 and as `off_policy`, for the one-floor reason given there. Strict inequality on both sides, matching `off_policy`.
- `ramp_unapproved`: the hidden discount with no recorded approver, the ramp analogue of `off_policy_unapproved`.
- No threshold on ramp depth alone. A deep year-1 ramp on a long term can be a fair trade for the term; depth is reported, and the flag fires only when the term-weighted result crosses the policy line. Poyar names ramps as a legitimate structure for protecting realization (`vault/poyar-usage-based-pricing.md`), so a ramp by itself is not a finding.

**States.**

| Order | Condition | Status | Reason |
|---|---|---|---|
| 1 | `ramp_year_1_acv` and `ramp_year_2_acv` both blank | not_provided | `no_ramp_recorded` |
| 2 | `list_acv` or `booked_acv` blank or `<= 0` | insufficient_data | `invalid_money_value` |
| 3 | `term_months` blank or `<= 0` | insufficient_data | `term_months_missing` |
| 4 | `term_months <= 12` | insufficient_data | `ramp_on_single_year_term` |
| 5 | `ramp_year_1_acv` blank | insufficient_data | `ramp_year_1_missing` |
| 6 | `ramp_year_2_acv` blank | insufficient_data | `ramp_year_2_missing` |
| 7 | any ramp value `< 0` | insufficient_data | `invalid_money_value` |
| 8 | any ramp value `> booked_acv * (1 + STEADY_STATE_TOLERANCE)` | insufficient_data | `ramp_above_steady_state` |
| 9 | otherwise | scored | empty |

Row 6 is strict by default: a missing year 2 is not read as steady state, because that would be an inferred schedule (section 8, Q4). Applies to every `value_metric`.

**Worked examples.**

- KA-10, 36-month ramp. `list_acv` 100,000, `booked_acv` 90,000, years 60,000 and 80,000, term 36, no approver. Depths 0.333333 and 0.111111. Concession 30,000 + 10,000 = 40,000.00. Steady TCV 270,000, contracted 230,000, list TCV 300,000. Effective discount 1 - 230,000 / 300,000 = 0.233333 against `discount_pct` 0.10; increment 0.133333; concession share 0.148148. Hidden discount true, unapproved true. Bounds check: annual discounts 0.40, 0.20, 0.10, mean 0.233333.
- KA-11, flat ramp. Booked 88,000, both years 88,000, term 36, list 100,000: concession 0.00, effective discount 0.12 equal to `discount_pct` 0.12, hidden false.
- KA-12, missing year 2. Year 1 70,000, year 2 blank, term 36: `insufficient_data`, `ramp_year_2_missing`.
- KA-13, 18-month partial term. List and booked 100,000, years 50,000 and 90,000, term 18: w1 1.0, w2 0.5, concession 50,000 + 5,000 = 55,000.00, contracted 95,000 against list TCV 150,000, effective discount 0.366667 against `discount_pct` 0.0. Hidden true.
- KA-24, ramp above steady state. Year 1 95,000 on booked 90,000: `ramp_above_steady_state`.
- KA-25, ramp on a 12-month term: `ramp_on_single_year_term`.

### 3.5 Lever 5: revenue-side pocket waterfall

**What it answers.** Where price goes between list and what the customer actually pays over the contract, on the revenue side only: list, discount to booked, ramp concessions, credits. Payment terms are not a step in v0 (section 7).

**Formulas** (annualized, consistent with the schema's ACV convention):

```
wf_list_acv            = list_acv
wf_discount_acv        = list_acv - booked_acv                 (signed; negative when booked above list)
wf_ramp_concession_acv = ramp_concession_tcv / term_years      if ramp step scored from data
                       = 0.0                                   if ramp lever not_provided and ramp columns are in the file
                       = NaN                                   if ramp columns are not in the file
wf_credits_acv         = credits_tcv / term_years              if credits_tcv (new) present
                       = NaN                                   otherwise
pocket_acv             = booked_acv - (wf_ramp_concession_acv or 0) - (wf_credits_acv or 0)
pocket_realization     = round(pocket_acv / list_acv, 6)
off_invoice_below_floor = (price_realization >= round(1 - floor_frac, 6))
                          and (pocket_realization < round(1 - floor_frac, 6))
```

A blank ramp field in a file that has the ramp columns is read as "not ramped", per the schema description ("Blank for single-year / non-ramped deals"). A file without the columns gives the step `not_provided`, not zero, and the label names the excluded step.

`wf_discount_acv` is signed on purpose: the waterfall must add up, so an above-list deal shows a negative step. This does not touch `discount_amount`, which stays floored at 0 in `ingest.enrich`.

Consistency property PK-32 must test: when the credits step is `not_provided` and the ramp step is scored, `pocket_realization == round(1 - tcv_weighted_effective_discount, 6)`, and `off_invoice_below_floor == ramp_hidden_discount`.

**Output fields.** `waterfall_status` (str), `waterfall_reason` (str), `wf_list_acv`, `wf_discount_acv`, `wf_ramp_concession_acv`, `wf_credits_acv`, `pocket_acv`, `pocket_realization` (floats), `wf_ramp_step_status` and `wf_credits_step_status` (str: `scored` or `not_provided`), `off_invoice_below_floor` (boolean, NA unless scored).

**Label text.** "Pocket price waterfall, revenue side: list, discount, ramp concessions, credits, annualized. Method: policy rule. Price only, no cost." When a step is not provided, append "Excludes {step}: not in the file."

**Thresholds and reasoning.**

- `off_invoice_below_floor`: the deal passed the discount policy at booking, and the off-invoice steps took the pocket price below the same floor. Simon-Kucher: track every leak past the invoice so the pocket price is governed, not just the headline (`vault/simon-kucher-discount-governance.md`). Same `floor_frac`, same one-floor reasoning.
- It overlaps `ramp_hidden_discount` when there are no credits. That is intended: lever 4 isolates the ramp, lever 5 shows the cumulative effect. The readout lists the contributing steps so the overlap is visible, and the two are never added.

**States.**

| Order | Condition | Status | Reason |
|---|---|---|---|
| 1 | `list_acv` or `booked_acv` blank, or `list_acv <= 0` | insufficient_data | `invalid_money_value` |
| 2 | lever 4 `insufficient_data` | insufficient_data | `ramp_step_insufficient` |
| 3 | `credits_tcv` (new) `< 0` | insufficient_data | `invalid_money_value` |
| 4 | `credits_tcv` (new) present and `term_months` blank or `<= 0` | insufficient_data | `term_months_missing` |
| 5 | lever 4 `not_provided` and `credits_tcv` (new) blank or column absent | not_provided | `no_off_invoice_steps` |
| 6 | `pocket_realization > REALIZATION_SANITY_CAP` | insufficient_data | `pocket_realization_out_of_bounds` |
| 7 | otherwise | scored | empty |

Row 5 exists because, with no off-invoice step, the waterfall is just `price_realization`, which the diagnostic already reports.

**Worked examples.**

- KA-10. List 100,000, discount 10,000, ramp 40,000 / 3 = 13,333.33, credits not provided, pocket 76,666.67, pocket realization 0.766667 (= 1 - 0.233333). `price_realization` 0.90 passes, pocket fails: flagged.
- KA-14, credits only. List 100,000, booked 90,000, term 24, ramp fields blank with columns present, `credits_tcv` 20,000: ramp step 0.00 (`scored`), credits 10,000.00, pocket 80,000.00, realization 0.80, flagged.
- KA-01. No ramp, no credits: `not_provided`, `no_off_invoice_steps`.
- KA-12. Ramp insufficient: `insufficient_data`, `ramp_step_insufficient`.
- KA-26. `credits_tcv` 5,000 with `term_months` blank: `insufficient_data`, `term_months_missing`.

### 3.6 Book-level summary

`contract_structure_summary(deals)` returns one dict per lever under keys `unit_rate`, `commit_share`, `overage_fence`, `ramp`, `waterfall`. Computed on won deals only. Each dict:

| Key | Type | Meaning |
|---|---|---|
| `lever` | str | lever id |
| `method` | str | `"policy rule"` |
| `label` | str | lever label text above |
| `n_won` | int | won deals in the book |
| `n_scored`, `n_insufficient_data`, `n_not_provided` | int | status counts on won deals |
| `reasons` | dict[str, int] | reason code counts on won deals |
| `n_flagged` | dict[str, int] | count per flag of this lever |
| `flagged_share` | dict[str, float] | `n_flagged / n_scored` per flag; NaN when `n_scored < CONTRACT_LENS_MIN_SCORED` |
| `share_status` | str | `scored` or `insufficient_data` by the same 15-deal rule |
| `dollars` | dict[str, float] | sums over flagged won deals, below |

Dollar sums, always reported with their deal count, never as a share when `share_status` is `insufficient_data`:

- unit_rate: `unit_rate_gap_to_floor_acv` summed over `unit_rate_below_floor`.
- commit_share: `uncommitted_booked_acv` summed over `low_commit_share`.
- overage_fence: `committed_usage_acv` summed over `overage_fence_breach` (labeled "committed usage exposed to the fence breach", not a loss figure).
- ramp: `ramp_concession_tcv` over all scored deals and over `ramp_hidden_discount` deals, separately.
- waterfall: totals of each step over scored deals, and `booked_acv - pocket_acv` over `off_invoice_below_floor` deals.

No summary combines dollars or counts across levers. There is no lens total.

## 4. Decision-record concession fields

PK-33 adds these to the `decision_log` row `payload` (JSON) for kind `exception`, through `pricing/governance.py`. They round-trip through `DecisionStore.insert` and `DecisionStore.list` unchanged. All new; no existing field is renamed.

`payload["contract_structure"]`, written when a logged decision concerns a deal the lens has scored:

| Field | Type | Notes |
|---|---|---|
| `lens_version` | str | `"contract-structure-v0"` |
| `method` | str | `"policy rule"` |
| `floor_frac`, `commit_share_floor` | float | the parameters used |
| `levers` | list[dict] | one dict per lever: `lever`, `status`, `reason`, `method`, the lever's output fields from section 3 |

`payload["concessions"]`: list of dicts, one per concession, entered or confirmed by a human:

| Field | Type | Notes |
|---|---|---|
| `concession_type` | str enum | `unit_rate_discount`, `commit_reduction`, `overage_rate_reduction`, `ramp`, `credits`, `price_protection`, `cost_decline_pass_through`, `other` |
| `value_acv` | float or null | annualized value; may be prefilled from the lens (unit_rate: `(list_unit_rate_used - effective_committed_unit_rate) * quantity`; ramp: `ramp_concession_tcv / term_years`; credits: `credits_tcv / term_years`) |
| `value_tcv` | float or null | whole-term value |
| `value_basis` | str enum | `lens_computed`, `human_entered`, `not_quantified` |
| `traded_for` | list[str enum], at least one entry | `longer_term`, `higher_commit`, `prepayment`, `reference_or_case_study`, `expanded_scope`, `faster_close`, `none` |
| `traded_for_detail` | str | free text, for example "term 24 to 36 months" |
| `traded_for_value_acv` | float or null | human-entered |
| `approved_by` | str | same meaning as the schema field |

Rules: the engine may prefill `value_acv` and `value_tcv` from lens outputs with `value_basis = "lens_computed"`; it never fills `traded_for`. `traded_for = ["none"]` is a valid, explicit entry and is what the readout counts as given, not traded (Simon-Kucher). An empty `traded_for` is rejected with a 422.

`payload["repricing_cadence"]`: recorded, never set, by the engine. The engine writes no default; null means not recorded.

| Field | Type | Notes |
|---|---|---|
| `rate_card_review_term_months` | int or null | how often the rate card may be revisited |
| `price_protection_term_months` | int or null | months the quoted rates are held |
| `price_protection_scope` | str enum or null | `unit_rate`, `overage_rate`, `platform_fee`, `all` |
| `cost_decline_pass_through` | str enum or null | `none`, `full`, `partial` |
| `cost_decline_pass_through_share` | float 0 to 1 or null | required when `partial` |
| `cost_decline_pass_through_reference` | str or null | what the pass-through is indexed to, for example a vendor's public token price list |

A committed pass-through of future cost declines is a concession and is also logged as a `concessions` entry of type `cost_decline_pass_through`, so it is traded like a discount. The engine computes nothing from these fields in v0: no cost figure enters, and no cadence is recommended. Campbell's "process, not project" is why the fields exist; the cadence itself is the deal desk's decision.

Retention: these fields live in the decision log, which already persists. Per-deal lens columns are row-level data and are not written to the per-tenant snapshot (D1 option a); only the section 3.6 counts and sums may be.

## 5. Readout

`contract_structure_readout(deals, n=25)` returns, for the diagnostic response (PK-33 wires it into `pricing/diagnostic.py` as key `contract_structure`, next to the existing sections):

- `summary`: the section 3.6 dicts.
- `flags`: one entry per flag below. Each entry: `flag`, `lever`, `method: "policy rule"`, `label`, `total_flagged` (int, won deals), `deals` (list of row dicts, at most `n`), `truncated` (bool). Won deals only. Sort as stated, ties broken by `opportunity_id` ascending, so output is deterministic.
- `coverage`: per lever, status counts and the first `n` won `opportunity_id` values for each `insufficient_data` reason, so the customer can fix the data.
- `trade_check`: won deals with `discount_pct > policy_threshold` and `low_commit_share` true, sorted by `discount_amount` descending. Both values in their own columns; no combined number. This is "discount given without commitment bought" (Simon-Kucher).

Every deal row starts with `opportunity_id`, then `resolved_account_name` and `segment` (as `metrics.top_leak_deals` does), then `value_metric`, then the flag's columns:

| Flag | Lever | Columns after the common ones | Sort |
|---|---|---|---|
| `unit_rate_below_floor` | 1 | `effective_committed_unit_rate`, `list_unit_rate_used`, `list_unit_rate_basis`, `unit_rate_realization`, `unit_rate_gap_to_floor_acv`, `unit_rate_outside_ev_grid`, `discount_pct` | `unit_rate_gap_to_floor_acv` desc |
| `low_commit_share` | 2 | `committed_acv`, `booked_acv`, `commit_share_of_booked`, `uncommitted_booked_acv` | `uncommitted_booked_acv` desc |
| `overage_fence_breach` | 3 | `effective_committed_unit_rate`, `overage_rate`, `overage_premium`, `committed_usage_acv` | `overage_premium` asc |
| `overage_below_list_unit_rate` | 3 | `overage_rate`, `list_unit_rate_used`, `list_unit_rate_basis` | `overage_rate / list_unit_rate_used` asc |
| `ramp_hidden_discount` | 4 | `term_months`, `ramp_year_1_acv`, `ramp_year_2_acv`, `booked_acv`, `discount_pct`, `tcv_weighted_effective_discount`, `ramp_concession_tcv`, `approved_by` | `ramp_concession_tcv` desc |
| `ramp_unapproved` | 4 | same as above | `ramp_concession_tcv` desc |
| `off_invoice_below_floor` | 5 | `price_realization`, `pocket_realization`, `wf_ramp_concession_acv`, `wf_credits_acv`, `steps_contributing` (list of `ramp`, `credits` with a nonzero value) | `booked_acv - pocket_acv` desc |

Readout sentence templates (deterministic, no LLM, no em dashes):

- "{k} of {n_scored} scored won usage deals sit below the {floor:.0%} unit-rate floor, ${gap:,.0f} below floor in total. Method: policy rule."
- "{k} won deals carry an overage rate at or below their effective committed unit rate. Method: policy rule."
- "{k} won deals pass the {floor:.0%} discount line at steady state but exceed it once the ramp is counted; {u} of them have no recorded approver. Method: policy rule."
- When `share_status` is `insufficient_data`: "Fewer than 15 scored won deals on this lever, so no share is reported. The deals are listed below."

## 6. Known-answer test plan for PK-31 and PK-32

### 6.1 Hand-built fixture (PK-32)

A CSV at `tests/fixtures/contract_structure/known_answers.csv` (add the path to PK-32's owned files) with the rows below, all `closed_won` unless stated, `segment` MidMarket, `currency` USD, the ramp columns present in the file, `floor_frac` 0.15, `commit_share_floor` 0.50. Blank cells are blank. Expected values to 6 decimal places for ratios, 2 for dollars.

| Id | vm | list | booked | commit | qty | plat fee | list unit | overage | term | y1 | y2 | credits | Expected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KA-01 | consumption | 100000 | 85000 | 85000 | 100000 | | | 1.10 | 12 | | | | L1 scored, basis derived, eff 0.85, real 0.85, below false, gap 0.00. L2 share 1.0, low false. L3 premium 0.294118, breach false, below list false. L4 not_provided `no_ramp_recorded`. L5 not_provided `no_off_invoice_steps` |
| KA-02 | consumption | 200000 | 160000 | 120000 | 200000 | | 1.00 | 0.70 | 12 | | | | L1 eff 0.60, real 0.60, discount 0.40, below true, gap 50000.00, grid false. L2 0.75, low false. L3 premium 0.166667, breach false, below list true |
| KA-03 | consumption | 100000 | 90000 | 60000 | 75000 | | 1.00 | 0.80 | 12 | | | | L1 eff 0.80, real 0.80, below true, gap 3750.00. L2 0.666667. L3 premium 0.0, breach true, below list true |
| KA-04 | consumption | 120000 | 102000 | 90000 | 100000 | | | 0.75 | 12 | | | | L1 insufficient `list_unit_rate_unavailable`, eff 0.90 populated. L2 0.882353. L3 premium -0.166667, breach true, below list NA |
| KA-05 | consumption | 100000 | 80000 | 30000 | 40000 | | 1.00 | 1.20 | 12 | | | | L1 eff 0.75, below true, gap 4000.00. L2 0.375, low true, uncommitted 50000.00. L3 premium 0.6, breach false. In `trade_check` (`discount_pct` 0.20) |
| KA-06 | consumption | 100000 | 90000 | 90000 | 0 | | | 1.00 | 12 | | | | L1 and L3 insufficient `quantity_missing_or_zero`. L2 scored 1.0 |
| KA-07 | hybrid | 150000 | 120000 | 100000 | 100000 | 50000 | 0.80 | 0.40 | 12 | | | | committed usage 50000.00, eff 0.50, real 0.625, below true, gap 18000.00. L2 0.833333. L3 premium -0.2, breach true, below list true |
| KA-08 | hybrid | 150000 | 120000 | 100000 | 100000 | | 0.80 | 0.40 | 12 | | | | L1 and L3 insufficient `platform_fee_missing_for_hybrid`. L2 scored 0.833333 |
| KA-09 | seats | 100000 | 90000 | | 100 | | | | 12 | | | | L1, L2, L3 not_provided `value_metric_seats` |
| KA-10 | seats | 100000 | 90000 | | 100 | | | | 36 | 60000 | 80000 | | L4 depth 0.333333 and 0.111111, concession 40000.00, contracted 230000.00, eff disc 0.233333, increment 0.133333, share 0.148148, hidden true, unapproved true. L5 ramp step 13333.33, credits not_provided, pocket 76666.67, real 0.766667, flag true |
| KA-11 | seats | 100000 | 88000 | | 100 | | | | 36 | 88000 | 88000 | | L4 concession 0.00, eff disc 0.12 equals `discount_pct` 0.12, hidden false. L5 pocket 88000.00, flag false |
| KA-12 | seats | 100000 | 90000 | | 100 | | | | 36 | 70000 | | | L4 insufficient `ramp_year_2_missing`. L5 insufficient `ramp_step_insufficient` |
| KA-13 | seats | 100000 | 100000 | | 100 | | | | 18 | 50000 | 90000 | | L4 concession 55000.00, contracted 95000.00, eff disc 0.366667, `discount_pct` 0.0, hidden true |
| KA-14 | seats | 100000 | 90000 | | 100 | | | | 24 | | | 20000 | L4 not_provided. L5 ramp step 0.00 scored, credits 10000.00, pocket 80000.00, real 0.80, flag true |
| KA-17 | consumption | 100000 | 60000 | 50000 | 50000 | | 2.00 | | 12 | | | | L1 eff 1.00, real 0.50, discount 0.50, below true, gap 35000.00, grid true. L3 not_provided `overage_rate_blank` |
| KA-18 | consumption | 105000 | 110000 | 110000 | 100000 | | 1.00 | 1.30 | 12 | | | | L1 basis supplied, real 1.10, below false. L3 premium 0.181818, breach false |
| KA-19 | consumption | 50000 | 50000 | 50000 | 50000 | | | 0 | 12 | | | | L1 derived, real 1.0. L3 premium -1.0, breach true |
| KA-20 | consumption | 100000 | 90000 | | 100000 | | | 1.20 | 12 | | | | L1, L2 not_provided `committed_acv_blank`. L3 not_provided `no_commitment` |
| KA-21 | consumption | 100000 | 100000 | 110000 | 100000 | | | 1.20 | 12 | | | | L1, L2, L3 insufficient `commit_exceeds_booked` |
| KA-22 | consumption, `closed_lost` | 120000 | 102000 | 90000 | 100000 | | | 0.75 | 12 | | | | Per-deal L3 breach true. Absent from won summary counts and from every readout list |
| KA-24 | seats | 100000 | 90000 | | 100 | | | | 36 | 95000 | 90000 | | L4 insufficient `ramp_above_steady_state` |
| KA-25 | seats | 100000 | 90000 | | 100 | | | | 12 | 70000 | 80000 | | L4 insufficient `ramp_on_single_year_term` |
| KA-26 | seats | 100000 | 90000 | | 100 | | | | | | | 5000 | L4 not_provided. L5 insufficient `term_months_missing` |

Fixture-level assertions:

- Every lever output dict and every summary and readout entry carries `method == "policy rule"`.
- Every flag is NA on every row whose lever status is not `scored`.
- `discount_pct`, `price_realization`, `discount_band`, `discount_amount`, `off_policy` are identical before and after `contract_structure_deals` (frame equality on those columns). The input frame is not mutated.
- A second copy of the fixture with the ramp columns removed gives KA-14 a waterfall ramp step of `not_provided` and NaN, pocket 80000.00, and a label naming the excluded step.
- The readout, serialized to JSON, contains no em dash and none of the cost vocabulary that section 7 excludes; the test scans for the excluded word explicitly.
- `EV_GRID_MAX_FRAC == governance.EXCEPTION_MAX_PCT / 100`.
- The summary has no key that sums or averages across levers.

Property tests (hypothesis or a seeded loop of 500 random valid ramped deals): flat ramp equals flat discount; TCV-weighted discount within the min and max annual discount; `pocket_realization == 1 - tcv_weighted_effective_discount` when credits are not provided; `overage_fence_breach` iff `overage_rate <= effective_committed_unit_rate` after rounding.

### 6.2 Planted population in the generator (PK-31)

New function in `pricing/generate.py`: `generate_contract_fixture(n: int = 600, seed: int = 7) -> tuple[pd.DataFrame, dict]`, on its own stream `np.random.default_rng(seed + 3)`, which never touches the streams `generate()` uses. `generate()` output and the pinned dataset stay byte-identical; `tests/test_generate_contract.py` asserts the existing pinned hash.

Population: 600 deals, 200 each `consumption`, `hybrid`, `seats`; exactly 420 `closed_won`. All schema fields populated as in `generate()`, plus `list_unit_rate` (new) on every usage deal except the planted `list_unit_rate_unavailable` rows, and `credits_tcv` (new) only where planted. The returned dict is the answer key: flag name to sorted list of `opportunity_id`, plus reason code to sorted list of ids.

Planted won deals, each set disjoint from the others unless stated:

| Planted set | Count | Construction |
|---|---|---|
| `overage_fence_breach`, equal | 20 | `overage_rate` set exactly to `effective_committed_unit_rate`, rounded to 6 dp |
| `overage_fence_breach`, below | 20 | `overage_rate` = effective rate times U(0.60, 0.95) |
| `unit_rate_below_floor` | 25 | realization: 20 deals U(0.62, 0.83) and 5 deals U(0.55, 0.58), so exactly 5 sit past the 0.60 EV-grid edge (`unit_rate_outside_ev_grid`) and none inside the (0.58, 0.62) noise band; amended 2026-11-09 because a single U(0.55, 0.83) draw contradicted the 2-point clearance rule below |
| `low_commit_share` | 20 | share U(0.20, 0.48) |
| `ramp_hidden_discount` | 30 | `discount_pct` U(0.00, 0.13), term 36, ramp chosen so TCV discount U(0.17, 0.30); 10 of the 30 with blank `approved_by` (the `ramp_unapproved` set) |
| `off_invoice_below_floor`, credits only | 15 | no ramp, `discount_pct` U(0.00, 0.13), `credits_tcv` sized so pocket realization U(0.70, 0.83) |
| one per insufficient reason | 10 each | `quantity_missing_or_zero`, `platform_fee_missing_for_hybrid`, `list_unit_rate_unavailable`, `commit_exceeds_booked`, `ramp_year_2_missing`, `ramp_above_steady_state` |
| lost-deal decoys | 20 | `closed_lost` deals built like the fence-breach rows; must not appear in any won list |

Every deal, planted or not, is built at least 2 percentage points clear of every threshold other than the one it is planted on (unit-rate realization at or above 0.87, commit share at or above 0.52, overage premium at or above 0.02, TCV discount at or below 0.13 when `discount_pct` is at or below 0.13, pocket realization at or above 0.87), so no boundary noise lands in the key. The `ramp_hidden_discount` set necessarily also carries `off_invoice_below_floor` (section 3.5 consistency property); the key lists those 30 ids under both flags. The two boundary cases (exact floor, exact fence) are covered by the hand-built fixture, where they are exact.

Recovery test (PK-32): for every flag, the set of won `opportunity_id` the lens flags equals the answer key exactly; for every reason code, the set of won ids equals the key; lost decoys appear in no readout list. Run at seeds 7, 11 and 23.

## 7. What this lens does not do

| Not done | Why | Trigger for adding it |
|---|---|---|
| Any cost input or cost-based figure | Margin is excluded: this lens takes no cost input and reports price only. | Founder decision D2 answered, ADR-006 cost-basis enum written, and a design partner supplying non-proxy unit cost |
| A modeled curve per lever (win rate by unit-rate band, commit band, ramp band) | Pilot-size books cannot support it; v0 is policy rules | A partner book where a lever has at least `SEGMENT_REF_MIN_BANDS` (3) bands with 15 closed deals each, the same bar as `metrics.reference_discount` (backend-engineer.md s2b) |
| Blending levers into one score or one total | A Head of Pricing cannot defend a composite in committee; each lever has its own owner and remedy | None planned. A multi-lever win model is a separate ai-engineer stop-and-report task, gated on the row above |
| EVC or any per-customer value figure | Inputs are hard to estimate and easy to inflate (Nagle watch-out) | Large exceptions in a live pilot; then a human-entered worksheet, not a lens |
| Commit coverage against forecast usage, commit attainment | No forecast or usage-actuals field exists | A partner billing export, with `contract_period_actuals` or usage history |
| Overage premium bands above zero | No evidence yet on what premium holds the fence | 30 or more scored fence deals on one partner book, then the founder sets a band |
| Payment terms as a waterfall step | Needs a time-value convention and a payment-terms field | A partner that records payment terms |
| Tiered overage, multi-meter rates, ramps past year 2 | The flat schema cannot express them | The `rate_card` and `contract_term` child entities, after the first real partner export |
| Cost-indexed value metric flag (tokens, compute priced near cost) | Needs `value_metric_unit` | PK-23 landing `value_metric_unit` |
| Setting a repricing cadence | The engine records cadence, it does not decide it | None; humans decide |
| Any change to `exception_verdict`, the EV grid or model features | Out of scope by design | The modeled-curve trigger above |

## 8. Open questions for the founder

**Answered 2026-11-07.** The founder confirmed all six defaults below and approved the two new fields, `list_unit_rate` (new) and `credits_tcv` (new). pk-lead call on Q6: the fields ride on PK-23 (the schema task), whose owned paths widen to `pricing/ingest.py#numeric`, `pricing/mapping.py#synonyms` and `gtm/data-request.md` so the ripple in section 2 lands in one reviewable diff; PK-31 then plants answers against fields that already exist. The questions stay here as the record of what was decided and why.

Only questions whose answer changes a formula or threshold. Each has the default this spec uses, now the decided value.

1. **Hybrid commitment.** Does `committed_acv` on a hybrid deal include the platform fee? Default yes, so `committed_usage_acv = committed_acv - platform_fee_acv`; the schema calls the commitment "the floor the customer commits to regardless of usage", and the platform fee is paid regardless of usage. If no, levers 1 and 3 use `committed_acv` directly for hybrid and check R2 is dropped.
2. **Quantity grain.** Is `quantity` committed units per year? Default yes. If partners export per-term or per-month units, `effective_committed_unit_rate` needs a grain field or a per-tenant setting.
3. **Commit on ramped deals.** Is `committed_acv` the steady-state annual commit, like `booked_acv`? Default yes. If it is the year-1 commit, check C5 and lever 2 must compare it with `ramp_year_1_acv` instead.
4. **Missing ramp year 2.** Default `insufficient_data`. Alternative: read a blank `ramp_year_2_acv` as steady state (`booked_acv`) when `ramp_year_1_acv` is present, with a disclosure. That scores more deals and infers a schedule nobody entered.
5. **Thresholds.** Unit-rate, ramp and waterfall floors reuse the 15 percent policy line (`DEFAULT_POLICY_THRESHOLD`); commit share floor is 0.50. Confirm one shared floor, or set a separate unit-rate floor.
6. **New fields.** Approve `list_unit_rate` (new) and `credits_tcv` (new), and say whether they ride on PK-23 or extend PK-31. Without `list_unit_rate`, lever 1 scores only fully committed consumption deals, where it repeats `price_realization`.
