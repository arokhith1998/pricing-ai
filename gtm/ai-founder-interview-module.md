---
title: 'AI founder interview module: 30-minute guide on pricing, cost and billing friction'
created: 2026-11-10
updated: 2026-11-10
tags: [gtm, interviews, ai-founders, discovery, audit-first, ai-margin]
status: draft
source: 'gtm/research/2026-11-10-founder-sheet-consumer-trends-and-opportunity.md (Opportunity moves 2 and 5; 30-day checklist; Consumer Trends bottlenecks 1, 2, 3, 5)'
---

# AI founder interview module (30 minutes)

Purpose: the first line of the founder's 30-day checklist, "10-15 B2B or AI founders about how they currently decide on pricing and where their billing causes friction." This module serves the **audit-first motion** for seed-to-Series-A AI companies moving from flat or per-seat pricing to usage or outcome pricing. Decision record: `vault/Decisions/2026-11-10-audit-first-motion-and-ai-margin-wedge.md`.

This is a separate module from `vault/GTM/problem-interview-guide.md` (the 20-minute discount-exception guide for RevOps and Pricing champions at $10-100M ARR Salesforce companies). That guide is owned by PK-18 and is not edited here. Do not mix the two scripts in one call. Questions in section E below overlap its optional module 7a to 7f on purpose, so answers can be compared across the two ICPs.

## Ground rules

- **Drafts only.** The founder runs every interview and sends every message. Nothing here is sent by an agent.
- **No customer data.** Do not ask for, accept or record any customer names, invoices, screenshots, API keys or provider bills. Ranges and round numbers are enough. If a founder starts reading customer names or sharing a screen with billing data, say "let's keep it to round numbers, I do not need names" and stop them. Notes hold aggregates only.
- **Research frame, not a pitch.** The interview earns learning. The audit is offered only in the close and only on strong signal.
- **Past tense and specifics.** "Tell me about the last time" beats "would you ever." Hypotheticals produce courtesy answers.
- **Notes and recording.** Ask permission to take notes at the start. Record only with an explicit yes.
- **This is a hypothesis check, not a confirmation exercise.** The sheet is the founder's synthesis of operator playbooks, not verified fact. The interviews must be able to say no. Falsifiers are listed at the end.

## Marker used below

**[NL]** = must not lead the witness. For each [NL] question the neutral wording is given, with the phrasing that is banned. If you catch yourself using the banned version, rephrase and note it in the log so the answer is discounted.

## Opening framing (say it, roughly, before Q1; 2 min)

> Thanks for making time. Context so it is not a surprise: I am pre-product, researching how AI companies decide pricing and handle billing when costs move with usage. This is a research conversation, not a sales call. I am not going to pitch software and I am not asking for any of your data. Please keep to round numbers and no customer names. I would like to understand what you actually do today, including the unglamorous parts. Is it okay if I take notes? And I will not record unless you say yes.

## The questions (30 minutes)

Time boxes sum to 30. If you are at minute 20 and have not reached section G, skip F and the second half of C.

### A. Warm-up (3 min)

1. What does {{company}} sell, and who signs or pays on the customer side? Listen for: buyer title, company size, whether the buyer is a team or a person.
2. Roughly where are you: customers, and revenue in a range? Ranges are fine. Listen for: stage, whether the ICP gate (seed to Series A, some real revenue) holds. Do not ask for exact figures.
3. **[NL]** Which model providers or GPU and storage vendors does the product depend on today? *Banned:* "Is OpenAI eating your margin?" or "Do model costs worry you?" Listen for: concentration on one provider, bring-your-own-key, multiple models, own-hosted.

### B. How they set price and packaging (4 min)

4. Walk me through what a customer sees on an invoice, line by line.
5. **[NL]** Who set that pricing, when, and what did you use to decide? *Banned:* any suggestion of method ("did you benchmark competitors?", "did you do cost-plus?"). Let them name the method, including "gut" and "copied a competitor". Those are signal too.
6. **[NL]** Has the pricing or packaging changed since launch? What happened, and what was the trigger? If no change: "What would make you change it?" *Banned:* "When did you realize per-seat was not working?" Listen for: the actual transition (flat or seat to credits, usage or outcome), who decided, what customers said, whether grandfathering happened.

### C. Where inference and storage cost shows up in their decisions (3 min)

7. **[NL]** When you set that price and those limits, what did you know about what a typical customer costs you to serve? Where did the number come from? *Banned:* "Did you model token costs?" Listen for: measured, estimated, or not known.
8. How often does anyone look at cost per customer now? Who? Listen for: owner named, cadence, or "nobody".
9. **[NL]** Besides model calls, what other costs grow as a customer uses the product? *Banned:* "Does storage blow up on you?" Listen for: storage, retrieval, embeddings, logs, human review, support. Whether they volunteer it unprompted is the signal.

### D. Heavy-user and negative-margin stories (4 min)

