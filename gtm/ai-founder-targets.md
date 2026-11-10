---
title: 'AI founder targets: sourcing 40 candidates to yield 10 to 15 interviews'
created: 2026-11-10
updated: 2026-11-10
tags: [gtm, sourcing, ai-founders, interviews, icp, audit-first]
status: draft
source: 'WebFetch of public pricing pages and WebSearch on 2026-11-10; vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md'
---

# AI founder targets

Scope: the **new audit-first motion** only. ICP here is seed-to-Series-A AI companies moving from flat or per-seat pricing to usage or outcome pricing. The site's $10M to $100M ARR ICP and the Salesforce-first design-partner list in [[design-partner-targets]] are unchanged and are not mixed with this list. There is no 500-closed-opportunities gate and no Salesforce requirement for interviews.

Rules: company names and public founder titles only. No private contact details, no personal email or phone, no scraped profile data. The founder does every outreach touch by hand. Real prospects and real interviews are logged apart from synthetic examples; see the tracker note in [[ai-founder-outreach-sequence]].

## Yield math, stated honestly

Goal: 10 to 15 completed interviews. From 40 candidates that needs roughly a 25 to 35 percent yield from first touch to completed call. That is optimistic for cold outreach to founders. A realistic cold yield is closer to 10 to 20 percent, which is 4 to 8 calls from 40. Plan for one of two things: add 20 more candidates (60 total), or convert at least a third of the pool through warm paths (intros from the first interviews, investors, communities where the founder already participates). Re-check yield after the first 15 touches and extend the list before the founder runs out of runway on the 30-day plan, not after.

## Sourcing criteria for the 40

All criteria are judged from public evidence. Each scored candidate needs an evidence URL and the date it was seen. No evidence means a zero on that line.

**Stage and size**
- Seed to Series A, or pre-seed with visible paying customers. Public proxies: funding announcement, headcount on the public company page (roughly 5 to 60), a pricing page with paid tiers.
- Prefer companies that raised within the last 24 months: pricing is still being set.
- Revenue is almost never public. Do not guess ARR. Ask in the interview, in ranges (Q2 of [[ai-founder-interview-module]]).

**Pricing-model transition signals visible on public pricing pages**
- A seat or flat tier alongside credits, usage or overage (hybrid in transition).
- Credits, tokens, minutes, runs, resolutions or "actions" as the unit, especially with an included allowance plus a top-up price.
- Wording such as "legacy plan", "grandfathered", "new pricing", "usage-based billing", "fair use", "spend cap", "auto-reload".
- Enterprise tier described as "custom credits" or "custom usage" (usage is being negotiated).
- A pricing change in the changelog, blog or release notes in the last 12 months.
- A Wayback Machine comparison of the pricing page 6 to 12 months ago showing a unit change. Pricing pages are snapshots: a hybrid page alone does not prove a transition, so the Wayback diff is what upgrades a candidate. None of the examples below has had that diff run yet.

**Model-provider dependence**
- Product behavior depends on third-party model APIs: model picker in the product, "bring your own key", docs listing OpenAI, Anthropic, Google or open-weight hosts, a pass-through of model cost on the pricing page.
- Strongest: the pricing page itself separates the platform fee from model or telephony cost (the founder is already exposed to unit cost).
- Weaker: founders who train and host their own frontier models (excluded, see below).

**Customers**
- B2B buyers or developers who pay by invoice or card. A consumer-only app has a different pricing problem.

**Geography**
- Pick regions that overlap the founder's working hours so interviews do not need unsocial slots. The founder to confirm the region list. Exclude jurisdictions where a cold approach on LinkedIn would breach local rules the founder is not prepared to check.

**Exclusion rules**
- Series B and later, or total funding well above the seed-to-A band (keep as a pattern reference only, see table below).
- Frontier model labs and large platform vendors.
- Billing and pricing-software vendors (metering, billing, monetization, CPQ tools): they are competitors or channel partners, not interviewees for this module. They can be studied separately.
- Pure per-seat products with no variable AI cost (nothing to reconcile).
- Companies with no public pricing and no public founder voice: not scoreable from public evidence.
- Personal acquaintances or investors: bias risk, interview them separately and tag as such.
- Anyone who has asked not to be contacted.
- Anyone whose only contact route would require scraping or guessing private details.

## Where to find them

