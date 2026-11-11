"""VCTA virtual cohort + safety scenario engine.

Generates N virtual participants under the protocol's design and efficacy assumptions, then
simulates adverse events (AEs) from the protocol's list of AEs of special interest (s. 8.3) plus
worsening of the underlying disease.

EVERY AE RATE BELOW IS A HYPOTHETICAL SCENARIO INPUT, NOT DATA ABOUT TJ301. Change them to explore
"what if" safety scenarios. Severity, causality, action and outcome categories follow protocol s. 8.2.2.
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from any folder

import json
import numpy as np
import pandas as pd
from engine import Scenario, calibrate_intercepts, ARMS

N_TOTAL = 1000
SEED = 2017
STUDY_DAYS = 105                       # 12-week treatment + follow-up to Day 105
INFUSION_DAYS = [0, 14, 28, 42, 56, 70]

# name, source, risk of >=1 event over the study per arm (Placebo, 300 mg, 600 mg),
# P(severity mild, moderate, severe), P(reasonable causal possibility as judged blind), P(serious)
AE_CATALOGUE = [
    # earlier TJ301 development (protocol s. 8.3)
    ("Infusion-related reaction", "Protocol: earlier TJ301 studies", (0.02, 0.05, 0.06), (0.70, 0.25, 0.05), 0.85, 0.02),
    ("Headache",                  "Protocol: earlier TJ301 studies", (0.06, 0.08, 0.09), (0.75, 0.22, 0.03), 0.35, 0.00),
    ("Nasopharyngitis",           "Protocol: earlier TJ301 studies", (0.08, 0.09, 0.10), (0.80, 0.19, 0.01), 0.20, 0.00),
    ("Myalgia",                   "Protocol: earlier TJ301 studies", (0.02, 0.03, 0.04), (0.75, 0.23, 0.02), 0.40, 0.00),
    ("Diarrhoea",                 "Protocol: earlier TJ301 studies", (0.04, 0.05, 0.05), (0.70, 0.25, 0.05), 0.25, 0.01),
    ("Cough",                     "Protocol: earlier TJ301 studies", (0.03, 0.04, 0.04), (0.85, 0.14, 0.01), 0.15, 0.00),
    ("Neutrophil count decreased","Protocol: earlier TJ301 studies + IL-6 class", (0.01, 0.03, 0.04), (0.60, 0.30, 0.10), 0.80, 0.03),
    # IL-6 inhibitor class effects (protocol s. 8.3)
    ("Thrombocytopenia",          "Protocol: IL-6 class effect", (0.005, 0.010, 0.015), (0.60, 0.30, 0.10), 0.75, 0.05),
    ("ALT increased",             "Protocol: IL-6 class effect", (0.02, 0.05, 0.06), (0.75, 0.20, 0.05), 0.70, 0.01),
    ("Total cholesterol increased","Protocol: IL-6 class effect", (0.02, 0.05, 0.06), (0.90, 0.09, 0.01), 0.70, 0.00),
    ("Serious infection",         "Protocol: IL-6 class effect", (0.005, 0.010, 0.015), (0.00, 0.30, 0.70), 0.50, 1.00),
    ("Gastrointestinal perforation","Protocol: IL-6 class effect", (0.0005, 0.0010, 0.0015), (0.00, 0.00, 1.00), 0.50, 1.00),
    ("AST increased",             "Protocol: IL-6 class effect", (0.02, 0.05, 0.06), (0.80, 0.17, 0.03), 0.70, 0.01),
    # the disease itself (expected; worse on placebo because the drug is assumed to work)
    ("Ulcerative colitis worsening","Underlying disease", (0.12, 0.09, 0.07), (0.40, 0.45, 0.15), 0.05, 0.15),
]
SEVERITIES = ["Mild", "Moderate", "Severe"]
# outcome given severity: Recovered, Recovering, Not recovered, Recovered with sequelae, Worse
OUTCOME_P = {
    "Mild":     (0.88, 0.07, 0.05, 0.00, 0.00),
    "Moderate": (0.75, 0.13, 0.09, 0.01, 0.02),
    "Severe":   (0.55, 0.20, 0.12, 0.06, 0.07),
}
OUTCOMES = ["Recovered", "Recovering", "Not recovered", "Recovered with sequelae", "Worse"]
# action taken with study drug given severity: No change, Interrupted, Withdrawn
ACTION_P = {"Mild": (0.97, 0.03, 0.00), "Moderate": (0.80, 0.14, 0.06), "Severe": (0.35, 0.25, 0.40)}
ACTIONS = ["No change", "Interrupted", "Withdrawn"]


def build(n_total=N_TOTAL, seed=SEED):
    cfg = json.load(open("trial_config.json"))
    rates = {k: v for k, v in cfg["protocol_assumptions"]["remission_rate"].items() if not k.startswith("_")}
    sc = Scenario("cohort", rates, n_per_arm=n_total // 3, dropout=0.20)
    rng = np.random.default_rng(seed)
    N = n_total
    arm = np.resize(np.arange(3), N); rng.shuffle(arm)        # 1:1:1
    w = np.asarray(sc.mayo_weights) / np.sum(sc.mayo_weights)
    mayo = rng.choice(np.asarray(sc.mayo_values), size=N, p=w)
    steroid = rng.random(N) < sc.steroid_prob
    age = np.clip(np.round(rng.normal(40, 13, N)), 18, 70).astype(int)   # ASSUMED; protocol allows 18-70
    female = rng.random(N) < 0.40                                        # ASSUMED share of women

    # ---- adverse events
    events = []
    withdrawn_day = np.full(N, np.inf)
    for name, src, risk, sev_p, rel_p, ser_p in AE_CATALOGUE:
        p = np.asarray(risk)[arm].astype(float)
        if name == "Serious infection":                 # steroids and age raise infection risk
            p = p * np.where(steroid, 1.5, 1.0) * np.where(age >= 60, 1.5, 1.0)
        hit = rng.random(N) < np.clip(p, 0, 1)
        for i in np.where(hit)[0]:
            n_ev = 1 + rng.poisson(0.15)                 # occasional repeat episodes
            for _ in range(n_ev):
                if name == "Infusion-related reaction":
                    day = int(rng.choice(INFUSION_DAYS))
                else:
                    day = int(rng.integers(1, STUDY_DAYS + 1))
                sev = rng.choice(SEVERITIES, p=sev_p)
                serious = bool(rng.random() < ser_p) or (sev == "Severe" and rng.random() < 0.3)
                action = rng.choice(ACTIONS, p=ACTION_P[sev]) if day <= 70 else "No change"
                outcome = rng.choice(OUTCOMES, p=OUTCOME_P[sev])
                dur = int(np.ceil(rng.exponential({"Mild": 5, "Moderate": 10, "Severe": 21}[sev])))
                if action == "Withdrawn":
                    withdrawn_day[i] = min(withdrawn_day[i], day)
                events.append(dict(participant=i, adverse_event=name, source=src, onset_day=day,
                                   severity=sev, serious="Yes" if serious else "No",
                                   related="Reasonable possibility" if rng.random() < rel_p else "No reasonable possibility",
                                   action_taken=action, outcome=outcome, duration_days=dur))
    ev = pd.DataFrame(events)

    # ---- efficacy (remission at week 12) with AE withdrawals feeding into dropout
    b0, mm = calibrate_intercepts(sc)
    p_rem = 1 / (1 + np.exp(-(b0[arm] + sc.beta_mayo * (mayo - mm))))
    remit = rng.random(N) < p_rem
    # other dropout (consent withdrawal, lost to follow-up, lack of efficacy): tuned so total ~20%
    other_drop = rng.random(N) < 0.16
    other_day = rng.choice([14, 28, 42, 56, 70], N)
    ae_drop = np.isfinite(withdrawn_day) & (withdrawn_day < 84)
    drop = ae_drop | other_drop
    drop_reason = np.where(ae_drop, "Adverse event", np.where(other_drop, "Other reason", ""))
    drop_day = np.where(ae_drop, withdrawn_day, np.where(other_drop, other_day, np.nan))
    status = np.where(drop, "Discontinued", np.where(remit, "Remission", "No remission"))

    ids = np.array([f"VP-{k + 1:04d}" for k in range(N)])
    ae_n = np.bincount(ev.participant, minlength=N) if len(ev) else np.zeros(N, int)
    ser = ev[ev.serious == "Yes"].participant.unique() if len(ev) else []
    severe = ev[ev.severity == "Severe"].participant.unique() if len(ev) else []
    df = pd.DataFrame(dict(
        participant=ids, arm=[ARMS[a] for a in arm], age=age, sex=np.where(female, "F", "M"),
        prior_steroids=np.where(steroid, "Yes", "No"), baseline_mayo=mayo,
        remission_probability=np.round(p_rem, 3), ae_count=ae_n,
        any_serious_ae=np.where(np.isin(np.arange(N), ser), "Yes", "No"),
        any_severe_ae=np.where(np.isin(np.arange(N), severe), "Yes", "No"),
        discontinued=np.where(drop, "Yes", "No"), discontinuation_reason=drop_reason,
        discontinuation_day=pd.array(np.where(np.isfinite(drop_day), drop_day, np.nan), dtype="Int64"),
        week12_status=status, itt_remission=(remit & ~drop).astype(int)))
    ev.insert(0, "event_id", [f"AE-{k + 1:04d}" for k in range(len(ev))])
    ev["arm"] = df.arm.values[ev.participant]
    ev["participant"] = ids[ev.participant]
    ev = ev.sort_values(["participant", "onset_day"]).reset_index(drop=True)
    return df, ev


def summaries(df, ev):
    rows = []
    for a in ARMS:
        d = df[df.arm == a]; e = ev[ev.arm == a]
        rows.append(dict(arm=a, n=len(d), mean_age=round(d.age.mean(), 1), female=round((d.sex == "F").mean(), 3),
                         prior_steroids=round((d.prior_steroids == "Yes").mean(), 3),
                         mean_baseline_mayo=round(d.baseline_mayo.mean(), 2),
                         itt_remission=round(d.itt_remission.mean(), 3),
                         any_ae=round((d.ae_count > 0).mean(), 3),
                         any_related_ae=round(d.participant.isin(e[e.related == "Reasonable possibility"].participant).mean(), 3),
                         any_serious_ae=round((d.any_serious_ae == "Yes").mean(), 3),
                         any_severe_ae=round((d.any_severe_ae == "Yes").mean(), 3),
                         discontinued_ae=round((d.discontinuation_reason == "Adverse event").mean(), 3),
                         discontinued_total=round((d.discontinued == "Yes").mean(), 3),
                         ae_events=len(e)))
    arm_s = pd.DataFrame(rows)

    t = []
    n_arm = df.arm.value_counts()
    for name, src, risk, *_ in AE_CATALOGUE:
        e = ev[ev.adverse_event == name]
        r = dict(adverse_event=name, source=src)
        for a, key in zip(ARMS, ["placebo", "dose300", "dose600"]):
            ea = e[e.arm == a]
            r[f"{key}_pct"] = round(ea.participant.nunique() / n_arm[a], 4)
            r[f"{key}_input_risk"] = risk[ARMS.index(a)]
        r["events"] = len(e)
        for s in SEVERITIES: r[s.lower()] = int((e.severity == s).sum())
        r["serious"] = int((e.serious == "Yes").sum())
        r["led_to_withdrawal"] = int((e.action_taken == "Withdrawn").sum())
        for o in OUTCOMES: r["out_" + o.lower().replace(" ", "_")] = int((e.outcome == o).sum())
        t.append(r)
    by_type = pd.DataFrame(t)

    out = ev.groupby(["arm", "outcome"]).size().unstack(fill_value=0).reindex(index=ARMS, columns=OUTCOMES, fill_value=0)
    out = out.reset_index().melt(id_vars="arm", var_name="outcome", value_name="events")
    out["share"] = (out.events / out.groupby("arm").events.transform("sum")).round(4)
    out["key"] = out.arm + "|" + out.outcome
    return arm_s, by_type, out


if __name__ == "__main__":
    df, ev = build()
    arm_s, by_type, out = summaries(df, ev)
    df.to_csv("data/participants.csv", index=False)
    ev.to_csv("data/ae_events.csv", index=False)
    arm_s.to_csv("data/cohort_summary.csv", index=False)
    by_type.to_csv("data/ae_by_type.csv", index=False)
    out.to_csv("data/ae_outcomes.csv", index=False)
    pd.set_option("display.width", 250)
    print(arm_s.T.to_string())
    print(by_type[["adverse_event", "placebo_pct", "dose300_pct", "dose600_pct", "events", "severe", "serious", "led_to_withdrawal"]].to_string())
    print(out.pivot(index="arm", columns="outcome", values="events"))
    print(len(df), len(ev))
