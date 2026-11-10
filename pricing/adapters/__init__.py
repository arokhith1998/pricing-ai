"""Source-adapter registry, keyed by pricing.schema.SourceSystem value.

SalesforceAdapter and CsvAdapter are imported from where they live (unmoved,
unedited); HubSpot is the first adapter that lives in this package. A request
that names no source resolves to Salesforce, so every pre-existing caller is
unchanged. An unknown system raises UnknownSourceSystemError rather than
falling back, because guessing a source would stamp the wrong provenance on a
decision-log row.
"""
from __future__ import annotations

from pricing.adapters.hubspot import HubSpotAdapter
from pricing.crm import ADAPTER as _SALESFORCE
from pricing.csv_adapter import CsvAdapter
from pricing.guardrail import DealDataError, DealSourceAdapter
from pricing.schema import SourceSystem

DEFAULT_SOURCE = SourceSystem.SALESFORCE.value


class UnknownSourceSystemError(ValueError):
    """source_system names a system with no registered adapter."""


class ClosedFloorError(DealDataError):
    """Too few usable closed deals for an analysis. Carries `code` so callers
    branch on it, not on message text. Raised by the /crm route today because
    pricing/guardrail.py (not in this task's claim) raises a plain
    DealDataError; the guardrail should adopt this type in PK-91."""

    code = "closed_floor"


_CSV = CsvAdapter()
_HUBSPOT = HubSpotAdapter()

REGISTRY: dict[str, DealSourceAdapter] = {
    _SALESFORCE.system: _SALESFORCE,
    _CSV.system: _CSV,
    _HUBSPOT.system: _HUBSPOT,
}


def get_adapter(source_system: str | None = None) -> DealSourceAdapter:
    key = str(source_system or "").strip().lower() or DEFAULT_SOURCE
    try:
        return REGISTRY[key]
    except KeyError:
        raise UnknownSourceSystemError(
            "No adapter is registered for that source_system; "
            f"registered: {', '.join(sorted(REGISTRY))}."
        ) from None
