---
title: Proposed tasks, site and app redesign
created: 2026-11-09
updated: 2026-11-09
tags: [tasks, proposal, web, redesign]
status: approved-for-entry
source: docs/design/2026-11-09-site-redesign.md
---

# Proposed tasks: site and app redesign

**Status 2026-11-09: approved-for-entry.** PK-75 to PK-84 are on the board in BACKLOG, owner web-engineer, none assigned. PK-85 is not entered. Founder questions carry lead defaults, founder may override: **D-R1** yes, `/diagnostic`, `/guidance`, `/upload`, `/competitor-watch` in scope (PK-81), `/crm` deferred; **D-R2** `/crm` restyle after PK-49 (PK-83 depends on PK-49); **D-R3** no light theme, PK-85 not entered; **D-R4** blog in the footer only; **D-R5** soften the hero to a claim the synthetic data supports and replace "Design-partner cohort" with wording that implies no cohort, exact copy chosen by PK-76 and checked against the evidence boundary; **D-R6** "We expect" wording, no "open code" claim (no public repository holds the engine, checked 2026-11-09, see "Changes on entry"), keep the one-business-day reply promise. A founder override changes acceptance lines on PK-75, PK-76, PK-77, PK-79, PK-81 or PK-83 before they are assigned. Changes made on entry are listed under "Changes on entry" at the end.

Original note: nothing here entered `project_state.json` until approval. Ids continue the board after PK-74. Owner is web-engineer on every task; a qa-engineer or code-reviewer marks the acceptance lines. "Gate" names a founder decision (design doc section 9, restated at the end of this file).

**Total: 10 tasks, 25 days, plus one conditional task (PK-85, 3 days, only if D-R3 is yes).**

## Notes on the board

- **Hot files.** `web/src/app/layout.tsx`, `globals.css`, `Nav.tsx`, `Footer.tsx` (and `ChromeEffects.tsx`, `AuroraBackground.tsx`, `ScrollProgress.tsx`, `Reveal.tsx`, `CountUp.tsx`) are owned by **PK-75 only**, then by **PK-84 only** for the final token cleanup. No task in between edits them. Page tasks consume tokens and `web/src/components/ui/**` and never edit `globals.css`.
- **PK-6 (PR 77, in review)** owns `web/src/app/privacy`, `trust`, `subprocessors`, `licenses`. PK-82 depends on it and may not start before it merges.
- **PK-26 (planned)** owns `web/src/lib/salesforce-*.ts` and renames the web canonical type. No redesign task edits any `web/src/lib` Salesforce or connector path; page tasks rebase after PK-26 merges and read `lib/api.ts` types without editing them.
- **Connector plan** (`TASKS-connectors-proposed.md`) claims: PK-42 and PK-43 (`web/src/lib/connector-*.ts`, `gate.ts`, `store.ts`), PK-47, PK-48, PK-57, PK-58, PK-64, PK-65 (`web/src/lib/*-sync.ts`, `web/src/app/api/**`), **PK-49** (`web/src/app/crm/page.tsx`, `SalesforceWorkspace.tsx`, `ConnectorWorkspace.tsx`), PK-59 and PK-66 (`ConnectorWorkspace.tsx` and setup panels), and **PK-52, PK-62, PK-69** (`web/src/app/privacy`, `trust`, `pricing/page.tsx`, `web/test/claims-connectors.test.ts`). The redesign touches none of the lib or api paths. It overlaps on `pricing/page.tsx` and the legal pages, so **PK-52 should take PK-77 and PK-82 as dependencies**; it overlaps on `/crm`, so **PK-83 waits for PK-49**.
- **Existing tests that must stay green:** `web/test/landing-page.test.ts`, `diagnostic-mobile-overflow.test.ts`, `reveal.test.tsx`, `lead-form.test.ts`, `decision-control.test.ts`, `guidance-client.test.ts`, `chat-panel.test.ts`.
- Read the relevant guide in `web/node_modules/next/dist/docs/` before writing code (web/AGENTS.md): metadata (`generate-metadata.md`, title template applies to child segments only), `layout.md`, `loading.md`, `template.md`.

## Common gates (every task; the row ids below refer to these)

A reviewer marks each true or false on the PR.

