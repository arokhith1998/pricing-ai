# Pricekeel whole-codebase review (read-only)

## Verdict

This is a serious codebase, well above what a pre-seed repo usually looks like: the
SSRF fetcher, the API perimeter, the ingest disclosure report, and the honesty labels
on every verdict are real engineering, and the Python suite (21 files, roughly 200
tests) asserts behavior rather than execution. It is not clean, though. The governance
digest, the one artifact that leaves the building by email, miscounts and mislabels CRM
activity, and I reproduced it. The demo tier writes user-typed names and justifications
into a shared tenant bucket that every other lead-gated visitor can read back. And the
strongest claim in the product, the dollar EV uplift on /recommend, is the only surface
that ships without the correlational caveat the rest of the codebase is scrupulous
about. Fix those three and this is close.

## Findings

**1. BLOCKER. Weekly digest miscounts CRM governance activity.**
C:\Pricing-AI\pricing\governance.py:435 counts every kind="exception" row as an
"exception request", and line 436 flags below-floor from verdict.below_floor. The CRM
path at C:\Pricing-AI\api\main.py:1057 writes a verdict with outside_guardrail and no
below_floor key, and C:\Pricing-AI\api\main.py:1229 writes Salesforce writeback receipts
under the same kind. Reproduced: one deal with one 32 percent override request, its
approval, and one writeback receipt renders as "3 exception requests this week, 0 below
the 15 percent floor". Both halves are wrong, and /api/digest/send emails it. Fix:
filter the digest to request-type events and exclude source salesforce_crm_writeback,
and read below-floor as verdict.get("below_floor") or verdict.get("outside_guardrail").
Add a known-answer test that seeds one CRM override plus one writeback and asserts the
headline reads 1 and 1.

**2. HIGH. Lead-gated visitors share one tenant and can read entries from each other.**
C:\Pricing-AI\web\src\lib\gate.ts customerRef returns "default" for anyone without an
access code, and C:\Pricing-AI\web\src\app\api\exceptions\route.ts:10 gates POST and GET
on requireLead only. Visitor A posts requested_by (a real name) and a free-text
justification; visitor B reads both back from GET /exceptions. The comment calls this
correct because it is the shared demo book, but these rows are visitor-entered text, not
demo data. Neither field is length-capped, so it is also an unauthenticated unbounded
write into production Neon. Fix: mint a signed per-visitor demo tenant (demo:<uuid> in a
cookie) instead of "default", and cap justification length in the route and in the
Pydantic model.

**3. HIGH. /recommend presents a correlational sweep as a causal dollar recommendation.**
C:\Pricing-AI\pricing\model.py:137 sweeps discount_pct through a classifier that learned
discount from observational deals, then C:\Pricing-AI\api\main.py:1379 returns uplift in
dollars labeled method: modeled_ev_curve with no caveat field. Every other surface
carries one: crm.guidance_for_open_deal has caveat, metrics.leakage says correlational,
copilot has _RECOVERABLE_CAVEAT. This is the number that lands in a pricing committee.
Fix: add a caveat key to the /recommend response and to leakage_vs_model, worded like the
CRM one, and render it beside the uplift in GuidanceClient.tsx. The stack already lists
DoWhy and CausalML for the deeper fix.

**4. HIGH. The house no-em-dash rule is unenforced exactly where text is generated.**
None of the three system prompts forbid em dashes and all three contain them, which is
what a model imitates: C:\Pricing-AI\pricing\assist.py:136,
C:\Pricing-AI\pricing\rag.py:149, C:\Pricing-AI\pricing\copilot.py:506. Deterministic UI
strings ship them too: copilot.py:173, :187, :190, :282, :333, :413, plus the ingest
disclosure at C:\Pricing-AI\pricing\ingest.py:472. Only governance.py:14 even mentions
the rule. Fix: add "never use em dashes, use commas, colons or periods" to all three
prompts, strip the seven literals, and add a test that scans the generated-string
surfaces for U+2014.

