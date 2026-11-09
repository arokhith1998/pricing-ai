"""PK-39: cpq_line exports are rolled up to deals before any deal is counted,
ask_user deals are surfaced and never counted, quotes resolve to one deal per
opportunity, and the stage table is the one in pricing.mapping."""

from __future__ import annotations

import io
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main
from api.shared import diagnostic_payload
from pricing import assist, ingest, mapping
from pricing.diagnostic import run
from pricing.ingest import LoadReport, SchemaError, ingest_verbose

HEAD = ["Quote ID", "Line ID", "Opportunity ID", "Account Name", "Segment",
        "Product Tier", "Value Metric", "Quantity", "List Unit Price",
        "Unit Price", "Quote Status", "Created Date", "Close Date"]


def _lines(quotes: list[dict]) -> pd.DataFrame:
    """Two lines per quote unless `lines` is given as [(qty, list, net), ...]."""
    rows = []
    for q in quotes:
        for n, (qty, lst, net) in enumerate(q.get("lines", [(10, 100.0, 80.0),
                                                            (5, 40.0, 40.0)])):
            row = {"Quote ID": q["qid"], "Line ID": f"{q['qid']}-L{n}",
                   "Opportunity ID": q.get("opp", f"OPP-{q['qid']}"),
                   "Account Name": q.get("acct", f"Acct {q['qid']}"),
                   "Segment": "MidMarket", "Product Tier": "Growth",
                   "Value Metric": "seats", "Quantity": qty,
                   "List Unit Price": lst, "Unit Price": net,
                   "Quote Status": q.get("status", "Accepted"),
                   "Created Date": q.get("created", "2025-01-10"),
                   "Close Date": "2025-03-15"}
            for k in ("Sent Date", "Is Primary"):
                if k in q:
                    row[k] = q[k]
            rows.append(row)
    return pd.DataFrame(rows).astype(str)


def _write(df: pd.DataFrame, tmp_path, name="quotes.csv") -> str:
    p = tmp_path / name
    df.to_csv(p, index=False)
    return str(p)


def _book(n_won=25, n_lost=15) -> list[dict]:
    """A closed book big enough to clear MIN_CLOSED_DEALS, with spread discounts."""
    out = []
    for i in range(n_won + n_lost):
        net = 100.0 * (1 - 0.05 * (i % 6))
        out.append({"qid": f"Q-{1000 + i}",
                    "status": "Accepted" if i < n_won else "Closed Lost",
                    "lines": [(10, 100.0, net), (4, 50.0, 50.0 * (1 - 0.05 * (i % 6)))]})
    return out


# --- known answer: 3 quotes, 7 lines -----------------------------------------

KNOWN = [
    {"qid": "Q-1", "lines": [(10, 100.0, 80.0), (5, 40.0, 40.0), (2, 50.0, 45.0)]},
    {"qid": "Q-2", "status": "Closed Lost", "lines": [(1, 1000.0, 900.0), (3, 10.0, 10.0)]},
    {"qid": "Q-3", "lines": [(4, 25.0, 20.0), (8, 10.0, 9.0)]},
]


def test_known_answer_three_quotes_seven_lines_load_as_three_deals(monkeypatch):
    seen: dict = {}
    real = ingest._exclude_open

    def spy(df, report):
        seen["frame"] = df.copy()          # what _exclude_open is handed
        return real(df, report)

    monkeypatch.setattr(ingest, "_exclude_open", spy)
    lines = _lines(KNOWN)
    assert len(lines) == 7
    report = LoadReport(source="known")
    with pytest.raises(SchemaError, match="closed deal"):   # 3 < MIN_CLOSED_DEALS
        ingest._ingest_loaded(lines, report, 0.15)
    f = seen["frame"].set_index("source_quote_id")
    assert list(f.index) == ["Q-1", "Q-2", "Q-3"]           # rolled up first
    assert f.loc["Q-1", "list_acv"] == 10 * 100 + 5 * 40 + 2 * 50
    assert f.loc["Q-1", "booked_acv"] == 10 * 80 + 5 * 40 + 2 * 45
    assert f.loc["Q-2", "list_acv"] == 1000 + 30
    assert f.loc["Q-2", "booked_acv"] == 900 + 30
    assert f.loc["Q-3", "list_acv"] == 100 + 80
    assert f.loc["Q-3", "booked_acv"] == 80 + 72
    assert report.profile == mapping.PROFILE_CPQ and report.quote_lines_read == 7


