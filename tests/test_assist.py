"""Offline tests for the LLM assist layer.

Pure-function tests (no network) plus evals against a mocked Anthropic SDK:
these assert guardrails (JSON validity under json_mode, cheap-tier routing,
timeout -> LLMUnavailableError, no sampling params), never model prose, and
never make a real API call.
"""

from __future__ import annotations

import inspect
import json
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from pricing import assist
from pricing.schema import REQUIRED_FIELDS


def _fake_message(text: str, *, blocks: list | None = None):
    """A minimal stand-in for anthropic.types.Message."""
    content = blocks if blocks is not None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(content=content)


class _FakeMessages:
    def __init__(self, create_fn):
        self._create_fn = create_fn

    def create(self, **kwargs):
        return self._create_fn(kwargs)


# A minimal, valid schema for tests that need "a json_schema, any schema" to
# exercise something other than schema *shape* (json_mode=True now requires
# one — see test_json_mode_without_a_schema_raises_instead_of_guessing_one).
_ANY_OBJECT_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "string"}},
    "required": ["a"],
    "additionalProperties": False,
}


def _install_fake_anthropic(monkeypatch, create_fn):
    """Patch anthropic.Anthropic so pricing.assist._complete's local
    `from anthropic import Anthropic` picks up the fake at call time."""
    init_kwargs: dict = {}

    class _Fake:
        def __init__(self, **kwargs):
            init_kwargs.update(kwargs)
            self.messages = _FakeMessages(create_fn)

    monkeypatch.setattr(anthropic, "Anthropic", _Fake)
    return init_kwargs


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


# --- Anthropic-only provider evals (mocked SDK, no network) -----------------

def test_has_llm_checks_only_the_anthropic_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert assist.has_llm() is False
    # An OpenAI key alone must not satisfy has_llm(): OpenAI is gone from
    # the product runtime, this is not a fallback provider anymore.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-only")
    assert assist.has_llm() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert assist.has_llm() is True


def test_json_mode_yields_json_loads_parseable_output(monkeypatch):
    """The core Gap-1 guarantee: json_mode=True must yield text json.loads
    accepts, not prose."""
    def _create(kwargs):
        return _fake_message('{"CustomerId": "customer_id", "ACV": null}')

    _install_fake_anthropic(monkeypatch, _create)
    raw = assist._complete("map headers", "{}", json_mode=True, small=True,
                            json_schema=_ANY_OBJECT_SCHEMA)
    parsed = json.loads(raw)  # must not raise
    assert parsed == {"CustomerId": "customer_id", "ACV": None}


def test_json_mode_tolerates_a_markdown_fence_but_still_parses(monkeypatch):
    def _create(kwargs):
        return _fake_message('```json\n{"a": "b"}\n```')

    _install_fake_anthropic(monkeypatch, _create)
    raw = assist._complete("sys", "user", json_mode=True, json_schema=_ANY_OBJECT_SCHEMA)
    assert json.loads(raw) == {"a": "b"}


def test_json_mode_raises_loudly_on_unparseable_output(monkeypatch):
    """If the model still returns prose under json_mode, that must be a loud
    failure (LLMError), never silently handed back to a JSON-expecting caller."""
    def _create(kwargs):
        return _fake_message("Sure, here is the mapping you asked for: ...")

    _install_fake_anthropic(monkeypatch, _create)
    with pytest.raises(assist.LLMError):
        assist._complete("sys", "user", json_mode=True, json_schema=_ANY_OBJECT_SCHEMA)


def test_json_mode_raises_loudly_on_a_non_object_json_value(monkeypatch):
    """json.loads happily accepts a bare list/string/number/null, and every
    json_mode caller here does `.get(...)` on the result. A non-dict parse
    must be a loud LLMError here, not an AttributeError in the caller."""
    def _create(kwargs):
        return _fake_message('["not", "an", "object"]')

    _install_fake_anthropic(monkeypatch, _create)
    with pytest.raises(assist.LLMError):
        assist._complete("sys", "user", json_mode=True, json_schema=_ANY_OBJECT_SCHEMA)


