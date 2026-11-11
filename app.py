"""VCTA — interactive dashboard (Streamlit).

Run locally:   streamlit run app.py
All figures come from simulator/data (regenerate with python simulator/run_all.py);
the Design explorer tab runs the engine live.
"""
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

ROOT = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(ROOT, "simulator")
DATA = os.path.join(SIM, "data")
sys.path.insert(0, SIM)
from engine import ARMS, Scenario, analytic_power, run  # noqa: E402

st.set_page_config(page_title="VCTA — Virtual Clinical Trial Agent", page_icon="🧪", layout="wide")
BLUE, ORANGE, GREEN, GREY, RED = "#2f6fdb", "#e0892b", "#3a9d6a", "#9a9a9a", "#d64545"


@st.cache_data
def load(name):
    return pd.read_csv(os.path.join(DATA, f"{name}.csv"))


def pct(v, d=0):
    return f"{float(v) * 100:.{d}f}%"


def pct_cols(df, cols):
    out = df.copy()
    for c in cols:
        out[c] = out[c].map(lambda v: pct(v, 1).replace(".0%", "%"))
    return out


def line_fig(traces, x_title, y_title="Power", target=0.8, x_pct=True, height=330):
    fig = go.Figure()
    for name, x, y, color in traces:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=name, line=dict(color=color, width=2.5),
                                 hovertemplate="%{x}<br>%{y:.0%} power<extra>" + name + "</extra>"))
    if target is not None:
        fig.add_hline(y=target, line_dash="dash", line_color="#888", annotation_text=f"{target:.0%}", annotation_position="top left")
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.12),
                      xaxis_title=x_title, yaxis_title=y_title, yaxis=dict(tickformat=".0%", range=[0, 1.02]))
    if x_pct:
        fig.update_xaxes(tickformat=".0%")
    return fig


# ---------------------------------------------------------------- header
headline = load("headline").set_index("metric").value
validation = load("validation").set_index("check")
scen = load("adv_scenarios").set_index("scenario")
design = load("adv_design").set_index("option")
BENCH = "Benchmark: typical new-mechanism phase 2"
FIX = "2 arms x 80, one-sided α 0.10 (160 patients)"

st.title("VCTA — Virtual Clinical Trial Agent")
st.caption("Stress-testing a trial design before the first patient · Case study: TJ301 (olamkicept) phase II in active ulcerative colitis, "
           "protocol CTJ301UC201 v1.1 ([NCT03235752](https://clinicaltrials.gov/study/NCT03235752))")
st.warning("Simulated participants are not patients. These results follow only from the stated assumptions and published benchmarks; "
           "they cannot show that any drug is safe or effective and do not replace expert, ethics or regulatory review.", icon="⚠️")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Power stated in protocol", pct(validation.loc["600mg_vs_placebo", "protocol_claim"]), help="600 mg vs placebo, 24 evaluable per arm")
k2.metric("As randomised, protocol's analysis", pct(headline["power_600_itt_logistic"]), help="10% vs 40% remission, 30/arm, 20% dropout, adjusted logistic regression")
k3.metric("At literature benchmark rates", pct(scen.loc[BENCH, "power_protocol_design"]), help="11% placebo vs 22% on 600 mg")
k4.metric("Recommended redesign", pct(design.loc[FIX, "power_response"]), help="2 arms of 80, clinical response primary, one-sided α 0.10")

tabs = st.tabs(["🚩 Red flags & recommendations", "🎛️ Design explorer (live)", "📚 Benchmarks", "✅ Checkpoints",
                "👥 Virtual cohort", "📈 What-if & validation", "ℹ️ Method & guardrails"])

