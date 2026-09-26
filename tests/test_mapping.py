"""Evals for pricing/mapping.py: the four-layer column-header mapper.

Guardrails asserted here:
  * messy real-world headers resolve through the deterministic layers
    (synonyms, fuzzy, embeddings) with no LLM call at all;
  * the cloud LLM fallback (Layer 4) is genuinely opt-in, never invoked
    unless `llm_fallback=True` AND a real provider is configured;
  * map_headers never returns a header that was not in its input, even when
    the LLM layer (stubbed here) tries to hand one back;
  * a Layer 4 exception is logged and surfaced via `llm_fallback_failed`,
    not swallowed silently (silent-failure-hunter F5).
"""

from __future__ import annotations

import logging

from pricing import mapping


# --- messy headers resolve through layers 1-3, no LLM ------------------------


def test_messy_headers_resolve_without_any_llm_call():
    """'Deal #' and 'Close Dt' are real-world CRM export headers. Layers 1-3
    must resolve them with `llm_fallback=False`, which never imports or
    calls pricing.assist at all."""
    out = mapping.map_headers(["Deal #", "Close Dt"], llm_fallback=False)
    assert out["mapping"]["opportunity_id"] == "Deal #"
    assert out["confidence"]["opportunity_id"] == "high"
    assert out["mapping"]["close_date"] == "Close Dt"
    assert out["used"]["Deal #"] == "synonyms"
    assert out["used"]["Close Dt"] in ("synonyms", "fuzzy", "embedding")
    assert out["llm_fallback_failed"] is False


def test_opp_id_resolves_to_opportunity_id_alone():
    out = mapping.map_headers(["Opp ID"], llm_fallback=False)
    assert out["mapping"]["opportunity_id"] == "Opp ID"
    assert out["used"]["Opp ID"] == "synonyms"


def test_close_dt_resolves_via_fuzzy_layer_without_llm():
    out = mapping.map_headers(["Close Dt"], llm_fallback=False, use_embeddings=False)
    assert out["mapping"]["close_date"] == "Close Dt"
    assert out["used"]["Close Dt"] == "fuzzy"


def test_messy_headers_together_resolve_deterministically():
    """All three together: only one header may claim opportunity_id (the
    canonical field maps to exactly one header), and that is correct
    behavior, not a bug — 'Opp ID' stays unmapped when 'Deal #' claims the
    field first."""
    out = mapping.map_headers(["Deal #", "Opp ID", "Close Dt"], llm_fallback=False)
    assert out["mapping"]["opportunity_id"] in ("Deal #", "Opp ID")
    assert out["mapping"]["close_date"] == "Close Dt"
    claimed_for_opp_id = out["mapping"]["opportunity_id"]
    other = "Opp ID" if claimed_for_opp_id == "Deal #" else "Deal #"
    # The unclaimed header is simply absent from `used`, not mis-mapped.
    assert other not in out["used"]


# --- Layer 4 is genuinely opt-in ----------------------------------------------


