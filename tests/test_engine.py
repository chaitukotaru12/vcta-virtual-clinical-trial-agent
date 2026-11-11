"""Validation tests for the VCTA simulation engine.

Each test checks the engine against a known answer: the protocol's own power claim,
an exact calculation, or a property the maths must have. Run with:  pytest -q
"""
import os
import sys

import numpy as np
import pytest
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "simulator"))
from engine import ARMS, Scenario, analytic_power, calibrate_intercepts, firth_logistic_batch, run  # noqa: E402
from check_claims import exact_power, trend_power  # noqa: E402

PROTOCOL = {"Placebo": 0.10, "TJ301 300 mg": 0.20, "TJ301 600 mg": 0.40}


def test_exact_and_normal_approximation_agree():
    """Two independent calculations of the protocol's pairwise power agree."""
    exact = exact_power(0.40, 0.10, 24, 24, 0.05)
    approx = analytic_power(0.40, 0.10, 24, 24, 0.05)
    assert abs(exact - approx) < 0.03
    assert 0.77 < exact < 0.83


def test_monte_carlo_matches_exact():
    """The patient-level simulation reproduces the exact power (24 per arm, no dropout)."""
    r = run(Scenario("protocol frame", PROTOCOL, n_per_arm=24, dropout=0.0), S=20000, seed=1, with_model=False)
    assert abs(r["power_600_itt_chisq"] - exact_power(0.40, 0.10, 24, 24, 0.05)) < 0.02


def test_trend_test_reproduces_protocol_claim():
    """The protocol's 83% is reproduced by a dose-trend test with 300 mg near 15%."""
    assert abs(trend_power(np.array([0.10, 0.15, 0.40]), 24, 0.05) - 0.83) < 0.02


def test_type_one_error_is_controlled():
    """With no drug effect, the trial 'succeeds' about 5% of the time at one-sided alpha 0.05."""
    null = {a: 0.15 for a in ARMS}
    r = run(Scenario("null", null, n_per_arm=60, dropout=0.0), S=20000, seed=2, with_model=False)
    assert r["power_600_itt_chisq"] < 0.07


def test_intercept_calibration_hits_target_rates():
    """Arm intercepts reproduce the stated marginal remission rates exactly."""
    sc = Scenario("cal", PROTOCOL)
    b0, mean = calibrate_intercepts(sc)
    v = np.asarray(sc.mayo_values, float)
    w = np.asarray(sc.mayo_weights) / np.sum(sc.mayo_weights)
    for i, arm in enumerate(ARMS):
        p = np.sum(w / (1 + np.exp(-(b0[i] + sc.beta_mayo * (v - mean)))))
        assert abs(p - PROTOCOL[arm]) < 1e-8


def test_firth_survives_separation():
    """Firth regression stays finite when no placebo patient remits (plain ML would diverge)."""
    n = 30
    arm = np.repeat([0, 1], n)
    y = np.r_[np.zeros(n), (np.arange(n) < 10).astype(float)]
    X = np.stack([np.ones(2 * n), arm.astype(float)], axis=-1)[None]
    beta, se = firth_logistic_batch(X, y[None])
    assert np.all(np.isfinite(beta)) and np.all(np.isfinite(se))
    assert beta[0, 1] > 0


def test_dropout_reduces_power():
    """More dropout (counted as failure) can only lower power."""
    p = [run(Scenario("d", PROTOCOL, dropout=d), S=4000, seed=3, with_model=False)["power_600_itt_chisq"] for d in (0.0, 0.2, 0.4)]
    assert p[0] > p[1] > p[2]


def test_safety_trigger_threshold():
    """4 serious infections in 40 patients gives at least 90% probability the rate exceeds 5%."""
    assert 1 - stats.beta.cdf(0.05, 4 + 0.5, 40 - 4 + 0.5) >= 0.9
    assert 1 - stats.beta.cdf(0.05, 3 + 0.5, 40 - 3 + 0.5) < 0.9


def test_virtual_cohort_is_well_formed():
    """The cohort generator produces 1,000 unique participants with valid categories."""
    cwd = os.getcwd()
    try:
        import cohort  # changes into simulator/ on import
        df, ev = cohort.build(n_total=1000, seed=7)
    finally:
        os.chdir(cwd)
    assert len(df) == 1000 and df.participant.is_unique
    assert set(df.arm) == set(ARMS)
    assert set(ev.severity) <= {"Mild", "Moderate", "Severe"}
    assert set(ev.outcome) <= set(cohort.OUTCOMES)
    assert df.age.between(18, 70).all()