- **G1 Lint and types.** `npm run lint`, `npx tsc --noEmit`, `npm test` and `npm run build` in `web/` are green, results pasted in the PR. No new runtime dependency in `web/package.json`.
- **G2 No new claims.** The extracted visible text of every changed route is diffed before and after; every added sentence is either a label (synthetic, illustrative), a limit, or navigation. Any removed or softened claim is listed in the PR from the audit (design doc section 3). No customers, users, pilots, logos, testimonials, traction numbers or "trusted by". Every figure comes from `src/data/sample-fallback.json` or arithmetic on it, and shows a `SyntheticTag` where it appears.
- **G3 Palette unchanged.** `git diff` shows no change to any color value in `globals.css` or `brand/PALETTE.md` except the documented clarifications named in PK-75; no new hex or raw Tailwind palette color (`amber-300`, `emerald-*`) in the changed files (grep in the PR).
- **G4 Contrast measured.** Text and control contrast on the changed routes is computed from the token values and listed in the PR: body text 4.5:1 or higher, large text and UI component borders 3:1 or higher. Status colors always carry a label or icon.
- **G5 Mobile 375.** Each changed route is checked at 375x667 and 390x844 (screenshots attached or a Playwright run); no horizontal page scroll; primary CTA visible without scrolling on the landing and contact pages; tap targets at least 44px; body text at least 16px on marketing pages, 14px in app tables, nothing below 12px.
- **G6 Reduced motion.** With `prefers-reduced-motion: reduce` there is no animation, no scroll-linked transform and no infinite loop on the changed routes; content is fully visible with JavaScript disabled (verified, not assumed).
- **G7 Lighthouse.** Scores on the preview URL meet the table in design doc section 6.9 for the route class, mobile and desktop, pasted per route. A score below target blocks merge unless the PR names the cause and the lead waives it in writing.
- **G8 Metadata.** Each changed route exports a unique title with no " · Pricekeel" suffix (the layout template adds it), a description of 70 to 160 characters, a canonical URL and matching `openGraph` and `twitter` fields via `pageMetadata()` (from PK-75); gated routes are `noindex`.
- **G9 No em dashes** in any copy, comments excluded; en dashes are not used for ranges ("10 to 100M").
- **G10 Scope.** `git diff --name-only` shows only the paths in Owns.

## Wave 0: design system and chrome (3 days)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-75 | Build the design system, tokens, shared UI primitives and site chrome | web-engineer | none | `web/src/app/globals.css`, `web/src/app/layout.tsx`, `web/src/components/Nav.tsx`, `web/src/components/Footer.tsx`, `web/src/components/ChromeEffects.tsx`, `web/src/components/AuroraBackground.tsx`, `web/src/components/ScrollProgress.tsx`, `web/src/components/Reveal.tsx`, `web/src/components/CountUp.tsx`, `web/src/components/ui/**`, `web/src/lib/site-nav.ts`, `web/src/lib/page-metadata.ts`, `brand/PALETTE.md`, `web/test/design-system.test.ts`, `web/test/chrome.test.tsx`, `web/test/page-metadata.test.ts` | 3 | none |

Acceptance:
- **PK-75:**
  - G1, G3, G4, G6, G9, G10 true.
  - A baseline is committed to the PR description before any change: Lighthouse mobile and desktop for `/`, `/pricing`, `/calculator`, `/sample`, `/trust`, `/login`, and a 375px screenshot of every public route.
  - `globals.css` defines the type scale of design doc 6.2, the spacing steps of 6.3 and the surfaces of 6.4 as `@theme` tokens or component classes; no hex value in `@theme` changes.
  - `web/src/components/ui/` exports `Section`, `PageHeader`, `Card`, `Artifact`, `Button`, `Stat`, `StatusPill`, `Eyebrow`, `DataTable`, `SyntheticTag`, each with a render test; `Button` primary is `bg-teal` with `text-bg` (10.29:1 computed in a test); `StatusPill` cannot render without a label and an icon (type-enforced and tested); `SyntheticTag` is required by `Stat` when a `source="sample"` prop is set.
  - Form controls use the Slate `#5B6B7B` border on inset; its contrast against `#0D1422` and `#111A2B` is computed in `design-system.test.ts` and is at least 3:1 (if it is not, the PR says so and proposes a derived tint, not a new hue).
  - The `.pk-card-3d` hover tilt, `.pk-upside-glow` and `.pk-headline-accent` infinite animations and the scroll-linked parallax in `AuroraBackground.tsx` are no longer applied by chrome; the classes may remain defined until PK-84 removes them so unmigrated pages do not break. The aurora becomes one static spotlight, and `ScrollProgress` renders only on `/blog/*`, `/methodology`, `/trust`.
  - `Nav.tsx`: links Product, Sample, Calculator, Pricing, Trust; a quiet Customer login; a primary "Talk to us" to `/contact`; "Live sample" is renamed "Sample"; mobile keeps the `<details>` menu with 48px rows and works with JavaScript disabled. `aria-current` is correct on every route.
  - `Footer.tsx`: four labelled columns (Product, Company, Trust and legal, Customers) built from `site-nav.ts`, every existing link still present, one global disclosure line "Every figure on this site comes from a synthetic 2,000-deal sample, not customer data.", footer links at least 44px tall on mobile.
  - `pageMetadata({ title, description, path, noindex? })` exists and is unit-tested: it never appends the suffix, sets `alternates.canonical`, `openGraph.url`, `openGraph.title`, `twitter`.
  - `layout.tsx` keeps `title.template` and `title.default` and the Vercel Analytics gate unchanged, and adds a skip-to-content link and a `<main id>` target contract documented for page tasks.
  - `brand/PALETTE.md` gains exactly two clarifications: the control-border rule, and the correction that white on `#0D9488` is 3.74:1 (large-text AA only) so action fills use dark text. No hex changes.
  - Chrome adds no more than 15 KB gzipped of first-load JS over the recorded baseline.

