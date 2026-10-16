"""Chart every Table 11.1 study's FAS incidence per 1,000 births, ranked high to low
and coloured by continent (Abel 1998).

Same data as table_11_1_chart.py, but one ranked list instead of country groups.
Studies with no cases are ordered by their upper bound, widest first.

Writes "Table 11.1 - FAS rate per 1,000 births by study, ranked.png".

Usage: python3 fas_ranked_chart.py   (reads the corrected Table 11.1.csv)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

import fas_rates_chart as fas
import fas_pooled_chart as pooled
import table_11_1_chart as t11

from paths import CHARTS
OUT_PNG = CHARTS / "Table 11.1 - FAS rate per 1,000 births by study, ranked.png"

XMAX = 15.5


def chart(studies):
    cases = sum(s["cases"] for s in studies)
    births = sum(s["n"] for s in studies)
    overall = 1000 * cases / births
    # High to low; among zero-case studies, the widest upper bound first.
    rows = sorted(studies, key=lambda s: (-s["rate"], -s["ci"][1]))

    fig = plt.figure(figsize=(11, 13.5), facecolor=fas.SURFACE)
    ax = fig.add_axes([0.36, 0.06, 0.6, 0.83])
    fas.style_axes(ax)

    ys = np.arange(len(rows))[::-1]
    for y, s in zip(ys, rows):
        c = pooled.REGION_COLOURS[pooled.region_of(s["country"])]
        ax.plot(s["ci"], [y, y], color=c, alpha=0.45, linewidth=2.5,
                solid_capstyle="round", zorder=2)
        ax.scatter(s["rate"], y, s=55, color=c, edgecolor=fas.SURFACE, linewidth=2, zorder=3,
                   clip_on=False)
        ax.annotate(f'{s["cases"]}/{s["n"]:,}', (s["ci"][1], y), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=7.5, color=fas.MUTED,
                    bbox=fas.LABEL_BOX, zorder=4)

    def label(s):
        country = fas.SHORT_NAME.get(s["country"], s["country"])
        if not s["place"]:
            return f'{country}: {s["study"]}'
        if s["place"].endswith(" (state)"):  # "Victoria (state)" -> "Victoria (state, Australia)"
            return f'{s["place"][:-1]}, {country}): {s["study"]}'
        return f'{s["place"]} ({country}): {s["study"]}'

    ax.set_yticks(ys)
    ax.set_yticklabels([label(s) for s in rows], fontsize=8.5)
    for tick, s in zip(ax.get_yticklabels(), rows):
        tick.set_color(pooled.REGION_COLOURS[pooled.region_of(s["country"])])
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlim(0, XMAX)
    ax.grid(axis="y", visible=False)

    ax.axvline(overall, color=fas.INK_2, linestyle=(0, (4, 3)), linewidth=1.2, zorder=1)
    ax.annotate(f"Pooled rate {overall:.2f}", (overall, -0.6), xytext=(5, 0),
                textcoords="offset points", fontsize=8.5, color=fas.INK_2, va="bottom",
                bbox=fas.LABEL_BOX)
    ax.set_xlabel("Estimated FAS incidence per 1,000 births (dot) with exact 95% CI (bar)",
                  color=fas.INK_2, fontsize=10)

    handles = [Line2D([], [], marker="o", linestyle="none", markersize=8, color=c, label=region)
               for region, c in pooled.REGION_COLOURS.items()]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9,
              title="Continent", title_fontsize=9)

    fas.titles(fig, "FAS incidence per 1,000 births in prospective studies, ranked",
               f"{len(studies)} studies from Abel (1998), Table 11.1, highest rate first, coloured by "
               f"continent. Pooled rate = {cases} cases / {births:,} births = {overall:.2f} per 1,000.\n"
               "Grey numbers: FAS cases / births. Studies with 0 cases are ordered by their upper "
               "bound, widest first: small samples cannot rule out\nrates of several per 1,000. "
               "Places from Table 11.4.csv.")
    fig.savefig(OUT_PNG, dpi=150, facecolor=fas.SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_PNG}")
    return rows


def main():
    rows = chart(t11.load_studies())
    for i, s in enumerate(rows, 1):
        print(f'{i:2} {s["country"]:15} {s["place"]:18} {s["study"]:32} {s["cases"]:3}/{s["n"]:6} '
              f'{s["rate"]:5.2f} ({s["ci"][0]:.2f}-{s["ci"][1]:.2f})')


if __name__ == "__main__":
    main()