# ---------------------------------------------------------------- 1. red flags & recommendations
with tabs[0]:
    st.subheader("Red flags to fix before the first patient")
    flags = load("adv_redflags")
    icon = {"High": "🔴", "Medium": "🟠", "Strength": "🟢"}
    for _, r in flags.iterrows():
        st.markdown(f"{icon.get(r.severity, '•')} **{r.area}** — {r.finding}")
    st.subheader("Recommendations and their simulated impact")
    recs = load("adv_recs")
    st.dataframe(recs.rename(columns={"priority": "#", "recommendation": "Recommendation", "detail": "How", "impact": "Simulated impact"}),
                 hide_index=True, width="stretch")
    st.subheader("Design options at benchmark rates")
    d = load("adv_design")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d.option, x=d.power_remission, orientation="h", name="Remission (11% vs 22%)", marker_color=GREY,
                         text=[pct(v) for v in d.power_remission], textposition="outside"))
    fig.add_trace(go.Bar(y=d.option, x=d.power_response, orientation="h", name="Clinical response (33% vs 53%)", marker_color=GREEN,
                         text=[pct(v) for v in d.power_response], textposition="outside"))
    fig.add_vline(x=0.8, line_dash="dash", line_color="#888")
    fig.update_layout(barmode="group", height=480, margin=dict(l=10, r=30, t=30, b=10), xaxis=dict(tickformat=".0%", range=[0, 1.05]),
                      yaxis=dict(autorange="reversed"), legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig, width="stretch")
    st.caption("Power for 600 mg vs placebo, 20% dropout counted as failure, chi-square approximation. Dashed line: 80% power.")

# ---------------------------------------------------------------- 2. design explorer
with tabs[1]:
    st.subheader("Try your own assumptions")
    st.caption("Instant results use the protocol's sample-size method (chi-square, normal approximation). "
               "Press the button to run the full patient-level simulation with the protocol's analysis model.")
    c1, c2, c3 = st.columns(3)
    p0 = c1.slider("Placebo remission", 0.0, 0.30, 0.10, 0.01, format="%.2f")
    p6 = c1.slider("600 mg remission", 0.0, 0.70, 0.40, 0.01, format="%.2f")
    p3 = c1.slider("300 mg remission", 0.0, 0.70, 0.20, 0.01, format="%.2f")
    n = c2.slider("Patients randomised per arm", 10, 300, 30, 5)
    drop = c2.slider("Dropout (counted as failure)", 0.0, 0.5, 0.20, 0.05, format="%.2f")
    alpha = c3.select_slider("One-sided α", options=[0.025, 0.05, 0.10, 0.20], value=0.05)
    target = c3.select_slider("Target power", options=[0.7, 0.8, 0.85, 0.9], value=0.8)

    pw = float(analytic_power(p6 * (1 - drop), p0 * (1 - drop), n, n, alpha))
    n_need = next((m for m in range(10, 2001) if analytic_power(p6 * (1 - drop), p0 * (1 - drop), m, m, alpha) >= target), None)
    m1, m2, m3 = st.columns(3)
    m1.metric("Power, 600 mg vs placebo", pct(pw))
    m2.metric(f"Per arm for {target:.0%} power", f"{n_need}" if n_need else "> 2,000")
    m3.metric("Difference after dropout", f"{(p6 - p0) * (1 - drop) * 100:.1f} pts")
    if p6 <= p0:
        st.error("The drug arm is not better than placebo under these assumptions, so no sample size gives power.")
    elif pw < 0.5:
        st.error("Under these assumptions the trial is more likely to miss a real effect than to find it.")
    elif pw < target:
        st.warning(f"Below the {target:.0%} target: consider more patients, a larger-signal endpoint or a different α.")
    else:
        st.success(f"Meets the {target:.0%} target under these assumptions.")

    ns = list(range(10, max(200, (n_need or 200) + 40), 5))
    st.plotly_chart(line_fig([("Power by patients per arm", ns, [float(analytic_power(p6 * (1 - drop), p0 * (1 - drop), m, m, alpha)) for m in ns], BLUE)],
                             "Patients randomised per arm", target=target, x_pct=False), width="stretch")

    if st.button("Run patient-level simulation (2,000 virtual trials)"):
        with st.spinner("Simulating virtual trials…"):
            r = run(Scenario("explorer", {"Placebo": p0, "TJ301 300 mg": p3, "TJ301 600 mg": p6}, n_per_arm=n, dropout=drop, alpha=alpha), S=2000, seed=11)
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("600 mg, protocol model (Firth logistic)", pct(r["power_600_itt_logistic"]))
        s2.metric("600 mg, chi-square", pct(r["power_600_itt_chisq"]))
        s3.metric("300 mg, protocol model", pct(r["power_300_itt_logistic"]))
        s4.metric("Trials with no placebo remitter", pct(r["zero_placebo_remitters"], 1))
        lo, med, hi = r["diff600_q"]
        st.caption(f"Observed 600 mg minus placebo difference across simulated trials: median {pct(med)} (90% of trials between {pct(lo)} and {pct(hi)}).")