10. Tell me about the customer who costs you the most to serve. How did you find out, and what did you do?
11. **[NL]** Tell me about a time a customer's usage surprised you. *Banned:* "Have you had heavy users lose you money?" Follow up with: what did it cost, in a range; how long before you noticed; what changed afterward (limits, repricing, a conversation, nothing).
12. **[NL]** Has any customer, plan or feature ever cost you more to serve than it brought in? How do you know, and how sure are you? *Banned:* "Are you gross-margin negative?" Listen for: a story with a magnitude and a date, versus "probably, but I have not checked". The second is a real answer: record it as "suspected, not measured".

### E. Reconciling model-provider bills against billing today (4 min) [the manual-workaround test]

This section tests the sheet's claim that founders are already "manually reconciling monthly OpenAI API bills against Stripe customer subscriptions on spreadsheets". Do not name that workaround. Let them describe their own.

13. **[NL]** Walk me through the last time you had to connect a provider bill to what customers paid. What did you open, in what order? *Banned:* "Do you reconcile your OpenAI bill against Stripe in a spreadsheet?" Listen for: named artifacts (sheet, script, warehouse query, dashboard), the join key (customer ID, API key, tag, project), what is a guess.
14. How long did it take, who did it, and how often does it happen? Listen for hours, a named person, a cadence.
15. **[NL]** What tools are involved: billing system, metering, provider dashboards, a warehouse, nothing? Did anyone build something? *Banned:* naming Stripe Billing, Orb, Metronome, Lago, or any vendor before they do.
16. When was the last time the answer changed a decision? What was the decision? This separates a ritual from a pain.

### F. Buyer pushback on usage billing (3 min)

17. When a customer or prospect pushes back on how you charge, what do they say? Give me the last example.
18. **[NL]** Has a deal stalled or been lost over the pricing model? What did you offer instead (caps, commits, tiers, a flat fee)? *Banned:* "Do buyers hate usage-based pricing?" Listen for: who objects (end user, procurement, finance), whether the concession cost margin.
19. Who on the customer side asks for predictability, and what form does it take (annual commit, hard cap, alerts)?

### G. Pilot-to-ARR conversion (2 min)

20. **[NL]** Of the pilots or paid trials you started in the last year, roughly how many became recurring contracts? How were the pilots priced? *Banned:* "Do your pilots fail to convert?" Listen for a ratio, even rough, and whether pilot revenue is counted as ARR in their own reporting.
21. **[NL]** What did a pilot cost you to deliver, including anyone's hours behind the scenes? *Banned:* "Are you doing human middleware?" Listen for: engineer hours, forward-deployed time, manual output review.

### H. The 10-word clarity test (1 min, then ask about price)

Run this after sections A to G, so the earlier answers are unaided. Say one line, then stop talking and watch the reaction. Alternate which line you use across interviews and log which.

- Line A: "We stop AI companies from losing money on heavy users." (10 words)
- Line B: "We find which customers cost more than they pay." (9 words)

> Before I ask about anything else: one line on what I am exploring. [say the line]. Without me explaining it further, what is your reaction?

What the reaction counts as:

| Reaction | Reads as | Log as |
|---|---|---|
| Asks "how much?", "when?", "how does it work?", or "can I try it?" unprompted | Strong. The sheet's test: asking for the price instead of saying "cool". | `asked_price` |
| Describes their own version, "that is the thing I do on Fridays in a sheet" | Strong, and it confirms the workaround from section E. | `named_own_workaround` |
| Asks "do you integrate with X?" or "who else uses it?" | Medium. Buyer evaluation behavior, but cheap to say. | `evaluating` |
| "Cool", "interesting", "makes sense", nods | Courtesy. No signal. | `polite` |
| "We already do that" with a specific tool or process named | Competitor or workaround found. Valuable. Ask what it misses. | `already_solved` |
| "That is not our problem" with a reason | Disconfirming. Valuable. | `not_a_problem` |

Honest caveats: a founder on a research call you framed as non-sales is being kind by default, so `asked_price` is a stronger signal here than it would be on a sales call, and "polite" is the base rate. This test is the sheet's heuristic, not a validated instrument. One strong reaction is an anecdote. Treat it as signal only if the same founder also gave a specific story in D and a named workaround in E.

If they ask "how much?", log it, then ask "what would you expect it to cost?" before saying any number. Do not quote the $2,500 a month anchor from the sheet: it is pending the strategist and CFO review.

### I. What they would pay for a 14-day audit (2 min)

Only now describe the audit, in neutral terms, as a service, not software:

> Hypothetically: someone spends 14 days with your billing export and a cost export from your providers, and hands back a written read of margin by customer, where heavy users sit, and two or three packaging options. A service, not a product. I have not run one yet.

Keep "I have not run one yet". It is true, and it is the house rule on honesty.

