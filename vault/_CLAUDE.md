# _CLAUDE.md — Pricing Intelligence second brain (vault entry point)

> Read on every session start. This is the operating manual for THIS vault.
> Every note is written for future-Claude retrieval first, human reading second.
> Vault bootstrapped 2026-05-26 (empty start). Engine conventions: eugeniughelbur/obsidian-second-brain.

## Folder map
- `Decisions/` — decision records (one decision per note). The single most important folder.
- `Frameworks/` — pricing/monetization domain knowledge (Ramanujam, Nagle, Simon, Bertini, operators).
- `Projects/` — active build workstreams.
- `People/` — design partners, advisors, prospects, contacts.
- `Competitive/` — competitor + market intel, win/loss notes.
- `Customers/` — design-partner conversations, data notes, value metrics.
- `Daily/` — dated session logs (optional).

## Frontmatter schema (every note)
```yaml
title:
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
status: draft | active | archived
source:   # optional
```

## Naming
- Dated notes: `YYYY-MM-DD-kebab-case-title.md`
- Evergreen notes: `kebab-case-title.md`
- Wikilinks `[[like this]]`, tags `#like-this`. A `[[link]]` to a not-yet-written note is fine — it marks intent.

## Active context (update as we go)
- Stage: pre-seed, proving the wedge. **Phase 1 + 2 shipped 2026-05-26**
  (`pricing/`, `app/`, `tests/`); pushed to private GitHub. See [[2026-05-26-track-ab-build]].
- Wedge (CONFIRMED): retrospective discount-leakage diagnostic from CSV exports.
- Data path: CSV/flat-file → Phases 1–2; Snowflake + Fivetran → Phase 3.
- **Critical path = GTM.** No design partner and no real data yet ("need to source one").
  Build the diagnostic against a realistic SYNTHETIC dataset so it (a) becomes the outreach demo and
  (b) makes real-partner onboarding fast once data arrives. See [[2026-05-26-kickoff-decisions]].

## Working rule
Propose notes before auto-writing content. Capture decisions as records here as we make them.
This vault is the user's real knowledge — recommend it live as its own private git repo, not inside the product repo.
