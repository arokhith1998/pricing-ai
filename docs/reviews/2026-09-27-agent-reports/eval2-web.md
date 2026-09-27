# Pricekeel web re-eval, 2026-09-27 (read-only)

## PK-6, PK-12, PK-14: closed, verified in code

- PK-6: `web/src/app/subprocessors/page.tsx:45-53` now lists Anthropic with a
  real DPA link; `web/src/app/trust/page.tsx:138-145` no longer names OpenAI,
  points to `/subprocessors` for "the current provider." Fixed.
- PK-14 (headline sign): `web/src/components/GuidanceClient.tsx:344-354`
  branches copy on `rec.uplift >= 0` vs coral "less in expected value." Fixed.
- PK-14 (comparables outcome word): `GuidanceClient.tsx:70-74` derives
  "won and lost" / "all won" / "all lost" from `rows`. Fixed.
- PK-14 (diagnostic subtitle): `web/src/app/diagnostic/page.tsx:34-72`
  classifies win-rate shape (`insufficient|monotone|rising_then_flat|flat|noisy`)
  from `win_rate_by_band` before choosing the sentence, including an explicit
  "Not enough discount bands with deals yet" case. Fixed.
- PK-12: `web/src/app/competitor-watch/page.tsx:180` now says "not
  Pricekeel's"; `FounderCta.tsx` is deleted (confirmed absent from
  `web/src/components/`); `FounderStrip.tsx:17` is the only rendered
  credential string. Fixed.

## Other items verified

- Insufficient-data disclosure: same `diagnostic/page.tsx:68-70` case above,
  plus `GuidanceClient.tsx:153-162` ("No {segment} deals sit this low... the
  model is pointing below this segment's historical discount floor").
- Caveat rendering: `GuidanceClient.tsx:192-217` (`ConfidenceCaveat`) branches
  on `c.split` and states AUC, n_train, base rate; not decorative.
- Tenant header on every proxy / per-visitor demo tenant:
  `web/src/lib/gate.ts:56-80` derives tenant from verified access code or a
  per-visitor `demo:<uuid>` cookie (`DEMO_TENANT_COOKIE`), comment states
  "Every proxy that talks to the decision-log/doc-store" uses this key.
- Static legal routes: no `export const dynamic` needed since none of
  `privacy|terms|licenses|subprocessors|trust` call `cookies()/headers()`;
  build output confirms prerendering (`web/.next/server/app/{privacy,terms,
  licenses,subprocessors,trust}.html` all exist as static HTML).
- "Segment-aware headline": not a marketing hero string. The only segment-
  keyed headline in the app is `GuidanceClient.tsx:114-116` ("Win rate by
  discount band · {ctx.segment}"), which is real and correct. The marketing
  hero (`HeroHeadline.tsx`) is a fixed 8-word string, not segment-aware, and
  was never claimed to be by CLAUDE.md, so this is not a defect, just a
  naming mismatch in the brief.

## Landing page audit (`web/src/app/page.tsx`)

Ten `<section>` blocks: hero, CrmWorkflowPreview, WhatYouGet,
DiagnosticPreview, an inline "evidence stack" source grid, a V1-boundary
card, FounderStrip, TrustStrip, MethodologyStrip, final CTA. Rough word
count of visible copy (headings, body, labels, mockup text) is ~1,100 words,
not counting Nav/Footer, which render on every route via `layout.tsx`.

Every claim checked traces to a real disclosure or is explicitly labeled
illustrative: the CrmWorkflowPreview mockup ("Hold at 16%," "$29.4K price
retained") carries an "Illustrative deal" chip (`CrmWorkflowPreview.tsx:107-
109`); DiagnosticPreview's KPIs are real `/sample` output per its own
comment (`DiagnosticPreview.tsx:19-23`) but that fact only appears in a
caption at the very bottom of the mockup (`DiagnosticPreview.tsx:213-218`),
after a visitor has already read four KPI numbers with no inline label. No
new honesty violation found; the problem is density, not accuracy.

What makes it feel heavy: the hero alone stacks nine sub-blocks (eyebrow,
headline, subhead, two CTAs, sample disclosure, best-fit line, ICP tags, V1
line, a billing-consolidation paragraph) before the first scroll. Three
separate sections then re-tell the same "evidence before a human decision"
story with three different mockups (workflow card, diagnostic card,
evidence-source grid), and the V1 commitment-tier caveat is repeated
verbatim in both the hero and CrmWorkflowPreview. Three more sections
(FounderStrip, TrustStrip, MethodologyStrip) run back to back as separate
credibility beats instead of one.

## Proposed structure: five sections, immersive, one CTA

**1. Hero.** One sentence, one real number, one action.
- Eyebrow: `Salesforce deal guidance for B2B SaaS`
- Headline: "See what a discount exception is really worth before you approve it."
- Number line: "On the 2,000-deal sample book, $8.9M of price sits below the segment's win point."
- CTA (single): button "Run the live engine on the sample" -> `/sample`. Drop the second competing button; keep `/contact` as a small text link beneath: "Or walk through one real exception ->"

**2. Immersive readout (scroll-revealed).** Keep `DiagnosticPreview` as the
only product mockup on the page (delete the CrmWorkflowPreview card and the
inline evidence-source grid as separate visual surfaces; fold their one-line
takeaways into the caption). Add the "illustrative vs. real" label to the
KPI row itself, not just the closing caption:
- Kicker above the KPI row: "Real output from the synthetic 2,000-deal sample, not a mockup."
- Keep the four KPIs and the win-rate bars as-is; keep the existing caption line about CSV/XLSX and thin books.

**3. What you get, three roles, one line each.**
- Heading: "One decision record, three views."
- Deal Desk: "See the guardrail and the closest comparable deals. Accept, trade, or override."
- Pricing: "See realization and win rate by segment and band, with cited competitor context."
- Finance: "See who approved what, and where CRM discount data stops and true margin needs billing or ERP."

**4. Trust and boundary, one line each, one strip.**
- "Row-level deal data is processed in memory and deleted. The model recommends a guardrail; a person decides."
- V1 boundary, exactly one line: "V1 prices the discount on committed, annualized ACV from Salesforce; margin still needs billing or ERP data."
- Small print row: methodology citations (Nagle, Ramanujam, Bertini, Simon-Kucher, Rivera) as a single linked line, not five cards. Founder credential moves to `/about` or the footer, not mid-scroll.

**5. Call to action.**
- Heading: "A 20-minute conversation, not a demo."
- Body: "Tell us how discount exceptions get approved today. No data and no Salesforce access needed to talk."
- One button: "Talk to us" -> `/contact`.

This drops ten sections to five, removes two of three redundant product
mockups, states the V1 boundary once instead of twice, and gives the visitor
exactly one number the engine produced and one action to take.
