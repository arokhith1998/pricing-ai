# Pricekeel full-company review, 2026-06-11

How this was run: one live hostile-customer walkthrough of pricekeel.com in a clean browser
context (real form submits, network inspection, live DNS checks), the full local test suite
(113/113 green), and seven parallel internal persona reviews (CTO, Website Builder, UI/UX,
CFO, COO, CBO, Sales), each grounded in the repo, the vault, and (where permitted) live web
research. Then: consolidated loophole list, simulated customer reviews, Phase 3 roadmap, and
outreach personas.

---

## 1. Live-tested customer walkthrough (verified in production, not from source)

**SHOWSTOPPER, found by actually submitting the form: production lead capture is dead.**
- Submitted the unlock form on /sample?unlock=diagnostic with a valid business email.
  Result: `POST /api/lead` returned **500**, user sees "Could not save right now. Try again."
- Root cause confirmed: `jzhnjxlsmdghcipzvjke.supabase.co` **no longer resolves in DNS**
  (control check: supabase.co resolves fine). The free-tier Supabase project has been paused
  (or deleted) for inactivity. Provisioned May 28; free projects pause after ~7 days idle.
- Blast radius: lead capture, access-code validation, and magic-link recovery are ALL down.
  Every prospect who has filled the form since the pause got an error. The bottom of the
  funnel is severed while outreach is about to start.
- Fix: log into supabase.com, restore the project (free projects restorable within 90 days),
  re-verify the `leads` schema has the launch-readiness columns, then either upgrade to Pro
  (~$25/mo) or add a weekly keep-alive ping (GitHub Action hitting a select) so it never
  pauses again. Add an uptime check on a synthetic form submit so this class of failure pages
  you instead of silently eating prospects.

**Verified working (credit where due):**
- Test suite: 113/113 pass.
- The two-tier gate works correctly for a fresh visitor: /diagnostic redirects to
  /sample?unlock=diagnostic, the banner names the locked view, magic-link recovery UI exists.
- Free-email rejection works ("Please use your company email address"), though only after
  submit, with no inline hint while the button sits silently disabled.
- The site reads coherent, the honesty posture (correlational caveats, "not a refund")
  survives all the way into public copy.

**Confirmed live contradictions:**
- /pricing says, publicly: "Pricekeel Operate ... priced at **$5K per month with a six-month
  term**." The internal plan says $15K 90-day pilot credited to year 1. The roadmap says
  $10-25K. Three prices in circulation; a prospect can read one of them.
- /privacy shows, live in production: "operated by **[legal entity], [jurisdiction]**" and
  "DRAFT, counsel review pending" in the header.
- Landing DiagnosticPreview shows win point at the 15% band with a curve climbing to 76%;
  the real /sample shows the win point at ~5%. The marquee chart fails its own audit.
- Founder strip: "$626M margin-recovery" chip with zero attribution.

**Stale founder cookie note:** the first walkthrough sailed straight into /diagnostic because
this browser still held the pk_lead cookie set during the 2026-05-30 session. The gate is
fine; remember that any demo machine carries state a prospect will not have.

---

## 2. Consolidated loopholes to fix (deduped across all eight reviews)

### P0 — before the first outreach email leaves the outbox