def test_cpq_file_loads_end_to_end_one_deal_per_quote(tmp_path):
    df, rep = ingest_verbose(_write(_lines(_book()), tmp_path))
    assert len(df) == 40 and rep.rows_kept == 40
    assert rep.profile == "cpq_line" and rep.quote_lines_read == 80
    assert df["source_quote_id"].is_unique
    assert df["list_acv"].iloc[0] == 10 * 100 + 4 * 50
    assert set(df["outcome"]) == {"closed_won", "closed_lost"}
    assert "quote-line roll-up" in rep.field_sources["booked_acv"]
    assert "Quote ID" not in rep.unmapped_columns


# --- ask_user ----------------------------------------------------------------

def _with_ask(extra: list[dict]) -> list[dict]:
    return _book() + extra


ASK = [{"qid": "Q-9001", "status": "Declined"}, {"qid": "Q-9002", "status": "Declined"},
       {"qid": "Q-9003", "status": "Expired"}]


def test_ask_user_deals_are_surfaced_not_open_not_dropped_silently(tmp_path):
    _df, rep = ingest_verbose(_write(_lines(_with_ask(ASK)), tmp_path))
    assert rep.excluded_open == {}                       # not "open"
    assert set(rep.ask_user) == {"Declined", "Expired"}
    d = rep.ask_user["Declined"]
    assert d["deals"] == 2 and d["ids"] == ["Q-9001", "Q-9002"]
    assert d["id_kind"] == "quote_id"
    assert rep.ask_user["Expired"]["deals"] == 1
    assert "Declined: 2" in rep.summary()


def test_ask_user_is_never_closed_lost_and_never_enters_win_rate(tmp_path):
    base = run(_write(_lines(_book()), tmp_path, "a.csv"))["win_rate_by_band"]
    with_ask = run(_write(_lines(_with_ask(ASK)), tmp_path, "b.csv"))
    pd.testing.assert_frame_equal(base.reset_index(drop=True),
                                  with_ask["win_rate_by_band"].reset_index(drop=True))
    assert with_ask["load_report"].rows_kept == 40


def test_all_ask_user_raises_naming_the_stage_values(tmp_path):
    book = [{"qid": f"Q-{i}", "status": "Declined" if i % 2 else "On Hold"}
            for i in range(40)]
    with pytest.raises(SchemaError) as e:
        ingest_verbose(_write(_lines(book), tmp_path))
    msg = str(e.value)
    assert "Declined" in msg and "On Hold" in msg
    assert "no closed (won or lost)" not in msg and "do not recognise" in msg


def test_ask_user_in_a_crm_file_and_accepted_declined_are_not_open():
    def deal(i, stage):
        return {"opportunity_id": f"O{i}", "account_name": f"A{i}",
                "outcome": stage, "created_date": "2025-01-01",
                "close_date": "2025-03-01", "segment": "SMB",
                "product_tier": "Growth", "value_metric": "seats",
                "list_acv": 1000 + i, "booked_acv": 900 + i}
    stages = (["Accepted"] * 20 + ["Closed Lost"] * 15 + ["Declined"] * 3
              + ["Negotiation"] * 4 + ["Pending Legal Review"])
    frame = pd.DataFrame([deal(i, s) for i, s in enumerate(stages)])
    df, rep = ingest.ingest_frame_verbose(frame, source="crm")
    assert rep.excluded_open == {"negotiation": 4}       # Declined is not open
    assert rep.ask_user["Declined"]["deals"] == 3
    assert rep.ask_user["Declined"]["id_kind"] == "opportunity_id"
    assert rep.ask_user["Pending Legal Review"]["ids"] == ["O42"]
    assert int(df["is_won"].sum()) == 20 and len(df) == 35


def test_single_stage_table_ingest_has_no_alias_table():
    assert not hasattr(ingest, "OUTCOME_ALIASES")
    s = pd.Series(["Closed Won", "closedwon", "W", "Closed-Lost", "L", "Accepted",
                   "Declined", "Negotiation", "", None])
    got = ingest._canonical_outcome(s).tolist()
    assert got == [mapping.normalize_stage(v) if v else mapping.OUTCOME_ASK_USER
                   for v in s]
    assert got[5] == "closed_won" and got[6] == "ask_user" and got[7] == "open"


