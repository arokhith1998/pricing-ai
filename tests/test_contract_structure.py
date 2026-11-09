"""PK-32: contract-structure lens, known-answer recovery and lever behaviour.

Inputs: tests/fixtures/contract_structure/known_answer_deals.csv concatenated
with the planted population (23 rows alone are below the closed-deal minimum),
loaded through pricing.ingest.ingest_frame_verbose. Expectations: the long-form
key known_answers.csv at the spec's rounding (6 dp ratios, 2 dp dollars).

pricing.generate is used here only to build the planted population. The lens
module itself must not import it, and a test below asserts that.
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pricing import contract_structure as cs
from pricing.contract_structure import (
    CONTRACT_LENS_MIN_SCORED, EV_GRID_MAX_FRAC, LEVERS, METHOD,
    contract_structure_deals, contract_structure_readout, contract_structure_summary,
)
from pricing.generate import generate_contract_fixture
from pricing.ingest import enrich, ingest_frame_verbose, ingest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "contract_structure"
MODULE_SRC = (ROOT / "pricing" / "contract_structure.py").read_text(encoding="utf-8")

# key column -> lever that owns it
LEVER_COLS = {
    "unit_rate": ["committed_usage_acv", "effective_committed_unit_rate", "list_unit_rate_used",
                  "list_unit_rate_basis", "unit_rate_realization", "unit_rate_discount",
                  "unit_rate_floor", "unit_rate_below_floor", "unit_rate_gap_to_floor_acv",
                  "unit_rate_outside_ev_grid"],
    "commit_share": ["commit_share_of_booked", "uncommitted_booked_acv", "low_commit_share"],
    "overage_fence": ["overage_premium", "overage_fence_breach", "overage_below_list_unit_rate"],
    "ramp": ["ramp_depth_year_1", "ramp_depth_year_2", "ramp_concession_tcv",
             "ramp_concession_pct_of_booked_tcv", "contracted_tcv", "list_tcv",
             "tcv_weighted_effective_discount", "ramp_discount_increment",
             "ramp_hidden_discount", "ramp_unapproved"],
    "waterfall": ["wf_list_acv", "wf_discount_acv", "wf_ramp_concession_acv", "wf_credits_acv",
                  "pocket_acv", "pocket_realization", "wf_ramp_step_status",
                  "wf_credits_step_status", "off_invoice_below_floor"],
}
STR_COLS = {"list_unit_rate_basis", "wf_ramp_step_status", "wf_credits_step_status"}
BOOL_COLS = {c for cols in LEVER_COLS.values() for c in cols
             if c.startswith(("low_", "unit_rate_below", "unit_rate_outside", "overage_fence_b",
                              "overage_below", "ramp_hidden", "ramp_unapproved", "off_invoice"))}
DOLLAR_COLS = {"committed_usage_acv", "unit_rate_gap_to_floor_acv", "uncommitted_booked_acv",
               "ramp_concession_tcv", "contracted_tcv", "list_tcv", "wf_list_acv",
               "wf_discount_acv", "wf_ramp_concession_acv", "wf_credits_acv", "pocket_acv"}

FLAG_COL = {  # key flag name -> lens column
    "overage_fence_breach": "overage_fence_breach",
    "unit_rate_below_floor": "unit_rate_below_floor",
    "unit_rate_outside_ev_grid": "unit_rate_outside_ev_grid",
    "low_commit_share": "low_commit_share",
    "overage_below_list_unit_rate": "overage_below_list_unit_rate",
    "ramp_hidden_discount": "ramp_hidden_discount",
    "ramp_unapproved": "ramp_unapproved",
    "off_invoice_below_floor": "off_invoice_below_floor",
}


@functools.lru_cache(maxsize=None)
def _frame_and_key(seed: int):
    pop, key = generate_contract_fixture(n=600, seed=seed)
    ka = pd.read_csv(FIX / "known_answer_deals.csv")
    return pd.concat([ka, pop], ignore_index=True), key


def _lens_for(seed: int = 7):
    frame, key = _frame_and_key(seed)
    enriched, report = ingest_frame_verbose(frame, source="PK-32 fixture")
    assert not report.blockers
    present = set(frame.columns)
    return contract_structure_deals(enriched, columns_present=present), key, enriched


@pytest.fixture(scope="module")
def lens7():
    return _lens_for(7)


@pytest.fixture(scope="module")
def keydf():
    return pd.read_csv(FIX / "known_answers.csv", dtype=str, keep_default_na=False)


def _blank_actual(v) -> bool:
    return v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v)) or v == ""


# --- known-answer recovery --------------------------------------------------------

def test_known_answers_recovered_row_by_row(lens7, keydf):
    deals, _, _ = lens7
    by_id = deals.set_index("opportunity_id")
    assert len(keydf) == 115
    matched, diffs = 0, []
    for _, k in keydf.iterrows():
        row, lever = by_id.loc[k["opportunity_id"]], k["lever"]
        bad = []
        if row[f"{lever}_status"] != k["state"]:
            bad.append(("state", k["state"], row[f"{lever}_status"]))
        if row[f"{lever}_reason"] != k["reason"]:
            bad.append(("reason", k["reason"], row[f"{lever}_reason"]))
        for col in LEVER_COLS[lever]:
            exp, act = k[col], row[col]
            if exp == "":
                if not _blank_actual(act):
                    bad.append((col, "blank", act))
            elif col in STR_COLS:
                if act != exp:
                    bad.append((col, exp, act))
            elif col in BOOL_COLS:
                if _blank_actual(act) or bool(act) != (exp == "true"):
                    bad.append((col, exp, act))
            else:
                dp = 2 if col in DOLLAR_COLS else 6
                if _blank_actual(act) or round(float(act), dp) != round(float(exp), dp):
                    bad.append((col, exp, act))
        if bad:
            diffs.append((k["case_id"], lever, bad))
        else:
            matched += 1
    assert matched == 115, f"{matched}/115 matched; disagreements: {diffs}"


@pytest.mark.parametrize("seed", [7, pytest.param(11, marks=pytest.mark.slow),
                                  pytest.param(23, marks=pytest.mark.slow)])
def test_population_flag_and_reason_sets_match_the_key(seed):
    deals, key, _ = _lens_for(seed)
    won = deals[deals["is_won"]]
    for name, ids in key["flags"].items():
        got = sorted(won.loc[won[FLAG_COL[name]].fillna(False).astype(bool), "opportunity_id"])
        # the 23 hand-built KA rows are not in the key; the key lists population ids only
        got = [i for i in got if not i.startswith("KA-")]
        assert got == sorted(ids), name
    for reason, ids in key["reasons"].items():
        mask = pd.Series(False, index=won.index)
        for lever in LEVERS:
            mask |= won[f"{lever}_reason"] == reason
        got = sorted(i for i in won.loc[mask, "opportunity_id"] if not i.startswith("KA-"))
        assert got == sorted(ids), reason
        if reason in ("quantity_missing_or_zero", "platform_fee_missing_for_hybrid",
                      "list_unit_rate_unavailable", "commit_exceeds_booked",
                      "ramp_year_2_missing", "ramp_above_steady_state"):
            assert len(ids) == 10


def test_planted_set_sizes_and_no_lost_decoy_flagged(lens7):
    deals, key, _ = lens7
    f = key["flags"]
    assert [len(f[n]) for n in ("overage_fence_breach", "unit_rate_below_floor",
                                "low_commit_share", "ramp_hidden_discount",
                                "off_invoice_below_floor", "unit_rate_outside_ev_grid",
                                "ramp_unapproved")] == [40, 25, 20, 30, 45, 5, 10]
    summary = contract_structure_summary(deals)
    decoys = set(key["lost_decoys"])
    assert len(decoys) == 20
    won = deals[deals["is_won"]]
    assert not decoys & set(won["opportunity_id"])
    for name, col in FLAG_COL.items():
        flagged_won = set(won.loc[won[col].fillna(False).astype(bool), "opportunity_id"])
        assert not decoys & flagged_won
    # decoys are built like fence breaches: the per-deal view still flags them, the summary does not
    lost = deals[deals["opportunity_id"].isin(decoys)]
    assert lost["overage_fence_breach"].fillna(False).astype(bool).any()
    n_breach_won = int(won["overage_fence_breach"].fillna(False).astype(bool).sum())
    assert summary["overage_fence"]["n_flagged"]["overage_fence_breach"] == n_breach_won


# --- spec properties --------------------------------------------------------------

def test_flat_ramp_equals_flat_discount_ka11(lens7):
    deals, _, _ = lens7
    r = deals.set_index("opportunity_id").loc["KA-11"]
    assert r["ramp_status"] == "scored"
    assert r["ramp_concession_tcv"] == 0.0
    assert r["tcv_weighted_effective_discount"] == r["discount_pct"] == pytest.approx(0.12)
    assert not r["ramp_hidden_discount"]
    assert r["pocket_acv"] == 88000.0 and not r["off_invoice_below_floor"]


def test_summary_counts_won_only_and_has_no_cross_lever_total(lens7):
    deals, _, _ = lens7
    s = contract_structure_summary(deals)
    assert list(s) == list(LEVERS)
    for lever, d in s.items():
        assert d["method"] == METHOD and d["lever"] == lever
        assert d["n_won"] == int(deals["is_won"].sum())
        assert d["n_scored"] + d["n_insufficient_data"] + d["n_not_provided"] == d["n_won"]
        assert sum(d["reasons"].values()) == d["n_insufficient_data"] + d["n_not_provided"]
    keys = {k.lower() for d in s.values() for k in (*d, *d["dollars"], *d["n_flagged"])}
    assert not any(w in k for k in keys for w in ("total", "blend", "composite", "score_all"))
    for d in s.values():  # dollars hold floats only; the counts sit beside them
        assert all(isinstance(v, float) for v in d["dollars"].values())
        assert all(isinstance(v, int) for v in d["dollars_n"].values())
    # KA-22 is closed_lost, so it never reaches the won summary reasons
    assert s["unit_rate"]["share_status"] == "scored"


def test_flags_are_na_whenever_the_lever_is_not_scored(lens7):
    deals, _, _ = lens7
    for lever, flags in cs.LEVER_FLAGS.items():
        unscored = deals[deals[f"{lever}_status"] != "scored"]
        for f in flags:
            assert unscored[f].isna().all(), f
            assert str(deals[f].dtype) == "boolean"
        assert (unscored[f"{lever}_reason"] != "").all()
        assert (deals.loc[deals[f"{lever}_status"] == "scored", f"{lever}_reason"] == "").all()


def test_existing_metrics_untouched_and_input_not_mutated(lens7):
    _, _, enriched = lens7
    before = enriched.copy()
    out = contract_structure_deals(enriched)
    pd.testing.assert_frame_equal(enriched, before)
    for c in ("discount_pct", "price_realization", "discount_band", "discount_amount",
              "off_policy", "off_policy_unapproved"):
        pd.testing.assert_series_equal(out[c], before[c])


def test_every_output_is_labelled_policy_rule(lens7):
    deals, _, _ = lens7
    assert (deals["contract_structure_method"] == METHOD).all()
    for lever in LEVERS:
        assert (deals[f"{lever}_method"] == METHOD).all()
    assert deals.attrs["contract_structure"]["method"] == METHOD
    for lever, d in contract_structure_summary(deals).items():
        assert d["method"] == METHOD and "Method: policy rule" in d["label"]


# --- three states per lever --------------------------------------------------------

def _one(**kw) -> pd.Series:
    base = dict(opportunity_id="X", outcome="closed_won", value_metric="consumption",
                list_acv=100000.0, booked_acv=85000.0, committed_acv=85000.0, quantity=100000.0,
                overage_rate=1.10, term_months=12, approved_by="")
    base.update(kw)
    df = pd.DataFrame([base])
    return contract_structure_deals(enrich(df), columns_present=set(df.columns)).iloc[0]


def test_unit_rate_three_states():
    assert _one()["unit_rate_status"] == "scored"
    assert _one(list_acv=100000.0, committed_acv=60000.0, booked_acv=85000.0)["unit_rate_reason"] \
        == "list_unit_rate_unavailable"
    assert _one(value_metric="seats")["unit_rate_status"] == "not_provided"
    assert _one(quantity=0.0)["unit_rate_reason"] == "quantity_missing_or_zero"
    assert _one(value_metric="mystery")["unit_rate_reason"] == "value_metric_unknown"
    assert _one(list_unit_rate=0.5)["unit_rate_reason"] == "unit_rate_realization_out_of_bounds"


def test_commit_share_three_states():
    assert bool(_one(committed_acv=30000.0)["low_commit_share"])
    assert _one(committed_acv=np.nan)["commit_share_status"] == "not_provided"
    assert _one(committed_acv=90000.0)["commit_share_reason"] == "commit_exceeds_booked"
    assert _one(value_metric="seats")["commit_share_reason"] == "value_metric_seats"
    zero = _one(committed_acv=0.0)
    assert zero["commit_share_of_booked"] == 0.0 and bool(zero["low_commit_share"])


def test_overage_fence_three_states():
    r = _one(overage_rate=0.0)
    assert r["overage_premium"] == -1.0 and bool(r["overage_fence_breach"])
    assert _one(overage_rate=np.nan)["overage_fence_reason"] == "overage_rate_blank"
    assert _one(committed_acv=np.nan)["overage_fence_reason"] == "no_commitment"
    assert _one(overage_rate=-1.0)["overage_fence_status"] == "insufficient_data"
    assert _one(value_metric="hybrid", platform_fee_acv=np.nan)["overage_fence_reason"] \
        == "platform_fee_missing_for_hybrid"
    # equality with the committed rate is a breach (strict premium <= 0)
    assert bool(_one(overage_rate=0.85)["overage_fence_breach"])
    assert not bool(_one(overage_rate=0.851)["overage_fence_breach"])
    # exact floor is not flagged
    assert not bool(_one()["unit_rate_below_floor"])


def test_ramp_three_states():
    base = dict(value_metric="seats", term_months=36, ramp_year_1_acv=60000.0, ramp_year_2_acv=80000.0,
                booked_acv=90000.0)
    assert _one(**base)["ramp_status"] == "scored"
    assert _one(**{**base, "ramp_year_1_acv": np.nan, "ramp_year_2_acv": np.nan})["ramp_reason"] \
        == "no_ramp_recorded"
    assert _one(**{**base, "ramp_year_2_acv": np.nan})["ramp_reason"] == "ramp_year_2_missing"
    assert _one(**{**base, "ramp_year_1_acv": np.nan})["ramp_reason"] == "ramp_year_1_missing"
    assert _one(**{**base, "term_months": 12})["ramp_reason"] == "ramp_on_single_year_term"
    assert _one(**{**base, "term_months": np.nan})["ramp_reason"] == "term_months_missing"
    assert _one(**{**base, "ramp_year_1_acv": 95000.0})["ramp_reason"] == "ramp_above_steady_state"
    assert _one(**{**base, "ramp_year_1_acv": -1.0})["ramp_reason"] == "invalid_money_value"


def test_waterfall_three_states_and_ramp_columns_absent():
    base = dict(value_metric="seats", booked_acv=90000.0, term_months=24)
    r = _one(**base, credits_tcv=20000.0)
    assert r["waterfall_status"] == "scored" and r["pocket_acv"] == 80000.0
    assert _one(**base)["waterfall_reason"] == "no_off_invoice_steps"
    assert _one(**{**base, "term_months": np.nan}, credits_tcv=5000.0)["waterfall_reason"] == "term_months_missing"
    assert _one(**base, credits_tcv=-1.0)["waterfall_status"] == "insufficient_data"
    assert _one(**base, credits_tcv=1.0, ramp_year_1_acv=70000.0)["waterfall_reason"] == "ramp_step_insufficient"


def test_ka14_without_ramp_columns_gives_a_not_provided_ramp_step():
    frame, _ = _frame_and_key(7)
    frame = frame.drop(columns=["ramp_year_1_acv", "ramp_year_2_acv"])
    enriched, _ = ingest_frame_verbose(frame, source="PK-32 no ramp cols")
    out = contract_structure_deals(enriched, columns_present=set(frame.columns))
    r = out.set_index("opportunity_id").loc["KA-14"]
    assert r["wf_ramp_step_status"] == "not_provided" and np.isnan(r["wf_ramp_concession_acv"])
    assert r["wf_credits_step_status"] == "scored" and r["wf_credits_acv"] == 10000.0
    assert r["pocket_acv"] == 80000.0 and r["waterfall_status"] == "scored"
    assert r["ramp_status"] == "not_provided"


def test_list_unit_rate_populated_regardless_of_lever_status():
    # KA-08 shape: hybrid without platform fee still shows the supplied list rate
    r = _one(value_metric="hybrid", platform_fee_acv=np.nan, list_unit_rate=0.8)
    assert r["unit_rate_status"] == "insufficient_data"
    assert r["list_unit_rate_used"] == 0.8 and r["list_unit_rate_basis"] == "supplied"
    # derivation needs quantity > 0
    r0 = _one(quantity=0.0)
    assert np.isnan(r0["list_unit_rate_used"]) and r0["list_unit_rate_basis"] == "unavailable"


# --- property loops ---------------------------------------------------------------

def _random_ramped(n: int = 500, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    list_acv = rng.uniform(50_000, 500_000, n)
    booked = list_acv * rng.uniform(0.5, 1.2, n)
    term = rng.choice([13, 18, 24, 30, 36, 48, 60], n)
    return pd.DataFrame({
        "opportunity_id": [f"R{i}" for i in range(n)], "outcome": "closed_won",
        "value_metric": rng.choice(["consumption", "hybrid", "seats"], n),
        "list_acv": list_acv, "booked_acv": booked, "term_months": term,
        "ramp_year_1_acv": booked * rng.uniform(0.3, 1.0, n),
        "ramp_year_2_acv": booked * rng.uniform(0.3, 1.0, n),
        "approved_by": rng.choice(["", "VP"], n),
    })


def test_property_tcv_discount_is_bounded_and_pocket_matches_when_no_credits():
    out = contract_structure_deals(enrich(_random_ramped()))
    assert (out["ramp_status"] == "scored").all()
    twed = out["tcv_weighted_effective_discount"]
    annual = pd.concat([1 - out["ramp_year_1_acv"] / out["list_acv"],
                        1 - out["ramp_year_2_acv"] / out["list_acv"],
                        1 - out["booked_acv"] / out["list_acv"]], axis=1)
    assert (twed >= annual.min(axis=1) - 1e-5).all() and (twed <= annual.max(axis=1) + 1e-5).all()
    ok = out["waterfall_status"] == "scored"
    assert ok.all()
    assert (out["pocket_realization"] - (1 - twed)).abs().max() < 2e-6
    flag = out["off_invoice_below_floor"].astype(bool)
    hid = out["ramp_hidden_discount"].astype(bool)
    # price_realization is capped at 1.5, which does not bind here, so the two flags agree
    assert (flag == hid).all()


def test_property_flat_ramp_equals_flat_discount():
    df = _random_ramped()
    df["ramp_year_1_acv"] = df["booked_acv"]
    df["ramp_year_2_acv"] = df["booked_acv"]
    out = contract_structure_deals(enrich(df))
    assert (out["ramp_concession_tcv"] == 0).all()
    assert (out["tcv_weighted_effective_discount"] - out["discount_pct"]).abs().max() < 2e-6
    assert not out["ramp_hidden_discount"].astype(bool).any()


def test_property_fence_breach_iff_overage_at_or_below_effective_rate():
    rng = np.random.default_rng(9)
    n = 500
    qty = rng.uniform(1000, 100000, n)
    rate = rng.uniform(0.5, 2.0, n)
    committed = qty * rate
    df = pd.DataFrame({
        "opportunity_id": [f"F{i}" for i in range(n)], "outcome": "closed_won",
        "value_metric": "consumption", "list_acv": committed * 1.2, "booked_acv": committed,
        "committed_acv": committed, "quantity": qty, "term_months": 12,
        "overage_rate": (rate * rng.uniform(0.7, 1.3, n)).round(6),
    })
    out = contract_structure_deals(enrich(df))
    exp = (out["overage_rate"] / out["effective_committed_unit_rate"] - 1).round(6) <= 0
    assert (out["overage_fence_breach"].astype(bool) == exp).all()


# --- boundaries of the module ------------------------------------------------------

def test_module_does_not_import_the_fixture_generator():
    assert not re.search(r"^\s*(from|import)\s+pricing\.generate\b", MODULE_SRC, re.M)
    assert not re.search(r"^\s*from\s+pricing\s+import\s+.*\bgenerate\b", MODULE_SRC, re.M)
    assert "_contract_expected_levers" not in MODULE_SRC
    import sys
    # fresh interpreter: importing the lens alone must not pull the generator in
    import subprocess
    code = "import sys; import pricing.contract_structure; print('pricing.generate' in sys.modules)"
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.stdout.strip() == "False", r.stderr


def test_no_margin_vocabulary_and_no_cost_input_is_read(lens7):
    deals, _, enriched = lens7
    assert "margin" not in MODULE_SRC.lower()
    assert "cogs" not in MODULE_SRC.lower()
    new_cols = [c for c in deals.columns if c not in enriched.columns]
    assert new_cols and not any("margin" in c.lower() or "cogs" in c.lower() for c in new_cols)
    blob = json.dumps(contract_structure_summary(deals), default=str).lower()
    assert "margin" not in blob and "cogs" not in blob
    # results do not move when the cost column changes or disappears
    changed = enriched.copy()
    changed["cogs_acv"] = 1e9
    dropped = enriched.drop(columns=["cogs_acv"])
    a = contract_structure_deals(changed)[new_cols]
    b = contract_structure_deals(dropped)[new_cols]
    c = contract_structure_deals(enriched)[new_cols]
    pd.testing.assert_frame_equal(a, c)
    pd.testing.assert_frame_equal(b, c)


def test_ev_grid_constant_matches_governance():
    gov = pytest.importorskip("pricing.governance")
    assert EV_GRID_MAX_FRAC == gov.EXCEPTION_MAX_PCT / 100
    assert cs.DEFAULT_POLICY_THRESHOLD * 100 == gov.FLOOR_PCT_DEFAULT


def test_synthetic_book_runs_clean_and_reports_not_provided_where_fields_are_missing():
    path = ROOT / "data" / "synthetic" / "deals.csv"
    raw = pd.read_csv(path)
    assert "list_unit_rate" not in raw.columns and "credits_tcv" not in raw.columns
    enriched, _ = ingest_frame_verbose(raw, source="synthetic")
    out = contract_structure_deals(enriched, columns_present=set(raw.columns))
    s = contract_structure_summary(out)
    assert list(s) == list(LEVERS)
    assert (out["list_unit_rate_basis"].isin(["derived", "unavailable"])).all()  # none supplied
    assert (out["wf_credits_step_status"] != "scored").all()
    assert (out["credits_tcv"].isna().all() if "credits_tcv" in out.columns else True)
    # ramp columns are in the book, credits are not: waterfall needs a ramp to score
    wf = out[out["waterfall_status"] == "scored"]
    assert (wf["ramp_status"] == "scored").all()
    for lever in LEVERS:
        d = s[lever]
        assert d["n_scored"] + d["n_insufficient_data"] + d["n_not_provided"] == d["n_won"]
    assert (out["opportunity_id"] == enriched["opportunity_id"]).all()
    # seats deals can never score the usage levers
    seats = out[out["value_metric"] == "seats"]
    assert (seats["unit_rate_status"] == "not_provided").all()
    assert (seats["overage_fence_status"] == "not_provided").all()


# --- review amendments (spec 7a) ----------------------------------------------------

def test_cent_denominated_floor_deals_agree_between_ramp_and_waterfall():
    rng = np.random.default_rng(31)
    n = 600
    list_acv = rng.uniform(20_000, 400_000, n).round(2)
    term = rng.choice([24, 36, 48], n)
    booked = (list_acv * 0.85).round(2)  # exactly 15 percent off, at cents
    df = pd.DataFrame({
        "opportunity_id": [f"C{i}" for i in range(n)], "outcome": "closed_won",
        "value_metric": "seats", "list_acv": list_acv, "booked_acv": booked, "term_months": term,
        "ramp_year_1_acv": (booked * 0.9).round(2), "ramp_year_2_acv": booked, "approved_by": "",
    })
    enriched = enrich(df)
    assert (enriched["price_realization"] < 0.85).any()  # the unrounded value really is below
    out = contract_structure_deals(enriched)
    assert (out["waterfall_status"] == "scored").all()
    assert (out["ramp_hidden_discount"].astype(bool) == out["off_invoice_below_floor"].astype(bool)).all()
    # a non-flat ramp at exactly 15 percent steady state crosses the line on every deal
    assert out["off_invoice_below_floor"].astype(bool).all()
    assert out["ramp_hidden_discount"].astype(bool).all()
    assert (out["pocket_realization"] - (1 - out["tcv_weighted_effective_discount"])).abs().max() < 2e-6


def test_cent_level_ramp_deals_keep_the_consistency_property():
    rng = np.random.default_rng(32)
    n = 600
    list_acv = rng.uniform(20_000, 400_000, n).round(2)
    booked = (list_acv * rng.choice([0.85, 0.9, 0.95], n)).round(2)
    df = pd.DataFrame({
        "opportunity_id": [f"D{i}" for i in range(n)], "outcome": "closed_won",
        "value_metric": "seats", "list_acv": list_acv, "booked_acv": booked,
        "term_months": rng.choice([24, 36, 48], n),
        "ramp_year_1_acv": (booked * rng.uniform(0.5, 1, n)).round(2),
        "ramp_year_2_acv": (booked * rng.uniform(0.5, 1, n)).round(2), "approved_by": "",
    })
    out = contract_structure_deals(enrich(df))
    assert (out["ramp_hidden_discount"].astype(bool) == out["off_invoice_below_floor"].astype(bool)).all()


def test_negative_platform_fee_on_hybrid_is_invalid_not_inflated_usage():
    # KA-02 economics as hybrid: commit 120,000, qty 200,000, list rate 1.00, overage 0.70
    r = _one(value_metric="hybrid", list_acv=200000.0, booked_acv=160000.0, committed_acv=120000.0,
             quantity=200000.0, list_unit_rate=1.0, overage_rate=0.70, platform_fee_acv=-50000.0)
    for lever in ("unit_rate", "overage_fence"):
        assert r[f"{lever}_status"] == "insufficient_data"
        assert r[f"{lever}_reason"] == "invalid_money_value"
    assert np.isnan(r["effective_committed_unit_rate"]) and np.isnan(r["committed_usage_acv"])
    assert r["commit_share_status"] == "scored"  # lever 2 does not use the fee


def test_waterfall_bounds_and_nonfinite_list_rate():
    seats = dict(value_metric="seats", list_acv=100000.0, booked_acv=90000.0, term_months=24)
    big = _one(**seats, credits_tcv=500000.0)
    assert big["waterfall_status"] == "insufficient_data"
    assert big["waterfall_reason"] == "pocket_realization_out_of_bounds"
    zero = _one(**{**seats, "booked_acv": 0.0}, credits_tcv=1000.0)
    assert zero["waterfall_reason"] == "invalid_money_value"
    short = _one(**{**seats, "term_months": 1}, credits_tcv=5000.0)  # 60,000 a year on a 100,000 list
    assert short["waterfall_status"] == "scored" and short["pocket_acv"] == 30000.0
    short2 = _one(**{**seats, "term_months": 1, "booked_acv": 50000.0}, credits_tcv=5000.0)
    assert short2["waterfall_reason"] == "pocket_realization_out_of_bounds"  # pocket < 0
    inf = _one(list_unit_rate=np.inf)
    assert inf["list_unit_rate_basis"] == "derived" and inf["list_unit_rate_used"] == 1.0
    assert inf["unit_rate_status"] == "scored"


def test_enriched_columns_are_required():
    raw = pd.DataFrame({"opportunity_id": ["a"], "outcome": ["closed_won"], "list_acv": [1.0],
                        "booked_acv": [1.0]})
    with pytest.raises(ValueError, match="discount_pct"):
        contract_structure_deals(raw)
    with pytest.raises(ValueError, match="is_won or outcome"):
        contract_structure_summary(pd.DataFrame({"unit_rate_status": ["scored"]}))


# --- readout --------------------------------------------------------------------------

def _no_em_dash(obj) -> None:
    assert chr(0x2014) not in json.dumps(obj, default=str, ensure_ascii=False)


def test_readout_entries_carry_method_and_text_is_clean(lens7):
    deals, _, _ = lens7
    ro = contract_structure_readout(deals)
    assert ro["method"] == METHOD and ro["trade_check"]["method"] == METHOD
    for entry in ro["flags"]:
        assert entry["method"] == METHOD and "policy rule" in entry["label"].lower()
        assert entry["total_flagged"] >= len(entry["deals"])
        assert entry["truncated"] == (entry["total_flagged"] > len(entry["deals"]))
    for cov in ro["coverage"].values():
        assert cov["method"] == METHOD
    for d in ro["summary"].values():
        assert d["method"] == METHOD
    blob = json.dumps(ro, default=str, ensure_ascii=False).lower()
    _no_em_dash(ro)
    assert "margin" not in blob and "cogs" not in blob


def test_readout_lists_are_won_only_sorted_and_deterministic(lens7):
    deals, key, _ = lens7
    ro = contract_structure_readout(deals, n=1000)
    decoys = set(key["lost_decoys"])
    by_flag = {e["flag"]: e for e in ro["flags"]}
    assert len(by_flag) == 7
    for e in ro["flags"]:
        ids = [d["opportunity_id"] for d in e["deals"]]
        assert not decoys & set(ids) and len(ids) == len(set(ids)) == e["total_flagged"]
        assert all(list(d)[:4] == ["opportunity_id", "resolved_account_name", "segment",
                                   "value_metric"] for d in e["deals"])
    gaps = [d["unit_rate_gap_to_floor_acv"] for d in by_flag["unit_rate_below_floor"]["deals"]]
    assert gaps == sorted(gaps, reverse=True)
    prem = [d["overage_premium"] for d in by_flag["overage_fence_breach"]["deals"]]
    assert prem == sorted(prem)
    conc = [d["ramp_concession_tcv"] for d in by_flag["ramp_hidden_discount"]["deals"]]
    assert conc == sorted(conc, reverse=True)
    assert contract_structure_readout(deals, n=1000) == ro
    small = contract_structure_readout(deals, n=3)
    assert all(len(e["deals"]) <= 3 for e in small["flags"])
    assert any(e["truncated"] for e in small["flags"])


def test_readout_sentences_templates_and_ev_grid_note(lens7):
    deals, _, _ = lens7
    ro = contract_structure_readout(deals)
    by_flag = {e["flag"]: e for e in ro["flags"]}
    u = by_flag["unit_rate_below_floor"]
    assert re.match(r"^\d+ of \d+ scored won usage deals sit below the 15% unit-rate floor, "
                    r"\$[\d,]+ below floor in total\. Method: policy rule\.$", u["sentence"])
    assert cs.UNIT_RATE_GRID_NOTE in u["label"]  # five planted deals sit beyond 40 percent
    assert any(cs.UNIT_RATE_GRID_NOTE in d["label"] for d in u["deals"] if d["unit_rate_outside_ev_grid"])
    assert all(cs.UNIT_RATE_GRID_NOTE not in d["label"] for d in u["deals"] if not d["unit_rate_outside_ev_grid"])
    assert "List unit rate supplied" in u["label"]
    r = by_flag["ramp_hidden_discount"]
    assert "exceed it once the ramp is counted" in r["sentence"] and "no recorded approver" in r["sentence"]
    d0 = r["deals"][0]
    assert re.search(r"The steady-state discount is \d+\.\d%; counting the ramp, it is \d+\.\d%\.", d0["label"])
    assert "at or below their effective committed unit rate" in by_flag["overage_fence_breach"]["sentence"]
    assert ro["trade_check"]["total_flagged"] >= 1  # KA-05 sits in the trade check
    assert "KA-05" in [d["opportunity_id"] for d in ro["trade_check"]["deals"]]


def test_readout_share_note_under_fifteen_scored_deals():
    df = pd.DataFrame([dict(opportunity_id=f"S{i}", outcome="closed_won", value_metric="consumption",
                            list_acv=100000.0, booked_acv=80000.0, committed_acv=30000.0,
                            quantity=40000.0, overage_rate=1.2, term_months=12) for i in range(3)])
    ro = contract_structure_readout(contract_structure_deals(enrich(df)))
    low = next(e for e in ro["flags"] if e["flag"] == "low_commit_share")
    assert low["share_note"] == cs.SHARE_INSUFFICIENT_SENTENCE and low["total_flagged"] == 3
    assert np.isnan(ro["summary"]["commit_share"]["flagged_share"]["low_commit_share"])


def test_readout_ka14_without_ramp_columns_names_the_excluded_step():
    frame, _ = _frame_and_key(7)
    frame = frame.drop(columns=["ramp_year_1_acv", "ramp_year_2_acv"])
    enriched, _ = ingest_frame_verbose(frame, source="PK-32 no ramp cols")
    out = contract_structure_deals(enriched, columns_present=set(frame.columns))
    ro = contract_structure_readout(out, n=1000)
    e = next(x for x in ro["flags"] if x["flag"] == "off_invoice_below_floor")
    assert "Excludes ramp: not in the file." in e["label"]
    ka14 = next(d for d in e["deals"] if d["opportunity_id"] == "KA-14")
    assert "Excludes ramp: not in the file." in ka14["label"]
    assert ka14["steps_contributing"] == ["credits"]
    _no_em_dash(ro)


def test_readout_coverage_lists_first_ids_per_insufficient_reason(lens7):
    deals, key, _ = lens7
    ro = contract_structure_readout(deals, n=1000)
    cov = ro["coverage"]["unit_rate"]["insufficient_data_ids"]
    planted = [i for i in key["reasons"]["quantity_missing_or_zero"]]
    assert set(planted) <= set(cov["quantity_missing_or_zero"])
    assert cov["quantity_missing_or_zero"] == sorted(cov["quantity_missing_or_zero"])
    assert ro["coverage"]["unit_rate"]["counts"]["scored"] == ro["summary"]["unit_rate"]["n_scored"]


def test_deal_labels_exclude_only_columns_absent_from_the_file(lens7):
    deals, _, _ = lens7
    ro = contract_structure_readout(deals, n=1000)
    e = next(x for x in ro["flags"] if x["flag"] == "off_invoice_below_floor")
    assert "Excludes" not in e["label"]
    assert e["deals"] and all("Excludes" not in d["label"] for d in e["deals"])
    ka10 = next(d for d in e["deals"] if d["opportunity_id"] == "KA-10")
    assert "Excludes credits" not in ka10["label"]
    # attrs missing: infer from the data rather than defaulting to present
    bare = deals.copy()
    bare.attrs = {}
    again = contract_structure_readout(bare, n=1000)
    e2 = next(x for x in again["flags"] if x["flag"] == "off_invoice_below_floor")
    assert all("Excludes" not in d["label"] for d in e2["deals"])


def test_readout_sentences_use_the_floor_the_flags_were_computed_with():
    frame, _ = _frame_and_key(7)
    enriched, _ = ingest_frame_verbose(frame, source="PK-32 floor 0.20")
    out = contract_structure_deals(enriched, floor_frac=0.20, columns_present=set(frame.columns))
    ro = contract_structure_readout(out, n=1000)  # policy_threshold left at its 15 percent default
    by = {e["flag"]: e for e in ro["flags"]}
    assert "20% unit-rate floor" in by["unit_rate_below_floor"]["sentence"]
    assert "20% discount line" in by["ramp_hidden_discount"]["sentence"]
    won = out[out["is_won"]]
    n_below = int(won["unit_rate_below_floor"].fillna(False).astype(bool).sum())
    assert by["unit_rate_below_floor"]["total_flagged"] == n_below
    base = contract_structure_deals(enriched, columns_present=set(frame.columns))
    assert n_below != int(base[base["is_won"]]["unit_rate_below_floor"].fillna(False).astype(bool).sum())


def test_readout_ties_break_on_opportunity_id_ascending(lens7):
    deals, _, _ = lens7
    ro = contract_structure_readout(deals, n=1000)
    sort_cols = {"low_commit_share": ("uncommitted_booked_acv", None),
                 "overage_below_list_unit_rate": ("overage_rate", "list_unit_rate_used"),
                 "ramp_unapproved": ("ramp_concession_tcv", None),
                 "off_invoice_below_floor": ("pocket_acv", None)}
    lists = {e["flag"]: e["deals"] for e in ro["flags"]}
    lists["trade_check"] = ro["trade_check"]["deals"]
    key_fn = {
        "low_commit_share": lambda d: -d["uncommitted_booked_acv"],
        "overage_below_list_unit_rate": lambda d: d["overage_rate"] / d["list_unit_rate_used"],
        "ramp_unapproved": lambda d: -d["ramp_concession_tcv"],
        "off_invoice_below_floor": None,
        "trade_check": lambda d: -d["discount_amount"],
    }
    by_id = deals.set_index("opportunity_id")
    key_fn["off_invoice_below_floor"] = (
        lambda d: -(by_id.loc[d["opportunity_id"], "booked_acv"] - by_id.loc[d["opportunity_id"], "pocket_acv"]))
    for flag, fn in key_fn.items():
        rows = lists[flag]
        assert rows, flag
        keyed = [(fn(d), d["opportunity_id"]) for d in rows]
        assert keyed == sorted(keyed), flag


def test_readout_tie_break_with_identical_sort_keys_in_shuffled_order():
    rng = np.random.default_rng(3)
    usage = dict(value_metric="consumption", list_acv=100000.0, booked_acv=80000.0,
                 committed_acv=30000.0, quantity=40000.0, list_unit_rate=1.0,
                 overage_rate=0.5, term_months=12)  # low commit, below list, trade check
    ramp = dict(value_metric="seats", list_acv=100000.0, booked_acv=90000.0, term_months=36,
                ramp_year_1_acv=60000.0, ramp_year_2_acv=80000.0)  # hidden, unapproved, off invoice
    rows = [dict(opportunity_id=f"T{i:02d}", outcome="closed_won", approved_by="",
                 **(usage if i % 2 else ramp)) for i in range(40)]
    order = rng.permutation(len(rows))
    df = enrich(pd.DataFrame([rows[i] for i in order]))
    ro = contract_structure_readout(contract_structure_deals(df), n=1000)
    lists = {e["flag"]: e["deals"] for e in ro["flags"]}
    lists["trade_check"] = ro["trade_check"]["deals"]
    for flag in ("low_commit_share", "overage_below_list_unit_rate", "ramp_unapproved",
                 "off_invoice_below_floor", "trade_check"):
        ids = [d["opportunity_id"] for d in lists[flag]]
        assert len(ids) == 20 and ids == sorted(ids), flag
