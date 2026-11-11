---
title: JAIR paper literature review, week 1 (discount causality)
created: 2026-11-11
updated: 2026-11-11
tags: [research, jair, causal-ml, literature-review]
status: draft
source: docs/design/2026-11-11-jair-paper-discount-causality.md
---

# Week 1 literature review: discount causality paper

Companion to `2026-11-11-jair-paper-discount-causality.md`. Three research
agents searched and summarized; the two papers they could not open were then
read directly from the PDFs.

## Verification key

- **[T]** read from the paper's own text in this session.
- **[S]** agent summary of the arXiv HTML full text. A paraphrase, not
  line-checked. Re-read before quoting.
- **[A]** abstract or index metadata only (citation confirmed, content not read).
- **[M]** from an agent's memory. Confirm the citation before it goes in the paper.

No citation here should go into the manuscript without a human check against
the source. JAIR holds authors fully responsible for reference accuracy.

## 1. Kill-criterion verdict

**Not triggered. Proceed, with the contributions reshaped as in section 6.**

No paper found combines a rep-leniency instrument, decision-regret scoring,
abstention and the monotone-constraint analysis for negotiated quotes. Every
ingredient exists separately. The search has known holes: Google Scholar and
DBLP were unreachable, so "nothing found" is strong evidence, not proof.

| Contribution | Status | What threatens it |
|---|---|---|
| C1, bias direction and the monotone constraint | Open | Gupta and Kamble show a sign reversal driven by pricing behaviour. No source analyses whether a monotone constraint corrects endogeneity or only its sign |
| C2, regret versus slope error | Narrow it | Quadratic regret near the optimum is textbook. Only the sign-flip regime is new. Fernandez-Loria and Provost argue confounded data can still give good decisions, so we must show when it does not |
| C3, instrument plus bounds plus abstention | Highest risk, still open | IV pricing with regret bounds (Miao et al.), partial identification with worst-case regret (Bian et al.), deferral under hidden confounding (Ghoummaid and Shalit; Li et al.; Gao and Yin). None uses an instrument to decide when to defer |
| C4, benchmark | Open, differentiate | Bockel-Rickermann et al. have the same semi-synthetic shape with observed confounding and no rep structure |

## 2. Closest prior work

**Phillips, Simsek, van Ryzin (2015).** "The Effectiveness of Field Price
Discretion: Empirical Evidence from Auto Lending." Management Science 61(8),
1741 to 1759. DOI 10.1287/mnsc.2014.2084. [T, working-paper version]
- Indirect auto lender; dealers negotiate rates inside limits.
- Control function (Petrin and Train 2010) in a probit take-up model.
- Instrument: the average rate offered for similar loans (same amount cluster,
  term, vehicle type, subvention status) in the other 21 pricing regions in the
  same month. A Hausman-type instrument. **Not agent leniency.**
- Correcting for endogeneity raised elasticity estimates by 126% to 285%. The
  authors attribute this to the sales force using deal-specific information.
  The same correction found no endogeneity in a direct online lender's data.
- For us: the best empirical evidence on direction. The naive model
  understates price sensitivity, which is our "rescue" case (flattened curve).
  One lender, one industry. They call wider use of their instrument a
  promising research direction.

**Karlinsky-Shichor and Netzer (2024).** "Automating the B2B Salesperson
Pricing Decisions: A Human-Machine Hybrid Approach." Marketing Science 43(1),
138 to 157. DOI 10.1287/mksc.2023.1449. [T, instrument passages only]
- B2B aluminium retailer; a model of each salesperson's own pricing, tested in
  a field experiment, with a random forest that routes each quote to model or
  human.
- Demand model uses a control function with cost, cut and quarter fixed
  effects as instruments. **Not rep identity.**
- For us: the closest B2B setting and a precedent for routing between model
  and human. Their routing is learned from predicted profit, not from whether
  the causal effect is identified. Read sections 1 to 4 in full before writing
  related work.

**Bockel-Rickermann, Verboven, Verdonck, Verbeke (2023).** "A Causal
Perspective on Loan Pricing: Investigating the Impacts of Selection Bias on
Identifying Bid-Response Functions." arXiv 2309.03730. [S]
- Over 12,000 Belgian mortgage offers, real covariates, simulated bids and
  outcomes from known curves, bias strength varied.
