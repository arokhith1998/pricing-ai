"""Pure-function tests for pricing/copilot.py.

The opportunity extractors do not call the LLM — they reduce an analysis
dict to structured Opportunity objects with dollar impact and confidence.
These tests pin the extractor behavior so the dollar logic cannot silently
drift.
"""
from __future__ import annotations

import pandas as pd

from pricing import copilot


def _base_analysis() -> dict:
    """A minimum analysis dict that exercises every extractor branch."""
    return {
        "overview": {"booked_acv_won": 60_000_000.0, "win_rate": 0.61,
                     "avg_discount_won": 0.14},
        "leakage": {
            "policy_threshold": 0.15,
            "gross_discount_won": 9_500_000.0,
            "off_policy_leakage_won": 1_200_000.0,
            "reference_threshold": 0.09,
            "reference_band": "5-10%",
            "excess_vs_reference_won": 4_800_000.0,
            "deals_above_reference": 612,
            "excess_pct_of_booked": 0.08,
        },
        "governance": {"off_policy_no_approver": 87},
        "quarter_end": {"qe_deals": 240, "qe_avg_discount": 0.18,
                        "rest_avg_discount": 0.13, "lift": 0.05,
                        "attributable_discount_won": 420_000.0},
        "realization_by_segment": pd.DataFrame([
            {"segment": "Enterprise", "win_rate": 0.78, "price_realization": 0.91,
             "deals": 120, "booked_acv": 22_000_000.0},
            {"segment": "Mid-Market", "win_rate": 0.55, "price_realization": 0.82,
             "deals": 350, "booked_acv": 25_000_000.0},
            {"segment": "SMB", "win_rate": 0.40, "price_realization": 0.75,
             "deals": 600, "booked_acv": 13_000_000.0},
        ]),
        "hierarchy_slices": {
            "line": pd.DataFrame([
                {"line": "Platform", "avg_discount": 0.18, "deals": 320,
                 "booked_acv": 28_000_000.0},
                {"line": "Data", "avg_discount": 0.08, "deals": 410,
                 "booked_acv": 14_000_000.0},  # below reference — skipped
                {"line": "AI Add-on", "avg_discount": 0.22, "deals": 180,
                 "booked_acv": 9_000_000.0},
            ]),
        },
        "top_leak_deals": pd.DataFrame([
            {"opp_id": "OPP-1", "discount_amount": 220_000.0},
            {"opp_id": "OPP-2", "discount_amount": 180_000.0},
            {"opp_id": "OPP-3", "discount_amount": 150_000.0},
        ]),
    }


# --- extractor unit tests ----------------------------------------------------

def test_excess_leakage_recovers_40_pct():
    o = copilot._opp_excess_leakage(_base_analysis())
    assert o is not None
    # 4.8M * 0.40 = 1.92M
    assert abs(o.revenue_impact_usd - 1_920_000.0) < 1.0
    assert o.kind == "reduce_leakage"
    assert "9.0%" in o.recommended  # reference threshold formatted
    assert any(ev.type == "leakage" for ev in o.evidence)


def test_off_policy_recovers_50_pct_and_flags_no_approver():
    o = copilot._opp_off_policy(_base_analysis())
    assert o is not None
    assert abs(o.revenue_impact_usd - 600_000.0) < 1.0  # 1.2M * 0.50
    # the no-approver evidence row must be present
    types = [ev.type for ev in o.evidence]
    assert "governance" in types


def test_raise_prices_only_emits_high_win_high_realization():
    opps = copilot._opp_raise_prices(_base_analysis())
    # Only Enterprise (win 78%, realization 91%) qualifies in the fixture
    assert len(opps) == 1
    assert "Enterprise" in opps[0].scope
    # 22M booked * 0.02 * 0.50 = 220_000
    assert abs(opps[0].revenue_impact_usd - 220_000.0) < 1.0


def test_over_discounted_slices_excludes_below_reference():
    opps = copilot._opp_over_discounted_slices(_base_analysis())
    # 'Data' line is at 8% (below reference 9%) → skipped
    scopes = [o.scope for o in opps]
    assert any("Platform" in s for s in scopes)
    assert any("AI Add-on" in s for s in scopes)
    assert not any("Data" in s for s in scopes)


def test_quarter_end_extractor_returns_attributable_share():
    o = copilot._opp_quarter_end(_base_analysis())
    assert o is not None
    assert abs(o.revenue_impact_usd - 210_000.0) < 1.0  # 420K * 0.50
    assert "quarter-end" in o.scope.lower()


def test_investigate_lists_top_leak_deals():
    o = copilot._opp_investigate(_base_analysis())
    assert o is not None
    # 220K + 180K + 150K = 550K → 20% recoverable = 110K
    assert abs(o.revenue_impact_usd - 110_000.0) < 1.0
    assert "3" in o.scope  # "Top 3 deals flagged"


# --- top-level opportunities() composition ----------------------------------

def test_opportunities_sorted_by_impact_descending():
    opps = copilot.opportunities(_base_analysis())
    impacts = [o.revenue_impact_usd for o in opps]
    assert impacts == sorted(impacts, reverse=True)
    # Highest should be excess leakage at $1.92M
    assert opps[0].kind == "reduce_leakage"
    assert opps[0].revenue_impact_usd > 1_500_000


def test_opportunities_min_impact_filter():
    opps_all = copilot.opportunities(_base_analysis())
    opps_big = copilot.opportunities(_base_analysis(), min_impact_usd=500_000)
    assert len(opps_big) < len(opps_all)
    assert all(o.revenue_impact_usd >= 500_000 for o in opps_big)


def test_empty_analysis_returns_empty_pool():
    assert copilot.opportunities({}) == []


# --- canonical-question routing ---------------------------------------------

def test_canonical_routes_to_kind_filtered_subsets():
    a = _base_analysis()
    losing = copilot._opps_for_question("losing_deals", a)
    raise_p = copilot._opps_for_question("raise_prices", a)
    big = copilot._opps_for_question("opportunities_over", a,
                                     min_impact_usd=500_000)

    assert all(o.kind in ("reduce_leakage", "governance") for o in losing)
    assert all(o.kind == "raise_price" for o in raise_p)
    assert all(o.revenue_impact_usd >= 500_000 for o in big)


# --- decision log -----------------------------------------------------------

def test_decision_log_round_trip():
    sid = "test-session-abc"
    copilot._DECISION_LOG.pop(sid, None)
    d = copilot.log_decision(sid, "losing_deals",
                             surfaced=["o1", "o2"], accepted=["o1"])
    assert d.qid == "losing_deals"
    out = copilot.decisions_for(sid)
    assert len(out) == 1
    assert out[0].opportunities_accepted == ["o1"]


def test_canonical_questions_have_six_entries_with_required_keys():
    assert len(copilot.CANONICAL_QUESTIONS) == 6
    for q in copilot.CANONICAL_QUESTIONS:
        assert {"id", "label", "hint"} <= set(q.keys())