| # | Loophole | Evidence | Owner / effort |
|---|---|---|---|
| 1 | Supabase project paused: lead capture, access codes, magic links all dead in prod | Live 500 + DNS NXDOMAIN | Founder, 30 min + keep-alive |
| 2 | GitHub repo is PUBLIC: GTM playbook, outreach sequence, NDA template, ICP targets readable; vault strategy files permanently in history | `gh repo view` | Founder, 10 min (private) + history is gone, accept |
| 3 | api.pricekeel.com has zero auth: /ask + /summary = open LLM spend, /matching = scraping-by-proxy, pk_lead cookie is presence-checked only | api/main.py, gate.ts:23 | Eng, 0.5 day (shared-secret header + slowapi + size cap) |
| 4 | `All Passwords.txt` in plaintext at repo root on a machine with a suspected rogue sync client; saved from the public repo by one .gitignore line | repo root | Founder, 1 hr: rotate Supabase key + DB password + Perplexity key + PRICEKEEL_SECRET, move to password manager, delete file |
| 5 | Three contradictory commercial structures, one of them public ($5K/mo live on /pricing vs $15K pilot vs $10-25K roadmap) | live fetch | Founder decision, 1 hr |
| 6 | /sample (the primary CTA) server-fetches Render per request, no timeout, no cache; failure renders `python -m uvicorn ...` to the buyer | ApiError.tsx, api.ts:253 | Eng, 2 hr (cached synthetic payload + buyer-facing fallback) |
| 7 | Privacy page live with [legal entity] placeholders + DRAFT stamp; Terms DRAFT; no entity, no counsel engaged; NDA template is bracketed boilerplate | live fetch + vault audit | Founder + counsel, this week (entity filing already planned ~Jun 24; counsel review must finish ~Jun 20 to hit the Jul 31 CSV goal) |
| 8 | Known-overstated headline number still live: global 5% reference vs Enterprise 10-15% win point; advisor sign-off still pending; gate: no real-data readout until segment-aware references + advisor sign-off | dry-run log + live /sample | Eng + advisor, before first readout |
| 9 | Moat thesis self-contradiction: benchmark moat vs "never stored" privacy promise; no benchmarking consent anywhere in funnel or addendum | upload page + addendum | Founder, rewrite moat story (see Phase 3) + consent language in addendum |
| 10 | No funnel instrumentation at all: no analytics (privacy page promises none third-party), no outreach tracker, UTM survives only on conversion | grep + vault | Eng 1 hr (Vercel cookieless + privacy wording) + 1 spreadsheet |

### P1 — within two weeks / before the first CSV

- Fail-open secrets: `PRICEKEEL_SECRET ?? "pricekeel-dev-secret"`; missing Supabase env silently stores leads in lambda memory while showing success. Fail fast in prod.
- One static shared access token for every customer; revocation is fictional with 2+ customers. Sign code identity into the cookie.
- No Sentry/observability on either tier; no LLM spend cap or budget alert. (Flagged by panel May 29, still open.)
- Decision log and doc store are in-process dicts: the $15K pilot's flagship artifact does not survive a deploy. Persist to Supabase.
- LoadReport (the trust feature the last three engine commits built) is not in the API payload; web buyers never see disclosures. One key in `_diagnostic_payload` + a UI panel.
- Unsanitized LLM markdown via `dangerouslySetInnerHTML` (Summary, ChatPanel) + no CSP headers: prompt-injected doc = XSS in the gated app.
- No rate limit on /api/lead or /api/lead/magic-link (Resend quota + sender-reputation burn during outreach week); /api/auth brute-forceable.
- Zero OG/Twitter metadata anywhere: every LinkedIn/email link renders naked. robots.txt advertises a sitemap.xml that 404s.
- No custom 404/error/loading pages. LeadForm fetch has no try/catch (network blip = button stuck on "Unlocking…").
- /upload is the hero's secondary CTA but lands cold visitors on an access-code wall with no request path. Wire the magic-link infra to it.
- Lead form: 7 required fields + consent to see synthetic data. Cut to email + company (+ inline business-email validation), enrich the rest on the call.
- Readout is not forwardable: no PDF export, no print stylesheet, and a pasted /diagnostic URL bounces the CFO to the lead form. (Dry-run wishlist 5; also the Sales ladder depends on it.)
- Data-handling contradiction: trust page promises in-memory-and-deleted while the runbook stores prospect CSVs in shared Drive folders on a machine with unresolved torn-write corruption. Pick one story; force founder-run files through the clean web path or write the SOP.
- Site sells discount-% language to a UBP market: commit/ramp/overage are optional columns, not a first-class lens. Either elevate them or soften the "usage-based" chip.
- Audience chip says "VP Pricing teams"; the ICP note says that title barely exists at $15-60M ARR. Say RevOps/Finance.
- 5-6 outreach touches over 3-4 weeks instead of 3-in-7-days; build target list to 120-150; instrument every stage.
- E&O + cyber insurance ($2-6K/yr) bound between incorporation and first CSV.
- Two landing pages in flight (cinematic on this branch vs v2 redesign in a worktree); decide and merge one. `landing-cinematic` also hides the H1 behind hydration (LCP risk) — check on a real phone before merging.

### P2 — track

- Segment-aware reference discounts also lower and harden the pricing anchor (price on tiers, narrate with leakage).
- "$626M" chip: one clause of provenance or cut it.
- Pilot contract protections: fee at signature, readout N business days after validated intake (not calendar dates), credit vests only on annual signature with pro-rata clawback, liability cap at fees paid, enumerate deliverables per cycle, price the benchmark consent instead of giving it away.
- Blog cadence already slipped (Jun 9/11 posts missing); posts go live at UTC midnight, which is the prior evening ET.
- Quarter-end outreach hook expires Jul 1; pre-write the H2-planning angle.
- WIP cap: 2 concurrent diagnostics; assign intake dates at NDA signature. Salesforce build waits for 2 committed partners (the runbook already says so).
- Internal jargon leaks: "Phase 3 connector", "Final phase coming soon", the lone 📈 emoji.

