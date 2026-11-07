Summary: Build a standalone "Quote check" screen with a unified decision log (about 8 web days) as the first non-CRM surface, defer Slack, email and any overlay behind it, and keep the site at "Salesforce plus CSV" until an adapter actually ships.

# Web engineer review: delivery surfaces and claim honesty

## 1. Findings

- The web app is Salesforce-shaped end to end. `web/src/app/crm/page.tsx` renders `SalesforceWorkspace.tsx` (592 lines: OAuth, mapping, workflow log). `web/src/lib/salesforce-workspace.ts` holds the only server-side orchestration (`/crm/reconcile`, `/crm/analyze`) and is `server-only`. The pattern is right and reusable: a route handler gates with `requireAccess()`, attaches `X-Pricekeel-Key` and `X-Pricekeel-Customer`, and calls FastAPI.
- Reusable UI exists. `GuidanceClient.tsx` (542 lines) renders a `Recommendation` (`web/src/lib/api.ts:338`: recommended discount, win probability, expected value, comparables, confidence, method, curve). `DecisionControl.tsx` records approve or exception and renders the verdict with a receipt id. `DecisionLog.tsx` lists entries and refetches on `pk:decision-logged`.
- Three couplings block a standalone screen. (a) `/api/recommend` and `/api/exceptions` look up a `deal_id` in the sample dataset and are gated by `requireLead()` (demo cookie), not tenant-scoped (`web/src/app/api/exceptions/route.ts`). (b) `Deal` (`api.ts:287`) is the sample schema; an ad hoc quote has no opportunity id. (c) Two decision logs already exist: `/api/exceptions` (demo) and `/api/salesforce/workflow` (per customer; events flagged, accepted, override_requested, approved, rejected). A new surface must not create a third.
- Claims today are accurate. `web/src/app/page.tsx:50` ("Salesforce deal guidance for B2B SaaS") and `:76` ("Salesforce orgs with 500+ closed opportunities"). `web/src/app/pricing/page.tsx:354-358` says CSV or Excel for other CRMs and that billing and telemetry connectors are not in V1; `:54-59` bars a CRM proxy presented as margin. `TrustBoundaryStrip.tsx` says commit, ramp and overage are captured, not scored.
- `docs/design/nextjs-ui.md` (plain language, label map, no snake_case, money first) and `docs/design/landing-flow-redesign.md` (one idea per viewport, one CTA phrase, no fake proof) apply to every new surface.

## 2. What would have to change

### Standalone quote screen (`/quote`), 8 web days
Flow: rep or deal desk enters a quote, confirms parsed fields, gets guidance, records the decision.
- Input, 2d. Typed form plus a one-row CSV/XLSX upload through the existing four-layer mapper (`/api/map-headers`, `docs/design/richer-ingest.md`). No PDF or free-text parsing in version one: an LLM extraction feeding a number is only acceptable if the user confirms every extracted field. A confirm table with readable labels (Appendix A of the UI doc) is mandatory.
- Guidance, 2d web plus an engine dependency I do not own. It needs `POST /quote/guidance` in `api/` that scores an ad hoc deal against a customer's stored reference book and returns the existing `Recommendation` shape (about 3d, backend owner). With no stored book, the only honest output is "insufficient data". Split the result panel out of `GuidanceClient` into `GuidanceResult` (1d, included).
- Decision, 2d. Reuse `DecisionControl` with a `source` field, tenant-scoped `requireAccess()` instead of `requireLead()`, writing to one unified decision log keyed by customer with `source` (salesforce, quote, slack, email) and an external reference. `/api/salesforce/workflow` should read the same table (backend and Neon change, flag to its owner).
- Log view and deep links, 1d. `/decisions` (DecisionLog plus source, actor, filter, CSV export) and `/decisions/[id]`.
- Brand pass and tests, 1d (the day is inside the 8).

### Slack and email delivery
Web must expose:
- `GET /decisions/[id]`: an authenticated page with guidance, requested terms, method, confidence and approve, reject, exception controls. The only place a number is computed and shown with its math. Auth through the existing magic link (`web/src/lib/magic.ts`). About 1d beyond the log view.
- An action endpoint taking signed one-time tokens (HMAC, short expiry, single use, bound to approver identity) so a forwarded email or replayed Slack payload cannot approve. 2d.
- Decision-log inclusion in the existing digest (`/api/digest/send`), 0.5d.

Server-side, not web (`api/`, next to governance): Slack app OAuth, request-signature verification, interactive payloads, retries and idempotency, email sending, approver routing, token minting. Estimates: Slack notification with deep link 3d; in-message approve buttons +3d; email notification with deep link 1.5d. Do not approve from an email click: link prefetchers and forwarding make it unsafe; always land on a confirm page.

Data posture: Slack and email carry a pointer and a one-line summary (deal name, requested versus recommended discount, status, link), never customer rows. That keeps the "row-level data processed in memory and deleted" promise intact. Add Slack to the subprocessors page when it ships.

