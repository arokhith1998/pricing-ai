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
            # Segment-aware lens (the headline the diagnostic/CRM screen use;
            # copilot._opp_excess_leakage reads this, not the global lens).
            "excess_vs_segment_reference_won": 4_800_000.0,
            "deals_above_segment_reference": 612,
            "excess_segment_pct_of_booked": 0.08,
        },
        "defended_vs_investigate": {
            "reference_threshold": 0.09,
            "defended_value": 48_000_000.0,
            "defended_deals": 603,
            "investigate_value": 12_000_000.0,
            "investigate_deals": 612,
            "defended_pct_of_booked": 0.80,
        },
        "governance": {"off_policy_unapproved_won": 87},
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
            {"opp_id": "OPP-1", "excess_discount_dollars": 220_000.0},
            {"opp_id": "OPP-2", "excess_discount_dollars": 180_000.0},
            {"opp_id": "OPP-3", "excess_discount_dollars": 150_000.0},
        ]),
    }


# --- extractor unit tests ----------------------------------------------------

def test_excess_leakage_recovers_40_pct():
    o = copilot._opp_excess_leakage(_base_analysis())
    assert o is not None
    # 4.8M * 0.40 = 1.92M, read from the segment-aware lens
    assert abs(o.revenue_impact_usd - 1_920_000.0) < 1.0
    assert o.kind == "reduce_leakage"
    assert "9.0%" in o.recommended  # global-fallback reference threshold formatted
    assert "segment" in o.scope.lower()
    assert any(ev.source == "leakage.excess_vs_segment_reference_won"
              for ev in o.evidence)
    assert o.caveat and "not bookable margin" in o.caveat.lower()


def test_off_policy_recovers_50_pct_and_flags_no_approver():
    o = copilot._opp_off_policy(_base_analysis())
    assert o is not None
    assert abs(o.revenue_impact_usd - 600_000.0) < 1.0  # 1.2M * 0.50
    # The no-approver evidence row must be present and carry the real count —
    # this fails if governance.off_policy_unapproved_won is misread as the
    # nonexistent off_policy_no_approver key (silently drops to 0/absent).
    gov_evidence = [ev for ev in o.evidence if ev.type == "governance"]
    assert gov_evidence, "no-approver governance evidence missing"
    assert "87" in gov_evidence[0].value
    assert "no recorded approver" in gov_evidence[0].value.lower()
    assert gov_evidence[0].source == "governance.off_policy_unapproved_won"
    assert o.caveat and "not bookable margin" in o.caveat.lower()


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
    # Top-by-magnitude is the defended-wins reportage ($48M booked) — it sorts
    # above the leakage opportunities by dollar size, which is correct: a
    # buyer asking 'biggest number first' should see what their discounting
    # bought before what it leaked. The leakage-kind opp still appears next.
    assert opps[0].kind == "defended"
    leakage_opps = [o for o in opps if o.kind == "reduce_leakage"]
    assert leakage_opps and leakage_opps[0].revenue_impact_usd > 1_500_000


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


# (The decision log moved to pricing/governance.py — see tests/test_governance.py.)


def test_canonical_questions_have_six_entries_with_required_keys():
    assert len(copilot.CANONICAL_QUESTIONS) == 6
    for q in copilot.CANONICAL_QUESTIONS:
        assert {"id", "label", "hint"} <= set(q.keys())


# --- defended-wins extractor (sales-friendly framing per 2026-05-30 review) -

def test_defended_wins_extractor_emits_with_reportage_framing():
    o = copilot._opp_defended_wins(_base_analysis())
    assert o is not None
    assert o.kind == "defended"
    # revenue_impact_usd is the defended VALUE itself — not a savings claim.
    assert o.revenue_impact_usd == 48_000_000.0
    # Recommendation should not say "save" or "recover" — it's reportage.
    rec = o.recommended.lower()
    assert "keep doing this" in rec or "defend" in rec
    assert "save" not in rec and "recover" not in rec


def test_defended_wins_returns_none_when_no_defended_value():
    a = _base_analysis()
    a["defended_vs_investigate"]["defended_value"] = 0
    assert copilot._opp_defended_wins(a) is None


def test_opportunities_includes_defended_card():
    pool = copilot.opportunities(_base_analysis())
    kinds = [o.kind for o in pool]
    assert "defended" in kinds, "defended-wins extractor must appear in the pool"


# --- missing-vs-zero (silent-failure-hunter F1) ------------------------------


def test_missing_leakage_key_is_flagged_degraded_not_a_real_zero():
    """A missing analysis key must never read as a computed zero. Deleting
    'leakage' entirely (not just zeroing a field inside it) must surface as
    degraded, distinct from a book that genuinely has no excess or off-policy
    leakage."""
    a = _base_analysis()
    del a["leakage"]
    degraded: list = []
    opps = copilot.opportunities(a, degraded=degraded)
    assert "leakage" in degraded
    # No opportunity may claim evidence sourced from the missing key: the
    # quarter-end extractor also emits kind="reduce_leakage" from an
    # unrelated (present) key, so the real invariant is on evidence source,
    # not on kind.
    assert not any(
        ev.source.startswith("leakage.") for o in opps for ev in o.evidence
    )


def test_missing_key_sets_degraded_without_a_collector_list():
    """Extractors called with no `degraded` list (the existing single-arg
    call pattern every other test in this file uses) must not raise, and
    must still return None/[] for the missing key exactly as before."""
    a = _base_analysis()
    del a["quarter_end"]
    assert copilot._opp_quarter_end(a) is None  # no degraded= kwarg passed


