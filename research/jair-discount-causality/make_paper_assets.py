"""Build every table and figure data file in paper/ from results/*.csv.

Nothing in the manuscript's tables or plots is typed by hand: rerun this after
rerunning the experiments.

Run:  python research/jair-discount-causality/make_paper_assets.py
Writes paper/tables/*.tex (booktabs tabulars) and paper/data/*.dat (pgfplots).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
R, T, D = HERE / "results", HERE / "paper" / "tables", HERE / "paper" / "data"


def cell(mean: float, se: float) -> str:
    return f"{mean:.1f} ({se:.1f})"


def signed(mean: float, se: float) -> str:
    return f"${mean:+.1f}$ ({se:.1f})"


def stats(df: pd.DataFrame, keys: list[str], col: str, value: str = "regret_pct"):
    """{(key values..., level): (mean, se)}"""
    g = df.groupby(keys + [col])[value].agg(["mean", "sem"])
    return {k: (v["mean"], v["sem"]) for k, v in g.iterrows()}


def paired(df, keys, col, a, b, value="regret_pct"):
    w = df.pivot_table(index=keys + ["seed"], columns=col, values=value)
    g = (w[a] - w[b]).groupby(level=keys).agg(["mean", "sem"])
    return {(k if isinstance(k, tuple) else (k,)): (v["mean"], v["sem"])
            for k, v in g.iterrows()}


def write_table(name: str, spec: str, header: list[str], rows: list[list[str]]) -> None:
    lines = [f"\\begin{{tabular}}{{{spec}}}", "\\toprule",
             " & ".join(header) + " \\\\", "\\midrule"]
    lines += [" & ".join(r) + " \\\\" if r else "\\midrule" for r in rows]
    lines += ["\\bottomrule", "\\end{tabular}", ""]
    (T / f"{name}.tex").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def rho_label(r: float) -> str:
    return "0" if r == 0 else f"${r:+.1f}$"


def constraint_tables():
    c = pd.read_csv(R / "constraint_full.csv")
    k = ["n_train", "rule", "rho"]
    s, d = stats(c, k, "model"), paired(c, k, "model", "constrained", "unconstrained")
    for n in (20000, 2000):
        rows = [[rho_label(r), cell(*s[(n, "full", r, "constrained")]),
                 cell(*s[(n, "full", r, "unconstrained")]), signed(*d[(n, "full", r)]),
                 cell(*s[(n, "cohort", r, "constrained")]), signed(*d[(n, "cohort", r)])]
                for r in sorted(c.rho.unique())]
        write_table(f"constraint_{n}", "rrrrrr",
                    ["$\\rho$", "Constrained", "Unconstrained", "Difference",
                     "Constrained (clip)", "Difference (clip)"], rows)


def spline_tables():
    s_ = pd.read_csv(R / "spline_full.csv")
    k = ["n_train", "rule", "rho"]
    s = stats(s_, k, "model")
    d = paired(s_, k, "model", "spline_cf", "spline")
    rows = [[rho_label(r)] + [cell(*s[(n, "full", r, m)])
                              for n in (20000, 2000)
                              for m in ("spline", "spline_cf", "spline_oracle")]
            for r in sorted(s_.rho.unique())]
    write_table("spline", "rrrrrrr",
                ["$\\rho$", "Naive", "Corrected", "Oracle", "Naive", "Corrected", "Oracle"], rows)
    return s, d


def exclusion_table():
    e = pd.read_csv(R / "exclusion_full.csv")
    k = ["n_train", "scenario", "rho"]
    s = stats(e, k, "rule")
    rules = ["uncorrected", "cf", "robust_cal", "robust_fixed", "segment_median"]
    rows = []
    for sc in ("valid", "aligned", "partial", "unaligned"):
        for r in (-0.6, 0.0, 0.6):
            rows.append([sc if r == -0.6 else "", rho_label(r)]
                        + [cell(*s[(20000, sc, r, rule)]) for rule in rules])
        rows.append([])
    worst = e[e.n_train == 20000].groupby(["scenario", "rho", "rule"]).regret_pct.mean() \
        .groupby("rule").max()
    rows.append(["worst case", ""] + [f"{worst[rule]:.1f}" for rule in rules])
    write_table("exclusion", "lrrrrrr",
                ["Scenario", "$\\rho$", "Naive", "Corrected", "Robust (calibrated)",
                 "Robust (fixed)", "Segment median"], rows)

    one = e[e.rule == "cf"]
    g = one.groupby(["scenario", "n_train"]).agg(
        tau=("tau", "mean"), flag=("rep_test_p", lambda p: 100 * (p < 0.05).mean()))
    rows = [[sc, f"{g.loc[(sc, 20000), 'tau']:.2f}", f"{g.loc[(sc, 20000), 'flag']:.0f}\\%",
             f"{g.loc[(sc, 2000), 'tau']:.2f}", f"{g.loc[(sc, 2000), 'flag']:.0f}\\%"]
            for sc in ("valid", "aligned", "partial", "unaligned")]
    write_table("rep_test", "lrrrr",
                ["Scenario", "$\\hat\\tau$", "Flagged", "$\\hat\\tau$", "Flagged"], rows)


def capacity_table():
    p = pd.read_csv(R / "capacity_full.csv")
    p["model"] = np.where(p.constrained, "con", "unc")
    k = ["n_train", "rho", "capacity"]
    s, d = stats(p, k, "model"), paired(p, k, "model", "con", "unc")
    rec = p[p.constrained].groupby(k).mean_rec.mean()
    names = {"product_50x7": "50 trees, 7 leaves, 150 per leaf (shipped)",
             "200x7": "200 trees, 7 leaves, 150 per leaf",
             "500x7_child50": "500 trees, 7 leaves, 50 per leaf",
             "500x15_child50": "500 trees, 15 leaves, 50 per leaf",
             "500x15_lr10_child20": "500 trees, 15 leaves, 20 per leaf, rate 0.1"}
    rows = [[label] + [cell(*s[(20000, r, cap, "con")]) for r in (-0.6, 0.0, 0.6)]
            + [signed(*d[(20000, r, cap)]) for r in (-0.6, 0.6)]
            + [f"{100 * rec[(20000, 0.0, cap)]:.1f}\\%"]
            for cap, label in names.items()]
    write_table("capacity", "lrrrrrr",
                ["Capacity", "$\\rho=-0.6$", "$\\rho=0$", "$\\rho=+0.6$",
                 "Diff., $-0.6$", "Diff., $+0.6$", "Mean rec."], rows)


def assignment_table():
    a = pd.read_csv(R / "assignment_full.csv")
    k = ["n_train", "mechanism", "rho"]
    s = stats(a, k, "rule")
    one = a[(a.rule == "cf")]
    bal = one.groupby("mechanism").balance_p.apply(lambda p: 100 * (p < 0.05).mean())
    rep = one[one.n_train == 20000].groupby("mechanism").rep_test_p.apply(
        lambda p: 100 * (p < 0.05).mean())
    labels = {"random": "Random", "territory_1.0": "Territory",
              "sorting_+0.3": "Sorting $+0.3$", "sorting_+0.6": "Sorting $+0.6$",
              "sorting_-0.3": "Sorting $-0.3$", "sorting_-0.6": "Sorting $-0.6$"}
    rows = []
    for mech, label in labels.items():
        for r in (-0.6, 0.0, 0.6):
            first = r == -0.6
            rows.append([label if first else "", rho_label(r)]
                        + [cell(*s[(20000, mech, r, rule)])
                           for rule in ("uncorrected", "cf", "robust_fixed")]
                        + ([f"{bal[mech]:.0f}\\%", f"{rep[mech]:.0f}\\%"] if first else ["", ""]))
        rows.append([])
    write_table("assignment", "lrrrrrr",
                ["Assignment", "$\\rho$", "Naive", "Corrected", "Robust (fixed)",
                 "Balance", "Rep test"], rows[:-1])


def reps_table():
    r_ = pd.read_csv(R / "reps_full.csv")
    k = ["n_train", "n_reps", "rho"]
    d = paired(r_, k, "model", "spline_cf", "spline")
    rows = [[str(n_reps)] + [signed(*d[(n, n_reps, r)]) for n in (20000, 2000)
                             for r in (-0.6, 0.0, 0.6)]
            for n_reps in (6, 12, 25, 50)]
    write_table("reps", "rrrrrrr",
                ["Reps", "$-0.6$", "$0$", "$+0.6$", "$-0.6$", "$0$", "$+0.6$"], rows)


def figure_data():
    # Figure 1: causal, observational and monotone-constrained win curves.
    import verify_propositions_2 as v2
    alpha, beta, rho = -0.5, 0.55, -0.5
    grid = v2.GRID
    causal = v2.structural_curve(alpha, beta)
    obs = v2.observational_curve(rho, alpha, beta)
    mono = v2.monotone_fit(obs, norm.pdf(grid, v2.M, v2.SD_D))
    keep = slice(0, len(grid), 20)
    pd.DataFrame({"d": 100 * grid[keep], "causal": causal[keep], "obs": obs[keep],
                  "mono": mono[keep]}).to_csv(D / "curves.dat", sep=" ", index=False,
                                              float_format="%.4f")
    picks = {name: 100 * grid[v2.first_argmax((1 - grid) * c)]
             for name, c in (("causal", causal), ("obs", obs), ("mono", mono))}
    (D / "curves_picks.txt").write_text(
        "\n".join(f"{k} {v:.1f}" for k, v in picks.items()) + "\n", encoding="utf-8")

    # Figure 2: regret against confounding strength, four models, 20,000 deals.
    c = pd.read_csv(R / "constraint_full.csv")
    s_ = pd.read_csv(R / "spline_full.csv")
    c = c[(c.n_train == 20000) & (c.rule == "full")]
    s_ = s_[(s_.n_train == 20000) & (s_.rule == "full")]
    out = pd.DataFrame({"rho": sorted(c.rho.unique())})
    for name, df, model in (("treecon", c, "constrained"), ("treeunc", c, "unconstrained"),
                            ("splinenaive", s_, "spline"), ("splinecf", s_, "spline_cf")):
        g = df[df.model == model].groupby("rho").regret_pct.agg(["mean", "sem"])
        out[name] = g["mean"].to_numpy()
        out[name + "se"] = g["sem"].to_numpy()
    out.to_csv(D / "regret.dat", sep=" ", index=False, float_format="%.3f")


if __name__ == "__main__":
    T.mkdir(parents=True, exist_ok=True)
    D.mkdir(parents=True, exist_ok=True)
    constraint_tables()
    spline_tables()
    exclusion_table()
    capacity_table()
    assignment_table()
    reps_table()
    figure_data()
    for f in sorted(list(T.glob("*.tex")) + list(D.glob("*"))):
        print(f.relative_to(HERE), f.stat().st_size, "bytes")
