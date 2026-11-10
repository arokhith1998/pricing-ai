# Customer success review: design-partner pilots and onboarding

**One line:** A non-Salesforce pilot is feasible only as a CSV-first, one-surface slice (a quote or billing export plus a CRM export, discount-governance only); cost data, BOM, margin and physical-goods asks would scare off a first $15K partner and should not enter the pilot or the interview script as offers.

## 1. Findings

- Every GTM asset assumes a CRM-shaped record. The ICP names "Salesforce or HubSpot + Stripe/Zuora" (`vault/Customers/ideal-first-design-partner.md`). The wedge is "CSV of last 4 quarters of closed deals" with list price, booked price, discount reason, approver. The interview target plan already says "do not assume Salesforce" and objection 4 already handles HubSpot (`vault/GTM/interview-target-plan.md`, `objection-inventory.md`). So CRM-agnostic is supported at the conversation layer. Nothing yet covers quote tools, billing systems, or where an approval actually happens.
- The data-handling SOP is built for one-off CSVs: web upload in memory, or email to a BitLocker folder with hash log and 30-day deletion (`docs/ops/data-handling-sop.md`). It fits a quote-tool or billing export. It does NOT fit a live API connection to Stripe or Chargebee, which implies stored tokens, ongoing pulls and a different breach scope. `docs/ops/incident-response.md` and the data register scope "what we hold" by file; there is no row type for OAuth tokens or event streams.
- The NDA addendum has purpose limitation, no-training, and an opt-in benchmarking clause (section 9, default off, minimum cohort of 10) (`docs/legal/one-page-mutual-nda-data-addendum.md`). It says nothing about cost data. BOM, landed cost and tax are a different sensitivity class (supplier terms, margin structure) than discount data. Benchmarking cost data across customers would be very hard to get consented, and a cohort of 10 is unreachable for a long time.
- The problem-interview guide tests only discount-exception pain (15 questions). Q6 asks where the decision is recorded, which is the closest hook to "where deals are priced." Nothing asks about cost data, usage commits, or AI-native contract structure (`vault/GTM/problem-interview-guide.md`).
- The target list is already AI and infra heavy (Deepgram, Baseten, Pinecone, AssemblyAI). That is the right pool for direction 3(a), and none of it is physical goods, so margin guidance from BOM has no interviewee in the current plan.
- Funnel tracker is header-only. There are zero verified partners (`docs/ops/README.md`). Every claim below about what a partner would pay for is a hypothesis.

## 2. What would have to change

**(1) Non-Salesforce pilot shape**

Data-readiness review, same four gates (500+ closed outcomes, reliable list and booked values, documented discount policy, named policy owner), asked as a column list, not data:

- **Quote or CPQ tool (DealHub, PandaDoc, Proposify, Salesbricks):** export of quotes with line items, list price, quoted price, discount percent, approval chain and timestamps, quote status, and a deal ID or customer ID. Value: this is where approver and timestamps live, often better than the CRM.
- **Billing (Stripe, Chargebee, Maxio):** subscription and invoice export: customer ID, plan, price, coupon or discount, start date, committed amount, invoiced amount. Value: shows booked-versus-billed truth. Weakness: no win/loss, so no win rate by band.
- **Other CRM (Pipedrive, Zoho, Close, Attio):** deals export with won and lost status, value, owner, close date, lost reason.
- **The gate that matters:** win rate by band needs closed-lost, and closed-lost lives only in the CRM. A billing-only or quote-only partner can get leakage and price realization, not win rate. Say so before the pilot, not at the readout.
- **Join key:** the pilot fails quietly if quote ID and CRM deal ID do not match. Ask "is there a shared deal ID across the three systems" in the readiness review.
- **Access method:** CSV or XLSX export only for pilot 1. Defer API and OAuth for Stripe or Chargebee. Metronome and Orb event streams are out of scope: row-level usage events are the highest-volume, highest-sensitivity data and break the in-memory-and-delete posture.
- **Time-to-first-readout:** the under-2-weeks target is credible for CSV exports of one quote tool plus one CRM, counted from validated intake (SOP step 1). Add 3 to 5 days for the mapping and join work if three systems are involved. Do not promise 2 weeks for three systems.

**Consent and NDA language to add (drafts for counsel review, founder acts):**

- A "data classes" schedule to the addendum: Class 1 deal and price data (covered today); Class 2 usage events (aggregates or monthly rollups only, no row-level events, no end-customer identifiers); Class 3 cost data (BOM, landed cost, tax). Class 3 is accepted only as a customer-supplied rate or margin-percentage table by product family, never supplier names or part-level BOM, and is excluded from section 9 benchmarking entirely.
- Billing credentials: no API keys or OAuth tokens held in the pilot. If that changes, revoke-on-request within 24 hours and a data register row for the token.
- Extend the register and incident-response scoping to name these classes.

**(4) Recurring-usage measurement for a non-CRM surface**

The success metric (recurring exception decisions through the loop, per the subscription-usecase decision note) cannot depend on a CRM webhook. Use the decision record as the source of truth:

- Count decisions logged in Pricekeel per week per partner (a request, a recommendation, a human decision, a reason), tagged with a source surface (quote tool, billing change, CRM, standalone screen).
- Define "recurring" as 3 or more decisions in each of weeks 4 to 12, from at least 2 distinct requesters. Founder confirms the threshold.
- Without a push integration, usage will be manual entry or paste of a quote ID. That is a real friction risk: a standalone quote screen may be used only when the champion remembers. Measure share of the partner's exceptions (their count, from their own quote tool export) that went through the loop. That coverage ratio is the honest number, and a low ratio is a finding, not a failure.
- Do not count readouts delivered or logins.