### Browser overlay or extension for CPQ
- Feasibility: possible, brittle. DealHub, PandaDoc, Proposify and Salesbricks have no stable DOM contract; each overlay is a bespoke content script on a single-page app that changes without notice. Webhooks or APIs are the better seam where offered.
- Cost: first overlay 10 to 15d (MV3, per-tool selectors, auth, store review, privacy review), then 1 to 2d per month per tool for breakage. Broad host permissions will also fail many customers' security reviews and sit badly beside the trust page.
- Verdict: not worth it pre-pilot. Revisit only if a design partner names one CPQ tool and refuses both the quote screen and a webhook or API path.

## 3. Claim honesty: "works with any platform"

Checked against `vault/Competitive/2026-08-01-salesforce-market-need-assessment.md`, `richer-ingest.md`, and the Tier A and Tier B sizing.

| State | Defensible copy | Not defensible |
|---|---|---|
| Today | "Salesforce live. Any other CRM: a free diagnostic from one CSV or Excel export." | "Works with any platform", "plugs into your quoting tool", "connects to billing" |
| After the quote screen | "Check any quote by hand, from any tool. Enter the terms, get guidance, record the decision." No integration implied. | "Add-on to your CPQ" (it is a separate tab) |
| After each named adapter | Name only shipped, tested adapters, with direction (read-only or writes back). A status table: shipped, in pilot, not built. | Logos or "coming soon" for adapters in progress |
| After Slack or email | "Approvals where your team works", describing the deep link and recorded decision precisely. | "Approves in Slack" if it only notifies; any autonomous-approval wording |
| Margin | Keep the existing billing or ERP disclosure. No "gross and net margin" copy until a cost-input path and method ship. | A CRM proxy called margin |

Also hold: no price-setting language (the wedge preserves requested terms and records the human call); "learns from your data" only with the thin-data caveat (hundreds of deals, engine returns insufficient data). Change the hero eyebrow (`page.tsx:50`, `:76`) only after `/quote` works for a non-Salesforce customer on real data. Add one `PLATFORM_STATUS` constant under `web/src/data/` that the landing, pricing and trust pages all read, so no page can claim more than another (0.5d, in the 8).

## 4. Brand and UI consistency

- Extract a `DecisionCard` shell (verdict, receipt id, method, confidence) shared by `/crm`, `/quote`, `/decisions/[id]` and the Slack and email text templates, so the same facts appear in the same order everywhere. The verdict markup currently lives inside `DecisionControl`.
- Status colors carry meaning only and always with a text label: Leak Coral (#F0654E) below floor, Signal Green (#2BB673) within policy or realized, Caution Amber (#E8A33D) governance flags and "insufficient data". Slack and HTML email must repeat the label in words since colors vary by client and dark mode.
- Email: table layout, inline styles, Keel Navy (#0C2D48) header, one Waterline Teal (#17B8A6) button, plain-text part required, no web-font dependence. Slack: words, not color. No em dashes in any template.
- `/quote` and `/decisions` should use the calm authenticated look, not the landing page's Reveal and Aurora effects. Nav changes touch `Nav.tsx` and `layout.tsx`, which are claimed site-wide surfaces.

## 5. Risks and tradeoffs

- Scope: each surface is another product while paid-pilot validation is the critical path. Only the quote screen is something a partner can try without IT.
- The unified decision log is the compounding asset (defensibility doc). Ship it before any channel, or each channel forks the record.
- Email approval links are an attack surface; require a confirm page and identity.
- Manual entry can make the screen unused. A quote must take under a minute to enter; that is a validation question, not a build question.
- Reference book dependency: a CSV-only partner has no persistent book, so `/quote` says insufficient data. Persisting derived aggregates (not rows) is a retention-policy decision before it is a build task.

## 6. Recommended first increment

Quote check screen plus unified decision log, no channels: about 8 web days plus about 3 days of `api/` work for the guidance endpoint.
1. `/quote`: form or one-row upload, confirm table, existing `Recommendation` output with method and confidence, "insufficient data" honored.
2. `DecisionControl` records to a tenant-scoped unified log with a `source` field.
3. `/decisions` and `/decisions/[id]` deep links, the same link Slack and email later use.
4. `PLATFORM_STATUS` constant; landing copy unchanged until it works on non-Salesforce data.

Design-partner validation: does a deal desk member run three real quotes in a week, and does the recorded decision match what they would have done? Slack and email follow only on a yes (about 5 to 8 more days total).

## 7. Open questions for the founder

1. Is there a reference book to score `/quote` against? Retained CSV-derived aggregates change the data-retention promise; Salesforce-only scoring limits `/quote` to Tier B (130 to 190 accounts).
2. Who approves at the first design partner (deal desk, finance, a manager in Slack)? That decides whether Slack actions or email links come first.
3. Is a named CPQ tool a pilot condition? If so, ask for its webhook or API instead of an overlay.