## Wave 1: marketing pages, parallel after PK-75 (13.5 days)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-76 | Redesign the landing page around the decision record and a scroll-driven walk | web-engineer | PK-75 | `web/src/app/page.tsx`, `web/src/app/opengraph-image.tsx`, `web/src/components/HeroHeadline.tsx`, `web/src/components/DiagnosticPreview.tsx`, `web/src/components/WhatYouGet.tsx`, `web/src/components/TrustBoundaryStrip.tsx`, `web/src/components/landing/**`, `web/src/lib/landing-sample.ts`, `web/test/landing-page.test.ts`, `web/test/landing-walk.test.tsx` | 4 | D-R5 |
| PK-77 | Redesign the pricing page and clear its claims that exceed the evidence | web-engineer | PK-75 | `web/src/app/pricing/page.tsx`, `web/test/pricing-page.test.ts` | 2 | D-R6 |
| PK-78 | Redesign methodology and contact, and show the method on the sample | web-engineer | PK-75 | `web/src/app/methodology/page.tsx`, `web/src/app/contact/page.tsx`, `web/src/components/methodology/**`, `web/test/methodology-page.test.ts` | 2 | none |
| PK-79 | Restyle the calculator, blog, 404 and error pages and promote the calculator | web-engineer | PK-75 | `web/src/app/calculator/page.tsx`, `web/src/components/LeakageCalculator.tsx`, `web/src/components/LeakageBars.tsx`, `web/src/app/blog/**`, `web/src/app/not-found.tsx`, `web/src/app/error.tsx`, `web/src/app/brand/page.tsx`, `web/test/calculator-page.test.ts` | 1.5 | D-R4 |
| PK-80 | Redesign the sample page, the lead gate and the login page | web-engineer | PK-75 | `web/src/app/sample/page.tsx`, `web/src/app/login/page.tsx`, `web/src/app/login/layout.tsx`, `web/src/components/LeadForm.tsx`, `web/src/components/MagicLinkForm.tsx`, `web/src/components/Summary.tsx`, `web/test/lead-form.test.ts`, `web/test/login-page.test.tsx` | 2.5 | none |

Acceptance:
- **PK-76:**
  - G1 to G10 true.
  - Landing keeps exactly five sections in the order hero, product, roles, boundary, close; `landing-page.test.ts` is extended to assert five top-level `<section>` elements, one h1, no em dash, no "system of record", and that the hero number equals `SAMPLE.leakage.excess_vs_segment_reference_won` (`$8,946,770` in the current snapshot, shown as `$8.9M`).
  - The hero number is no larger than the H1 or Display size, carries the label "Gap to segment win point" with a status icon, and its caption contains the word "synthetic". The word "nothing." is no longer coral and has no glow; no coral or amber is used for chrome or dots.
  - At 1280x720 the first product visual (the decision record Artifact) is visible above the fold; the hero is no longer `min-h-[100svh]`.
  - The decision record Artifact renders one deal chosen deterministically from `sample-fallback.json` (rule written in `landing-sample.ts` and tested), shows the opportunity id and segment and not an account name, shows requested discount, segment reference band, band win rate with its confidence interval, the method label, and `evidence_version`, and is tagged "Synthetic sample deal. Real engine output."
  - The walk has four steps (Request, Evidence, Decision, Outcome). The Decision step shows a human choosing and a log row; no copy says or implies the product sets or approves a price. The Outcome step says it is the outcome the synthetic book recorded. Below `lg`, with JavaScript off, or under reduced motion, the four steps render stacked and fully visible (tested by rendering without the arming effect).
  - The band probe reads `win_rate_by_band` and `reference_discount.band_win_rate_ci` only, calls no API, and the route is still `force-static`.
  - "Design-partner cohort" is replaced by wording that implies no existing cohort; the hero line "wins you nothing" is changed only if the founder chose so in D-R5; `DiagnosticPreview.tsx:149` is rewritten to describe the synthetic book ("In this synthetic book, win rate stops improving past the win point") rather than assert causation.
  - No faux browser traffic-light dots remain.
  - The per-route `opengraph-image.tsx` text matches the landing headline decision and adds no claim.
  - Lighthouse mobile performance at or above 90, accessibility at or above 95, LCP at or below 2.5s, CLS at or below 0.05 on the preview.