22. **[NL]** What would you need to see before you would consider something like that? Who else would have to agree? *Banned:* "Would you pay for that?" Listen for: a named co-decider, a security or data objection, a time objection.
23. What have you paid for pricing or finance help before, and roughly how much: advisor, consultant, fractional CFO, a tool, a hire?
24. **[NL]** At what price would that be so cheap you would doubt it, and at what price too expensive to consider? *Banned:* stating any figure first. Record both numbers as their ranges, not as a quote.
25. **[NL]** What would you want to hand over for it to work, and what would you not? *Banned:* "Would you share your Stripe export?" This is the data-authorization test. Listen for: cost export shareable as a percentage or per-customer ID; billing export with account names stripped; "never".

### J. Close (2 min)

Choose by signal tier from the scorecard below. Never choose the audit offer by default.

**Strong signal (audit offer).**

> Based on what you described, I think a short written audit could be useful to you, but only if you agree. I would send you one page describing exactly what I would need and what you would get, and you decide. No data changes hands on this call. Is that okay? And is there anyone else on your side who should see it?

Send nothing until the audit one-pager exists and the founder has approved it. Under ADR-006 any cost basis from a founder-supplied export is labelled `declared_cost`, never "verified margin".

**Medium signal (follow-up).**

> This has been really useful. Could I come back in a month with a short note on what I am hearing across founders, no names, and see whether it matches your experience?

**Weak signal or not a problem (honest close).**

> Thank you, this is genuinely useful for me to know. It sounds like this is not a live problem for {{company}} right now. If that changes I would love to hear.

**Every call, last question:** "Who else is dealing with this that I should talk to?" Warm intros beat cold lists. Record the introducer only as a role unless they say a name aloud and agree to the introduction.

## Signal scorecard (fill in within 24 hours)

Score each dimension 0 (no evidence or contradicted), 1 (vague, hypothetical, or "we plan to"), 2 (specific, past tense, with a number, name or date).

| Dimension | Source questions | 2 means |
|---|---|---|
| Pricing transition | 4, 5, 6 | Changed pricing in the last 12 months or is mid-change, and can say why |
| Cost visibility | 7, 8, 9 | Measures cost per customer, or can name exactly why they do not |
| Heavy-user or negative-margin story | 10, 11, 12 | One concrete story with a magnitude and a date |
| Manual workaround | 13, 14, 15, 16 | A named artifact, an owner, hours or a cadence, and it changed a decision |
| Buyer pushback | 17, 18, 19 | A specific lost or stalled deal, or a concession that cost margin |
| Pilot-to-ARR | 20, 21 | A ratio given, or admits pilots are counted as ARR |
| Clarity test | H | `asked_price` or `named_own_workaround` |
| Willingness to pay and access | 22 to 25 | Gave a price range from real spend history, named a co-decider, and named what they would share |

Interpretation, with the honesty rule applied:

- **12 to 16: audit-ready conversation.** Offer the audit in the close. It is still **only a positive interview** until money moves.
- **7 to 11: promising.** Follow-up ask, intros, a second call.
- **0 to 6: not a fit now.** Log reasons. This is a useful result, not a failure.

**What counts as validation in this motion.** A positive interview is not validation. Following the sheet's own test, the first real validation is a founder who commits money for a paid audit (card out or signed), plus agreement on what data they will hand over. Interest, praise, "send me the one-pager" and an intro offer are logged as positive interviews. If a call scores 12 or more but section I produced no price range and no data answer, say so plainly in the notes field.

## Falsifiers (propose these to the founder; stop and rethink if they hold)

After 10 completed interviews, the thesis is in trouble if any of these hold:

- 6 or more say they have not looked at cost per customer and do not plan to in the next two quarters.
- 6 or more describe reconciliation as a solved, trivial task (provider dashboard, off-the-shelf metering, a 10-minute query) with no recurring pain.
- Fewer than 3 give a concrete heavy-user or negative-margin story with a magnitude.
- Nobody names a price range or a data-sharing path in section I, even among high scorers.
- The clarity test returns `polite` or `not_a_problem` in 8 or more of 10.

Also watch for the opposite failure: a pattern of founders who say everything is fine because they check the provider dashboard weekly. That may mean the problem is real but the buyer is an operator, not a founder, which changes the ICP.

## Log fields per interview (proposal, see outreach file for tracker columns)

Date, company, founder title (role only), stage as stated, provider dependence (single / multiple / own-hosted), pricing model today, transition status, cost visibility (measured / estimated / unknown), heavy-user story (y/n and magnitude range), reconciliation method and hours per month, clarity line used and reaction code, audit price range as stated, data-sharing answer, co-decider role, close outcome, scorecard total, and a plain-language note including any leading-question slips.

## Related

[[ai-founder-targets]] · [[ai-founder-outreach-sequence]] · [[objection-inventory]] · [[problem-interview-guide]] · [[2026-11-10-audit-first-motion-and-ai-margin-wedge]]
