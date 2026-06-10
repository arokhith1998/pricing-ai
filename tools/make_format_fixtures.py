"""Generate ingestion test fixtures in the export formats companies actually use.

Takes the canonical synthetic CSV and re-exports it the way different systems
name and format the same data. Each fixture is the SAME underlying 300 deals,
so a correct ingest should produce identical metrics from every file.

    PYTHONPATH=. python tools/make_format_fixtures.py \
        --base data/synthetic/format-base.csv \
        --out  data/synthetic/format-fixtures

Fixtures:
  salesforce_export.csv   Spaced Title Case headers, "Closed Won", MM/DD/YYYY,
                          "$1,234.56" money, TRUE/FALSE, CRLF
  hubspot_export.csv      HubSpot-ish headers (Record ID, Deal Stage),
                          "closedwon", ISO datetimes with time
  eu_export.csv           semicolon delimiter, DD.MM.YYYY, decimal commas
                          "1.234,56", Won/Lost
  warehouse_export.csv    UPPER_SNAKE abbreviated headers (OPP_ID, ACCT_NAME),
                          ISO timestamps, 1/0 booleans
  finance_export.xlsx     Excel: title + blank rows above header, currency
                          strings, totals row at the bottom
  messy_export.csv        UTF-8 BOM, padded/mixed-case headers, account_id
                          column missing, mutated account names, blank rows
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd


def _money_us(x) -> str:
    return "" if pd.isna(x) or x == "" else f"${float(x):,.2f}"


def _money_eu(x) -> str:
    if pd.isna(x) or x == "":
        return ""
    s = f"{float(x):,.2f}"            # 1,234,567.89
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _dt(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series)


def make_salesforce(df: pd.DataFrame, out: Path) -> None:
    d = pd.DataFrame()
    d["Opportunity ID"] = df["opportunity_id"]
    d["Account ID"] = df["account_id"]
    d["Account Name"] = df["account_name"]
    d["Stage"] = df["outcome"].map({"closed_won": "Closed Won",
                                    "closed_lost": "Closed Lost"})
    d["Created Date"] = _dt(df["created_date"]).dt.strftime("%m/%d/%Y")
    d["Close Date"] = _dt(df["close_date"]).dt.strftime("%m/%d/%Y")
    d["Segment"] = df["segment"]
    d["Region"] = df["region"]
    d["Industry"] = df["industry"]
    d["Business Unit"] = df["business_unit"]
    d["Product Line"] = df["product_line"]
    d["Product Family"] = df["product_family"]
    d["Product Tier"] = df["product_tier"]
    d["SKU"] = df["sku"]
    d["Value Metric"] = df["value_metric"]
    d["List Amount"] = df["list_acv"].map(_money_us)
    d["Amount"] = df["booked_acv"].map(_money_us)
    d["Platform Fee"] = df["platform_fee_acv"].map(_money_us)
    d["Usage Amount"] = df["usage_acv"].map(_money_us)
    d["Term (Months)"] = df["term_months"]
    d["Quantity"] = df["quantity"]
    d["Opportunity Owner"] = df["rep_id"]
    d["Approved By"] = df["approved_by"]
    d["Competitor Present"] = df["competitor_present"].astype(str).str.upper()
    d["Loss Reason"] = df["lost_reason"]
    d.to_csv(out / "salesforce_export.csv", index=False, lineterminator="\r\n")


def make_hubspot(df: pd.DataFrame, out: Path) -> None:
    d = pd.DataFrame()
    d["Record ID"] = df["opportunity_id"]
    d["Company ID"] = df["account_id"]
    d["Company name"] = df["account_name"]
    d["Deal Stage"] = df["outcome"].map({"closed_won": "closedwon",
                                         "closed_lost": "closedlost"})
    d["Create Date"] = _dt(df["created_date"]).dt.strftime("%Y-%m-%d %H:%M")
    d["Close Date"] = _dt(df["close_date"]).dt.strftime("%Y-%m-%d %H:%M")
    d["Customer Segment"] = df["segment"]
    d["Country/Region"] = df["region"]
    d["Industry"] = df["industry"]
    d["Business Unit"] = df["business_unit"]
    d["Product Line"] = df["product_line"]
    d["Product Family"] = df["product_family"]
    d["Plan"] = df["product_tier"]
    d["SKU"] = df["sku"]
    d["Pricing Model"] = df["value_metric"]
    d["List Price"] = df["list_acv"]
    d["Deal amount"] = df["booked_acv"]
    d["Platform fee"] = df["platform_fee_acv"]
    d["Usage revenue"] = df["usage_acv"]
    d["Contract term"] = df["term_months"]
    d["Units"] = df["quantity"]
    d["Deal owner"] = df["rep_id"]
    d["Approver"] = df["approved_by"]
    d["Competitive deal"] = df["competitor_present"].map(
        {"true": "Yes", "false": "No", True: "Yes", False: "No"})
    d["Closed lost reason"] = df["lost_reason"]
    d.to_csv(out / "hubspot_export.csv", index=False)


def make_eu(df: pd.DataFrame, out: Path) -> None:
    d = pd.DataFrame()
    d["Opportunity"] = df["opportunity_id"]
    d["Customer ID"] = df["account_id"]
    d["Customer"] = df["account_name"]
    d["Result"] = df["outcome"].map({"closed_won": "Won", "closed_lost": "Lost"})
    d["Created"] = _dt(df["created_date"]).dt.strftime("%d.%m.%Y")
    d["Closed"] = _dt(df["close_date"]).dt.strftime("%d.%m.%Y")
    d["Segment"] = df["segment"]
    d["Territory"] = df["region"]
    d["Sector"] = df["industry"]
    d["Division"] = df["business_unit"]
    d["Product Line"] = df["product_line"]
    d["Product Family"] = df["product_family"]
    d["Package"] = df["product_tier"]
    d["Article"] = df["sku"]
    d["Billing Model"] = df["value_metric"]
    d["List Value (EUR)"] = df["list_acv"].map(_money_eu)
    d["Contract Value (EUR)"] = df["booked_acv"].map(_money_eu)
    d["Base Fee (EUR)"] = df["platform_fee_acv"].map(_money_eu)
    d["Consumption (EUR)"] = df["usage_acv"].map(_money_eu)
    d["Term"] = df["term_months"]
    d["Quantity"] = df["quantity"]
    d["Sales Rep"] = df["rep_id"]
    d["Approved By"] = df["approved_by"]
    d["Competitor"] = df["competitor_present"].map(
        {"true": "ja", "false": "nein", True: "ja", False: "nein"})
    d["Loss Reason"] = df["lost_reason"]
    d.to_csv(out / "eu_export.csv", index=False, sep=";")


def make_warehouse(df: pd.DataFrame, out: Path) -> None:
    d = pd.DataFrame()
    d["OPP_ID"] = df["opportunity_id"]
    d["ACCT_ID"] = df["account_id"]
    d["ACCT_NAME"] = df["account_name"]
    d["DEAL_STATUS"] = df["outcome"].map({"closed_won": "WON",
                                          "closed_lost": "LOST"})
    d["CREATED_AT"] = _dt(df["created_date"]).dt.strftime("%Y-%m-%dT00:00:00Z")
    d["CLOSED_AT"] = _dt(df["close_date"]).dt.strftime("%Y-%m-%dT00:00:00Z")
    d["SEGMENT"] = df["segment"]
    d["REGION"] = df["region"]
    d["INDUSTRY"] = df["industry"]
    d["BU"] = df["business_unit"]
    d["PRODUCT_LINE"] = df["product_line"]
    d["PRODUCT_FAMILY"] = df["product_family"]
    d["TIER"] = df["product_tier"]
    d["SKU"] = df["sku"]
    d["VALUE_METRIC"] = df["value_metric"]
    d["LIST_ACV_USD"] = df["list_acv"]
    d["NET_ACV_USD"] = df["booked_acv"]
    d["PLATFORM_ACV_USD"] = df["platform_fee_acv"]
    d["USAGE_ACV_USD"] = df["usage_acv"]
    d["TERM_MONTHS"] = df["term_months"]
    d["QTY"] = df["quantity"]
    d["REP_ID"] = df["rep_id"]
    d["APPROVER_ID"] = df["approved_by"]
    d["IS_COMPETITIVE"] = df["competitor_present"].map(
        {"true": 1, "false": 0, True: 1, False: 0})
    d["LOST_REASON"] = df["lost_reason"]
    d.to_csv(out / "warehouse_export.csv", index=False)


def make_finance_xlsx(df: pd.DataFrame, out: Path) -> None:
    d = pd.DataFrame()
    d["Deal #"] = df["opportunity_id"]
    d["Customer"] = df["account_name"]
    d["Won/Lost"] = df["outcome"].map({"closed_won": "W", "closed_lost": "L"})
    d["Open Date"] = _dt(df["created_date"]).dt.strftime("%m/%d/%y")
    d["Close"] = _dt(df["close_date"]).dt.strftime("%m/%d/%y")
    d["Seg"] = df["segment"]
    d["Plan"] = df["product_tier"]
    d["Pricing"] = df["value_metric"]
    d["List Price (USD)"] = df["list_acv"].map(_money_us)
    d["Net Price (USD)"] = df["booked_acv"].map(_money_us)

    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Closed Deals"
    ws.append(["FY25 Closed Deals — CONFIDENTIAL — prepared by Finance"])
    ws.append([])
    ws.append(list(d.columns))
    for i, row in enumerate(d.itertuples(index=False)):
        if i in (40, 90):           # stray blank rows mid-table
            ws.append([])
        ws.append(list(row))
    ws.append([])
    total = pd.to_numeric(
        df["booked_acv"], errors="coerce").sum()
    ws.append(["TOTAL", "", "", "", "", "", "", "", "", _money_us(total)])
    wb.save(out / "finance_export.xlsx")


def make_messy(df: pd.DataFrame, out: Path, seed: int = 7) -> None:
    rng = random.Random(seed)

    def mutate_name(name: str) -> str:
        roll = rng.random()
        if roll < 0.25:
            return name.upper()
        if roll < 0.45:
            return name.replace(", Inc.", " inc").replace(" Co.", " co")
        if roll < 0.60:
            return f"  {name} "
        return name

    d = pd.DataFrame()
    d[" Opportunity Id "] = df["opportunity_id"]
    # account_id intentionally OMITTED — identity must resolve from names
    d["ACCOUNT name"] = df["account_name"].map(mutate_name)
    d["deal stage "] = df["outcome"].map({"closed_won": "Closed-Won",
                                          "closed_lost": "Closed-Lost"})
    d["created"] = df["created_date"]
    d["CloseDate"] = df["close_date"]
    d["segment"] = df["segment"]
    d["tier"] = df["product_tier"]
    d["pricing model"] = df["value_metric"]
    d["list acv"] = df["list_acv"].map(
        lambda x: f"{float(x):,.0f}" if x != "" else "")
    d["net acv"] = df["booked_acv"].map(
        lambda x: f"{float(x):,.0f}" if x != "" else "")
    # inject blank rows
    blanks = pd.DataFrame([{c: "" for c in d.columns}] * 3)
    d = pd.concat([d.iloc[:50], blanks, d.iloc[50:]], ignore_index=True)
    d.to_csv(out / "messy_export.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="data/synthetic/format-base.csv")
    ap.add_argument("--out", default="data/synthetic/format-fixtures")
    args = ap.parse_args()

    df = pd.read_csv(args.base, dtype=str, keep_default_na=False)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    make_salesforce(df, out)
    make_hubspot(df, out)
    make_eu(df, out)
    make_warehouse(df, out)
    make_finance_xlsx(df, out)
    make_messy(df, out)
    print(f"Wrote 6 fixtures to {out}/ from {len(df)} canonical deals.")


if __name__ == "__main__":
    main()
