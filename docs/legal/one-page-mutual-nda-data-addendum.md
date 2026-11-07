# Mutual NDA + Data-Handling Addendum (1-page)

> ⚠️ **Not legal advice. Starting template only. NOT SIGNABLE in its current form.** This
> document must not be sent to, or signed by, any party until (a) qualified counsel has
> reviewed and adapted it to the governing jurisdiction, and (b) the Company legal entity is
> formed and named below (the "Company" signature block currently has no legal person behind
> it). Bracketed `[...]` fields need completion. Sections 9 through 12 are DRAFT additions
> awaiting counsel review and are marked as such.
>
> **Changelog.** 2026-11-07 [DRAFT, for counsel]: added one marked retention bullet to section 4
> (aggregate statistics) and a new section 12, Schedule A: Data classes (Classes 1 to 3, pilot
> scope, integration credentials). Counsel reviews all of these before any use. Nothing in this
> file is executed, and no wording here has been judged legally sufficient.

**Parties:** [Your Company, Inc.] ("Company") and [Design Partner, Inc.] ("Partner").
**Effective date:** [date].

### 1. Purpose
The parties wish to explore a pricing-intelligence design-partnership (the "Purpose"). Partner may
share business data, including historical deal, quote, discount, and billing records, to evaluate it.

### 2. Confidential Information
"Confidential Information" = non-public information disclosed by either party, in any form, including
Partner's customer, revenue, pricing, and deal data, and Company's models, methods, and software.

### 3. Obligations
Each party will: (a) use Confidential Information solely for the Purpose; (b) protect it with at least
reasonable care; (c) limit access to personnel/contractors with a need to know who are bound by
confidentiality; and (d) not disclose it to third parties without prior written consent.

### 4. Data handling (applies to Partner data)
- **Purpose limitation:** Company uses Partner data only to deliver the Purpose for Partner.
- **No model training without consent:** Company will not use Partner data to train models that
  benefit other customers without Partner's prior written consent. Aggregated, fully de-identified
  benchmarks are permitted only if individual Partner data is not derivable.
- **Security:** access controls, encryption in transit and at rest, and audit logging of access.
- **Subprocessors:** any cloud/processing subprocessors disclosed on request; bound by equivalent terms.
- **Deletion / return:** on request or termination, Company deletes or returns Partner data within
  [30] days and certifies deletion in writing.
- **[DRAFT, for counsel] Retention of aggregates:** Deal rows are processed in memory and deleted
  per section 12, and Company may retain, per Partner, aggregate statistics (such as win rate by
  discount band and reference discounts, with counts) that contain no deal rows, no account names
  and no individual values, which Company deletes within [N] days of Partner's written request.
- **Breach notice:** Company notifies Partner without undue delay (and within [72] hours) of any
  confirmed breach affecting Partner data.

### 5. Exclusions
Obligations do not apply to information that is public through no fault of the receiver, already known
without duty of confidence, independently developed, or rightfully received from a third party.

### 6. Term
Confidentiality survives [2] years from disclosure (indefinitely for trade secrets while they remain so).
Either party may terminate the evaluation on [14] days' written notice; data-handling obligations survive.

### 7. No license / no obligation
No IP license is granted except the limited right to use data for the Purpose. Nothing obligates either
party to proceed to a commercial agreement.

### 8. Governing law
[State/Country]. Disputes resolved in the courts of [venue].

---

> 🚧 **DRAFT, FOR COUNSEL REVIEW. Sections 9 through 12 below are proposed additions and are
> not part of the operative template until counsel approves them.**

### 9. [DRAFT] Optional benchmarking consent (opt-in; default is OFF)

This section applies **only if Partner affirmatively opts in** by checking the box and
initialing below. Absent that opt-in, section 4 governs unchanged: no cross-customer use of
Partner data of any kind.

- **Scope of consent:** Company may include Partner data in aggregated, anonymized
  cross-customer benchmarks (for example: median price realization, win-rate-by-discount-band
  distributions by segment and pricing model).
- **Hard limits:** no row-level or deal-level Partner data is ever exposed to any third
  party; no benchmark output may identify Partner or permit Partner's individual data to be
  derived (including by small-cohort inference; benchmarks publish only above a minimum
  cohort size of [10] consenting customers); Partner data is never used to train models that
  benefit other customers.
