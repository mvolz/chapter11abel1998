"""Pool FAS incidence per 1,000 births by region, weighting by sample size
(Abel 1998, Table 11.1).

Each pooled rate is total FAS cases / total births across a group's studies, so
large studies count for more - unlike the book's "average rate per study", which
gives every study equal weight. Exact (Clopper-Pearson) 95% CIs.

Writes "Table 11.1 - pooled FAS incidence by region.png" and
"Table 11.1 - studies and pooled rates.csv" (every study, then the pooled rows).

Usage: python3 fas_pooled_chart.py   (reads the corrected Table 11.1.csv)
"""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fas_rates_chart as fas
import table_11_1_chart as t11

from paths import CHARTS, TABLES
OUT_PNG = CHARTS / "Table 11.1 - pooled FAS incidence by region.png"
OUT_ALL_CSV = TABLES / "Table 11.1 - studies and pooled rates.csv"

NORTH_AMERICA = {"United States", "Canada"}
REGION_COLOURS = {"Europe": "#4a3aa7", "North America": "#1baf7a", "Australia": "#eb6834"}


def region_of(country):
    if country in NORTH_AMERICA:
        return "North America"
    return "Australia" if country == "Australia" else "Europe"


def pool(name, group, colour, indent=False):
    cases, births = sum(s["cases"] for s in group), sum(s["n"] for s in group)
    return {"name": name, "studies": len(group), "cases": cases, "births": births,
            "rate": 1000 * cases / births, "ci": t11.exact_ci(cases, births),
            "unweighted": float(np.mean([s["rate"] for s in group])),
            "colour": colour, "indent": indent}


def build(studies):
    rows = []
    for region, c in REGION_COLOURS.items():
        group = [s for s in studies if region_of(s["country"]) == region]
        rows.append(pool(region, group, c))
        if region == "Europe":
            # Sweden supplies 2 of Europe's 4 cases. (Finland is not in Table 11.1.)
            rows.append(pool("Sweden", [s for s in group if s["country"] == "Sweden"],
                             fas.colour("Sweden"), indent=True))
            rows.append(pool("Europe excluding Sweden",
                             [s for s in group if s["country"] != "Sweden"], c, indent=True))
        if region == "North America":
            rows.append(pool("United States", [s for s in group if s["country"] == "United States"],
                             fas.colour("United States"), indent=True))
            rows.append(pool("Canada", [s for s in group if s["country"] == "Canada"],
                             fas.colour("Canada"), indent=True))
    rows.append(None)  # divider
    rows.append(pool("All studies except the US",
                     [s for s in studies if s["country"] != "United States"], fas.INK_2))
    rows.append(pool("All studies", studies, fas.INK))
    return rows


