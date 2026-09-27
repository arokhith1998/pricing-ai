# CTO evaluation: Pricekeel (read-only, 2026-09-26)

## 1. Verdict

Conditional yes. Credible and unusually disciplined for the stage: one bounded workflow, a
real OAuth connector, a deterministic engine that labels which engine produced each number,
an append-only decision log, a fail-closed API perimeter, and CI that runs the gates. Two
conditions hold the yes. First, the live Salesforce path cannot see usage, commitments,
ramps, or overage, yet the copy sells usage and hybrid SaaS: V1 prices CRM-visible contract
values and must say so everywhere. Second, the two things that make this decision integrity
rather than a dashboard, authenticated actor identity and a durable audit write, are
unfinished, and the legal pack (entity, counsel-reviewed terms and privacy) is still open
from the 2026-05-30 audit. That is about a week of engineering plus founder paperwork, and
it belongs before any real customer data lands.

## 2. Top five findings

**1. Salesforce cannot carry usage truth, and the copy does not admit it. Severity: high.**
`web/src/lib/salesforce-adapter.ts:18-36` defines the canonical deal with no committed_acv,
overage_rate, or ramp fields; `value_metric` is guessed from a text field or a tenant default
(`:146-150`). Those fields exist only on the CSV path (`pricing/ingest.py:114`,
`pricing/mapping.py:127-133`). `web/src/app/page.tsx:53` still claims a usage or hybrid ICP.
Recommendation: one stated data contract. V1 governs discount on CRM contract values;
commitments, consumption, and overage need a billing connector or a CSV backfill joined on
account_id. Add a "usage evidence: not connected" state in the Deal Desk now. Do not build
the connector before a pilot asks.

**2. Actor identity is self-asserted, so the audit trail is company-level, not person-level.
Severity: blocker for accepting customer data.** `api/routers/crm.py:219-223` records
`"actor_assertion": "self_asserted"`, and the self-approval check is a normalized compare of
typed names (`:141-146`). The tenant key is a shared access code (`web/src/lib/gate.ts:58-62`).
One shared credential plus a free-text name defeats segregation of duties by spelling your
name differently. Recommendation: per-user authenticated identity (per-user magic link is
enough for pilot one), actor bound to the session, approver allowlist. Three to five days.

**3. The append-only log silently degrades to process memory. Severity: high.**
`pricing/governance.py:137-161` catches every storage failure, warns, writes to a list, and
returns `persisted: False`. Nothing blocks the action or alerts. An audit record that quietly
is not there is the one failure that kills this wedge. Recommendation: for CRM workflow
events fail with 503 instead of degrading, keep the memory fallback for demo and copilot
logs only, alert on fallback.

**4. No evidence version, despite the acceptance criteria claiming one. Severity: medium.**
`vault/Projects/pricekeel-salesforce-workflow-v1.md:71-77,131` promises a persisted evidence
version; grep across `pricing/`, `api/`, and `web/src` finds none. The verdict snapshot
(`api/routers/crm.py:172-205`) stores outputs but not the book that produced them.
Recommendation: hash record count, max sync timestamp, policy threshold, engine label, and
code SHA into `verdict.evidence_version`. Half a day, and past recommendations become
reproducible under audit.

**5. Integration cost is already visible in the hot path. Severity: medium.**
Every workflow action refetches the full 730-day Opportunity book
(`web/src/lib/salesforce-workspace.ts:136-148`, `web/src/lib/salesforce-adapter.ts:11,226`)
with no cache, and ships the whole book across the Next to FastAPI perimeter per click. At a
real org this is API-limit and timeout exposure on pilot day one. Recommendation: persist the
canonical book per tenant with a sync timestamp, serve guidance from it, refresh on a
schedule plus a manual button.

## 3. Three things that are genuinely good

1. **Engine honesty is enforced in code, not in copy.** The live path labels itself
`band_guardrail` and carries a correlational caveat (`pricing/crm.py:150,176`), the degenerate
list-field mapping raises a blocker instead of a silent zero discount
(`salesforce-adapter.ts:53-60`), multiyear ramp risk is disclosed rather than transformed
(`:63-68,368`), and the 30-outcome floor refuses guidance (`pricing/crm.py:228`). That is
explainability as an architecture driver.

2. **The monotone constraint on discount.** `pricing/model.py:17-35` forces P(win) to be
non-decreasing in discount, documents the AUC cost (0.640 to 0.619), and says why the
unconstrained model is a correlation read as a cause. Buying defensibility with accuracy is
exactly the right trade for enterprise pricing.

3. **The security perimeter is real.** Fail-closed API key in production
(`api/main.py:170-186`), SSRF-hardened fetcher with per-hop DNS pinning
(`pricing/_safe_fetch.py:1-24`), robots.txt plus kill switch before any competitor fetch
(`pricing/matching.py:123,167-202`), AES-GCM encrypted Salesforce tokens with a production
key requirement (`web/src/lib/salesforce-crypto.ts:19-28`), and CI that reruns the flaky OAuth
tamper test (`.github/workflows/ci.yml`).

## 4. The one thing I would do next week

Ship a single "pilot admissibility" branch and nothing else: authenticated per-user actor
identity with an approver allowlist, fail-closed durable writes for CRM workflow events, and
`evidence_version` on every verdict. That is one week, it closes findings 2, 3, and 4, and it
converts the audit trail from a demo artifact into something a CFO can rely on. Run entity
formation and the counsel review of terms and privacy in parallel, since
`web/src/lib/legal.ts:18-20` still defaults to `[legal entity]` and `[jurisdiction]`. Everything
else, including the billing connector, waits for a signed design partner.