def test_llm_fallback_false_never_touches_assist(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("assist.has_llm must not be called")

    monkeypatch.setattr("pricing.assist.has_llm", _boom, raising=False)
    out = mapping.map_headers(["Totally Unrecognizable Column"], llm_fallback=False)
    assert out["mapping"]["opportunity_id"] is None
    assert out["llm_fallback_failed"] is False


def test_llm_fallback_true_but_no_provider_configured_skips_llm(monkeypatch):
    """llm_fallback=True is opt-in permission, not a guarantee the LLM runs:
    with no configured provider, has_llm() is False and map_columns is never
    called."""
    from pricing import assist

    monkeypatch.setattr(assist, "has_llm", lambda: False)

    def _boom(*_a, **_k):
        raise AssertionError("assist.map_columns must not be called when "
                             "has_llm() is False")

    monkeypatch.setattr(assist, "map_columns", _boom)
    out = mapping.map_headers(["Totally Unrecognizable Column"], llm_fallback=True,
                              use_embeddings=False)
    assert out["mapping"]["opportunity_id"] is None
    assert out["llm_fallback_failed"] is False


def test_llm_fallback_true_with_provider_maps_unmatched_header(monkeypatch):
    from pricing import assist

    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(assist, "map_columns",
                        lambda headers: {"account_name": headers[0]})
    out = mapping.map_headers(["Totally Unrecognizable Column"], llm_fallback=True,
                              use_embeddings=False)
    assert out["mapping"]["account_name"] == "Totally Unrecognizable Column"
    assert out["used"]["Totally Unrecognizable Column"] == "llm"
    assert out["confidence"]["account_name"] == "low"


# --- map_headers never returns a header absent from the input ---------------


def test_map_headers_never_claims_a_header_the_llm_invented(monkeypatch):
    """A stubbed LLM layer that hallucinates a header never in the input
    must not have that header appear anywhere in the result. This is a
    defense-in-depth check inside map_headers itself, not a re-test of
    assist.map_columns's own (separate) validity guard."""
    from pricing import assist

    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(
        assist, "map_columns",
        lambda headers: {"account_name": "A Header That Was Never Sent"},
    )
    out = mapping.map_headers(["Totally Unrecognizable Column"], llm_fallback=True,
                              use_embeddings=False)
    assert out["mapping"]["account_name"] is None
    assert "A Header That Was Never Sent" not in out["used"]
    all_mapped_headers = [h for h in out["mapping"].values() if h is not None]
    assert "A Header That Was Never Sent" not in all_mapped_headers


def test_map_headers_output_headers_are_a_subset_of_input(monkeypatch):
    """General invariant, not just the LLM path: every non-null value in the
    mapping must be one of the headers actually passed in."""
    from pricing import assist

    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(
        assist, "map_columns",
        lambda headers: {f: "invented header" for f in headers[:1]}
        if headers else {},
    )
    headers = ["Deal #", "Close Dt", "Weird Column A", "Weird Column B"]
    out = mapping.map_headers(headers, llm_fallback=True)
    mapped = {h for h in out["mapping"].values() if h is not None}
    assert mapped <= set(headers)


# --- llm_fallback_failed flag + logging (silent-failure-hunter F5) ----------


def test_llm_fallback_exception_sets_flag_and_logs(monkeypatch, caplog):
    from pricing import assist

    monkeypatch.setattr(assist, "has_llm", lambda: True)

    def _raise(*_a, **_k):
        raise RuntimeError("provider timeout")

    monkeypatch.setattr(assist, "map_columns", _raise)
    with caplog.at_level(logging.WARNING, logger="pricekeel.mapping"):
        out = mapping.map_headers(["Totally Unrecognizable Column"], llm_fallback=True,
                              use_embeddings=False)
    assert out["llm_fallback_failed"] is True
    assert any("LLM header fallback failed" in n for n in out["notes"])
    assert "LLM fallback failed" in caplog.text
    assert "RuntimeError" in caplog.text


def test_no_unmatched_fields_skips_llm_entirely(monkeypatch):
    """If every field is already claimed by layers 1-3, Layer 4 must not
    even attempt a call (nothing left for it to resolve)."""
    from pricing import assist

    monkeypatch.setattr(assist, "has_llm", lambda: True)

    def _boom(*_a, **_k):
        raise AssertionError("map_columns must not be called with nothing "
                             "left to map")

    monkeypatch.setattr(assist, "map_columns", _boom)
    all_fields = list(mapping._FIELDS_BY_NAME)
    headers = [mapping.SYNONYMS[f][0] for f in all_fields if f in mapping.SYNONYMS]
    out = mapping.map_headers(headers, llm_fallback=True)
    assert out["llm_fallback_failed"] is False


# --- currency synonym (data-engineer's schema addition) ----------------------


def test_currency_synonyms_resolve_via_layer_one():
    """pricing/schema.py is gaining an optional `currency` field (ISO 4217).
    An explicit 'Currency' column in a real CRM export must resolve through
    the deterministic synonyms layer, not fall to unmapped_columns."""
    for header in ("Currency", "CCY", "Currency Code"):
        assert mapping.synonyms_match(header) == "currency", header


def test_currency_synonym_entry_does_not_break_existing_field_resolution():
    """Adding 'currency' to SYNONYMS must not collide with or shadow any
    existing field's resolution."""
    out = mapping.map_headers(["Deal #", "Close Dt", "Currency"], llm_fallback=False)
    assert out["mapping"]["opportunity_id"] == "Deal #"
    assert out["mapping"]["close_date"] == "Close Dt"
