# Market sizing re-evaluation, 2026-09-27

## 1. Arithmetic check: the vault reproduces

Recomputed every figure in the corrected notes. All reproduce.

- Pre-funnel: 3,000 x $30K = $90M; 3,600 x $60K = $216M. Tier A: 350 x $30K = $10.5M,
  480 x $60K = $28.8M. Tier B: $3.9M to $11.4M. Matches the tables.
- Collapse: 7.5x, 8.6x, 6.3x, 10.3x. "Roughly 8x, range 6x to 10x" is correct.
- Bridge: 2 x 1.5 x 2 x 2 = 12; 2 x 2 x 3 x 3 = 36. On $11M to $29M = $132M to $1.05B.
  Conservative geography 1.7x to 2x gives 10.2x to 24x = $112M to $700M. Correct.
- SOM: midpoint 415; 8-12% = 33 to 50 accounts; at $45K = $1.5M to $2.3M; span
  $0.8M to $3.5M; old SOM = 24% to 60% share. All correct.
- One nit only: the Tier B SOM row rounds 13-19 accounts x $45K ($0.58M to $0.86M)
  to "$0.5M to $1.0M". Print $0.6M to $0.9M.

The 2026-09-11 amendment line 103 is garbled prose ("3,600 and 3,000 against their
matched ends") though the numbers are right. Rewrite as 3,600/480 and 3,000/350.

## 2. Stale numbers still on this tree

`tools/build_investor_deck.py`
- :396 "$120M to $215M SAM" -> $90M to $216M
- :397 "collapses it four to six times" -> roughly 8x, range 6x to 10x
- :407 card "$120M to $215M" -> $90M to $216M
- :427 "roughly 15 to 40 times" -> 12x to 36x (conservative 10.2x to 24x)
- :428 "$300M to $1B+" -> $132M to $1.05B (conservative $112M to $700M)
- :438 geography "~2 to 3x" -> 1.7x to 2x, the company's own global/US ratio
- :203 "Adyen agrees to acquire Orb" -> completed 1 Jul 2026
- :204 "Salesforce agrees to acquire m3ter" -> completed 1 Jul 2026
- :210 window "12 to 18 months" -> 9 to 15 months, to Q2/Q3 2027
- :543 defensibility "12 to 18 months" -> 9 to 15 months (:641 runway is fine)
- No SOM slide exists. Once the founder signs the draft, add 33 to 50 accounts,
  $1.5M to $2.3M, labeled ACV-hypothesis.

`gtm/llama-ventures/pitch-base.md`
- :57 "$120M to $215M" -> $90M to $216M
- :178-179 "$40K to $60K ACV ... $120M to $215M" -> $30K to $60K, $90M to $216M
- :197-198 "15 to 40x ... $300M to $1B+" -> 12x to 36x, $132M to $1.05B
- :109 / :110 "agreed to acquire" -> both completed 1 Jul 2026
- :113 "verified 2026-08-09" -> 2026-09-26
- :116, :164 "12 to 18 months from mid-2026" -> 9 to 15 months
- :58, :203-204 the $350M to $850M adjacency at $60-120K ACV is a second
  unvalidated ACV. Label it as such or drop it.

Same set unfixed in `gtm/llama-ventures/rehearsal-script.md:113,114,121,144,154,159,170,171`.

## 3. Verdict

Upgraded. The vault is now the cleanest sizing chain I have audited at this stage:
pre-funnel labeled and retired, one ACV band, a collapse factor that divides, a
bridge that multiplies, and a SOM that admits the wedge cannot fund a Series B.
The remaining exposure is purely distribution: every corrected number lives in
`vault/` while the investor-facing surfaces on this tree still carry the retired
ones. Ship the corrections or an investor reads the old deck against the new note.
The 350 to 480 count remains the only wholly unsourced figure and it carries the slide.

## 4. The one thing next week

Unchanged and now overdue: instrument the funnel. Measure four gates on the 18 named
US candidates (`2026-08-09-two-tier-sizing...:133-135`) and publish per-gate survival
with n. Fold the deck and pitch-base edits into that same PR.

## 5. Landing page, category positioning

- **Claim the decision record.** Every discount exception priced, evidenced and
  logged before approval. That is a category nobody owns; price optimization is one
  Vendavo already does.
- **Claim the evidence floor.** Show the comparable deals and say "insufficient data"
  out loud. Explainability is the enterprise buying criterion, not accuracy.
- **Claim speed.** First recommendation in under two weeks from a CSV, any CRM,
  against incumbent 6 to 12 month deployments.
- **Drop:** "usage or hybrid SaaS" as differentiation (V1 prices a discount percent,
  keep it as a fit note only), any market-size figure, and "system of record".
