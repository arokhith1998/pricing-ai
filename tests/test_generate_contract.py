"""PK-31: planted contract-structure known answers in the generator.

The planted stream (seed + 3) is opt-in and must not move a single byte of the
default output. These tests pin that, and check the planted population and the
hand-built KA cases against the spec
(docs/design/2026-11-07-contract-structure-lens-spec.md, section 6).

No lens is implemented or imported here: that is PK-32. The key is produced by
the oracle in pricing/generate.py, and the spec's worked examples below are
typed in as literals so the oracle is checked against the spec text, not
against itself.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from pricing import generate as gen
from pricing.generate import (
    CONTRACT_COLUMNS, KEY_COLUMNS, KNOWN_ANSWER_CASES, contract_expected_levers,
    generate, generate_contract_fixture, generate_known_answer_cases,
    write_contract_fixtures,
)
from pricing.ingest import ingest_frame_verbose
from pricing.schema import ALL_COLUMNS, GENERATOR_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "contract_structure"
# sha256 of generate(n=2000, seed=7).to_csv(index=False) as UTF-8 text, taken
# on origin/main at 0976558 before PK-31. Pinned with an explicit CRLF line
# terminator: the value was taken on Windows, and to_csv defaults to os.linesep,
# so without this the same data hashes differently on Linux CI.
PINNED_SHA256 = "ecfa1b6b25bd69d8258ced8d88ded57d21e31e87fc45166cdc8a2c306143ea48"
CRLF = chr(13) + chr(10)


def _sha(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False, lineterminator=CRLF).encode("utf-8")).hexdigest()


# --- default output is unchanged -------------------------------------------------

PINNED_COLUMN_SHA12 = {"opportunity_id": "781ac24a15f4", "account_id": "02da12607669", "account_name": "cc7e876907a4", "outcome": "d95d30d3ba4a", "created_date": "d1cd1a78ca9c", "close_date": "1632efa4c6d1", "segment": "37012db6bbea", "region": "a40fe57313d2", "industry": "9c0977ccb326", "business_unit": "5fe328c7930d", "product_line": "4c9758345c61", "product_family": "3aa5fad5ef5e", "product_tier": "1aebbc3390bb", "sku": "936c8013d6ee", "value_metric": "46baf58525e9", "list_acv": "e57cf4741fa1", "booked_acv": "e1ce25a10fb4", "platform_fee_acv": "7e287173a957", "usage_acv": "096250ede28c", "term_months": "e637202a7b84", "quantity": "98df75176b14", "rep_id": "88020e8d6b49", "approved_by": "c3a2dc7bc87a", "competitor_present": "c9238be1942c", "lost_reason": "058061c27a4b", "currency": "e89bc4d234c0", "committed_acv": "2dd66fb844a1", "overage_rate": "d80662bab12d", "ramp_year_1_acv": "7be67221ec9b", "ramp_year_2_acv": "76d30818fb9e", "is_renewal": "61ab1cdbd851", "renewal_uplift": "0db9758b9f7f", "cogs_acv": "63fd271fbb51"}


def test_default_output_is_byte_identical():
    df = generate(n=2000, seed=7)
    cols = {c: hashlib.sha256(df[[c]].to_csv(index=False, lineterminator=CRLF).encode("utf-8")).hexdigest()[:12]
            for c in df.columns}
    assert cols == PINNED_COLUMN_SHA12  # names the columns that moved
    assert _sha(df) == PINNED_SHA256


def test_planting_does_not_perturb_the_default_stream():
    before = _sha(generate(n=2000, seed=7))
    generate_contract_fixture(seed=7)
    generate_known_answer_cases()
    assert _sha(generate(n=2000, seed=7)) == before == PINNED_SHA256


def test_default_output_has_no_new_columns():
    df = generate(n=300, seed=7)
    assert "list_unit_rate" not in df.columns and "credits_tcv" not in df.columns
    assert list(df.columns[:len(GENERATOR_COLUMNS)]) == GENERATOR_COLUMNS


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def test_synthetic_deals_csv_matches_origin_main():
    rev = _git("rev-parse", "--verify", "-q", "origin/main")
    if rev.returncode != 0:
        pytest.skip("origin/main is not available in this checkout")
    diff = _git("diff", "--quiet", "origin/main", "--", "data/synthetic/deals.csv")
    assert diff.returncode == 0, "data/synthetic/deals.csv differs from origin/main"


# --- the hand-built KA cases ------------------------------------------------------

# Spec section 6.1 inputs, retyped: id, vm, outcome, list, booked, commit, qty,
# plat fee, list unit, overage, term, y1, y2, credits.
SPEC_INPUTS = {
    "KA-01": ("consumption", "closed_won", 100000, 85000, 85000, 100000, None, None, 1.10, 12, None, None, None),
    "KA-02": ("consumption", "closed_won", 200000, 160000, 120000, 200000, None, 1.00, 0.70, 12, None, None, None),
    "KA-03": ("consumption", "closed_won", 100000, 90000, 60000, 75000, None, 1.00, 0.80, 12, None, None, None),
    "KA-04": ("consumption", "closed_won", 120000, 102000, 90000, 100000, None, None, 0.75, 12, None, None, None),
    "KA-05": ("consumption", "closed_won", 100000, 80000, 30000, 40000, None, 1.00, 1.20, 12, None, None, None),
    "KA-06": ("consumption", "closed_won", 100000, 90000, 90000, 0, None, None, 1.00, 12, None, None, None),
    "KA-07": ("hybrid", "closed_won", 150000, 120000, 100000, 100000, 50000, 0.80, 0.40, 12, None, None, None),
    "KA-08": ("hybrid", "closed_won", 150000, 120000, 100000, 100000, None, 0.80, 0.40, 12, None, None, None),
    "KA-09": ("seats", "closed_won", 100000, 90000, None, 100, None, None, None, 12, None, None, None),
    "KA-10": ("seats", "closed_won", 100000, 90000, None, 100, None, None, None, 36, 60000, 80000, None),
    "KA-11": ("seats", "closed_won", 100000, 88000, None, 100, None, None, None, 36, 88000, 88000, None),
    "KA-12": ("seats", "closed_won", 100000, 90000, None, 100, None, None, None, 36, 70000, None, None),
    "KA-13": ("seats", "closed_won", 100000, 100000, None, 100, None, None, None, 18, 50000, 90000, None),
    "KA-14": ("seats", "closed_won", 100000, 90000, None, 100, None, None, None, 24, None, None, 20000),
    "KA-17": ("consumption", "closed_won", 100000, 60000, 50000, 50000, None, 2.00, None, 12, None, None, None),
    "KA-18": ("consumption", "closed_won", 105000, 110000, 110000, 100000, None, 1.00, 1.30, 12, None, None, None),
    "KA-19": ("consumption", "closed_won", 50000, 50000, 50000, 50000, None, None, 0, 12, None, None, None),
    "KA-20": ("consumption", "closed_won", 100000, 90000, None, 100000, None, None, 1.20, 12, None, None, None),
    "KA-21": ("consumption", "closed_won", 100000, 100000, 110000, 100000, None, None, 1.20, 12, None, None, None),
    "KA-22": ("consumption", "closed_lost", 120000, 102000, 90000, 100000, None, None, 0.75, 12, None, None, None),
    "KA-24": ("seats", "closed_won", 100000, 90000, None, 100, None, None, None, 36, 95000, 90000, None),
    "KA-25": ("seats", "closed_won", 100000, 90000, None, 100, None, None, None, 12, 70000, 80000, None),
    "KA-26": ("seats", "closed_won", 100000, 90000, None, 100, None, None, None, None, None, None, 5000),
}
INPUT_COLS = ["value_metric", "outcome", "list_acv", "booked_acv", "committed_acv",
              "quantity", "platform_fee_acv", "list_unit_rate", "overage_rate",
              "term_months", "ramp_year_1_acv", "ramp_year_2_acv", "credits_tcv"]


@pytest.fixture(scope="module")
def ka():
    return generate_known_answer_cases()


def test_every_ka_case_appears_exactly_once_with_spec_inputs(ka):
    deals, _ = ka
    assert sorted(deals["opportunity_id"]) == sorted(SPEC_INPUTS)
    assert deals["opportunity_id"].is_unique
    assert [c[0] for c in KNOWN_ANSWER_CASES] == [d for d in deals["opportunity_id"]]
    by_id = deals.set_index("opportunity_id")
    for cid, want in SPEC_INPUTS.items():
        got = by_id.loc[cid, INPUT_COLS]
        for col, w in zip(INPUT_COLS, want):
            g = got[col]
            if w is None:
                assert pd.isna(g), f"{cid}.{col} should be blank, got {g!r}"
            elif isinstance(w, str):
                assert g == w, f"{cid}.{col}"
            else:
                assert float(g) == pytest.approx(w), f"{cid}.{col}"
    assert (deals["segment"] == "MidMarket").all() and (deals["currency"] == "USD").all()


def test_ka_key_has_five_levers_per_case(ka):
    _, key = ka
    assert list(key.columns) == KEY_COLUMNS
    assert len(key) == 5 * len(SPEC_INPUTS)
    assert (key.groupby("opportunity_id")["lever"].apply(list)
            == pd.Series([["unit_rate", "commit_share", "overage_fence", "ramp", "waterfall"]]
                         * len(SPEC_INPUTS), index=sorted(SPEC_INPUTS))).all()
    assert (key["case_id"] == key["opportunity_id"]).all()
    assert set(key["state"]) <= {"scored", "insufficient_data", "not_provided"}


def _k(key, cid, lever):
    r = key[(key.opportunity_id == cid) & (key.lever == lever)]
    assert len(r) == 1
    return r.iloc[0]


# (case, lever, expected state, reason, {field: text at spec rounding}) typed from
# spec sections 3.1 to 3.5 and 6.1.
SPEC_OUTPUTS = [
    ("KA-01", "unit_rate", "scored", "", dict(list_unit_rate_basis="derived", effective_committed_unit_rate="0.850000", unit_rate_realization="0.850000", unit_rate_below_floor="false", unit_rate_gap_to_floor_acv="0.00")),
    ("KA-01", "commit_share", "scored", "", dict(commit_share_of_booked="1.000000", low_commit_share="false")),
    ("KA-01", "overage_fence", "scored", "", dict(overage_premium="0.294118", overage_fence_breach="false", overage_below_list_unit_rate="false")),
    ("KA-01", "ramp", "not_provided", "no_ramp_recorded", {}),
    ("KA-01", "waterfall", "not_provided", "no_off_invoice_steps", {}),
    ("KA-02", "unit_rate", "scored", "", dict(effective_committed_unit_rate="0.600000", unit_rate_realization="0.600000", unit_rate_discount="0.400000", unit_rate_below_floor="true", unit_rate_gap_to_floor_acv="50000.00", unit_rate_outside_ev_grid="false")),
    ("KA-02", "commit_share", "scored", "", dict(commit_share_of_booked="0.750000", low_commit_share="false")),
    ("KA-02", "overage_fence", "scored", "", dict(overage_premium="0.166667", overage_fence_breach="false", overage_below_list_unit_rate="true")),
    ("KA-03", "unit_rate", "scored", "", dict(effective_committed_unit_rate="0.800000", unit_rate_realization="0.800000", unit_rate_below_floor="true", unit_rate_gap_to_floor_acv="3750.00")),
    ("KA-03", "commit_share", "scored", "", dict(commit_share_of_booked="0.666667")),
    # overage equal to the effective unit rate: premium exactly zero, a breach
    ("KA-03", "overage_fence", "scored", "", dict(overage_premium="0.000000", overage_fence_breach="true", overage_below_list_unit_rate="true")),
    ("KA-04", "unit_rate", "insufficient_data", "list_unit_rate_unavailable", dict(effective_committed_unit_rate="0.900000", list_unit_rate_basis="unavailable")),
    ("KA-04", "commit_share", "scored", "", dict(commit_share_of_booked="0.882353")),
    ("KA-04", "overage_fence", "scored", "", dict(overage_premium="-0.166667", overage_fence_breach="true", overage_below_list_unit_rate="")),
    ("KA-05", "unit_rate", "scored", "", dict(effective_committed_unit_rate="0.750000", unit_rate_below_floor="true", unit_rate_gap_to_floor_acv="4000.00")),
    ("KA-05", "commit_share", "scored", "", dict(commit_share_of_booked="0.375000", low_commit_share="true", uncommitted_booked_acv="50000.00")),
    ("KA-05", "overage_fence", "scored", "", dict(overage_premium="0.600000", overage_fence_breach="false")),
    # zero quantity: levers 1 and 3 insufficient, lever 2 still scored
    ("KA-06", "unit_rate", "insufficient_data", "quantity_missing_or_zero", dict(effective_committed_unit_rate="")),
    ("KA-06", "commit_share", "scored", "", dict(commit_share_of_booked="1.000000", low_commit_share="false")),
    ("KA-06", "overage_fence", "insufficient_data", "quantity_missing_or_zero", {}),
    # hybrid: committed_acv includes the platform fee
    ("KA-07", "unit_rate", "scored", "", dict(committed_usage_acv="50000.00", effective_committed_unit_rate="0.500000", unit_rate_realization="0.625000", unit_rate_below_floor="true", unit_rate_floor="0.680000", unit_rate_gap_to_floor_acv="18000.00")),
    ("KA-07", "commit_share", "scored", "", dict(commit_share_of_booked="0.833333", low_commit_share="false")),
    ("KA-07", "overage_fence", "scored", "", dict(overage_premium="-0.200000", overage_fence_breach="true", overage_below_list_unit_rate="true")),
    ("KA-08", "unit_rate", "insufficient_data", "platform_fee_missing_for_hybrid", {}),
    ("KA-08", "commit_share", "scored", "", dict(commit_share_of_booked="0.833333")),
    ("KA-08", "overage_fence", "insufficient_data", "platform_fee_missing_for_hybrid", {}),
    ("KA-09", "unit_rate", "not_provided", "value_metric_seats", {}),
    ("KA-09", "commit_share", "not_provided", "value_metric_seats", {}),
    ("KA-09", "overage_fence", "not_provided", "value_metric_seats", {}),
    ("KA-10", "ramp", "scored", "", dict(ramp_depth_year_1="0.333333", ramp_depth_year_2="0.111111", ramp_concession_tcv="40000.00", contracted_tcv="230000.00", list_tcv="300000.00", tcv_weighted_effective_discount="0.233333", ramp_discount_increment="0.133333", ramp_concession_pct_of_booked_tcv="0.148148", ramp_hidden_discount="true", ramp_unapproved="true")),
    ("KA-10", "waterfall", "scored", "", dict(wf_ramp_concession_acv="13333.33", wf_credits_step_status="not_provided", pocket_acv="76666.67", pocket_realization="0.766667", off_invoice_below_floor="true")),
    # flat ramp must equal the flat discount
    ("KA-11", "ramp", "scored", "", dict(ramp_concession_tcv="0.00", tcv_weighted_effective_discount="0.120000", ramp_discount_increment="0.000000", ramp_hidden_discount="false")),
    ("KA-11", "waterfall", "scored", "", dict(pocket_acv="88000.00", off_invoice_below_floor="false")),
    # missing ramp year 2 is insufficient_data, never read as steady state
    ("KA-12", "ramp", "insufficient_data", "ramp_year_2_missing", {}),
    ("KA-12", "waterfall", "insufficient_data", "ramp_step_insufficient", {}),
    ("KA-13", "ramp", "scored", "", dict(ramp_concession_tcv="55000.00", contracted_tcv="95000.00", tcv_weighted_effective_discount="0.366667", ramp_hidden_discount="true")),
    ("KA-14", "ramp", "not_provided", "no_ramp_recorded", {}),
    ("KA-14", "waterfall", "scored", "", dict(wf_ramp_concession_acv="0.00", wf_ramp_step_status="scored", wf_credits_acv="10000.00", pocket_acv="80000.00", pocket_realization="0.800000", off_invoice_below_floor="true")),
    ("KA-17", "unit_rate", "scored", "", dict(effective_committed_unit_rate="1.000000", unit_rate_realization="0.500000", unit_rate_discount="0.500000", unit_rate_below_floor="true", unit_rate_gap_to_floor_acv="35000.00", unit_rate_outside_ev_grid="true")),
    ("KA-17", "overage_fence", "not_provided", "overage_rate_blank", {}),
    ("KA-18", "unit_rate", "scored", "", dict(list_unit_rate_basis="supplied", unit_rate_realization="1.100000", unit_rate_below_floor="false")),
    ("KA-18", "overage_fence", "scored", "", dict(overage_premium="0.181818", overage_fence_breach="false")),
    ("KA-19", "unit_rate", "scored", "", dict(list_unit_rate_basis="derived", unit_rate_realization="1.000000")),
    ("KA-19", "overage_fence", "scored", "", dict(overage_premium="-1.000000", overage_fence_breach="true")),
    ("KA-20", "unit_rate", "not_provided", "committed_acv_blank", {}),
    ("KA-20", "commit_share", "not_provided", "committed_acv_blank", {}),
    ("KA-20", "overage_fence", "not_provided", "no_commitment", {}),
    ("KA-21", "unit_rate", "insufficient_data", "commit_exceeds_booked", {}),
    ("KA-21", "commit_share", "insufficient_data", "commit_exceeds_booked", {}),
    ("KA-21", "overage_fence", "insufficient_data", "commit_exceeds_booked", {}),
    ("KA-22", "overage_fence", "scored", "", dict(overage_premium="-0.166667", overage_fence_breach="true")),
    ("KA-24", "ramp", "insufficient_data", "ramp_above_steady_state", {}),
    ("KA-25", "ramp", "insufficient_data", "ramp_on_single_year_term", {}),
    ("KA-26", "ramp", "not_provided", "no_ramp_recorded", {}),
    ("KA-26", "waterfall", "insufficient_data", "term_months_missing", {}),
]


@pytest.mark.parametrize("cid,lever,state,reason,fields", SPEC_OUTPUTS,
                         ids=[f"{c}-{lv}" for c, lv, *_ in SPEC_OUTPUTS])
def test_ka_key_matches_spec_worked_examples(ka, cid, lever, state, reason, fields):
    row = _k(ka[1], cid, lever)
    assert row["state"] == state
    assert row["reason"] == reason
    for field, want in fields.items():
        assert row[field] == want, f"{cid} {lever} {field}: {row[field]!r} != {want!r}"


def test_ka_flat_ramp_equals_flat_discount(ka):
    deals, key = ka
    r = _k(key, "KA-11", "ramp")
    disc = 1 - 88000 / 100000
    assert float(r["tcv_weighted_effective_discount"]) == pytest.approx(disc, abs=1e-9)
    assert float(r["ramp_concession_tcv"]) == 0.0


def test_ka_lost_decoy_is_flagged_per_deal_but_marked_lost(ka):
    _, key = ka
    assert _k(key, "KA-22", "overage_fence")["won"] == "false"
    assert (key.loc[key.opportunity_id != "KA-22", "won"] == "true").all()


def test_ka_blank_cells_stay_blank_on_flags_of_unscored_levers(ka):
    _, key = ka
    flag_cols = [f for f, k in sum((v for v in gen.LEVER_OUTPUTS.values()), []) if k == "b"]
    unscored = key[key["state"] != "scored"]
    assert (unscored[flag_cols] == "").all().all()


# --- the planted bulk population ---------------------------------------------------

@pytest.fixture(scope="module")
def pop():
    return generate_contract_fixture(n=600, seed=7)


def test_population_shape(pop):
    deals, _ = pop
    assert list(deals.columns) == CONTRACT_COLUMNS
    assert set(CONTRACT_COLUMNS) <= set(ALL_COLUMNS)
    assert len(deals) == 600 and deals["opportunity_id"].is_unique
    assert (deals["outcome"] == "closed_won").sum() == 420
    assert deals["value_metric"].value_counts().to_dict() == {
        "consumption": 200, "hybrid": 200, "seats": 200}
    assert deals["cogs_acv"].isna().all(), "planted deals carry no cost input"


def test_population_planted_set_sizes(pop):
    _, key = pop
    f, r = key["flags"], key["reasons"]
    assert len(f["overage_fence_breach"]) == 40
    assert f["overage_fence_breach"] == f["overage_below_list_unit_rate"]
    assert len(f["unit_rate_below_floor"]) == 25
    assert len(f["low_commit_share"]) == 20
    assert len(f["ramp_hidden_discount"]) == 30
    assert len(f["ramp_unapproved"]) == 10
    assert set(f["ramp_unapproved"]) <= set(f["ramp_hidden_discount"])
    assert len(f["off_invoice_below_floor"]) == 45
    assert set(f["ramp_hidden_discount"]) <= set(f["off_invoice_below_floor"])
    for code in ("quantity_missing_or_zero", "platform_fee_missing_for_hybrid",
                 "list_unit_rate_unavailable", "commit_exceeds_booked",
                 "ramp_year_2_missing", "ramp_above_steady_state"):
        assert len(r[code]) == 10, code
    assert len(key["lost_decoys"]) == 20


def test_planted_sets_are_disjoint_where_the_spec_says(pop):
    _, key = pop
    f = key["flags"]
    disjoint = ["overage_fence_breach", "unit_rate_below_floor", "low_commit_share",
                "ramp_hidden_discount"]
    seen: set[str] = set()
    for name in disjoint:
        ids = set(f[name])
        assert not (ids & seen), name
        seen |= ids
    assert not (set(f["off_invoice_below_floor"]) - set(f["ramp_hidden_discount"])) & seen
    insufficient = [set(key["reasons"][c]) for c in (
        "quantity_missing_or_zero", "platform_fee_missing_for_hybrid",
        "list_unit_rate_unavailable", "commit_exceeds_booked",
        "ramp_year_2_missing", "ramp_above_steady_state")]
    for i, a in enumerate(insufficient):
        for b in insufficient[i + 1:]:
            assert not (a & b)
        assert not (a & seen)


def test_lost_decoys_appear_in_no_won_list(pop):
    deals, key = pop
    decoys = set(key["lost_decoys"])
    lost = set(deals.loc[deals["outcome"] == "closed_lost", "opportunity_id"])
    assert decoys <= lost
    listed = {i for ids in key["flags"].values() for i in ids}
    listed |= {i for ids in key["reasons"].values() for i in ids}
    assert not (decoys & listed)
    # they are built like fence-breach rows: per deal the fence is breached
    by_id = deals.set_index("opportunity_id")
    for i in key["lost_decoys"]:
        res = contract_expected_levers(by_id.loc[i].to_dict() | {"opportunity_id": i})
        assert res["overage_fence"]["overage_fence_breach"] is True


def test_planted_deals_sit_two_points_clear_of_every_other_threshold(pop):
    """No planted or clean deal lands within 2 points of a threshold it is not
    planted on: the bands below are empty, so the key holds no boundary noise."""
    deals, _ = pop
    bands = {  # (field, lever, lo, hi): open interval that must hold no deal
        ("unit_rate_realization", "unit_rate"): [(0.83, 0.87), (0.58, 0.62)],
        ("commit_share_of_booked", "commit_share"): [(0.48, 0.52)],
        ("overage_premium", "overage_fence"): [(0.0, 0.02)],
        ("tcv_weighted_effective_discount", "ramp"): [(0.13, 0.17)],
        ("pocket_realization", "waterfall"): [(0.83, 0.87)],
    }
    for rec in deals.to_dict("records"):
        res = contract_expected_levers(rec)
        for (field, lever), spans in bands.items():
            v = res[lever][field]
            if v is None:
                continue
            for lo, hi in spans:
                assert not (lo < v < hi), (rec["opportunity_id"], field, v)
        # discount_pct on a ramp or credits deal is at or below 0.13
        if res["ramp"]["status"] == "scored":
            assert 1 - rec["booked_acv"] / rec["list_acv"] <= 0.1300001


def test_waterfall_consistency_on_ramp_only_deals(pop):
    deals, _ = pop
    n = 0
    for rec in deals.to_dict("records"):
        res = contract_expected_levers(rec)
        if res["ramp"]["status"] == "scored" and pd.isna(rec["credits_tcv"]):
            n += 1
            wf = res["waterfall"]
            assert wf["pocket_realization"] == pytest.approx(
                round(1 - res["ramp"]["tcv_weighted_effective_discount"], 6), abs=2e-6)
            assert wf["off_invoice_below_floor"] == res["ramp"]["ramp_hidden_discount"]
    assert n == 30


def test_usage_deals_carry_a_list_unit_rate_except_the_planted_unavailable(pop):
    deals, key = pop
    usage = deals[deals["value_metric"] != "seats"]
    missing = set(usage.loc[usage["list_unit_rate"].isna(), "opportunity_id"])
    assert missing == set(key["reasons"]["list_unit_rate_unavailable"])
    assert deals.loc[deals["value_metric"] == "seats", "list_unit_rate"].isna().all()
    credit_ids = set(deals.loc[deals["credits_tcv"].notna(), "opportunity_id"])
    assert len(credit_ids) == 15 and credit_ids <= set(key["flags"]["off_invoice_below_floor"])


def test_population_is_reproducible_from_the_seed():
    d1, k1 = generate_contract_fixture(n=600, seed=7)
    d2, k2 = generate_contract_fixture(n=600, seed=7)
    assert d1.equals(d2) and k1 == k2
    assert _sha(d1) == _sha(d2)
    d3, k3 = generate_contract_fixture(n=600, seed=11)
    assert k3 != k1 and not d3.equals(d1)


@pytest.mark.parametrize("seed", [11, 23])
def test_other_seeds_also_plant_cleanly(seed):
    # generate_contract_fixture raises if any planted set drifts, so reaching
    # the assertions means the designed sets and the oracle agree.
    deals, key = generate_contract_fixture(n=600, seed=seed)
    assert len(key["flags"]["overage_fence_breach"]) == 40
    assert len(key["flags"]["ramp_hidden_discount"]) == 30
    assert (deals["outcome"] == "closed_won").sum() == 420


def test_population_reads_ingest_clean_with_no_errors(pop, ka):
    pop_deals, _ = pop
    ka_deals, _ = ka
    frame = pd.concat([ka_deals, pop_deals], ignore_index=True)
    enriched, report = ingest_frame_verbose(frame, source="PK-31 planted fixture")
    assert len(enriched) == len(frame) == 623
    assert report.rows_kept == 623
    assert not report.blockers and not report.conflicting_ids
    assert report.exact_duplicates_dropped == 0 and not report.excluded_open
    assert report.currencies in ([], ["USD"]) or set(report.currencies) <= {"USD", "$"}
    # lens-input columns survive coercion with their planted values
    by_id = enriched.set_index("opportunity_id")
    assert by_id.loc["KA-07", "list_unit_rate"] == pytest.approx(0.80)
    assert by_id.loc["KA-14", "credits_tcv"] == pytest.approx(20000.0)
    assert pd.isna(by_id.loc["KA-26", "term_months"])
    # ingest does not re-base the steady-state discount on the ramp deal
    assert by_id.loc["KA-10", "discount_pct"] == pytest.approx(0.10)


def test_population_alone_ingests_without_error(pop):
    deals, _ = pop
    enriched, report = ingest_frame_verbose(deals, source="PK-31 population")
    assert len(enriched) == 600 and not report.blockers


# --- the key file -----------------------------------------------------------------

def test_key_file_round_trips(tmp_path, ka):
    _, key = ka
    key_path, deals_path = write_contract_fixtures(tmp_path)
    assert key_path.name == "known_answers.csv"
    back = pd.read_csv(key_path, dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(back, key)
    # input rows round-trip through ingest-compatible CSV text
    deals_back = pd.read_csv(deals_path, dtype=str, keep_default_na=False)
    assert list(deals_back["opportunity_id"]) == [c[0] for c in KNOWN_ANSWER_CASES]
    assert list(deals_back.columns) == CONTRACT_COLUMNS


def test_key_file_is_reproducible(tmp_path):
    a, _ = write_contract_fixtures(tmp_path / "a")
    b, _ = write_contract_fixtures(tmp_path / "b")
    assert a.read_bytes() == b.read_bytes()


def test_committed_fixture_is_current():
    committed = FIXTURE_DIR / "known_answers.csv"
    assert committed.exists(), "run: python -m pricing.generate --contract-fixture-dir tests/fixtures/contract_structure"
    _, key = generate_known_answer_cases()
    back = pd.read_csv(committed, dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(back, key)
    deals, _ = generate_known_answer_cases()
    dback = pd.read_csv(FIXTURE_DIR / "known_answer_deals.csv", dtype=str, keep_default_na=False)
    assert list(dback["opportunity_id"]) == list(deals["opportunity_id"])


# --- hard constraints ----------------------------------------------------------------

def test_no_margin_label_and_no_cost_input_in_the_planted_stream():
    src = Path(gen.__file__).read_text(encoding="utf-8")
    start = src.index("# Contract-structure planted stream (PK-31)")
    block = src[start:src.index("def main()")]
    assert "margin" not in block.lower()
    assert chr(0x2014) not in block and chr(0x2013) not in block
    assert 'row.get("cogs_acv")' not in block and 'rec["cogs_acv"]' not in block
    assert "margin" not in " ".join(KEY_COLUMNS).lower()
    assert not any("cogs" in c or "cost" in c for c in KEY_COLUMNS)

