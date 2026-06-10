"""Round-2 ADVERSARIAL ingestion fixtures — silent-corruption traps.

Round 1 (make_format_fixtures.py) tested naming/formatting variety. This round
tests the failure modes that produce WRONG NUMBERS WITHOUT ERRORS, plus crash
cases. Same canonical 300 deals (data/synthetic/format-base.csv) underneath.

    PYTHONPATH=. python tools/make_adversarial_fixtures.py
    PYTHONPATH=. python tools/check_adversarial_fixtures.py

Fixtures and the trap each one sets:
  uk_dates.csv         DD/MM/YYYY with slashes. Rows with day<=12 are ambiguous;
                       wrong dayfirst silently swaps day/month -> quarter-end
                       analysis is corrupted with zero errors raised.
  open_pipeline.csv    40 OPEN deals (Negotiation/Proposal/Qualification) mixed
                       in, as real CRM exports often arrive. Must be excluded
                       loudly - mapping them to won/lost corrupts win rates.
  credits_zero.csv     Accounting negatives "(12,000.00)", $0.00 list_acv rows
                       (division by zero -> inf discount), one "N/A" money cell.
  dupe_opps.csv        12 rows duplicated exactly (re-export artifact). Naive
                       ingest double-counts $ totals silently.
  cp1252_names.csv     Windows-1252 encoded (Café, Müller, em-dash). UTF-8
                       decode either crashes or produces mojibake names that
                       break identity resolution.
  space_thousands.csv  French money: "96 000,00" with NBSP thousands separator.
  multisheet.xlsx      Sheet 1 is a summary pivot; real data on sheet 2.
  header_only.csv      Headers, zero rows. Want clean SchemaError-class message.
  garbage.csv          Not a deals file at all (random text columns). Must fail
                       loudly, never produce a number.
"""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

BASE = Path("data/synthetic/format-base.csv")
OUT = Path("data/synthetic/adversarial-fixtures")


def _sf_style(df: pd.DataFrame) -> pd.DataFrame:
    """Salesforce-flavored headers (known-good from round 1) so these tests
    isolate VALUE traps, not header mapping."""
    d = pd.DataFrame()
    d["Opportunity ID"] = df["opportunity_id"]
    d["Account ID"] = df["account_id"]
    d["Account Name"] = df["account_name"]
    d["Stage"] = df["outcome"].map({"closed_won": "Closed Won",
                                    "closed_lost": "Closed Lost"})
    d["Created Date"] = pd.to_datetime(df["created_date"]).dt.strftime("%m/%d/%Y")
    d["Close Date"] = pd.to_datetime(df["close_date"]).dt.strftime("%m/%d/%Y")
    d["Segment"] = df["segment"]
    d["Product Tier"] = df["product_tier"]
    d["Value Metric"] = df["value_metric"]
    d["List Amount"] = df["list_acv"].map(lambda x: f"${float(x):,.2f}")
    d["Amount"] = df["booked_acv"].map(lambda x: f"${float(x):,.2f}")
    return d


def make_uk_dates(df: pd.DataFrame) -> None:
    d = _sf_style(df)
    d["Created Date"] = pd.to_datetime(df["created_date"]).dt.strftime("%d/%m/%Y")
    d["Close Date"] = pd.to_datetime(df["close_date"]).dt.strftime("%d/%m/%Y")
    d.to_csv(OUT / "uk_dates.csv", index=False)


def make_open_pipeline(df: pd.DataFrame, rng: random.Random) -> None:
    d = _sf_style(df)
    stages = ["Negotiation", "Proposal Sent", "Qualification", "Discovery"]
    extra = d.sample(40, random_state=11).copy()
    extra["Opportunity ID"] = [f"OPP-9{i:04d}" for i in range(len(extra))]
    extra["Stage"] = [rng.choice(stages) for _ in range(len(extra))]
    extra["Close Date"] = ""          # open deals have no close date
    pd.concat([d, extra], ignore_index=True).sample(
        frac=1, random_state=3).to_csv(OUT / "open_pipeline.csv", index=False)


def make_credits_zero(df: pd.DataFrame) -> None:
    d = _sf_style(df)
    d.loc[5, "Amount"] = "(12,000.00)"          # accounting negative
    d.loc[17, "List Amount"] = "$0.00"          # div-by-zero discount
    d.loc[42, "List Amount"] = "$0.00"
    d.loc[88, "Amount"] = "N/A"                 # unparseable money
    d.to_csv(OUT / "credits_zero.csv", index=False)


def make_dupes(df: pd.DataFrame) -> None:
    d = _sf_style(df)
    dupes = d.iloc[10:22].copy()                # 12 exact duplicate rows
    pd.concat([d, dupes], ignore_index=True).to_csv(
        OUT / "dupe_opps.csv", index=False)


def make_cp1252(df: pd.DataFrame, rng: random.Random) -> None:
    d = _sf_style(df)
    fancy = ["Café Lumière SARL", "Müller & Söhne GmbH",
             "Ångström Analytics AB", "São Paulo Dados Ltda",
             "Beyoncé Tech — Holdings"]
    idx = d.sample(25, random_state=5).index
    d.loc[idx, "Account Name"] = [rng.choice(fancy) + f" {i}" for i in idx]
    (OUT / "cp1252_names.csv").write_bytes(
        d.to_csv(index=False).encode("cp1252", errors="replace"))


def make_space_thousands(df: pd.DataFrame) -> None:
    d = _sf_style(df)

    def fr(x: str) -> str:
        s = f"{float(x.strip('$').replace(',', '')):,.2f}"
        return s.replace(",", " ").replace(".", ",")  # NBSP + decimal comma

    d["List Amount"] = d["List Amount"].map(fr)
    d["Amount"] = d["Amount"].map(fr)
    d.to_csv(OUT / "space_thousands.csv", index=False, sep=";",
             encoding="utf-8")


def make_multisheet(df: pd.DataFrame) -> None:
    import openpyxl
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Summary"
    ws1.append(["Quarter", "Bookings"])
    ws1.append(["Q1", 1200000])
    ws1.append(["Q2", 1310000])
    ws2 = wb.create_sheet("Deals")
    d = _sf_style(df)
    ws2.append(list(d.columns))
    for row in d.itertuples(index=False):
        ws2.append(list(row))
    wb.save(OUT / "multisheet.xlsx")


def make_degenerate(df: pd.DataFrame) -> None:
    _sf_style(df).head(0).to_csv(OUT / "header_only.csv", index=False)
    pd.DataFrame({
        "lorem": ["ipsum", "dolor"], "sit": ["amet", "consectetur"],
        "adipiscing": ["elit", "sed"], "tempor": ["incididunt", "ut"],
    }).to_csv(OUT / "garbage.csv", index=False)


def main() -> None:
    rng = random.Random(13)
    df = pd.read_csv(BASE, dtype=str, keep_default_na=False)
    OUT.mkdir(parents=True, exist_ok=True)
    make_uk_dates(df)
    make_open_pipeline(df, rng)
    make_credits_zero(df)
    make_dupes(df)
    make_cp1252(df, rng)
    make_space_thousands(df)
    make_multisheet(df)
    make_degenerate(df)
    print(f"Wrote 9 adversarial fixtures to {OUT}/")


if __name__ == "__main__":
    main()