def write_combined_csv(studies):
    """Every study, then its country's and region's pooled rows, then the overall rows."""
    header = ["Level", "Region", "Country", "Place", "Study (source)", "Studies", "FAS cases",
              "Births", "Rate per 1,000", "95% CI low", "95% CI high"]

    def line(level, region, country, place, study, group):
        cases, births = sum(s["cases"] for s in group), sum(s["n"] for s in group)
        lo, hi = t11.exact_ci(cases, births)
        return [level, region, country, place, study, len(group), cases, births,
                f"{1000 * cases / births:.2f}", f"{lo:.2f}", f"{hi:.2f}"]

    out = [header]
    for region in REGION_COLOURS:
        in_region = [s for s in studies if region_of(s["country"]) == region]
        for country in fas.COUNTRY_ORDER:
            group = [s for s in in_region if s["country"] == country]
            if not group:
                continue
            for s in group:
                out.append(line("Study", region, country, s["place"], s["study"], [s]))
            if len(group) > 1:
                out.append(line("Country pooled", region, country, "", "", group))
        if region == "Europe":
            out.append(line("Region pooled", region, "Europe excluding Sweden", "", "",
                            [s for s in in_region if s["country"] != "Sweden"]))
        out.append(line("Region pooled", region, "", "", "", in_region))
    out.append(line("Overall pooled", "All studies except the US", "", "", "",
                    [s for s in studies if s["country"] != "United States"]))
    out.append(line("Overall pooled", "All studies", "", "", "", studies))
    with open(OUT_ALL_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(out)
    print(f"Saved {OUT_ALL_CSV}")


def chart(rows):
    fig = plt.figure(figsize=(11, 7), facecolor=fas.SURFACE)
    ax = fig.add_axes([0.25, 0.15, 0.5, 0.6])
    fas.style_axes(ax)

    ys = np.arange(len(rows))[::-1]
    labels = []
    for y, r in zip(ys, rows):
        if r is None:
            ax.axhline(y, color=fas.AXIS, linewidth=1)
            labels.append("")
            continue
        ax.plot(r["ci"], [y, y], color=r["colour"], alpha=0.45, linewidth=4,
                solid_capstyle="round", zorder=2)
        ax.scatter(r["rate"], y, s=80, marker="D", color=r["colour"], edgecolor=fas.SURFACE,
                   linewidth=1.5, zorder=3)
        ax.scatter(r["unweighted"], y, s=40, marker="o", facecolor=fas.SURFACE,
                   edgecolor=r["colour"], linewidth=1.5, zorder=3)
        labels.append(("    " if r["indent"] else "") + f'{r["name"]} ({r["studies"]})')
        # Numbers in a column to the right of the plot.
        ax.annotate(f'{r["rate"]:.2f}  ({r["ci"][0]:.2f}–{r["ci"][1]:.2f})   '
                    f'{r["cases"]} / {r["births"]:,}',
                    (1.02, y), xycoords=("axes fraction", "data"), va="center", fontsize=8.5,
                    color=fas.INK_2, annotation_clip=False)

    ax.annotate("Pooled rate (95% CI)   cases / births", (1.02, len(rows) - 0.4),
                xycoords=("axes fraction", "data"), va="bottom", fontsize=8.5,
                fontweight="bold", color=fas.INK, annotation_clip=False)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)
    for tick, r in zip(ax.get_yticklabels(), rows):
        if r and r["name"].startswith("All"):
            tick.set_fontweight("bold")
            tick.set_color(fas.INK)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlim(0, 4.2)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("FAS cases per 1,000 births", color=fas.INK_2, fontsize=10)

    total = next(r for r in rows if r and r["name"] == "All studies")
    us = next(r for r in rows if r and r["name"] == "United States")
    fig.suptitle("FAS incidence pooled by sample size, by region", x=0.03, y=0.965, ha="left",
                 fontsize=15, fontweight="bold", color=fas.INK)
    fig.text(0.03, 0.915,
             f"{total['studies']} prospective studies from Abel (1998), Table 11.1 (number of studies "
             "in brackets). Diamonds: pooled rate = all FAS cases / all births,\nso larger studies "
             "count for more; bars are exact 95% CIs. Hollow circles: the unweighted average of the "
             "study rates (the method behind the\nbook's 0.50 per 1,000). "
             f"The US supplies {us['cases']} of the {total['cases']} cases.",
             ha="left", va="top", fontsize=9.5, color=fas.INK_2)
    fig.text(0.03, 0.025, "Rates for the two Larsson studies and Sokol et al., 1993 are recomputed "
             "from cases / births (see Corrections in Table 11.1.csv).\nEurope = all Table 11.1 "
             "countries outside North America and Australia; Finland is not in Table 11.1. Sweden's and Canada's CIs run to 6.36 and 6.13, past the "
             "edge of the axis.", ha="left", fontsize=8, color=fas.MUTED)
    fig.savefig(OUT_PNG, dpi=150, facecolor=fas.SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_PNG}")


def main():
    studies = t11.load_studies()
    rows = build(studies)
    write_combined_csv(studies)
    chart(rows)
    for r in rows:
        if r:
            print(f'{r["name"]:28} {r["studies"]:3} {r["cases"]:3}/{r["births"]:6}  '
                  f'pooled {r["rate"]:.2f} ({r["ci"][0]:.2f}-{r["ci"][1]:.2f})  '
                  f'unweighted {r["unweighted"]:.2f}')


if __name__ == "__main__":
    main()
