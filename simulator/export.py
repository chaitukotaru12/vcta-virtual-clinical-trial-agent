import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from any folder
import json, csv
o=json.load(open("data/results.json"))
def w(name, rows):
    with open(f"data/{name}.csv","w",newline="") as f:
        c=csv.DictWriter(f, fieldnames=list(rows[0].keys())); c.writeheader(); c.writerows(rows)
r3=lambda x: round(float(x),3)
v=o["validation"]; h=o["headline"]
w("validation",[
 dict(check="600mg_vs_placebo", label="600 mg vs placebo (10% vs 40%, 24/arm)", protocol_claim=0.83, simulated=r3(v["exact_pairwise_24"]), method="Pairwise chi-square, exact enumeration"),
 dict(check="600mg_trend", label="Dose trend across 3 arms (300 mg at 15%)", protocol_claim=0.83, simulated=r3(v["trend_24"]["0.15"]), method="Cochran-Armitage trend test, simulated"),
 dict(check="pooled_evaluable", label="Pooled active vs placebo (30% vs 10%), 72 evaluable", protocol_claim=0.70, simulated=r3(v["pooled_48v24"]), method="Chi-square, exact enumeration, 48 vs 24"),
 dict(check="pooled_randomised", label="Pooled active vs placebo, all 90 randomised", protocol_claim=0.70, simulated=r3(v["pooled_60v30"]), method="Chi-square, normal approximation, 60 vs 30"),
])
w("headline",[dict(metric=k, value=r3(h[k])) for k in ["power_600_itt_chisq","power_600_itt_logistic","power_300_itt_logistic","power_pooled_itt_logistic","power_600_completers_chisq","zero_placebo_remitters"]]+
  [dict(metric="power_600_itt_logistic_alpha20", value=r3(o["headline_a20"]["power_600_itt_logistic"]))])
def curve(key, xname, xf):
    return [ {xname: xf(x), "power_chisq": r3(x["power_600_itt_chisq"]), "power_logistic": r3(x["power_600_itt_logistic"])} for x in o[key]]
w("effect_curve", curve("effect_curve","rate_600", lambda x: x["rates"]["TJ301 600 mg"]))
w("placebo_curve", curve("placebo_curve","rate_placebo", lambda x: x["rates"]["Placebo"]))
w("dropout_curve", curve("dropout_curve","dropout", lambda x: x["dropout"]))
w("n_curve", [dict(n_per_arm=x["n_per_arm"], endpoint="Remission (protocol assumptions)", power=r3(x["power_600_itt_logistic"])) for x in o["n_curve"]] +
             [dict(n_per_arm=x["n_per_arm"], endpoint="Clinical response (published rates)", power=r3(x["power_600_itt_logistic"])) for x in o["n_curve_response"]])
rr,rp=o["reality_remission"],o["reality_response"]
w("reality",[
 dict(endpoint="Remission — protocol assumption", placebo=0.10, dose300=0.20, dose600=0.40, power600=r3(h["power_600_itt_logistic"]), power600_chisq=r3(h["power_600_itt_chisq"])),
 dict(endpoint="Remission — published result", placebo=0.0, dose300=0.067, dose600=0.207, power600=r3(rr["power_600_itt_logistic"]), power600_chisq=r3(rr["power_600_itt_chisq"])),
 dict(endpoint="Clinical response — published result", placebo=0.345, dose300=0.433, dose600=0.586, power600=r3(rp["power_600_itt_logistic"]), power600_chisq=r3(rp["power_600_itt_chisq"])),
])
w("safety",[dict(true_rate=float(r), p_seen_30=r3(d["30"]), p_seen_60=r3(d["60"])) for r,d in o["safety"].items()])
