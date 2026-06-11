# Landing redesign brief — aqqrue.com flow benchmark

> For the coding agent (Opus 4.8). Benchmark: https://www.aqqrue.com/ (June 2026).
> **Emulate the structure, pacing, and discipline. Do NOT copy their copy, assets,
> colors, logo treatment, or section text** — we are IP-cautious by policy
> (`vault/Decisions/2026-05-30-legal-compliance-audit.md`). Layout patterns are fair
> game; their words and pixels are not.

## Why aqqrue works (teardown)

1. **One idea per viewport.** Every scroll-stop makes exactly one claim. No competing CTAs,
   no stat-block walls.
2. **The hero shows the product working** — a product video, not screenshots. Motion proves
   the thing is real before a single feature is named.
3. **Audience-flattering headline** ("Built to make accountants exceptional") — identity,
   not features. Subhead is one line. One CTA, repeated verbatim all the way down.
4. **Use-case cards** (4): short animated clip + capability name + 2 concrete sentences in
   the customer's vocabulary ("books 2 years behind", "vendor reclassification across 8 months").
5. **Outcome multipliers, not adjectives** ("x3 clients per accountant, x2.5 hours saved").
6. **Trust block** late-page: audits, "zero training on client data", public trust center.
7. **Scarcity + identity close**: "Early access · 100 spots. For small firms. Solo
   practitioners. The overlooked." Converts by belonging, not urgency theater.
8. Manifesto page carries the narrative so the landing page doesn't have to.

## Diagnosis of current pricekeel.com landing

Headline is good — keep "Stop giving away price that wins you nothing." Everything after it
violates rule 1: dense dashboard dumps, multiple stat blocks competing per viewport, several
CTA variants, no motion, no trust section, no close. It reads like a demo handout, not a flow.

## New page flow (section by section)

1. **Announcement bar** — founding-cohort scarcity, true numbers only:
   "Founding cohort — 10 free diagnostic slots for usage-based SaaS." Links to CTA.
2. **Nav** — Logo · How it works · Sample report · Manifesto · CTA "Get your leakage number".
   Single CTA phrase, reused everywhere.
3. **Hero** — keep headline; subhead one line ("A free, NDA-backed diagnostic on your last 4
   quarters of closed deals. One CSV in, your leakage number out.") + **screen-recorded video**
   of the diagnostic running on the synthetic dataset (upload → metrics animate → leakage
   number lands). MP4, muted, autoplay, ≤20s loop. This replaces ALL hero screenshots.
4. **Use-case cards (4, short clips or scroll-triggered animation), customer vocabulary:**
   - *Find the leak* — "Price realization by segment. Where booked ÷ list quietly fell to 0.81."
   - *Win rate by discount band* — "The curve that shows where discounting stopped buying wins."
   - *Quarter-end effect* — "What the last week of the quarter actually costs you."
   - *Deals to investigate* — "A ranked list with the why attached — comparables, not a black box."
5. **Mid-page CTA band** — one sentence + the CTA.
6. **Proof section — we have zero customers, so NO testimonials (real or implied).** Substitute
   the interactive **sample report on 2,000 synthetic deals** as the proof artifact: "Explore a
   full diagnostic. Synthetic data, real math." Embed live, full-bleed, clearly labeled sample.
7. **How it works (3 steps, grid)** — Sign the one-page mutual NDA → Export one CSV (~30 min,
   no integration, schema doc linked) → Readout in days, with every number explainable.
8. **Outcome numbers** — from the sample, honestly labeled: "$3.24M found across 2,000 sample
   deals" + realization/leakage stats. Multiplier format, one row, three numbers max.
9. **Trust block** — mutual NDA standard; your data never trains models; deletion on request /
   after N days; correlational-not-causal honesty note. **No fake badges, no SOC 2 claims.**
   Link Privacy + Terms (Terms must exist first — see legal audit; sequence accordingly).
10. **Identity + scarcity close** — "For pricing teams running deal desks on spreadsheets.
    Series B–C. Usage-based. The ones the enterprise pricing suites ignore." + slots remaining
    + CTA.
11. **Footer** — Manifesto · Sample report · Privacy · Terms · © entity name (variable).

## Design-system rules

- Whitespace is the design. Max one stat block per viewport; cut 60% of current page content.
- Type scale: oversized hero (clamp ~3.5–5.5rem), generous line-height, short lines (~60ch).
- Palette: keep dark brand base but reduce to bg + one accent + neutrals. Accent = CTA + key
  numbers ONLY. No multi-color chart rainbow above the fold.
- Motion: prefers-reduced-motion respected; videos lazy-loaded, poster frames; Lighthouse ≥90.
- Mobile-first; the use-case cards stack with the clip above text.
- CTA: identical label + destination everywhere; destination is the diagnostic-request form.

## Build order for Opus

1. Record/render the hero demo MP4 from the existing Streamlit/sample flow (script the capture).
2. Rebuild `web/` landing to the 11-section flow above (content in `web/content/`).
3. Wire the sample-report embed (section 6) to the existing live sample page.
4. Add Terms/Privacy links only when those pages ship (legal audit items 1–2).
5. Screenshot full page at 390px and 1440px; compare against this brief before declaring done.

## Related
`docs/design/buyer-funnel.md` · `docs/design/nextjs-ui.md` ·
`vault/Decisions/2026-05-26-nextjs-ui-direction.md` · `vault/Decisions/2026-05-30-legal-compliance-audit.md`
