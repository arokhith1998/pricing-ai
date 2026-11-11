"""PK-99: the cost_period_actuals grain and the planted margin-health answer key.

Pins three things. (1) The schema: the cost grain sits beside CONTRACT_PERIOD_
FIELDS, carries no end-customer name or email, and changes nothing the deal
schema or the billing grain emitted before. (2) The generator: seeded, on its
own stream, and hash-pinned like data/synthetic/deals.csv, with the committed
fixture under data/synthetic/cost-export/ byte-equal to a fresh run. (3) The
planted answers (design doc section 7.1, MA-01 to MA-15): literals typed here,
re-derived from the CSV bytes by a small independent loop, and compared with
the key the generator writes.

Binding decisions: ADR-006, ADR-007, founder F1 and F12 in
docs/reviews/2026-11-10-audit-first/FOUNDER-DECISIONS.md.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from pricing.generate import generate
from pricing.generate_billing import (
    COST_FILE_COLUMNS, COST_PRICE_POLICIES, COST_SPAWN_KEY, _allocate,
    cost_frame_in_cents, cost_key_json, cost_key_map_frame, generate_billing,
    generate_cost_fixture, write_cost_fixture,
)
from pricing.schema import (
    ALL_COLUMNS, ALL_FIELD_NAMES, CONTRACT_PERIOD_COLUMNS, COST_EXACT_ONLY_FIELDS,
    COST_EXPORT_PROFILE, COST_KEY_MAP_COLUMNS, COST_PERIOD_COLUMNS, COST_PERIOD_DERIVED_FIELDS,
    COST_PERIOD_FIELDS, COST_PERIOD_FILE_COLUMNS, COST_PERIOD_KEY_FIELDS,
    COST_PERIOD_MONEY_FIELDS, COST_UPLOAD_BASIS_ALLOWED, FIELDS, GENERATOR_COLUMNS,
    CostAttribution, CostBasis, CostCategory, CostKeyType,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "data" / "synthetic" / "cost-export"
CRLF = chr(13) + chr(10)
D = Decimal


def _sha(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False, lineterminator=CRLF).encode("utf-8")).hexdigest()


def _cols(df: pd.DataFrame) -> dict[str, str]:
    return {c: hashlib.sha256(df[[c]].to_csv(index=False, lineterminator=CRLF).encode("utf-8")).hexdigest()[:12]
            for c in df.columns}


@pytest.fixture(scope="module")
def book():
    b, c, k = generate_cost_fixture(7, 20, "cost_plus")
    return b, c, k


# --- (1) the schema ----------------------------------------------------------

def test_cost_grain_fields_and_order():
    assert COST_PERIOD_COLUMNS == [
        "cost_vendor", "cost_category", "cost_line", "customer_key", "customer_key_type",
        "cost_start", "cost_end", "cost_currency", "cost_amount", "cost_basis", "attribution"]
    assert [f.name for f in COST_PERIOD_FIELDS] == COST_PERIOD_COLUMNS
    assert all(not f.required for f in COST_PERIOD_FIELDS)  # nothing is guessed into REQUIRED_FIELDS
    assert COST_PERIOD_MONEY_FIELDS == ["cost_amount"]
    assert COST_PERIOD_KEY_FIELDS == ["cost_start", "cost_end", "cost_currency", "cost_amount"]
    assert COST_KEY_MAP_COLUMNS == ["customer_key_type", "customer_key", "source_record_id"]
    assert COST_EXPORT_PROFILE == "cost_export"


def test_attribution_is_derived_never_read_from_a_file():
    assert COST_PERIOD_DERIVED_FIELDS == ["attribution"]
    assert "attribution" not in COST_PERIOD_FILE_COLUMNS
    assert {m.value for m in CostAttribution} == {"direct", "allocated", "not_attributable"}
    assert "never read from a file" in {f.name: f for f in COST_PERIOD_FIELDS}["attribution"].description


def test_enums():
    assert {m.value for m in CostCategory} == {"inference", "compute", "storage", "other"}
    assert {m.value for m in CostKeyType} == {
        "source_record_id", "api_key_id", "project_id", "workspace_id", "customer_tag"}


def test_no_end_customer_name_email_or_contact_field():
    banned = ("name", "email", "mail", "contact", "phone", "address", "person", "user")
    for f in COST_PERIOD_FIELDS:
        assert not any(b in f.name.lower() for b in banned), f.name
    for col in COST_KEY_MAP_COLUMNS:
        assert not any(b in col.lower() for b in banned), col


def test_cost_amount_is_text_so_blank_and_unparseable_stay_visible():
    amount = {f.name: f for f in COST_PERIOD_FIELDS}["cost_amount"]
    assert amount.dtype == "str"
    assert "never read as 0" in amount.description


def test_the_cost_grain_is_a_separate_grain():
    cost = set(COST_PERIOD_COLUMNS)
    assert cost & set(ALL_FIELD_NAMES) == {"cost_basis"}  # the ADR-006 enum is shared on purpose
    assert not cost & set(GENERATOR_COLUMNS)
    assert not cost & set(CONTRACT_PERIOD_COLUMNS)
    assert ALL_COLUMNS == ALL_FIELD_NAMES
    assert len(FIELDS) == len(ALL_FIELD_NAMES)


def test_billing_grain_is_unchanged_and_carries_no_cost_field():
    assert CONTRACT_PERIOD_COLUMNS == [
        "source_system", "source_record_id", "period_index", "period_start", "period_end", "currency",
        "list_amount", "invoiced_amount", "discount_amount", "credit_amount", "usage_units",
        "usage_amount", "committed_amount"]


def test_exact_only_fields_and_the_upload_basis_rule():
    assert COST_EXACT_ONLY_FIELDS == frozenset({
        "customer_key", "customer_key_type", "cost_amount", "cost_category", "cost_basis",
        "source_record_id"})
    # ADR-007: an upload may carry declared_cost and nothing stronger. erp_verified is
    # reserved for a connector Pricekeel operates; crm_proxy is the no-declaration state.
    assert COST_UPLOAD_BASIS_ALLOWED == frozenset({"declared_cost"})
    assert CostBasis.ERP_VERIFIED.value not in COST_UPLOAD_BASIS_ALLOWED


def test_generated_columns_omit_basis_and_attribution():
    assert COST_FILE_COLUMNS == [c for c in COST_PERIOD_COLUMNS if c not in ("cost_basis", "attribution")]


def test_fixture_headers_look_like_a_cost_export_not_a_crm_or_billing_file():
    """Header-only reading of the cost_export fingerprint (design 2.5): a cost-amount
    header, a cost dimension, and no CRM or billing veto."""
    tokens = {t for h in COST_FILE_COLUMNS for t in h.lower().split("_")}
    assert tokens & {"cost", "spend", "charge", "unblended"}
    assert tokens & {"model", "project", "workspace", "key", "service", "product", "line"}
    assert not tokens & {"stage", "opportunity", "subscription", "invoice", "mrr", "plan", "interval"}
    assert "amount" in tokens and "cost_amount" in COST_FILE_COLUMNS


# --- existing generators are untouched --------------------------------------------

DEALS_PIN = "ecfa1b6b25bd69d8258ced8d88ded57d21e31e87fc45166cdc8a2c306143ea48"
# Taken on origin/main at 4f6f33b, before PK-99, for generate_billing(7, 20).
BILLING_PIN = "776e67c52b4b0c73307b0d0f8e537ce89b0b57ef088aee0b179c3953a85b7548"
BILLING_KEY_PIN = "8496975d15cad30755726153b33a19c8eddda825da3d253456fc957ac09ef960"


def test_deal_generator_output_is_byte_identical():
    df = generate(n=2000, seed=7)[GENERATOR_COLUMNS]
    assert _sha(df) == DEALS_PIN


def test_pk53_billing_generator_and_key_are_byte_identical():
    df, key = generate_billing(7, 20)
    assert _sha(df) == BILLING_PIN
    assert hashlib.sha256(json.dumps(key, default=str, sort_keys=True).encode()).hexdigest() == BILLING_KEY_PIN


def test_cost_stream_is_its_own():
    assert COST_SPAWN_KEY == (0x4D48,)
    assert COST_SPAWN_KEY != (53,)  # generate_billing's key


# --- (2) the generator: seeded and hash-pinned -----------------------------------

PIN_BILLING_COST_PLUS = "412668ebbf35871cc13150dc2a1ee0c1c341e228ba4575177960f115a87153b5"
PIN_BILLING_HELD = "fb2258f9a36207e287f464aa321ddc6f81ca440ce70310a90302188f2257dcdb"
PIN_COST = "355d70089d102e2a380f465aa7485c633d42d63ede167219151d90cc6a3af3ff"
PIN_COST_CENTS = "7d564ba76e57e3bba8f790d6f62f2952f3790500acfaf174db543e9890ca86bb"
PIN_COST_COLUMNS = {"cost_vendor": "3eb4ed11dd16", "cost_category": "ccc34034ae88", "cost_line": "6a1fbfcc0ba3", "customer_key": "6846efc0d4e3", "customer_key_type": "4b650835eff6", "cost_start": "405b357e43e2", "cost_end": "411f9f908be8", "cost_currency": "2c523737a4ae", "cost_amount": "37c2aa892d3b"}
PIN_BILLING_COST_PLUS_COLUMNS = {"source_system": "44e8102b0ee0", "source_record_id": "31ae3ce5baf1", "period_index": "34f2ff55af85", "period_start": "9eaaff320e4c", "period_end": "ec289eef1c42", "currency": "25d03e089aa3", "list_amount": "51f4f1a10a83", "invoiced_amount": "8db14de1c5a9", "discount_amount": "b352407a2026", "credit_amount": "2a35df1416e5", "usage_units": "b51a1c5cf375", "usage_amount": "1162a42a0f6b", "committed_amount": "6e539f549211"}
PIN_BILLING_HELD_COLUMNS = {"source_system": "44e8102b0ee0", "source_record_id": "31ae3ce5baf1", "period_index": "34f2ff55af85", "period_start": "9eaaff320e4c", "period_end": "ec289eef1c42", "currency": "25d03e089aa3", "list_amount": "cad510db74c5", "invoiced_amount": "6e534c13320c", "discount_amount": "b352407a2026", "credit_amount": "2a35df1416e5", "usage_units": "b51a1c5cf375", "usage_amount": "58a12159e1bc", "committed_amount": "6e539f549211"}


def test_cost_frame_hash_pin(book):
    _, cost, _ = book
    assert list(cost.columns) == COST_FILE_COLUMNS
    assert _cols(cost) == PIN_COST_COLUMNS  # names the column that moved
    assert _sha(cost) == PIN_COST


def test_billing_frame_hash_pins_per_price_policy(book):
    bp = book[0]
    bh, _, _ = generate_cost_fixture(7, 20, "held")
    assert list(bp.columns) == CONTRACT_PERIOD_COLUMNS
    assert _cols(bp) == PIN_BILLING_COST_PLUS_COLUMNS
    assert _cols(bh) == PIN_BILLING_HELD_COLUMNS
    assert _sha(bp) == PIN_BILLING_COST_PLUS
    assert _sha(bh) == PIN_BILLING_HELD


def test_cents_frame_hash_pin(book):
    assert _sha(cost_frame_in_cents(book[1])) == PIN_COST_CENTS


def test_same_seed_same_bytes_and_policy_only_moves_billing(book):
    b2, c2, k2 = generate_cost_fixture(7, 20, "cost_plus")
    assert _sha(b2) == _sha(book[0]) and _sha(c2) == _sha(book[1])
    assert cost_key_json(k2) == cost_key_json(book[2])
    bh, ch, kh = generate_cost_fixture(7, 20, "held")
    assert _sha(ch) == _sha(book[1])
    assert cost_key_json(kh) == cost_key_json(book[2])  # the key holds both policies
    assert _sha(bh) != _sha(book[0])
    with pytest.raises(ValueError):
        generate_cost_fixture(7, 20, "bogus")


def test_planted_accounts_do_not_depend_on_the_seed_and_filler_does():
    b0, c0, k0 = generate_cost_fixture(1, 0)
    b1, c1, k1 = generate_cost_fixture(99, 0)
    assert _sha(b0) == _sha(b1) and _sha(c0) == _sha(c1)
    assert k0["accounts"] == k1["accounts"]
    ba, ca, _ = generate_cost_fixture(1, 20)
    bb, cb_, _ = generate_cost_fixture(2, 20)
    assert _sha(ca) != _sha(cb_) and _sha(ba) != _sha(bb)


def test_committed_fixture_matches_a_fresh_run_byte_for_byte(tmp_path):
    """Never skips: the committed bytes (LF, per .gitattributes) equal a regeneration."""
    fresh = write_cost_fixture(tmp_path / "fresh", 7, 20)
    names = {p.name for p in fresh}
    assert names == {"billing-cost-plus.csv", "billing-held.csv", "cost.csv", "cost-anthropic-cents.csv",
                     "key-map.csv", "answer-key.json"}
    assert {p.name for p in FIXTURE_DIR.iterdir()} == names
    for p in fresh:
        assert (FIXTURE_DIR / p.name).read_bytes() == p.read_bytes(), p.name
    assert (FIXTURE_DIR / "cost.csv").read_bytes().replace(b"\r\n", b"\n") == (FIXTURE_DIR / "cost.csv").read_bytes()
    assert hashlib.sha256((FIXTURE_DIR / "cost.csv").read_bytes()).hexdigest() == \
        "b0e42403b72f67679c8ff3acc38662e4c93311ca43279ffac333f18449110893"
    assert hashlib.sha256((FIXTURE_DIR / "answer-key.json").read_bytes()).hexdigest() == \
        "1c2c02f43d381101d87f5554936ebee7550c1156bf54de55fd4891ca12478e9b"


def test_fixture_has_no_contact_data_or_real_names():
    text = "".join(p.read_text(encoding="utf-8") for p in FIXTURE_DIR.glob("*.csv"))
    assert "@" not in text
    for row in csv.DictReader(io.StringIO((FIXTURE_DIR / "billing-cost-plus.csv").read_text())):
        assert row["source_record_id"].startswith("sub_")


# --- a small independent reader of the CSV bytes ------------------------------------

def _read(name):
    with open(FIXTURE_DIR / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _month_end_ok(start: str, end: str) -> bool:
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    nxt = date(e.year + (e.month == 12), e.month % 12 + 1, 1)
    return s.day == 1 and e.month == s.month and e.year == s.year and (nxt - e).days == 1


def _valid_cost_rows(rows, *, scale=D(1)):
    """Row hygiene in the spec's order, done the slow obvious way.

    Returns (survivors, counts). survivors: dicts with Decimal dollars."""
    counts = defaultdict(int)
    parsed = []
    for r in rows:
        raw = r["cost_amount"]
        if raw.strip() == "":
            counts["cost_blank_amount"] += 1
            continue
        try:
            amount = D(raw) * scale
        except Exception:
            counts["cost_unparseable_amount"] += 1
            continue
        if amount < 0:
            counts["cost_negative_amount"] += 1
            continue
        parsed.append({**r, "amount": amount, "cost_currency": r["cost_currency"].upper()})
    ident = lambda r: (r["cost_vendor"], r["cost_category"], r["cost_line"], r["customer_key"],
                       r["cost_start"], r["cost_end"], r["cost_currency"])
    seen, deduped = set(), []
    for r in parsed:
        t = ident(r) + (r["amount"],)
        if t in seen:
            counts["cost_duplicate_collapsed"] += 1
            continue
        seen.add(t)
        deduped.append(r)
    amounts = defaultdict(set)
    for r in deduped:
        amounts[ident(r)].add(r["amount"])
    out = []
    for r in deduped:
        if len(amounts[ident(r)]) > 1:
            counts["cost_conflict"] += 1
            continue
        out.append(r)
    return out, dict(counts)


def _oracle(cost_name="cost.csv", billing_name="billing-cost-plus.csv", scale=D(1)):
    """Per-account (revenue, cost, result) over aligned account-periods, from the files."""
    cost, counts = _valid_cost_rows(_read(cost_name), scale=scale)
    keymap = {(r["customer_key_type"], r["customer_key"]): r["source_record_id"] for r in _read("key-map.csv")}
    billing = defaultdict(list)
    for r in _read(billing_name):
        billing[r["source_record_id"]].append(r)
    acct = {}
    for c in cost:
        k = c["customer_key"]
        if c["customer_key_type"] == "source_record_id" and k in billing:
            c["sub"] = k
        else:
            c["sub"] = keymap.get((c["customer_key_type"], k))
    per = defaultdict(lambda: [D(0), D(0), 0])
    for sub, rows in billing.items():
        by_period = defaultdict(list)
        for r in rows:
            by_period[(r["period_start"], r["period_end"])].append(r)
        for (ps, pe), rs in by_period.items():
            if len(rs) > 1 or not _month_end_ok(ps, pe):
                continue
            inside = [c for c in cost if c.get("sub") == sub and ps <= c["cost_start"] and c["cost_end"] <= pe]
            if not inside or any(c["cost_currency"] != rs[0]["currency"] for c in inside):
                continue
            rev = D(rs[0]["invoiced_amount"])
            cst = sum((c["amount"] for c in inside), D(0))
            per[sub][0] += rev
            per[sub][1] += cst
            per[sub][2] += 1
    return {s: (v[0], v[1], v[0] - v[1], v[2]) for s, v in per.items()}, cost, counts


# --- (3) the planted answers ---------------------------------------------------------

def test_oracle_from_the_csv_bytes_matches_the_key_for_every_scored_account(book):
    got, _, _ = _oracle()
    key = book[2]
    scored = {s for s, a in key["accounts"].items() if a["status"] == "scored"} | set(key["filler_accounts"])
    assert set(got) == scored  # nothing extra scored, nothing missing
    for s, a in key["accounts"].items():
        if a["status"] == "scored":
            assert (got[s][0], got[s][1], got[s][2], got[s][3]) == (
                D(a["revenue_total"]), D(a["cost_total"]), D(a["result_total"]), a["scored_periods"]), s
    for s, f in key["filler_accounts"].items():
        p = f["cost_plus"]
        assert (got[s][0], got[s][1], got[s][2]) == (p["revenue_total"], p["cost_total"], p["result_total"]), s


def test_held_policy_oracle_matches_the_key_for_filler():
    got, _, _ = _oracle(billing_name="billing-held.csv")
    key = generate_cost_fixture(7, 20, "held")[2]
    for s, f in key["filler_accounts"].items():
        p = f["held"]
        assert (got[s][0], got[s][1], got[s][2]) == (p["revenue_total"], p["cost_total"], p["result_total"]), s


# Spec 7.1, typed independently of the generator: (cost a month, result a month, result_pct,
# break-even units, headroom). Dollars; ratios to 4 places.
PLANTED = {
    "sub_heavy_1":   (D("8000.00"), D("-5000.00"), D("-1.6667"), 750_000, D("0.3750")),   # MA-01
    "sub_heavy_2":   (D("6000.00"), D("-1000.00"), D("-0.2000"), 1_250_000, D("0.8333")),  # MA-02
    "sub_thin":      (D("800.00"), D("200.00"), D("0.2000"), 200_000, D("2.0000")),        # MA-03
    "sub_near":      (D("2800.00"), D("200.00"), D("0.0667"), 750_000, D("1.0714")),       # MA-04
    "sub_hybrid_ok": (D("400.00"), D("1600.00"), D("0.8000"), None, None),                 # MA-05
}


@pytest.mark.parametrize("sub", sorted(PLANTED))
def test_planted_heavy_and_thin_users(book, sub):
    cost_pm, res_pm, pct, star, headroom = PLANTED[sub]
    a = book[2]["accounts"][sub]
    assert a["status"] == "scored" and a["scored_periods"] == 12
    assert a["cost_total"] == cost_pm * 12
    assert a["result_by_period"] == [res_pm] * 12
    assert a["result_pct_by_period"] == [pct] * 12
    assert a["break_even_units"] == star and a["headroom"] == headroom


def test_planted_flags(book):
    k = book[2]
    assert k["negative_accounts"] == ["sub_heavy_1", "sub_heavy_2"]
    assert k["accounts"]["sub_heavy_1"]["negative_periods"] == 12
    assert k["accounts"]["sub_heavy_1"]["persistent"] is True
    assert k["accounts"]["sub_heavy_2"]["persistent"] is True
    assert k["near_break_even_accounts"] == ["sub_near"]
    assert k["accounts"]["sub_hybrid_ok"]["price_above_cost"] is True
    thin = k["accounts"]["sub_thin"]
    assert (thin["price_per_unit"], thin["cost_per_unit"]) == (D("0.0060"), D("0.0080"))
    heavy = k["accounts"]["sub_heavy_1"]
    assert (heavy["price_per_unit"], heavy["cost_per_unit"]) == (D("0.0000"), D("0.0040"))


def test_ma06_free_months_are_scored_with_a_null_percentage(book):
    a = book[2]["accounts"]["sub_free"]
    assert a["scored_periods"] == 12 and a["zero_revenue_periods"] == 3
    assert a["result_by_period"][:3] == [D("-400.00")] * 3
    assert a["result_pct_by_period"][:3] == [None] * 3
    assert a["result_by_period"][3:] == [D("600.00")] * 9
    b = book[0]
    free = b[b["source_record_id"] == "sub_free"]
    assert list(free["invoiced_amount"][:3]) == [0.0] * 3
    assert all(c > 0 for c in free["credit_amount"][:3])  # a coupon, not a refund


def test_ma07_no_cost_is_not_a_hundred_percent_result(book):
    k = book[2]
    a = k["accounts"]["sub_nocost"]
    assert a["status"] == "not_provided" and a["reason"] == "cost_not_in_file"
    assert "result_total" not in a
    assert k["exclusions"]["accounts"]["cost_not_in_file"] == {
        "count": 1, "noun": "accounts", "revenue": D("12000.00")}
    assert not any(r["customer_key"] == "sub_nocost" for r in _read("cost.csv"))
    assert "sub_nocost" not in {m["source_record_id"] for m in _read("key-map.csv")}


def test_ma08_currency_mismatch_is_counted_not_converted(book):
    k = book[2]
    assert k["accounts"]["sub_eur"]["reason"] == "period_currency_mismatch"
    ex = k["exclusions"]["account_periods"]["period_currency_mismatch"]
    assert (ex["count"], ex["revenue"], ex["revenue_currency"], ex["cost"], ex["cost_currency"]) == (
        12, D("12000.00"), "EUR", D("3600.00"), "USD")
    b = book[0]
    assert set(b[b["source_record_id"] == "sub_eur"]["currency"]) == {"EUR"}
    assert {r["cost_currency"] for r in _read("cost.csv") if r["customer_key"] == "ws_eur"} == {"USD"}
    assert "sub_eur" not in _oracle()[0]


def test_ma09_weekly_periods_are_never_rounded_to_a_month(book):
    b = book[0]
    w = b[b["source_record_id"] == "sub_weekly"]
    assert len(w) == 8
    assert all((date.fromisoformat(e) - date.fromisoformat(s)).days == 6
               for s, e in zip(w["period_start"], w["period_end"]))
    assert book[2]["exclusions"]["account_periods"]["period_not_whole_months"]["count"] == 8
    assert "sub_weekly" not in _oracle()[0]


def test_ma10_conflicting_billing_rows_exclude_march_only(book):
    b = book[0]
    c = b[b["source_record_id"] == "sub_conflict"]
    march = c[c["period_start"] == "2026-03-01"]
    assert len(march) == 2 and march["invoiced_amount"].nunique() == 2
    a = book[2]["accounts"]["sub_conflict"]
    assert a["scored_periods"] == 11 and a["conflict_reason"] == "period_billing_conflict"
    assert book[2]["exclusions"]["account_periods"]["period_billing_conflict"]["count"] == 1
    assert _oracle()[0]["sub_conflict"][3] == 11


def test_ma11_zero_usage_with_cost(book):
    z = book[0]
    z = z[z["source_record_id"] == "sub_zero_usage"]
    assert list(z["usage_units"]) == [0.0, 0.0, 0.0]  # a zero, not a blank
    a = book[2]["accounts"]["sub_zero_usage"]
    assert a["break_even_status"] == "insufficient_data" and a["break_even_reason"] == "zero_usage_units"
    assert a["cost_per_unit"] == "not_given" and a["cost_total"] == D("450.00")


def test_ma12_and_ma13_unattributable_pools(book):
    """F12: no allocation rule by default. Unattributable cost stays a line of its own and
    marks the readout upper_bound when it passes the 20 percent cap."""
    at = book[2]["attribution"]
    assert at["pools"]["shared_compute"] == {"rows": 12, "amount": D("14400.00")}
    assert at["pools"]["unmapped_project"] == {"key": "proj_unmapped", "rows": 31, "amount": D("775.00")}
    assert at["pools"]["shared_storage"]["rows"] == 12
    assert at["not_attributable"]["rows"] == 12 + 31 + 12
    assert at["not_attributable"]["amount"] == D("14400.00") + D("775.00") + at["pools"]["shared_storage"]["amount"]
    total = at["direct"]["amount"] + at["not_attributable"]["amount"]
    assert total == book[2]["book_cost"]["amount"]
    assert at["not_attributable"]["share"] == (at["not_attributable"]["amount"] / total).quantize(D("0.0001"))
    assert at["not_attributable"]["share"] > D("0.20") and at["upper_bound"] is True
    rows = _read("cost.csv")
    unmapped = [r for r in rows if r["customer_key"] == "proj_unmapped"]
    assert len(unmapped) == 31 and all(r["cost_amount"] == "25.00" for r in unmapped)
    assert {r["cost_start"][:7] for r in unmapped} == {"2026-03"}
    assert "proj_unmapped" not in {m["customer_key"] for m in _read("key-map.csv")}
    shared = [r for r in rows if r["customer_key"] == "" and r["cost_category"] == "compute"]
    assert len(shared) == 12 and all(r["cost_amount"] == "1200.00" for r in shared)


def test_ma14_storage_share_rises_from_ten_to_forty_percent_from_the_csv(book):
    """Recomputed from the file bytes, not from the key."""
    _, valid, _ = _oracle()
    by_month = defaultdict(lambda: [D(0), D(0)])
    for r in valid:
        if r["cost_start"] < "2026-01-01":
            continue
        by_month[r["cost_start"][:7]][0 if r["cost_category"] == "storage" else 1] += r["amount"]
    shares = [by_month[m][0] / (by_month[m][0] + by_month[m][1]) for m in sorted(by_month)]
    assert len(shares) == 12
    assert shares[0].quantize(D("0.0001")) == D("0.1000") and shares[-1].quantize(D("0.0001")) == D("0.4000")
    assert shares == sorted(shares)
    tr = book[2]["storage_trend"]
    assert tr["direction"] == "up" and (tr["first_share"], tr["last_share"]) == (D("0.1000"), D("0.4000"))
    assert [m["realized_share"] for m in tr["months"]] == [s.quantize(D("0.0001")) for s in shares]


def test_ma15_price_policy_pass_through_and_markup(book):
    pp = book[2]["price_policy"]
    cost = pp["cost_per_credit_by_month"]
    assert cost[0] == D("0.004000") and cost[-1] == D("0.002000")  # falls 50 percent
    assert [i["index"] for i in pp["supplied_index"]][0] == D("100.00")
    assert [i["index"] for i in pp["supplied_index"]][-1] == D("50.00")
    cp, held = pp["policies"]["cost_plus"], pp["policies"]["held"]
    assert cp["expected_label"] == "cost_plus_pattern" and cp["pass_through"] == D("1.0000")
    assert held["expected_label"] == "markup_expanding" and held["pass_through"] is None
    for m in range(12):
        assert cp["filler_price_per_credit_by_month"][m] == (cost[m] * D("2.5")).quantize(D("0.0000001"))
        assert held["filler_price_per_credit_by_month"][m] == D("0.01")
    # In the billing files the filler metered price per credit is what the key says.
    for name, pol in (("billing-cost-plus.csv", cp), ("billing-held.csv", held)):
        rows = [r for r in _read(name) if r["source_record_id"] == "sub_f000"]
        for m, r in enumerate(rows):
            implied = D(r["usage_amount"]) / D(r["usage_units"])
            assert abs(implied - pol["filler_price_per_credit_by_month"][m]) < D("0.0001")  # cents rounding


def test_hygiene_rows_have_known_counts_and_amounts(book):
    ex = book[2]["exclusions"]["cost_rows"]
    assert {k: (v["count"], v["amount"]) for k, v in ex.items()} == {
        "cost_straddles_periods": (1, D("500.00")),
        "cost_outside_billing_periods": (4, D("650.00")),   # 2025-12, two sub_weekly, one March sub_conflict
        "cost_duplicate_collapsed": (7, D("2000.04")),
        "cost_conflict": (2, D("95.00")),
        "cost_blank_amount": (3, None),
        "cost_unparseable_amount": (2, None),
        "cost_negative_amount": (1, D("-75.00")),
    }
    assert book[2]["exclusions"]["lowercase_currency_rows"] == 1
    # Re-derive the row-hygiene counts from the file.
    _, _, counts = _oracle()
    assert counts == {"cost_blank_amount": 3, "cost_unparseable_amount": 2, "cost_negative_amount": 1,
                      "cost_duplicate_collapsed": 7, "cost_conflict": 2}
    rows = _read("cost.csv")
    assert sum(1 for r in rows if r["cost_amount"] == "") == 3
    assert {"1,200", "$100"} <= {r["cost_amount"] for r in rows}
    straddle = [r for r in rows if (r["cost_start"], r["cost_end"]) == ("2026-05-15", "2026-06-14")]
    assert len(straddle) == 1
    outside = [r for r in rows if r["cost_start"].startswith("2025-12")]
    assert len(outside) == 1


def test_never_zero_no_cost_row_is_a_zero_and_blank_cells_are_empty(book):
    for r in _read("cost.csv"):
        a = r["cost_amount"]
        if a in ("", "1,200", "$100"):
            continue
        assert D(a) != 0, r


def test_coverage_spans_the_billing_year_and_one_earlier_row(book):
    rows = _read("cost.csv")
    starts = sorted(r["cost_start"] for r in rows)
    ends = sorted(r["cost_end"] for r in rows)
    assert starts[0] == "2025-12-01" and ends[-1] == "2026-12-31"


# --- the join: a customer-declared key map ----------------------------------------------

def test_key_map_is_unique_per_key_and_joins_only_declared_keys(book):
    km = _read("key-map.csv")
    keys = [(m["customer_key_type"], m["customer_key"]) for m in km]
    assert len(keys) == len(set(keys))  # one key never maps to two accounts
    billing_ids = {r["source_record_id"] for r in _read("billing-cost-plus.csv")}
    assert {m["source_record_id"] for m in km} <= billing_ids
    assert list(cost_key_map_frame(book[2]).columns) == COST_KEY_MAP_COLUMNS
    cost = _read("cost.csv")
    mapped = set(keys)
    direct_ids = {(r["customer_key_type"], r["customer_key"]) for r in cost
                  if r["customer_key_type"] == "source_record_id"}
    assert all(k in billing_ids for _, k in direct_ids)
    unmapped = {(r["customer_key_type"], r["customer_key"]) for r in cost
                if r["customer_key"] and r["customer_key_type"] != "source_record_id"} - mapped
    assert unmapped == {("project_id", "proj_unmapped")}
    # Every key type in the file is a CostKeyType, every category a CostCategory.
    assert {r["customer_key_type"] for r in cost} - {""} <= {m.value for m in CostKeyType}
    assert {r["cost_category"] for r in cost} <= {m.value for m in CostCategory}


# --- the allocation variant (F12: only with a rule the user confirms) ----------------------

def test_allocate_sums_exactly_and_breaks_ties_by_id():
    assert _allocate(100_000, {"a": 1, "b": 1, "c": 1}) == {"a": 33_334, "b": 33_333, "c": 33_333}
    assert _allocate(10, {"b": 1, "a": 1}) == {"a": 5, "b": 5}
    assert _allocate(1, {"b": 1, "a": 1}) == {"a": 1, "b": 0}
    assert _allocate(500, {"a": 0, "b": 0}) == {}  # no driver: stays not_attributable


def test_allocation_variant_conserves_the_storage_pool_each_month(book):
    av = book[2]["allocation_variant"]
    assert av["rule"] == "proportional_to_usage_units" and av["pool"] == {"cost_category": "storage"}
    assert len(av["months"]) == 12
    for m in av["months"]:
        assert sum(m["allocated_cents"].values()) == m["pool_cents"]
        assert m["driver_units_total"] > 0
    # Not a default: nothing in the cost file carries an attribution or allocation.
    assert "attribution" not in COST_FILE_COLUMNS
    # A zero-usage account is in the driver set for its months and gets no share.
    jan = av["months"][0]["allocated_cents"]
    assert jan["sub_zero_usage"] == 0
    # Excluded account-periods are not drivers: MA-08, MA-09, MA-07 and conflicted March.
    assert not {"sub_eur", "sub_weekly", "sub_nocost"} & set(jan)
    assert "sub_conflict" not in av["months"][2]["allocated_cents"]
    assert "sub_conflict" in av["months"][3]["allocated_cents"]


# --- the Anthropic cents case: a 100x error is caught ---------------------------------------

def test_cents_file_is_exactly_the_dollar_file_times_one_hundred():
    dollars, cents = _read("cost.csv"), _read("cost-anthropic-cents.csv")
    assert len(dollars) == len(cents)
    for d, c in zip(dollars, cents):
        assert {k: v for k, v in d.items() if k != "cost_amount"} == {k: v for k, v in c.items() if k != "cost_amount"}
        if d["cost_amount"] in ("", "1,200", "$100"):
            assert d["cost_amount"] == c["cost_amount"]
        else:
            assert D(c["cost_amount"]) == D(d["cost_amount"]) * 100


def test_a_cents_file_read_as_dollars_overstates_cost_exactly_100x_and_flips_accounts_negative():
    ok, _, _ = _oracle()
    wrong, _, _ = _oracle("cost-anthropic-cents.csv")            # read as dollars
    scaled, _, _ = _oracle("cost-anthropic-cents.csv", scale=D("0.01"))  # the confirmed 0.01 scale
    assert scaled == ok                                           # totals equal the dollar fixture exactly
    for s in ok:
        assert wrong[s][1] == ok[s][1] * 100                      # exactly 100 times, every account
    negative = lambda r: sorted(s for s, v in r.items() if v[2] < 0)
    assert negative(ok) == ["sub_heavy_1", "sub_heavy_2"]
    assert len(negative(wrong)) > 20  # the misread turns nearly every scored account negative
    us = _read("cost.csv")
    assert D(sum(D(r["cost_amount"]) for r in us if r["cost_amount"] not in ("", "1,200", "$100"))) == \
        book_total_from_key(generate_cost_fixture(7, 20)[2])


def book_total_from_key(key):
    return key["unit_scale"]["parseable_amount_total_dollars"]


def test_unit_scale_block_in_the_key():
    us = generate_cost_fixture(7, 20)[2]["unit_scale"]
    assert us["scale"] == D("0.01") and us["factor"] == 100
    assert us["cents_file"] == "cost-anthropic-cents.csv"
    assert us["parseable_rows"] == 766 - 3 - 2
