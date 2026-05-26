"""Offline tests for the LLM assist layer (pure helpers only — no network)."""

from __future__ import annotations

from pricing import assist
from pricing.schema import REQUIRED_FIELDS


def test_mapping_targets_cover_the_schema():
    targets = assist.mapping_targets()
    names = {t["field"] for t in targets}
    assert set(REQUIRED_FIELDS).issubset(names)
    required = {t["field"] for t in targets if t["required"]}
    assert required == set(REQUIRED_FIELDS)


def test_summary_facts_uses_only_provided_numbers():
    res = {
        "overview": {"booked_acv_won": 1_000_000, "price_realization_won": 0.8,
                     "avg_discount_won": 0.2, "win_rate": 0.55, "won": 110, "lost": 90},
        "leakage": {"reference_threshold": 0.05, "excess_vs_reference_won": 120_000,
                    "excess_pct_of_booked": 0.12, "off_policy_leakage_won": 40_000,
                    "gross_discount_won": 250_000},
        "quarter_end": {"lift": 0.04, "attributable_discount_won": 30_000},
        "governance": {"off_policy_unapproved_won": 12,
                       "unapproved_discount_dollars": 55_000},
    }
    facts = assist.summary_facts(res)
    assert "booked_acv_won=1000000" in facts
    assert "reference_discount=0.050" in facts
    assert "correlational" in facts          # caveat carried into the prompt
    assert "off_policy_unapproved_deals=12" in facts


def test_summary_facts_tolerates_missing_quarter_end():
    res = {
        "overview": {"booked_acv_won": 1.0, "price_realization_won": 0.9,
                     "avg_discount_won": 0.1, "win_rate": 0.5, "won": 1, "lost": 1},
        "leakage": {"reference_threshold": 0.1, "excess_vs_reference_won": 0.0,
                    "excess_pct_of_booked": 0.0, "off_policy_leakage_won": 0.0,
                    "gross_discount_won": 0.0},
        "quarter_end": {},
        "governance": {"off_policy_unapproved_won": 0, "unapproved_discount_dollars": 0.0},
    }
    facts = assist.summary_facts(res)            # must not raise
    assert "quarter_end_discount_lift" not in facts
