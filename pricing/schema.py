"""Canonical deal schema, the single source of truth for the platform.

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


class SourceSystem(str, Enum):
    """Where a deal row came from (provenance, not a pricing input)."""

    CSV = "csv"
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    CPQ = "cpq"
    BILLING = "billing"  # vendor-unknown billing export (CSV)
    STRIPE = "stripe"  # vendor-level, read by the Stripe connector (PK-53)
    CHARGEBEE = "chargebee"  # vendor-level, read by the Chargebee connector
    MANUAL = "manual"


class CostBasis(str, Enum):
    """Trust level behind any cost figure on the deal (ADR-006).

    The label a reader sees is built in code from this enum. A crm_proxy value
    is never labeled margin.
    """

    CRM_PROXY = "crm_proxy"
    DECLARED_COST = "declared_cost"
    ERP_VERIFIED = "erp_verified"


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
          "Deal outcome: closed_won or closed_lost. A billing-sourced row "
          "(see BILLING_SOURCES) carries the marker billing_only instead, "
          "never closed_won or closed_lost, and never enters win rate.",
          "closed_won"),
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
    Field("currency", "str", False,
          "ISO 4217 code the money columns (list_acv, booked_acv, "
          "platform_fee_acv, usage_acv, committed_acv, overage_rate, "
          "list_unit_rate, credits_tcv, ramp_year_*_acv, cogs_acv) are denominated in. Blank/absent is "
          "read as USD. Ingestion (pricing/ingest.py) derives this per row "
          "from the currency symbol when the column itself is absent; a file "
          "that mixes currencies is blocked by default (or normalized to USD "
          "when fx_rates are supplied) rather than silently summed as one "
          "number. See pricing.ingest.CurrencyBlockedError.", "USD"),
    # --- Usage-based-pricing structure (all OPTIONAL) ---------------------
    # These let a deal express its UBP shape so guidance can eventually reason
    # about commit vs rate, not just discount %. The diagnostic degrades
    # gracefully without them; they are populated by the synthetic generator.
    Field("committed_acv", "float", False,
          "Committed annual spend / minimum commitment (usage-based & hybrid "
          "deals). The floor the customer commits to regardless of usage. "
          "Blank for pure seat deals.", "72000.00"),
    Field("overage_rate", "float", False,
          "Price per usage unit beyond the commitment (the overage / "
          "on-demand rate). Blank for pure seat deals.", "0.85"),
    Field("ramp_year_1_acv", "float", False,
          "Booked ACV scheduled for contract year 1 on a ramped multi-year "
          "deal (below steady state). Blank for single-year / non-ramped "
          "deals.", "60000.00"),
    Field("ramp_year_2_acv", "float", False,
          "Booked ACV scheduled for contract year 2 on a ramped multi-year "
          "deal. Blank if not ramped. STEADY-STATE CONVENTION: there is no "
          "ramp_year_3_acv field. Year 3 (and any later year) of a ramped "
          "deal is, by convention, booked_acv itself, the annualized "
          "steady-state figure the ramp climbs to. A 36-month ramped deal "
          "therefore expresses its full ramp as (ramp_year_1_acv, "
          "ramp_year_2_acv, booked_acv). Documented here rather than adding a "
          "third field: it is the smaller change, and term_months already "
          "tells you whether year 3 exists for a given deal.", "96000.00"),
    # --- Source, provenance and contract structure (all OPTIONAL) ---------
    # Provenance fields say where a row came from so a connector, a CSV and a
    # manual entry can be told apart. The contract-structure fields carry the
    # unit price behind the discount and off-invoice concessions. Absent
    # columns load as the defaults below (see PROVENANCE_DEFAULTS).
    Field("source_system", "enum", False,
          "System the row came from: csv | salesforce | hubspot | cpq | "
          "billing | stripe | chargebee | manual. Defaults to csv when "
          "absent. A billing-sourced row (billing | stripe | chargebee) "
          "never enters win rate: billing holds paying customers only.", "salesforce"),
    Field("source_record_id", "str", False,
          "Opportunity or record id in the source system.", "006Dn00000AbCdE"),
    Field("source_account_id", "str", False,
          "Account id in the source system (distinct from account_id, which "
          "is the customer's stable id).", "001Dn00000XyZ12"),
    Field("source_quote_id", "str", False,
          "Quote or CPQ document id in the source system.", "Q-004217"),
    Field("source_url", "str", False,
          "Deep link to the record in the source system.",
          "https://example.my.salesforce.com/006Dn00000AbCdE"),
    Field("value_metric_unit", "str", False,
          "Free text naming the unit behind value_metric (what one unit of "
          "quantity is), for example 'audio minute' or '1K tokens'.",
          "audio minute"),
    Field("cost_basis", "enum", False,
          "Trust level of any cost figure on the deal: crm_proxy | "
          "declared_cost | erp_verified. Defaults to crm_proxy (cost that "
          "arrived through a CRM or CSV, including cogs_acv). A crm_proxy "
          "value is never labeled margin.", "crm_proxy"),
    Field("list_unit_rate", "float", False,
          "List price per usage unit, in the same unit as quantity and "
          "overage_rate, in the deal currency. Money.", "1.10"),
    Field("credits_tcv", "float", False,
          "Total value over the whole term of service credits, free months "
          "and other off-invoice concessions, in the deal currency. Money.",
          "12000.00"),
    Field("is_renewal", "bool", False,
          "Whether this opportunity is a renewal of an existing contract "
          "(vs new business or expansion).", "false"),
    Field("renewal_uplift", "float", False,
          "Price uplift applied at renewal vs the prior term, as a fraction "
          "(0.07 = 7%). Blank for non-renewals.", "0.07"),
    # --- Cost (OPTIONAL), enables the Phase 3 margin layer ----------------
    Field("cogs_acv", "float", False,
          "Annualized cost of goods sold attributable to the deal (infra / "
          "delivery cost). Enables cost-proxy analysis; never labeled margin "
          "(ADR-006). The leakage diagnostic itself is price-based and does not "
          "require it.",
          "28000.00"),
]

REQUIRED_FIELDS: list[str] = [f.name for f in FIELDS if f.required]

# Optional provenance columns added by PK-23 (non-money). The two contract
# structure money fields are named separately so ingest can treat them as money.
PROVENANCE_FIELDS: list[str] = [
    "source_system", "source_record_id", "source_account_id",
    "source_quote_id", "source_url", "value_metric_unit", "cost_basis",
]
CONTRACT_MONEY_FIELDS: list[str] = ["list_unit_rate", "credits_tcv"]
# Defaults applied by ingest when the column is absent from a file.
PROVENANCE_DEFAULTS: dict[str, str] = {
    "source_system": SourceSystem.CSV.value,
    "cost_basis": CostBasis.CRM_PROXY.value,
}
# Enum-valued provenance columns and their allowed values.
PROVENANCE_ENUMS: dict[str, frozenset[str]] = {
    "source_system": frozenset(m.value for m in SourceSystem),
    "cost_basis": frozenset(m.value for m in CostBasis),
}
# --- Billing sources and the closed-lost gap (PK-53) -----------------------
# Billing systems hold paying customers only: there is no closed-lost row to
# find. A billing-sourced row must therefore never enter win rate or
# win-rate-by-band. Outcome stays a two-value enum (closed_won | closed_lost),
# so a billing-derived deal row carries this documented marker instead. Every
# consumer that builds closed history (ingest._exclude_open, the guardrail)
# already drops any outcome that is not closed_won or closed_lost, so the
# marker keeps the row out of win rate without a new code path. Billing rows
# never carry closed_lost.
BILLING_SOURCES: frozenset[str] = frozenset({
    SourceSystem.BILLING.value,
    SourceSystem.STRIPE.value,
    SourceSystem.CHARGEBEE.value,
})
BILLING_ONLY_OUTCOME: str = "billing_only"


def _plain(value: object) -> str:
    """An enum member or string as lowercase text; a missing value as "".

    Missing is None, float NaN, pandas NA and NaT. pandas is not imported
    here, so NA and NaT are recognised by type name.
    """
    value = getattr(value, "value", value)
    if value is None or type(value).__name__ in {"NAType", "NaTType"}:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return str(value).strip().lower()


def win_rate_eligible(source_system: object, outcome: object) -> bool:
    """True only for a closed_won or closed_lost row from a known non-billing source.

    Accepts plain strings or the SourceSystem and Outcome enum members. A
    missing source (None, NaN or blank) is NOT read as csv here: the csv
    default is applied by ingest, and a row whose origin is unknown is not
    let into win rate. The normalised source must be a SourceSystem value,
    so an unknown alias such as "stripe_billing" is ineligible. Billing
    sources are never eligible, whatever their outcome says.
    """
    source = _plain(source_system)
    if source not in PROVENANCE_ENUMS["source_system"] or source in BILLING_SOURCES:
        return False
    return _plain(outcome) in {m.value for m in Outcome}


# --- contract_period_actuals: the billing grain (PK-53) ---------------------
# One row per subscription (contract) per billed period, built from invoice
# lines, which are already period rollups (NDA Class 2: rollups only, no
# row-level usage events). It is a SEPARATE grain from the deal: it is not in
# FIELDS, ALL_COLUMNS or GENERATOR_COLUMNS, so deal files, ingest, the mapper
# and gtm/data-request.md are unchanged. In memory only; see the connector
# design doc, section 4 (docs/design/2026-11-09-native-connectors-hubspot-
# stripe-chargebee.md).
#
# Conventions: every money field on a row is in the one `currency` of that
# row; all money is tax excluded; amounts are per period, NOT annualised (the
# derivations annualise by interval); discount_amount and credit_amount are
# positive reductions. discount_amount is coupon and discount objects only;
# custom-price overrides and ramp phases leave it 0 (the gap is list_amount
# minus invoiced_amount), and free coupon months are credit_amount. So
# list_amount >= invoiced_amount + discount_amount + credit_amount. There is
# no outcome, no contact data and no end-customer identifier on the grain,
# and it carries no cost field: billing holds no product cost (ADR-006).
CONTRACT_PERIOD_FIELDS: list[Field] = [
    Field("source_system", "enum", False,
          "Billing source: stripe | chargebee | billing.", "stripe"),
    Field("source_record_id", "str", False,
          "Opaque subscription or contract id in the billing system, the same "
          "value the derived deal row carries as source_record_id. Joins the "
          "period to its deal; it is not a customer id.", "sub_1Nxyz"),
    Field("period_index", "int", False,
          "1-based ordinal of the billed period within the subscription.", "1"),
    Field("period_start", "date", False,
          "First day of the billed period.", "2025-01-01"),
    Field("period_end", "date", False,
          "Last day of the billed period (inclusive).", "2025-01-31"),
    Field("currency", "str", False,
          "ISO 4217 code every money field on this row is denominated in. "
          "One currency per row.", "USD"),
    Field("list_amount", "float", False,
          "Amount for the period at confirmed list price, before discounts "
          "and credits, tax excluded. Blank when list is not confirmed or "
          "not derivable (for example a tiered price). Money.", "10000.00"),
    Field("invoiced_amount", "float", False,
          "Amount invoiced for the period after discounts and credits, tax "
          "excluded. Money.", "9000.00"),
    Field("discount_amount", "float", False,
          "Coupon and discount objects only (a percentage or amount off) "
          "applied in the period, as a positive number. A custom-price "
          "override or a ramp phase is not a discount: the gap shows as "
          "list_amount minus invoiced_amount. Free months from a "
          "100-percent-off coupon are credits (credit_amount), not "
          "discount_amount. Money.", "1000.00"),
    Field("credit_amount", "float", False,
          "Credit notes, promotional credits and free periods from a "
          "100-percent-off coupon applied in the period, as a positive "
          "number. Money.", "0.00"),
    Field("usage_units", "float", False,
          "Metered units billed in the period (an invoice-line rollup, never "
          "event rows). Blank for licensed-only subscriptions.", "22000"),
    Field("usage_amount", "float", False,
          "Portion of invoiced_amount that is metered usage. Money.",
          "11000.00"),
    Field("committed_amount", "float", False,
          "Committed spend for the period when the source supplies it "
          "(a metadata key or commit product the user marked). Blank "
          "otherwise. Money.", "1500.00"),
]
CONTRACT_PERIOD_COLUMNS: list[str] = [f.name for f in CONTRACT_PERIOD_FIELDS]
CONTRACT_PERIOD_MONEY_FIELDS: list[str] = [
    "list_amount", "invoiced_amount", "discount_amount", "credit_amount",
    "usage_amount", "committed_amount",
]
# The minimum a row needs to be usable. Every field is optional in the schema
# sense (nothing here is in REQUIRED_FIELDS); a row missing a key field is
# skipped by consumers rather than guessed.
CONTRACT_PERIOD_KEY_FIELDS: list[str] = [
    "source_record_id", "period_start", "period_end", "currency",
    "invoiced_amount",
]

# --- cost_period_actuals: the customer cost grain (PK-99) -------------------
# One row per cost line per day or date range, from a founder-supplied cost
# export (model-provider, hosting or storage cost rolled up per customer key).
# It is a THIRD grain, separate from the deal and from contract_period_actuals:
# it is not in FIELDS, ALL_COLUMNS, GENERATOR_COLUMNS or
# CONTRACT_PERIOD_FIELDS, so deal files, ingest, the mapper's deal fields,
# data/synthetic/deals.csv and gtm/data-request.md are unchanged. In memory
# only. Spec: docs/design/2026-11-10-margin-health-analysis.md sections 2.2 to
# 2.6. Binding decisions: ADR-006 (the basis enum, label text owned by code),
# ADR-007 (declared_cost only by an explicit upload declaration, never
# erp_verified on an upload; joined only through a customer-declared key map),
# founder F1 (contribution margin only) and F12 (no allocation rule by default;
# unattributable cost marks the readout upper_bound).
#
# Conventions: cost_end is INCLUSIVE, like period_end on the billing grain; a
# daily row has cost_start equal to cost_end. cost_amount is in cost_currency,
# at source precision, never converted. A cost_amount that is absent is NOT a
# zero cost: a blank, a missing column and a missing period are each "not in
# the file", counted by the consumer, never read as 0. The grain carries no
# end-customer name, email or contact field: customer_key is an opaque
# attribution key (api key, project, workspace, tag or subscription id) and it
# reaches a billing account only through a customer-declared key map.
class CostCategory(str, Enum):
    """What the cost line is for. Blank is 'uncategorized', never guessed."""

    INFERENCE = "inference"
    COMPUTE = "compute"
    STORAGE = "storage"
    OTHER = "other"


class CostKeyType(str, Enum):
    """What kind of identifier customer_key holds."""

    SOURCE_RECORD_ID = "source_record_id"
    API_KEY_ID = "api_key_id"
    PROJECT_ID = "project_id"
    WORKSPACE_ID = "workspace_id"
    CUSTOMER_TAG = "customer_tag"


class CostAttribution(str, Enum):
    """How a cost line reached an account (spec 2.3). Set by the loader from
    the key map and the confirmed allocation rules; never read from a file.

    direct: the key is a billing source_record_id, or is in the confirmed key
    map. allocated: the line belongs to a pool the user confirmed a rule for.
    not_attributable: everything else; never dropped, never spread.
    """

    DIRECT = "direct"
    ALLOCATED = "allocated"
    NOT_ATTRIBUTABLE = "not_attributable"


COST_PERIOD_FIELDS: list[Field] = [
    Field("cost_vendor", "str", False,
          "Who billed the line: openai, anthropic, aws, free text. Display and "
          "de-duplication only.", "anthropic"),
    Field("cost_category", "enum", False,
          "inference | compute | storage | other. Set from a user-confirmed "
          "table; blank is uncategorized, never guessed.", "inference"),
    Field("cost_line", "str", False,
          "The dimension that makes a row unique within a day: model, "
          "line_item, description or product code.", "claude-large"),
    Field("customer_key", "str", False,
          "Opaque attribution key as exported (api key, project, workspace, "
          "tag, or a subscription id). Not a customer name or email. Blank "
          "means shared cost.", "ws_acme_01"),
    Field("customer_key_type", "enum", False,
          "source_record_id | api_key_id | project_id | workspace_id | "
          "customer_tag.", "workspace_id"),
    Field("cost_start", "date", False,
          "First day the line covers.", "2026-01-01"),
    Field("cost_end", "date", False,
          "Last day the line covers (inclusive). Equal to cost_start for a "
          "daily row.", "2026-01-31"),
    Field("cost_currency", "str", False,
          "ISO 4217 code, upper-cased on read. One currency per row; never "
          "converted.", "USD"),
    Field("cost_amount", "str", False,
          "Cost for the range in cost_currency, at source precision (fractions "
          "of a cent kept). Held as text so a blank or an unparseable cell "
          "stays visible and is never read as 0. Money. Units are the file's: "
          "an Anthropic cost report is in cents.", "8000.00"),
    Field("cost_basis", "enum", False,
          "Exact-only. Absent, or declared_cost, in an upload. erp_verified "
          "in an uploaded file is a 422; any other value makes the row "
          "crm_proxy. The basis is set by code from the upload declaration, "
          "not by this cell.", ""),
    Field("attribution", "enum", False,
          "direct | allocated | not_attributable. DERIVED by the loader, "
          "never read from a file: an uploaded value is ignored.", ""),
]
COST_PERIOD_COLUMNS: list[str] = [f.name for f in COST_PERIOD_FIELDS]
COST_PERIOD_MONEY_FIELDS: list[str] = ["cost_amount"]
# Fields set by the loader. A file never supplies them, so the synthetic cost
# export has COST_PERIOD_FILE_COLUMNS only.
COST_PERIOD_DERIVED_FIELDS: list[str] = ["attribution"]
COST_PERIOD_FILE_COLUMNS: list[str] = [
    n for n in COST_PERIOD_COLUMNS if n not in COST_PERIOD_DERIVED_FIELDS]
# The minimum a row needs to be usable; a row missing one is counted and
# excluded by the consumer, never guessed.
COST_PERIOD_KEY_FIELDS: list[str] = [
    "cost_start", "cost_end", "cost_currency", "cost_amount",
]
# Mapping profile name for a cost export (spec 2.5). The fingerprint itself is
# header-only and lives with the mapper; these are the exact-only fields it
# must never fuzzy-match: bare words collide with real columns ("Customer",
# "Account" and "Project" are different things, and mapping a provider project
# to a customer is an attribution decision a person confirms; a bare "Amount"
# is on every CRM opportunity export).
COST_EXPORT_PROFILE = "cost_export"
COST_EXACT_ONLY_FIELDS: frozenset[str] = frozenset({
    "customer_key", "customer_key_type", "cost_amount", "cost_category",
    "cost_basis", "source_record_id",
})
# The customer-declared key map: cost key to billing account. The only join
# between the cost grain and the billing grain (ADR-007). One key mapping to
# two accounts is rejected by the loader (that is an allocation, not an
# attribution). Several keys may map to one account.
COST_KEY_MAP_COLUMNS: list[str] = [
    "customer_key_type", "customer_key", "source_record_id",
]
# A cost_basis cell may hold only this in an upload (ADR-007).
COST_UPLOAD_BASIS_ALLOWED: frozenset[str] = frozenset({CostBasis.DECLARED_COST.value})

# Every canonical field name.
ALL_FIELD_NAMES: list[str] = [f.name for f in FIELDS]
# Columns the synthetic generator emits. Explicit pre-PK-23 list: the new
# optional columns are not generated, so data/synthetic output stays stable.
GENERATOR_COLUMNS: list[str] = [
    n for n in ALL_FIELD_NAMES
    if n not in PROVENANCE_FIELDS and n not in CONTRACT_MONEY_FIELDS
]
ALL_COLUMNS: list[str] = ALL_FIELD_NAMES  # alias: every field

# Discount bands used for win-rate-by-band analysis. Half-open bins on
# discount_pct = 1 - booked_acv/list_acv. The first band is NEGATIVE: deals
# booked above list (expansion / CPI indexation / scarcity pricing) are a
# pricing-power signal, the opposite of leakage. It is kept as its own band so
# band_for never mislabels it into "0-5%", and metrics excludes it from the
# reference-discount search (it is not a discount policy level).
DISCOUNT_BANDS: list[tuple[float, float, str]] = [
    (-1.01, 0.00, "above list"),
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