- **PK-77:**
  - G1 to G10 true.
  - Two tiers (Diagnostic, Operate) render side by side in a roomy layout; "Data expansion" is a roadmap line with no CTA button and no card styling of a tier; body copy is 16px.
  - Removed: "Most subscribers will clear all three"; "Worth the subscription at the $50M ARR tier on its own". The Monday scenarios either read their figures from the snapshot with a `SyntheticTag`, or carry an "Illustrative, not customer data" label on the block. The three ROI thresholds are reframed as the reader's own assumptions, labelled as such.
  - "Typically start in the low five figures" and "open code" are handled per the founder answer to D-R6 and the repository fact check, and the PR states which.
  - Title renders "Pricing · Pricekeel" exactly once.
  - Plain `<a href="/contact">` elements are `Link`.
  - PK-52 is updated to list PK-77 as a dependency.
- **PK-78:**
  - G1 to G10 true.
  - Methodology leads with how the engine finds the win point, what the confidence band means, and when it returns "insufficient data", rendered from `reference_discount` in the snapshot with a `SyntheticTag`; the bibliography follows.
  - "grounded in a published framework, not invented math" is reworded to "informed by"; no source is added or removed and every link still resolves (checked by a link test or manual list in the PR).
  - Contact has one primary email action, the template inside a `<details>`, and "what happens next" as a three-step row; the founder email and LinkedIn fallbacks are unchanged; claims about reply time are unchanged unless the founder says otherwise.
- **PK-79:**
  - G1 to G10 true.
  - The calculator remains `force-static`, its numbers and formulas are unchanged (existing `web/test` leakage tests, if any, and a new known-answer test for three inputs pass), and the result card uses the Artifact surface. "No data leaves your browser" stays true (no network call added; verified in the PR).
  - Blog index and post use the shared prose and measure rules; blog stays in the footer, and stays in the header only if D-R4 says so.
  - `not-found.tsx` and `error.tsx` use `Button`; `error.tsx` still resets.
- **PK-80:**
  - G1 to G10 true.
  - `/sample` has its own title and description; the win-rate-by-band chart leads; the lead gate shows a real, blurred preview of the locked sections beside the form; the "Cached sample" disclosure is preserved verbatim.
  - `/login` has a sibling `layout.tsx` exporting metadata with `robots: { index: false }`, exactly one h1, a two-panel layout at `lg` and a single column below, and a short factual line on what the code unlocks (workspace, competitor context, upload) with no new claim.
  - Primary buttons in `LeadForm`, `MagicLinkForm` and login are `bg-teal text-bg`; no `bg-navy text-white` remains in the files this task owns; input borders meet 3:1.
  - `lead-form.test.ts` stays green; form behavior, field names, endpoints and error copy are unchanged (diffed).

## Wave 2: legal, app screens (6 days)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-81 | Restyle diagnostic, guidance, upload and competitor-watch onto the shared system | web-engineer | PK-75, PK-80 | `web/src/app/diagnostic/page.tsx`, `web/src/app/guidance/page.tsx`, `web/src/app/upload/page.tsx`, `web/src/app/competitor-watch/page.tsx`, `web/src/components/charts/**`, `web/src/components/GuidanceClient.tsx`, `web/src/components/DecisionLog.tsx`, `web/src/components/DecisionControl.tsx`, `web/src/components/UploadClient.tsx`, `web/src/components/UploadPrivacyCallout.tsx`, `web/src/components/PageGuide.tsx`, `web/src/components/NextStep.tsx`, `web/src/components/NextActionsBlock.tsx`, `web/src/components/ApiError.tsx`, `web/src/components/CompetitorContextPanel.tsx`, `web/src/components/app/**`, `web/test/diagnostic-mobile-overflow.test.ts`, `web/test/guidance-client.test.ts`, `web/test/decision-control.test.ts` | 4 | D-R1 |
| PK-82 | Give trust, privacy, terms, subprocessors and licenses one legal layout, wording unchanged | web-engineer | PK-75, PK-6 | `web/src/app/trust/page.tsx`, `web/src/app/privacy/page.tsx`, `web/src/app/terms/page.tsx`, `web/src/app/subprocessors/page.tsx`, `web/src/app/licenses/page.tsx`, `web/src/components/legal/**`, `web/test/legal-text-frozen.test.ts` | 2 | none |

