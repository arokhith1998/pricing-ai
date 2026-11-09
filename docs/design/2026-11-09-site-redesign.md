---
title: Site and app redesign audit and plan
created: 2026-11-09
updated: 2026-11-09
tags: [design, web, redesign, audit]
status: approved-for-entry
source: founder review of the live site 2026-11-09; lead notes at an 800px viewport; code read of web/src
---

# Site and app redesign: audit and plan

**Status 2026-11-09: approved-for-entry.** PK-75 to PK-84 are on the board in BACKLOG; PK-85 is not entered. D-R1 to D-R6 carry lead defaults, founder may override; see the status line and "Changes on entry" in `docs/reviews/2026-11-06-product-direction/TASKS-redesign-proposed.md`.

The founder asked for every page of the marketing site and the app to be rechecked and redesigned where needed so it reads as "more professional and immersive". This document is the audit and the plan. Nothing under `web/` was changed. Tasks are in `docs/reviews/2026-11-06-product-direction/TASKS-redesign-proposed.md` (PK-75 to PK-85).

## 0. Method and limits

- Read: `brand/PALETTE.md`, design doc 2026-11-06 section 4, the git history of `web/src/app/page.tsx` (PR 70), `globals.css`, `layout.tsx`, every chrome component, every `page.tsx` under `web/src/app`, and the components each renders.
- Computed WCAG contrast ratios from the dark tokens with the standard relative-luminance formula. Every ratio quoted below is computed, none is estimated.
- Not done: no dev server, no browser, no screenshots, no Lighthouse run. Layout findings come from reading class names, so "at 800px" statements are inferences from breakpoints. The first task (PK-75) records a measured baseline (Lighthouse mobile and desktop for six routes, plus a 375px screenshot of each page) before anything changes, so the later acceptance numbers are checked against fact.
- `npm run build` was not needed: route metadata is readable in source.

## 1. The lead's observations, confirmed or refuted from code

| Observation | Verdict | Evidence |
|---|---|---|
| Hero is "Stop giving away price that wins you nothing." with "nothing." and a large "$8.9M" in coral on a navy aurora, then a stats widget | Confirmed. Also a hierarchy inversion: the number is larger than the headline | `HeroHeadline.tsx:8` h1 is `text-4xl sm:text-5xl` (36 to 48px); `page.tsx:57` number is `text-5xl sm:text-6xl` (48 to 60px). `$8,946,770` is the segment-aware gap in `sample-fallback.json` |
| Clean but template-like: uniform thin-bordered cards | Confirmed | 108 occurrences of `border-mist bg-surface` across components and pages; the same `rounded-xl border bg-surface p-5` is used for a KPI, a FAQ, a legal section and a form |
| Small, low-contrast grey body copy | Half refuted. Contrast passes, size and weight do not | Muted `#8EA3BD` is 7.41:1 on canvas and 6.73:1 on surface, so it clears AA and AAA. The problem is size: 150 uses of `text-xs`, 33 uses of 10 or 11px, and body copy set at `text-sm` (14px) in the lightest text tone on every page. It reads faint because it is small and long, not because the ratio is low |
| No product imagery beyond the stats widget | Confirmed | The only product render is `DiagnosticPreview.tsx`. There is no render of the decision record, the guardrail, or the decision log anywhere on the marketing site |
| Pricing is three dense columns of small text | Confirmed | `pricing/page.tsx:177` `md:grid-cols-3` starts at 768px, so at 800px each column is about 240px of `text-sm` copy with 4 bullets each |
| Methodology is a thin list of cards | Confirmed | Five link cards and one paragraph, no content about the method itself |
| Trust is plain text | Confirmed | One `max-w-3xl` column of `text-sm` bullets, no structure for scanning, no status labels |
| Login is a small box in a large empty canvas | Confirmed | `login/page.tsx:73` `min-h-[70vh]` with a `max-w-sm` form and no h1, no explanation of what is behind the code |
| Calculator is the strongest page | Confirmed | Ungated, interactive, shows its math, discloses its limits. It is the model for the rest |
| Footer is a flat row of 14 links | Confirmed, count is 13 links plus the wordmark | `Footer.tsx` one `flex-wrap` nav, no grouping |
| Sample and login carry the home page title; pricing reads "Pricing · Pricekeel · Pricekeel" | Confirmed, and it is wider than reported | See section 4: eleven routes double-suffix, seven routes inherit the home title |
| No visible mobile check | Confirmed | The only viewport test is `web/test/diagnostic-mobile-overflow.test.ts` (jsdom, structural, 390px, one route). No screenshot or browser test exists |
| Immersion is the aurora and reveal animations only | Confirmed | `AuroraBackground.tsx` (three scroll-linked layers), `Reveal.tsx`, `CountUp.tsx`, `pk-card-3d`, two infinite glow pulses. None of it shows the product |

## 2. Findings that most undermine a professional read

Ranked by how much each costs the first impression and by how cheap it is to fix.

