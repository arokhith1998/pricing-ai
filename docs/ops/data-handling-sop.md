# Customer data-handling SOP (one page)

> **READ FIRST: this machine has a known, unresolved file-corruption agent** (working trees
> truncated post-commit; suspected sync client or AV; culprit not yet identified). Customer
> files therefore NEVER sit in a synced, shared, or unaudited directory: no Drive, no
> Dropbox, no OneDrive, no Desktop, no Downloads, no repo. One designated folder only, as
> defined below. This supersedes the shared-cloud-folder setup in the older operate
> runbook.

Owner: Adhithya Bhaskar (adhithya@pricekeel.com). Applies to every customer or prospect
file containing deal, pricing, or revenue data, from first receipt to certified deletion.
The NDA data-handling addendum promises purpose limitation, access logging, 30-day
deletion with written certification, and 72-hour breach notice; this SOP is how those
promises are kept. Companion: `docs/ops/incident-response.md`.

## 1. Accepted receipt channels

**Preferred: the web path, pricekeel.com/upload.** CSV processed in memory, nothing
retained, founder never sees the file or the result. Steer every prospect here first.
Nothing to log, store, or delete: the best data handling is none.

**Founder-run path: email to adhithya@pricekeel.com only.** No Slack files, no shared
links, no USB, no personal addresses. On receipt, IMMEDIATELY (before any analysis):

1. Move the attachment to the ONE designated encrypted local folder:
   `C:\pricekeel-customer-data\<customer-slug>\` (BitLocker/VeraCrypt-encrypted volume,
   explicitly EXCLUDED from every sync client, indexer, and backup agent on this machine).
2. Delete the attachment from the mail client AND the mail provider's trash.
3. Record the file in the access log and the data register (below).
4. Verify the file opens and row count matches what the customer said they sent. The
   corruption risk on this machine makes a same-day integrity check mandatory; keep the
   file's SHA-256 hash in the access log and re-verify before each processing run.

Any file that arrives by a non-accepted channel: do not open it; ask the sender to resend
by email, then have them delete the original share.

## 2. Access log (one per customer, `access-log.md` inside the customer folder)

| File | Received | Location | Accessed by / when | Deleted when |
|---|---|---|---|---|
| velora-deals-2026q2.csv (sha256: ...) | 2026-06-15 | C:\pricekeel-customer-data\velora\ | AB 2026-06-15 (intake validation); AB 2026-06-17 (diagnostic run) | 2026-07-02, certified |

Every open, copy, or processing run gets a row entry. There is exactly one person with
access (the founder); the log exists so that statement is provable, not assumed.

## 3. Processing steps

1. Validate intake (schema, row counts, closed-lost rows present). The readout clock (N
   business days, default 5) starts only at validated intake; confirm the start date to
   the customer in writing.
2. Run the diagnostic from the designated folder. Derived artifacts (readouts, working
   files) live in the same customer folder, never elsewhere; they are customer data too.
3. Never paste row-level data into any LLM, chat tool, or third-party service. Aggregates
   and column headers only, per the security one-pager.
4. Deliver the readout; log the delivery in the access log and funnel tracker.

## 4. Deletion checklist (within 30 days of engagement end, or on request, whichever is sooner)

- [ ] Delete the customer folder contents (file + derived artifacts) with secure delete.
- [ ] Empty Recycle Bin; confirm no copies in mail trash, temp dirs, or shell history.
- [ ] Mark every access-log row "deleted" with date; retain the log itself (it contains no
      customer data).
- [ ] Update the data register status to "deleted + certified."
- [ ] Send the certification email (template below) and file the sent copy.

**Certification email template:**

> Subject: Deletion certification, [Customer], per our NDA
>
> Hi [name],
>
> Confirming in writing, per section 4 of our mutual NDA and data-handling addendum: all
> data [Customer] provided to Pricekeel ([file name(s)], received [date(s)]), together
> with all derived working files, was permanently deleted on [date]. No copies remain in
> our possession. The access log for the engagement is available to you on request.
>
> Thanks for the trust,
> Adhithya Bhaskar, Pricekeel

## 5. Per-customer data register (`docs/ops/data-register.md`, one row per customer; this is also the scoping source in an incident)

| Customer | What we hold | Where | Since | Status (held / deleted+certified) |
|---|---|---|---|---|
| (example) Velora Systems | closed-deal CSV, 1,438 rows; readout PDF | C:\pricekeel-customer-data\velora\ | 2026-06-15 | held |

Keep the register current the same day anything is received or deleted. If the register
and reality ever disagree, that is an incident-response trigger, not a paperwork error.
