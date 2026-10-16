"""FAS incidence vs. drinking during pregnancy, using ONLY exact citation matches
(Abel 1998, Tables 11.1, 11.2 and 11.3).

Same analysis as fas_vs_drinking_chart.py, but without the three same-site links
(Detroit, Netherlands, Roubaix): only studies whose FAS count (Table 11.1) and
during-pregnancy drinking rate (Table 11.2 or 11.3) come from the same citation.

Writes "Table 11.1-11.3 - FAS vs drinking during pregnancy (exact matches).png".

Usage: python3 fas_vs_drinking_exact_chart.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

import fas_rates_chart as fas
import fas_vs_drinking_chart as fvd

from paths import CHARTS
OUT_PNG = CHARTS / "Table 11.1-11.3 - FAS vs drinking during pregnancy (exact matches).png"


def p_text(p):
    return "p<0.001" if p < 0.001 else f"p={p:.2f}"


def main():
    all_studies, matched = fvd.matched_studies()
    exact = [s for s in matched if s["link"] == "exact"]

    fig = plt.figure(figsize=(12, 8.5), facecolor=fas.SURFACE)
    ax = fig.add_axes([0.08, 0.32, 0.6, 0.5])
    fas.style_axes(ax)

    for s in exact:
        c = fvd.REGION_COLOURS[s["region"]]
        ax.scatter(s["during"], s["rate"], s=12 + s["n"] / 60, color=c, alpha=0.45,
                   edgecolor=c, linewidth=0.8, zorder=2)
        label = f'{s["place"]} ({s["cases"]}/{s["n"]:,})'
        if s["cases"]:
            ax.annotate(label, (s["during"], s["rate"]), xytext=(8, 4), textcoords="offset points",
                        fontsize=8, color=fas.INK_2, bbox=fas.LABEL_BOX, zorder=6)

    # Zero-case studies are listed under the axis rather than crowding the zero line.
    zero = sorted((s for s in exact if not s["cases"]), key=lambda s: s["during"])

    rows = []
    for region, c in fvd.REGION_COLOURS.items():
        group = [s for s in exact if s["region"] == region]
        p = fvd.pool(group)
        rows.append((region, p))
        ax.plot([p["drink"]] * 2, p["ci"], color=c, linewidth=3, alpha=0.8,
                solid_capstyle="round", zorder=3)
        ax.scatter(p["drink"], p["rate"], s=120, marker="D", color=c, edgecolor=fas.SURFACE,
                   linewidth=1.5, zorder=5)

    f = fvd.fit(exact)
    xx = np.array([f["x"].min(), f["x"].max()])
    ax.plot(xx, f["intercept"] + f["slope"] * xx, color=fas.INK, linewidth=1.8, zorder=4)

    ax.set_xlim(30, 85)
    ax.set_ylim(-0.15, 2.6)
    ax.axhline(0, color=fas.AXIS, linewidth=0.8, zorder=1)
    ax.set_xlabel("Drinking during pregnancy (% of women)", color=fas.INK_2, fontsize=10)
    ax.set_ylabel("FAS per 1,000 births", color=fas.INK_2, fontsize=10)

    handles = [Line2D([], [], marker="s", linestyle="", markersize=9, markerfacecolor=c,
                      markeredgecolor=c, label=name) for name, c in fvd.REGION_COLOURS.items()]
    handles += [Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor="none",
                       markeredgecolor=fas.INK_2, alpha=0.6, label="Single study (area = births)"),
                Line2D([], [], marker="D", linestyle="", markersize=9, markerfacecolor=fas.INK_2,
                       markeredgecolor=fas.INK_2, label="Region pooled (95% CI bar)"),
                Line2D([], [], color=fas.INK, linewidth=1.8, label="Fit (weighted by births)")]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False,
              fontsize=9, labelcolor=fas.INK_2)

    lines = ["Region          Studies  Drinking   FAS per 1,000 (95% CI)   Cases / births"]
    for region, p in rows:
        lines.append(f'{region:15} {p["studies"]:4}     {p["drink"]:5.1f}%     '
                     f'{p["rate"]:.2f} ({p["ci"][0]:.2f}–{p["ci"][1]:.2f}){"":10}'
                     f'{p["cases"]} / {p["births"]:,}')
    lines += ["", f'Fit: {f["slope"]:+.3f} FAS per 1,000 per point of drinking (95% CI '
                  f'{f["slope_ci"][0]:+.3f} to {f["slope_ci"][1]:+.3f}, {p_text(f["p"])}); '
                  f'Poisson rate ratio per +10 points {f["rr10"]:.2f} '
                  f'({f["rr10_ci"][0]:.2f}–{f["rr10_ci"][1]:.2f}, {p_text(f["p_pois"])})']
    fig.text(0.08, 0.235, "\n".join(lines), ha="left", va="top", fontsize=8.5, color=fas.INK_2,
             family="DejaVu Sans Mono", linespacing=1.4)

    fig.suptitle("FAS incidence vs. drinking during pregnancy: exact matches only",
                 x=0.03, y=0.97, ha="left", fontsize=15, fontweight="bold", color=fas.INK)
    fig.text(0.03, 0.93,
             f"The {len(exact)} of {len(all_studies)} Table 11.1 studies whose during-pregnancy "
             "drinking rate in Tables 11.2/11.3 comes from the same citation. Detroit, the "
             "Netherlands and\nRoubaix are left out (their drinking rates come from other "
             "publications on the same site). Pooled FAS = all cases / all births; drinking = "
             "births-weighted mean.",
             ha="left", va="top", fontsize=9.5, color=fas.INK_2)
    fig.text(0.03, 0.025,
             "Studies with 0 FAS cases (on the zero line): " +
             "; ".join(f'{s["place"]} {s["during"]:g}%' for s in zero) +
             ".\nDrinking = any drinking during pregnancy, not heavy drinking. Spain's two EUROMAC "
             "rows are matched to Vizcaya and Guipuzcoa by sample size (Ogston & Parry 1992).",
             ha="left", fontsize=8, color=fas.MUTED, wrap=True)
    fig.savefig(OUT_PNG, dpi=150, facecolor=fas.SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_PNG}")


if __name__ == "__main__":
    main()