1. **Public lists.** Accelerator and fund portfolio pages (filter to AI, application layer), Product Hunt "AI" launches, Hacker News Show HN, public "AI startups to watch" lists. Lists are for names only: confirm stage elsewhere.
2. **Launch posts.** Founder launch threads and release notes that mention credits, usage limits or a new plan. Search: `"new pricing" OR "usage-based" OR "credits" site:blog` plus the product category.
3. **Pricing-page changes.** Wayback Machine (public) comparison; the founder's own page-change alerts on a short list. Changelog entries titled "pricing", "plans", "limits".
4. **Job posts.** Roles titled pricing, monetization, billing, finance operations, "GTM engineer" or "founding finance" at AI companies. A job post for billing at a 20-person company is a strong pain signal.
5. **Founder content.** LinkedIn or X posts by founders about margins, token costs, pricing changes, "we moved to usage", plus podcast and conference talks. A founder who posted about pricing gets the post-based outreach variant.
6. **Communities** the founder is already part of. No unsolicited posting. Warm intros from interview 1 onward.
7. **Referrals.** The last question of every interview.

## Scoring rubric (100 points)

Score from public evidence. Record the evidence URL and date for each non-zero line.

| Dimension | Points | 0 | Full marks |
|---|---|---|---|
| Pricing-model transition signal | 30 | Pure seat or pure flat, no change | Hybrid or credits page plus a dated pricing change or Wayback diff |
| Model-provider dependence | 20 | No third-party model use shown | Platform fee separated from model cost, or multiple providers named |
| Stage and size fit | 15 | Series B or later, or unknown | Seed to A, 5 to 60 staff, funding in the last 24 months |
| B2B or developer buyers | 10 | Consumer only | Invoiced B2B or developer API customers |
| Founder public pricing voice | 10 | No public content | Posted or spoke about pricing, margin or token costs in the last 6 months |
| Reachability | 10 | Cold only | Warm path or shared community |
| Billing complexity | 5 | One meter | Several meters, commits, overage or caps |

Tiers:
- **A (70 or more):** interview ask, and the 14-day audit mention is allowed in follow-up 1 (see [[ai-founder-outreach-sequence]]).
- **B (50 to 69):** interview ask only.
- **C (under 50):** park. Do not touch.

## Example companies that publicly fit the pattern

Seen on **2026-11-10** unless a different date is noted. Method: WebFetch of each public pricing page, which returns a model-written summary of the page, not the raw page. **The founder must open each page and verify wording before quoting any of it in outreach.** Stage is unverified unless a source is named; the stage column uses only what searches returned, and several sources were low reliability. Prices change: treat all figures as of 2026-11-10.

Honest read on the list: most of these companies are probably past the seed-to-A band or their stage is unverified. Only one (Gradient Labs) was described as seed-stage, and that was from a secondary article. Treat the table as **pattern evidence plus a source of smaller peers**, not as 16 targets. The 40-candidate list needs stage confirmation from a funding database before any touch.

