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
