"""VCTA prototype engine: Monte Carlo simulation of a parallel-arm trial with a binary endpoint.

Pure NumPy/SciPy so it runs without statsmodels. Everything the engine does follows from
the config's stated assumptions; it produces no evidence about the real drug.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
from scipy import optimize, stats


# ---------------------------------------------------------------- config
@dataclass
class Scenario:
    name: str
    rates: dict            # arm -> marginal remission rate (among completers)
    n_per_arm: int = 30    # randomised per arm
    dropout: float = 0.20
    alpha: float = 0.05    # one-sided
    beta_mayo: float = -0.25
    steroid_prob: float = 0.45
    pk_n: int = 24
    mayo_values: tuple = tuple(range(5, 13))
    mayo_weights: tuple = (0.06, 0.12, 0.17, 0.20, 0.18, 0.13, 0.09, 0.05)


def load_config(path):
    with open(path) as f:
        return json.load(f)


ARMS = ["Placebo", "TJ301 300 mg", "TJ301 600 mg"]


# ---------------------------------------------------------------- cohort
def virtual_cohort(rng, sc: Scenario, S: int):
    """S simulated trials x N patients. Returns arm index, covariates."""
    n = sc.n_per_arm
    N = 3 * n
    arm = np.tile(np.repeat(np.arange(3), n), (S, 1))
    w = np.asarray(sc.mayo_weights) / np.sum(sc.mayo_weights)
    mayo = rng.choice(np.asarray(sc.mayo_values), size=(S, N), p=w).astype(float)
    steroid = (rng.random((S, N)) < sc.steroid_prob).astype(float)
    # PK substudy: pk_n patients, balanced across arms (8 per arm in protocol)
    pk = np.zeros((S, N))
    per = min(sc.pk_n // 3, n)
    for a in range(3):
        idx = np.arange(a * n, a * n + per)
        pk[:, idx] = 1.0
    return arm, mayo, steroid, pk


def calibrate_intercepts(sc: Scenario):
    """Arm intercepts so that the marginal remission rate over the baseline-Mayo
    distribution equals the stated rate."""
    v = np.asarray(sc.mayo_values, float)
    w = np.asarray(sc.mayo_weights) / np.sum(sc.mayo_weights)
    vc = v - np.sum(w * v)
    out = []
    for a in ARMS:
        p = sc.rates[a]
        if p <= 0:
            out.append(-30.0)
            continue
        f = lambda b0: np.sum(w / (1 + np.exp(-(b0 + sc.beta_mayo * vc)))) - p
        out.append(optimize.brentq(f, -30, 30))
    return np.array(out), np.sum(w * v)


def simulate_outcomes(rng, sc: Scenario, S: int):
    arm, mayo, steroid, pk = virtual_cohort(rng, sc, S)
    b0, mayo_mean = calibrate_intercepts(sc)
    lin = b0[arm] + sc.beta_mayo * (mayo - mayo_mean)
    remit = rng.random(arm.shape) < 1 / (1 + np.exp(-lin))
    dropped = rng.random(arm.shape) < sc.dropout      # missing completely at random
    y_itt = (remit & ~dropped).astype(float)          # non-responder imputation
    return dict(arm=arm, mayo=mayo, steroid=steroid, pk=pk,
                y_itt=y_itt, remit=remit.astype(float), dropped=dropped)


# ---------------------------------------------------------------- analyses
def chisq_one_sided(x1, n1, x0, n0, alpha):
    """Pearson chi-square without continuity correction as a one-sided z test
    (the protocol's sample-size method). Vectorised."""
    p1, p0 = x1 / n1, x0 / n0
    pbar = (x1 + x0) / (n1 + n0)
    se = np.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n0))
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(se > 0, (p1 - p0) / se, 0.0)
    return z > stats.norm.ppf(1 - alpha)