1. **The site never shows the product's own artifact.** The wedge is "the decision record": requested terms, the evidence behind a recommendation, the human decision, the log row. A visitor never sees one. They see a KPI strip and a bar chart, which any dashboard has. This is the single biggest reason it reads as a template. It is also the best honest immersion available, because the artifact can be rendered from the real synthetic sample.
2. **Metadata is wrong on 18 of 21 routes.** Eleven routes double-suffix their title (the layout template appends " · Pricekeel" to titles that already end in it), seven routes (including `/sample` and `/login`) inherit the home title, and every page inherits `og:url` of `/`, so a shared pricing link unfurls as the home page. This is what a prospect sees in a browser tab, a Slack unfurl and a search result before the page loads.
3. **Hierarchy and type scale are inconsistent.** The hero number outranks the h1. Body copy is 14px in the faintest text tone sitewide. There are 33 uses of 10 to 11px text, including trust status badges and chart labels. h1 sizes range from `text-2xl` (app pages) to `text-4xl` (marketing) with no scale behind them. `font-extrabold` appears on hero, wordmark and calculator but not elsewhere.
4. **One surface pattern for everything, plus gimmicks where depth should be.** Every block is the same thin hairline card (border `#1F2C43` against surface `#111A2B` is 1.24:1, so edges are nearly invisible and cards read as faint outlines). Where the site adds depth it does so with a hover tilt (`pk-card-3d`, `rotateX`) on static information cards and two infinite coral glow pulses. Those read as effects, not product.
5. **Status color used as decoration, and an AA failure in the action fill.** `DiagnosticPreview.tsx:103` draws traffic-light dots in coral, amber and teal as fake browser chrome. The hero word "nothing." is coral with a breathing glow. PALETTE.md reserves coral and amber for status, never decoration. Separately, the `bg-navy` action fill (`#0D9488`) carries white text in five places (login, lead form, magic link, upload x2) and white on `#0D9488` is 3.74:1, which fails AA for normal text (4.5:1). PALETTE.md line 55 says "white text passes AA"; that is true only for large text. The primary button elsewhere (`bg-teal text-bg`) is 10.29:1, so the fix is to use one button.

Next tier, still worth fixing: pricing mixes a deferred roadmap item into three equal-weight cards with the same "Talk to us" button (section 3, pricing); inputs and controls use the 1.24:1 border so form fields fail the 3:1 non-text contrast rule (WCAG 1.4.11); the footer is ungrouped; login has no h1 and no explanation; `/crm` is one 592-line file whose render functions are single lines of 2,000 or more characters, which blocks any restyle; `SalesforceWorkspace.tsx` uses raw Tailwind `amber-300/amber-200` (off palette).

## 3. Page by page audit

Format: purpose and audience, what works, what undermines, mobile risks, metadata, claims.

### / (landing, `page.tsx`, force-static)

- **Purpose and audience.** First contact for a Head of Pricing, Deal Desk lead or RevOps lead at a $10 to 100M ARR Salesforce shop, and for investors. Goal: one conversation.
- **Works.** PR 70 discipline holds: five sections, one number, `force-static`, the number is read from the bundled snapshot not typed, `DiagnosticPreview` says "Real output of the engine on a synthetic 2,000-deal book", `TrustBoundaryStrip` states limits once. `Reveal` is safe by default after the 2026-09-27 empty-viewport bug.
- **Undermines.** Hero hierarchy inversion (finding 3). Hero is `min-h-[100svh]` under a 64px sticky nav, so the only product visual is entirely below the fold at any viewport; above the fold is text, a number and a button. The hero number caption says "on the sample book" but not "synthetic"; the evidence-boundary rule says every number must say so where it appears. `DiagnosticPreview` is a faux browser window with traffic-light dots (finding 5), a tilt on hover, a pulsing coral KPI, and an eyebrow "Scroll to see it run" for a chart that animates once. Section 3 "One decision record, three views" is three small cards with one sentence each, and no decision record is shown. Section 4 is a bordered bullet list with a link row at `text-xs`. Section 5 is a second CTA with an eyebrow "Design-partner cohort" that implies a cohort exists; the founder has no design partner yet, so "cohort" overstates.
- **Mobile.** Hero stacks fine. Six chart bars at 375px are about 45px each with `whitespace-nowrap` labels (acceptable). `text-5xl` number at 48px fits. The mock browser URL bar and 4-up KPI grid collapse to 2-up, which is fine. Risk: the ChatPanel launcher (global) was already found obstructing content on mobile once.
- **Metadata.** Default title and description are right for the home page. No page-level `og:image` variant; the single root image is fine.
- **Claims.** Headline "wins you nothing": in the synthetic book the 25%+ band still wins 42% against a 68% peak (5 to 10% band), so discount past the win point buys fewer wins but not zero. "Buys fewer wins, not more" (`DiagnosticPreview.tsx:149`) is a causal-sounding sentence about a synthetic book generated with that shape; the calculator page correctly calls the same relationship "correlational". Recommend wording that describes the sample: "In this synthetic book, win rate stops improving past the win point." The headline itself is a founder call (decision D-R5). "Design-partner cohort" as above.

### /sample (`sample/page.tsx`, force-dynamic)