---

## 3. Internal panel reviews (condensed; full reports in session transcripts)

**CTO:** Engine is real (113 green tests, adversarial fixtures, LLM confined to narration,
genuinely clean no-retention CSV path). Perimeter is the opposite: public repo describing an
unauthenticated API, one static shared token as the entire customer auth model, live
credentials in a text file on a machine already suspected of running a rogue sync process.
Five demands before the first real CSV: close the API perimeter, repo private + rotate
everything, per-customer cookie identity, Sentry + LLM spend alert, ship LoadReport through
the API + persist the decision log. Two to three focused days closes all of it.

**Website Builder:** The substance is unusually strong (pricing page answers real CFO
objections, careful gating/magic-link plumbing, real reduced-motion discipline), but failures
cluster exactly where a skeptical buyer lands: demo CTA that can die into uvicorn
instructions, naked link previews on a LinkedIn-led GTM, DRAFT-stamped legal pages, zero
funnel visibility. Ten quick wins under one day total, ranked; do 1-5 before the first email.

**UI/UX:** Dark cinematic theme is not the problem; it reads trading-terminal, not crypto,
and the receipts pattern (every claim decomposes into auditable evidence with stated limits)
is the moat in the UI; do not break it. What erodes trust: homepage chart contradicting the
product one click away, dev error page in the buyer path, upload flow with no door, flagship
artifact that cannot be forwarded, marketing motion (pulsing glow, CountUp) leaking into
product surfaces where numbers should sit still. Three highest-leverage changes: unbreak the
two dead ends, make the readout forwardable, cut the form to 2 fields + reconcile the preview.

**CFO:** Cash COGS per pilot is under $100 (99% cash margin) but economic margin after
founder hours is 40-55%: consulting margin, not software margin, capped at 3 accounts. The
credited pilot is a deposit, not revenue (ASC 606 material right), an effective 25-50% year-1
discount, and double-counts in ARR under DD. The 5-10%-of-leakage anchor prices against a
number our own product disclaims, and at ICP scale yields a fee range of $2.5K-60K (24x):
fails as a mechanism. Pipeline decomposition says touch-to-CSV is ~1-2% cold, not 5-10%, so
the Sep 30 milestone needs 200-400 touches or a warm channel. Pre-revenue outlays: $6-16K
before the first dollar in; write the personal-runway number down or the Q1 2027 fork is
arithmetic that happens to us. Eight procurement loopholes enumerated (term has no teeth,
credit arbitrage, free deliverable, SLA asymmetry, their-paper NDA, scope vectors, benchmark
carve-out strike, no payment-before-value gate).

**COO:** Counsel engagement, not outreach volume, is the critical path: the NDA is a
bracketed placeholder, no entity exists, and a prospect's legal takes 1-3 weeks on even a
one-page NDA, so counsel must finish ~Jun 20 to protect the Jul 31 CSV goal. The
data-handling promise and the delivery motion are two different systems (clean in-memory web
path nobody will use; emailed CSVs into shared folders on a corruption-suspect machine, in
breach of our own addendum from day one). 72-hour breach promise with no IR plan and no data
register. Capacity math: ~13-19 founder-hours per prospect reaching a readout against ~20-25
net GTM hours/week; quarter-end clustering makes 3 concurrent CSVs = 39-45 hours inside
promised named-date windows. Cap WIP at 2/week, assign intake dates at signature. Five
artifacts must exist before the first NDA: counsel-reviewed NDA + one engagement letter,
data-handling SOP + per-customer register, funnel tracker, IR one-pager, delivery runbook
with QA gate covering the two silent-wrong-number classes.

