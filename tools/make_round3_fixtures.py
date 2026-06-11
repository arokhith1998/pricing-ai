"""Round-3 ingestion fixtures — judgment traps.

Rounds 1-2 covered formats and silent corruption. Round 3 attacks cases where
the RIGHT answer requires a judgment call — and the pass condition is that the
pipeline either makes the defensible call or DISCLOSES the assumption in the
LoadReport. Hidden judgment = failure, even when the number happens to be right.

    PYTHONPATH=. python tools/make_round3_fixtures.py
    PYTHONPATH=. python tools/check_round3_fixtures.py

Fixtures:
  conflicting_dupes.csv   Same opportunity_id, DIFFERENT amounts (partial
                          re-export after deal edits). Exact-dupe dropping
                          doesn't apply — keeping either row silently is wrong.
                          Want: loud data-quality flag.
  ambiguous_dates.csv     Every date has day<=12 in DD/MM/YYYY. Mathematically
                          indistinguishable from MM/DD. Whatever is assumed,
                          the LoadReport must SAY so.
  mixed_currency.csv      90 rows in EUR (euro symbol + EU format), 210 in USD. A
                          money parser that strips symbols sums them into one
                          meaningless total with zero errors. Want: loud flag.
  uplift_deals.csv        15 won deals booked ABOVE list (expansion/uplift).
                          Legitimate. Must not be dropped, clamped to zero
                          discount, or "corrected".
  blank_booked_lost.csv   20 lost deals with empty Amount (no final quote
                          recorded — very common). Want graceful handling +
                          reporting, not NaN propagation or silent zeroes.
  big_injection.csv       30,000 rows + spreadsheet-formula cells in names
                          ("=HYPERLINK(...)", "+SUM(A1)"). Must stay text,
                          ingest in reasonable time, never evaluate.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("data/synthetic/format-base.csv")
OUT = Path("data/synthetic/round3-fixtures")


def _sf(df: pd.DataFrame) -> pd.DataFrame:
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


def make_conflicting_dupes(df: pd.DataFrame) -> None:
    d = _sf(df)
    dupes = d.iloc[10:22].copy()
    dupes["Amount"] = dupes["Amount"].map(
        lambda s: f"${float(s.strip('$').replace(',', '')) + 10000:,.2f}")
    pd.concat([d, dupes], ignore_index=True).to_csv(
        OUT / "conflicting_dupes.csv", index=False)


def make_ambiguous_dates(df: pd.DataFrame) -> None:
    d = _sf(df)

    def clamp(col: str) -> pd.Series:
        dt = pd.to_datetime(df[col])
        return dt.map(lambda t: t.replace(day=min(t.day, 12)))

    # intended format: DD/MM/YYYY, every day <= 12 -> fully ambiguous
    d["Created Date"] = clamp("created_date").dt.strftime("%d/%m/%Y")
    d["Close Date"] = clamp("close_date").dt.strftime("%d/%m/%Y")
    d.to_csv(OUT / "ambiguous_dates.csv", index=False)


def make_mixed_currency(df: pd.DataFrame) -> None:
    d = _sf(df)

    def eu(s: str) -> str:
        v = f"{float(s.strip('$').replace(',', '')):,.2f}"
        return "€" + v.replace(",", "\x00").replace(".", ",").replace("\x00", ".")

    d.loc[:89, "List Amount"] = d.loc[:89, "List Amount"].map(eu)
    d.loc[:89, "Amount"] = d.loc[:89, "Amount"].map(eu)
    d.to_csv(OUT / "mixed_currency.csv", index=False, encoding="utf-8")


def make_uplift(df: pd.DataFrame) -> None:
    d = _sf(df)
    won_idx = d.index[d["Stage"] == "Closed Won"][:15]
    lists = d.loc[won_idx, "List Amount"].map(
        lambda s: float(s.strip("$").replace(",", "")))
    d.loc[won_idx, "Amount"] = (lists * 1.15).map(lambda v: f"${v:,.2f}")
    d.to_csv(OUT / "uplift_deals.csv", index=False)


def make_blank_booked(df: pd.DataFrame) -> None:
    d = _sf(df)
    lost_idx = d.index[d["Stage"] == "Closed Lost"][:20]
    d.loc[lost_idx, "Amount"] = ""
    d.to_csv(OUT / "blank_booked_lost.csv", index=False)


def make_big_injection(df: pd.DataFrame) -> None:
    d = _sf(df)
    blocks = []
    for i in range(100):
        b = d.copy()
        b["Opportunity ID"] = b["Opportunity ID"].map(lambda s, i=i: f"{s}-{i}")
        blocks.append(b)
    big = pd.concat(blocks, ignore_index=True)
    big.loc[7, "Account Name"] = '=HYPERLINK("http://example.com","click")'
    big.loc[19, "Account Name"] = "+SUM(A1:A9)"
    big.loc[23, "Account Name"] = "@cmd|' /C calc'!A0"
    big.loc[31, "Account Name"] = "-2+3+acme"
    big.to_csv(OUT / "big_injection.csv", index=False)


def main() -> None:
    df = pd.read_csv(BASE, dtype=str, keep_default_na=False)
    OUT.mkdir(parents=True, exist_ok=True)
    make_conflicting_dupes(df)
    make_ambiguous_dates(df)
    make_mixed_currency(df)
    make_uplift(df)
    make_blank_booked(df)
    make_big_injection(df)
    print(f"Wrote 6 round-3 fixtures to {OUT}/")


if __name__ == "__main__":
    main()