def test_present_but_zero_value_is_not_flagged_degraded():
    """A key that is present with a legitimate zero/absent value (e.g. no
    defended value this run) must NOT be treated as missing."""
    a = _base_analysis()
    a["defended_vs_investigate"]["defended_value"] = 0
    degraded: list = []
    assert copilot._opp_defended_wins(a, degraded) is None
    assert degraded == []


def test_answer_canonical_missing_key_sets_degraded_flag_on_answer(monkeypatch):
    monkeypatch.setattr(copilot.assist, "has_llm", lambda: False)
    a = _base_analysis()
    del a["leakage"]
    ans = copilot.answer_canonical("losing_deals", a)
    assert ans.degraded is True
    assert "leakage" in ans.degraded_keys
    # Never render a degraded result as a confident "no opportunities" claim.
    assert "no opportunities" not in ans.text.lower()
    assert "degraded" in ans.text.lower()


def test_answer_canonical_not_degraded_on_a_complete_analysis(monkeypatch):
    monkeypatch.setattr(copilot.assist, "has_llm", lambda: False)
    ans = copilot.answer_canonical("losing_deals", _base_analysis())
    assert ans.degraded is False
    assert ans.degraded_keys == []


def test_non_additive_caveat_present_when_opportunities_returned(monkeypatch):
    monkeypatch.setattr(copilot.assist, "has_llm", lambda: False)
    ans = copilot.answer_canonical("losing_deals", _base_analysis())
    assert ans.opportunities
    assert "not additive" in ans.non_additive.lower()
    assert "not be summed" in ans.non_additive.lower() or "not additive" in ans.non_additive.lower()


def test_non_additive_caveat_absent_when_no_opportunities(monkeypatch):
    monkeypatch.setattr(copilot.assist, "has_llm", lambda: False)
    ans = copilot.answer_canonical("raise_prices", {})
    assert ans.opportunities == []
    assert ans.non_additive == ""


def test_answer_to_dict_includes_degraded_and_non_additive_keys():
    ans = copilot.Answer(text="x", opportunities=[], qid="losing_deals",
                         degraded=True, degraded_keys=["leakage"],
                         non_additive="not additive")
    d = ans.to_dict()
    assert d["degraded"] is True
    assert d["degraded_keys"] == ["leakage"]
    assert d["non_additive"] == "not additive"


# --- no em dashes (code-reviewer F4) -----------------------------------------


def test_copilot_system_prompt_forbids_em_dashes_and_contains_none():
    assert "—" not in copilot._COPILOT_SYSTEM
    assert "em dash" in copilot._COPILOT_SYSTEM.lower()


def test_opportunity_ui_strings_contain_no_em_dashes():
    """Every Opportunity field a user reads must not carry an em dash
    (code-reviewer F4): a model imitates whatever house style the
    deterministic strings around it use."""
    opps = copilot.opportunities(_base_analysis())
    for o in opps:
        for field in (o.scope, o.current, o.recommended, o.methodology, o.caveat):
            assert "—" not in field, f"{o.kind}: em dash in {field!r}"


def test_no_llm_answer_is_flagged_not_narrated(monkeypatch):
    """With no provider the opportunities are still engine output; the UI
    needs a structured flag, not a prose apology, to say the narration is
    off (2026-09-27 external review)."""
    from pricing import assist, copilot
    monkeypatch.setattr(assist, "has_llm", lambda: False)
    analysis = copilot.__dict__.get("_demo_analysis", None)
    ans = copilot.answer_canonical("q1", {"leakage": {}, "defended_vs_investigate": {}})
    assert ans.narrated is False
    assert "opportunityies" not in ans.text


# --- PK-74: investigate must fire on a real book -----------------------------

def test_investigate_fires_on_the_synthetic_book_with_the_real_frame():
    """Eval on the real pipeline (no invented columns): the investigate card
    must fire, and its dollar figure must equal the sum of the real
    excess_discount_dollars column, so no number is made up."""
    from pathlib import Path
    from pricing import diagnostic
    book = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "deals.csv"
    a = diagnostic.run(book)
    top = a["top_leak_deals"]
    assert "discount_amount" not in top.columns
    assert "excess_discount_dollars" in top.columns
    o = copilot._opp_investigate(a)
    assert o is not None and o.kind == "investigate"
    assert copilot.INVESTIGATE_RECOVERABLE_SHARE == 0.20  # pin the heuristic
    expected = float(top["excess_discount_dollars"].sum())
    assert abs(o.revenue_impact_usd - expected * copilot.INVESTIGATE_RECOVERABLE_SHARE) < 0.01
    prefixes = {x.id.split("-")[0] for x in copilot.opportunities(a)}
    assert "invest" in prefixes
    assert "margin" not in (o.current + o.recommended).lower()
    phrase = "excess discount above the reference threshold"
    assert phrase in o.current
    assert any(phrase in e.value for e in o.evidence)
    assert o.caveat

    # The API sends records (api/shared.py), not a frame: same card, same impact.
    api_shaped = {**a, "top_leak_deals": top.to_dict("records")}
    o2 = copilot._opp_investigate(api_shaped)
    assert o2 is not None
    assert abs(o2.revenue_impact_usd - o.revenue_impact_usd) < 0.01


def test_investigate_empty_top_leak_frame_produces_no_card():
    a = {"top_leak_deals": pd.DataFrame(columns=["opportunity_id", "excess_discount_dollars"])}
    assert copilot._opp_investigate(a) is None