## 3. Which directions a first partner would pay $15K to pilot

| Direction | Pay $15K for pilot? | Reasoning |
|---|---|---|
| Platform-agnostic intake (CSV from quote tool, billing, other CRM) | Yes, this is the pilot | Removes the "we are not on Salesforce" disqualifier. Smallest scope. |
| Deal-time guidance in Slack, email, standalone screen | Maybe, as pilot phase 2 | Closes the usage gap in (4). Standalone screen first. Browser overlay and email are build-heavy and unvalidated. |
| Usage-native pricing for AI-native (commits, ramps, overages) | Probably the strongest pull, but only on the right account | AI infra companies in the target list feel commit-setting pain and deflating unit cost. Risk: V1 does not score commits or overages, so the pilot would sell something not built. Scope the pilot to commit-and-ramp capture plus a descriptive readout, labelled as such. |
| Price recommendation, scenario and elasticity | No for a first partner | Needs volume and history a first partner lacks, and "insufficient data" will fire often. Premature. |
| Customer-level value-based pricing | No | Needs willingness-to-pay inputs no partner will have ready. Reads as consulting. |
| Margin guidance from BOM, shipping, tax | Would scare off | Asks the buyer to share cost structure with a pre-revenue, solo-founder vendor. Different buyer (finance or ops, not RevOps), physical goods, and gated in the Phase-3 sizing note on the SaaS wedge paying first. Not a pilot feature. |

For AI-native SaaS the margin question is real but narrower: gross margin per usage unit (inference cost per token against price). Treat that as a later interview topic, with a single customer-supplied cost-per-unit input, not BOM.

## 4. Interview questions to add (the next ten interviews)

Add as a 6-question module after Q7, optional, to stay inside 20 minutes. Do not pitch. Ask only about the past, per the existing guide's rule.

Where deals are priced:
1. In your last three negotiated deals, which tool did the final price and discount get set in: CRM, a quote or CPQ tool, the billing system, or somewhere else? Which one holds the approval record?
2. Is there one deal ID that appears in your CRM, quote tool and billing system, or does someone reconcile by hand?

Cost data (listen for sharable versus not):
3. When a deal is discounted, does anyone check what the deal costs you to serve (inference, compute, support, landed cost)? Where does that number live and who owns it?
4. If it were useful, could that number be shared as a percentage by product family, or is cost data off limits outside finance?

AI-native commits:
5. How did you set the commit on your last large usage deal, and what happened when actual usage came in far under or over it? Did you give credits, true-ups, or re-paper?
6. Over the past year, how did falling unit costs change what you charge or what customers ask for? Did you reprice, and who decided?

Log these as new fields in the interview notes: pricing surface, cost-data availability (none, internal only, shareable as percentage), commit-setting method, and reprice event (yes or no). Add one disqualifier line: if the answer to Q3 is "never checked" and no one owns it, margin guidance is a solution without a buyer for that account.

The 20 target accounts are mostly AI and infra, so Q5 and Q6 will get answers. Q1 and Q2 will tell whether the founder's premise (most deals not on Salesforce or HubSpot) holds for this ICP. That is a hypothesis stated, not evidence, and ten interviews can falsify it.

## 5. Risks and tradeoffs

- **Scope creep against the critical path:** the board's critical path is still the first paid pilot. Every new direction adds interviews' worth of unknowns before any partner exists. A broader pitch lowers the chance of a clean yes ("what exactly are you selling").
- **Honesty gap:** pitching usage-native or margin guidance when V1 scores only discount on committed ACV would violate the "name your method, never overclaim" rules. Pilot copy must say what is scored.
- **Billing-platform entrants:** neutrality is the defensibility argument, but a partner on Stripe or Chargebee may ask "why not their native tool." Have the answer ready, plus the two CEO diligence answers ("who else uses this" is currently "no one, you would be first," which must be said plainly).
- **Cost data is toxic early:** one cost-data request in a first call can end the relationship. Hold it until after a signed pilot.
- **Data-handling load:** each added surface adds files, joins and register rows for one person on a machine with a known corruption problem. Cap pilot 1 at two sources.
- **Time-to-readout:** the speed wedge erodes if mapping three differently shaped exports takes weeks. The four-layer mapper has been designed for CRM-ish headers, and quote-line-item exports are one-to-many, which it may not handle (outside my lane to verify, flag to the ingest owner).

## 6. Recommended first increment

**The multi-source readiness review plus the interview module, no product build** (about 3 days):

1. Write a one-page data-readiness checklist per source type (quote tool, billing, other CRM), column list only, with the join-key and closed-lost gates above (1 day).
2. Add the 6-question module and four log fields to the interview guide, and a data-classes schedule draft to the NDA addendum for counsel (1 day plus counsel time).
3. Run it in the next 10 interviews, then offer the readiness review to the first account that shows named pain plus data access. Pilot copy: "CSV from your quote tool or billing system plus your CRM, discount governance, readout in 2 weeks from validated intake."

Product work (quote-export mapper, standalone quote screen with source-surface tagging) starts only after one partner confirms they price outside Salesforce or HubSpot. Effort then: roughly 5 to 8 days for mapper changes, which the ingest owner should size.

## 7. Open questions for the founder

1. Should pilot 1 accept a billing-only partner (leakage and realization, no win rate), or require a CRM with closed-lost? This changes the readiness gate and the readout.
2. Is a usage-native, descriptive-only pilot (commits and ramps captured and described, not scored) acceptable to sell at $15K, or must scoring ship first?
3. Will you accept any cost input before a signed pilot, or is the rule "no cost data until after signature, and only as a percentage table"?
4. Is a standalone quote screen enough as the "where the rep works" surface for pilot 1, or is Slack the minimum?
