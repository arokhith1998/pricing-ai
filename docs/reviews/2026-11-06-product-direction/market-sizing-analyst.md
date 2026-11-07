**One line:** Public data does not support "most deals are not priced in Salesforce or HubSpot"; platform-agnostic intake barely moves Tier A (350 to 480, upper bound about 600), AI-native usage firms are a 5 to 35 account sub-segment already inside Tier A, and BOM/landed-cost/tax margin pulls Phase 3 onto the incumbents' home turf the same month Vendavo shipped there, so measure where deals are priced before building any connector.

# Market sizing and category review, 2026-11-06

Lens: market sizing and category. Vault consulted: `vault/Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md`, `vault/Decisions/2026-09-26-som-re-derived-against-tier-a-pool.md` (still draft), `vault/Competitive/2026-08-09-two-tier-sizing-crm-agnostic-and-india.md`, `vault/Competitive/2026-08-09-phase3-distribution-manufacturing-sizing.md`, `vault/Competitive/defensibility-rebuttal.md`, `vault/Competitive/2026-08-09-metering-landgrab-why-now.md`, `vault/Competitive/2026-06-10-panel-review-tam-sam-som.md`, `vault/Competitive/2026-08-01-salesforce-market-need-assessment.md`. Every ACV-derived figure below is a hypothesis: no signed pilot, no observed ACV, no measured NRR.

## 1. Findings

**(1) The "not in Salesforce or HubSpot" claim is unsupported as stated.**
- Verified: Salesforce holds about 20% of global CRM revenue (IDC 2025 tracker, via truto.one, 2026-08-24). 6sense install detection: Salesforce 27.1%, HubSpot 7.4% of the CRM category (undated, retrieved 2026-11-06). These are all-company figures, dominated by SMB and non-software firms.
- Verified: no primary source gives CRM share for $10M to $100M ARR SaaS. I found none from Bridge Group, Ramp, Vertice or Carta. Mid-market figures in circulation (Salesforce 28% to 46%) conflict and are untraceable.
- Assumed (vault): Salesforce is about 40% of the qualified pool (`two-tier-sizing` note), with HubSpot the mid-market default. A sales-led company with 500+ negotiated closed outcomes a year almost always keeps the opportunity in one of the two. My working estimate: Salesforce plus HubSpot is 75% to 85% of Tier A. That is assumed, not verified.
- The narrower claim holds up. The quote is often produced outside the CRM: CPQ adoption is roughly 30% to 47% (Copperberg and vendor blogs, weak). Salesforce CPQ has been end-of-sale since 2025-03-19, so new Salesforce customers either reimplement on Revenue Cloud Advanced or buy third-party CPQ (salesforce.com/sales/cpq/end-of-life). DealHub, PandaDoc and Salesbricks all sync back to Salesforce or HubSpot. So the price is often set outside the CRM, and the record of it still lands in the CRM.
- Conflict in our own docs: the ICP filter requires "a deal desk / RevOps on spreadsheets", but the founder ruled out spreadsheets and email. In the ICP as written, approval often happens in spreadsheets and Slack.

**(2) Platform-agnostic intake does not widen Tier A much, and the August note already covers the CRM half.** Tier A is already defined as "any CRM" via CSV (`two-tier-sizing`, ICP filter line "CRM: ANY for Tier A"). Intake affects only one gate, data readiness. It does not touch 500+ outcomes, policy owner, champion or buyer.

| Change | Arithmetic | US accounts | Status |
|---|---|---|---|
| Tier A today | vault | 350 to 480 | assumed |
| CPQ or billing intake rescues accounts with unusable CRM fields, +10% to 25% | 350x1.10 to 480x1.25 | 385 to 600 ($12M to $36M at $30K to $60K) | assumed upper bound |
| Native workflow on Salesforce only (Tier B) | 40% | 130 to 190 | vault |
| Native workflow on Salesforce plus HubSpot | 75% to 85% x Tier A | 260 to 410 | assumed |
| HubSpot alone | 35% to 45% x Tier A | 120 to 215 | assumed |
| Pipedrive, Zoho, Close, Attio, Freshsales combined | 5% to 15% x Tier A | 18 to 72, about 4 to 15 per vendor | assumed |

The August note does not cover CPQ-only or billing-only data sources. That is the only new reach, and it is small. Counted in accounts, the next native surface should be HubSpot, not the long-tail CRMs the founder named. Billing intake (Stripe, Metronome, Orb) adds depth rather than accounts: realized usage and overage are what usage-native scoring needs (`defensibility-rebuttal.md`, honesty gap).

**(3) AI-native usage-based segment, bottoms-up (US):**