| # | Company (type) | Public evidence on pricing page, seen 2026-11-10 | Stage per search results | Use |
|---|---|---|---|---|
| 1 | Lindy (AI agent builder) | Page shows seats and credits together: "Every active user in your workspace is billed"; Team plan from $29.99/mo for 3,000 credits; top-ups "$10 per 1,000 credits"; Enterprise "Custom credits and billing" | Unverified. A low-reliability site said about $50M raised | Seat plus credit hybrid pattern |
| 2 | Greptile (AI code review) | Pro has no seat fees; prepaid credits at $1 each; reviews priced as Base 1, Plus 3, Apex 10 credits; credits "shared across your whole org" | Series A $25M (Benchmark) reported 2025; Series B reported in 2026 with conflicting figures. Likely above band | Per-credit review pricing pattern; study, do not target |
| 3 | Firecrawl (web data API) | Credit tiers from Free (1,000) to Scale (1,000,000, $749/mo); pay-as-you-go in "5 USD increments, up to a monthly limit you set"; Enterprise custom credits | Series A $14.5M announced Aug 2025 on its own blog; a banner on the same page mentions a later Series B. Likely above band | Credits plus auto-recharge pattern |
| 4 | Vapi (voice agent platform) | Hosting "$0.05/min Vapi hosting" with "Models pass-through at cost"; Pro at "10% of the Vapi hosting fee" with a $999/mo minimum | A low-reliability site reported a 2026 Series B. Unverified | Platform fee plus provider pass-through pattern |
| 5 | Retell AI (voice agents) | Voice "$0.07-$0.31 / min" with the LLM listed as its own per-minute line; Enterprise "Custom Pricing" | Unverified; a low-reliability site claimed about $60M ARR, which would be above the band | Component per-minute pattern |
| 6 | Browserbase (browser infrastructure) | Developer $20/mo with 100 browser hours, overage "$0.12/browser hr"; proxies "$12/GB"; model usage billed through a gateway at market price; Scale "usage-based" | Not checked. Likely above band | Multi-meter billing complexity |
| 7 | Hyperbrowser (browser infrastructure) | "1,000 credits equal to $1"; browser time 100 credits per hour; proxy 10,000 credits per GB; credits reset at renewal | Not checked. Smaller peer to Browserbase | Credit design pattern; candidate for stage check |
| 8 | Exa (search API) | "There is no subscription and no minimum spend"; $4 to $7 per 1k search requests; Agent mode with "$0.10 per Agent Compute Unit" and default spend caps | Not checked | Prepaid usage pattern; agent compute unit |
| 9 | Parallel (web research API) | Per-1k request rates by API; Scale plan "$1,000 per month"; up to $250 credits for qualified startups | Not checked | Usage pricing plus startup credits |
| 10 | CodeRabbit (AI code review) | Per-seat tiers $30, $60, $90 per user/month plus "$0.25 per reviewed file" after an hourly allowance, with a monthly spend cap set by admins; Agent at "$0.40 per agent minute" | Not checked. Likely above band | Seat to usage hybrid, caps |
| 11 | Mintlify (documentation platform) | Pro $450/mo with "Unlimited editor seats"; AI features metered in credits, Assistant "25 credits per answer"; overage "$0.01 per credit" with a hard limit option | Not checked | Seats de-emphasized, AI metered in credits |
| 12 | Relevance AI (AI workforce platform) | Only an Enterprise plan shown; headline "Pricing That Scales With Your AI Workforce"; "decouple growth from headcount"; "Custom Vendor Credits"; "Talk to sales" | Not checked | Seat de-emphasis with custom credits |
| 13 | Tavus (conversational video) | Developer tiers with included minutes and pay-as-you-go overage "from $0.26 to $0.35 per minute"; the page carried two different versions of tier prices when fetched | Not checked | Monthly fee plus overage; pricing in flux (verify page) |
| 14 | Cartesia (voice AI) | Plans with credits and "prepaid dollars" for voice agents; overage per 1M credits on paid plans; voice agents "$0.03 per minute" with LLM billed separately | A low-reliability site reported a 2025 Series A. Unverified | Two-meter plan structure |
| 15 | Lorikeet (AI customer support) | "a plan fee plus per-resolution charges": Start $2,100/mo and Scale $5,100/mo billed annually; $0.99 and $0.90 per resolution (chat, email, SMS); article updated Apr 15, 2026 | Not checked | Outcome pricing with a platform floor |
| 16 | Gradient Labs (AI customer support) | Outcomes-based model "with no platform fees", "only for successful query resolutions"; no price shown, "request a demo" | Described as seed-stage by a Future Nexus article (secondary source) | Pure outcome pricing; best stage fit in this list |

Also seen as context, not companies to contact: GitHub Copilot moved to usage-based AI credits on June 1, 2026, and several coding-assistant vendors changed limits during 2026, according to secondary sources (a tracker, tech press and dev blogs of mixed quality). These show buyer expectations are shifting, which feeds the buyer-pushback section of the interview. Re-verify before quoting.

Next step before any touch: confirm stage, headcount and funding for each from a funding database, run the Wayback diff, and add 24 or more genuinely seed-to-A names to reach 40. Do not fill the gap with larger companies to hit the count.

## Candidate record template (one row per company in the founder's working sheet, not committed with private data)

Company, URL, stage (source and date), headcount band, evidence URLs with seen dates per dimension, rubric score and tier, outreach variant (posted about pricing / not), warm path (role only), status. Founder title as publicly listed on the company page, no personal contact details.

## Related

[[ai-founder-interview-module]] · [[ai-founder-outreach-sequence]] · [[design-partner-targets]] · [[personas]] · [[2026-11-10-audit-first-motion-and-ai-margin-wedge]]