- Assumes unconfoundedness. No instrument. Bias runs through observed
  covariates. Scored by curve error, squared gap to the optimal bid, and Brier
  score. Hidden confounding is listed as a limitation.
- For us: the template for C4, and the comparator reviewers will name. We
  differ on unobserved confounding, rep structure, an instrument, and regret
  in revenue terms. Their finding that Brier score cannot rank pricing models
  supports our evaluation choice.

**Miao, Qi, Shi, Lin (2023, revised 2026).** "Personalized Pricing with
Invalid Instrumental Variables: Identification, Estimation, and Policy
Learning." arXiv 2302.12670. [S]
- Continuous pricing with instruments that may violate exclusion; adversarial
  min-max estimator; revenue regret bound; US online auto lender data.
- Handles a doubtful instrument by estimation, not by abstaining. No leniency
  instrument, no few-cluster analysis.
- For us: the strongest theory neighbour for C3. Must be a baseline or be
  argued out explicitly.

**Gupta and Kamble (2026).** "Causal Multi-Task Demand Learning." arXiv
2602.09969, listed as accepted at NeurIPS 2026. [S]
- Retail linear demand across many products with few price points; no
  instruments.
- Appendix A: pooled estimation converges to a positive price coefficient when
  managers price near the revenue-maximizing level, although the true slope is
  negative.
- For us: prior art for "the pricing behaviour determines the sign of the
  bias". C1 must cite it and go further (two motives, constraint analysis).
- Correction: the design doc had this paper's title and author order wrong.

**Biggs, Gao, Sun (2021, revised 2023).** "Loss Functions for Discrete
Contextual Pricing with Observational Data." arXiv 2111.09933. [S]
- Assumes unconfoundedness and a known logging policy. Not a threat; cite as
  the observational-pricing baseline family.

**Other close work**
- Bian, Wang, Qi (2024). "A Tale of Two Cities: Pessimism and Opportunism in
  Offline Dynamic Pricing." arXiv 2411.08126. [A] Uses monotone demand to
  bound revenue at unobserved prices, with worst-case policies. Partial
  identification from coverage gaps, not confounding.
- Kolesar, Montiel Olea, Roth (2025). "Evaluating Counterfactual Policies
  Using Instruments." arXiv 2512.24096. [A] Sharp bounds on policy effects
  with leniency-style instruments. Likely the right tool for our bounds. Read
  in full.
- Kadiyala, Phillips, Simsek, van Ryzin (2023). "Predicting transaction
  outcomes under customized pricing with discretion: A structural estimation
  approach." Production and Operations Management 32(6), 1654 to 1673. [A]
  Models the agent's side of the negotiation. Instrument not checked.
- Dobbie and Liberman, with co-authors to confirm. "Measuring Bias in Consumer
  Lending." Review of Economic Studies 88(6). [A] Leave-out examiner leniency
  in lending. Prior art for the instrument outside pricing.
- Phillips (2010). "Customized Pricing." Columbia CPRM working paper 2010-1.
  [A] The standard framing of bid-response with endogenous price.

## 3. Methods map

### Leniency instruments
- Kling (2006). "Incarceration Length, Employment, and Earnings." AER 96(3),
  863 to 876. [A] The template; needs random assignment.
- Dobbie, Goldin, Yang (2018). AER 108(2), 201 to 240. [A] The standard
  leave-one-out recipe and balance tests.
- Frandsen, Lefgren, Leslie (2023). "Judging Judge Fixed Effects." AER 113(1),
  253 to 277. [A] A joint test of exclusion and monotonicity. A failed test
  can be an abstention trigger. Power with 8 to 50 reps is doubtful.
- Chyn, Frandsen, Leslie (2025). "Examiner and Judge Designs in Economics: A
  Practitioner's Guide." Journal of Economic Literature 63(2), 401 to 439. [A]
  Read in full before the methods section.
- Chan, Gentzkow, Yu (2022). "Selection with Variation in Diagnostic Skill."
  QJE 137(2), 729 to 783. [A] Leniency designs break when agents differ in
  skill, not only in threshold. The sharpest critique of our instrument: a
  skilled rep may discount less and win more.