Acceptance:
- **PK-81 (starts only if D-R1 is yes):**
  - G1 to G10 true (G8: `noindex` on all four; each has its own title).
  - `ChatPanel.tsx` is not edited (class-level token drift there is a follow-up, not this task).
  - Every table uses `DataTable` with right-aligned numerics, a sticky first column and a scroll-edge fade at narrow widths, inside the existing `overflow-x-auto` wrapper; `diagnostic-mobile-overflow.test.ts` (390px) stays green and a 375px assertion is added.
  - One Recharts theme module reads colors from the tokens; no hex literal in a chart file.
  - `/diagnostic` gets a section rail (sticky at `lg`, a select on mobile); `/guidance` shows the decision log above model quality; the builder-facing text "← lead with this" is removed from the user view.
  - `guidance/page.tsx` copy "The model learns from your closed deals" gains the limit that thin segments return "insufficient data" (a limit added, no claim added); no other copy changes.
  - Buttons: no `bg-navy text-white` remains in owned files; the optional-columns string on `/upload` becomes a list.
  - No behavior change in `DecisionControl`, `GuidanceClient`, `UploadClient` (existing tests unchanged and green).
- **PK-82:**
  - G1, G3 to G10 true; G2 is replaced by a stronger rule: `legal-text-frozen.test.ts` extracts the visible text of the five pages from the PK-6 merge commit as a fixture and fails on any difference in wording; only headings may gain ids and the layout may add a table of contents and the at-a-glance status table built from existing statements.
  - Shared `LegalLayout` provides a sticky table of contents at `lg`, `max-w-3xl` measure, 16px body, no motion chrome (the four legal routes stay free of framer-motion; verified by bundle check).
  - Trust gets an at-a-glance table whose status pills (live, in progress, not yet) are derived only from statements already on the page ("Pre-SOC 2 · controls live", "Error tracking is in implementation", and so on); no new status is invented.
  - The literal placeholder `[security@pricekeel.com]` can no longer render: the fallback is the founder address used by `/contact`, or the build fails if the env var is missing in production (the PR states which; this is a rendering fix, not a fact change; `trust/page.tsx` fact text is untouched).
  - The `Updated` date is whatever PK-6 left; this task does not change it.
  - Titles render once with the suffix; trust, privacy, terms, subprocessors, licenses each have a description.

## Wave 3: workspace and close (4 days)

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-83 | Split and restyle the Salesforce workspace into readable components | web-engineer | PK-75, PK-49 | `web/src/app/crm/page.tsx`, `web/src/components/SalesforceWorkspace.tsx`, `web/src/components/workspace/**`, `web/test/salesforce-workspace.test.ts` | 2.5 | D-R1, D-R2 |
| PK-84 | Audit the whole site, remove dead styles, and pin the budgets in tests | web-engineer | PK-76, PK-77, PK-78, PK-79, PK-80, PK-81, PK-82 | `web/src/app/globals.css`, `web/test/site-audit.test.ts`, `web/scripts/lighthouse-budget.mjs`, `brand/PALETTE.md` | 1.5 | none |

Acceptance:
- **PK-83:**
  - G1 to G10 true; `crm` is `noindex`.
  - Every render function in `SalesforceWorkspace.tsx` is split so no source line exceeds 140 characters; the file is under 250 lines and the pieces live in `components/workspace/`.
  - Behavior is unchanged: `salesforce-workspace.test.ts` and `salesforce-workspace-route.test.ts` pass untouched, the accept, override, approve, reject, writeback and disconnect paths call the same endpoints with the same bodies (diffed), the insufficient-data branch still shows no recommended discount.
  - Raw `amber-*` classes are replaced by `text-amber`/`border-amber` tokens with a label or icon; the h1 uses `PageHeader`.
  - If PK-49 changed the file, this task starts from PK-49's merged version and keeps its source switcher.
