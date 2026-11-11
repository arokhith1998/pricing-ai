// Single source for the audit's commercial terms, so the landing page, the
// /audit page and the pricing tier cannot drift apart. Source: the founder's
// one-page offer (gtm/ai-margin-audit-offer.md) and F4 in the 2026-11-10
// founder decisions. The fee is fixed and paid upfront. The 14-day clock
// starts at validated intake, not at signature.
export const AUDIT_PRICE = "$7,500";
export const AUDIT_DAYS = 14;
// F16: a delivery guarantee only, never an outcome guarantee. The follow-on
// subscription is offered after the readout and its price is not published.
export const AUDIT_DELIVERY_GUARANTEE = "If we do not deliver the 14-day readout, you pay nothing.";
export const AUDIT_FOLLOW_ON =
  "After the audit, an ongoing subscription is available; we price it with you once the readout shows the numbers.";
export const AUDIT_PRICE_LINE = `${AUDIT_PRICE} fixed, paid upfront`;
// The only label a margin figure may carry on this site (ADR-006, ADR-007).
export const COST_BASIS_LABEL = "contribution margin, customer-supplied cost basis";