### Control functions with a binary outcome
- Petrin and Train (2010), used by both closest empirical papers. [T, cited there]
- Rivers and Vuong (1988), J. Econometrics 39(3). [M]
- Blundell and Powell (2004), Rev. Econ. Studies 71(3), 655 to 679. [A]
- Imbens and Newey (2009), Econometrica 77(5), 1481 to 1512. [A]
- Wooldridge (2015), J. Human Resources 50(2), 420 to 445. [A]

Validity conditions we must meet: a first stage that is continuous and
strictly monotone in the unobservable; independence of the structural error
and the instrument given the control residual; common support; and standard
errors that bootstrap both stages together, clustered by rep.

### Weak instruments and few clusters
- Lee, McCrary, Moreira, Porter (2022). AER 112(10), 3260 to 3290. [A] The
  usual t-test is not valid at first-stage F near 10; gives the tF adjustment.
- Young (2022). European Economic Review 147. [A] First-stage F pre-tests are
  largely uninformative with leveraged, clustered data.
- Stock and Yogo (2005); Angrist, Imbens, Krueger (1999); Cameron, Gelbach,
  Miller (2008); Canay, Santos, Shaikh (2021). [M]

### Bounds and sensitivity
- Manski (1990) [M]; Manski and Pepper (2000), Econometrica 68(4) [A];
  Balke and Pearl (1997) [M]; Conley, Hansen, Rossi (2012), Rev. Econ. Stat.
  94(1), 260 to 272 [A]; Kallus and Zhou (2018 NeurIPS; 2021 Management
  Science 67(5)) [A]; Kallus, Mao, Zhou (2019 AISTATS) [A].
- Usable directly for a max-min pricing rule: Kallus and Zhou, Manski and
  Pepper. Conley et al. is a sensitivity knob for exclusion in linear models;
  the nonlinear version would be ours to derive.

### Deferral and abstention under hidden confounding
- Madras, Pitassi, Zemel (2018 NeurIPS) [A]; Mozannar and Sontag (2020 ICML) [A].
- Ghoummaid and Shalit (2024 NeurIPS). "When to Act and When to Ask: Policy
  Learning With Deferral Under Hidden Confounding." [T, abstract] Defers to a
  human expert using costs robust to bounded hidden confounding. The closest
  precedent to our abstention.
- Li et al. (2026 AAAI). "A Causal Target for Learning to Defer Under Hidden
  Confounding." [A]
- Gao and Yin, "Confounding-Robust Deferral Policy Learning," arXiv
  2310.08824. [M for authors and venue]
- Ek and Zachariah (2025), arXiv 2505.08378. [A]

All of these size the uncertainty with a user-chosen sensitivity parameter
and a binary action. None uses an instrument, and none prices.

### Shape constraints and endogeneity
- Chetverikov and Wilhelm (2017). Econometrica 85(4), 1303 to 1320. [A]
  Monotonicity stabilizes nonparametric IV. It does not correct bias without
  an instrument.
- Blundell, Horowitz, Parey (2012). Quantitative Economics 3(1), 29 to 51. [A]
- No paper found analyses whether a monotone constraint corrects endogeneity
  bias in a tree model. That claim needs our own proof and simulation.

### Decision-focused evaluation
- Elmachtoub and Grigas (2022). Management Science 68(1), 9 to 26. [A]
- Fernandez-Loria and Provost (2022). INFORMS J. Data Science 1(1), 4 to 16. [A]
- Bertsimas and Kallus (2020). Management Science 66(3). [M]

### ML instrument methods
DeepIV (Hartford et al. 2017), Kernel IV (Singh et al. 2019), DFIV (Xu et al.
2021), DeepGMM (Bennett et al. 2019), and the GRF instrumental forest (Athey,
Tibshirani, Wager 2019, Annals of Statistics 47(2)). [A] None is built for a
binary outcome. Only `grf` is actively maintained. With one scalar instrument
the deep methods add little over a control function.

## 4. Closest JAIR papers (for the submission form)

1. Ge, Cai, Wan, Xu, Song (2026). "A Review of Causal Decision Making." JAIR
   85. DOI 10.1613/jair.1.21001. [A] A survey; we contribute a method and an
   identification analysis.