**5. MEDIUM. The per-IP rate limiter never sees the user.**
C:\Pricing-AI\api\main.py:130 trusts the first X-Forwarded-For, but apiFetch in
C:\Pricing-AI\web\src\lib\api.ts never forwards the browser IP, so every request arrives
with the Vercel egress IP. /ask at 10 per 60s is therefore one global bucket for all
customers: one chatty user throttles everyone. In the other direction, any holder of the
API key spoofs the header and bypasses the limiter entirely. Fix: key the bucket on
X-Pricekeel-Customer with an IP fallback, and forward the real client IP from the proxy
in a header the API trusts only from the proxy.

**6. MEDIUM. Uploaded document chunks are not tenant-scoped.**
C:\Pricing-AI\api\main.py:551 keys _DOC_STORE on a client-supplied session_id alone and
:683 reads it with no customer check. /api/docs requires an access code but /api/ask
requires only the lead cookie, so a session id is a bearer token for uploaded policy
documents belonging to another customer. The decision log received exactly this fix
(Finding 3 in the comments); the doc store did not. Fix: key on (customer_ref,
session_id) and pass _customer_ref(request) on both paths.

**7. MEDIUM. /ask forwards a client-supplied analysis blob straight into the prompt.**
C:\Pricing-AI\api\main.py:684 accepts analysis: dict from the caller and
C:\Pricing-AI\pricing\rag.py:176 serializes it into the LLM context under a comment
saying row-level customer data is never sent. But _analysis_payload includes
top_leak_deals, trade_or_give_deals, quarter_end_deals and comparables, each carrying
resolved_account_name and opportunity_id. Named customer deals do reach the provider.
Either strip the deal-level arrays in rag.ask, or correct the three docstrings that
promise otherwise (assist.py:6, rag.py:12, main.py:611).

**8. MEDIUM. Repeated bootstrap work and one database connection per store operation.**
metrics.reference_discount runs a 500-sample bootstrap per band and is recomputed from
scratch by leakage, segment_reference_table (once globally plus once per segment),
top_leak_deals, defended_vs_investigate, trend_by_quarter, policy_simulations and
new_vs_renewal, so a single run() repeats it roughly a dozen times on identical input.
Separately, C:\Pricing-AI\pricing\governance.py:137 and :202 open a fresh psycopg
connection per insert and per list, so one /crm/workflow call costs up to three Neon
handshakes. Fix: memoize the reference on a frame fingerprint and thread it through; use
a module-level pool.

**Low.** The Streamlit app hardcodes the v1 palette (app/_app_lib.py:25) while the web
uses v2, so the two shipped UIs are off-brand from each other. /matching/competitor
(api/main.py:1296) takes an untyped req: dict unlike its two neighbours and returns 200
with an empty plan list when the SSRF guard blocks, which reads to a user as "no plans
found".

## Three genuinely good things

1. C:\Pricing-AI\pricing\_safe_fetch.py resolves, validates every returned address, pins
   the socket to a checked IP through a custom adapter, re-validates each redirect hop,
   and fails closed rather than falling back to an unpinned GET. Most implementations of
   this have the rebinding hole. It has 319 lines of tests behind it.
2. The perimeter fails closed in both directions: no API key in production returns 503
   rather than serving (api/main.py:172), and an unset PRICEKEEL_ENV is treated as
   production for CORS (:238). tests/test_api_perimeter.py asserts the whole prod/dev
   matrix, including the lying-Content-Length backstop.
3. The honesty scaffolding is real rather than decorative: _guard_degenerate_list refuses
   a book instead of reporting a confident zero, persisted never claims durability it
   does not have, book_source: "demo" discloses the shared book, actor_assertion:
   "self_asserted" refuses to imply authentication, and the self-approval guard is tested.

## The one thing to fix next week

Give every visitor a real tenant key. The shared "default" bucket is what turns finding 2
into a data exposure, it is what will make the digest fix in finding 1 produce correct
numbers for the wrong person, and it has to be right before Salesforce data from a design
partner lands in the decision log.
