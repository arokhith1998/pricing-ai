# Product direction review, 2026-11-06: shared brief

Read this first. Every reviewer works from the same facts and writes one report to
this folder. The founder decides; reviewers recommend.

## The founder's direction (2026-11-06, in their words, lightly ordered)

1. "Most of the deals are not done on Salesforce/HubSpot. So it should be like an
   add-on to any platform." Asked where deals are actually priced and approved, the
   founder picked: quoting and CPQ tools (DealHub, PandaDoc, Proposify, Salesbricks),
   billing and metering platforms (Stripe, Chargebee, Maxio, Metronome, Orb), and
   other CRMs (Pipedrive, Zoho, Close, Attio, Freshsales). Not picked: spreadsheets
   and email.
2. "Add more features to what it can do." All four offered directions were chosen:
   platform-agnostic intake; deal-time guidance wherever the rep works (Slack, email,
   browser overlay, standalone quote screen); the next pillars (price recommendation,
   scenario and elasticity modeling, customer-level insights); usage-native pricing
   (commits, ramps, overages, not only the discount on committed ACV).
3. A new direction in the founder's words: "With AI companies growing, usage based
   pricing is gonna fluctuate as physical AI ramps up, token cost might come down.
   Also, margin guidance: from BOM, shipping location, tax deals to evaluate the
   gross and net margin and pricing based on what each customer values." Read this
   as three asks: (a) usage-based pricing for AI-native companies whose unit costs
   deflate and whose volumes swing; (b) margin-aware guidance that can take cost
   inputs (bill of materials, landed cost by shipping location, tax treatment) and
   return gross and net margin per deal, which reaches into physical goods and the
   Phase-3 distribution and manufacturing adjacency; (c) value-based pricing per
   customer (what each customer values, Nagle's economic value to the customer).
4. Deliverable: a design doc plus an ordered task breakdown with owners. The founder
   approves before anyone builds.

## Facts that bound every recommendation

- Pre-seed, pre-revenue, pre-user. Zero customers, zero signed design partners, a
  handful of early problem conversations. Solo founder. The critical path on the
  board is still paid-pilot validation.
- Shipped today: deterministic engine (`pricing/`: diagnostic, metrics, model,
  governance, ingest, mapping, crm, copilot, rag), FastAPI perimeter (`api/`),
  Next.js app (`web/`), Neon Postgres, a Salesforce workflow V1 (`docs/design/
  salesforce-crm-workflow-v1.md`), a CSV/XLSX path with a four-layer header mapper
  (`docs/design/richer-ingest.md`), 400+ tests. V1 governs the discount on
  committed or annualized contract value; commit, ramp and overage are captured but
  not scored. CRM numbers are never called margin (`docs/agents/DECISIONS.md`,
  vault `Decisions/2026-08-08-crm-honesty-and-ubp-math.md`).
- Rules that do not move: explainability over accuracy, humans decide, the LLM
  never computes a number, every recommendation names its method, thin data returns
  "insufficient data", row-level customer data is processed in memory and deleted.
- Sizing today: Tier A (diagnostic-addressable, any CRM) 350 to 480 US accounts,
  $11M to $29M at a $30K to $60K hypothesized ACV; Tier B (Salesforce-native) 130
  to 190. Vault `Decisions/2026-09-11-arr-band-and-post-funnel-sizing.md`. Phase-3
  distribution and manufacturing is sized separately in vault
  `Competitive/2026-08-09-phase3-distribution-manufacturing-sizing.md` and gated on
  the SaaS wedge paying first.
- The defensibility argument (vault `Competitive/defensibility-rebuttal.md`):
  neutrality across billing systems and CRMs, a decision record that compounds,
  explainability as the category. Billing platforms are the feared entrant.
- Production: API on Render was suspended Nov 4 to Nov 6 for an unpaid card; an
  uptime workflow now probes every 30 minutes.

## What each report must contain (keep under 1,500 words, no em dashes)

1. **Findings**: what in the current product, docs or sizing conflicts with or
   supports this direction. Cite file paths.
2. **What would have to change** in your area, concretely.
3. **Risks and tradeoffs**, including scope creep against the pilot critical path.
4. **Recommended first increment**: the smallest slice that moves the direction and
   can be validated with a design partner, with a rough effort estimate (days).
5. **Open questions for the founder**: only ones that change what gets built.

Write to `docs/reviews/2026-11-06-product-direction/<your-agent-name>.md` with a
one-line summary at the top. Read-only on product code: do not edit anything
outside this folder. If you cannot write, return the full report in your reply.