def test_json_mode_sends_structured_output_config(monkeypatch):
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message('{"ok": true}')

    _install_fake_anthropic(monkeypatch, _create)
    assist._complete("sys", "user", json_mode=True, json_schema=_ANY_OBJECT_SCHEMA)
    assert captured["output_config"]["format"]["type"] == "json_schema"
    assert captured["output_config"]["format"]["schema"] == _ANY_OBJECT_SCHEMA


def test_map_columns_builds_a_full_field_schema_and_returns_valid_json(monkeypatch):
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message('{"customer_id": "CustomerId", "acv": null}')

    _install_fake_anthropic(monkeypatch, _create)
    out = assist.map_columns(["CustomerId", "Amount"])
    assert isinstance(out, dict)
    targets = {t["field"] for t in assist.mapping_targets()}
    assert set(out) == targets
    # map_columns is the small/cheap tier's real call site, not just a
    # source-grep for "small=True" (that would pass with the tiers inverted).
    assert captured["model"] == assist._DEFAULT_MAP_MODEL
    schema = captured["output_config"]["format"]["schema"]
    assert schema["type"] == "object"
    assert set(schema["properties"]) == targets
    assert set(schema["required"]) == targets
    assert schema["additionalProperties"] is False
    # Per-field nullable must be the anyOf form, not a JSON Schema type
    # array: {"type": ["string", "null"]} crashes the real SDK strictifier
    # (PK-5 review round 2, blocker 1). Checked again, for real, below.
    for field, prop in schema["properties"].items():
        assert "anyOf" in prop, f"{field}: expected anyOf nullable, got {prop}"
        assert {"type": "string"} in prop["anyOf"]
        assert {"type": "null"} in prop["anyOf"]


def test_map_columns_schema_survives_the_real_sdk_strictifier(monkeypatch):
    """Blocker regression (PK-5 review round 2): mocking the SDK, as every
    other test here does, would happily accept a schema shape the live API
    rejects — that's exactly how the type-array nullable shipped. There is
    no offline way to call the live API's constrained-decoding validator
    directly, so this uses the closest available proxy instead:
    anthropic.lib._parse._transform.transform_schema, a static encoding of
    the documented structured-outputs subset the SDK itself ships. It is
    NOT on this module's runtime path (output_config goes to the API as the
    raw dict we build, unmodified by the SDK; transform_schema is only used
    by the SDK's separate output_format/parse/stream/count_tokens helpers) —
    but it raises on exactly the shapes the documented subset forbids, so
    "does it survive transform_schema" is a real, checkable pre-flight
    signal for "will the live API accept this", run here offline and free."""
    from anthropic.lib._parse._transform import transform_schema

    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message('{"customer_id": null}')

    _install_fake_anthropic(monkeypatch, _create)
    assist.map_columns(["CustomerId"])
    schema = captured["output_config"]["format"]["schema"]

    transformed = transform_schema(schema)  # must not raise

    assert transformed["type"] == "object"
    assert transformed["additionalProperties"] is False
    assert transformed["properties"], "properties must survive the transform"
    for field, prop in transformed["properties"].items():
        assert "anyOf" in prop, f"{field} lost its nullable anyOf: {prop}"
        types = {branch["type"] for branch in prop["anyOf"]}
        assert types == {"string", "null"}, f"{field}: {types}"


def test_json_mode_without_a_schema_raises_instead_of_guessing_one(monkeypatch):
    """Blocker regression (PK-5 review round 2): the old permissive fallback
    ({"type": "object", "additionalProperties": True}) is not "any object"
    under constrained decoding against a schema with no declared properties
    — it is useless for getting real data back. There is no safe generic
    schema, so a missing json_schema under json_mode must be a loud,
    immediate LLMConfigError (a caller-contract bug, not a ValueError: see
    LLMConfigError's docstring for why api/main.py's ValueError -> 422
    handling would misattribute this to the client)."""
    _install_fake_anthropic(monkeypatch, lambda kwargs: _fake_message("{}"))
    with pytest.raises(assist.LLMConfigError):
        assist._complete("sys", "user", json_mode=True)


