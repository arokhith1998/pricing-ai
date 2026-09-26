# Pricekeel web surface evaluation (read-only)

## Verdict

The site is in good shape structurally and unusually disciplined on marketing honesty:
the homepage, pricing page, and trust page all carry the margin-disclosure and
cold-start caveats CLAUDE.md demands, status colors are consistently paired with text
labels, and secrets stay server-side with no NEXT_PUBLIC_ leakage. The real problem is
that three tasks already marked READY (PK-6, PK-12, PK-14) are not actually done: the
files they target still show the exact defects their acceptance criteria describe. This
reads as tasks that were scoped and queued but never executed, not as fresh regressions.
Ship-blocking for trust: a security/IT reviewer hitting /trust or /subprocessors today
sees OpenAI named as the sole LLM subprocessor while the backend can run on Anthropic,
which is a subprocessor-disclosure gap, not just a copy nit.

## Top 6 findings

1. **[High] PK-6 not done: OpenAI-only subprocessor disclosure.**
   `web/src/app/trust/page.tsx:138` ("The cloud LLM (OpenAI) sees only...") and
   `web/src/app/subprocessors/page.tsx:46-53` list only OpenAI, no Anthropic row, no DPA
   link. `pricing/assist.py:53-56` shows the backend is provider-swappable via
   `LLM_PROVIDER=anthropic`. `gtm/security-one-pager.md:28` has the same gap. Fix: add an
   Anthropic subprocessor row with a real DPA URL and date, and make the trust-page
   prose provider-agnostic or list both.

2. **[High] PK-14 not done: expected-value headline ignores negative uplift.**
   `web/src/components/GuidanceClient.tsx:253-259` always renders "more in expected
   value" when a lower discount is recommended, even though the accent logic three
   lines later (`GuidanceClient.tsx:281`, `accent={rec.uplift >= 0 ? "navy" : "coral"}`)
   already anticipates `uplift < 0`. A CFO reading a coral tile next to a headline that
   says "more" is exactly the asserted-not-computed mismatch PK-11 flagged. Fix: branch
   the copy on `rec.uplift` sign.

3. **[Medium] PK-14 not done: two more hardcoded shape claims.**
   `GuidanceClient.tsx:75` ("...closed deals... won and lost") renders regardless of
   whether `rec.comparables` actually contains both outcomes. `web/src/app/diagnostic/
   page.tsx:211` ("Win rate climbs with discount, then flattens") is a fixed subtitle
   independent of `d.win_rate_by_band`'s actual shape. Fix per acceptance criteria:
   derive both from the data.

4. **[Medium] PK-12 not done, all three nits.** `competitor-watch/page.tsx:180` still
   reads "under the operator's terms (see /terms)" linking to Pricekeel's own terms page,
   which a user can misread as Pricekeel's terms governing the third-party site.
   `docs/reviews/founder-action-checklist.md:97` is still accurate today because
   `web/src/components/FounderCta.tsx` is genuinely dead code (not imported anywhere)
   still holding the retracted "$626M margin-recovery" chip. `vault/GTM/seed-deck-
   outline.md:98` says "M.S. in Pricing" while the live site's `FounderCta.tsx:24` says
   "M.S. Marketing Analytics, Pricing" and `FounderStrip.tsx:17` (the component actually
   rendered on the homepage) says "Founder, M.S. Pricing" — three different phrasings of
   one credential across the repo, one of them on a dead component. Fix: pick one
   phrasing, delete `FounderCta.tsx`, sync the deck.

5. **[Low-Medium] Global layout ships framer-motion to every route, including
   force-static pages.** `web/src/app/layout.tsx:5-6,42-43` mounts `AuroraBackground`
   (`web/src/components/AuroraBackground.tsx`, `"use client"` + framer-motion scroll
   listeners) and `ScrollProgress` unconditionally in the root layout, so `/privacy`,
   `/terms`, `/licenses`, and `/subprocessors` all pull in framer-motion JS despite
   `web/CLAUDE.md`'s "static marketing pages stay dependency-free and fast" rule. These
   are exactly the pages a compliance reviewer opens first; they don't need parallax.

6. **[Low] Client-side fetch error messages are generic but not localized to failure
   type.** `web/src/lib/api.ts:356,404,420,440` all throw `API responded ${status}` with
   no distinction between 4xx (bad input) and 5xx (backend down), and every caller
   (`GuidanceClient.tsx:237-241`, `DecisionLog.tsx:53-58`) collapses that into one
   generic "is the API running?" message. Not wrong, just leaves no path for a
   recoverable client error (e.g., bad deal id) versus a real outage.

## Three good things

- `web/src/app/trust/page.tsx` and `subprocessors/page.tsx` are otherwise a genuinely
  careful, non-euphemistic disclosure (in-memory-only processing, AES-256-GCM token
  encryption, SOC 2 honestly stated as "not yet certified").
- Marketing copy is disciplined: `web/src/app/page.tsx:24-29,44-64` and `WhatYouGet.tsx:22`
  keep the "recommends," never "sets," framing and the CRM-proxy-is-not-margin
  disclosure intact, matching the evidence-boundary intent in CLAUDE.md.
- Status-color usage (`DecisionLog.tsx:21-30`, `LeakageBars.tsx:6-26`) never relies on
  color alone; every coral/amber/green chip carries a text label, matching
  `brand/PALETTE.md`'s accessibility note.

## One thing to fix next week

Close PK-6 for real: add Anthropic as a named subprocessor with a dated, real DPA link
on `/trust`, `/subprocessors`, and `gtm/security-one-pager.md`, and make the "cloud LLM"
prose provider-agnostic so it stops silently going stale every time `LLM_PROVIDER`
changes. This is the one gap a security reviewer can catch and use to distrust every
other disclosure on the page.
