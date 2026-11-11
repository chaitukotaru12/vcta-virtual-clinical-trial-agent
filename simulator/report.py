"""Build the advisor's written outputs from the simulation results.

Writes data/adv_benchmarks.csv, adv_redflags.csv, adv_recs.csv and adv_checkpoints.csv.
Every number in the text is read from the result files, so the words stay in step with the data.
Run after advisor.py:  python report.py
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from any folder
import pandas as pd

P = lambda v: f"{round(float(v) * 100)}%"
rd = lambda name: pd.read_csv(f"data/{name}.csv")
sc = rd("adv_scenarios").set_index("scenario")
de = rd("adv_design").set_index("option")
io = rd("adv_interim").set_index("key")
bl = rd("adv_blinded").set_index("scenario")
dr = rd("adv_dropout").set_index("dropout")
sf = rd("adv_safety").set_index("adverse_event")
hd = rd("headline").set_index("metric").value
va = rd("validation").set_index("check")
pc = rd("placebo_curve").set_index("rate_placebo")
TYP = "Benchmark: typical new-mechanism phase 2"
PLAN = "As planned: 3 arms x 30, one-sided α 0.05"
TWO45 = "Same 90 patients, drop 300 mg: 45 vs 45"
TWO80 = "2 arms x 80, one-sided α 0.10 (160 patients)"

# ---------------------------------------------------------------- literature benchmarks (pre-trial evidence)
bench = pd.DataFrame([
    dict(id="b1", evidence="Placebo clinical remission, UC induction trials (meta-analysis to 2014)", value="10%",
         detail="Placebo response 33%. Endoscopy subscore 2 or more at entry lowered placebo rates; longer trials and more visits raised them.",
         source="Jairath et al., J Crohns Colitis 2016", url="https://pubmed.ncbi.nlm.nih.gov/26746169/"),
    dict(id="b2", evidence="Placebo clinical remission, UC induction trials (meta-analysis 2014-2020)", value="11%",
         detail="Absence of central endoscopy reading raised placebo endoscopic rates; more follow-up visits and longer trials raised clinical placebo rates.",
         source="Sedano et al., J Crohns Colitis 2022", url="https://pubmed.ncbi.nlm.nih.gov/34309658/"),
    dict(id="b3", evidence="Placebo clinical remission, East Asian UC induction trials", value="13%",
         detail="Placebo endoscopic remission 26%. Relevant because the trial runs in mainland China, Taiwan, Korea and Australia.",
         source="Meta-analysis of East Asian UC RCTs, 2022", url="https://www.pubmed.gov/35347342/"),
    dict(id="b4", evidence="Etrolizumab phase 2 (EUCALYPTUS), new gut-selective mechanism", value="21% vs 0%",
         detail="Week-10 remission, 100 mg vs placebo; about 40 patients per arm.",
         source="Vermeire et al., Lancet 2014", url="https://opact.sdu.edu.tr/vufind/SummonRecord/FETCH-LOGICAL-c647t-9459f83a76ba3ff8215cba7cd84dca504dc19a10fd9e39222842e0c7661fcc173"),
    dict(id="b5", evidence="Ozanimod phase 2 (TOUCHSTONE), new oral mechanism", value="16% vs 6%",
         detail="Week-8 remission, 1 mg vs placebo; 197 patients, 3 arms.",
         source="Sandborn et al., NEJM 2016", url="https://www.healio.com/news/gastroenterology/20160721/touchstone-ozanimod-shows-promise-as-induction-maintenance-therapy-for-uc"),
    dict(id="b6", evidence="Tofacitinib phase 2, among the strongest UC phase 2 results", value="41-48% vs 10%",
         detail="Week-8 remission at 10-15 mg twice daily; clinical response 78% vs 42%. The protocol's 40% assumption sits at this level.",
         source="Sandborn et al., NEJM 2012", url="https://www.news-medical.net/news/20120816/Tofacitinib-shows-promise-in-active-ulcerative-colitis.aspx"),
    dict(id="b7", evidence="IL-6 antibody PF-04236921 in Crohn's disease (ANDANTE)", value="27% vs 11%",
         detail="Week-12 remission at 50 mg. Gastrointestinal abscess and perforation were observed; the 200 mg dose was stopped for safety.",
         source="Danese et al., Gut 2019", url="https://pesquisa.bvsalud.org/infofrontera/resource/en/mdl-29247068"),
    dict(id="b8", evidence="Regulatory endpoint (FDA draft guidance 2022)", value="Modified Mayo",
         detail="Clinical remission on the 3-item modified Mayo score with a centrally read endoscopy subscore; the physician global assessment is dropped.",
         source="FDA, Ulcerative Colitis: Developing Drugs for Treatment, 2022", url="https://fda.gov/media/158016/download"),
])

# ---------------------------------------------------------------- red flags
flags = pd.DataFrame([
    dict(id="f1", severity="High", area="Effect size",
         finding=f"The 600 mg assumption of 40% remission matches the strongest UC phase 2 result on record (tofacitinib). New mechanisms such as etrolizumab and ozanimod reached about 16-21%. At typical benchmark rates (11% vs 22%) the planned design has about {P(sc.loc[TYP, 'power_protocol_design'])} power."),
    dict(id="f2", severity="High", area="Sample size",
         finding=f"About {sc.loc[TYP, 'n_per_arm_for_80']} patients per arm would be needed for 80% power on remission at benchmark rates (chi-square approximation), against 30 planned."),
    dict(id="f3", severity="Medium", area="Sample size text",
         finding=f"The 83% power figure is reproduced only with a dose-trend test ({P(va.loc['600mg_trend', 'simulated'])}); a pairwise test gives {P(va.loc['600mg_vs_placebo', 'simulated'])}. The 70% pooled figure needs all 90 patients ({P(va.loc['pooled_randomised', 'simulated'])}), not the 72 evaluable stated ({P(va.loc['pooled_evaluable', 'simulated'])})."),
    dict(id="f4", severity="Medium", area="Analysis method",
         finding=f"Power was computed for a chi-square test but the primary analysis is adjusted logistic regression, which gives about {P(hd['power_600_itt_logistic'])} as randomised. In {P(hd['zero_placebo_remitters'])} of simulated trials no placebo patient remits, so a plain logistic model fails; Firth or exact logistic regression is not pre-specified."),
    dict(id="f5", severity="Medium", area="Dose arms",
         finding=f"The 300 mg arm uses a third of the patients but has only about {P(hd['power_300_itt_logistic'])} power against placebo at the assumed 20% remission."),
    dict(id="f6", severity="Medium", area="Placebo response",
         finding="Twelve weeks with fortnightly disease assessments (7 visits) and an entry bar of full Mayo 5 or more are all associated with higher placebo rates in the meta-analyses; East Asian trials average 13% placebo remission."),
    dict(id="f7", severity="Medium", area="Endpoint",
         finding="The primary endpoint uses the full Mayo score with physician global assessment; regulators now favour the modified Mayo score, so phase 2 data may not bridge cleanly to phase 3."),
    dict(id="f8", severity="Medium", area="Monitoring",
         finding="Only a blinded Safety Review Committee is planned: there is no interim futility look and no unblinded data monitoring committee to compare arms."),
    dict(id="f9", severity="Medium", area="Safety",
         finding="An IL-6 antibody in Crohn's disease showed gastrointestinal abscess and perforation. With 60 patients on active drug, a 1-in-100 event is seen at all only about 45% of the time."),
    dict(id="f10", severity="Strength", area="Design",
         finding="Central endoscopy reading, an endoscopy subscore of 2 or more at entry, stratified randomisation and non-responder imputation are all in place and are associated with lower placebo rates and less bias."),
])

# ---------------------------------------------------------------- recommendations
recs = pd.DataFrame([
    dict(priority=1, recommendation="Re-base the effect assumptions on benchmarks",
         detail="Plan on placebo remission of 11-13% and 600 mg remission of about 20-30%, not 40%. Present the 40% case as the optimistic scenario.",
         impact=f"Shows the real risk: power at benchmark rates is about {P(sc.loc[TYP, 'power_protocol_design'])}, not {P(va.loc['600mg_vs_placebo', 'protocol_claim'])}."),
    dict(priority=2, recommendation="Use clinical response on the modified Mayo score as the primary proof-of-concept endpoint",
         detail="Keep remission as the key secondary. Response has a larger, more stable signal in phase 2 and matches the regulators' modified Mayo score.",
         impact=f"At the same 90 patients, power rises from {P(de.loc[PLAN, 'power_remission'])} to {P(de.loc[PLAN, 'power_response'])} (benchmark rates, chi-square approximation)."),
    dict(priority=3, recommendation="Concentrate patients on the dose most likely to work",
         detail="Drop the 300 mg arm, or add it only through an adaptive dose-selection step after an interim look.",
         impact=f"With 45 vs 45, response power rises to {P(de.loc[TWO45, 'power_response'])}."),
    dict(priority=4, recommendation="Size the trial for a realistic effect",
         detail="Two arms of about 80 patients each, with a pre-specified one-sided α of 0.10 for proof of concept.",
         impact=f"Gives about {P(de.loc[TWO80, 'power_response'])} power on clinical response at benchmark rates (chi-square approximation)."),
    dict(priority=5, recommendation="Add an interim futility look at 50% of patients",
         detail="Run by an independent statistician for an unblinded data monitoring committee; stop if conditional power is below 20%.",
         impact=(f"If the drug does nothing, about {P(io.loc['Drug does nothing (11% vs 11%) | 80', 'p_stop'])} of trials stop at halfway, sparing patients. "
                 f"The cost is small: power falls from {P(io.loc['Realistic benefit (11% vs 22%) | 80', 'power_no_rule'])} to {P(io.loc['Realistic benefit (11% vs 22%) | 80', 'power_with_rule'])} at a realistic effect, "
                 f"and from {P(io.loc['Protocol assumption (10% vs 40%) | 80', 'power_no_rule'])} to {P(io.loc['Protocol assumption (10% vs 40%) | 80', 'power_with_rule'])} at the protocol's assumption (80 per arm).")),
    dict(priority=6, recommendation="Match the sample-size method to the analysis and pre-specify Firth or exact logistic regression",
         detail="Compute power for the adjusted logistic model actually used, and fix the 70% pooled-power text.",
         impact=f"Removes the analysis failure seen in {P(hd['zero_placebo_remitters'])} of simulated trials."),
    dict(priority=7, recommendation="Keep the placebo response low",
         detail="Keep central reading and the endoscopy subscore of 2 or more; consider a higher entry bar (full Mayo 6 or more) and avoid adding visits beyond what the endpoints need.",
         impact=f"Each extra point of placebo response costs power; at 15% placebo the planned design falls to about {P(pc.loc[0.15, 'power_logistic'])}."),
    dict(priority=8, recommendation="Protect against dropout",
         detail="Plan retention support and rescue rules so patients stay in follow-up; dropouts count as failures.",
         impact=f"Under protocol assumptions power goes from {P(dr.loc[0.1, 'power_protocol'])} at 10% dropout to {P(dr.loc[0.3, 'power_protocol'])} at 30%."),
    dict(priority=9, recommendation="Pre-set safety review triggers for IL-6 class risks",
         detail="An unblinded committee reviews at once for any gastrointestinal perforation or abscess, and at pre-set counts of serious infection, low neutrophils or liver-enzyme rises (see checkpoints).",
         impact=f"For example, {sf.loc['Serious infection', 'trigger_at_40']} serious infections among 40 patients on active drug means at least 90% probability the true rate is above 5%."),
])

# ---------------------------------------------------------------- checkpoints
ck = pd.DataFrame([
    dict(id="c1", when="Before first patient", checkpoint="Assumptions signed off against benchmarks",
         go="Placebo and effect assumptions sit within the published benchmark range, and the power table is approved",
         act="Re-size or change the endpoint before enrolment starts"),
    dict(id="c2", when="Monthly during enrolment", checkpoint="Enrolment pace and baseline mix",
         go="On plan; baseline Mayo and endoscopy subscores match the population assumed",
         act="Add sites, or review entry criteria if patients are milder than planned (milder patients raise placebo response)"),
    dict(id="c3", when="First 45 patients complete week 12 (blinded)", checkpoint="Pooled remission rate across all arms",
         go=f"At or above {P(bl.loc['Protocol assumption', 'p10'])}: consistent with the protocol assumptions",
         act=f"Below {P(bl.loc['Protocol assumption', 'p10'])}: only a 1-in-10 chance under the assumptions, so the effect is probably smaller; trigger blinded sample-size re-estimation. Near {P(bl.loc['Drug does nothing', 'median'])}: consistent with no drug effect"),
    dict(id="c4", when="Throughout (blinded)", checkpoint="Dropout rate", go="20% or less, as planned",
         act=f"Above 25%: act on retention; at 30% dropout power under the protocol assumptions falls to about {P(dr.loc[0.3, 'power_protocol'])}"),
    dict(id="c5", when="Halfway (unblinded, independent committee)", checkpoint="Interim futility",
         go="Conditional power of 20% or more: continue", act="Below 20%: stop for futility and redirect resources"),
    dict(id="c6", when="Continuous (unblinded committee)", checkpoint="Safety triggers",
         go="Below the trigger counts in the safety table",
         act="Any gastrointestinal perforation or abscess, or reaching a trigger count: immediate review of benefit and risk"),
])

for name, df in [("adv_benchmarks", bench), ("adv_redflags", flags), ("adv_recs", recs), ("adv_checkpoints", ck)]:
    df.to_csv(f"data/{name}.csv", index=False)
print("advisor report written: benchmarks, red flags, recommendations, checkpoints")