# ---------------------------------------------------------------- 3. benchmarks
with tabs[2]:
    st.subheader("What comparable trials achieved")
    b = load("adv_benchmarks")
    st.dataframe(b.drop(columns=["id"]).rename(columns={"evidence": "Evidence", "value": "Result", "detail": "Why it matters", "source": "Source", "url": "Link"}),
                 hide_index=True, width="stretch", column_config={"Link": st.column_config.LinkColumn("Link", display_text="open")})
    st.subheader("The planned design under each set of assumptions")
    s = load("adv_scenarios")
    st.dataframe(pct_cols(s, ["placebo", "dose300", "dose600", "power_protocol_design", "power_alpha20"]).rename(columns={
        "scenario": "Scenario", "kind": "Type", "placebo": "Placebo", "dose300": "300 mg", "dose600": "600 mg",
        "power_protocol_design": "Power, α 0.05", "power_alpha20": "Power, α 0.20", "n_per_arm_for_80": "Per arm for 80%"}),
        hide_index=True, width="stretch")
    e = load("adv_endpoints")
    st.subheader("Choosing the endpoint: power by patients per arm")
    tr = []
    for name, color in zip(e.endpoint.unique(), [GREEN, GREY, BLUE]):
        sub = e[e.endpoint == name]
        tr.append((name, sub.n_per_arm, sub.power, color))
    st.plotly_chart(line_fig(tr, "Patients randomised per arm", x_pct=False), width="stretch")

# ---------------------------------------------------------------- 4. checkpoints
with tabs[3]:
    st.subheader("Checkpoints to keep the trial achievable")
    ck = load("adv_checkpoints")
    st.dataframe(ck.drop(columns=["id"]).rename(columns={"when": "When", "checkpoint": "Checkpoint", "go": "On track if", "act": "Act if"}),
                 hide_index=True, width="stretch")
    a, b2 = st.columns(2)
    with a:
        st.markdown("**Blinded check: pooled remission in the first 45 completers**")
        bl = load("adv_blinded")
        st.dataframe(pct_cols(bl, ["expected_pooled", "p10", "median", "p90"]).rename(columns={
            "scenario": "If the truth is", "expected_pooled": "Expected", "p10": "Low (10th pct)", "median": "Typical", "p90": "High (90th pct)"}),
            hide_index=True, width="stretch")
        st.markdown("**Dropout check**")
        dr = load("adv_dropout")
        st.dataframe(pct_cols(dr, ["dropout", "power_protocol", "power_realistic"]).rename(columns={
            "dropout": "Dropout", "power_protocol": "Protocol assumptions", "power_realistic": "Benchmark rates"}), hide_index=True, width="stretch")
    with b2:
        st.markdown("**Interim futility look at 50%**")
        io = load("adv_interim")
        st.dataframe(pct_cols(io.drop(columns=["key"]), ["p_stop", "power_no_rule", "power_with_rule"]).rename(columns={
            "truth": "If the truth is", "n_per_arm": "Per arm", "p_stop": "Stops early", "power_no_rule": "Power, no look", "power_with_rule": "Power, with look"}),
            hide_index=True, width="stretch")
        st.markdown("**Safety review trigger calculator**")
        cc1, cc2 = st.columns(2)
        n_exp = cc1.number_input("Patients exposed to active drug", 5, 2000, 40, 5)
        concern = cc2.number_input("Rate of concern (%)", 0.5, 50.0, 5.0, 0.5) / 100
        k = next((k for k in range(0, int(n_exp) + 1) if 1 - stats.beta.cdf(concern, k + 0.5, n_exp - k + 0.5) >= 0.9), None)
        st.info(f"Review when **{k}** events occur among {int(n_exp)} patients on drug: at that point there is at least 90% probability "
                f"the true rate exceeds {concern:.1%} (Jeffreys posterior). Any gastrointestinal perforation or abscess: review at once." if k is not None
                else "No event count reaches 90% probability at this size.")

