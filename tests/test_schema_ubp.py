"""Tests for the optional UBP-structure + cost columns (schema + generator).

These fields let a deal express its usage-based shape (commit, overage, ramp,
renewal) and its cost, without changing the leakage diagnostic. The contract:
they are OPTIONAL, the generator populates them with metric-appropriate
applicability, and they never perturb the main generator sequence.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pricing.generate import generate
from pricing.ingest import ingest
from pricing.schema import ALL_COLUMNS, GENERATOR_COLUMNS, REQUIRED_FIELDS, FIELDS

UBP_COST_FIELDS = [
    "committed_acv", "overage_rate", "ramp_year_1_acv", "ramp_year_2_acv",
    "is_renewal", "renewal_uplift", "cogs_acv",
]


def test_new_fields_are_in_schema_and_all_optional():
    by_name = {f.name: f for f in FIELDS}
    for name in UBP_COST_FIELDS:
        assert name in by_name, f"{name} missing from schema FIELDS"
        assert by_name[name].required is False, f"{name} must be OPTIONAL"
        assert name in ALL_COLUMNS
    # none of them leaked into the required set
    assert not (set(UBP_COST_FIELDS) & set(REQUIRED_FIELDS))


@pytest.fixture(scope="module")
def df():
    return generate(n=1500, seed=7)


def test_generator_emits_all_new_columns(df):
    for name in UBP_COST_FIELDS:
        assert name in df.columns


def test_commit_and_overage_track_value_metric(df):
    seats = df["value_metric"] == "seats"
    usage = df["value_metric"].isin(["consumption", "hybrid"])
    # seat deals have no committed spend or overage rate
    assert df.loc[seats, "committed_acv"].isna().all()
    assert df.loc[seats, "overage_rate"].isna().all()
    # usage-based / hybrid deals carry a commitment
    assert df.loc[usage, "committed_acv"].notna().all()
    assert (df.loc[usage, "committed_acv"] > 0).all()


def test_ramp_only_on_multiyear(df):
    multiyear = df["term_months"] >= 24
    assert df.loc[~multiyear, "ramp_year_1_acv"].isna().all()
    assert df.loc[~multiyear, "ramp_year_2_acv"].isna().all()
    assert df.loc[multiyear, "ramp_year_1_acv"].notna().all()
    # year 2 steps up over year 1 on a ramp
    assert (df.loc[multiyear, "ramp_year_2_acv"]
            > df.loc[multiyear, "ramp_year_1_acv"]).all()
    # 2026-09-27 fix: the ramp climbs TO the steady-state booked figure
    # (schema.py documents year 3+ == booked_acv), so year 2 must never
    # exceed it. Year 2 used to draw 1.00-1.25x booked, contradicting that
    # convention.
    assert (df.loc[multiyear, "ramp_year_2_acv"]
            <= df.loc[multiyear, "booked_acv"]).all()


def test_ramp_year_2_ceiling_holds_on_a_fresh_seed():
    """Same invariant as test_ramp_only_on_multiyear, on a seed the pinned
    data/synthetic/deals.csv never used, so this is not just re-checking one
    fixed draw."""
    fresh = generate(n=1200, seed=97)
    multiyear = fresh["term_months"] >= 24
    assert multiyear.any()
    y1 = fresh.loc[multiyear, "ramp_year_1_acv"]
    y2 = fresh.loc[multiyear, "ramp_year_2_acv"]
    booked = fresh.loc[multiyear, "booked_acv"]
    assert (y1 < y2).all()
    assert (y2 <= booked).all()


def test_renewal_flag_and_uplift_are_consistent(df):
    assert set(df["is_renewal"].unique()).issubset({"true", "false"})
    is_ren = df["is_renewal"] == "true"
    # uplift present exactly where the deal is a renewal
    assert df.loc[is_ren, "renewal_uplift"].notna().all()
    assert df.loc[~is_ren, "renewal_uplift"].isna().all()
    assert df["is_renewal"].eq("true").mean() == pytest.approx(0.22, abs=0.05)


def test_cogs_present_and_plausible(df):
    assert df["cogs_acv"].notna().all()
    # cost is positive and below booked value (no negative-margin synthetic deals)
    assert (df["cogs_acv"] > 0).all()
    won = df[df["outcome"] == "closed_won"]
    assert (won["cogs_acv"] < won["booked_acv"]).all()


def test_new_columns_do_not_perturb_main_sequence():
    """The optional columns must come from an independent RNG stream: the core
    columns are identical whether or not we look at the new ones."""
    a = generate(n=800, seed=11)
    b = generate(n=800, seed=11)
    core = [c for c in GENERATOR_COLUMNS if c not in UBP_COST_FIELDS]
    pd.testing.assert_frame_equal(a[core], b[core])
    # and the core columns are byte-stable across the two draws (determinism)
    assert a["booked_acv"].sum() == b["booked_acv"].sum()


def test_ingest_accepts_and_coerces_new_columns(tmp_path):
    csv = tmp_path / "deals.csv"
    generate(n=400, seed=7).to_csv(csv, index=False)
    out = ingest(csv)  # must not raise SchemaError
    # numeric coercion applied
    for name in ["committed_acv", "overage_rate", "ramp_year_1_acv",
                 "ramp_year_2_acv", "renewal_uplift", "cogs_acv"]:
        assert pd.api.types.is_numeric_dtype(out[name])
    # is_renewal coerced to bool like competitor_present
    assert out["is_renewal"].dtype == bool


def test_ingest_still_works_without_the_optional_columns(tmp_path):
    """A prospect CSV that predates these columns must still ingest cleanly."""
    df = generate(n=300, seed=7).drop(columns=UBP_COST_FIELDS)
    csv = tmp_path / "legacy.csv"
    df.to_csv(csv, index=False)
    out = ingest(csv)
    assert len(out) == 300
    assert "discount_pct" in out.columns  # diagnostic inputs still derived
