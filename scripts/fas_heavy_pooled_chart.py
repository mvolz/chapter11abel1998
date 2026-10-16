"""Pool FAS cases per 1,000 estimated heavy drinkers by region (Abel 1998, Table 11.4).

Each study's rate is all its FAS cases divided by its estimated number of heavy
drinkers (Abel's study-level estimate), not a rate observed in heavy-drinking
women followed individually.

Each pooled rate is total FAS cases / total heavy drinkers across a group's
studies, with an exact (Clopper-Pearson) 95% CI. Only studies that give a number
of heavy drinkers can be pooled; the rest are listed in the footnote.

Writes:
  - "Table 11.4 - pooled FAS among heavy drinkers by region.png"
  - "Table 11.4 - heavy drinkers, studies and pooled rates.csv": every study with a
    count, then country, region and overall pooled rows.

Usage: python3 fas_heavy_pooled_chart.py   (reads the corrected Table 11.4.csv)
"""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fas_rates_chart as fas
import table_11_1_chart as t11

from paths import CHARTS, TABLES
OUT_PNG = CHARTS / "Table 11.4 - pooled FAS among heavy drinkers by region.png"
OUT_CSV = TABLES / "Table 11.4 - heavy drinkers, studies and pooled rates.csv"

REGION_COLOURS = {"Europe": "#4a3aa7", "North America": "#1baf7a", "Australia": "#eb6834"}


def region_of(country):
    if country in ("United States", "Canada"):
        return "North America"
    return "Australia" if country == "Australia" else "Europe"


def load():
    with_n, without_n = [], []
    for s in fas.load_studies():
        s["region"] = region_of(s["country"])
        (with_n if s["heavy"] else without_n).append(s)
    return with_n, without_n


def pool(name, group, colour, indent=False):
    cases, n = sum(s["cases"] for s in group), sum(s["heavy"] for s in group)
    return {"name": name, "studies": len(group), "cases": cases, "n": n,
            "rate": 1000 * cases / n, "ci": t11.exact_ci(cases, n),
            "colour": colour, "indent": indent}


def is_sokol(s):
    return s["study"].startswith("Sokol")


def build(studies):
    rows = []
    europe = [s for s in studies if s["region"] == "Europe"]
    rows.append(pool("Europe", europe, REGION_COLOURS["Europe"]))
    for country in ("Finland", "Hungary", "Sweden", "France"):
        rows.append(pool(country, [s for s in europe if s["country"] == country],
                         fas.colour(country), indent=True))
    rows.append(pool("Rest of Europe (UK, Italy, Netherlands)",
                     [s for s in europe if s["country"] not in ("Finland", "Hungary", "Sweden", "France")],
                     REGION_COLOURS["Europe"], indent=True))
    na = [s for s in studies if s["region"] == "North America"]
    us = [s for s in na if s["country"] == "United States"]
    rows.append(pool("North America", na, REGION_COLOURS["North America"]))
    rows.append(pool("United States", us, fas.colour("United States"), indent=True))
    rows.append(pool("Sokol (Cleveland, Detroit)", [s for s in us if is_sokol(s)],
                     fas.colour("United States"), indent=True))
    rows.append(pool("US without Sokol", [s for s in us if not is_sokol(s)],
                     fas.colour("United States"), indent=True))
    rows.append(pool("Canada", [s for s in na if s["country"] == "Canada"],
                     fas.colour("Canada"), indent=True))
    rows.append(pool("Australia", [s for s in studies if s["region"] == "Australia"],
                     REGION_COLOURS["Australia"]))
    rows.append(None)
    rows.append(pool("All studies except the US",
                     [s for s in studies if s["country"] != "United States"], fas.INK_2))
    rows.append(pool("All studies with a count", studies, fas.INK))
    return rows


def write_csv(studies):
    header = ["Level", "Region", "Country", "Place", "Study (source)", "Studies", "FAS cases",
              "Heavy drinkers", "Cases per 1,000 estimated heavy drinkers", "95% CI low", "95% CI high"]

    def line(level, region, country, place, study, group):
        cases, n = sum(s["cases"] for s in group), sum(s["heavy"] for s in group)
        lo, hi = t11.exact_ci(cases, n)
        return [level, region, country, place, study, len(group), cases, n,
                f"{1000 * cases / n:.1f}", f"{lo:.1f}", f"{hi:.1f}"]

    out = [header]
    for region in REGION_COLOURS:
        in_region = [s for s in studies if s["region"] == region]
        for country in fas.COUNTRY_ORDER:
            group = [s for s in in_region if s["country"] == country]
            for s in group:
                out.append(line("Study", region, country, s["place"], s["study"], [s]))
            if len(group) > 1:
                out.append(line("Country pooled", region, country, "", "", group))
        out.append(line("Region pooled", region, "", "", "", in_region))
    us = [s for s in studies if s["country"] == "United States"]
    out.append(line("Subgroup pooled", "North America", "United States", "", "Sokol studies only",
                    [s for s in us if is_sokol(s)]))
    out.append(line("Subgroup pooled", "North America", "United States", "", "Without Sokol studies",
                    [s for s in us if not is_sokol(s)]))
    out.append(line("Overall pooled", "All studies except the US", "", "", "",
                    [s for s in studies if s["country"] != "United States"]))
    out.append(line("Overall pooled", "All studies with a count", "", "", "", studies))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(out)
    print(f"Saved {OUT_CSV}")