# ---------------------------------------------------------------- 5. virtual cohort
with tabs[4]:
    st.subheader("1,000 virtual participants under the protocol's assumptions")
    st.caption("Adverse-event types come from the protocol's list of adverse events of special interest (section 8.3) plus UC worsening. "
               "**All adverse-event rates are hypothetical scenario inputs, not data about TJ301.**")
    cs = load("cohort_summary")
    st.dataframe(pct_cols(cs, ["female", "prior_steroids", "itt_remission", "any_ae", "any_related_ae", "any_serious_ae", "any_severe_ae", "discontinued_ae", "discontinued_total"]),
                 hide_index=True, width="stretch")
    ae = load("ae_by_type").sort_values("dose600_pct")
    fig = go.Figure()
    for f, lab, col in [("placebo_pct", "Placebo", BLUE), ("dose300_pct", "300 mg", ORANGE), ("dose600_pct", "600 mg", GREEN)]:
        fig.add_trace(go.Scatter(x=ae[f], y=ae.adverse_event, mode="markers", name=lab, marker=dict(size=10, color=col),
                                 hovertemplate="%{y}: %{x:.1%}<extra>" + lab + "</extra>"))
    fig.update_layout(height=480, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(tickformat=".0%", title="Share with at least one event"),
                      legend=dict(orientation="h", y=1.06))
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Browse the participants**")
    pts = load("participants")
    events = load("ae_events")
    f1, f2, f3 = st.columns(3)
    arm = f1.selectbox("Arm", ["All arms"] + ARMS)
    show = f2.selectbox("Show", ["Everyone", "Had any adverse event", "Had a serious adverse event", "Stopped early", "In remission at week 12"])
    view = pts if arm == "All arms" else pts[pts.arm == arm]
    view = {"Everyone": view, "Had any adverse event": view[view.ae_count > 0], "Had a serious adverse event": view[view.any_serious_ae == "Yes"],
            "Stopped early": view[view.discontinued == "Yes"], "In remission at week 12": view[view.week12_status == "Remission"]}[show]
    st.caption(f"{len(view)} participants match.")
    st.dataframe(view.drop(columns=["remission_probability", "itt_remission"]), hide_index=True, width="stretch", height=320)
    pid = f3.selectbox("Participant's adverse events", ["—"] + view.participant.tolist())
    if pid != "—":
        ev = events[events.participant == pid].drop(columns=["participant", "arm", "source"])
        st.dataframe(ev, hide_index=True, width="stretch") if len(ev) else st.write(f"{pid} had no adverse events.")

# ---------------------------------------------------------------- 6. what-if and validation
with tabs[5]:
    st.subheader("Step 1 — The engine reproduces the protocol's own power claims")
    v = load("validation")
    st.dataframe(pct_cols(v.drop(columns=["check"]), ["protocol_claim", "simulated"]).rename(columns={
        "label": "Claim checked", "protocol_claim": "Protocol", "simulated": "Engine", "method": "Method"}), hide_index=True, width="stretch")
    st.subheader("Step 2 — How fragile is the planned design?")
    c1, c2, c3 = st.columns(3)
    for col, name, x, lab in [(c1, "placebo_curve", "rate_placebo", "Placebo remission (600 mg at 40%)"),
                              (c2, "effect_curve", "rate_600", "600 mg remission (placebo at 10%)"),
                              (c3, "dropout_curve", "dropout", "Dropout (counted as failure)")]:
        df = load(name)
        col.plotly_chart(line_fig([("Protocol model", df[x], df.power_logistic, BLUE), ("Chi-square", df[x], df.power_chisq, ORANGE)], lab, height=300),
                         width="stretch")

# ---------------------------------------------------------------- 7. method
with tabs[6]:
    st.markdown("""
**How it works.** Every number comes from deterministic, tested Python code (NumPy/SciPy): a patient-level Monte Carlo engine with calibrated
virtual cohorts, dropout counted as failure, the protocol's chi-square test and its adjusted logistic regression (Firth-penalised). The design
advisor adds literature benchmarks, design options, an interim futility simulation, blinded checkpoints and Bayesian safety triggers.

**Sources.** Placebo rates from meta-analyses of ulcerative colitis induction trials (global and East Asian); phase 2 results of etrolizumab,
ozanimod and tofacitinib; IL-6 class safety from the ANDANTE trials; FDA 2022 draft guidance. See the Benchmarks tab for links.

**Guardrails.** Simulated participants are not patients. Results cannot establish safety or efficacy. Every result depends on stated
assumptions, and anything not in the protocol is marked as assumed. Nothing here supports exposing people to a drug without the usual
ethics, regulatory and expert review.

**Code and docs:** [GitHub repository](https://github.com/chaitukotaru12/vcta-virtual-clinical-trial-agent)
""")
