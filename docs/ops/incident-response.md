# Incident response (one page)

Owner: Adhithya Bhaskar (adhithya@pricekeel.com). Scope: any suspected or confirmed
unauthorized access, loss, corruption, or disclosure of customer data. The NDA and the
privacy page both promise customer notification within 72 hours of a confirmed breach;
this page is how that promise is met by one person under stress. Companion:
`docs/ops/data-handling-sop.md` (the data register is the scoping source).

## 1. Detection triggers (any of these starts the clock)

- File integrity failure: a customer file's SHA-256 no longer matches the access-log hash,
  or the known corruption agent touches `C:\pricekeel-customer-data\`.
- Unexpected access: Supabase logs show reads/writes you did not make; Render or Vercel
  shows deploys, env-var changes, or traffic you did not initiate.
- Credential exposure: any key, password, or access code found in a public repo, paste,
  email thread, or screenshot.
- Provider notice: breach notification from Supabase, Render, Vercel, OpenAI, Microsoft,
  or GoDaddy affecting our tenancy.
- Customer report: "we received something odd" or "someone has our numbers."
- Register mismatch: the data register and reality disagree about what we hold or where.

## 2. Scope (first hour)

Open `docs/ops/data-register.md` and answer in writing: which customers' data could be
affected, what categories (deal rows, contact details, access codes), the time window, and
whether exposure is confirmed or only possible. The register is why scoping takes minutes
instead of days; if it cannot answer these questions, that gap is a finding for the
post-incident review.

## 3. Containment (in parallel with scoping)

- Rotate all keys: Supabase service + anon keys, database password, OpenAI and Perplexity
  keys, PRICEKEEL_SECRET, Vercel and Render tokens.
- Revoke or rotate customer access codes and invalidate outstanding magic links.
- Pause the API (Render service suspend) if it is a plausible vector; the static site can
  stay up.
- Isolate affected local files: copy to a quarantine subfolder for forensics, hash them,
  stop all processing runs.
- Preserve evidence before fixing: export provider logs, screenshot anomalies, note
  timestamps. Do not destroy state the review will need.

## 4. Customer notification (within 72 hours of confirmation, earlier if practical)

> Subject: Security notice from Pricekeel regarding your data
>
> Hi [name],
>
> I am writing to notify you of a security incident affecting data you provided to
> Pricekeel, per our NDA commitment to notify you within 72 hours.
>
> What happened: [one factual paragraph, no speculation].
> What was affected: [specific files/categories from the data register; state plainly what
> is confirmed versus possible].
> When: [detection date/time; window of exposure as best known].
> What I have done: [containment actions taken, with timestamps].
> What I am still doing: [open investigation items and when you will hear next; commit to a
> specific date].
> What you may want to do: [any customer-side actions, e.g. rotating an access code].
>
> I will send an update by [date] even if there is nothing new. Direct line for questions:
> adhithya@pricekeel.com.
>
> Adhithya Bhaskar, Pricekeel

Honesty rule: never minimize, never speculate, never say "out of an abundance of caution"
when the cause is known. State facts, unknowns, and the next update date.

## 5. Regulator thresholds (one paragraph)

Customer data is business deal data, largely non-personal, but rep identifiers, contact
details in the leads table, or any EU/UK personal data can trigger statutory duties. Where
GDPR applies, a personal-data breach must be reported to the supervisory authority within
72 hours of awareness unless it is unlikely to risk individuals' rights, and affected
individuals notified without undue delay when risk is high. US state breach-notification
laws vary by state in scope, triggers, and deadlines, and generally key on personal
information such as name plus identifiers. Decision rule for a solo founder: if any
personal data of EU/UK individuals or US-state-covered personal information is plausibly
involved, engage counsel the same day and let them call the regulator question; our 72-hour
customer notice happens regardless.

## 6. Post-incident review (within 7 days, written, filed in `docs/ops/`)

- Timeline: detection, scoping, containment, notification, resolution, with timestamps.
- Root cause: what actually failed (technical, process, or judgment), stated plainly.
- What worked / what did not: against this document, section by section.
- Register and SOP gaps: did the data register answer the scoping questions in an hour?
- Fixes with dates: each corrective action gets an owner (there is one) and a deadline.
- Disclosure: affected customers get the summary of the review on request; offering it
  unprompted is usually the better move.
