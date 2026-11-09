"""CSV adapter: the second implementation of pricing.guardrail.DealSourceAdapter."""
from __future__ import annotations

from pricing.guardrail import SourceLabels
from pricing.schema import SourceSystem


class CsvAdapter:
    """Pass-through for rows that already arrive in canonical shape (a file
    or a pasted frame). Stamps source_system=csv when the row does not say."""

    system = SourceSystem.CSV.value
    labels = SourceLabels(system="CSV", records="deals", record="deal")

    def to_canonical(self, record: dict) -> dict:
        row = dict(record)
        if not str(row.get("source_system") or "").strip():
            row["source_system"] = self.system
        return row
