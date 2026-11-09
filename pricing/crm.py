"""Salesforce adapter and CRM-shaped entry points over the neutral guardrail.

Salesforce authentication and SOQL stay in the Next.js server tier. This
module receives a bounded list of canonical records, maps each one to the
canonical deal (SalesforceAdapter), and hands the result to pricing.guardrail,
which holds the deterministic engine. It never calls an LLM and never persists
input rows.

The public functions here (analyze_records, selected_guidance,
guidance_for_open_deal, CRMDataError, MAX_CRM_RECORDS) keep their original
signatures and output shapes so every existing call site works unchanged: they
are thin wrappers that run the adapter, call the guardrail, and rename the
neutral keys (deal_id, source_url) back to the Salesforce ones the web tier
already reads (opportunity_id, salesforce_url).
"""
from __future__ import annotations

from pandas import DataFrame

from pricing import guardrail, metrics  # noqa: F401  (metrics: patched by tests)
from pricing.guardrail import (  # noqa: F401  (re-exported for existing callers)
    DealDataError,
    SourceLabels,
    _reference_for_segment,
)
from pricing.schema import DEFAULT_POLICY_THRESHOLD, SourceSystem

MAX_CRM_RECORDS = guardrail.MAX_RECORDS

# Same class as the engine's error, so `except crm.CRMDataError` still catches
# everything the guardrail raises.
CRMDataError = DealDataError


class SalesforceAdapter:
    """Maps a canonical Salesforce row (as the web tier emits it) to the
    canonical deal. Pure: no network, input is not mutated.

    Adds the provenance fields (source_system, source_record_id,
    source_account_id, source_url) and leaves every pricing field as sent.
    """

    system = SourceSystem.SALESFORCE.value
    labels = SourceLabels(
        system="Salesforce",
        records="opportunities",
        record="opportunity",
        list_field_hint=(
            "Map a pre-discount Salesforce list field, or add Opportunity "
            "Products with true list prices"
        ),
    )

    def to_canonical(self, record: dict) -> dict:
        row = dict(record)
        row["source_system"] = self.system
        row["source_record_id"] = str(row.get("opportunity_id") or "")
        row["source_account_id"] = str(row.get("account_id") or "")
        row["source_url"] = str(row.get("salesforce_url") or "")
        return row


ADAPTER = SalesforceAdapter()


def _canonical(records: list[dict]) -> list[dict]:
    return guardrail.canonical_records(ADAPTER, records)


def _legacy_shape(row: dict) -> dict:
    """Neutral guardrail keys back to the names the web tier reads."""
    out = dict(row)
    out["opportunity_id"] = out.pop("deal_id")
    out["salesforce_url"] = out.pop("source_url")
    out["comparables"] = [
        {("opportunity_id" if key == "deal_id" else key): value
         for key, value in comp.items()}
        for comp in out.get("comparables", [])
    ]
    return out


def guidance_for_open_deal(df: DataFrame, deal: dict,
                           policy_threshold: float = DEFAULT_POLICY_THRESHOLD,
                           *, global_ref: dict | None = None,
                           segment_table: list[dict] | None = None) -> dict:
    """Deterministic guardrail for one open Salesforce deal; see
    pricing.guardrail.guidance_for_open_deal."""
    row = guardrail.guidance_for_open_deal(
        df, ADAPTER.to_canonical(deal), policy_threshold,
        global_ref=global_ref, segment_table=segment_table,
        labels=ADAPTER.labels,
    )
    return _legacy_shape(row)


def analyze_records(records: list[dict], policy_threshold_pct: float = 15.0,
                    *, list_field_mapped: bool = False) -> dict:
    result = guardrail.analyze_deals(
        _canonical(records), policy_threshold_pct,
        list_field_mapped=list_field_mapped, labels=ADAPTER.labels,
        max_records=MAX_CRM_RECORDS,
    )
    result["guidance"] = [_legacy_shape(row) for row in result["guidance"]]
    return result


def selected_guidance(records: list[dict], deal_id: str,
                      policy_threshold_pct: float = 15.0,
                      *, list_field_mapped: bool = False) -> dict:
    row = guardrail.selected_deal_guidance(
        _canonical(records), deal_id, policy_threshold_pct,
        list_field_mapped=list_field_mapped, labels=ADAPTER.labels,
        max_records=MAX_CRM_RECORDS,
    )
    return _legacy_shape(row)
