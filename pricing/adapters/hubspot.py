"""HubSpot adapter: the third implementation of pricing.guardrail.DealSourceAdapter.

Pure mapping of HubSpot CRM deal records to the canonical deal. No network,
no auth, no LLM; the web tier fetches and whitelists, this module maps and
does the money arithmetic (Decimal, so line sums are exact).

Input record, one per deal (the web tier assembles it from the CRM v3 deal
object, a batch read of its line items and a batch read of its company):

    {"id": "501", "properties": {"dealname", "amount", "dealstage", "pipeline",
                                  "closedate", "createdate", "hubspot_owner_id",
                                  "deal_currency_code", ...},
     "associations": {"companies": {"results": [{"id": "9001", "type": ...}]}},
     "line_items": [{"id": ..., "properties": {"price", "quantity", "amount"}}],
     "company": {"id": "9001", "properties": {"name", ...}}}

Outcome is never read from the deal. It comes only from the stage map a person
confirmed: a stage that is absent, unconfirmed, ambiguous or mapped to
anything but won, lost or open yields outcome "ask_user", which the engine
excludes and the readiness disclosure counts by stage. Lost is never
inferred: an open stage with a past close date stays open.

List price comes from line items (unit price times quantity, before line
discounts) or from a property the user mapped. A deal with neither has
list_acv None and list_source "none", so the engine's existing missing-value
exclusion and its "at least 30 usable closed deals" refusal apply. There is no
declared list book fallback (founder answer F6). No cost field is ever set.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from pricing.guardrail import SourceLabels
from pricing.schema import SourceSystem

ASK_USER = "ask_user"
_STAGE_OUTCOMES = {"won": "closed_won", "lost": "closed_lost", "open": "open"}
_VALUE_METRICS = {"seats", "consumption", "hybrid"}
# HubSpot app hosts by data center. Anything else is refused so the deep link
# can never point off HubSpot.
_APP_HOSTS = frozenset({"app.hubspot.com", "app-eu1.hubspot.com"})
_DEAL_OBJECT_TYPE_ID = "0-3"
_PRIMARY_COMPANY_TYPE_ID = 5
_DIGITS = re.compile(r"^[0-9]{1,20}$")


class HubSpotConfigError(ValueError):
    """The connection config (portal id, stage map, mapping) is unusable."""


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _money(value: Any) -> Decimal | None:
    """A HubSpot numeric string as an exact Decimal; None when absent,
    non-numeric, non-finite or negative."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not out.is_finite() or out < 0:
        return None
    return out