- **Withdrawal:** Partner may opt out at any time by written notice. Opt-out is honored
  prospectively: Partner data is excluded from all benchmark computations performed after
  notice. Benchmarks already published in aggregate form are not recalled.
- **Incentive:** consenting Partners receive the benchmark readout (their own figures placed
  against the anonymized cohort) at no additional charge, as it becomes available.

> ☐ **Partner OPTS IN to benchmarking under section 9.**  Initials: ________  Date: ________
>
> Leaving the box unchecked means no benchmarking use whatsoever. The diagnostic and all
> other services are identical either way.

### 10. [DRAFT] Commercial terms applicable to paid engagements

The following apply to any paid pilot or subscription executed under or alongside this
agreement, and are stated here for counsel to relocate into the engagement letter as
appropriate:

- **Payment at signature:** pilot and subscription fees are due in full at signature, before
  the first readout of the paid engagement is delivered.
- **Readout SLA:** each readout is due [N, default 5] **business days after validated
  intake**, defined as the date Company confirms in writing that Partner's submitted data
  passes intake validation. Calendar-named delivery dates are not used. Failure to meet the
  SLA entitles Partner to the remedy stated in the engagement letter.
- **Pilot success criterion (usage-based):** the parties will treat the pilot as
  successful when at least [20] deals have been run through Pricekeel's guidance
  (logged approvals and exception requests) during the pilot term, in addition to the
  delivered readouts. This is a shared definition of success for the conversion
  conversation, not a refund condition [counsel: confirm framing].
- **Liability cap:** each party's aggregate liability arising out of or relating to this
  agreement and any engagement under it is capped at the fees paid by Partner to Company in
  the twelve (12) months preceding the event giving rise to the claim. The cap does not
  apply to breaches of confidentiality obligations or to either party's willful misconduct
  [counsel: confirm carve-outs and conform to jurisdiction].

### 11. [DRAFT] Decision responsibility disclaimer

Company's deliverables are analytical and advisory only. They describe historical,
correlational patterns in Partner's data and do not constitute a promise of recoverable
revenue, a price recommendation guarantee, or financial advice. **All pricing, discounting,
and commercial decisions remain solely Partner's**, made by Partner's own personnel with a
human in the loop. Company is not liable for outcomes of decisions Partner takes or declines
to take based on the deliverables, subject to section 10's cap for everything else.

### 12. [DRAFT, for counsel] Schedule A: Data classes

Partner data falls into three classes. Company accepts only what each class below permits, and
declines or deletes anything outside it. Class membership is stated in the data register.

**Class 1: Deal and price data.** What section 4 covers today: historical deal, quote, discount,
and booked-value records, including closed-won and closed-lost outcomes and Partner's discount
policy.
- Deal rows are processed in memory and deleted within [30] days of engagement end or written
  request, with written certification, per section 4.
- Only the aggregate statistics described in section 4 may be retained.

**Class 2: Usage data.** Accepted only as aggregates or monthly rollups (for example, monthly
committed and consumed units per product line).
- Never row-level usage events.
- Never end-customer identifiers (no end-customer names, user IDs, account IDs, or emails).
- Company may decline or delete any submission that contains either.

**Class 3: Cost data.** Accepted only as a Partner-supplied rate or margin-percentage table by
product family.
- Never supplier names.
- Never part-level bill of materials.
- Never landed-cost or tax detail.
- **Excluded entirely from section 9 benchmarking, even if Partner opts in under section 9.**
  Class 3 data is never included in any cross-customer computation.
- Company may decline Class 3 data before signature, and may decline a given submission after.

**Scope for a first pilot.** Class 1 is in scope. Class 2 is optional and in scope only if Partner
elects it in writing. **Class 3 is off by default** and enters scope only through a written
amendment signed by both parties.

**Integration credentials.** No API keys or OAuth tokens are held by Company under a pilot unless
a written amendment names them. If such an amendment is made, Company will revoke or delete any
named credential within 24 hours of Partner's written request, and will record each credential
in Company's data register entry for Partner.

---

**Company:** ______________________  **Partner:** ______________________
