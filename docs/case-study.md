# Case study: stress-testing the TJ301 phase II design in ulcerative colitis

## The trial

| | |
|---|---|
| Drug | TJ301 (olamkicept), a selective inhibitor of the soluble IL-6 receptor/IL-6 complex |
| Indication | Active ulcerative colitis (full Mayo ≥5, rectal bleeding ≥1, endoscopy subscore ≥2) |
| Design | Phase II, randomised 1:1:1, double-blind: placebo, 300 mg, 600 mg IV every 2 weeks for 12 weeks |
| Size | 90 randomised, 72 evaluable expected (20% dropout) |
| Primary endpoint | Clinical and endoscopic remission at week 12 (full Mayo ≤2, no subscore >1, rectal bleeding 0) |
| Analysis | Logistic regression adjusted for prior corticosteroids, PK substudy and baseline Mayo; missing = non-remission |
| Sample-size assumption | Placebo 10%, 600 mg 40% remission; 24 per arm gives 83% power (one-sided α 0.05) |
| Registry | [NCT03235752](https://clinicaltrials.gov/study/NCT03235752), protocol CTJ301UC201 v1.1 (16 May 2017) |

## The question

*If a sponsor had run this design through a simulator before enrolling the first patient, what would it have learned, and what would it have changed?*

## Step 1 — Can the protocol's own numbers be reproduced?

Before trusting any what-if, the engine must reproduce what the protocol claims.

| Claim | Protocol | Engine | Method |
|---|---|---|---|
| 600 mg vs placebo, 24/arm | 83% | 80.5% | Pairwise chi-square, exact enumeration |
| Dose trend across 3 arms (300 mg at 15%) | 83% | 83% | Cochran–Armitage trend test |
| Pooled active vs placebo, 72 evaluable | 70% | 65% | Exact enumeration |
| Pooled active vs placebo, all 90 randomised | 70% | 71% | Normal approximation |

**Finding:** the 83% is only reproduced as a *trend* test, and the 70% only with all 90 patients rather than the 72 evaluable the text describes. Small inconsistencies, but the kind a regulator or DMC statistician would query.

## Step 2 — How fragile is the design under its own assumptions?

- Simulated **as randomised** (30 per arm, 20% dropout counted as failure) with the protocol's **adjusted logistic model**, power is **75%**, not 83%: the sample size was computed for a different test than the one the analysis uses.
- In **8.4%** of simulated trials no placebo patient reaches remission. A plain logistic model has no finite estimate then; Firth or exact logistic regression should be pre-specified.
- The **300 mg** arm has about **18%** power against placebo (at an assumed 20% remission; the protocol states no 300 mg rate).
- If placebo remission is **15%** instead of 10%, power falls to about **56%**; if 600 mg reaches **30%** instead of 40%, to about **47%**.

## Step 3 — What did comparable trials actually achieve?

Benchmarks available before the trial (sources in `simulator/data/adv_benchmarks.csv`):

| Evidence | Result |
|---|---|
| Placebo clinical remission, UC induction trials (Jairath et al. 2016) | 10% (response 33%) |
| Same, 2014–2020 update (Sedano et al. 2022) | 11% |
| Placebo clinical remission, East Asian UC trials | 13% |
| Etrolizumab phase 2 (EUCALYPTUS) | 21% vs 0% |
| Ozanimod phase 2 (TOUCHSTONE) | 16% vs 6% |
| Tofacitinib phase 2 (strongest result) | 41–48% vs 10% |
| IL-6 antibody PF-04236921 in Crohn's (ANDANTE) | 27% vs 11%; GI abscess/perforation signal |
| FDA draft guidance 2022 | Remission on the modified Mayo score, central endoscopy reading |

**Finding:** the 40% remission assumption matches the best UC phase 2 result on record; new mechanisms typically reached 16–21%. At **11% vs 22%**, the planned design has about **18% power**, and roughly **182 patients per arm** would be needed for 80% power on remission.

## Step 4 — Recommendations and their simulated impact

| # | Recommendation | Simulated impact |
|---|---|---|
| 1 | Re-base effect assumptions on benchmarks; present 40% as the optimistic case | Shows the real risk: ~18% power at benchmark rates |
| 2 | Clinical response on the modified Mayo score as primary proof-of-concept endpoint; remission as key secondary | Same 90 patients: 26% → 36% power |
| 3 | Drop the 300 mg arm or select doses adaptively | 45 vs 45: response power 48% |
| 4 | Two arms of ~80, one-sided α 0.10 | ~80% power on clinical response |
| 5 | Interim futility look at 50% (conditional power <20%) with an unblinded DMC | Stops ~75% of trials of an ineffective drug at halfway; power 50% → 45% at a realistic effect |
| 6 | Match the sample-size method to the analysis; pre-specify Firth/exact logistic | Removes the 8% model-failure risk |
| 7 | Keep placebo response low: central reading, endoscopy ≥2, consider a higher entry bar, no unnecessary visits | Each point of placebo response costs power |
| 8 | Protect against dropout | 80% at 10% dropout vs 66% at 30% (protocol assumptions) |
| 9 | Pre-set safety review triggers for IL-6 class risks | e.g. 4 serious infections in 40 patients on drug → ≥90% probability rate >5% |

## Step 5 — Checkpoints to keep the trial achievable

| When | Checkpoint | Act if |
|---|---|---|
| Before first patient | Assumptions signed off against benchmarks | Re-size or change endpoint |
| Monthly during enrolment | Enrolment pace and baseline mix | Milder-than-planned patients raise placebo response |
| First 45 complete week 12 (blinded) | Pooled remission across all arms | Below ~16%: effect probably smaller than assumed → blinded sample-size re-estimation |
| Throughout (blinded) | Dropout | Above 25%: act on retention |
| Halfway (unblinded committee) | Interim futility | Conditional power <20%: stop |
| Continuous | Safety triggers | Any GI perforation/abscess or a trigger count: immediate benefit–risk review |

## Step 6 — Virtual participants

One simulated trial of **1,000 virtual participants** (1:1:1) under the protocol's assumptions, each with a profile, a week-12 outcome and adverse events drawn from the protocol's list of adverse events of special interest (section 8.3) and UC worsening. Severity, seriousness, causality, action taken and outcome follow the protocol's categories. **All adverse-event rates are hypothetical scenario inputs**, used to show what a safety scenario looks like and how rare events (1 in 1,000) can go unseen even at this size.

## What happened in reality (retrospective)

The trial completed in December 2020 and was published in JAMA (2023) with **clinical response** as the primary endpoint. See [`validation.md`](validation.md) for how the engine's view of the design compares with what was observed. This retrospective is deliberately kept out of the pre-trial advisor.

## Takeaway

The design problems were all visible **before** enrolment: an optimistic effect assumption, a mismatch between sample-size method and analysis, a thin dose arm and no futility look. A simulation-first review turns these into concrete, quantified changes, which is the value proposition of VCTA.
