# External CEO-style review of pricekeel.com, 2026-09-27: triage

Source: a buyer-perspective review of the live site (main at cf37f27, before
PR #70 and PR #71 deployed). Verdict there: would not buy an annual
production subscription yet; would accept the free diagnostic and consider a
tightly scoped 30 to 60 day pilot. This file maps each blocker to its status.

| # | Reviewer finding | Status | Where |
|---|---|---|---|
| 1 | Contracting entity not formed; privacy and terms under legal review | Founder | docs/legal, web/src/lib/legal.ts placeholders |
| 2 | Pre-SOC 2, no named-user SSO, MFA, RBAC, SCIM; access-code workspace | Roadmap; per-user identity is the next engineering gate (cto, day two) | PK-22 proposal in eval2-pk-lead.md |
| 3 | Homepage $8.9M vs live sample $12.48M | Fixed in PR #71: segment-first reference precedence, headline pinned, fallback regenerated | pricing/metrics.py, web/src/data/sample-fallback.json |
| 4 | Production LLM off ("llm": false); "opportunityies" typo; apology bubble then opportunities | Typo fixed and a narrated flag added in PR #71; narration-off banner in progress; the provider key on Render is a founder action | pricing/copilot.py, web/src/components/ChatPanel.tsx |
| 5 | "lowering the discount to 14% from 14%" with a dollar gain | Fixed in PR #71: copy compares at rendered precision and says "holding"; support floors no longer ship a dollar uplift | web/src/components/GuidanceClient.tsx, pricing/model.py |
| 6 | Diagnostic breaks at 390px (document 685px wide) | Fixed in PR #71 and verified in a browser at 390px against the local API: both charts told recharts to render at 640px before measuring (initialDimension), plus grid children without min-w-0 and unwrapped flex rows; document scroll width is now 390 and wide tables scroll inside their own card. A dev-only unlock (PRICEKEEL_DEV_UNLOCK, ignored in production) and a structural test were added | web/src/components/charts, web/src/app/diagnostic/page.tsx, web/src/proxy.ts |
| 7 | No customer proof | Founder; the site already says design-partner mode | gtm, funnel tracker |
| 8 | HSTS claim "preload-eligible" but header lacks includeSubDomains and preload; API sends none | Fixed in PR #71: header set on every web and API response | web/next.config.ts, api/main.py |
| 9 | Pricing page vague ("low five figures"), empty viewport at top | Price is a founder decision (cfo recommends $15K diagnostic credited to a $30K to $60K annual, delete the ROI table); the empty viewport was the Reveal component holding sections at opacity 0 until an intersection observer fired, which audit tools never trigger; Reveal is now visible at first paint, animates only when JS and the observer run, falls back to visible after 800 ms and respects reduced motion (verified: served HTML carries no inline opacity 0) | web/src/components/Reveal.tsx, web/src/app/pricing/page.tsx |

Reviewer questions worth answering in writing before a pilot: contracting
entity and paper timeline; pilot success metric (retained price, override
reduction, cycle time, or policy adherence, against a pre-pilot baseline);
why the two headline figures differed (answer: a reference-precedence
regression, fixed, with a known-answer test); what fails when the LLM is off
(answer: only narration; every number is deterministic); AUC 0.61 and the
predicted-versus-actual win-rate bias (answer: the model is honest, weak, and
disclosed; recommendations carry method labels and a skill gate); sparse
cohorts and drift (answer: insufficient-data refusal, support floors, time
split); feedback loops (open: no policy yet for excluding recommended deals
from future training); renewals, multi-currency, bundles, CPQ (answer:
renewal versus new is split, multi-currency blocks or normalizes with a
stated rate, bundles and CPQ are not supported); AppExchange review, OAuth
scopes, API volume (answer: not reviewed, read-only Opportunity scope, full
730-day book per sync); SSO, MFA, RBAC, SCIM, tenant audit logs (roadmap);
pen test and SOC 2 Type I (not scheduled); SLA, RTO, RPO, insurance
(founder); what a decision evidence record holds and export or delete on
termination (evidence_version inputs are returned; export and delete need a
runbook); what "low five figures" includes (founder); what "open code" means
(reproducible methodology and receipts, not public source).

The pilot terms the reviewer would approve match the design-partner motion
already documented in gtm: redacted CSV or read-only sandbox, no writeback,
signed NDA and DPA, reconciled figures, a working narration-off state, named
users, deletion and incident commitments, predetermined success metrics, a
fixed fee, no auto-renewal.