def firth_logistic_batch(X, y, iters=30):
    """Batched Firth-penalised logistic regression. X: (S,N,p), y: (S,N).
    Firth handles separation (e.g. zero remissions on placebo), which breaks ordinary ML."""
    S, N, p = X.shape
    beta = np.zeros((S, p))
    for _ in range(iters):
        eta = np.einsum("snp,sp->sn", X, beta)
        mu = 1 / (1 + np.exp(-np.clip(eta, -30, 30)))
        W = mu * (1 - mu)
        XtWX = np.einsum("snp,sn,snq->spq", X, W, X) + 1e-9 * np.eye(p)
        inv = np.linalg.inv(XtWX)
        h = np.einsum("snp,spq,snq->sn", X, inv, X) * W   # leverages
        U = np.einsum("snp,sn->sp", X, y - mu + h * (0.5 - mu))
        step = np.einsum("spq,sq->sp", inv, U)
        step = np.clip(step, -5, 5)
        beta = beta + step
    eta = np.einsum("snp,sp->sn", X, beta)
    mu = 1 / (1 + np.exp(-np.clip(eta, -30, 30)))
    W = mu * (1 - mu)
    cov = np.linalg.inv(np.einsum("snp,sn,snq->spq", X, W, X) + 1e-9 * np.eye(p))
    se = np.sqrt(np.einsum("spp->sp", cov))
    return beta, se


def protocol_model(sim, pooled=False):
    """SAP model: treatment + prior steroids + PK substudy + baseline Mayo (centred)."""
    arm = sim["arm"]
    S, N = arm.shape
    one = np.ones((S, N))
    mayo_c = sim["mayo"] - sim["mayo"].mean()
    if pooled:
        cols = [one, (arm > 0).astype(float)]
    else:
        cols = [one, (arm == 1).astype(float), (arm == 2).astype(float)]
    X = np.stack(cols + [sim["steroid"], sim["pk"], mayo_c], axis=-1)
    return firth_logistic_batch(X, sim["y_itt"])


def ml_separation_rate(sim):
    """Share of simulated trials with zero remissions on placebo (ordinary ML logistic
    regression has no finite estimate there)."""
    y, arm = sim["y_itt"], sim["arm"]
    return np.mean((y * (arm == 0)).sum(1) == 0)


# ---------------------------------------------------------------- runner
def run(sc: Scenario, S=4000, seed=1, with_model=True):
    rng = np.random.default_rng(seed)
    sim = simulate_outcomes(rng, sc, S)
    arm, y = sim["arm"], sim["y_itt"]
    n = sc.n_per_arm
    x = np.stack([(y * (arm == a)).sum(1) for a in range(3)], 1)

    # ITT (non-responder imputation), chi-square, as randomised
    p600 = chisq_one_sided(x[:, 2], n, x[:, 0], n, sc.alpha)
    ppool = chisq_one_sided(x[:, 1] + x[:, 2], 2 * n, x[:, 0], n, sc.alpha)

    # completers-only (what the protocol's 24-per-arm power claim implicitly assumes)
    comp = ~sim["dropped"]
    yc = sim["remit"] * comp
    xc = np.stack([(yc * (arm == a)).sum(1) for a in range(3)], 1)
    nc = np.stack([(comp * (arm == a)).sum(1) for a in range(3)], 1)
    c600 = chisq_one_sided(xc[:, 2], nc[:, 2], xc[:, 0], nc[:, 0], sc.alpha)

    obs = x / n
    res = dict(
        scenario=sc.name, n_per_arm=n, dropout=sc.dropout, alpha=sc.alpha,
        rates=sc.rates,
        power_600_itt_chisq=p600.mean(),
        power_pooled_itt_chisq=ppool.mean(),
        power_600_completers_chisq=c600.mean(),
        obs_rate_mean=obs.mean(0).tolist(),
        diff600_q=np.quantile(obs[:, 2] - obs[:, 0], [0.05, 0.5, 0.95]).tolist(),
        zero_placebo_remitters=ml_separation_rate(sim),
        sims=S,
    )
    if with_model:
        z = stats.norm.ppf(1 - sc.alpha)
        b, se = protocol_model(sim)
        res["power_600_itt_logistic"] = np.mean(b[:, 2] / se[:, 2] > z)
        res["power_300_itt_logistic"] = np.mean(b[:, 1] / se[:, 1] > z)
        bp, sep = protocol_model(sim, pooled=True)
        res["power_pooled_itt_logistic"] = np.mean(bp[:, 1] / sep[:, 1] > z)
    return res


def analytic_power(p1, p0, n1, n0, alpha):
    """Normal-approximation power for the one-sided uncorrected chi-square test."""
    pbar = (n1 * p1 + n0 * p0) / (n1 + n0)
    se0 = np.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n0))
    se1 = np.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
    return stats.norm.cdf(((p1 - p0) - stats.norm.ppf(1 - alpha) * se0) / se1)
