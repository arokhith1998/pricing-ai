"""Canonical deal schema — the single source of truth for the platform.

Everything speaks this schema: the synthetic generator, the ingestion/identity
layer, the metrics, and the GTM "data request" we hand a prospect. Keeping one
contract is the explicit de-risking move from the kickoff decisions
(vault/Decisions/2026-05-26-kickoff-decisions.md): when a real design partner
sends a CSV, onboarding is a column-mapping exercise, not a schema redesign.

A "deal" here is one closed B2B SaaS opportunity (won or lost) on a
usage-based / hybrid pricing model. ACV figures are annualized.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    WON = "closed_won"
    LOST = "closed_lost"


class Segment(str, Enum):
    SMB = "SMB"
    MID_MARKET = "MidMarket"
    ENTERPRISE = "Enterprise"


class ValueMetric(str, Enum):
    """How the customer is primarily charged (the 'value metric')."""

    SEATS = "seats"
    CONSUMPTION = "consumption"
    HYBRID = "hybrid"  # platform fee + consumption


@dataclass(frozen=True)
class Field:
    """One column in the deal schema.

    `required` marks the minimum set we need from a prospect to run the
    retrospective leakage diagnostic. Optional fields enrich the analysis
    (rep, approver, competitor) but the diagnostic degrades gracefully without
    them.
    """

    name: str
    dtype: str  # logical type: str | date | float | int | bool | enum
    required: bool
    description: str
    example: str


# Order here is the canonical column order for generated/exported CSVs.
FIELDS: list[Field] = [
    Field("opportunity_id", "str", True,
          "Unique opportunity identifier (one row per opportunity).", "OPP-00481"),
    Field("account_id", "str", False,
          "Stable account identifier if available. If absent we resolve identity "
          "from account_name during ingestion.", "ACC-0123"),
    Field("account_name", "str", True,
          "Customer account name as it appears in the CRM (may be messy / "
          "inconsistent across rows).", "Acme, Inc."),
    Field("outcome", "enum", True,
          "Deal outcome: closed_won or closed_lost.", "closed_won"),
    Field("created_date", "date", True,
          "Date the opportunity was created (used to derive cycle length).",
          "2025-08-04"),
    Field("close_date", "date", True,
          "Date the opportunity closed (won or lost). Drives quarter-end "
          "analysis.", "2025-09-30"),
    Field("segment", "enum", True,
          "Customer segment: SMB | MidMarket | Enterprise.", "MidMarket"),
    Field("region", "str", False, "Sales region.", "NA"),
    Field("industry", "str", False, "Customer industry / vertical.", "FinTech"),
    Field("business_unit", "str", False,
          "Top-level business group (e.g. Cloud, Data, Platform). Optional; "
          "enables BU-level slicing.", "Cloud"),
    Field("product_line", "str", False,
          "Product line within the business unit. Optional; enables "
          "line-level slicing.", "Compute"),
    Field("product_family", "str", False,
          "Family within the product line. Optional.", "Containers"),
    Field("product_tier", "str", True,
          "Plan / package the deal was sold on.", "Growth"),
    Field("sku", "str", False,
          "Leaf product / SKU / part number. Optional.", "CMP-K8S-PRO"),
    Field("value_metric", "enum", True,
          "Primary value metric: seats | consumption | hybrid.", "hybrid"),
    Field("list_acv", "float", True,
          "Annualized contract value at LIST price (pre-discount). The "
          "reference price for realization & leakage.", "120000.00"),
    Field("booked_acv", "float", True,
          "Annualized contract value actually booked (post-discount). For "
          "lost deals this is the quoted ACV at the time of loss.", "96000.00"),
    Field("platform_fee_acv", "float", False,
          "Portion of booked_acv that is fixed platform fee (hybrid deals).",
          "36000.00"),
    Field("usage_acv", "float", False,
          "Portion of booked_acv attributable to usage/consumption.",
          "60000.00"),
    Field("term_months", "int", False, "Contract term in months.", "12"),
    Field("quantity", "float", False,
          "Seats or usage units committed (interpretation depends on "
          "value_metric).", "150"),
    Field("rep_id", "str", False, "Sales rep identifier.", "REP-07"),
    Field("approved_by", "str", False,
          "Who approved the discount, if above policy (governance signal). "
          "Empty if no approval was recorded.", "MGR-02"),
    Field("competitor_present", "bool", False,
          "Whether a competitor was in the deal (discount-pressure signal).",
          "true"),
    Field("lost_reason", "str", False,
          "Reason captured on closed_lost deals (price | product | "
          "no_decision | competitor | timing).", "price"),
]

REQUIRED_FIELDS: list[str] = [f.name for f in FIELDS if f.required]
ALL_COLUMNS: list[str] = [f.name for f in FIELDS]

# Discount bands used for win-rate-by-band analysis. Half-open bins on
# discount_pct = 1 - booked_acv/list_acv, expressed as fractions [0,1].
DISCOUNT_BANDS: list[tuple[float, float, str]] = [
    (0.00, 0.05, "0-5%"),
    (0.05, 0.10, "5-10%"),
    (0.10, 0.15, "10-15%"),
    (0.15, 0.20, "15-20%"),
    (0.20, 0.25, "20-25%"),
    (0.25, 1.01, "25%+"),
]

# Default discount policy threshold: discount above this is "off-policy" and
# requires approval. Configurable per customer; 15% is a common deal-desk line.
DEFAULT_POLICY_THRESHOLD: float = 0.15


def band_for(discount_pct: float) -> str:
    """Return the discount-band label for a given discount fraction."""
    for lo, hi, label in DISCOUNT_BANDS:
        if lo <= discount_pct < hi:
            return label
    return DISCOUNT_BANDS[-1][2]
