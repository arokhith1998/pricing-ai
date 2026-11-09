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
Salesforce connection is available to customers we authorize; its handling is described below.

## Architecture: what data goes where

| Component | Provider | What it holds |
|---|---|---|
| Web app (pricekeel.com) | Vercel (US) | HTTP requests and session cookies. No deal data. |
| Analysis API (api.pricekeel.com) | Render (US) | Your CSV during processing, **in memory only**. Nothing written to disk, no database of deal data. |
| Database | Neon (US) | Contact details from the lead form, access codes, and the decision log, which holds the deal identifier and discount figures for decisions you log; no bulk deal rows. If Salesforce is connected: encrypted OAuth tokens and connection and mapping metadata. |
| LLM | Anthropic API | Aggregate figures, column header names, uploaded document chunks, question text and public pricing-page text, for narration, column-header mapping, copilot answers and plan extraction. See "What the cloud LLM sees" below. |
| Email | Microsoft 365 (US/EEA); Resend (region depends on account configuration) | Correspondence, including files you choose to email us; transactional email such as sign-in links. |

Full subprocessor list with DPA links and link status: pricekeel.com/subprocessors. Salesforce OAuth tokens
are encrypted with AES-256-GCM before storage, and disconnecting removes the stored tokens.

## The no-retention CSV path

pricekeel.com/upload is the zero-trust option: your CSV is parsed and analyzed in memory
within the request, results render in your browser, and nothing is stored. The founder
never sees the file or the results. If your policy prohibits sending data to vendors, this
path means you never have to.

## What the cloud LLM sees, and never sees

Every number in a Pricekeel readout is computed by a deterministic, tested analysis engine.
The LLM never computes a figure. Anthropic receives: aggregate figures, column header
names, uploaded document chunks, question text, and public pricing-page text. Its purposes
are narrating results it is handed, column-header mapping, copilot answers, and plan
extraction.

**Deal rows from CSV uploads are never sent.** Documents you upload to the copilot for Q&A
are sent in chunks, so do not upload deal exports as documents. The provider, Anthropic, is
bound by its Commercial Terms (which state it may not train models on customer content) and
its data-processing addendum. The optional web search (Perplexity Sonar, Tavily) receives
question text only, and only when you turn it on.

## Contractual commitments

- **Mutual NDA before any founder-run analysis**, ours or yours.
- **Purpose limitation:** your data is used only to deliver your engagement. Cross-customer
  benchmarking happens only with explicit written opt-in, off by default.
- **Deletion:** within 30 days of engagement end or on request, with written certification.
- **Breach notice:** within 72 hours of a confirmed breach affecting your data, backed by a
  written incident-response procedure and a per-customer data register so scoping is fast.
- **Decision log:** if you log approvals or exception requests, that record is deleted
  manually by customer reference on request or at engagement end. No automatic purge exists,
  and no retention window is promised beyond what the privacy page states.
- Founder-run files are handled under a written data-handling SOP: one encrypted local
  folder, excluded from sync clients, access-logged per file.

## Current state, honestly

- **No SOC 2.** Pre-revenue company; an audit at this stage would be theater. We will
  complete security questionnaires instead, and this page is written to start that.
- **Solo founder.** One person has data access, which is also why the access log is
  short and provable. The bus-factor risk is real; the deletion and breach commitments
  bind contractually regardless.
- **Legal entity in formation; counsel not yet engaged.** The NDA and terms are drafts
  pending counsel review. We will not take customer data under signature until both are
  complete.
- No third-party analytics or trackers on the site.

## Roadmap (security items, in order)

1. Entity formation, then counsel review of the NDA, terms, and privacy policy (counsel not yet engaged).
2. API authentication hardening and per-customer access revocation.
3. Error monitoring and alerting on both tiers; uptime checks on the lead path.
4. E&O and cyber insurance bound before the first paid engagement.
5. SOC 2 Type I when customer count justifies it; questionnaire support in the meantime.

If your review finds something we missed, tell us: we would rather fix it than argue.
