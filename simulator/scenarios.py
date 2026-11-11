import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from any folder
import json, numpy as np
from engine import *
from check_claims import exact_power, trend_power
S=3000
base={"Placebo":.10,"TJ301 300 mg":.20,"TJ301 600 mg":.40}
out={}
def R(**kw): 
    r=dict(base); r.update(kw); return r
def go(name, rates, **kw):
    r=run(Scenario(name, rates, **kw), S=S, seed=7)
    return {k:(float(v) if isinstance(v,(np.floating,float)) else v) for k,v in r.items()}

out["validation"]=dict(
  claim_600=0.83, claim_pooled=0.70,
  exact_pairwise_24=exact_power(.4,.1,24,24,.05),
  analytic_pairwise_24=float(analytic_power(.4,.1,24,24,.05)),
  trend_24={m:trend_power(np.array([.1,m,.4]),24,.05) for m in [.1,.15,.2,.25,.3]},
  pooled_48v24=exact_power(.3,.1,48,24,.05),
  pooled_60v30=float(analytic_power(.3,.1,60,30,.05)),
)
out["headline"]=go("Protocol assumptions, as randomised (30/arm, 20% dropout, ITT-NRI)", base)
out["headline_a20"]=go("Same, one-sided alpha 0.20", base, alpha=0.20)
out["effect_curve"]=[go(f"600mg={p}", R(**{"TJ301 600 mg":p})) for p in [.15,.20,.25,.30,.35,.40,.45,.50]]
out["placebo_curve"]=[go(f"pbo={p}", R(Placebo=p)) for p in [.0,.05,.10,.15,.20]]
out["dropout_curve"]=[go(f"drop={d}", base, dropout=d) for d in [0,.1,.2,.3,.4]]
out["n_curve"]=[go(f"n={n}", base, n_per_arm=n) for n in [20,30,40,50,60,80]]
obs_rem={"Placebo":.0,"TJ301 300 mg":.067,"TJ301 600 mg":.207}
obs_resp={"Placebo":.345,"TJ301 300 mg":.433,"TJ301 600 mg":.586}
out["reality_remission"]=go("Published week-12 remission rates as truth", obs_rem, dropout=0.13)
out["reality_response"]=go("Published week-12 clinical response rates as truth", obs_resp, dropout=0.13)
out["n_curve_response"]=[go(f"resp n={n}", obs_resp, n_per_arm=n, dropout=0.13) for n in [30,45,60,80,100]]
# safety: chance of seeing >=1 case of an AE with true per-patient rate r
out["safety"]={str(r):{str(n):1-(1-r)**n for n in [30,60]} for r in [.005,.01,.02,.05]}
json.dump(out, open("data/results.json","w"), indent=1, default=float)
h=out["headline"]; print({k:h[k] for k in h if "power" in k or "zero" in k})
for k in ["effect_curve","placebo_curve","dropout_curve","n_curve","n_curve_response"]:
    print(k,[ (x["scenario"], round(x["power_600_itt_logistic"],3), round(x["power_600_itt_chisq"],3)) for x in out[k]])
for k in ["reality_remission","reality_response","headline_a20"]:
    x=out[k]; print(k, round(x["power_600_itt_logistic"],3), round(x["power_600_itt_chisq"],3), round(x["power_300_itt_logistic"],3), x["zero_placebo_remitters"])
print(out["validation"])
