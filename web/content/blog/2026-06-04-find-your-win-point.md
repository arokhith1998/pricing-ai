---
title: How to find your win point with one spreadsheet
date: 2026-06-04
author: Adhithya Bhaskar
excerpt: You do not need a data team or a warehouse to find where your discounting stops paying off. You need one export and a few honest columns.
published: true
---

You do not need a data warehouse to find where your discounting stops paying off. You need one export of closed opportunities and a willingness to look at it honestly.

## The columns that matter

At minimum, one row per closed opportunity with:

- **outcome** — won or lost
- **list value** and **booked value** (annualized) — so we can compute the discount
- **segment** and **close date** — so we can see *where* and *when* the curve bends

Everything else (rep, approver, competitor present, product tier) makes the picture sharper, but the four above are enough to start.

## The four moves

1. **Compute discount per deal** as `1 − booked / list`. This is price realization's mirror image.
2. **Bucket into bands** (0–5%, 5–10%, …) and compute the win rate in each band, with confidence intervals so you do not over-read thin buckets.
3. **Find where win rate stops climbing.** The first band whose win rate the deeper bands never beat is your win point.
4. **Sum the discount given beyond it** on won deals. That is your pricing upside to pursue — a prioritized list, not a refund.

## The traps

- **Don't trust thin bands.** A 78% win rate from nine deals is noise. Confidence intervals keep you honest.
- **Watch quarter-end.** If late-quarter deals are systematically deeper, that is a process leak, not a value signal.
- **Segment before you conclude.** A blended curve can hide that Enterprise is fine and MidMarket is bleeding.

This is exactly the math Pricekeel runs for you — and it is deliberately the kind of thing you could check by hand, because a pricing recommendation you cannot explain is one finance will not trust.

[Run it on your own CSV →](/upload)
