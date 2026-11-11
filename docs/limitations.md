# Limitations and guardrails

## Guardrails
1. Simulated participants are not real patients.
2. Simulated results cannot establish clinical safety or efficacy.
3. Every simulation exposes its assumptions; anything not in the protocol is labelled `ASSUMED`.
4. Models must be validated against appropriate evidence before serious research use.
5. The tool never recommends exposing humans to a drug based on simulated results.
6. Human-subject research still follows ethics, regulatory and clinical-trial requirements.

## Known limitations
- **Effect-size benchmarks are judgement calls.** The "realistic" 600 mg rate (22%) and the clinical-response effect (+20 points) are based on other drugs; a different choice changes downstream results.
- **Simplified disease model.** Remission is modelled directly; individual Mayo subscores are not simulated, so remission and response are not generated from the same virtual patient.
- **Dropout is missing completely at random.** Informative dropout (sicker patients leaving) is not yet modelled.
- **Approximations.** Design options and sample sizes use a normal approximation to the chi-square test; the logistic analysis uses a Wald test, which is conservative under Firth penalisation.
- **Adverse-event rates are hypothetical** and do not represent TJ301 data.
- **Single trial, single disease area.** Generalisation is the subject of the roadmap.
- **Not regulatory-grade software.** No GxP validation; decision support for discussion only.