- **PK-84:**
  - G1 to G10 true.
  - `site-audit.test.ts` renders every static route and asserts: no title contains " · Pricekeel · Pricekeel", every public route has a unique title and a 70 to 160 character description, every gated route is `noindex`, exactly one h1 per page, no heading level skipped, no em dash in rendered text, no text node below 12px class (`text-[10px]`, `text-[11px]` absent), no `bg-navy`, no raw Tailwind palette colors.
  - `.pk-card-3d`, `.pk-upside-glow`, `.pk-headline-accent`, `.pk-aurora-layer` and the `--color-navy` alias are deleted from `globals.css` only after a grep shows zero uses; if any remain they are listed with owners.
  - `brand/PALETTE.md` correction from PK-75 is complete and the dark-theme table still matches `globals.css` (tested by comparing the hex values).
  - `web/scripts/lighthouse-budget.mjs` runs Lighthouse via `npx` (not a dependency) against a URL and fails when a budget in design doc 6.9 is missed; the final numbers for all routes are pasted in the PR.
  - A 375px screenshot of every route, public and gated (with a dev unlock), is attached; the PR lists any residual issue as a follow-up with an owner rather than closing silently.
  - Cross-check against `vault/Competitive/2026-08-01-salesforce-market-need-assessment.md` and the design doc section 4 rules, recorded line by line in the PR.

## Conditional

| Id | Title | Owner | Deps | Owns | Days | Gate |
|---|---|---|---|---|---|---|
| PK-85 | Add a light theme from the canonical palette | web-engineer | PK-84 | `web/src/app/globals.css`, `web/src/app/layout.tsx`, `web/src/components/ThemeToggle.tsx`, `brand/PALETTE.md`, `web/test/theme.test.tsx` | 3 | D-R3 yes |

Acceptance:
- **PK-85 (not counted in the 25 days):**
  - Light tokens use the canonical hex of `brand/PALETTE.md` exactly (Paper `#F7FAFC`, White, Mist, Deep Ink, Slate, Keel Navy, Waterline Teal and status colors); contrast is measured for every text and control pairing (Waterline Teal `#17B8A6` as text on White is not AA and must not be used for text).
  - Theme follows `prefers-color-scheme`, a toggle persists the choice in a cookie with no flash of the wrong theme, and the default stays dark.
  - G1 to G10 true on every route in both themes.

## Total and order

| Task | Days | Cumulative |
|---|---|---|
| PK-75 design system and chrome | 3 | 3 |
| PK-76 landing | 4 | 7 |
| PK-77 pricing | 2 | 9 |
| PK-80 sample and login | 2.5 | 11.5 |
| PK-78 methodology and contact | 2 | 13.5 |
| PK-79 calculator, blog, 404, error | 1.5 | 15 |
| PK-82 legal layout | 2 | 17 |
| PK-81 app screens (if D-R1) | 4 | 21 |
| PK-83 workspace (after PK-49, if D-R1 and D-R2) | 2.5 | 23.5 |
| PK-84 site audit and cleanup | 1.5 | 25 |

**Total 10 tasks, 25 days.** Without D-R1 (app screens deferred), PK-81 and PK-83 drop out: 8 tasks, 18.5 days. If D-R1 is yes but PK-49 is not scheduled soon, drop PK-83 only: 9 tasks, 22.5 days.

### Order under the two-slot cap alongside connector work

The cap is two concurrent engineering tasks across the whole board. The connector critical path is mostly backend, data and ai tasks (PK-23 to PK-40, PK-41, PK-46) and uses one slot most of the time; web connector tasks (PK-42, PK-43, PK-47 onward) wait on PK-41 and PK-44 and arrive later. Proposed use of the slots:

1. **Slot A is the redesign slot, slot B stays with the connector path.** PK-75 first, alone (3 days), so no page task starts against moving chrome.
2. **After PK-75, run the prospect-facing surfaces in this order:** PK-76 landing (4), PK-77 pricing (2), PK-80 sample and login (2.5), PK-78 methodology and contact (2), PK-79 calculator and blog (1.5). That is 12 days and finishes everything a prospect sees. If slot B is idle at any point (connector work waiting on a gate), run PK-77 and PK-80 in parallel with PK-76: three of these five can overlap because they own disjoint files.
3. **PK-82 legal layout** after PK-6 merges; it can run any time from the second wave on and does not conflict with anything except PK-52, which waits for it.
4. **PK-81 app screens** next if the founder says yes to D-R1. It does not touch connector paths.
5. **PK-83 workspace** only after PK-49 merges; **PK-84** last.
6. **Wall clock.** One slot for the whole plan: about 25 working days. Both slots free after PK-75: about 17 working days (slot A: PK-76, PK-78, PK-81, then PK-83; slot B: PK-77, PK-80, PK-79, PK-82; PK-84 after both). Reality will sit between, depending on how long connector web tasks hold slot B. If the founder wants connectors first, PK-75 and the landing, pricing and sample/login trio (11.5 days) are the smallest set that changes what a prospect sees.
7. **PK-52, PK-62, PK-69 reordering.** Ask the lead to add PK-77 and PK-82 as dependencies of PK-52, so the later connector copy edits land on the redesigned files, not the reverse.

