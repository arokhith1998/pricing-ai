# Pricekeel: paid design-partner pilot readiness (customer-success lens)

## Verdict: Conditional, not yet.

The product's data-readiness review, column mapping, diagnostic output, and governance loop
are pilot-grade and arguably ahead of where a pre-revenue tool usually is. But the business is
not ready to run a paid pilot today: there is no signed design partner, the Salesforce app
cannot yet be installed into a customer's own org, and the legal paper a customer would need to
sign is explicitly marked not signable. Fix the packaging and legal blockers and this is ready
to run the motion described in the vault the moment a prospect says yes.

## Top 6 findings

1. **[Critical] No live pipeline.** `C:\Pricing-AI\docs\agents\PROJECT_STATE.md` shows all
   active work is internal engineering (PK-12 through PK-16); `C:\Pricing-AI\docs\ops\funnel-tracker.csv:1`
   has a header row and zero prospects logged. The GTM motion described in the vault is not
   currently running. Recommendation: resume `gtm/outreach-sequence.md` against
   `gtm/design-partner-targets.md` in parallel with the engineering fixes below.

2. **[Critical] Salesforce app is not distributable to a customer org.**
   `C:\Pricing-AI\docs\ops\salesforce-integration-runbook.md:10-23` and `:62-73`: the only
   working connection is a Local/Developer-Edition ECA in the founder's own org. "The current
   repository does not yet contain a Salesforce DX package" (line 73), and packaging is listed
   as a release gate before any external customer connects. This directly threatens the
   under-2-weeks time-to-first-recommendation target: a real prospect cannot even OAuth in
   today.

3. **[High] Legal paper isn't signable.** `C:\Pricing-AI\docs\legal\one-page-mutual-nda-data-addendum.md:3-8`
   states the NDA/data addendum is "NOT SIGNABLE in its current form" pending counsel and entity
   formation; `C:\Pricing-AI\web\src\lib\legal.ts:18-20` shows the entity name still falls back
   to the bracketed placeholder. No data-readiness review or CSV can be requested under NDA
   until this closes. This blocks the very first step of the commercial motion.

4. **[High] Recurring usage is logged per tenant but not rolled up for the founder.**
   The decision log (`web/src/app/api/exceptions/route.ts`) and weekly digest
   (`web/src/app/api/digest/send/route.ts`) correctly implement the subscription-usecase
   decision (exception loop, weekly digest), but there is no cross-pilot view that answers "are
   our 2-3 pilots actually running guidance calls/week" per the funding gate in
   `vault/Decisions/2026-06-11-subscription-usecase-discount-exception-loop.md:53-56`. Without
   it, "recurring usage, not readouts delivered" can't be verified at a glance across accounts.

5. **[Medium] Evidence floor unproven at real volume.**
   `C:\Pricing-AI\docs\reviews\2026-08-01-end-to-end-acceptance.md:11-16,52-54`: the only live
   Salesforce org has 18 usable closed outcomes, below the 30-outcome minimum and far below the
   500+ target in the ICP. The full pipeline has never been exercised end-to-end against
   pilot-scale data.

6. **[Medium] Audit trail actor is self-asserted, not authenticated.**
   `salesforce-integration-runbook.md:182-185` and `end-to-end-acceptance.md:94-95`: names in
   the approve/reject flow are operator-typed, not SSO-verified. This is a real gap against the
   "human-in-the-loop and audit trail" safety posture the CS motion is supposed to lead with,
   and it weakens the answer to "what happens to our deal data / who controls decisions" if a
   CFO probes segregation of duties.

## Three genuinely good things

- **The column mapper** (`pricing/mapping.py`) is a real onboarding wedge: four cascading
  layers (synonyms, fuzzy match, local embeddings, opt-in cloud LLM on header strings only),
  matching the promise that "onboarding is a column-mapping exercise, not a schema redesign."
- **The readout is built for a skeptical VP Finance**, not a demo. `pricing/diagnostic.py`
  leads with a load-report disclosure of exactly what was read/dropped/excluded before any
  finding, discloses segment-aware reference discounts and basis, and includes a "what we would
  not change" counterweight; `gtm/readout-close-script.md` operationalizes all of it into a
  scripted call with the caveats said before the prospect can ask.
- **Governance and data-handling maturity is unusually high for pre-revenue**: fail-closed API
  perimeter, AES-256-GCM token encryption, append-only decision events, and a carefully drafted
  opt-in (off-by-default) benchmarking-consent clause with a minimum cohort size and withdrawal
  rights (`docs/legal/one-page-mutual-nda-data-addendum.md:58-81`), which preempts both
  guaranteed CEO diligence questions directly.

## The one thing to do next week

Build and test the 2GP managed Salesforce package end-to-end in a fresh scratch org
(`docs/ops/salesforce-integration-runbook.md`, "Package for customer orgs" section). This is
the single concrete blocker standing between "works in the founder's own org" and "a design
partner can actually connect it," and it is bounded, testable engineering work that does not
depend on an external counterparty, unlike closing legal or landing the first signature.
