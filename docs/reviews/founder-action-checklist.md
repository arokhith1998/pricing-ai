# Founder action checklist (post review-fixes, 2026-06-11)

Everything engineering-fixable was fixed on branch `review-fixes` (see
`2026-06-11-full-company-review.md`). These items need YOU because they require accounts,
money, counsel, or a signature. Ordered by urgency.

## Done for you today (no action, awareness only)

- Supabase project RESUMED (it had paused and killed prod lead capture; verified working
  end-to-end after resume). RLS enabled on `leads` + `access_codes` (service role bypasses;
  app unaffected, verified live).
- GitHub repo set to PRIVATE. Keep-alive + uptime GitHub Action added (Mon+Thu; a failed run
  emails you). GH secrets SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY set for it.
- One commercial structure decided and applied everywhere (vault decision note 2026-06-11;
  veto window open until the first readout call).

## This week, in order

1. **Engage counsel (the critical path, not outreach).** Package: NDA + data addendum
   (including the new DRAFT benchmarking-consent and liability-cap sections), pilot
   engagement letter, privacy + terms finalization. Prospect-side legal review takes 1-3
   weeks, so counsel must finish ~Jun 20 to protect the Jul 31 first-CSV goal.
2. **File the entity** (~Jun 24 per roadmap; before any NDA signature). If you are on a
   student/work visa, immigration attorney BEFORE filing.
3. **Rotate all credentials**, then delete `All Passwords.txt` into a password manager
   (1Password/Bitwarden). Rotate: Supabase service key + DB password (dashboard), Perplexity
   key (console), PRICEKEEL_SECRET (generate new). Update in: Vercel env, Render env, and the
   two GitHub Actions secrets. Reason: the file sat in plaintext during the public-repo era,
   on a machine with an unidentified sync/corruption agent.
4. **Close the API perimeter**: generate one random key, set `PRICEKEEL_API_KEY` in BOTH
   Render and Vercel, redeploy both. Until set, api.pricekeel.com stays open (code is
   deployed and enforces the moment the env var exists). Also confirm in Vercel:
   `PRICEKEEL_SECRET`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` are present (the app now
   fails fast in production without them) and `PRICEKEEL_ENV` is NOT `dev` on Render.
5. **Sentry**: create the account, add DSN to both tiers (the code-side wiring is a 30-minute
   follow-up once you have the DSN; ask and it gets done).
6. **Provider spend caps**: set hard monthly limits in the OpenAI, Anthropic, and Perplexity
   consoles. The rate limiter bounds abuse; the caps bound the blast radius.
7. **Email deliverability before touch #1**: verify SPF/DKIM/DMARC for pricekeel.com sends
   (M365 + Resend) at e.g. mxtoolbox.com. Cold outreach from an unauthenticated domain is
   dead on arrival.

## Next two weeks

8. **E&O + cyber insurance** quote (Vouch/Embroker class, roughly $2-6K/yr); bind between
   incorporation and the first real CSV.
9. **Advisor methodology call**: segment-aware references are now shipped (demo headline
   $11.2M → $8.9M); get the sign-off the roadmap already requires. HARD GATE: no real-data
   readout before sign-off.
10. **Supabase plan decision**: keep-alive prevents pausing, but Pro ($25/mo) adds real
    backups (the privacy page promises "daily automated backups"; verify that claim or
    soften it).
11. **Blog cadence**: Jun 9 and Jun 11 posts are missing; the calendar already slipped.
    Write or reschedule before prospects you email see a stale blog.
12. **Warm channels**: recruit 3-5 pricing consultants / fractional CFOs and pitch one VC
    platform team (CBO review, section 3). Target list to 120-150.

## Decisions you may want to revisit (made today, reversible)

- The web sample still headlines the GLOBAL leakage lens ($11.2M, labeled) for internal
  consistency; the segment-aware number ($8.9M) ships in the API payload and the CLI readout.
  Adopting it as the web headline is a deliberate follow-up PR (touches sample, diagnostic,
  copilot, preview).
- Lead form sends sentinel values ("Not provided"/"Unknown") for blank optional fields to
  keep the API contract; clean up by making the route accept empties.
- `web/src/components/FounderCta.tsx` still contains the removed $626M chip but is unused;
  delete when convenient.
