"""VCTA design advisor: benchmark-calibrated power, design options, interim futility,
blinded in-trial checkpoints and safety review triggers.

Uses only the protocol plus PRE-TRIAL literature benchmarks (no results of the TJ301 trial itself).
Run from the vcta folder:  python advisor.py   -> writes data/adv_*.csv
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from any folder

import numpy as np
import pandas as pd
from scipy import stats
from engine import Scenario, run, analytic_power

S = 3000
ARMS = ["Placebo", "TJ301 300 mg", "TJ301 600 mg"]


def sc(name, pbo, d300, d600, n=30, drop=0.20, alpha=0.05):
    return Scenario(name, {"Placebo": pbo, "TJ301 300 mg": d300, "TJ301 600 mg": d600},
                    n_per_arm=n, dropout=drop, alpha=alpha)


def n_for_power(p1, p0, alpha=0.05, drop=0.20, target=0.8):
    """Smallest randomised n per arm (two-arm comparison, dropouts = failures) for target power,
    normal approximation to the protocol's chi-square test."""
    for n in range(10, 1001):
        if analytic_power(p1 * (1 - drop), p0 * (1 - drop), n, n, alpha) >= target:
            return n
    return None


# ---------------------------------------------------------------- 1. assumption scenarios
scen = [
    # label, kind, placebo, 300, 600
    ("Protocol assumption", "Protocol", 0.10, 0.20, 0.40),
    ("Benchmark: typical placebo, strong drug", "Benchmark", 0.11, 0.18, 0.30),
    ("Benchmark: typical new-mechanism phase 2", "Benchmark", 0.11, 0.15, 0.22),
    ("Benchmark: East Asian placebo, typical drug", "Benchmark", 0.13, 0.16, 0.22),
    ("Pessimistic: weak drug", "Stress test", 0.13, 0.13, 0.18),
]
rows = []
for label, kind, p0, p3, p6 in scen:
    r = run(sc(label, p0, p3, p6), S=S, seed=11)
    rows.append(dict(scenario=label, kind=kind, placebo=p0, dose300=p3, dose600=p6,
                     power_protocol_design=round(float(r["power_600_itt_logistic"]), 3),
                     power_alpha20=round(float(run(sc(label, p0, p3, p6, alpha=0.20), S=S, seed=11)["power_600_itt_logistic"]), 3),
                     n_per_arm_for_80=n_for_power(p6, p0)))
    print(rows[-1])
scen_df = pd.DataFrame(rows)

# ---------------------------------------------------------------- 2. endpoint alternative: clinical response
# Benchmarks: pooled placebo response in UC induction trials ~33%; assume +20 points on 600 mg (typical phase 2 signal).
resp_rows = []
for n in [30, 45, 60, 80, 100]:
    r = run(sc(f"response n={n}", 0.33, 0.43, 0.53, n=n), S=S, seed=12, with_model=True)
    resp_rows.append(dict(n_per_arm=n, endpoint="Clinical response (33% vs 53%)", power=round(float(r["power_600_itt_logistic"]), 3)))
for n in [30, 45, 60, 80, 100]:
    r = run(sc(f"remission n={n}", 0.11, 0.15, 0.22, n=n), S=S, seed=12, with_model=True)
    resp_rows.append(dict(n_per_arm=n, endpoint="Remission (11% vs 22%)", power=round(float(r["power_600_itt_logistic"]), 3)))
for n in [30, 45, 60, 80, 100]:
    r = run(sc(f"protocol n={n}", 0.10, 0.20, 0.40, n=n), S=S, seed=12, with_model=True)
    resp_rows.append(dict(n_per_arm=n, endpoint="Remission (protocol 10% vs 40%)", power=round(float(r["power_600_itt_logistic"]), 3)))
endpoint_df = pd.DataFrame(resp_rows)
print(endpoint_df)

# ---------------------------------------------------------------- 3. design options at a realistic benchmark (11% vs 22%)
p0, p6 = 0.11, 0.22
def two_arm_power(n_act, n_pbo, alpha=0.05, drop=0.20, pa=p6, pp=p0):
    return analytic_power(pa * (1 - drop), pp * (1 - drop), n_act, n_pbo, alpha)
opts = [
    ("As planned: 3 arms x 30, one-sided α 0.05", 30, 30, 0.05, 90),
    ("As planned, one-sided α 0.20 (protocol's exploratory level)", 30, 30, 0.20, 90),
    ("Same 90 patients, drop 300 mg: 45 vs 45", 45, 45, 0.05, 90),
    ("Same 90 patients, 2 arms 2:1 (60 vs 30)", 60, 30, 0.05, 90),
    ("3 arms x 60 (180 patients)", 60, 60, 0.05, 180),
    ("3 arms x 80 (240 patients)", 80, 80, 0.05, 240),
    ("2 arms x 80, one-sided α 0.10 (160 patients)", 80, 80, 0.10, 160),
]
opt_rows = [dict(option=o, total_patients=tot, n_active=a, n_placebo=b, alpha_one_sided=al,
                 power_remission=round(float(two_arm_power(a, b, al)), 3),
                 power_response=round(float(two_arm_power(a, b, al, pa=0.53, pp=0.33)), 3))
            for o, a, b, al, tot in opts]
design_df = pd.DataFrame(opt_rows)
print(design_df)