| Step | Factor | Result | Status |
|---|---|---|---|
| AI-native at $100M+ ARR, global | Sapphire 2026 Software x AI report (via SaaStr) | 80+ | verified, secondary |
| Count at $10M+ | 3x to 6x the $100M+ count, power law, short time in the band | 240 to 480 | assumed |
| In the $10M to $100M band | minus 80 | 160 to 400 | derived |
| US share | 70% to 80% (arr.club regional mix) | 112 to 320 | assumed |
| B2B, not consumer | 75% to 85% | 84 to 272 | assumed |
| Usage or hybrid pricing | 60% to 85% (ICONIQ 2025: 19% usage + 38% hybrid; Orb agents study: 91%) | 50 to 231 | partly verified |
| Operational funnel (500+ negotiated outcomes, owner, champion, buyer) | 10% to 15%, harsher than Tier A's ~12% because these firms are PLG-heavy with $1M to $5M ARR per employee | **5 to 35** | assumed |

Wedge SAM: $0.15M to $2.1M at $30K to $60K (hypothesis). Most of these accounts already sit inside the 350 to 480. Four of the 18 named candidates (Deepgram, AssemblyAI, Pinecone, Baseten) are AI infrastructure companies. **This segment changes which Tier A accounts we target first. It does not add accounts.**

