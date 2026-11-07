"""PK-23: source, provenance and contract-structure fields on the canonical deal."""

from __future__ import annotations

import pandas as pd
import pytest

from pricing.generate import generate
from pricing.ingest import _FX_MONEY_COLS, _NUMERIC, _NUMERIC_NONMONEY, ingest
from pricing.mapping import SYNONYMS
from pricing.schema import (
    ALL_COLUMNS, ALL_FIELD_NAMES, FIELDS, PROVENANCE_DEFAULTS, PROVENANCE_FIELDS,
    REQUIRED_FIELDS, InvalidEnumValueError, apply_provenance_defaults,
    validate_provenance_enums,
)

NEW = ["source_system", "source_record_id", "source_account_id", "source_quote_id",
       "source_url", "value_metric_unit", "cost_basis", "list_unit_rate",
       "credits_tcv"]


def test_nine_fields_exist_and_are_optional():
    by_name = {f.name: f for f in FIELDS}
    assert sorted(NEW) == sorted(PROVENANCE_FIELDS)
    for n in NEW:
        assert n in by_name
        assert by_name[n].required is False
    assert not (set(NEW) & set(REQUIRED_FIELDS))


def test_types_and_defaults():
    by_name = {f.name: f for f in FIELDS}
    assert by_name["source_system"].dtype == "enum"
    assert by_name["cost_basis"].dtype == "enum"
    assert by_name["list_unit_rate"].dtype == "float"
    assert by_name["credits_tcv"].dtype == "float"
    assert PROVENANCE_DEFAULTS == {"source_system": "csv", "cost_basis": "crm_proxy"}
    assert "never labeled margin" in by_name["cost_basis"].description
    assert "list_unit_rate" in by_name["currency"].description
    assert "credits_tcv" in by_name["currency"].description


def test_generator_columns_are_pre_change_list():
    assert not (set(NEW) & set(ALL_COLUMNS))
    assert set(NEW) <= set(ALL_FIELD_NAMES)
    assert not (set(NEW) & set(generate(n=50, seed=7).columns))


def test_money_lists_and_synonyms():
    assert "list_unit_rate" in _NUMERIC and "credits_tcv" in _NUMERIC
    assert "list_unit_rate" in _FX_MONEY_COLS and "credits_tcv" in _FX_MONEY_COLS
    assert "list_unit_rate" not in _NUMERIC_NONMONEY
    assert "credits_tcv" not in _NUMERIC_NONMONEY
    assert "rate card price" in SYNONYMS["list_unit_rate"]
    assert "service credits" in SYNONYMS["credits_tcv"]


def _base(n=60) -> pd.DataFrame:
    return generate(n=n, seed=7)[ALL_COLUMNS]


def test_csv_without_new_columns_loads_unchanged(tmp_path):
    p = tmp_path / "deals.csv"
    _base().to_csv(p, index=False)
    out = ingest(p)
    for n in ["list_unit_rate", "credits_tcv"]:
        assert n not in out.columns


def test_csv_with_new_columns_keeps_values(tmp_path):
    df = _base()
    df["list_unit_rate"] = 1.10
    df["credits_tcv"] = 12000.0
    df["source_record_id"] = [f"R-{i}" for i in range(len(df))]
    df["value_metric_unit"] = "audio minute"
    p = tmp_path / "deals.csv"
    df.to_csv(p, index=False)
    out = ingest(p)
    assert (out["list_unit_rate"] == 1.10).all()
    assert (out["credits_tcv"] == 12000.0).all()
    assert out["source_record_id"].tolist() == df["source_record_id"].tolist()
    assert (out["value_metric_unit"] == "audio minute").all()


def test_money_columns_are_fx_normalized(tmp_path):
    df = _base()
    df["list_unit_rate"] = 1.0
    df["credits_tcv"] = 1000.0
    df["currency"] = ["EUR"] * 30 + ["USD"] * 30  # mixed file triggers FX
    p = tmp_path / "deals.csv"
    df.to_csv(p, index=False)
    out = ingest(p, fx_rates={"EUR": 1.5, "USD": 1.0}, fx_rates_date="2026-11-01")
    assert out["list_unit_rate"].round(6).tolist() == [1.5] * 30 + [1.0] * 30
    assert out["credits_tcv"].round(6).tolist() == [1500.0] * 30 + [1000.0] * 30


def test_defaults_applied_when_columns_absent():
    out = apply_provenance_defaults(_base(10))
    assert (out["source_system"] == "csv").all()
    assert (out["cost_basis"] == "crm_proxy").all()


def test_defaults_fill_blank_cells_only():
    df = _base(4)
    df["source_system"] = ["salesforce", "", "hubspot", " "]
    df["cost_basis"] = ["declared_cost", "", "erp_verified", ""]
    out = apply_provenance_defaults(df)
    assert out["source_system"].tolist() == ["salesforce", "csv", "hubspot", "csv"]
    assert out["cost_basis"].tolist() == [
        "declared_cost", "crm_proxy", "erp_verified", "crm_proxy"]


@pytest.mark.parametrize("col,bad", [("cost_basis", "margin"),
                                     ("cost_basis", "ERP"),
                                     ("source_system", "oracle")])
def test_invalid_enum_rejected_with_named_error(col, bad):
    df = _base(5)
    df[col] = ["crm_proxy" if col == "cost_basis" else "csv"] * 4 + [bad]
    for fn in (apply_provenance_defaults, validate_provenance_enums):
        with pytest.raises(InvalidEnumValueError) as e:
            fn(df)
        assert col in str(e.value)
        assert "Not coerced" in str(e.value)


def test_no_new_field_is_required():
    assert all(not f.required for f in FIELDS if f.name in NEW)