- **Purpose and audience.** The lead-capture door: shows four KPIs, then gates the rest behind a company email form.
- **Works.** Honest labelling ("A worked example on a realistic synthetic book of 2,000 closed deals"), the cached-snapshot disclosure, `CountUp` respects reduced motion, KPI sub-labels explain weighting differences, the gate states what unlocks.
- **Undermines.** Title is the home title and there is no description. The `LeadGate` is the weakest moment in the funnel: a plain card with a bullet list on the left and a form on the right, no preview of what unlocks. The four KPI cards use `pk-card-3d` tilt. Unlocked state (`FullSample`) leads with a `PageGuide` panel, then a text summary, then two link cards, then a six-box flow strip; there is no chart, which is the opposite of what a "sample report" should lead with. `Flow` boxes wrap into an uneven ragged row on mobile.
- **Mobile.** Grid is `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`, fine. The `Flow` strip wraps with arrows orphaned at line ends.
- **Metadata.** Home title inherited. Fix.
- **Claims.** Nav labels it "Live sample"; it is a snapshot with a live-engine fallback path, and the page itself says "Cached sample" when it falls back. Rename to "Sample" (decision-free copy fix). "Unlock the full diagnostic" copy is accurate.

### /calculator (`calculator/page.tsx`, force-static)

- **Purpose and audience.** The ungated engine-adjacent tool for any visitor. Strongest page.
- **Works.** Interactive, shows its math, explicitly refuses to invent a recovery rate, discloses that the average-based figure understates. Honest "no data leaves your browser" badge.
- **Undermines.** Not in the primary nav (only in the footer), so the best page is hard to find. `LeakageBars` and the result card share the generic card pattern; result is not given more visual weight than the inputs. Title doubles (`calculator/page.tsx:8`).
- **Mobile.** Single column `max-w-4xl`; inputs need verification at 375px (not read in detail; PK-79 verifies).
- **Metadata.** Description is good. Title doubled.
- **Claims.** Clean. "typical 15% deal-desk line" is disclosed as a typical policy threshold, not a finding.

### /pricing (`pricing/page.tsx`, force-static)

