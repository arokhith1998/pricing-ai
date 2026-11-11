---
title: The plan from the Solo AI Builder Guide video
created: 2026-11-11
updated: 2026-11-11
tags: [plan, strategy, gtm, adr-008]
status: active
source: Solo_AI_Builder_Guide.mp4 (founder-supplied, 7 min 50 s, made with Gemini Notebook from the founder's research sheet); transcribed locally on 2026-11-11
---

# The plan from the Solo AI Builder Guide video

The founder supplied this video on 2026-11-11 as "what should be our plan, detailed". It narrates the two filled tabs of the research sheet (`2026-11-10-founder-sheet-consumer-trends-and-opportunity.md`) and is addressed to Pricekeel by name. It extends ADR-008 in `docs/agents/DECISIONS.md`; every agent reads both.

## The thesis

A solo founder with deep pricing knowledge can build a B2B AI company without a large engineering team. The edge is domain expertise, not code. Pricekeel is "a machine that runs a machine": find one specific B2B bottleneck, sell the fix by hand first, use AI heavily, and scale with AI agents instead of headcount.

## The six chapters

1. **The solo AI founder.** The old way: code first, hire big teams, scale headcount. The new way: find a specific B2B bottleneck, sell manually, use AI as leverage, scale with agents.
2. **Price before product.** Madhavan Ramanujam's rule: you cannot prioritise a roadmap without a willingness-to-pay conversation. If prospects do not agree to the price and the value up front, the software will not matter. The one-page offer is the demand test: problem, promise, timeline, price, guarantee.
3. **Validate without code.** Five steps: draft the one-page offer; pitch it to 10 target prospects; solve the problem by hand in spreadsheets; only after proving value, build a clickable prototype from their feedback; launch an MVP with only the core features. "In an AI native services company, automating the manual process is the product." Five customer calls teach more than five weeks of coding.
4. **The AI pricing dilemma.** Traditional software has high gross margins; AI companies do not, because inference, compute and storage cost scale with use. Horizontal products priced on inputs (tokens) to a broad market carry high margin risk. Vertical products priced on outcomes for a specific niche carry low margin risk. Four revenue models: pure subscription (risk: power users drain cost), usage-based API (tokens), hybrid (flat fee plus usage credits), outcome-based (charge on the value delivered). Navigating these is Pricekeel's core value.
5. **Charge for the outcome.** Customers do not want another dashboard; they want their pricing fixed and their margin up. Sell the outcome, not the tool or the tokens; that is where enterprise willingness to pay sits.
6. **Scale with AI agents.** Phase 1, revenue up to about $100K: do everything by hand, AI as thought partner. Phase 2, $100K to $1M: automate workflows and operations. Phase 3, $1M to $10M: stack AI agents as subcontractors for onboarding, data analysis and support; the founder works on strategy.

Closing line: "your pricing strategy is your ultimate product feature." Final question: build another software tool, or an outcome engine?

## How this maps to what is already running

| Video step | Where it stands, 2026-11-11 |
|---|---|
| Draft the one-page offer | Done: `gtm/ai-margin-audit-offer.md`, the `/audit` page in PR 99 |
| Pitch to 10 target prospects | Running: 50 LinkedIn invitations with notes sent over two days; first DMs go to acceptances |
| Solve manually in spreadsheets | Ready: `gtm/ai-margin-audit-runbook.md`, the 14-day hand-delivered audit; blocked on counsel, entity and insurance before customer cost files (F11) |
| Clickable prototype | In build: calculator formula module (PR 98), page next (PK-110) |
| MVP, core features only | Designed: margin-health engine, first piece in PR 96; nothing beyond core |
| Phase 1, manual plus AI | This is where we are |

## Three points where the video differs from decisions already taken

These are not applied. The site and the offer stay as decided until the founder rules on each.

1. **The offer's price and term.** The video's example offer is "optimise your pricing strategy and increase margins in 30 days for $2,500 a month or your money back." The current decision (F4, F6) is a 14-day audit at $7,500 fixed, paid up front, with no subscription price published. The CFO priced a hand-run audit's break-even near $7,500 at the founder's time, and the strategist found $2,500 a month fails a seed founder's reference price but works for Series B and later. **Lead recommendation:** keep $7,500 fixed for the audit, and use "$2,500 a month" only as the follow-on subscription offered after an audit has shown the numbers, never as the opening price.
2. **The money-back guarantee.** The video's offer includes one; every reviewer advised against guarantees on a historical audit, because the result depends on data the customer supplies and on decisions the customer makes. **Lead recommendation:** no outcome guarantee; a delivery guarantee instead ("if we do not deliver the 14-day readout, you pay nothing"), which is honest and fully within our control.
3. **"Increase margins" and "autonomous outcome engine".** The video promises increased margins and ends on an autonomous outcome engine. The cost-basis rule (ADR-006, F1) allows the word margin only as "contribution margin, customer-supplied cost basis", and F10 rejected "autonomous" because the product keeps a human in the loop. **Lead recommendation:** keep the wording rules; describe the outcome as "find which customers cost more to serve than they pay, and the packaging that fixes it", and call the product an outcome engine without "autonomous".

## What agents do with this

Every task, review and line of copy is checked against this file and ADR-008. Work that does not serve the current step (pitch, then solve by hand) is deferred. The test for any build: does it make the manual audit faster or let a prospect see the outcome? If neither, it waits.
