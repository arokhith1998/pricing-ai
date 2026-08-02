# docs/ops

Operating records for Pricekeel go-to-market activity.

## The one rule

`funnel-tracker.csv` holds **verified activity only**. A row exists only when the
contact, the touch, and the stage actually happened. It is currently header-only
because no design-partner outreach has been verified yet, and an empty file is
the honest representation of that.

Illustrative or scenario data lives in `funnel-tracker-example.csv`, whose rows
are prefixed `EXAMPLE-` and whose notes begin `SYNTHETIC EXAMPLE` so a row stays
self-labeling even when quoted out of context.

## Why the split exists

The 2026-08-01 progress audit found three simulated rows sitting unlabeled in the
operating tracker: they had been committed on 2026-06-11 carrying July dates, and
recorded outreach, replies, a signed NDA, and a received CSV. Nothing marked them
as fictional. Any reader, human or agent, would have counted them as traction.

Never mix the two files. If a number from here reaches a deck, an investor
update, or a customer conversation, it must come from `funnel-tracker.csv`.