def test_diagnostic_payload_carries_ask_user_as_counts_and_ids_only(tmp_path):
    payload = diagnostic_payload(_write(_lines(_with_ask(ASK)), tmp_path), 0.15)
    sec = payload["ask_user"]
    assert sec["deals"] == 3
    by = {v["stage"]: v for v in sec["values"]}
    assert by["Declined"]["ids"] == ["Q-9001", "Q-9002"] and by["Declined"]["deals"] == 2
    allowed = {"stage", "deals", "id_kind", "ids", "ids_omitted"}
    assert all(set(v) == allowed for v in sec["values"])
    assert payload["load_report"]["ask_user"]["Expired"]["deals"] == 1
    blob = json.dumps(sec)
    assert "Acct" not in blob and "Northwind" not in blob      # no row values
    clean = diagnostic_payload(_write(_lines(_book()), tmp_path, "c.csv"), 0.15)
    assert clean["ask_user"] == {"deals": 0, "values": []}


# --- quarantine --------------------------------------------------------------

def test_blank_quote_ids_are_quarantined_and_counted(tmp_path):
    lines = _lines(_book())
    stray = lines.iloc[:2].copy()
    stray["Quote ID"] = ["", "  "]
    stray["Unit Price"] = "9999"
    _df, rep = ingest_verbose(_write(pd.concat([lines, stray]), tmp_path))
    assert rep.quarantined_lines == 2 and rep.rows_kept == 40
    assert "blank" in rep.quarantined_reason
    assert "2 line(s) with a blank or missing quote id" in rep.summary()


# --- several quotes per opportunity ------------------------------------------

def _multi(extra: list[dict]) -> pd.DataFrame:
    return _lines(_book() + extra)


def test_latest_quote_by_created_date_wins_and_is_not_double_counted(tmp_path):
    extra = [{"qid": "Q-5001", "opp": "OPP-X", "created": "2025-01-01",
              "lines": [(1, 500.0, 400.0)]},
             {"qid": "Q-5002", "opp": "OPP-X", "created": "2025-02-01",
              "lines": [(1, 700.0, 600.0)]}]
    df, rep = ingest_verbose(_write(_multi(extra), tmp_path))
    x = df[df["opportunity_id"] == "OPP-X"]
    assert len(x) == 1 and x["source_quote_id"].iloc[0] == "Q-5002"
    assert x["booked_acv"].iloc[0] == 600.0              # not 1000
    assert len(df) == 41
    qr = rep.quote_resolution
    assert qr["by_rule"] == {"latest_created_date": 1}
    assert qr["superseded_quote_ids"] == ["Q-5001"] and qr["quotes_superseded"] == 1
    assert "latest quote by sent date" in qr["rule"] and "primary" in qr["rule"]
    assert "Q-5001" not in json.dumps(rep.ask_user)


def test_sent_date_beats_created_date(tmp_path):
    extra = [{"qid": "Q-5001", "opp": "OPP-X", "created": "2025-01-01",
              "Sent Date": "2025-03-01", "lines": [(1, 500.0, 400.0)]},
             {"qid": "Q-5002", "opp": "OPP-X", "created": "2025-02-01",
              "Sent Date": "2025-02-10", "lines": [(1, 700.0, 600.0)]}]
    df, rep = ingest_verbose(_write(_multi(extra), tmp_path))
    assert df[df["opportunity_id"] == "OPP-X"]["source_quote_id"].tolist() == ["Q-5001"]
    assert rep.quote_resolution["by_rule"] == {"latest_sent_date": 1}


def test_primary_quote_when_dates_do_not_decide(tmp_path):
    extra = [{"qid": "Q-5001", "opp": "OPP-X", "Is Primary": "true", "lines": [(1, 500.0, 400.0)]},
             {"qid": "Q-5002", "opp": "OPP-X", "Is Primary": "false", "lines": [(1, 700.0, 600.0)]}]
    # identical created dates tie, so the primary flag decides
    df, rep = ingest_verbose(_write(_multi(extra), tmp_path))
    assert df[df["opportunity_id"] == "OPP-X"]["source_quote_id"].tolist() == ["Q-5001"]
    assert rep.quote_resolution["by_rule"] == {"primary_quote": 1}


def test_highest_quote_id_is_the_last_resort(tmp_path):
    extra = [{"qid": "Q-5009", "opp": "OPP-X", "lines": [(1, 500.0, 400.0)]},
             {"qid": "Q-5010", "opp": "OPP-X", "lines": [(1, 700.0, 600.0)]}]
    df, rep = ingest_verbose(_write(_multi(extra), tmp_path))
    assert df[df["opportunity_id"] == "OPP-X"]["source_quote_id"].tolist() == ["Q-5010"]
    assert rep.quote_resolution["by_rule"] == {"highest_quote_id": 1}   # 10 > 9, not "9" > "10"


