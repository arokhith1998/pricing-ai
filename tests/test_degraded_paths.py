"""Degraded paths must say so.

Every fallback here returns something that looks like a real answer: an empty
opportunity list, no web context, zero competitor plans. These tests pin that
each one also leaves a trace, a warning for operators and, for web search, a
status the API returns to the user.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import requests

from pricing import assist, copilot, mapping, matching, rag
from pricing.ingest import ingest_frame_verbose

DEALS_CSV = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "deals.csv"


class _Unreadable:
    def to_dict(self, orient="records"):
        raise ValueError("malformed frame")


def _boom(*_args, **_kwargs):
    raise RuntimeError("provider down")


# -- copilot -----------------------------------------------------------------

def test_copilot_raise_prices_logs_unreadable_frame(caplog):
    with caplog.at_level(logging.WARNING, logger="pricekeel.copilot"):
        assert copilot._opp_raise_prices({"realization_by_segment": _Unreadable()}) == []
    assert "realization_by_segment unreadable" in caplog.text


def test_copilot_slices_logs_and_skips_unreadable_dimension(caplog):
    analysis = {"hierarchy_slices": {"business_unit": _Unreadable()},
                "leakage": {"reference_threshold": 0.10}}
    with caplog.at_level(logging.WARNING, logger="pricekeel.copilot"):
        assert copilot._opp_over_discounted_slices(analysis) == []
    assert "hierarchy_slices.business_unit unreadable" in caplog.text


def test_copilot_investigate_logs_unreadable_frame(caplog):
    with caplog.at_level(logging.WARNING, logger="pricekeel.copilot"):
        assert copilot._opp_investigate({"top_leak_deals": _Unreadable()}) is None
    assert "top_leak_deals unreadable" in caplog.text


# -- rag web search ----------------------------------------------------------

def _clear_web_keys(monkeypatch):
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)


def test_search_web_unconfigured(monkeypatch):
    _clear_web_keys(monkeypatch)
    assert rag.search_web("q") == ([], "unconfigured")


def test_search_web_provider_failure_is_error_and_logged_without_key(monkeypatch, caplog):
    _clear_web_keys(monkeypatch)
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pk-test-not-a-real-key")

    def down(*_args, **_kwargs):
        raise requests.ConnectionError("pk-test-not-a-real-key unreachable")

    monkeypatch.setattr(requests, "post", down)
    with caplog.at_level(logging.WARNING, logger="pricekeel.rag"):
        assert rag.search_web("q") == ([], "error")
    assert "perplexity failed: ConnectionError" in caplog.text
    assert "pk-test-not-a-real-key" not in caplog.text


def test_search_web_zero_results_is_ok_not_error(monkeypatch):
    _clear_web_keys(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tv-test")
    monkeypatch.setattr(rag, "_web_tavily", lambda q, n: [])
    assert rag.search_web("q") == ([], "ok")


def test_ask_surfaces_web_status(monkeypatch):
    _clear_web_keys(monkeypatch)
    monkeypatch.setattr(rag.assist, "has_llm", lambda: False)
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pk-test")
    monkeypatch.setattr(rag, "_web_perplexity", lambda q, n: None)

    failed = rag.ask("q", {}, [], use_web=True)
    assert failed.web_status == "error"
    assert failed.used_web is False
    assert rag.ask("q", {}, [], use_web=False).web_status == "off"


# -- matching ----------------------------------------------------------------

def test_extract_plans_logs_llm_failure(monkeypatch, caplog):
    monkeypatch.setattr(matching.assist, "has_llm", lambda: True)
    monkeypatch.setattr(matching.assist, "_complete", _boom)
    with caplog.at_level(logging.WARNING, logger="pricekeel.matching"):
        vendor, plans = matching.extract_plans_from_text("x" * 200, fallback_vendor="Acme")
    assert (vendor, plans) == ("Acme", [])
    assert "plan extraction failed: RuntimeError" in caplog.text


def test_blocked_url_is_reported_as_blocked_not_as_no_plans(monkeypatch, caplog):
    def refuse(_url):
        raise matching.FetchBlocked("https://blocked.example/pricing",
                                    "robots.txt disallows /pricing")

    monkeypatch.setattr(matching, "fetch_pricing_page", refuse)
    with caplog.at_level(logging.WARNING, logger="pricekeel.matching"):
        vendor, plans, status = matching._extract_with_status("https://blocked.example/pricing")
    assert (vendor, plans, status) == ("", [], "blocked")
    assert "blocked.example refused: FetchBlocked" in caplog.text


def test_compare_names_the_pages_it_could_not_read(monkeypatch):
    monkeypatch.setattr(matching.assist, "has_llm", lambda: False)

    def refuse(url):
        raise matching.FetchBlocked(url, "robots.txt disallows /pricing")

    monkeypatch.setattr(matching, "fetch_pricing_page", refuse)
    comp = matching.compare("https://mine.example/pricing",
                            ["https://a.example/pricing", "https://b.example/pricing"])
    payload = comp.to_dict()
    assert [s["status"] for s in payload["sources"]] == ["blocked"] * 3
    assert [s["role"] for s in payload["sources"]] == ["mine", "competitor", "competitor"]
    # The user reads the summary, not the server log.
    assert "3 of 3 pricing pages could not be read" in payload["summary"]


def test_summary_failure_is_logged(monkeypatch, caplog):
    monkeypatch.setattr(matching.assist, "has_llm", lambda: True)
    monkeypatch.setattr(matching.assist, "_complete", _boom)
    with caplog.at_level(logging.WARNING, logger="pricekeel.matching"):
        text = matching._summarize_matches("Me", [], [], [])
    assert "summary unavailable" in text
    assert "summary failed: RuntimeError" in caplog.text


# -- ingest ------------------------------------------------------------------

def test_blank_list_price_is_counted_and_disclosed():
    """A blank list price leaves discount, realization and band NaN, so the row
    drops out of every leakage metric while still counting as a deal. The load
    report has to say so, the way it already does for a blank booked value."""
    raw = pd.read_csv(DEALS_CSV, dtype=str)
    raw.loc[:4, "list_acv"] = ""
    _df, report = ingest_frame_verbose(raw, source="blank-list-price fixture")
    assert report.blank_list_acv == 5
    assert "blank or zero list price" in report.summary()


def test_clean_book_reports_no_blank_list_prices():
    raw = pd.read_csv(DEALS_CSV, dtype=str)
    _df, report = ingest_frame_verbose(raw, source="clean fixture")
    assert report.blank_list_acv == 0
    assert "blank or zero list price" not in report.summary()


# -- mapping -----------------------------------------------------------------

def test_mapping_logs_llm_fallback_failure(monkeypatch, caplog):
    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(assist, "map_columns", _boom)
    with caplog.at_level(logging.WARNING, logger="pricekeel.mapping"):
        out = mapping.map_headers(["qqqq"], llm_fallback=True, use_embeddings=False)
    assert "LLM fallback failed for 1 headers: RuntimeError" in caplog.text
    assert "qqqq" not in out["mapping"].values()
