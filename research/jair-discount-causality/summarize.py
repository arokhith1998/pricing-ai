"""Summary tables for results/*_full.csv (mean and standard error over seeds).

Run:  python research/jair-discount-causality/summarize.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "results"
pd.set_option("display.width", 250, "display.max_rows", 500, "display.max_columns", 50)


def ms(df, keys, col, value="regret_pct"):
    """Mean (se) of `value`, one column per level of `col`."""
    g = df.groupby(keys + [col])[value].agg(["mean", "sem"])
    txt = g.apply(lambda r: f"{r['mean']:.1f} ({r['sem']:.1f})", axis=1)
    return txt.unstack(col)


def paired(df, keys, col, a, b, value="regret_pct"):
    """Mean (se) of the per-seed difference a minus b."""
    w = df.pivot_table(index=keys + ["seed"], columns=col, values=value)
    d = (w[a] - w[b]).groupby(level=keys).agg(["mean", "sem"])
    return d.apply(lambda r: f"{r['mean']:+.1f} ({r['sem']:.1f})", axis=1)


if __name__ == "__main__":
    c = pd.read_csv(R / "constraint_full.csv")
    k = ["n_train", "rule", "rho"]
    t = ms(c, k, "model")
    t["constrained - unconstrained"] = paired(c, k, "model", "constrained", "unconstrained")
    print("== 1. Monotone constraint, tree model\n", t.to_string())

    s = pd.read_csv(R / "spline_full.csv")
    t = ms(s, k, "model")
    t["cf - uncorrected"] = paired(s, k, "model", "spline_cf", "spline")
    print("\n== 2. Spline model\n", t.to_string())

    r = pd.read_csv(R / "reps_full.csv")
    k = ["n_train", "n_reps", "rho"]
    t = ms(r, k, "model")
    t["cf - uncorrected"] = paired(r, k, "model", "spline_cf", "spline")
    one = r[r.model == "spline"]
    t["right direction"] = one.assign(ok=np.where(
        one.rho < 0, one.verdict == "rescue",
        np.where(one.rho > 0, one.verdict == "whale", one.verdict == "none detected"))
    ).groupby(k).ok.mean().round(2)
    t["wrong direction"] = one.assign(bad=np.where(
        one.rho < 0, one.verdict == "whale",
        np.where(one.rho > 0, one.verdict == "rescue", False))).groupby(k).bad.mean().round(2)
    print("\n== 3. Number of reps (right direction at rho=0 means 'none detected')\n",
          t.to_string())

    e = pd.read_csv(R / "exclusion_full.csv")
    k = ["n_train", "scenario", "rho"]
    print("\n== 4. Broken instrument\n", ms(e, k, "rule").to_string())
    worst = e.groupby(k + ["rule"]).regret_pct.mean().groupby(["n_train", "rule"]).max().unstack()
    print("\nworst case over scenarios and rho:\n", worst.round(1).to_string())
    one = e[e.rule == "cf"]
    print("\nrep test:\n", one.groupby(["n_train", "scenario"]).agg(
        tau=("tau", "mean"), flagged=("rep_test_p", lambda p: (p < 0.05).mean())
    ).round(3).to_string())
    ab = e.pivot_table(index=k + ["seed"], columns="rule", values="regret_pct")
    for a, b in (("robust_fixed_abstain", "robust_fixed"), ("robust_cal_abstain", "robust_cal")):
        d = (ab[a] - ab[b]).groupby(level=["n_train", "scenario"]).agg(["mean", "sem"]).round(2)
        print(f"\n{a} minus {b}:\n", d.to_string())

    p = pd.read_csv(R / "capacity_full.csv")
    p["model"] = np.where(p.constrained, "constrained", "unconstrained")
    k = ["n_train", "rho", "capacity"]
    t = ms(p, k, "model")
    t["constrained - unconstrained"] = paired(p, k, "model", "constrained", "unconstrained")
    t["mean rec (constrained)"] = p[p.constrained].groupby(k).mean_rec.mean().round(3)
    print("\n== 5. Tree capacity (true best discount is about 0.086)\n", t.to_string())