def test_the_old_permissive_fallback_would_have_meant_the_empty_object():
    """Documents *why* test_json_mode_without_a_schema_raises... exists.
    anthropic.lib._parse._transform.transform_schema is not called on this
    module's runtime path (see test_map_columns_schema_survives_the_real_
    sdk_strictifier's docstring) but is a static encoding of the documented
    structured-outputs subset: run offline here, it shows the permissive
    schema this module used to fall back to collapses to the *empty* object
    (properties={}, additionalProperties forced False), not "any object" —
    the fallback was actively wrong, not just unverified."""
    from anthropic.lib._parse._transform import transform_schema

    old_fallback = {"type": "object", "additionalProperties": True}
    transformed = transform_schema(old_fallback)
    assert transformed["properties"] == {}
    assert transformed["additionalProperties"] is False


def test_non_json_mode_does_not_set_output_config(monkeypatch):
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message("A plain narrative sentence.")

    _install_fake_anthropic(monkeypatch, _create)
    text = assist._complete("sys", "user")
    assert text == "A plain narrative sentence."
    assert "output_config" not in captured


def test_small_true_routes_to_the_cheap_model_by_default(monkeypatch):
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message("ok")

    _install_fake_anthropic(monkeypatch, _create)
    monkeypatch.delenv("ANTHROPIC_MAP_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_SUMMARY_MODEL", raising=False)
    assist._complete("sys", "user", small=True)
    assert captured["model"] == assist._DEFAULT_MAP_MODEL
    assert captured["model"] != assist._DEFAULT_SUMMARY_MODEL


def test_small_false_routes_to_the_summary_model_by_default(monkeypatch):
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message("ok")

    _install_fake_anthropic(monkeypatch, _create)
    monkeypatch.delenv("ANTHROPIC_MAP_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_SUMMARY_MODEL", raising=False)
    assist._complete("sys", "user", small=False)
    assert captured["model"] == assist._DEFAULT_SUMMARY_MODEL


def test_model_tiers_are_env_overridable(monkeypatch):
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message("ok")

    _install_fake_anthropic(monkeypatch, _create)
    monkeypatch.setenv("ANTHROPIC_MAP_MODEL", "claude-map-override")
    monkeypatch.setenv("ANTHROPIC_SUMMARY_MODEL", "claude-summary-override")
    assist._complete("sys", "user", small=True)
    assert captured["model"] == "claude-map-override"
    assist._complete("sys", "user", small=False)
    assert captured["model"] == "claude-summary-override"


def test_no_sampling_parameters_are_sent(monkeypatch):
    """Current Claude models reject temperature/top_p/top_k; these must never
    be carried over from the old OpenAI branch."""
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message("ok")

    _install_fake_anthropic(monkeypatch, _create)
    assist._complete("sys", "user")
    for forbidden in ("temperature", "top_p", "top_k"):
        assert forbidden not in captured


def test_thinking_is_not_enabled_by_default(monkeypatch):
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message("ok")

    _install_fake_anthropic(monkeypatch, _create)
    assist._complete("sys", "user")
    assert "thinking" not in captured


def test_every_call_carries_the_configured_timeout(monkeypatch):
    seen_timeouts: list = []

    class _Fake:
        def __init__(self, **kwargs):
            seen_timeouts.append(kwargs.get("timeout"))
            self.messages = _FakeMessages(lambda kwargs: _fake_message("ok"))

    monkeypatch.setattr(anthropic, "Anthropic", _Fake)
    assist._complete("sys", "user")
    assert seen_timeouts == [assist.LLM_TIMEOUT_SECONDS]


def test_timeout_maps_to_llm_unavailable_error(monkeypatch):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    def _create(kwargs):
        raise anthropic.APITimeoutError(request)

    _install_fake_anthropic(monkeypatch, _create)
    with pytest.raises(assist.LLMUnavailableError):
        assist._complete("sys", "user")


def test_connection_failure_maps_to_llm_unavailable_error(monkeypatch):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    def _create(kwargs):
        raise anthropic.APIConnectionError(message="boom", request=request)

    _install_fake_anthropic(monkeypatch, _create)
    with pytest.raises(assist.LLMUnavailableError):
        assist._complete("sys", "user")


