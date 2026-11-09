---
title: Pricekeel security one-pager (forwardable, for prospect IT review)
created: 2026-06-11
updated: 2026-11-09
tags: [gtm, security, trust, it-review]
status: active
---

# Pricekeel security one-pager

Written for the person doing the vendor review. Plain language, no certifications we do not
hold, no claims we cannot demonstrate. Questions: Adhithya Bhaskar, adhithya@pricekeel.com.

## What Pricekeel does

Pricekeel runs a pricing diagnostic on a CSV export of your closed deals (won and lost):
price realization, win rate by discount band, and the specific deals behind each finding.
The CSV path needs no CRM integration, no API keys to your systems, and no PII: account and
opportunity-level fields only, with reps as internal identifiers. A separate, optional
Salesforce connection exists for authorized customers; its handling is described below.

## Architecture: what data goes where

| Component | Provider | What it holds |
|---|---|---|
| Web app (pricekeel.com) | Vercel (US) | HTTP requests and session cookies. No deal data. |
| Analysis API (api.pricekeel.com) | Render (US) | Your CSV during processing, **in memory only**. Nothing written to disk, no database of deal data. |
| Database | Neon (US) | Contact details from the lead form, access codes, and the decision log. If Salesforce is connected: encrypted OAuth tokens and connection and mapping metadata. **No deal rows.** |
| LLM | Anthropic API | Narration of computed results and column-header mapping only. See "What the LLM sees" below. |
| Email | Microsoft 365 (US/EEA); Resend (US) | Correspondence, including files you choose to email us; transactional email such as sign-in links. |

Full subprocessor list with DPA links: pricekeel.com/subprocessors. Salesforce OAuth tokens
are encrypted with AES-256-GCM before storage, and disconnecting removes the stored tokens.

## The no-retention CSV path

pricekeel.com/upload is the zero-trust option: your CSV is parsed and analyzed in memory
within the request, results render in your browser, and nothing is stored. The founder
never sees the file or the results. If your policy prohibits sending data to vendors, this
path means you never have to.

## What the cloud LLM sees, and never sees

Every number in a Pricekeel readout is computed by a deterministic, tested analysis engine.
The LLM is used only to narrate results it is handed. It receives **aggregate figures and
column header names only**: realization percentages, band-level win rates, header strings
for column mapping. It never receives deal rows, account names, or amounts tied to
identifiable records. The provider, Anthropic, is bound by its Commercial Terms
(which state it may not train models on customer content) and its data-processing addendum.
Because only aggregates and headers are sent, provider-side retention never holds your
row-level data.

## Contractual commitments

- **Mutual NDA before any founder-run analysis**, ours or yours.
- **Purpose limitation:** your data is used only to deliver your engagement. Cross-customer
  benchmarking happens only with explicit written opt-in, off by default.
- **Deletion:** within 30 days of engagement end or on request, with written certification.
- **Breach notice:** within 72 hours of a confirmed breach affecting your data, backed by a
  written incident-response procedure and a per-customer data register so scoping is fast.
- **Decision log:** if you log approvals or exception requests, that record is retained for
  your engagement plus the audit window in the privacy policy, and deleted on request.
- Founder-run files are handled under a written data-handling SOP: one encrypted local
  folder, excluded from sync clients, access-logged per file.

## Current state, honestly

- **No SOC 2.** Pre-revenue company; an audit at this stage would be theater. We will
  complete security questionnaires instead, and this page is written to start that.
- **Solo founder.** One person has data access, which is also why the access log is
  short and provable. The bus-factor risk is real; the deletion and breach commitments
  bind contractually regardless.
- **Legal entity in formation; counsel review of the NDA and terms in progress.** We will
  not take customer data under signature until both are complete.
- No third-party analytics or trackers on the site.

## Roadmap (security items, in order)

1. Entity formation and counsel-reviewed NDA, terms, and privacy policy (in progress).
2. API authentication hardening and per-customer access revocation.
3. Error monitoring and alerting on both tiers; uptime checks on the lead path.
4. E&O and cyber insurance bound before the first paid engagement.
5. SOC 2 Type I when customer count justifies it; questionnaire support in the meantime.

If your review finds something we missed, tell us: we would rather fix it than argue.