def chart(rows, studies, without_n):
    fig = plt.figure(figsize=(12, 9), facecolor=fas.SURFACE)
    ax = fig.add_axes([0.27, 0.2, 0.45, 0.6])
    fas.style_axes(ax)
    xmax = 400

    ys = np.arange(len(rows))[::-1]
    labels = []
    for y, r in zip(ys, rows):
        if r is None:
            ax.axhline(y, color=fas.AXIS, linewidth=1)
            labels.append("")
            continue
        ax.plot([r["ci"][0], min(r["ci"][1], xmax)], [y, y], color=r["colour"], alpha=0.45,
                linewidth=4, solid_capstyle="round", zorder=2)
        ax.scatter(r["rate"], y, s=80, marker="D", color=r["colour"], edgecolor=fas.SURFACE,
                   linewidth=1.5, zorder=3)
        labels.append(("    " if r["indent"] else "") + f'{r["name"]} ({r["studies"]})')
        ax.annotate(f'{r["rate"]:5.1f}  ({r["ci"][0]:.1f}–{r["ci"][1]:.1f})   '
                    f'{r["cases"]} / {r["n"]:,}', (1.02, y), xycoords=("axes fraction", "data"),
                    va="center", fontsize=8.5, color=fas.INK_2, annotation_clip=False)
    ax.annotate("Per 1,000 (95% CI)   cases / est. heavy drinkers", (1.02, len(rows) - 0.4),
                xycoords=("axes fraction", "data"), va="bottom", fontsize=8.5,
                fontweight="bold", color=fas.INK, annotation_clip=False)

    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)
    for tick, r in zip(ax.get_yticklabels(), rows):
        if r and not r["indent"]:
            tick.set_fontweight("bold")
            tick.set_color(fas.INK)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlim(0, xmax)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("FAS cases per 1,000 estimated heavy drinkers "
                  "(all FAS cases / estimated number of heavy drinkers)", color=fas.INK_2,
                  fontsize=10)

    us = next(r for r in rows if r and r["name"] == "United States")
    eu = next(r for r in rows if r and r["name"] == "Europe")
    fig.suptitle("FAS cases per 1,000 estimated heavy drinkers, pooled by region", x=0.03,
                 y=0.965, ha="left",
                 fontsize=15, fontweight="bold", color=fas.INK)
    fig.text(0.03, 0.915,
             f"{len(studies)} of the {len(studies) + len(without_n)} studies in Abel (1998), Table 11.4 "
             "that give a number of heavy drinkers (number of studies in brackets).\nPooled rate = all "
             "FAS cases, whoever the mother was, / all estimated heavy drinkers - a study-level ratio, not a rate observed "
             "in heavy-drinking women followed\nindividually; bars are exact 95% CIs. Per 1,000 "
             f"estimated heavy drinkers, Europe ({eu['rate']:.1f}) and the US ({us['rate']:.1f}) are "
             "almost identical. Europe's cases come from\nFinland, Hungary and Sweden.",
             ha="left", va="top", fontsize=9.5, color=fas.INK_2)
    fig.text(0.03, 0.02,
             f"Not pooled (no number of heavy drinkers): " +
             "; ".join(f'{s["place"]} ({s["study"]})' for s in without_n) + ".\n"
             "Heavy drinking is defined differently across studies (Table 11.4 footnote: 2+ drinks/day, "
             "5-6 per occasion, positive MAST or clinical diagnosis; Day et al. 0.89+ drinks/day). "
             "Several European samples are\nwomen in alcoholism treatment (Budapest, Helsinki, "
             "Gothenburg). Finnish citations swapped per Corrections in Table 11.4.csv.",
             ha="left", fontsize=7.8, color=fas.MUTED, wrap=True)
    fig.savefig(OUT_PNG, dpi=150, facecolor=fas.SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_PNG}")


def main():
    studies, without_n = load()
    rows = build(studies)
    write_csv(studies)
    chart(rows, studies, without_n)
    for r in rows:
        if r:
            print(f'{r["name"]:42} {r["studies"]:3} {r["cases"]:3}/{r["n"]:5}  '
                  f'{r["rate"]:6.1f} ({r["ci"][0]:.1f}-{r["ci"][1]:.1f})')


if __name__ == "__main__":
    main()