def test_quote_resolution_is_deterministic_under_row_order(tmp_path):
    extra = [{"qid": "Q-5001", "opp": "OPP-X", "created": "2025-01-01"},
             {"qid": "Q-5002", "opp": "OPP-X", "created": "2025-02-01"}]
    a, _ = ingest_verbose(_write(_multi(extra), tmp_path, "a.csv"))
    shuffled = _multi(extra).sample(frac=1, random_state=3)
    b, _ = ingest_verbose(_write(shuffled, tmp_path, "b.csv"))
    assert (sorted(a["source_quote_id"]) == sorted(b["source_quote_id"])
            and a["booked_acv"].sum() == b["booked_acv"].sum())


# --- currency ----------------------------------------------------------------

def test_mixed_currency_symbols_on_quote_lines_are_blocked(tmp_path):
    lines = _lines(_book())
    lines.loc[0, "Unit Price"] = "$80"
    lines.loc[1, "Unit Price"] = "€40"
    with pytest.raises(ingest.CurrencyBlockedError):
        ingest_verbose(_write(lines, tmp_path))


# --- existing paths are unchanged --------------------------------------------

def test_crm_opportunity_profile_does_not_roll_up(tmp_path):
    from pricing.generate import generate
    df = generate(n=300, seed=7)
    p = tmp_path / "crm.csv"
    df.to_csv(p, index=False)
    out, rep = ingest_verbose(str(p))
    assert rep.profile != "cpq_line" and not rep.ask_user
    assert rep.quote_resolution == {} and rep.quarantined_lines == 0
    assert len(out) == int(df["outcome"].isin(["closed_won", "closed_lost"]).sum())


def test_pinned_dataset_hash_is_unchanged():
    import hashlib
    from pricing.generate import generate
    crlf = chr(13) + chr(10)
    sha = hashlib.sha256(generate(n=2000, seed=7).to_csv(
        index=False, lineterminator=crlf).encode("utf-8")).hexdigest()
    assert sha == "ecfa1b6b25bd69d8258ced8d88ded57d21e31e87fc45166cdc8a2c306143ea48"


# --- /map-columns ------------------------------------------------------------

@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("PRICEKEEL_API_KEY", raising=False)
    monkeypatch.setenv("PRICEKEEL_ENV", "dev")
    main._rate_state_reset()
    yield TestClient(main.app)
    main._rate_state_reset()


def test_map_columns_bounds_the_header_count(client):
    ok = client.post("/map-columns", json={"headers": [f"h{i}" for i in range(200)]})
    assert ok.status_code == 200
    over = client.post("/map-columns", json={"headers": [f"h{i}" for i in range(201)]})
    assert over.status_code == 422


def test_map_columns_goes_through_layer_zero_and_says_it_is_header_only(client, monkeypatch):
    monkeypatch.setattr(assist, "has_llm", lambda: True)

    def boom(_h):
        raise AssertionError("LLM must not see a billing export's headers")

    monkeypatch.setattr(assist, "map_columns", boom)
    headers = ["Subscription ID", "Customer ID", "Plan", "Billing Interval",
               "Subscription Status", "Unit Amount"]
    r = client.post("/map-columns", json={"headers": headers}).json()
    via_headers = mapping.map_headers(headers, llm_fallback=False, use_embeddings=False)
    assert r["refusal"] == via_headers["refusal"] and r["refusal"]["refused"]
    assert r["profile"] == via_headers["profile"]
    assert "header suggestion only" in r["scope"]


def test_map_columns_reports_the_cpq_profile_and_never_an_llm_outcome(client, monkeypatch):
    monkeypatch.setattr(assist, "has_llm", lambda: True)
    monkeypatch.setattr(assist, "map_columns",
                        lambda hs: {"outcome": "Quote Status", "segment": "Tier Zone"})
    headers = HEAD + ["Tier Zone"]
    r = client.post("/map-columns", json={"headers": headers}).json()
    assert r["profile"]["profile"] == "cpq_line" and r["refusal"] is None
    assert r["mapping"]["outcome"] is None


def test_diagnostic_route_returns_ask_user_and_all_ask_user_is_422(client, tmp_path):
    csv = _lines(_with_ask(ASK)).to_csv(index=False).encode()
    r = client.post("/diagnostic", files={"file": ("q.csv", io.BytesIO(csv), "text/csv")},
                    data={"policy": "0.15"})
    assert r.status_code == 200 and r.json()["ask_user"]["deals"] == 3
    bad = _lines([{"qid": f"Q-{i}", "status": "Declined"} for i in range(40)])
    r = client.post("/diagnostic",
                    files={"file": ("q.csv", io.BytesIO(bad.to_csv(index=False).encode()), "text/csv")},
                    data={"policy": "0.15"})
    assert r.status_code == 422 and "Declined" in r.json()["detail"]