Willingness to pay. Unit costs deflate about 10x a year at fixed capability (a16z "LLMflation", 2024), with a median of 50x a year across benchmarks (Epoch AI, 2025-03). Average AI gross margin is about 52% (ICONIQ, Jan 2026, secondary). Margin raises WTP: a 10% discount removes 20% of gross profit at 50% margin, against 12.5% at 80% margin, so the same leakage hurts AI-native companies 1.6x more. Deflation makes "discount off list" a weak metric when list prices fall each quarter. The live decision becomes how much cost deflation to pass through on commits and ramps. That is a genuine need, but WTP evidence is zero. It is also the slice where billing vendors already compete (Chargebee's 2026 release ships "margin controls built for agents"; Metronome, now Stripe, sells to AI companies).

**(4) Margin from BOM, landed cost and tax.** This closes only prerequisite 2 of the five Phase-3 gates (`phase3` note, section 5). It leaves open wedge validation, ERP connectors, a distribution design partner, and pocket-price-waterfall depth. The Phase-3 note rates this ~60% rebuild work. Cost of pulling it forward:
- The asymmetry tempts a pivot. Phase-3 is a $350M to $850M hypothesis against a $11M to $29M Tier A, 12x to 77x larger. That note still cites a "SaaS wedge $150-200M" and a "$40-60K" SaaS ACV. Both are stale and should be corrected to $11M to $29M and $30K to $60K.
- Its funnel is shallower. Distribution goes from 10K to 13K accounts down to 2,500 to 3,300, about a 4x collapse, while the SaaS funnel collapses about 8x. So the Phase-3 SAM has not been through the same funnel discipline and is probably overstated.
- The incumbents just moved. Vendavo launched an AI Deal Desk Assistant for manufacturers and distributors on 2026-10-20, with price guidance and margin alerts through SAP, Oracle, Dynamics, Infor, Epicor and NetSuite connectors. The defensibility flip in the `phase3` note is now live, not theoretical.
- Tax is mostly pass-through, not margin. Duties belong in landed cost. Tax logic is Avalara and Anrok territory and carries liability.
- The useful kernel already exists: `cogs_acv` in `pricing/schema.py:158` ("infra / delivery cost"). Fed with inference and hosting COGS, it gives SaaS-native deal margin. That serves AI-native accounts (3) without leaving the wedge.

**(5) Competitor moves since 2026-09-26 (stale-fast, re-verify 2026-12-26):**
- Vendavo AI Deal Desk Assistant, 2026-10-20 (verified, PR Newswire). Approval workflows are listed as a future extension.
- Pricefx Accelerate, 2026-10-13 to 15. Its bring-your-own-AI-assistant early-adopter program starts October 2026, GA early 2027 (announced 2026-08-19). Pricefx also published a "Win Rate Optimization" capability (Jan 2026).
- DealHub "Price Optimization AI" scores a live quote against look-alike historical deals, with a win-rate estimate and per-SKU discount reasoning. This is Pricekeel's wedge feature, inside a CPQ the founder wants to plug into. It appears on an undated on-demand page, so I cannot confirm it shipped in the window. DealHub also owns Subskribe (consumption billing, acquired Nov 2025).
- Stripe/Metronome, Adyen/Orb, Salesforce Agentforce Revenue Management (Dreamforce was 2026-09-15 to 17), Maxio, Zuora, PandaDoc, Salesbricks: I found no new discount or margin-guidance launch in the window. That is an absence in search results, not a verified fact. I found no new M&A.
- The window in `metering-landgrab-why-now.md` (9 to 15 months as of 2026-09-26) is now about 8 to 14 months. The sharper threat has moved from billing to CPQ.

## 2. What would have to change

- Sizing language: "any platform" adds at most about 120 Tier A accounts and should never appear as a market expansion. Report Tier B as "Salesforce plus HubSpot, 260 to 410" only once a HubSpot surface exists.
- Add an AI-native tag to Tier A and order outreach by it. Do not add an AI-native SAM line.
- Correct the stale SaaS figures in the `phase3` note and keep its five gates intact.
- Add DealHub to `defensibility-rebuttal.md`. The neutrality argument applies to CPQ the same way it applies to billing: a CPQ only benchmarks its own base.
- Leave the 2026-09-26 SOM unchanged. It remains a draft awaiting founder sign-off.

## 3. Risks and tradeoffs

- Connector sprawl. Five long-tail CRMs plus four CPQs plus five billing platforms is 14 integrations for about 18 to 72 incremental accounts, pre-pilot, built by a solo founder.
- Two markets, zero validation. Margin guidance for physical goods splits the story right when the deck has to defend a $1.5M to $2.3M wedge. The Aug 1 verdict says "do not expand into a generic AI pricing platform".
- Overlay surfaces inside DealHub put us on a competitor's platform.
- Upside: AI-native margin pressure is the strongest WTP argument found so far, and it stays inside SaaS.

## 4. Recommended first increment

A **platform census plus one question**, about 4 to 5 days, almost no code. (a) For the 18 named US candidates plus about 30 AI-native usage candidates, record CRM, CPQ or quote tool, and billing platform from public signals (job posts, integration pages, case studies). Publish the observed shares with n. (b) Add "where is the price on this deal set, and where is it approved?" to every discovery call and to the design-partner data-readiness review. (c) Only if HubSpot reaches 30% or more of the census: add a HubSpot deals-export header profile to the existing CSV mapper (`docs/design/richer-ingest.md`, about 1 to 2 days, engineering owns). That gets validated against a design partner's real export, and it replaces the most load-bearing assumed number in this review.

## 5. Open questions for the founder

1. Which conversations produced "most deals are not on Salesforce or HubSpot"? How many, and which systems did they name? If n is 3 or fewer, the census decides.
2. Did the BOM, landed cost and tax ask come from a named prospect, or is it a thesis? A named manufacturer prospect changes the Phase-3 gate. A thesis does not.
3. Is AI-native the lead ICP for the paid pilot, or a sub-segment? It changes the outreach order and whether `cogs_acv` gets scored in V1.
4. Is DealHub a channel or a competitor?

Proposed vault note (not written): `vault/Competitive/2026-11-06-platform-census-and-ai-native-sizing.md`, tags `#market-sizing #icp #ai-native #competitive`, linked to `[[2026-08-09-two-tier-sizing-crm-agnostic-and-india]]`, `[[2026-08-09-phase3-distribution-manufacturing-sizing]]` and `[[2026-08-09-metering-landgrab-why-now]]`.

## Sources (retrieved 2026-11-06; counts, funding and M&A go stale fast)
- [truto.one, B2B integrations ranking, 2026-08-24](https://truto.one/blog/data-driven-ranking-most-requested-b2b-sales-integrations-in-2026/) · [6sense technographics](https://technographics.6sense.com/crm-platforms/salesforce-vs-hubspotcrm)
- [Salesforce CPQ end of sale](https://www.salesforce.com/sales/cpq/end-of-life/) · [Copperberg CPQ survey](https://www.copperberg.com/?p=17824)
- [SaaStr on Sapphire 2026 Software x AI](https://www.saastr.com/top-10-learnings-from-sapphire-ventures-2026-software-x-ai-report-80-100m-arr-ai-startups-the-ultra-round-is-the-new-normal-and-enterprise-is-50-of-vc-now/) · [arr.club rankings](https://www.arr.club/rankings) · [Orb on ICONIQ/agent pricing](https://www.withorb.com/blog/2026-state-of-ai-agent-pricing-models-trends-and-whats-working) · [SaaStr on ICONIQ 2025](https://www.saastr.com/what-300-of-the-highest-growth-b2b-startups-are-doing-with-ai-the-latest-from-iconiq)
- [a16z LLMflation](https://www.a16z.com/llmflation-llm-inference-cost) · [Monetizely AI-first economics 2026](https://www.getmonetizely.com/articles/the-economics-of-ai-first-b2b-saas-in-2026-margins-pricing-models-and-profitability)
- [Vendavo AI Deal Desk Assistant, 2026-10-20](https://www.prnewswire.com/news-releases/vendavo-launches-ai-deal-desk-assistant-bringing-deal-intelligence-directly-into-the-quoting-workflow-302911681.html) · [Pricefx BYO AI, 2026-08-19](https://www.businesswire.com/news/home/20260819253321/en/Pricefx-Opens-Its-Pricing-Platform-to-the-AI-Assistants-Enterprises-Already-Use) · [Pricefx Accelerate 2026](https://www.morningstar.com/news/business-wire/20260922544186/pricefx-accelerate-2026-showcases-ai-powered-pricing-in-action) · [DealHub agentic walkthrough](https://dealhub.io/events/agentic-workflows-and-quote-to-revenue-a-partner-walkthrough/) · [Chargebee on SaaStr](https://saastr.com/saastr-ai-app-of-the-week-chargebee-the-billing-system-behind-how-gorgias-coderabbit-lambda-and-zapier-price-ai)