## Founder decisions (only those that change what gets built)

- **D-R1. Are the app screens behind the login in scope now?** Covers `/diagnostic`, `/guidance`, `/upload`, `/competitor-watch` (PK-81, 4 days) and `/crm` (PK-83, 2.5 days). Recommendation: yes for PK-81, because the sample's unlocked state sends every lead into `/diagnostic` and `/guidance`, so they are part of the marketing funnel; defer PK-83 until PK-49 lands. If no: 18.5 days, and those pages keep the old look next to the new chrome (visible seam).
- **D-R2. `/crm` restyle timing.** Restyle after PK-49 (default, 2.5 days, no conflict) or reorder PK-49 earlier. Changes only the order.
- **D-R3. Is a light theme wanted?** Default no. If yes, PK-85 adds 3 days and the redesign must be checked in both themes. Matters for printing and for buyers who dislike dark UIs, but there is no evidence either way yet.
- **D-R4. Does the blog stay in the header?** Three posts. Default: keep the blog in the footer only and take it out of the primary nav; if the founder plans to publish weekly, put it back. Changes PK-75 nav items and PK-79 scope.
- **D-R5. Landing headline wording.** "Stop giving away price that wins you nothing." In the synthetic sample the 25%+ band still wins 42% of deals against a 68% peak, so "nothing" is stronger than the data. Options: keep, or "Stop giving away price that wins you no more deals." Keep is a founder choice; the design is the same either way. Also confirm replacing "Design-partner cohort" in the closing section.
- **D-R6. Pricing statements.** (a) Keep or remove "Engagements typically start in the low five figures" (no engagements exist yet; recommend "We expect"). (b) Is the diagnostic code actually open or available to customers? The pricing page says "open code". (c) Keep the one-business-day reply promise.

## Changes on entry, 2026-11-09

Entered by pk-lead with one `agentctl add` per task through a subprocess, one `--acceptance` per criterion, test files in owns also passed as `--test`. 10 tasks, PK-75 to PK-84, all BACKLOG, owner web-engineer, dependencies as in the tables above (PK-82 on PK-6 and PK-83 on PK-49 were already in the tables and are on the board).

Claims changed:
- **Glob claims converted to directory claims**, because `agentctl` refuses glob patterns: `web/src/components/ui/**`, `landing/**`, `methodology/**`, `charts/**`, `app/**`, `legal/**`, `workspace/**` and `web/src/app/blog/**` are the directory without `/**`. Same coverage.
- No claim was changed to resolve a collision. A dry run of every new claim against live and backlog claims found only overlaps that dependencies or the sequencing rule below already order: PK-82 against PK-6 (live, `REWORK_REQUIRED` on PR 77; PK-82 depends on PK-6); PK-83 against PK-49 (PK-83 depends on PK-49); PK-75 against PK-84 on `globals.css` and `brand/PALETTE.md` (PK-84 depends on PK-75 through every page task); PK-77 and PK-82 against PK-52, PK-62, PK-69 (sequencing rule below). No overlap with PK-26, PK-42, PK-43, PK-47, PK-48, PK-57, PK-58, PK-64, PK-65 (`web/src/lib` connector and Salesforce files, `web/src/app/api/*`, `web/scripts/revoke-tenant-connections.ts`), nor with PK-24, PK-27, PK-29, PK-31 (non-web paths).

