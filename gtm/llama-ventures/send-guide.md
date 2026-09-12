---
title: Pitch deck send guide — the golden rules, applied to Pricekeel
created: 2026-09-11
updated: 2026-09-11
type: gtm
tags: [gtm, fundraising, deck, investor, process]
status: active
related: ["[[deck-audit]]", "[[pitch-base]]", "[[traction-update]]", "[[rehearsal-script]]"]
confidence: high
ai-first: true
---

## For future Claude

How the Pricekeel deck gets sent, and the rules the rebuild already follows.
Checklist first, reasoning second.

---

# The artifact

`decks/Pricekeel-Pre-Seed-Deck.pdf`, 16 slides, A4 landscape, about 330 KB.
Built by `python tools/build_investor_deck.py`.

Rename on send to `Pricekeel-Pre-Seed-Deck-2026-09.pdf`. A dated filename sits
legibly in an investor's downloads folder six weeks later; `deck-final-v3.pdf`
does not.

---

# The golden rules, and how this deck meets each

**1. Send a PDF, never a link that can expire or a file that needs an account.**
Met. Screenshots are embedded as base64, so the PDF is self-contained and renders
identically offline.

**2. It must read standalone, with no presenter.** Met, and it is why the deck
runs 16 slides rather than 10. Every headline states the point rather than naming
a topic: "Feasibility is retired. Demand is not," not "Traction." An investor
should be able to forward it to a partner who was never on the call.

**3. One idea per slide.** Met, enforced by the slide frame in the builder.

**4. Lead with what it is, not with a story.** Met. Slide 1 says what the product
does, what is raised, and the honest status, in that order.

**5. Traction early and honest.** Partially deliberate deviation. Traction sits at
slide 14 rather than slide 3, because at intro-call stage leading with it would be
leading with the weakest fact. The status line is on slide 1 instead, so nobody
reaches slide 14 feeling misled. If a signed pilot lands, move traction to slide 3
and lead with it.

**6. A clear, specific ask.** Met. Amount, duration, and six named milestones the
round buys.

**7. No unsourced market statistics.** Met by removal. The old deck's headline,
"B2B SaaS companies leak 4 to 8% of ARR," had no citation anywhere in the repo and
is gone. Every remaining figure is either computed by the engine, drawn from a
dated and attributable acquisition, or explicitly labeled assumed.

**8. Own the weaknesses before the reader finds them.** Met, and it is the deck's
main structural choice. A dedicated risks slide, the platform risk stated inside
the why-now slide, the self-asserted approver gap named in full, and the
defensibility slide conceding the copyable feature before claiming the moat.

**9. Do not stamp it Confidential.** Met by removal. It is unenforceable on a deck
you email to strangers and it reads as inexperience. The footer carries
"Pricekeel · Pre-seed · <date>" instead, which is the useful half.

**10. Keep it under a few MB and do not embed video.** Met. About 330 KB. The
walkthrough recording is a separate hosted link, never an attachment.

**11. Date it and version it.** Met. Every footer carries the build date, and the
sample figures are recomputed from the engine on every build, so a stale number
cannot survive a rebuild.

**12. Name a human on the first and last slide.** Met.

---

# The walkthrough video

`decks/assets/sample-walkthrough.webm`, about 40 seconds, 1280x720, 2.7 MB.
Rebuild with `python tools/record_sample_walkthrough.py`.

**Do not attach it.** Upload to Loom, YouTube unlisted, or Vimeo, and put one line
in the follow-up email: "40-second walkthrough of the live engine on the sample
book: <link>." Video belongs in the follow-up, not in the first touch, because the
first touch has to survive being read on a phone in thirty seconds.

Convert to MP4 before hosting if the platform prefers it:
`ffmpeg -i sample-walkthrough.webm -c:v libx264 -crf 23 -preset slow sample-walkthrough.mp4`

---

# Pre-send checklist

- [ ] `python tools/build_investor_deck.py` rerun, so the date and sample figures
      are current.
- [ ] [[traction-update]] still accurate today. If a conversation advanced, the
      deck's slide 14 and slide 1 status line both change.
- [ ] Acquisition figures on slide 3 re-verified if more than a quarter has passed
      since 2026-08-09.
- [x] ARR band resolved 2026-09-11: **$10M to $100M, servability gated on deal
      volume rather than ARR**. The sourced derivation always used $10M to $100M;
      the $20M to $100M that had spread through the deck, the site and the agent
      definitions was drift. Fixed everywhere. See
      `vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md`.
- [ ] Check the market slide still reports the **post-funnel** wedge ($11M to $29M
      Tier A, $4M to $11M Tier B), never the $120M to $215M pre-funnel layer as a
      headline. That layer may appear only to show funnel depth.
- [ ] Renamed to `Pricekeel-Pre-Seed-Deck-2026-09.pdf`.
- [ ] Opened once in a plain PDF viewer, not just the build check PNGs.

---

# Order of operations for Llama Ventures

1. Rebuild and read the deck end to end.
2. Confirm the market slide reports the post-funnel wedge. The band question is
   settled; the live risk now is quoting the pre-funnel SAM as a headline.
3. Run the rehearsal in [[rehearsal-script]].
4. Start the real session, upload this deck, not the May one.
5. Finalize only on explicit founder approval.