@pytest.mark.parametrize("status_code", [429, 500, 502, 503, 529])
def test_rate_limit_and_server_status_errors_map_to_llm_unavailable(monkeypatch, status_code):
    """429 (rate limit) and 5xx are genuine provider-unavailable conditions,
    not a request bug; they must degrade the same way a timeout does rather
    than escape as a raw 500 to our own API layer."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code, request=request)

    def _create(kwargs):
        raise anthropic.APIStatusError("provider trouble", response=response, body=None)

    _install_fake_anthropic(monkeypatch, _create)
    with pytest.raises(assist.LLMUnavailableError):
        assist._complete("sys", "user")


def test_other_status_errors_are_not_mistaken_for_unavailable(monkeypatch):
    """A 400 (e.g. a malformed schema, blocker 1's failure mode) is a bug in
    this module, not the provider being unavailable — it must not be
    swallowed into a falsely-reassuring LLMUnavailableError/503."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(400, request=request)

    def _create(kwargs):
        raise anthropic.APIStatusError("bad request", response=response, body=None)

    _install_fake_anthropic(monkeypatch, _create)
    with pytest.raises(anthropic.APIStatusError):
        assist._complete("sys", "user")


def test_text_block_extraction_skips_non_text_blocks(monkeypatch):
    """content[0] is not assumed to be text — a non-text block (e.g. a future
    tool_use/citations block) ahead of the text block must be skipped, not
    crash or silently return the wrong block's data."""
    blocks = [
        SimpleNamespace(type="server_tool_use", input={"x": 1}),
        SimpleNamespace(type="text", text="the real narration"),
    ]

    def _create(kwargs):
        return _fake_message(None, blocks=blocks)

    _install_fake_anthropic(monkeypatch, _create)
    assert assist._complete("sys", "user") == "the real narration"


def test_no_text_block_raises_llm_error(monkeypatch):
    def _create(kwargs):
        return _fake_message(None, blocks=[SimpleNamespace(type="server_tool_use", input={})])

    _install_fake_anthropic(monkeypatch, _create)
    with pytest.raises(assist.LLMError):
        assist._complete("sys", "user")


# --- installed-SDK guard (no mocking: catches a version downgrade) ----------
#
# Every test above mocks anthropic.Anthropic, so it would happily pass even
# against an SDK build old enough to reject output_config outright (pre-0.77.0
# had neither output_config nor output_format on the stable messages.create).
# This test introspects the *real*, unmocked `anthropic` package instead, so
# it fails the moment `pip install -r requirements.txt` resolves to something
# below the verified floor.

def test_installed_sdk_has_the_output_config_parameter_at_all():
    """Guards the anthropic>=0.77.0 floor in requirements.txt (API-surface
    check only). If this starts failing, the installed anthropic build has
    no output_config parameter on messages.create at all, and every
    json_mode call would 400 regardless of schema shape.

    This does NOT guard schema *shape* correctness — a fabricated sample
    passing this kind of check is exactly how the type-array nullable
    shipped (PK-5 review round 2). Shape correctness is covered by the
    round-trip tests below, which run the schemas this module actually
    builds through the real strictifier.
    """
    create_sig = inspect.signature(anthropic.Anthropic(api_key="x").messages.create)
    assert "output_config" in create_sig.parameters, (
        "installed anthropic SDK's messages.create has no output_config "
        "parameter; raise the anthropic>=0.77.0 floor in requirements.txt "
        "or pip install a newer anthropic"
    )

    from anthropic.types.json_output_format_param import JSONOutputFormatParam

    format_fields = JSONOutputFormatParam.__annotations__
    assert "schema" in format_fields
    assert "type" in format_fields


def test_json_output_config_shape_survives_the_real_sdk_strictifier():
    """Round-trip _json_output_config's own output (not a hand-picked sample)
    through the real, unmocked transform_schema and assert it doesn't raise."""
    from anthropic.lib._parse._transform import transform_schema

    config = assist._json_output_config(_ANY_OBJECT_SCHEMA)
    assert config["format"]["type"] == "json_schema"
    transformed = transform_schema(config["format"]["schema"])  # must not raise
    assert transformed["type"] == "object"
    assert set(transformed["properties"]) == {"a"}


# --- no em dashes (code-reviewer F4) -----------------------------------------


def test_summary_system_prompt_forbids_em_dashes_and_contains_none():
    assert "—" not in assist._SUMMARY_SYSTEM
    assert "em dash" in assist._SUMMARY_SYSTEM.lower()