**CBO (with live market research):** The wedge white space verifiably still exists, but the
moat story is internally contradictory and the window shortened. Since the May landscape
note: Stripe completed the Metronome acquisition (Jan 2026) with "sales-led + revenue
analytics" named in the announcement; Salesforce signed a definitive agreement to acquire
m3ter (closing ~now) aimed exactly at quote-time monetization inside the CRM; Orb rebranded
toward "revenue design" and ships pricing simulations. Revise the window to 12-18 months for
the diagnostic wedge; treat quote-time embed as a feature inside Salesforce's ecosystem, not
the moat. The honest, winnable moat: (a) closed-lost deal data billing platforms structurally
never see, (b) the audit-grade decision log as accumulating system of record, (c)
CFO-grade explainability. Three moves: open consultant/fractional-CFO and VC-platform
referral channels now (LinkedIn is air cover, not pipeline), rewrite the moat story + put
benchmark consent in the addendum, pre-position against the bundles ("what your billing
system cannot tell you about discounting" + one-click Salesforce-report-to-CSV guide).
Require closed-lost rows for every free diagnostic: differentiation and tire-kicker filter.

**Sales:** A funnel with a strong middle and no top or bottom. The first ask (NDA + 4
quarters of data) is the maximum-trust ask while the zero-trust self-serve path (/upload, in
memory, founder never sees it) goes unmentioned in outreach, and there is no script for the
only call that converts revenue. Do not send email #1 until: one commercial story, a
readout-to-pilot close script (lead with their number, walk top-5 deals, "what would catching
these before close have been worth?", name the offer in one sentence, date the next step),
and the no-readout-before-advisor-sign-off gate. Run the smaller-yes ladder: sample readout
PDF → column list → self-serve /upload ("if the number is boring, I stop emailing") → fit
call → NDA + CSV ("your paper or mine") → readout with the CFO invited. Full objection
inventory written (Excel, sensitive data, ChatGPT, Pricefx, no customers, one person) — keep
it in gtm/. Title reality: email VP/Director RevOps first, CFO never cold, CRO only after
the champion is in.

---

## 4. Customer reviews (simulated, grounded in the live walkthrough)

**VP RevOps, $28M ARR hybrid-pricing SaaS (the champion):** "The sample readout is the best
artifact a vendor has shown me this year: it shows its work, names its limits, and the rep
league table writes my next CRO conversation for me. But I filled out your seven-field form
and got 'Could not save right now.' Twice. I closed the tab. Also, my CFO clicked the link
I sent her and hit the same form. If forwarding your report to my CFO is the sales motion,
why does your product punish it?"

**CFO, $45M ARR usage-based SaaS (the economic buyer):** "Your homepage chart says the win
point is 15%; your sample says 5%. Your privacy policy is operated by '[legal entity],
[jurisdiction]', and your pricing page quotes $5K/month while your founder quoted me a $15K
pilot. Individually, small. Together, on a product whose pitch is 'we keep your numbers
honest,' disqualifying. The methodology caveats are genuinely impressive, which is exactly
why the sloppiness around them stands out. Come back when the company is as disciplined as
the math."

**Director of IT Security (the blocker, doing the vendor review):** "Their API subdomain
answers without authentication. Their GitHub repo is public and includes their NDA template
and, in history, their internal strategy notes. The privacy page is marked DRAFT. There is
no SOC 2, which is fine at this stage, but there is also no security one-pager, no liability
cap in the NDA, and the data-handling story differs between the trust page and what the
founder described on the call (emailed CSVs). Recommend: do not send data until they have an
entity, signed terms, and the API perimeter closed. Re-review in 30 days."

---

## 5. Phase 3 roadmap (revised by this review)

Reframe: Phase 3 is not "Margin Enhancement" first. Phase 3 is **the live loop**, because the
subscription is only legitimate when value recurs, and because the CBO review shows quote-time
is where the war is. Margin Enhancement becomes 3C. Every stage has an entry gate; no stage
starts early.

**3A. Live monitoring (entry gate: 2 committed paying partners; target start Sep-Oct 2026)**
- Salesforce/HubSpot OAuth, nightly incremental pull of closed opps through the existing
  four-layer mapper (this is why those three hardening rounds mattered).
- Leakage/realization trend, drift alerts, off-policy approval alerts, monthly auto-readout.
- Decision log persisted (Supabase), per-customer identity and revocation, LoadReport
  disclosures in every artifact.
- Engineering precondition carried in from P0: segment-aware reference discounts shipped and
  advisor-signed; New/Renewal split (Type column is read, currently ignored); one-page PDF
  export (it is also the sales asset for 3A upsells).
- Explicitly NOT: Snowflake/Fivetran, SOC 2 audit (questionnaire + security one-pager
  suffices), second vertical, paid ads.

**3B. Quote-time guidance (entry gate: 3A live at 2+ customers and retention proven)**
- Sidebar (Salesforce LWC / HubSpot CRM card): price band, comparables, win probability,
  the why, approval flow below floor.
- Strategic posture per CBO: this is a feature shipped inside Salesforce's ecosystem, not the
  moat. Build it thin, standardized, AppExchange-listable. The moat it feeds is the decision
  log + closed-lost dataset, which Salesforce-m3ter does not retroactively own.
- UBP first-class: commit level, ramp, overage rate, renewal uplift as guidance outputs
  ("raise the commit, hold the rate"), not just discount %.

**3C. Margin layer (entry gate: 5+ subscription customers; the original Phase 3 scope)**
- Active-contract data, special pricing agreements, fixed-discount and margin gaps across the
  book, renewal-uplift leakage, price-floor breaches. Snowflake/Fivetran connectors only here.
- Benchmark product v1 only if consented cohort ≥ 30 logos; until then benchmarks stay
  honest synthetic placeholders, clearly labeled.

**Standing constraints across all of Phase 3:** explainability over accuracy, correlational
claims never sold as causal, humans in the loop on every recommendation, every number ships
with its receipt and its caveat.

---

## 6. Outreach personas (build the list against these, in this order)

**Persona 1 — The RevOps Owner (primary; email first)**
- Title: VP / Director of Revenue Operations (sometimes "Deal Desk Lead").
- Company: $15-45M ARR B2B SaaS, hybrid or usage-based pricing, 40-120 sales/CS heads,
  Series B-C. No dedicated pricing team; RevOps inherited discount governance.
- Pains: ad-hoc discount approvals in Slack, quarter-end fire drills, CFO asking "why is
  realization down" with no answer that survives scrutiny, comp plans rewarding bookings
  over price quality.
- Trigger events: new CFO arrives; board asks about NRR or gross margin; annual comp/policy
  planning; a big renewal that re-priced badly; CPQ rollout being scoped.
- Watering holes: LinkedIn (RevOps voices), RevOps Co-op, Pavilion, Wizards of Ops.
- Hook: "Your deal desk already knows which reps over-discount. This shows you what it costs,
  from one CSV, with the receipts." Lead with the rep league table and policy simulation.
- Likely objection: "we can pivot-table this" → won AND lost deals, band-level win rates,
  calibrated model; the diagnostic is free, so Excel confirming it costs you 30 minutes.

**Persona 2 — The First Pricing Hire (primary; co-equal with 1)**
- Title: Head / Director of Pricing & Packaging (often the only one).
- Company: $30-80M ARR, usage-based or hybrid, often PLG+sales-led motion. Frequently
  ex-Simon-Kucher / ex-OpenView orbit; 0-2 staff; 6-18 months into the role.
- Pains: needs a defensible quick win to justify the role; no data engineering support; CRO
  pushes back on every policy proposal; wants named-methodology air cover.
- Trigger events: just hired (90-day plan), pricing-model migration (seats → usage), pricing
  council being formed, repricing project on the roadmap.
- Watering holes: LinkedIn pricing community, PeakSpan/OpenView content orbit, Professional
  Pricing Society, pricing Slack groups.
- Hook: methodology-forward. "Nagle reference price + Simon-Kucher governance, run on your
  own book, free, with the caveats printed. You present it; it makes your case to the CFO."
- Note: this person will spot the global-vs-segment reference issue. Say it first; it builds
  more trust than it costs.

**Persona 3 — The Operator CFO (economic buyer; never cold-email)**
- Title: CFO / VP Finance at $10-50M ARR usage-based SaaS.
- Reached via: fractional CFO networks, pricing consultants, VC platform teams, the
  CFO-forwardable readout a Persona 1/2 champion sends. This persona is the destination of
  the artifact, not the target of the sequence.
- Pains: gross margin and NRR pressure from the board, price realization unmeasured, deal
  desk feels like a cost center, no audit trail on discount decisions.
- Hook (via referrer): "the diagnostic produces the business case in their numbers; the
  consultant presents it." White-label-friendly.

**Persona 4 — The Pricing-Owner CEO (opportunistic; small but fast-closing)**
- Title: Founder/CEO at $8-20M ARR usage-based SaaS who still personally approves discounts.
- Pains: knows discounting is leaking, has zero time to analyze it, no RevOps function yet.
- Trigger events: raising a round (clean unit-economics story needed), first VP Sales hire
  (about to lose direct control of discounting), board pressure on burn multiple.
- Watering holes: founder communities, their investors (VC platform channel), LinkedIn.
- Hook: speed and self-serve. "Upload one CSV, in memory, never stored; if the number is
  boring, delete the tab." One decision-maker, no procurement: the fastest possible first
  logo, accepted opportunistically per the market-narrow/build-neutral decision.

**Anti-persona (do not target):** seat-based-only enterprises >$100M (Pricefx/Vendavo
territory), companies <$8M ARR (too few deals for band-level win rates to mean anything),
CROs as first contact (the diagnostic names their reps; they enter after the champion),
retail/e-comm anything (per the 2026-05-29 decision).

---

## 7. The week-one sequence (what actually happens before any email goes out)

Day 1: restore Supabase + keep-alive + synthetic-submit uptime check; repo private; rotate
all four credentials; delete All Passwords.txt into a password manager.
Day 1-2: pick the single commercial structure; fix /pricing copy; engage counsel (NDA +
engagement letter + privacy/terms placeholders); start entity filing.
Day 2-3: API perimeter (shared-secret header, rate limits, size cap); cached /sample
fallback + prospect-safe error copy; fail-fast env guards; Sentry both tiers + spend alert.
Day 3-4: OG metadata + sitemap; lead form to 2 fields with try/catch; reconcile
DiagnosticPreview with the real sample; de-fang DRAFT stamps once counsel-dated; Vercel
cookieless analytics + funnel tracker spreadsheet.
Day 4-5: segment-aware reference discounts + advisor call scheduled; readout-to-pilot close
script + objection doc into gtm/; data-handling SOP + per-customer register + IR one-pager.
Then: build the 120-150 target list against personas 1-2 and send touch #1.

---

## 8. Tech-stack review (added 2026-06-11, post-fix pass)

Verdict up front: every technology choice is right-sized for a solo pre-seed company; all of
the failures found were configuration and operations, not architecture. Nothing needs
replatforming. Two line items are worth money now (Supabase Pro, Sentry); everything else is
keep-and-harden, and the hardening shipped today.

| Layer | Choice | Assessment |
|---|---|---|
| Web | Next.js App Router on Vercel | Right. Was missing metadata/sitemap/error pages/headers/analytics (all added). No staging env; Vercel preview deploys partially cover this, acceptable until the first paid pilot. |
| API | FastAPI on Render Starter ($7/mo) | Right. Starter does not sleep (health answered in <1s cold), but the /sample render had no timeout or fallback, so any API hiccup took the funnel's front door down (fixed: 8s timeout + bundled snapshot). Perimeter was fully open (fixed: shared-secret + rate limits + size cap). Single 512MB instance is fine to ~10 customers of CSV-sized workloads. |
| DB | Supabase free | The week's villain: free-tier 7-day pause silently killed prod lead capture. Keep-alive action now prevents recurrence; RLS now on. Recommend Pro ($25/mo) for real backups, since /privacy promises "daily automated backups" that free tier does not deliver. |
| Engine | pandas + sklearn, deterministic core, LLM narration-only | The strongest layer: 144 tests, adversarial ingest fixtures, receipts-and-caveats output. The LLM-never-invents-numbers architecture is the correct one for this buyer and is now also timeout-hardened. |
| Embeddings | fastembed (local) | Right: it is the privacy story ("row data never leaves") and costs nothing. Keep. |
| LLMs | OpenAI gpt-4o + Anthropic, Perplexity/Tavily for web | Fine. Timeouts added; rate limiter bounds abuse. Missing piece is provider-side spend caps (founder console action). |
| Charts/motion | Recharts 3 + Framer Motion | Fine; Tremor avoided for the React 18 pin, good call. Motion now reduced on product surfaces and SSR-safe in the hero. Watch bundle size if more chart types land. |
| Leads/notify | Supabase + Resend | Fine; magic-link plumbing is genuinely good. Now rate-limited and origin-pinned. SPF/DKIM verification is the remaining founder step. |
| Observability | None | The real gap left: Sentry on both tiers the day the founder creates the account; until then the keep-alive action is the only alarm. |
| Dev machine | Windows + unresolved torn-write agent | The only unsound component in the stack. Mitigations (commit-on-green, push-all-branches, sync-excluded data folder per the new SOP) are in place, but customer CSVs should never live on this disk longer than a processing run. |

Deferred by design and still correct to defer: Snowflake/Fivetran/dbt (Phase 3C), SOC 2
(questionnaire + security one-pager until then), LangGraph/MLflow (no orchestration or model
registry needed at one model), WorkOS (no enterprise SSO buyer yet).