def _date(value: Any) -> str:
    """ISO date (YYYY-MM-DD) from an ISO timestamp or epoch milliseconds."""
    text = _text(value)
    if not text:
        return ""
    if text.isdigit() and len(text) >= 11:
        try:
            return datetime.fromtimestamp(int(text) / 1000, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return ""
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return ""


def _bool(value: Any) -> bool:
    return _text(value).lower() in {"true", "1", "yes", "y"}


def _whole(value: Any) -> int | None:
    dec = _money(value)
    return None if dec is None else int(dec)


def _parse_stage_map(raw: Any) -> tuple[dict, set]:
    """(entries by (pipeline_id, stage_id), keys that are ambiguous).

    An entry is (label, outcome, confirmed). A key listed twice with different
    outcomes or confirmations is ambiguous and resolves to ask_user.
    `confirmed` counts only when it is exactly True, so the string "true" or
    the number 1 never confirm a stage.
    """
    if raw in (None, ""):
        return {}, set()
    if not isinstance(raw, (list, tuple)):
        raise HubSpotConfigError("stage_map must be a list of stage entries.")
    entries: dict = {}
    ambiguous: set = set()
    for item in raw:
        if not isinstance(item, dict):
            raise HubSpotConfigError("Each stage_map entry must be an object.")
        pipeline_id = _text(item.get("pipeline_id"))
        stage_id = _text(item.get("stage_id"))
        if not pipeline_id or not stage_id:
            raise HubSpotConfigError("Each stage_map entry needs pipeline_id and stage_id.")
        entry = (_text(item.get("label")), _text(item.get("outcome")).lower(),
                 item.get("confirmed") is True)
        key = (pipeline_id, stage_id)
        prior = entries.get(key)
        if prior is not None and prior[1:] != entry[1:]:
            ambiguous.add(key)
        entries[key] = entry
    return entries, ambiguous


class HubSpotAdapter:
    """Maps a HubSpot deal record to the canonical deal. Pure: no network,
    the input is never mutated.

    The registry holds an unconfigured instance, which maps every deal to
    ask_user (no confirmed stage map). `configured(config)` returns a new
    instance bound to one tenant's portal, confirmed stage map and property
    mapping; `config` is a plain dict so it can ride a request body:

        portal_id           HubSpot portal (hub) id, digits, required
        stage_map           [{pipeline_id, stage_id, label, outcome, confirmed}]
        property_mapping    canonical field -> HubSpot property; a value
                            starting "company." reads the associated company.
                            Keys: booked_acv, list_acv, segment, industry,
                            product_tier, term_months, approved_by,
                            competitor_present, value_metric, rep_id, quantity
        pipeline_labels     {pipeline_id: label}, the product_tier fallback
        default_value_metric  seats | consumption | hybrid (default seats)
        use_home_currency   read amount_in_home_currency and state the
                            currency as home_currency; HubSpot's own rates
                            converted it. Not combinable with a booked_acv
                            mapping.
        home_currency       ISO code, required with use_home_currency
        default_currency    ISO code for portals without deal_currency_code
        app_host            app.hubspot.com (default) or app-eu1.hubspot.com
    """

    system = SourceSystem.HUBSPOT.value
    labels = SourceLabels(
        system="HubSpot",
        records="deals",
        record="deal",
        list_field_hint=(
            "Map a pre-discount HubSpot list property, or add line items "
            "with true list prices"
        ),
    )

    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        self._portal_id = _text(cfg.get("portal_id"))
        if self._portal_id and not _DIGITS.match(self._portal_id):
            raise HubSpotConfigError("portal_id must be digits.")
        self._host = _text(cfg.get("app_host")) or "app.hubspot.com"
        if self._host not in _APP_HOSTS:
            raise HubSpotConfigError("app_host is not a HubSpot app host.")
        self._stages, self._ambiguous = _parse_stage_map(cfg.get("stage_map"))
        mapping = cfg.get("property_mapping") or {}
        if not isinstance(mapping, dict):
            raise HubSpotConfigError("property_mapping must be an object.")
        self._mapping = {str(k): _text(v) for k, v in mapping.items() if _text(v)}
        labels = cfg.get("pipeline_labels")
        self._pipeline_labels = (
            {str(k): _text(v) for k, v in labels.items()}
            if isinstance(labels, dict) else {}
        )
        self._default_metric = _text(cfg.get("default_value_metric")).lower() or "seats"
        if self._default_metric not in _VALUE_METRICS:
            raise HubSpotConfigError(
                "default_value_metric must be seats, consumption or hybrid.")
        self._home = bool(cfg.get("use_home_currency"))
        self._home_currency = _text(cfg.get("home_currency")).upper()
        if self._home and not self._home_currency:
            raise HubSpotConfigError("use_home_currency requires home_currency.")
        if self._home and "booked_acv" in self._mapping:
            raise HubSpotConfigError(
                "use_home_currency cannot be combined with a booked_acv mapping.")
        self._default_currency = _text(cfg.get("default_currency")).upper()

    def configured(self, config: dict | None) -> "HubSpotAdapter":
        cfg = dict(config or {})
        if not _text(cfg.get("portal_id")):
            raise HubSpotConfigError("portal_id is required.")
        return HubSpotAdapter(cfg)

    # --- outcome ------------------------------------------------------------

    def resolve_outcome(self, pipeline_id: str, stage_id: str) -> tuple[str, str, str]:
        """(outcome, reason, stage_label). The outcome is closed_won,
        closed_lost, open or ask_user; the reason is empty unless ask_user."""
        if not pipeline_id or not stage_id:
            return ASK_USER, "stage_missing", ""
        key = (pipeline_id, stage_id)
        entry = self._stages.get(key)
        if entry is None:
            return ASK_USER, "stage_not_in_map", ""
        label, outcome, confirmed = entry
        if key in self._ambiguous:
            return ASK_USER, "stage_ambiguous", label
        if not confirmed:
            return ASK_USER, "stage_unconfirmed", label
        mapped = _STAGE_OUTCOMES.get(outcome)
        if mapped is None:
            return ASK_USER, "stage_outcome_invalid", label
        return mapped, "", label

    # --- mapping ------------------------------------------------------------

    def _prop(self, canonical: str, props: dict, company: dict, default: str = "") -> Any:
        name = self._mapping.get(canonical) or default
        if not name:
            return None
        if name.startswith("company."):
            return company.get(name[len("company."):])
        return props.get(name)

    @staticmethod
    def _company_id(record: dict) -> str:
        assoc = (record.get("associations") or {}).get("companies")
        found: list[tuple[bool, str]] = []
        if isinstance(assoc, dict):
            for item in assoc.get("results") or []:
                if isinstance(item, dict) and _text(item.get("id")):
                    found.append((False, _text(item["id"])))
        elif isinstance(assoc, list):
            # v4 shape: {"toObjectId": 9001, "associationTypes": [{"typeId": 5}]}
            for item in assoc:
                if not isinstance(item, dict) or not _text(item.get("toObjectId")):
                    continue
                types = item.get("associationTypes") or []
                primary = any(
                    isinstance(t, dict) and t.get("typeId") == _PRIMARY_COMPANY_TYPE_ID
                    for t in types
                )
                found.append((primary, _text(item["toObjectId"])))
        if not found:
            expanded = record.get("company")
            return _text(expanded.get("id")) if isinstance(expanded, dict) else ""
        primaries = [cid for is_primary, cid in found if is_primary]
        pool = primaries or [cid for _, cid in found]
        return sorted(pool, key=lambda c: (len(c), c))[0]

    @staticmethod
    def _line_totals(items: Any) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        """(list, net, quantity) over usable line items. List is unit price
        times quantity before any line discount; net is the sum of line
        `amount` and is None unless every usable line carries one."""
        if not isinstance(items, list) or not items:
            return None, None, None
        list_total = net_total = quantity = Decimal(0)
        net_complete = True
        used = 0
        for item in items:
            props = item.get("properties") if isinstance(item, dict) else None
            if not isinstance(props, dict):
                continue
            price, qty = _money(props.get("price")), _money(props.get("quantity"))
            if price is None or qty is None:
                continue
            used += 1
            list_total += price * qty
            quantity += qty
            net = _money(props.get("amount"))
            if net is None:
                net_complete = False
            else:
                net_total += net
        if not used or list_total <= 0:
            return None, None, None
        return list_total, (net_total if net_complete else None), quantity

    def to_canonical(self, record: dict) -> dict:
        props = record.get("properties") if isinstance(record.get("properties"), dict) else {}
        expanded = record.get("company") if isinstance(record.get("company"), dict) else {}
        company = expanded.get("properties") if isinstance(expanded.get("properties"), dict) else {}
        deal_id = _text(record.get("id"))
        pipeline_id = _text(props.get("pipeline"))
        stage_id = _text(props.get("dealstage"))
        outcome, reason, stage_label = self.resolve_outcome(pipeline_id, stage_id)

        # Currency and scale. Home-currency mode reads HubSpot's converted
        # amount and scales line-item figures by the same implied rate (home
        # amount over deal amount); when that rate is not derivable, list is
        # left unresolved rather than mixed across currencies.
        currency = _text(props.get("deal_currency_code")).upper() or self._default_currency
        factor: Decimal | None = Decimal(1)
        if self._home:
            currency = self._home_currency
            home, raw = _money(props.get("amount_in_home_currency")), _money(props.get("amount"))
            deal_amount = home
            factor = home / raw if home is not None and raw is not None and raw > 0 else None
        else:
            deal_amount = _money(self._prop("booked_acv", props, company, "amount"))

        list_total, net_total, line_qty = self._line_totals(record.get("line_items"))
        mapped_list = _money(self._prop("list_acv", props, company)) \
            if "list_acv" in self._mapping else None
        if mapped_list is not None and mapped_list > 0:
            # A mapped list property holds the amount in the deal's own
            # currency, so it takes the same scale as line items.
            list_value = mapped_list * factor if factor is not None else None
            list_source = "mapped_field" if list_value is not None else "none"
        elif list_total is not None and factor is not None:
            list_value, list_source = list_total * factor, "line_items"
        else:
            list_value, list_source = None, "none"

        booked, booked_source = deal_amount, "deal_property"
        if net_total is not None and factor is not None and "booked_acv" not in self._mapping:
            booked, booked_source = net_total * factor, "line_items"
        # Flag a deal whose typed amount disagrees with its line items by more
        # than one percent; the engine uses line items, the reader sees why.
        amount_mismatch = bool(
            booked_source == "line_items" and deal_amount is not None
            and deal_amount > 0 and abs(booked - deal_amount) / deal_amount > Decimal("0.01")
        )

        tier = (_text(self._prop("product_tier", props, company))
                or self._pipeline_labels.get(pipeline_id) or pipeline_id or "Unknown")
        metric = _text(self._prop("value_metric", props, company)).lower()
        mapped_qty = _money(self._prop("quantity", props, company)) \
            if "quantity" in self._mapping else None
        qty = mapped_qty if mapped_qty is not None else line_qty
        company_id = self._company_id(record)
        url = ""
        if self._portal_id and _DIGITS.match(deal_id):
            url = (f"https://{self._host}/contacts/{self._portal_id}"
                   f"/record/{_DEAL_OBJECT_TYPE_ID}/{deal_id}")

        return {
            "opportunity_id": deal_id,
            "account_id": company_id,
            "account_name": _text(company.get("name")) or _text(props.get("dealname")) or deal_id,
            "outcome": outcome,
            "outcome_reason": reason,
            "pipeline_id": pipeline_id,
            "stage_id": stage_id,
            "stage_label": stage_label,
            "created_date": _date(props.get("createdate")),
            "close_date": _date(props.get("closedate")),
            "segment": _text(self._prop("segment", props, company)) or "Unknown",
            "industry": _text(self._prop("industry", props, company)) or "Unknown",
            "product_tier": tier,
            "value_metric": metric if metric in _VALUE_METRICS else self._default_metric,
            "list_acv": float(list_value) if list_value is not None else None,
            "booked_acv": float(booked) if booked is not None else None,
            "list_source": list_source,
            "booked_source": booked_source,
            "amount_mismatch": amount_mismatch,
            "quantity": float(qty) if qty is not None else None,
            "term_months": _whole(self._prop("term_months", props, company)),
            "rep_id": _text(self._prop("rep_id", props, company, "hubspot_owner_id")),
            "approved_by": _text(self._prop("approved_by", props, company)),
            "competitor_present": _bool(self._prop("competitor_present", props, company)),
            "currency_iso": currency,
            "source_system": self.system,
            "source_record_id": deal_id,
            "source_account_id": company_id,
            "source_url": url,
        }

    # --- readiness ----------------------------------------------------------

    @staticmethod
    def readiness_extras(rows: list[dict]) -> dict:
        """Disclosure of the deals the engine could not place: counts by
        pipeline, stage and reason, plus how list prices were resolved. Counts
        only, no names or amounts."""
        asked: dict[tuple, int] = {}
        sources: dict[str, int] = {}
        for row in rows:
            src = str(row.get("list_source") or "none")
            sources[src] = sources.get(src, 0) + 1
            if row.get("outcome") == ASK_USER:
                key = (str(row.get("pipeline_id") or ""), str(row.get("stage_id") or ""),
                       str(row.get("stage_label") or ""), str(row.get("outcome_reason") or ""))
                asked[key] = asked.get(key, 0) + 1
        by_stage = [
            {"pipeline_id": p, "stage_id": s, "stage_label": label,
             "reason": reason, "deals": count}
            for (p, s, label, reason), count in sorted(asked.items())
        ]
        return {
            "ask_user": {"deals": sum(asked.values()), "by_stage": by_stage},
            "list_source_counts": dict(sorted(sources.items())),
        }