2. Mandi, Kotary, Berden, Mulamba, Bucarey, Guns, Fioretto (2024).
   "Decision-Focused Learning: Foundations, State of the Art, Benchmark and
   Future Opportunities." JAIR 80, 1623 to 1701. DOI 10.1613/jair.1.15320. [A]
   Decision-focused learning assumes the logged data sample the decision
   environment faithfully. Ours do not.
3. Kube, Das, Fowler (2023). "Fair and Efficient Allocation of Scarce
   Resources Based on Predicted Outcomes." JAIR 76, 1219 to 1245. DOI
   10.1613/jair.1.12847. [A] Counterfactual prediction feeding a decision
   under selection on observables. We assume hidden confounding.

JAIR has published nothing found on instruments, off-policy learning under
confounding, learning to defer, or revenue management. That makes novelty
safe and venue fit the question a reviewer may ask. Frame the paper as causal
decision making and decision-focused learning, which JAIR does publish. All
three abstracts must be read in full before the 150-word answer is written.

## 5. Datasets

No public dataset found has real quoted prices, lost quotes and a salesperson
identifier together.

| Dataset | Has | Missing | Access |
|---|---|---|---|
| Columbia CPRM / Nomis online auto lending (CPRM-12-001, the "e-Car" data) | Real offered rates, competitor rate, accept or reject, about 208,000 applications (sources disagree: 208,085, 208,805, and a 50,000-row version) | Any agent identifier. It is a direct lender, and Phillips et al. found no endogeneity in it | Unverified. The Columbia and Nomis pages could not be loaded. Check in a browser; count rows before citing |
| Kaggle Homesite Quote Conversion | Real quotes with conversions, about 260,000 rows | A clean price, an agent, readable features. Competition rules may bar research use | Kaggle login |
| Maven CRM Sales Opportunities | Sales agent column, public domain | Synthetic, small, no price variation | Open |

Consequence: the real-covariate check has to simulate rep identities and
leniency on top of real covariates. It tests robustness to realistic
covariate structure, not the instrument itself. Say so in the paper.

## 6. What changes in the design

1. **C3 is reframed.** The claim is not "IV for pricing" or "defer under
   confounding", both taken. It is: use instrument diagnostics (first-stage
   strength with few reps, the Frandsen et al. test, exclusion sensitivity) to
   decide when a discount recommendation is identified, and fall back to the
   guardrail when it is not.
2. **C2 is narrowed** to the sign-flip regime, with Fernandez-Loria and
   Provost as the counterpoint we must answer.
3. **The instrument's own weak points become dials.** Rep skill that affects
   wins directly (Chan, Gentzkow, Yu), non-random assignment of reps to deals,
   and the mechanical bias in leave-one-out means with few reps.
4. **Point mass at zero discount.** The generator clips discounts at zero, and
   SMB deals start near 4%, so a real share of deals has no discount. A
   control function needs a continuous first stage. Decide the handling
   (a Tobit-style first stage, or modelling discounted deals only) before code.
5. **Baselines revised.** Naive and monotone gradient boosting; linear IV with
   leave-one-out leniency and weak-instrument-robust intervals; Rivers-Vuong
   and Blundell-Powell control functions; Kallus-Zhou robust policy, with
   Ghoummaid-Shalit as the deferral comparator; GRF instrumental forest; Miao
   et al. if code is available. DeepIV and DFIV dropped unless porting is cheap.
6. **Direction evidence.** Phillips et al. support the rescue direction in
   auto lending. Larkin (2014, Journal of Labor Economics 32(2)) and Oyer
   (1998, QJE 113(1)) show discounting driven by incentive timing. Nothing
   verified shows the whale direction, so the paper presents it as a
   possibility the method must survive, not as an observed fact.

## 7. Reading list before any code (week 2)

In full, by a human: Karlinsky-Shichor and Netzer (2024); Miao et al.;
Bockel-Rickermann et al.; Kolesar, Montiel Olea, Roth; Chyn, Frandsen, Leslie;
Ghoummaid and Shalit; Chan, Gentzkow, Yu; Ge et al. (JAIR).

Then: re-run the JAIR comparator search on Google Scholar, confirm every [M]
citation, and check whether the CPRM data can still be downloaded.
