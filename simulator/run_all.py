"""Regenerate every result in data/ from scratch (about 5 minutes on a laptop).

    python simulator/run_all.py
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
STEPS = [
    ("check_claims.py", "Reproduce the protocol's own power claims"),
    ("scenarios.py", "What-if scenarios under the protocol's assumptions"),
    ("export.py", "Export scenario results to CSV"),
    ("cohort.py", "1,000 virtual participants with adverse events"),
    ("advisor.py", "Benchmark scenarios, design options, interim, checkpoints, safety triggers"),
    ("report.py", "Red flags, recommendations, checkpoints and benchmark table"),
]
for script, what in STEPS:
    print(f"\n=== {script}: {what} ===")
    runpy.run_path(os.path.join(HERE, script), run_name="__main__")
print("\nAll results written to simulator/data/")
