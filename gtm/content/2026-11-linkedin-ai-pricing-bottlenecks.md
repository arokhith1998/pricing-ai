---
title: LinkedIn series, AI pricing bottlenecks (drafts)
created: 2026-11-10
updated: 2026-11-10
tags: [gtm, linkedin, content, ai-pricing, drafts]
status: draft
source: gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md (Consumer Trends tab); public sources named per post
---

# LinkedIn series: AI pricing bottlenecks (drafts, nothing published)

Everything here is a draft for the founder to approve per item. Nothing has been posted, scheduled, or sent, and no profile or account setting is touched. The founder presses publish.

Grounding: [[linkedin-strategy]] (five pillars, four posts a week, credibility-only until late August is the manual's stance, no hard selling), [[2026-11-10-audit-first-motion-and-ai-margin-wedge]] (decision 4: founder-led content from the Consumer Trends memo), and ADR-006 in `docs/agents/DECISIONS.md` (a CRM or CSV cost figure is "cost proxy, not margin").

## Evidence boundary used for every post

- Live product: a CSV and Salesforce discount-leakage diagnostic, with a lens for commit, ramp, overage and unit-rate floors. HubSpot analysis just merged; Stripe and Chargebee are in progress. None of the posts claims more than that, and most claim nothing about the product.
- No customers, no design partner, no results. Post 8 and post 5 say so plainly; the founder can cut those sentences, but should not replace them with anything implying traction.
- The memo's bracketed citations point to a source list we do not have. Every memo figure was searched. Only figures with a named public source appear, and only in the post that names the source. The rest are in the "do not post" list at the end.
- No em dashes anywhere. Posts avoid "proven" and guarantees.

## Algorithm note (the strategy's `[algo-watch]` review was due 2026-08-28 and is overdue)

One quick search on 2026-11-10 (vendor blogs, not LinkedIn documentation, so treat as directional). I did not edit the strategy doc; proposals only.

- Dwell time still described as a major signal; document carousels still the most cited B2B format. Consistent with the manual.
- Link posts reported at roughly 60 percent less reach (the manual says about 30 percent). Direction agrees, size differs by source. One source says the link-in-first-comment workaround is also penalised as of early 2026, unsettled. Proposal: keep links out of the body and treat first-comment links as a test, not a rule.
- Frequency: sources conflict (3 to 5 a week, flat engagement from 1 to 6 a week, 3 to 4 a week). Four a week is inside the range; no change proposed.
- Timing: Tuesday to Thursday still the most consistent recommendation. Manual's Mon, Tue, Thu, Fri slots unchanged here.
- Proposed edit to the manual: bump `updated:`, change the link-penalty figure to "reported 30 to 60 percent, varies by source", and add a note that the first-comment workaround is contested. Founder decides.

Format note: the manual sets 600 to 2,400 characters by pillar. Per the brief, every post body below is under 1,300 characters, so the two Framework posts (normally 1,800 to 2,400) run shorter than the manual says. A carousel version of posts 2 and 6 would be the place for the longer form; I would propose it, not draft it.

## The six bottlenecks (from the Consumer Trends tab) and how the series covers them

| # | Bottleneck | Posts |
|---|---|---|
| 1 | Cost floor: variable inference, compute and storage cost | 1, 8 |
| 2 | Packaging paradox: per seat, per usage, predictability | 2, 3, 4 |
| 3 | Value metric and outcome pricing | 2, 7 |
| 4 | Variance and trust before high-tier pricing | 4 |
| 5 | Pilot trap and false recurring revenue | 5 |
| 6 | Incumbent bundling and commoditisation | 6 |

## Two-week calendar (eight posts, four a week)

Cadence follows the manual: Monday counter-intuitive, Tuesday framework, Thursday diagnostic, Friday builder narrative or buyer pain. Times are ET. Wednesday is engagement-only. Week 2 Thursday is US Thanksgiving (2026-11-26); I recommend moving post 7 to Wednesday 11-25 at 8:30 am, or holding it to 2026-12-03. Founder decides.

| # | Date and time (ET) | Pillar | Bottleneck | Status |
|---|---|---|---|---|
| 1 | Mon 2026-11-16, 8:30 am | 3 Counter-intuitive | 1 Cost floor | draft, awaiting approval |
| 2 | Tue 2026-11-17, 8:00 am | 2 Framework breakdown | 2, 3 Packaging, value metric | draft, awaiting approval |
| 3 | Thu 2026-11-19, 8:30 am | 1 Diagnostic insight | 2 Predictability vs usage | draft, awaiting approval |
| 4 | Fri 2026-11-20, 11:00 am | 5 Buyer-pain language | 4, 2 Trust, forecastable bill | draft, awaiting approval |
| 5 | Mon 2026-11-23, 8:30 am | 3 Counter-intuitive | 5 Pilot trap | draft, awaiting approval |
| 6 | Tue 2026-11-24, 8:00 am | 2 Framework breakdown | 6 Bundling | draft, awaiting approval |
| 7 | Thu 2026-11-26 (move to Wed 11-25 or hold) | 1 Diagnostic insight | 3 Outcome pricing | draft, awaiting approval |
| 8 | Fri 2026-11-27, 11:00 am | 4 Builder narrative | 1 Cost floor (measurement) | draft, awaiting approval |

Pillar mix over the two weeks: counter-intuitive 2, framework 2, diagnostic 2, builder 1, buyer-pain 1. This is heavier on buyer-pain and builder than the manual's weights (5 percent and 15 percent) because the series is one theme; the manual's weights apply over a quarter, not a fortnight.

Engagement ritual per manual: reply to comments within the first hour and again at 8 pm. First-comment links: only where noted.

---

## Post 1

- **Pillar:** 3 Counter-intuitive
- **Audience:** Heads of Pricing, CFOs and founders at AI and usage-based B2B companies
- **Bottleneck taught:** 1, the cost floor. Variable cost to serve breaks the flat-rate assumption.
- **Suggested time:** Mon 2026-11-16, 8:30 am ET

**Hook:** A flat monthly price on an AI product is a bet that your heaviest user looks like your lightest one.

**Body:**

Classic SaaS pricing assumed one more user cost close to nothing to serve. A flat rate worked because heavy and light users cost about the same.

AI breaks that. Every query and agent step has a real cost behind it: model calls, compute, storage. Two customers on the same plan can cost very different amounts to serve.

Bessemer's Atlas team drew the contrast in late 2025: the 80 to 90 percent gross margin associated with traditional SaaS is not what AI companies typically see, and one fal co-founder said no one in AI really has it.

So the pricing question changes. It is no longer only "what will they pay." It is "what does this customer cost me at high usage, and does the price still clear it."

Three checks before touching price:

1. Does the plan have a usage ceiling, or just a hope?
2. Is cost to serve visible per customer, or only in aggregate?
3. When a customer doubles usage, what happens to your revenue from them?

If the answer to the third is "nothing," that is not a price. It is a subsidy.

**Closing question:** Do you know what your most active customer costs you to serve, or only what they pay?

**Source line:** Bessemer Atlas, "Scaling an AI Supernova: Lessons from Anthropic, Cursor and fal", 2025-11-10, https://www.bvp.com/atlas/scaling-an-ai-supernova-lessons-from-anthropic-cursor-and-fal . Caveat: the 80 to 90 percent SaaS figure is Bessemer's own framing with no underlying citation, so the post attributes it and does not state it as measured fact. The article's 40 to 50 percent AI margin figure is deliberately not used.

---

## Post 2

- **Pillar:** 2 Framework breakdown (Nagle, economic value and value metric)
- **Audience:** Pricing and product leaders designing AI packaging
- **Bottleneck taught:** 2 and 3, the packaging paradox and the value metric.
- **Suggested time:** Tue 2026-11-17, 8:00 am ET

**Hook:** Per-seat pricing has a hidden assumption: that the product makes your customer need more seats, not fewer.

**Body:**

Nagle's economic value framing says price is justified by the value a customer gets relative to their next best alternative. The value metric is the unit you charge on, and it should move with that value.

Seats worked because software value grew with the number of people using it. Agentic products often create value by doing work a person did. If the product works, seats go down, and so does your revenue. You get paid less for being better.

Three tests for any value metric:

1. Does it rise when the customer gets more value?
2. Does it rise roughly with your cost to serve?
3. Can the customer forecast it?

Seats pass the third and often fail the first two for AI. Raw tokens pass the second, but fail the first and third, because buyers do not think in tokens.

A common compromise is a unit in the customer's language (documents, tickets, claims) inside a committed band. Salesforce's public Agentforce page lists conversation, credit and per-user options side by side, so the right unit is still being found in public.

**Closing question:** Which of the three tests does your current value metric fail first?

**Source line:** Salesforce, Agentforce Pricing, https://www.salesforce.com/agentforce/pricing/ , retrieved 2026-11-10 (page is undated and subject to change). No figures are quoted in the post. Framework attribution: Nagle, *The Strategy and Tactics of Pricing*.

---

## Post 3

- **Pillar:** 1 Diagnostic insight (conceptual, no customer data)
- **Audience:** Heads of Pricing, RevOps, deal-desk leads at usage-based B2B
- **Bottleneck taught:** 2, predictability versus usage. The contract is where the buyer's wish for a stable bill meets the vendor's variable cost.
- **Suggested time:** Thu 2026-11-19, 8:30 am ET

**Hook:** Usage-based contracts leak in the gap between the commit, the overage rate and the unit-rate floor.

**Body:**

Buyers want a predictable number. Vendors with variable cost want revenue that moves with usage. The contract is where the two meet: a commit for predictability, an overage rate for usage beyond it, and a unit-rate floor so discounts cannot push price below what you can serve.

Four places the leak hides when you read a deal book:

1. An overage rate negotiated below the committed unit rate, so the customer's heaviest months are their cheapest per unit.
2. Ramp schedules that discount early periods and never reconcile to the floor.
3. A commit sized to what the customer hoped to use, then waived or rolled when they under-use.
4. A floor that exists in policy but not in the quote.

You do not need a model to check this. For each deal, compute the effective unit rate across commit plus expected overage, then compare it to list and to the floor. Count the deals under the floor. A CSV and a pivot table is enough to start.

The point is not that discounts are bad. It is that a discount should be a decision someone can see.

**Closing question:** In your contracts, is the overage rate higher than, lower than, or equal to the committed unit rate?

**Source line:** none (no figures used).

**First comment (optional):** link to the synthetic sample at pricekeel.com/sample, only if the founder confirms the sample shows the commit, ramp, overage and floor lens. Otherwise omit; do not link to anything that does not show what the post describes.

---

## Post 4

- **Pillar:** 5 Buyer-pain language (a mirror, no CTA)
- **Audience:** Heads of Pricing and finance leaders evaluating AI tools; also founders selling to them
- **Bottleneck taught:** 4 and 2, trust before full-price commitment and a forecastable bill.
- **Suggested time:** Fri 2026-11-20, 11:00 am ET

**Hook:** Three questions a finance leader asks before approving an AI tool at full price. None of them is about the model.

**Body:**

These are the three I would prepare for if I were selling AI into a finance review. They are my read of the buyer's side, not survey results.

1. What does a wrong output cost us, and who owns it? Variance is a bigger risk than a slightly slower or pricier tool. If the answer is "we will fix it," the buyer hears "we have not priced it."

2. What will the bill be next quarter, and within what range? Usage-based pricing is easy for the vendor to defend and hard for a budget owner to approve. A commit, a cap, or a stated range turns a promise into a number someone can sign.

3. What happens to the price when your own costs change? Model costs move. If your costs fall, does the customer see it? If they rise, who carries it? A vendor who can answer in a contract term is easier to approve than one who answers in a sentence.

None of these needs a discount to resolve. They need a clearer structure.

**Closing question:** Which of these can your sales team answer today in one sentence?

**Source line:** none (no figures used). The memo's accuracy thresholds are deliberately not used; see the "do not post" list.

---

## Post 5

- **Pillar:** 3 Counter-intuitive
- **Audience:** AI founders, Heads of Pricing, investors reading pricing posts
- **Bottleneck taught:** 5, the pilot trap and false recurring revenue.
- **Suggested time:** Mon 2026-11-23, 8:30 am ET

**Hook:** A paid pilot is a purchase order for an answer. It is not recurring revenue.

**Body:**

Pilots are valuable. They are how a product earns trust. The trouble starts when pilot revenue is reported, or priced, as if it were a subscription.

Three ways it misleads:

1. The price was set for learning, not steady state. When renewal comes, the negotiation starts from the pilot price. In Nagle's terms, you handed the buyer a reference price before the real offer existed.

2. The delivery cost hides. If people on your side are fixing things behind the scenes, or engineers are embedded at the customer, the revenue says software and the cost says services.

3. Nobody wrote down what converts. What result turns a pilot into a contract, at what price, for how long?

The fix is dull and effective. Write the success criteria and the conversion price into the pilot paper before it starts. Report pilot revenue on its own line.

I have no pilot revenue to report, which is exactly why I am writing the rules down now, before a number makes them awkward.

**Closing question:** If a pilot ends with no conversion price on paper, what is the renewal negotiation anchored to?

**Source line:** none (no figures used). The memo's claim that a large share of pilots fail to convert is deliberately not used.

---

## Post 6

- **Pillar:** 2 Framework breakdown (Nagle, reference price)
- **Audience:** Pricing leaders and founders of AI add-on and workflow products
- **Bottleneck taught:** 6, incumbent bundling and commoditisation.
- **Suggested time:** Tue 2026-11-24, 8:00 am ET

**Hook:** When an incumbent bundles your feature, they do not just take the sale. They reset the reference price to zero.

**Body:**

Nagle's point on reference price: buyers judge what you charge against the alternatives and recent prices they have seen. They do not judge it against your cost or your roadmap.

When a platform includes a capability in a suite the buyer already owns, the comparison stops being "standalone tool A versus standalone tool B." It becomes "this versus included." A narrow add-on charging for a feature a suite could ship has a hard price argument, even if the product is better.

Three responses worth testing:

1. Price the workflow, not the feature. What is the end-to-end job, and what is it worth to finish it?
2. Build switching cost from value, not friction. Customer-specific data and configuration that make the product better over time are a reason to stay. A hard export is only a reason to resent.
3. Segment honestly. Some buyers will take the bundled version and be fine. Price for the ones who need more, and do not chase the rest with a discount.

None of this guarantees pricing power. It describes where pricing power has a chance to exist.

**Closing question:** What reference price does a buyer carry into your category today, and who set it?

**Source line:** none (no figures used). The memo's named-incumbent bundling examples are deliberately not used.

---

## Post 7

- **Pillar:** 1 Diagnostic insight (conceptual, no customer data)
- **Audience:** Heads of Pricing, finance and RevOps leaders considering outcome-based pricing
- **Bottleneck taught:** 3, outcome pricing is lumpy and hard to define.
- **Suggested time:** Thu 2026-11-26 is US Thanksgiving. Recommended: Wed 2026-11-25, 8:30 am ET, or hold to Thu 2026-12-03.

**Hook:** Outcome-based pricing fails first on a definition, not on a price.

**Body:**

Pricing per resolved ticket, per completed claim, per percent saved sounds aligned. Both sides win when the work gets done. But three things have to exist before the number does.

1. A definition both sides can audit. What counts as an outcome, and who decides? Intercom's public Fin page lists $0.99 per outcome and defines a resolution as no further help being requested after Fin's last answer, with a minimum of 50 outcomes a month. That is a clear, checkable definition, which is the point.

2. A baseline. An outcome compared to what? Without one, a savings share is an argument waiting to happen.

3. A forecast range for finance. Revenue now moves with the customer's volume, so both finance teams need a way to estimate next quarter.

Test on your own deal book: what share of contract value is committed, and what share is variable? How many months of history sit behind the variable part?

**Closing question:** Could your finance team and your customer's finance team both reproduce the billable outcome count from raw data?

**Source line:** Intercom, Fin pricing page, https://fin.ai/pricing , retrieved 2026-11-10 (page is undated and subject to change). Quoted: $0.99 per outcome, "No further help is requested after Fin's last answer", "50 outcomes per month minimum".

---

## Post 8

- **Pillar:** 4 Builder narrative (honest, first person)
- **Audience:** Heads of Pricing, RevOps, founders; people who value careful labeling
- **Bottleneck taught:** 1, the cost floor, specifically that you cannot price against cost you cannot measure per customer.
- **Suggested time:** Fri 2026-11-27, 11:00 am ET

**Hook:** I have no customers yet, and the first rule I set for my product is about one word: margin.

**Body:**

My diagnostic reads deal data from a CSV or Salesforce. Those exports often carry a cost field. It is rarely a field a finance leader would trust.

If I labeled a discount against that field as margin, I would be telling someone something I cannot stand behind. So the rule I set: a figure that arrives through a CRM or CSV is called a cost proxy, not margin. Margin language is reserved for cases where the customer states the cost basis in writing, or where cost is read from their own billing system.

It sounds pedantic. It is the same issue that makes AI pricing hard. Revenue sits in billing, cost sits in a cloud or model bill, and the join between them per customer is the hard part. A number that skips the join but wears the word margin is the most dangerous number in the room.

I am not claiming to have solved that join. I am saying the label is part of the work.

**Closing question:** When someone on your team says margin, do they know which cost basis sits underneath it?

**Source line:** none (no figures used). Product statement limited to the live CSV and Salesforce diagnostic and the labeling rule in ADR-006.

---

## Two teardown outlines (longer posts, 1,800 to 2,400 characters each)

Rules for both: only public information, cited by URL and date. Describe what the company changed and said. Do not speculate on motives beyond what the company stated, do not score the company, and do not imply Pricekeel would have done better. Credit the company where it did something right. Suggested slots: after the two-week run, or replace a Tuesday framework post. The founder approves before drafting full text.

### Teardown A: Cursor, June to July 2025, requests to compute

**Pillar:** 2 Framework breakdown. **Bottleneck:** 1 cost floor and 2 packaging. **Audience:** pricing leaders and AI founders.

**Public record (with URLs and dates):**
- 2025-06-16: Cursor published a pricing change for its Pro plan, updated 2025-06-30, with a clarification on 2025-07-04. All on https://cursor.com/blog/june-2025-pricing (author Michael Truell). The post describes: before, external models billed by request, with a limit of 500 requests a month and Sonnet models counting as two; after, Pro includes unlimited Tab and Auto plus $20 of frontier model usage per month at API pricing, with more available at cost. Cursor states it was not clear that "unlimited" applied to Auto and not to other models.
- 2025-07-04: Cursor apologized and offered refunds for unexpected charges for usage from 2025-06-16 to 2025-07-04 (same URL).
- 2025-07-07: TechCrunch reported the apology and Cursor's stated reason: newer models can use more tokens per request on longer, multistep tasks, and Cursor had absorbed those costs under the old plan. TechCrunch also reported the $200 a month Ultra plan introduced days after 06-16. https://techcrunch.com/2025/07/07/cursor-apologizes-for-unclear-pricing-changes-that-upset-users/

**Outline:**
1. Hook: "A request is a unit the vendor understands and the customer understands. A token is only one of them. Cursor's 2025 change is a clean look at what happens when the unit drifts from the cost."
2. What changed, in three plain lines, with dates and the URL.
3. The mechanism, in the company's own words: the cost per request moved as models used more tokens on longer tasks. A flat per-request limit tied to a cost that was moving.
4. What the new unit trades off: it matches cost better (usage at API rates) and is harder for a buyer to forecast. Apply the three value metric tests from post 2.
5. The part worth copying: the company said it had not communicated clearly, took responsibility, and offered refunds, in public and within about three weeks of the first post (06-16 to 07-04). Pricing communication is part of the price.
6. Takeaways for a pricing leader: define the unit in the customer's language, show usage before the bill does, set caps or alerts by default, and write the change log before the change.
7. Closing question: "When your unit's cost changes under you, how does your customer find out: from you, or from the invoice?"

**Do not say:** that users left, that revenue fell, or anything from third-party commentary on sentiment. Only the cited facts. Keep the tone as a case study of a hard problem.

### Teardown B: Salesforce Agentforce, one product, several units

**Pillar:** 2 Framework breakdown. **Bottleneck:** 2 packaging paradox and 3 value metric. **Audience:** pricing leaders, CFOs, RevOps.

**Public record (with URLs and dates):**
- 2025-05-15: Salesforce announced Flex Credits: $500 for 100,000 credits, with an Agentforce action using 20 credits, or $0.10. The release names its earlier conversation-based pricing as $2 per conversation, and cites a Salesforce survey that 90 percent of CIOs say managing AI costs is limiting their ability to drive value (a Salesforce claim; attribute it to Salesforce, do not adopt it). Release: https://www.salesforce.com/news/?p=87214 (the Business Wire copy is https://www.businesswire.com/news/home/20250515332990/en/ ; it returned 403 to my fetch, so cite the Salesforce copy).
- Retrieved 2026-11-10: the Agentforce pricing page lists Flex Credits at $500 per 100k credits, conversations at $2, per-user add-ons at $125 and $150 per user per month, a $5 per user per month Agentforce User License that requires Flex Credits, an Agentforce Coworker User License at $50, and Max Edition from $550 per user per month. https://www.salesforce.com/agentforce/pricing/ . The page is undated and "subject to change", so cite it as "as retrieved 2026-11-10".

**Outline:**
1. Hook: "One vendor, one agent product, and three different units on the public price list: a conversation, an action, and a user."
2. What the May 2025 release changed and why Salesforce said it did it (in its words: pricing aligned to how agents deliver outcomes, let customers start small).
3. What the page lists now, as a table in the post or carousel: unit, price, who bears usage risk.
4. Read it with a framework: for each unit, who carries the volume risk, the vendor or the customer? Per-user puts it on the vendor, per-action on the customer, credits split it by prepayment. This is the packaging paradox from the Consumer Trends memo, visible on one public page.
5. What it teaches: the right unit is not settled even at the largest vendor, and offering several is a way of letting buyers choose their own risk. It is also harder to explain. Fine to say so as an observation, not a verdict.
6. Takeaways: write down who carries volume risk for each unit you offer; if you offer more than one, state the switch rule.
7. Closing question: "For each unit on your price list, who carries the risk when volume doubles?"

**Gaps to close before drafting:** I did not retrieve the original date of the $2 per conversation launch, and the pricing page is undated. Confirm both with the Internet Archive (https://web.archive.org/) and cite the capture dates, or say "earlier pricing, per the May 2025 release" and nothing more. Do not state when per-user options appeared without a dated capture.

**Do not say:** that any option is better or worse, that customers prefer one, or anything about Salesforce revenue.

---

## The ten-word line

The series should repeat one line, in the same words, as the last line of the profile About paragraph, the sign-off of each post where it fits naturally, and the title of any carousel. It should describe a practice, not a product capability, so it can be true on day one.

**Candidates (word counts checked):**

- **A.** "Price AI products against what each customer costs, not seats." (10)
- **B.** "Pricing is a system: see where your price leaks first." (10)
- **C.** "Know your cost to serve before you choose a unit." (10)

**Recommended: C, "Know your cost to serve before you choose a unit."**

Why it stays inside the evidence boundary:
- It states a sequence of work (measure cost, then choose the pricing unit), which anyone can follow and no one can falsify with our numbers. It claims no result, no customer outcome, and no Pricekeel capability.
- It does not say Pricekeel computes cost to serve. The live product does not yet join revenue to per-customer inference or storage cost, and under ADR-006 a CRM or CSV cost figure is a proxy, not margin. The line is advice to the reader, not a product promise.
- It covers bottlenecks 1 to 3 in one sentence (cost floor, packaging, value metric), so every post in the series can point at it honestly.
- It avoids the memo's example line ("We stop AI companies from losing money on heavy users"), which is a capability and outcome claim we cannot support today, and avoids "proven" or guarantee language.

Why not the others: A asserts that seats are wrong for AI, which rests on the memo's argument rather than a source we have named, and reads as a verdict. B matches the manual's existing through-line ("pricing is a system, not a number") and is safe, but it is about discount leakage in general and is less specific to this series; keep it as the fallback and as the brand-level line. Proposal for the founder, not an edit: add the chosen line to the through-line section of [[linkedin-strategy]] if it is approved.

---

## Do not post: memo claims that cannot be sourced

Each memo figure was searched on 2026-11-10. Status below.

**Sourced, in use with attribution and caveat**
- 80 to 90 percent traditional SaaS gross margins, in contrast to AI: Bessemer Atlas, 2025-11-10, used in post 1 as Bessemer's own framing. Bessemer gives no underlying citation, and a fal co-founder is quoted as saying no one in AI really has 80 to 90 percent. Do not state it as a measured industry fact, and do not add the article's 40 to 50 percent AI figure without further sourcing.

**Not sourced, do not post**
- Storage growing from 5 percent to over 50 percent of COGS: no source found. Related material exists (MIT Technology Review, 2026-10-22, argues storage is an overlooked, compounding cost for generated media) but it gives no such figures. A qualitative statement that storage can compound could cite that piece after the founder reads it; the numbers cannot be used.
- Foundational model creators losing $1.60 to $3.00 per dollar of revenue: not supportable as written. Secondary outlets report OpenAI spending about $1.60 per dollar of revenue in 2025 (an expense ratio, not a loss), and other reports use different bases (adjusted operating margin, cash burn, net loss) that vary by period. Most are reporting on leaked or unaudited financials. The memo's range and its framing as "lose" mix definitions. Do not post.
- Enterprise buyers will not pay full rates until accuracy reaches 97 percent, and 60 to 70 percent accuracy being enough to raise money or get a trial: no source found. The closest material says buyers distrust a single accuracy number and want task-specific evidence, which supports a qualitative point, not the figure.
- Legal-tech buyers rejecting per-use pricing in favour of $6,000 per seat per year: no source found. The nearest data point is a vendor, Spellbook, stating enterprise platforms start at $500 per seat per month ($6,000 a year when multiplied), which is a list price and says nothing about buyer preference. Reports that Legora moved to usage pricing while Harvey kept seats are split evidence, not support for the claim.
- "Software budgets of $20 to $50 a month versus labor budgets of $5,000 to $20,000 a month or $500 to $1,000 per contract or claim": no source searched or found. Do not post.
- Opus Clip at a $215M valuation, Casetext's $650M exit, Searchable at an $85M valuation and $1M ARR in 60 days, the "Matt and Precision" anecdote: not verified here. Do not cite in any post, since none teaches a pricing point and each is a third-party claim.
- "A large portion of AI pilots fail to convert": no source. Post 5 argues the mechanism without the claim.
- Microsoft, Google and Zoom bundling AI notetakers for free and "wiping out pricing power overnight": not verified and disparaging in tone. Post 6 uses the mechanism without naming companies.
- "Customers cancel immediately if outputs are hallucinated" and "discounting to win early logos signals low quality": generalizations with no source. Phrase only as the founder's own opinion if at all, never as a finding.
- Any Pricekeel claim from the Opportunity tab: "optimized packaging structure in 14 days", a "Margin Health Score", $2,500 a month, "recover $50,000 in leaked margins", "double contract values", "we stop AI companies from losing money on heavy users", "autonomous outcome engine". The audit motion and calculator are in design under [[2026-11-10-audit-first-motion-and-ai-margin-wedge]], not live, and the pricing is under review. None belongs in a public post.
- Anything that calls a CRM or CSV figure margin (ADR-006). Use "cost proxy, not margin" or avoid the word.

## Approval checklist for the founder

1. Approve, edit or cut each of the eight posts individually, including the two lines that disclose having no customers or pilot revenue (posts 5 and 8).
2. Decide the Thanksgiving slot for post 7.
3. Choose the ten-word line.
4. Approve the teardown outlines, and have the two Internet Archive captures checked before teardown B is drafted in full.
5. Decide on the proposed edits to [[linkedin-strategy]] (link-penalty note, overdue algo review, ten-word line). I have not made them.

Nothing in this file has been published, scheduled, or connected to any social account.