# ---------------------------------------------------------------- 4. interim futility at 50% information (conditional power)
def interim_oc(pa, pp, n_final=80, frac=0.5, cp_cut=0.20, alpha=0.05, drop=0.20, sims=20000, seed=3):
    """Two-arm comparison (600 mg vs placebo). At the interim, compute conditional power under the
    current trend; stop for futility if CP < cp_cut. Returns P(stop), power with and without the rule."""
    rng = np.random.default_rng(seed)
    n1 = int(round(n_final * frac)); n2 = n_final - n1
    ea, ep = pa * (1 - drop), pp * (1 - drop)
    xa1 = rng.binomial(n1, ea, sims); xp1 = rng.binomial(n1, ep, sims)
    xa2 = rng.binomial(n2, ea, sims); xp2 = rng.binomial(n2, ep, sims)
    za = stats.norm.ppf(1 - alpha)
    def z(xa, xp, n):
        pbar = (xa + xp) / (2 * n); se = np.sqrt(np.maximum(pbar * (1 - pbar) * 2 / n, 1e-12))
        return (xa / n - xp / n) / se
    z1 = z(xa1, xp1, n1)
    t = frac
    # conditional power under the current trend (B-value method)
    theta = z1 / np.sqrt(t)
    cp = 1 - stats.norm.cdf((za - z1 * np.sqrt(t) - theta * (1 - t)) / np.sqrt(1 - t))
    stop = cp < cp_cut
    zf = z(xa1 + xa2, xp1 + xp2, n_final)
    win = zf > za
    return dict(p_stop=round(float(stop.mean()), 3), power_no_rule=round(float(win.mean()), 3),
                power_with_rule=round(float((win & ~stop).mean()), 3))

oc_rows = []
for label, pa, pp in [("Drug does nothing (11% vs 11%)", 0.11, 0.11),
                      ("Realistic benefit (11% vs 22%)", 0.22, 0.11),
                      ("Protocol assumption (10% vs 40%)", 0.40, 0.10)]:
    for n_final in [30, 80]:
        r = interim_oc(pa, pp, n_final=n_final)
        oc_rows.append(dict(truth=label, n_per_arm=n_final, **r))
oc_df = pd.DataFrame(oc_rows)
oc_df["key"] = oc_df.truth + " | " + oc_df.n_per_arm.astype(str)
print(oc_df)

# ---------------------------------------------------------------- 5. blinded checkpoints (no unblinding needed)
# Pooled remission across all arms among the first 45 completers, and observed dropout.
def pooled_band(rates, n_completers=45, drop_rate=0.20, sims=20000, seed=5):
    rng = np.random.default_rng(seed)
    pooled = np.mean(rates)
    x = rng.binomial(n_completers, pooled, sims) / n_completers
    return np.quantile(x, [0.1, 0.5, 0.9])
ck = []
for label, rates in [("Protocol assumption", (0.10, 0.20, 0.40)),
                     ("Realistic benchmark", (0.11, 0.15, 0.22)),
                     ("Drug does nothing", (0.11, 0.11, 0.11))]:
    lo, med, hi = pooled_band(rates)
    ck.append(dict(scenario=label, expected_pooled=round(float(np.mean(rates)), 3),
                   p10=round(float(lo), 3), median=round(float(med), 3), p90=round(float(hi), 3)))
ck_df = pd.DataFrame(ck)
print(ck_df)

# dropout checkpoint: power of the planned design at the protocol assumption by observed dropout
drop_rows = []
for d in [0.10, 0.20, 0.30, 0.40]:
    r = run(sc(f"drop {d}", 0.10, 0.20, 0.40, drop=d), S=S, seed=13)
    r2 = run(sc(f"drop {d} realistic", 0.11, 0.15, 0.22, drop=d), S=S, seed=13)
    drop_rows.append(dict(dropout=d, power_protocol=round(float(r["power_600_itt_logistic"]), 3),
                          power_realistic=round(float(r2["power_600_itt_logistic"]), 3)))
drop_df = pd.DataFrame(drop_rows)
print(drop_df)

# ---------------------------------------------------------------- 6. safety review triggers
# Number of events among N exposed active patients at which there is >=90% probability (Jeffreys prior)
# that the true per-patient rate exceeds a level of concern.
def trigger(n, concern):
    for k in range(0, n + 1):
        if 1 - stats.beta.cdf(concern, k + 0.5, n - k + 0.5) >= 0.9:
            return k
    return None
saf = []
for ev, concern, note in [("Serious infection", 0.05, "IL-6 class risk; protocol AE of special interest"),
                          ("Neutrophil count decreased (clinically significant)", 0.10, "Seen in earlier TJ301 studies"),
                          ("ALT or AST above 3x ULN", 0.10, "IL-6 class liver-enzyme effect"),
                          ("Gastrointestinal perforation or abscess", 0.0, "Signal reported with an IL-6 antibody in Crohn's disease: any single case triggers an immediate unblinded review")]:
    row = dict(adverse_event=ev, concern_rate=concern, rationale=note)
    for n in [20, 40, 60]:
        row[f"trigger_at_{n}"] = 1 if concern == 0 else trigger(n, concern)
    saf.append(row)
saf_df = pd.DataFrame(saf)
print(saf_df)

for name, df in [("adv_scenarios", scen_df), ("adv_endpoints", endpoint_df), ("adv_design", design_df),
                 ("adv_interim", oc_df), ("adv_blinded", ck_df), ("adv_dropout", drop_df), ("adv_safety", saf_df)]:
    df.to_csv(f"data/{name}.csv", index=False)
print("written")
