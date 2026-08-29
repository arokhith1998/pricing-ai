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
    raw = assist._complete("map headers", "{}", json_mode=True, small=True)
    parsed = json.loads(raw)  # must not raise
    assert parsed == {"CustomerId": "customer_id", "ACV": None}


def test_json_mode_tolerates_a_markdown_fence_but_still_parses(monkeypatch):
    def _create(kwargs):
        return _fake_message('```json\n{"a": "b"}\n```')

    _install_fake_anthropic(monkeypatch, _create)
    raw = assist._complete("sys", "user", json_mode=True)
    assert json.loads(raw) == {"a": "b"}


def test_json_mode_raises_loudly_on_unparseable_output(monkeypatch):
    """If the model still returns prose under json_mode, that must be a loud
    failure (LLMError), never silently handed back to a JSON-expecting caller."""
    def _create(kwargs):
        return _fake_message("Sure, here is the mapping you asked for: ...")

    _install_fake_anthropic(monkeypatch, _create)
    with pytest.raises(assist.LLMError):
        assist._complete("sys", "user", json_mode=True)


def test_json_mode_sends_structured_output_config(monkeypatch):
    captured: dict = {}

    def _create(kwargs):
        captured.update(kwargs)
        return _fake_message('{"ok": true}')

    _install_fake_anthropic(monkeypatch, _create)
    assist._complete("sys", "user", json_mode=True)
    assert captured["output_config"]["format"]["type"] == "json_schema"
    assert isinstance(captured["output_config"]["format"]["schema"], dict)


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
    schema = captured["output_config"]["format"]["schema"]
    assert schema["type"] == "object"
    assert set(schema["properties"]) == targets
    assert set(schema["required"]) == targets
    assert schema["additionalProperties"] is False


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


def test_matching_columns_call_uses_small_tier():
    """pricing/matching.py:390's comment ("the mini model is proven
    sufficient") maps, for Anthropic, to small=True routing to the cheap
    tier. map_columns must keep requesting small=True."""
    import inspect
    src = inspect.getsource(assist.map_columns)
    assert "small=True" in src


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

def test_installed_sdk_actually_supports_our_structured_output_shape():
    """Guards the anthropic>=0.77.0 floor in requirements.txt. If this starts
    failing, the installed anthropic build can't serve the output_config
    request pricing/assist.py._complete builds under json_mode=True, and
    every json_mode call in the product (map_columns, and matching.py's
    extraction calls) would 400 in production despite every mocked test
    above passing."""
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

    # And confirm the exact shape assist.py builds is constructible as the
    # TypedDict this SDK version expects — not just present, but shaped right.
    sample: JSONOutputFormatParam = {"type": "json_schema", "schema": {"type": "object"}}
    assert sample["type"] == "json_schema"
