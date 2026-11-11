# Validation

## 1. Reproducing the protocol
The engine reproduces the protocol's stated power with three independent methods (exact enumeration, normal approximation, Monte Carlo), and explains both discrepancies (83% = trend test; 70% = all 90 randomised). See `simulator/data/validation.csv`.

## 2. Automated tests (`pytest -q`)

| Test | What it proves |
|---|---|
| `test_exact_and_normal_approximation_agree` | Two independent power calculations agree within 3 points |
| `test_monte_carlo_matches_exact` | The patient-level simulation matches exact power within 2 points |
| `test_trend_test_reproduces_protocol_claim` | The protocol's 83% is reproduced by a trend test |
| `test_type_one_error_is_controlled` | With no drug effect, false-positive rate stays near 5% |
| `test_intercept_calibration_hits_target_rates` | Simulated arms hit the stated remission rates exactly |
| `test_firth_survives_separation` | The analysis model stays finite when no placebo patient remits |
| `test_dropout_reduces_power` | More dropout never increases power |
| `test_safety_trigger_threshold` | Safety-trigger counts match the posterior definition |
| `test_virtual_cohort_is_well_formed` | 1,000 unique participants, valid categories, ages within protocol range |

## 3. Retrospective back-test (kept out of the pre-trial advisor)
The trial completed in 2020 and was published (Zhang et al., JAMA 2023; NCT03235752). Using the published week-12 rates as "truth" in the engine:

| Rates used | Placebo | 300 mg | 600 mg | Simulated power, 600 mg vs placebo |
|---|---|---|---|---|
| Remission, protocol assumption | 10% | 20% | 40% | 75% |
| Remission, published | 0% | 6.7% | 20.7% | 73% (logistic) / 93% (chi-square) |
| Clinical response, published | 34.5% | 43.3% | 58.6% | ~49% |

What this shows: real remission rates were far below the protocol's assumptions on every arm, consistent with the advisor's red flag on the effect assumption; and on clinical response, the endpoint the publication reports as primary, a 30-per-arm design had roughly coin-flip power, consistent with the advisor's recommendation to size for a realistic response effect. One trial is an anecdote, not a validation; see the roadmap for a systematic back-test.

## 4. Not yet validated
- Benchmarks are cross-drug averages; whether they transfer to a new mechanism is a judgement.
- The remission/response model is not calibrated on patient-level data.
- Adverse-event scenarios are illustrative only.
- Results should be independently replicated in standard software (PASS, nQuery, R `pwr`/`gsDesign`) and reviewed by a biostatistician and a gastroenterologist before any real use.
