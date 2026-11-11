"""Draw the README charts from simulator/data.  python docs/make_charts.py"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "simulator", "data")
OUT = os.path.join(ROOT, "docs", "images")
os.makedirs(OUT, exist_ok=True)
C = ["#2f6fdb", "#e0892b", "#3a9d6a", "#9a9a9a"]
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
pct = lambda a: [f"{round(v * 100)}%" for v in a]

# 1. engine reproduces the protocol
v = pd.read_csv(os.path.join(D, "validation.csv"))
fig, ax = plt.subplots(figsize=(8, 3.4))
y = range(len(v))
ax.barh([i + 0.2 for i in y], v.protocol_claim, 0.38, color=C[3], label="Stated in protocol")
ax.barh([i - 0.2 for i in y], v.simulated, 0.38, color=C[0], label="VCTA engine")
for i, (a, b) in enumerate(zip(v.protocol_claim, v.simulated)):
    ax.text(a + 0.01, i + 0.2, pct([a])[0], va="center", fontsize=9)
    ax.text(b + 0.01, i - 0.2, pct([b])[0], va="center", fontsize=9)
ax.set_yticks(list(y), [l.replace(" (", "\n(") for l in v.label]); ax.invert_yaxis()
ax.set_xlim(0, 1); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
fig.suptitle("Step 1 · The engine reproduces the protocol's own power claims", x=0.01, ha="left", fontweight="bold")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2); fig.tight_layout(); fig.savefig(os.path.join(OUT, "01_validation.png")); plt.close(fig)

# 2. fragility of the planned design
pc = pd.read_csv(os.path.join(D, "placebo_curve.csv")); ec = pd.read_csv(os.path.join(D, "effect_curve.csv"))
fig, axs = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
for ax, df, x, lab in [(axs[0], pc, "rate_placebo", "Placebo remission rate (600 mg at 40%)"),
                       (axs[1], ec, "rate_600", "600 mg remission rate (placebo at 10%)")]:
    ax.plot(df[x], df.power_logistic, "-o", color=C[0], label="Protocol analysis model")
    ax.plot(df[x], df.power_chisq, "-o", color=C[1], label="Chi-square")
    ax.axhline(0.8, ls="--", color="#777", lw=1); ax.set_xlabel(lab)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1)); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_ylim(0, 1.02)
axs[0].set_ylabel("Power, 600 mg vs placebo"); axs[0].legend(frameon=False, loc="lower left")
fig.suptitle("Step 2 · The planned 90-patient design is fragile (dashed line = 80% power)", x=0.01, ha="left", fontweight="bold")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "02_fragility.png")); plt.close(fig)

# 3. benchmark reality check and design options
de = pd.read_csv(os.path.join(D, "adv_design.csv"))
fig, ax = plt.subplots(figsize=(9, 4.6))
y = range(len(de))
ax.barh([i - 0.2 for i in y], de.power_remission, 0.38, color=C[3], label="Remission (11% vs 22%)")
ax.barh([i + 0.2 for i in y], de.power_response, 0.38, color=C[2], label="Clinical response (33% vs 53%)")
for i, (a, b) in enumerate(zip(de.power_remission, de.power_response)):
    ax.text(a + 0.01, i - 0.2, pct([a])[0], va="center", fontsize=8.5); ax.text(b + 0.01, i + 0.2, pct([b])[0], va="center", fontsize=8.5)
ax.axvline(0.8, ls="--", color="#777", lw=1)
ax.set_yticks(list(y), de.option); ax.invert_yaxis(); ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1)); ax.set_xlabel("Power at literature benchmark rates (chi-square approximation)")
fig.suptitle("Step 3 · Design options: which redesign reaches 80% power?", x=0.01, ha="left", fontweight="bold")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.4, -0.16), ncol=2); fig.tight_layout(); fig.savefig(os.path.join(OUT, "03_design_options.png")); plt.close(fig)

# 4. virtual cohort side-effect scenario
ae = pd.read_csv(os.path.join(D, "ae_by_type.csv")).sort_values("dose600_pct")
fig, ax = plt.subplots(figsize=(8, 4.6))
for i, (f, lab) in enumerate([("placebo_pct", "Placebo"), ("dose300_pct", "300 mg"), ("dose600_pct", "600 mg")]):
    ax.scatter(ae[f], ae.adverse_event, color=C[i], label=lab, zorder=3, s=28)
for _, r in ae.iterrows():
    ax.plot([min(r.placebo_pct, r.dose300_pct, r.dose600_pct), max(r.placebo_pct, r.dose300_pct, r.dose600_pct)], [r.adverse_event] * 2, color="#ddd", zorder=1)
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1)); ax.set_xlabel("Share of 1,000 virtual participants with at least one event")
fig.suptitle("Virtual cohort · side-effect scenario (hypothetical rates, not drug data)", x=0.01, ha="left", fontweight="bold")
ax.legend(frameon=False, loc="lower right"); fig.tight_layout(); fig.savefig(os.path.join(OUT, "04_virtual_cohort_ae.png")); plt.close(fig)
print("charts written to", OUT)