- **Purpose and audience.** Answers "how is it sold and what does it cost" for Finance and the founder-led sale. There are no prices, by design.
- **Works.** Candid that engagements are scoped, not self-serve; CRM-evidence boundary stated in the third "why not a feature" card.
- **Undermines.** About 400 lines of `text-sm` copy in eight stacked bordered boxes. Three equal-weight tier cards at `md:grid-cols-3`. The third card, "Data expansion", is labelled "Explicitly deferred" and "not a current sales tier" yet carries the same "Talk to us" button as the others. The page uses plain `<a href="/contact">` where the rest of the site uses `Link`. The FAQ block, the "why not a feature" block and the scenarios block each restate the same boundary. `pricing/page.tsx:5` title `"Pricing · Pricekeel"` renders as "Pricing · Pricekeel · Pricekeel".
- **Mobile.** Cards stack under 768px, fine. The thresholds `<table>` is inside `overflow-x-auto`. At 768 to 1000px the three columns are too narrow (the lead's observation).
- **Metadata.** Doubled title, inherited description.
- **Claims (several exceed the evidence boundary).**
  - `pricing/page.tsx:257` "Most subscribers will clear all three." There are no subscribers. Remove.
  - `pricing/page.tsx:119` "Largest: $480K Enterprise at 22%. The disclosed segment reference is 14%..." is a hand-typed scenario, not a sample figure and not labelled illustrative. The evidence-boundary rule says every number comes from the synthetic sample and says so. Either take the figures from the snapshot (a real synthetic deal, labelled) or mark the whole block "Illustrative, not customer data".
  - `pricing/page.tsx:153` and nearby ROI thresholds ("5 hours per week, $80 per hour = ~$20K", "1 to 2 deals per quarter ... $30K to $50K per year saved") are assumptions presented as arithmetic. Label as the reader's own inputs with a calculator-style "your numbers" framing, or cut. "Worth the subscription at the $50M ARR tier on its own" is an unsupported value claim.
  - `pricing/page.tsx:187, 395` "Engagements typically start in the low five figures." "Typically" implies a population of engagements. Say "We expect early engagements to start in the low five figures" or drop; founder decision D-R6.
  - `pricing/page.tsx:301` "Our diagnostic is open code." Verify the repository is public or the code is available to customers; if not, say "reproducible code you can audit under NDA" (the FAQ already says "audit").
  - `pricing/page.tsx:184` "reply within one business day" is an operational promise; keep only if the founder will meet it.
  - The "Operate" tier text describes Salesforce OAuth, writeback and weekly digest as present tense. These ship per the state board; keep, but PK-52/62/69 later edit this file, so the redesign must land first (sequencing in the task list).

### /methodology (`methodology/page.tsx`, force-static)

- **Purpose and audience.** The bibliography a Head of Pricing can cite.
- **Works.** Real, correct sources with links; moved off the landing page by PR 70.
- **Undermines.** It is a list of five cards under one paragraph. It says what the method cites, not what the method does. A diligence reader wants: how the win point is found, what the confidence band is, what "insufficient data" means, what is correlational versus modeled. All of that exists in the engine and in `sample-fallback.json` (`reference_discount.band_win_rate_ci`, `reference_basis`, `sufficient`, `band_counts`) but none of it is shown.
- **Mobile.** Two-column grid collapses at `sm`; fine.
- **Metadata.** Doubled title.
- **Claims.** `methodology/page.tsx:72` "grounded in a published framework, not invented math" over-credits: the win point, leakage lenses and trade-or-give are Pricekeel computations informed by those authors, not published formulas. Reword to "informed by" and show the actual computation.

### /trust (`trust/page.tsx`) and /privacy, /terms, /subprocessors, /licenses

- **PK-6 (PR 77, in review) owns** `web/src/app/privacy`, `trust`, `subprocessors`, `licenses`. This audit does not touch their facts. Findings are structural only and apply after PK-6 merges.
- **Purpose and audience.** The IT or security reviewer and Finance. First page a compliance reviewer opens.
- **Works.** Candid tone, a "Pre-SOC 2 · controls live" badge, a "where the data lives" list with providers and regions, explicit "what we do NOT store", clear AI handling section. `ChromeEffects` already removes aurora and scroll bar on the four legal routes.
- **Undermines.** One narrow column of `text-sm` bullets: no table of contents, no at-a-glance summary, no status labels (live, in progress, not yet) on controls, no consistent legal layout shared across the five pages. The badge is `text-[10px]`. `trust/page.tsx:11` renders the literal placeholder `[security@pricekeel.com]` when `NEXT_PUBLIC_CONTACT_EMAIL` is unset, which is placeholder content on a trust page. The "Updated 30 May 2026" date should be checked against PK-6's edits.
- **Metadata.** All doubled titles; trust has no description.
- **Claims.** Not assessed here; PK-6 owns. The redesign must be copy-neutral: restructure and restyle, change no sentence. A test (PK-82) diffs the extracted text of each page before and after and fails on any wording change.

### /contact (`contact/page.tsx`, force-static)

- **Purpose and audience.** Conversion page.
- **Works.** Offers a no-credentials first conversation, three paths (email, LinkedIn, sample), an email template.
- **Undermines.** Three equal cards, then a code block template, then a bulleted "what happens next". No form (a mailto is a conversion cliff, but that is a founder decision, not a redesign item). Title doubled. "Every request goes directly to Adhithya" and "reply within one business day" are accurate only while volume is near zero; fine today.
- **Claims.** Clean; "Salesforce OAuth tokens stay server-side and encrypted at rest" matches PK-6's corrected trust facts.

### /blog and /blog/[slug]

- **Purpose.** Credibility content. Three posts exist (`web/content/blog`).
- **Works.** Correct metadata (`Blog` plus template, canonical on index), dated scheduling, rendered markdown through `sanitize-html`.
- **Undermines.** A three-post blog reads as thin. Index is a stack of identical cards; `pk-prose` body is `1rem` in the muted tone with no measure cap beyond `max-w-3xl`. Fine, not urgent. Founder decision D-R4 on whether to keep it in the nav.

### /login (`login/page.tsx`, client component)

- **Purpose.** Entry to the customer workspace, `/upload`, `/competitor-watch`.
- **Works.** Honest recovery paths: email for a code, contact page; NDA before data.
- **Undermines.** Tiny centred form on an empty canvas (the lead's note). No h1. No metadata at all and it cannot export any (client component). Not marked noindex. The submit button is `bg-navy text-white` (3.74:1, fails AA). Input border is `border-mist` (1.24:1). Two different "no code" paragraphs say overlapping things. A cold visitor does not learn what the workspace is.
- **Metadata.** Home title inherited. Needs a sibling `layout.tsx` with metadata and `robots: noindex`.

### /diagnostic, /guidance, /upload, /competitor-watch, /crm (the app)

All behind the proxy gate (`proxy.ts:104` to `130`: `/upload`, `/crm`, `/competitor-watch` need the access code; `/diagnostic`, `/guidance` need the lead cookie). A visitor without the right cookie is redirected to `/login` or `/sample`.

- **/diagnostic.** Long single page of seven `Card` sections, four tables, three chart components, a copilot panel. All tables are inside `overflow-x-auto` and pinned by the 390px test. What works: the "receipts" tables (deal by deal evidence), `classifyWinRateShape` (PK-14, never asserts a shape the data does not show). What undermines: no sticky section navigation on a very long page, every section is the same card, tables at `text-sm` with no row hover or number alignment system, charts (Recharts) styled per file. No `<title>`.
- **/guidance.** Header, `PageGuide`, `GuidanceClient`, decision log, model quality. Works: the decision log is the real artifact and the page includes it. Undermines: it is buried below a deal picker, and the model-quality block uses an arrow-text "← lead with this" instruction aimed at the builder, visible to the user. Claim risk: `guidance/page.tsx:29` "The model learns from your closed deals". That is accurate but hides the cold-start reality (hundreds of deals). The sentence that follows should say the model returns "insufficient data" on thin segments, which the engine does. Copy change belongs to PK-81 with a founder-visible note; it adds a limit, not a claim.
- **/upload.** Required-columns table, optional-columns run-on string, privacy callout, upload client. Works: the privacy contract at the upload moment. Undermines: the optional column list is one 300-character string; buttons use the failing `bg-navy` fill.
- **/competitor-watch.** Client component with no metadata, its own pill and card styling (`text-[10px]` uppercase pills).
- **/crm (`SalesforceWorkspace.tsx`, 592 lines).** The real product screen: connect, readiness, executive/pricing/deals views, accept/override/approve/reject, append-only history. Undermines: render functions are single 1,500 to 2,500 character lines, so no one can restyle them safely; raw `amber-300/amber-200` classes are off palette; the workspace has its own h1 "Salesforce pricing desk" in a different scale from every other page. **PK-49 (connector plan, not started) owns `crm/page.tsx` and `SalesforceWorkspace.tsx`.** A restyle must either wait for it or be agreed with it. See decision D-R1.

### /brand, /brand/cover

Internal-ish brand kit and a 1128x191 cover. Title doubled on `/brand`. `/brand/cover` is noindex and has no h1 (intentional, it is a render target). Low priority; token cleanup only.

### not-found, error

Plain, correct, on-palette. Restyle to the new primitives in PK-79 for consistency.

## 4. Metadata audit (rendered result of `layout.tsx` title template `%s · Pricekeel`)

| Route | Rendered title | Own description | Own OG | Issue |
|---|---|---|---|---|
| `/` | Pricekeel · Salesforce deal guidance for B2B SaaS | default | default image | OK |
| `/sample` | same as home | none | none | wrong title |
| `/pricing` | Pricing · Pricekeel · Pricekeel | none | none | doubled |
| `/calculator` | Discount leakage calculator · Pricekeel · Pricekeel | yes | none | doubled |
| `/contact` | Contact · Pricekeel · Pricekeel | yes | none | doubled |
| `/methodology` | Methodology · Pricekeel · Pricekeel | none | none | doubled |
| `/trust`, `/privacy`, `/terms`, `/subprocessors`, `/licenses` | X · Pricekeel · Pricekeel | none | none | doubled (PK-6 owns four) |
| `/brand`, `/brand/cover` | X · Pricekeel · Pricekeel | yes / none | none | doubled |
| `/blog`, `/blog/[slug]` | Blog · Pricekeel; post title · Pricekeel | yes | yes for posts | OK |
| `/login`, `/upload`, `/crm`, `/diagnostic`, `/guidance`, `/competitor-watch` | home title | none | none | wrong title; not marked noindex |

Every page also inherits `og:url` `/` and the root title in `og:title`, so unfurls of any inner page show the home page. Only the blog sets a canonical. `sitemap.ts` lists the 12 public routes and is otherwise right (gated routes excluded).

Fix pattern: a small `pageMetadata({ title, description, path })` helper (PK-75) that returns title without the suffix, description, `alternates.canonical`, and `openGraph` and `twitter` blocks with the right url. Each page task adopts it for the pages it owns. A site-wide test (PK-84) asserts no rendered title contains " · Pricekeel · Pricekeel", every public route has a unique title and description, every gated route is noindex.

## 5. Mobile risk read (from code, not a device)

- No fixed widths over 360px found. Inline pixel widths: `Nav.tsx:88` popover `w-64` (256px, fine), `DiagnosticPreview.tsx:43` `max-w-[28px]` bars (fine).
- Tables: 14 `<table>`s, every one inside `overflow-x-auto` (verified by grep). Table scroll is acceptable on narrow screens but gives no scroll affordance. App tables should add a right-edge fade and a sticky first column.
- Grids with a `lg:` or `md:` breakpoint and a single-column base are fine. Risk areas to measure: `/crm` `lg:grid-cols-[0.9fr_1.1fr]` with `max-h-[580px]` inner scroll, `GuidanceClient` two-column factor layout, `/calculator` inputs.
- Hero: `min-h-[100svh]` is right on mobile as long as the CTA is above the fold; verify it at 375x667.
- Touch targets: nav links are `px-3 py-2` (about 36px high); footer links are bare text with `gap-y-1` and are well under 44px. Fix in PK-75.
- Text floor: 33 uses of 10 to 11px text; set a 12px floor sitewide and reserve 12px for chart axes and legal meta only.
- The hero and the decision walk (new) must degrade without JS and without sticky positioning below `md`.

## 6. Design direction

### 6.1 Principles

1. **Show the artifact.** The decision record and the readout are the product. Render them from the synthetic sample, label them as such, and let them carry the immersion.
2. **One system.** Fewer patterns, applied consistently: three surfaces, one radius family, one type scale, one button.
3. **Restraint is the premium signal.** Remove effects that do not show the product (card tilt, infinite glows, scroll-linked parallax). Keep motion that explains (bars drawing, a step advancing, a number counting once).
4. **Honest by construction.** Every number on a marketing page is imported from `sample-fallback.json` or computed from it; every such block carries a "Synthetic sample" label as a component prop, not as hand-typed text. No stock images, no logos, no testimonials, no invented counts.
5. **Inside the palette.** No new hues. Derived alpha tints of existing tokens are permitted (the code already uses `teal/50`, `coral/30`).

### 6.2 Type scale (Inter via `next/font`, already loaded; no second face)

| Role | Size and line height | Weight | Use |
|---|---|---|---|
| Display | `clamp(2.5rem, 5vw, 4rem)` / 1.05 | 700, tracking -0.025em | Landing hero only |
| H1 | 2.5rem / 1.15 (2rem on mobile) | 700 | Every page, one per page |
| H2 | 1.875rem / 1.25 (1.5rem on mobile) | 650 | Section heads |
| H3 | 1.25rem / 1.4 | 600 | Card and block heads |
| Lead | 1.125rem / 1.75 | 400 | First paragraph under an H1, tone fg |
| Body | 1rem / 1.65 | 400 | All running copy, tone muted `#8EA3BD` (7.41:1) |
| Small | 0.875rem / 1.5 | 500 | Table cells, captions, form labels |
| Eyebrow | 0.8125rem / 1.2, uppercase, tracking 0.12em | 600 | Section labels, teal |
| Micro | 0.75rem / 1.3 | 500 | Chart axes and legal meta only; nothing at 10 or 11px |
| Figure | tabular-nums, 2rem to 3.75rem | 700 | KPIs and the hero number; never larger than the H1 or Display on the same page |
| Mono | `ui-monospace` stack, 0.8125rem | 500 | Ids, evidence versions, column names; system font, no download |

Rule: body copy never goes below 16px on marketing pages and 14px in app tables. The hero number is capped at the display size, fixing the inversion.

### 6.3 Spacing and rhythm

- 4px base unit; 8-point steps for components; section padding 96px (desktop), 64px (tablet), 48px (mobile).
- Container 1152px (`max-w-6xl`) for sections, 720px (`max-w-3xl`) for prose and legal, 1280px for the app shell. Gutters 24px, 16px on mobile.
- Section rhythm alternates three bands: **canvas** (bg `#0A0F1A`), **band** (surface-2 `#0D1422` with a 1px hairline above and below), **spotlight** (canvas with one radial teal glow behind the artifact). No two adjacent sections share a band.
- Every section: eyebrow, H2, optional lead (measure capped at 68ch), then content. One CTA per section at most.

### 6.4 Surface system (cards that read as one product)

| Surface | Token | Border | Use |
|---|---|---|---|
| Canvas | `--color-bg` `#0A0F1A` | none | Page |
| Card | `--color-surface` `#111A2B` | 1px `#1F2C43` plus 1px top inner highlight (white at 4%) | Content blocks |
| Inset | `--color-surface-2` `#0D1422` | 1px `#1F2C43` | Wells inside cards, table heads, inputs |
| Artifact | `--color-surface` | 1px `#1F2C43` plus a 24px teal-at-10% outer glow, one per page | The decision record and readout renders |

- One radius family: 12px (cards, inputs, buttons 8px), 20px for the artifact only.
- Controls (inputs, selects, toggles) use the canonical **Slate `#5B6B7B`** as the border on inset (about 3.3:1, to be measured), meeting the 3:1 non-text rule; decorative card edges keep `#1F2C43`.
- Elevation by tone and glow, not by shadow stacks. No hover tilt. Hover on interactive cards: border to teal at 50%, 120ms.
- Components in `web/src/components/ui/`: `Section`, `PageHeader`, `Card`, `Artifact`, `Button` (primary teal fill with `#0A0F1A` text 10.29:1, secondary outlined, quiet text), `Stat`, `StatusPill` (status color plus icon plus label), `Eyebrow`, `DataTable` (right-aligned numerics, sticky first column, scroll fade), `SyntheticTag`.
- Primary action fill retires `bg-navy text-white` (3.74:1). All primary buttons become `bg-teal text-bg`. The `--color-navy` alias stays in place until the last page task removes its final consumer, then PK-84 deletes it and corrects `brand/PALETTE.md` line 55 (white on `#0D9488` is 3.74:1, large-text AA only).

### 6.5 Dark theme discipline

- The dark tokens in `brand/PALETTE.md` are the only colors. Computed contrast on canvas / surface: text `#E9F0F8` 16.68 / 15.16; muted `#8EA3BD` 7.41 / 6.73; teal `#2DD4BF` 10.29 / 9.35; coral `#FF6B54` 6.83 / 6.20; green `#34D399` 9.97 / 9.05; amber `#F0B34A` 10.26 / 9.33. All pass AA. Teal fill with `#0A0F1A` text is 10.29.
- Status colors: coral = leakage or gap to win point; green = realization or within policy; amber = governance flag or pending; each with an icon and a word. Never on chrome, headings, dots or glows that carry no state. The hero word "nothing." goes to foreground tone; the one coral on the hero is the number itself, labelled "Gap to segment win point".
- Light theme: not planned. If wanted (decision D-R3) it would use the canonical light table in PALETTE.md and costs about 3 extra days (PK-85); not in the base total.
- Document in PALETTE.md one clarification (PK-75, `brand/**`): the control-border rule and the corrected `--color-navy` note. No hex changes.

### 6.6 Immersion, honestly

All five ship inside the five-section landing shape; none adds a claim.

1. **The decision record render (hero artifact).** A static server-rendered component built from one synthetic deal in `sample-fallback.json` (an `OPP-` id, segment, list value, requested discount, the segment's reference band, the band's win rate with its confidence interval, the method label "support floor, correlational", `evidence_version`, and a log row "recorded by a human"). It shows the real fields the product records (`DecisionControl`, `DecisionLog` already define them). Account names in the snapshot are synthetic company-like strings (for example "Lattice AI Corp."); the render shows the opportunity id and segment, not the name, so it cannot be mistaken for a customer logo. Caption: "Synthetic sample deal. Real engine output."
2. **A scroll-driven walk through one exception** (replaces section 2's stats widget; same section slot, so still five sections). Four steps in a sticky two-column layout at `lg` and above: Request (the AE asks for 40% on a 537K Enterprise deal), Evidence (band win rates with the CI, the segment reference, the closest comparable won and lost deals), Decision (Accept, trade or override; a human picks, the log row is written), Outcome (what the synthetic book recorded: won or lost, realized price). The left column scrolls through step copy; the right artifact transitions between states. Without JS, or below `lg`, or under `prefers-reduced-motion`, all four steps render stacked and fully visible (the same safe-by-default pattern `Reveal.tsx` adopted after 2026-09-27). Built with `framer-motion` (already shipped) or CSS `animation-timeline: view()` with a feature-query fallback; no new dependency. Wording must say the decision step is "what the log records", never "the product decides". The walk states that "outcome" is the synthetic book's recorded result.
3. **Hero composition.** At `lg`, copy left and the Artifact right, both above the fold at 1280x720; one number (the gap) as a `Figure` inside the artifact header, not floating below the headline. Under `lg` the artifact stacks below the CTA, partially visible. Hero height drops from `100svh` to content height so the first product visual is above the fold.
4. **One interactive element that uses real numbers: the win-rate by band probe.** A slider or segmented control over the six discount bands on the sample book, showing win rate, confidence interval and where the band sits against the win point, read from `win_rate_by_band` and `reference_discount.band_win_rate_ci`. It is a lookup of engine outputs on the synthetic book, not a forecast, and says so. This is the landing's equivalent of the calculator and calls no API, so `force-static` holds. If the founder later wants a true live call, the proxy would need to expose a demo recommend route; that is a backend decision and not in this plan.
5. **Restrained motion.** Keep: a single count-up for the one number, bars drawing once, the walk's step transitions, 120ms hover states. Remove: `pk-card-3d` tilt, `pk-upside-glow` and `pk-headline-accent` infinite pulses, the three scroll-linked aurora layers. Replace the aurora with one static radial spotlight behind the artifact (pure CSS, no JS) and, optionally, one CSS-only slow drift on the landing hero. `ScrollProgress` stays on long-form routes only (blog, trust, methodology). All motion under `@media (prefers-reduced-motion: reduce)` becomes static; the existing `reveal.test.tsx` pattern pins that.

Out of scope on purpose: video, 3D or WebGL, stock imagery, illustrated people, logos, testimonials, customer counts, "trusted by", animated AI sparkle, chat-bubble product mocks that imply the LLM computes numbers.

### 6.7 Page treatments (summary; detail in the task acceptance)

| Page | Treatment |
|---|---|
| Landing | Hero with Artifact, decision walk, the band probe, "one record, three views" as three tabs or a row rendering the same record three ways (Deal Desk, Pricing, Finance), boundary strip as a two-column "will / will not" table, closing CTA reworded without "cohort" |
| Sample | Chart-led: win-rate-by-band chart first, then KPI strip, gate as a blurred real preview of the locked sections with the form beside it |
| Calculator | Promote in nav; result card becomes the Artifact tier; inputs move into a sticky left panel at `lg` |
| Pricing | Two tiers side by side (Diagnostic, Operate) at 1 row with larger copy; "Data expansion" becomes a quiet roadmap line below with no CTA; scenarios block labelled illustrative or fed from the snapshot; ROI block recast as "your numbers" |
| Methodology | Method first (how the win point, confidence band and "insufficient data" work, rendered from the sample), bibliography second |
| Trust and legal | Shared `LegalLayout`: sticky table of contents at `lg`, at-a-glance summary table with status pills (live, in progress, not yet), body text unchanged |
| Contact | One primary email action, template in a collapsible, "what happens next" as a three-step row |
| Login | Two-panel at `lg`: left explains what is behind the code (workspace, evidence, decision log) with a small Artifact thumbnail, right the form; single column on mobile; h1; noindex |
| App (diagnostic, guidance, upload, competitor-watch) | App shell with a section rail, one `DataTable`, Recharts theme from tokens in one file, decision log promoted above model quality |
| /crm | Split `SalesforceWorkspace.tsx` into readable components, replace raw amber classes with tokens; sequenced after PK-49 |

### 6.8 Navigation and footer information architecture

- **Header (desktop):** wordmark, then Product (anchor to the walk), Sample, Calculator, Pricing, Trust; right side: Customer login (quiet) and a primary "Talk to us" button to `/contact`. Methodology, Blog and Brand leave the header.
- **Header (mobile):** keep the `<details>` menu (works without JS), full-height sheet, 48px rows, "Talk to us" as a pinned primary row.
- **Rename "Live sample" to "Sample".** It is a bundled snapshot with a live-engine path, not a live customer environment.
- **Footer:** four labelled columns on a 12-column grid.
  - Product: Sample, Calculator, Pricing, Methodology.
  - Company: Contact, Blog (if kept), Brand.
  - Trust and legal: Trust, Privacy, Terms, Subprocessors, Licenses.
  - Customers: Login, Salesforce workspace, Run it on your data.
  - Above the columns, a one-line global disclosure: "Every figure on this site comes from a synthetic 2,000-deal sample, not customer data." Below: wordmark, year, "Pre-seed" is not stated (decision-free: do not add status claims).
- Workspace and Your-data links lead to the access-code wall; label them "Customers" so a visitor is not surprised.

### 6.9 Performance and quality budgets

Measured on a Vercel preview of each PR, Lighthouse 12 mobile (simulated slow 4G, 4x CPU) and desktop. Baseline recorded by PK-75 first; where the baseline is already better, hold it.

| Route class | Performance | Accessibility | Best practices | SEO | Other |
|---|---|---|---|---|---|
| Landing, pricing, methodology, calculator, contact | mobile at or above 90, desktop at or above 95 | at or above 95 | at or above 95 | at or above 95 | LCP at or below 2.5s, CLS at or below 0.05, TBT at or below 200ms |
| Trust and legal (static, no chrome effects) | at or above 95 | 100 target, at or above 98 | at or above 95 | at or above 95 | zero framer-motion on these routes |
| Sample (dynamic) | mobile at or above 80 | at or above 95 | at or above 95 | at or above 90 | LCP at or below 3.0s |
| App routes (diagnostic, guidance, upload, crm) | mobile at or above 70 | at or above 95 | at or above 95 | not applicable (noindex) | Recharts only loaded on routes that render charts |

- No new runtime dependencies in this plan. `framer-motion` (12.x), `recharts` (3.x) and Tailwind 4 are already shipped. Recharts must not appear in the marketing bundle; marketing charts are inline SVG or CSS. Lighthouse itself is run with `npx` from outside the repo, not added to `package.json`.
- Fonts: Inter only, `display: swap`, subset latin. No second face.
- Images: none beyond SVG; the artifact is HTML and CSS, so there is no image weight and no layout shift.
- Landing first-load JS must not exceed the PK-75 baseline by more than 15 KB gzipped.
- Reduced motion, keyboard focus (the existing teal focus ring stays), and heading order (one h1, no skipped levels) are checked on every page.

## 7. What must not change

- **The palette.** Dark tokens and canonical hex exactly as in `brand/PALETTE.md`. No new hue. Status colors carry state only and always pair with a label or icon.
- **The honesty rules.** No users, customers, pilots, logos, testimonials, counts or traction. Every number comes from the synthetic sample and is labelled where it appears. No autonomous price-setting: the walk shows a human decision step. No "learns from your data" without the cold-start limit. No CRM proxy called margin; the billing-or-ERP disclosure stays. Design doc 2026-11-06 section 4 rules 1 to 7 apply.
- **The five-section landing.** Hero, product, roles, boundary, close. The redesign changes how they look and adds immersion inside them. It adds no section, no claim, no stat.
- **The trust and privacy facts PK-6 corrected.** The wording on `/trust`, `/privacy`, `/subprocessors`, `/licenses` is frozen; PK-82 restyles and restructures only, and a text-diff test enforces it.
- **No em dashes** in any copy; a test scans the rendered text of every route.
- **Static pages stay static** (`force-static` where used) and the legal routes stay free of motion chrome.
- **Existing tests stay green:** `landing-page.test.ts` (no em dash, no "system of record", number read from the snapshot), `diagnostic-mobile-overflow.test.ts`, `reveal.test.tsx`.

## 8. Risks

- **Conflicts on shared hot files.** `layout.tsx`, `globals.css`, `Nav.tsx`, `Footer.tsx` are touched only by PK-75, then PK-84 for the final token cleanup, with nothing in between. Page tasks add component-local styles or `ui/` primitives, never edit `globals.css`.
- **Connector plan overlap.** `pricing/page.tsx` is also owned by PK-52, PK-62, PK-69 (name HubSpot, Stripe, Chargebee) and `privacy`, `trust` by the same tasks and PK-6. `crm/page.tsx` and `SalesforceWorkspace.tsx` belong to PK-49. PK-26 owns `web/src/lib/salesforce-*.ts` and renames the web canonical type; the redesign edits no `web/src/lib` connector or Salesforce path and reads `lib/api.ts` types only. The proposed order puts pricing and legal restyle first and asks PK-52 to take PK-77 and PK-82 as dependencies.
- **Walk complexity.** Scroll-driven sticky UIs fail on iOS Safari and in-app browsers. The stacked fallback is the default render; the enhancement arms only after mount when `matchMedia('(min-width: 1024px)')` and motion are allowed.
- **Copy drift.** A restyle tempts rewriting. The rule: page tasks may delete or soften claims listed in section 3 and may add disclosure, never add claims. Reviewers check the diff of extracted text.
- **No browser in this audit.** Hierarchy and density findings should be spot-checked against screenshots in PK-75's baseline before the page tasks start; any finding that does not reproduce is dropped.

## 9. Founder decisions (only where they change what gets built)

See the task file for the same list with defaults. They are D-R1 (app screens in scope now), D-R2 (/crm restyle timing), D-R3 (light theme), D-R4 (blog), D-R5 (landing headline wording), D-R6 (pricing figures and "typically").
