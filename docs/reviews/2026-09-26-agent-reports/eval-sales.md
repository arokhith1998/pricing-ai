# Pricekeel sellability evaluation, 2026-09-26

## Verdict

The engine and demo path are ahead of the GTM motion meant to sell them. The diagnostic and copilot code are legitimately CFO-credible: deterministic, receipts-first, methodology-cited, and honest about their own limits. The landing page's claims track what the engine actually outputs, including an explicit "V1 boundary" that a VP Finance buyer would respect rather than distrust. But the binding constraint the Aug 1 decision named has not moved: the 15-interview validation program is still close to zero real touches, the GTM collateral sales would use in the room is three-plus months stale and describes an ICP the product no longer targets, and two structural gates (Salesforce customer-install distribution, legal/insurance readiness to accept real data) are still open. This is sellable in principle, not yet demoable end-to-end to a real buyer's real org, and not yet safe to accept a real customer's CSV.

## Top 6 findings

1. **Critical: validation program stalled near zero.** `vault/Boards/pricekeel-board.md:26` still lists "15 problem interviews, five data-readiness reviews... two paid 90-day pilots" under "This Week" (board last updated 2026-08-02). `gtm/llama-ventures/traction-update.md:29-34` (2026-09-11) says plainly: "Two design-partner conversations in progress. Intro calls only. No NDA, no data received, no commitment, no revenue." `docs/ops/funnel-tracker.csv:1-2` is header-only. Recommendation: pause all other work; run a pure sourcing/interview sprint for two weeks against the current ICP, log every real touch to the tracker as it happens.

2. **High: GTM collateral describes the wrong, stale ICP.** `gtm/personas.md:1,11,24-30` (created 2026-06-11) targets "$15-45M ARR... Salesforce or HubSpot" and a 120-150 contact list; `gtm/outreach-sequence.md:1-16,46-52` still carries "Through Jun 30 only" / "Jul 1 onward" seasonal hooks, three months expired. The live ICP is `vault/Competitive/2026-08-01-salesforce-market-need-assessment.md:61-74`: $20-100M ARR, Salesforce-only, 500+ closed outcomes. Recommendation: rewrite personas, outreach-sequence, and design-partner-targets around the Aug 1 Salesforce-first ICP before the next outreach batch; today the founder is armed to sell a CSV-diagnostic wedge that pricekeel.com no longer leads with.

3. **High: distribution to a real customer's Salesforce org is unproven.** `vault/Boards/pricekeel-board.md:25`: "prove customer distribution... A source-org app is not sufficient customer-install evidence" is still open. Recommendation: do not commit to a pilot start date until the packaged (2GP) app installs cleanly in a subscriber org; a live prospect call will expose this gap within minutes of asking "how do I install it."

4. **High: legal/data-acceptance readiness unresolved.** `vault/Boards/pricekeel-board.md:29`: "Close the real-data readiness gates... legal-entity, counsel, methodology-advisor, and cyber/E&O insurance status before accepting a customer CSV" is still open. Recommendation: close entity and insurance status before offering the first NDA; a CFO-level economic buyer will ask this directly, and "in progress" is a credible answer only once.

5. **Medium: objection-inventory internally contradicts the current ICP.** `gtm/objection-inventory.md:23` still answers "Why not Pricefx/Vendavo" with "$15-60M ARR usage-based teams," but `web/src/app/page.tsx:53` and the Aug 1 doc say $10-100M ARR with a 500+ closed-outcome floor, which the objection inventory never mentions or defends. Recommendation: add a talk track for "we don't have 500 closed deals a year" / "why Salesforce-only now," and fix the ARR figure everywhere it recurs.

6. **Medium: synthetic data still stands in for a real first readout.** `pricekeel-board.md:24`: "Prepare at least 30 closed test Opportunities" is still "This Week," and the site itself discloses the sample "runs the real engine on a synthetic 2,000-deal book" (`web/src/app/page.tsx:45`). Fine as a public sample; the risk is letting a polished demo substitute, in the founder's own head or in a prospect call, for evidence that the engine has ever run on a real customer's data.

## Three genuinely good things

1. The landing page is unusually honest for pre-revenue: the "V1 boundary" section (`web/src/app/page.tsx:121-140`) states outright that Salesforce data alone cannot support true margin or application-level recommendations, which matches `pricing/schema.py`'s explicit not-yet-built `cogs_acv` hook rather than overselling it.
2. The diagnostic/copilot engine is legitimately finance-credible: `pricing/diagnostic.py` leads every output with "what we read from your file" before any conclusion, and `pricing/copilot.py`'s `_RECOVERABLE_CAVEAT` and system prompt (lines 506-521) forbid the LLM from inventing numbers and force every dollar figure to disclose it is correlational, not bookable margin.
3. The organization is catching its own dishonesty before it ships: `gtm/llama-ventures/traction-update.md` separates "VERIFIED, in code" from "NOT TRUE, do not say it" line by line, and the team already caught and relabeled synthetic funnel rows (`docs/ops/funnel-tracker-example.csv`) rather than letting them count as traction.

## One thing to do next week

Stop all product and collateral work and run five real, scheduled problem interviews against the Aug 1 Salesforce-first ICP, pairing a CFO/VP Pricing economic buyer with a RevOps/Deal Desk champion where possible, and log every touch to `docs/ops/funnel-tracker.csv` in real time. That is the only artifact that moves the actual binding constraint.