Acceptance changes on the board:
- Common gates are referenced by one line per task ("common gates G1 to G10 in this file are true"), not copied, so the board stays readable; this file is the definition.
- **PK-76** gains two D-R5 lines (hero softened with the snapshot figures quoted in the PR; "Design-partner cohort" replaced with no-cohort wording) and loses the "changed only if the founder chose so" clause.
- **PK-77** gains three D-R6 lines: both "typically start in the low five figures" instances (`pricing/page.tsx:187` and `:395`) become "We expect" wording; the "open code" claim (`:301`) is removed; the one-business-day promise is kept verbatim. Its line "PK-52 is updated to list PK-77 as a dependency" is dropped: an agent cannot edit another task's dependencies, so the lead records it as the sequencing rule below.
- **PK-75** and **PK-79** state the D-R4 default (blog in the footer only). **PK-81** and **PK-83** name D-R1 and D-R2 as lead defaults.
- **PK-82**'s frozen-text fixture is taken from the latest merged commit that touched the legal pages (PK-6's merge commit unless a later task changed them first), so the test is not wrong if the order slips.
- **PK-83** adds `web/test/salesforce-workspace-route.test.ts` as a required regression suite (named in its acceptance, not owned).

D-R6 repository fact (2026-11-09, `gh repo list arokhith1998 --visibility public`): the product repository `arokhith1998/pricing-ai` is private. Public repositories exist under the account, none holds the Pricekeel engine; `adhi-pricing-ai` is a public Next.js portfolio site ("Portfolio variant"), not the diagnostic code. So "open code" is not supportable and is removed.

### Sequencing rule: redesign before connector copy on shared pages

`agentctl add` cannot edit dependencies of tasks already on the board, so this is a lead rule, not a tool gate:

- **PK-52 is not moved to READY or assigned until PK-77 and PK-82 are MERGED.** PK-62 and PK-69 already follow PK-52 by dependency, so they inherit the order. The connector copy edits on `pricing/page.tsx`, `privacy` and `trust` then land on the redesigned files, not the reverse.
- The tool still referees the overlap if the rule is missed: PK-52 claims `web/src/app/privacy`, `web/src/app/trust` and `web/src/app/pricing/page.tsx`, so its assignment is refused while PK-77 or PK-82 holds a live claim, and the reverse.
- If the founder wants PK-52 first, PK-77 and PK-82 start from PK-52's merged version and PK-82's frozen-text fixture comes from that merge.
- PK-12 (competitor-watch copy) and PK-14 (GuidanceClient and diagnostic copy) are READY and touch files PK-81 owns. Run them before PK-81; `assign` refuses whichever comes second while the other is live.

### Board check after entry

`python tools/agentctl.py check`: `FAIL`, `5 tasks in active work, cap is 2`. Known and not caused by this entry: PK-24 and PK-31 in progress, PK-27, PK-29 and PK-6 in `REWORK_REQUIRED`, each in its own worktree (see the board commits of 2026-11-09). No collision and no unmet dependency on live work was reported. PK-75 is READY-eligible (no dependencies) but cannot be assigned until active work is back under the cap.

## Lead note, 2026-11-09: upload callout

PK-6 could not reach `web/src/components/UploadPrivacyCallout.tsx` (outside its claim). PK-81 (app screens, which includes /upload) adds the sentence "Deal rows from CSV uploads are never sent to the LLM; documents uploaded for Q&A are sent in chunks, so do not upload deal exports as documents" to that callout, word for word as on the privacy page.

## Lead decisions from the PR 87 review, 2026-11-09

- The global footer disclosure reads: "Figures on this site come from a synthetic 2,000-deal sample or are illustrative. None is customer data." It replaces the sentence in PK-75's acceptance line 8, which was literally false on /calculator (reader inputs), /pricing (hand-built scenarios) and /blog (illustrative figures). It is shown on every route except /crm, /upload and /competitor-watch, which can show a customer's own data or public competitor pages; /diagnostic and /guidance show the synthetic sample and carry it.
- Customer login links to /crm; the proxy redirects an unauthenticated visitor to /login?next=/crm and a signed-in customer lands in the workspace. aria-current for /login is matched separately.
- pageMetadata() sets openGraph.images and twitter.images to the root /opengraph-image (1200 by 630, existing alt text) from one shared constant, because a page-level openGraph replaces the root file-based image in Next 16; a test asserts both.
- Page tasks PK-76 to PK-83 add id="main" to their <main> as a gate; the ChromeEffects shim is a bridge that PK-84 removes.
- PK-84 note: the PALETTE.md action-fill row correction assigned to it was done in PK-75; PK-77 and PK-79 remove the static coral glow on the pricing tier and calculator result (status colour as decoration).
- Lighthouse against the Vercel preview URL (design doc 6.9) is blocked by deployment protection (the preview 302s to vercel.com/sso-api). Lead decision 2026-11-09: local production-build Lighthouse numbers are accepted for PK-75 and the page tasks until the founder either grants a protection-bypass token for automation or runs the six routes on the preview; this is a founder setting, not an agent change.
