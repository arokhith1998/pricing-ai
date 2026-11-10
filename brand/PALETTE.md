# Pricekeel — Color Palette

All hex values are canonical. Use them verbatim. Do not approximate or re-tint.

| Name             | Hex       | Usage |
|------------------|-----------|-------|
| Keel Navy        | `#0C2D48` | Primary brand color. Headers, nav, brand surfaces, logo waterline, dark UI fills. |
| Deep Ink         | `#0B1727` | Default body and high-emphasis text. Near-black with a navy cast. |
| Waterline Teal   | `#17B8A6` | Accent. Primary CTAs, active states, links, logo hull/keel, focus rings. |
| Signal Green     | `#2BB673` | Positive / healthy. Strong price realization, on-policy quotes, gains. |
| Leak Coral       | `#F0654E` | Alert. Discount leakage, over-discounting, margin erosion callouts. |
| Caution Amber    | `#E8A33D` | Warning. Off-policy quotes, governance flags, approvals pending. |
| Slate            | `#5B6B7B` | Muted / secondary text, captions, axis labels, placeholder copy. |
| Mist             | `#E6EDF3` | Borders, dividers, table rules, subtle background fills, chart gridlines. |
| Paper            | `#F7FAFC` | App / page background. Off-white canvas behind cards and content. |
| White            | `#FFFFFF` | Card surfaces, inverse text on Keel Navy, logo waterline on dark. |

## Semantic usage (status & metrics)

| Meaning                              | Color          | Hex       |
|--------------------------------------|----------------|-----------|
| Healthy price realization / gains    | Signal Green   | `#2BB673` |
| Discount leakage / over-discount     | Leak Coral     | `#F0654E` |
| Off-policy / governance flag / pending| Caution Amber | `#E8A33D` |
| Primary action / accent / link       | Waterline Teal | `#17B8A6` |
| Brand / headers / structure          | Keel Navy      | `#0C2D48` |

## Notes
- Reserve Leak Coral, Signal Green, and Caution Amber for *status* — never decorate with them.
- Status colors should always be paired with a label or icon, not color alone (accessibility).
- On Keel Navy backgrounds, use White text and Waterline Teal accents.
- Charts: Mist for gridlines, Slate for labels, status colors for series meaning.

## Dark theme (web app)

The marketing site and app render on a dark, navy-black canvas. The status and
accent hues are intentionally **brightened** from the canonical values above so
they pass AA contrast on the dark surface; this is a deliberate dark-mode
adaptation, not drift. Canonical hex still governs light surfaces, print, PDFs,
logo files, and any single-light-mode asset. Source of truth in code:
`web/src/app/globals.css`.

| Token | Dark value | Adapted from |
|-------|-----------|--------------|
| Canvas (`--color-bg`, `paper`) | `#0A0F1A` | inverse of Paper `#F7FAFC` |
| Surface / card (`--color-surface`) | `#111A2B` | dark cousin of Keel Navy `#0C2D48` |
| Inset (`--color-surface-2`) | `#0D1422` | — |
| Border (`--color-border`, `mist`) | `#1F2C43` | dark Mist `#E6EDF3` |
| Primary text (`--color-fg`, `ink`) | `#E9F0F8` | inverse of Deep Ink `#0B1727` |
| Muted text (`--color-muted`, `slate`) | `#8EA3BD` | Slate `#5B6B7B` lifted |
| Accent (`--color-teal`) | `#2DD4BF` | Waterline Teal `#17B8A6` brightened |
| Alert (`--color-coral`) | `#FF6B54` | Leak Coral `#F0654E` brightened |
| Positive (`--color-green`) | `#34D399` | Signal Green `#2BB673` brightened |
| Warning (`--color-amber`) | `#F0B34A` | Caution Amber `#E8A33D` brightened |
| Action fill (`--color-navy` alias) | `#0D9488` | a deep teal, not navy; white text on it is 3.74:1, large-text AA only, so action fills use dark text (see below) |

Note: the legacy `--color-navy` alias is a deep teal used as an action-fill on
dark, not the brand navy. When adding light-mode or export assets, use the
canonical table above, never these dark values.

### Dark-theme clarifications (PK-75)

1. **Control borders.** The border of form controls (inputs, selects, toggles) is canonical Slate `#5B6B7B` (`--color-control`) on the inset `#0D1422` or card `#111A2B` surface: 3.36:1 and 3.18:1, meeting the 3:1 non-text rule (WCAG 1.4.11). The decorative border `#1F2C43` is 1.24:1 and is for card edges and dividers only, never for a control.
2. **Action fills use dark text.** White on `#0D9488` is 3.74:1, which passes AA for large text only, so it is not used for normal-size text. The primary action is Waterline Teal `#2DD4BF` (`bg-teal`) with canvas `#0A0F1A` text (`text-bg`), 10.29:1. The `--color-navy` alias stays only until the last page that uses it is migrated.
