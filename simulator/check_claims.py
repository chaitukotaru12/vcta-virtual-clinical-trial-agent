import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from any folder
import numpy as np
from scipy import stats
from engine import analytic_power
def exact_power(p1,p0,n1,n0,alpha):
    k1=np.arange(n1+1)[:,None]; k0=np.arange(n0+1)[None,:]
    a=(k1/n1); b=(k0/n0); pbar=(k1+k0)/(n1+n0)
    se=np.sqrt(pbar*(1-pbar)*(1/n1+1/n0))
    with np.errstate(all="ignore"): z=np.where(se>0,(a-b)/se,0)
    rej=z>stats.norm.ppf(1-alpha)
    return float((stats.binom.pmf(k1,n1,p1)*stats.binom.pmf(k0,n0,p0)*rej).sum())
def trend_power(ps,n,alpha,S=200000,seed=0):
    rng=np.random.default_rng(seed); s=np.array([0,1,2.])
    x=rng.binomial(n,ps,size=(S,3)); N=3*n; pbar=x.sum(1)/N
    T=(s*x).sum(1)-pbar*n*s.sum(); V=pbar*(1-pbar)*n*((s**2).sum()-n*(s.sum())**2/N)
    with np.errstate(all="ignore"): z=np.where(V>0,T/np.sqrt(V),0)
    return (z>stats.norm.ppf(1-alpha)).mean()
if __name__ == "__main__":
    print("exact chisq 40 vs 10, 24/arm:", round(exact_power(.4,.1,24,24,.05),3))
    print("exact pooled 30 vs 10, 48 vs 24:", round(exact_power(.3,.1,48,24,.05),3))
    for mid in [.10,.20,.25,.30,.40]:
        print("trend test 10/%d/40, 24/arm:"%(mid*100), round(trend_power(np.array([.1,mid,.4]),24,.05),3))
    print("pooled 30 vs 10 at 60 vs 30 analytic:", round(analytic_power(.3,.1,60,30,.05),3))
    print("pooled 30 vs 10 at 48 vs 24 alpha .05 two-arm 24v24:", round(analytic_power(.3,.1,24,24,.05),3))
