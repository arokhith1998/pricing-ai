---
title: Bertini & Koenigsberg — The Ends Game
created: 2026-05-26
updated: 2026-05-26
tags: [framework, pricing, outcome-based, monetization, value-metric]
status: active
source: Marco Bertini & Oded Koenigsberg — The Ends Game (2020)
---

# Bertini & Koenigsberg — The Ends Game

**TL;DR:** Stop selling products (the *means*) and start charging for the
outcomes customers actually want (the *ends*). The more your revenue model is
tied to the value delivered, the more incentives align — but the more risk you
take on, so design the metric and the guardrails deliberately.

## Core principles
- **Means vs ends.** Traditional pricing charges for access to a product;
  ends-based pricing charges for the result it produces. The closer billing
  sits to the customer's outcome, the stronger the trust and the alignment.
- **A spectrum of models**, increasing in outcome-alignment and seller risk:
  pay-per-use → subscription/access → pay-for-performance/outcome-based. Each
  shifts who carries the risk of unrealized value.
- **The friction the model removes is the point.** Ends-based models exist to
  kill the "I paid but didn't get value" gap that erodes retention.
- **Outcome pricing demands measurement and control.** You can only charge for
  an end you can measure, attribute, and partly influence — otherwise you carry
  uncontrollable risk.

## How it informs our product
- **Frames the value-metric question** at the heart of usage-based/hybrid
  pricing: is the metric a proxy for the customer's *end* (outcomes) or just a
  *means* (seats, API calls)? A weak proxy is a future leakage and churn source.
- **Elasticity & scenario modeling (pillar #3)** should let a customer simulate
  moving along the means→ends spectrum (e.g. usage vs outcome component) and
  see the NRR / risk tradeoff.
- **Retention lens on leakage:** discounts that paper over a means-vs-ends
  mismatch are leakage with a churn tail, not just margin given away.
- Supports **customer-level insights (pillar #4):** flag accounts where what
  they pay for diverges from the value they realize.

## Watch-outs / where it's weak
- Outcome-based pricing is operationally heavy (attribution disputes, gaming,
  measurement cost) — for our first design partner, prefer a clean hybrid
  metric over true outcome pricing (see [[ideal-first-design-partner]]).
- "Align to outcomes" is easy to say and hard to instrument; without solid data
  it becomes a slogan.

## Related
[[pricing-frameworks-index]] · [[campbell-willingness-to-pay]] · [[poyar-usage-based-pricing]] · [[ramanujam-monetizing-innovation]] · [[ideal-first-design-partner]]
