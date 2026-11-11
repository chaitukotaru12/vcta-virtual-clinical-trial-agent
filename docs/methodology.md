# Methodology

## Principle
Language models may plan, extract and explain. **Every number is computed by deterministic, tested Python code** (NumPy, SciPy, pandas). Every input not stated in the protocol is labelled `ASSUMED`.

## Design spec (`simulator/trial_config.json`)
The protocol's design as structured data: arms and allocation, enrolment and dropout, stratification factors, population (baseline Mayo distribution), primary endpoint and missing-data rule, assumed effect sizes, analysis model and the protocol's power claims.

## Virtual trials (`engine.py`)
For each simulated trial:
1. **Virtual cohort:** baseline full Mayo (5–12), prior corticosteroids, PK-substudy membership.
2. **Outcomes:** remission probability from a logistic model, `logit p = b0[arm] + β·(Mayo − mean)`. Arm intercepts are **calibrated** (root-finding) so each arm's marginal remission rate equals the stated assumption exactly; β = −0.25 per Mayo point (assumed).
3. **Dropout:** missing completely at random at the stated rate; dropouts count as non-remission (non-responder imputation), as in the protocol.
4. **Analyses:**
   - Pearson chi-square without continuity correction, one-sided (the protocol's sample-size method), vectorised;
   - the protocol's adjusted logistic regression, fitted with **Firth's penalised likelihood** (batched Newton–Raphson in NumPy) so it stays finite under separation; one-sided Wald test.
5. Repeated 3,000–20,000 times with a fixed seed; power = share of trials that reject.

## Claims check (`check_claims.py`)
- Exact power by full enumeration of the two binomial distributions.
- Normal-approximation power.
- Cochran–Armitage trend-test power by simulation.

## Design advisor (`advisor.py`)
- **Benchmark scenarios:** the planned design re-simulated at literature-based rates.
- **Sample size for 80% power:** smallest n per arm, normal approximation, dropouts as failures.
- **Endpoint comparison:** remission vs clinical response (33% vs 53%, pooled placebo response plus a typical phase 2 effect — an assumption).
- **Design options:** alternative arm counts, allocation, sizes and α levels (chi-square approximation).
- **Interim futility:** two-stage simulation; conditional power under the current trend (B-value method) at 50% information, stop if < 20%; reports stopping probability and power with and without the rule.
- **Blinded checkpoint:** distribution (10th/50th/90th percentile) of pooled remission among the first 45 completers under each scenario.
- **Safety triggers:** smallest event count k among n patients on drug such that P(true rate > concern level) ≥ 0.9 under a Jeffreys Beta(k+½, n−k+½) posterior.

## Virtual cohort (`cohort.py`)
1,000 participants, 1:1:1. Profiles (age within the protocol's 18–70, sex, prior steroids, baseline Mayo), week-12 outcome, and adverse events from a catalogue: per-arm risk, severity mix, probability judged drug-related, probability serious. Serious infection risk is raised 1.5× for prior steroids and for age ≥60. Action taken and outcome are drawn by severity using the protocol's categories; stopping drug for an adverse event counts as discontinuation (non-remission). **All rates are hypothetical.**
