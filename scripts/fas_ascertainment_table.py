"""Pool Table 11.1 FAS incidence by how each study looked for FAS (Abel 1998).

Reads "Table 11.1 - FAS ascertainment.csv", which classifies each study as
screened (a systematic FAS or dysmorphology examination of the infants), not
screened (FAS left to routine clinical recognition, or infants not examined for
FAS at all) or unverified (paper not yet checked), with the evidence.

Writes "Table 11.1 - pooled by FAS ascertainment.csv": every study with its
class, then pooled rows per class and per class x region, with exact 95% CIs.
Charts: "Table 11.1 - FAS rate by study, by FAS ascertainment.png" (every study,
grouped by class, coloured by continent) and "Table 11.1 - pooled FAS incidence
by FAS ascertainment.png" (pooled rates per class and class x region).

Usage: python3 fas_ascertainment_table.py
"""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

import fas_rates_chart as fas
import fas_pooled_chart as pooled
import table_11_1_chart as t11

from paths import CHARTS, DATA, TABLES
CLASS_PATH = DATA / "Table 11.1 - FAS ascertainment.csv"
OUT_CSV = TABLES / "Table 11.1 - pooled by FAS ascertainment.csv"
OUT_BY_STUDY = CHARTS / "Table 11.1 - FAS rate by study, by FAS ascertainment.png"
OUT_POOLED = CHARTS / "Table 11.1 - pooled FAS incidence by FAS ascertainment.png"

CLASSES = ["Yes", "No", "Unverified"]
CLASS_NAME = {"Yes": "Screened", "No": "Not screened", "Unverified": "Unverified"}
CLASS_DESC = {
    "Yes": "Screened: infants examined for FAS or dysmorphology under a study protocol",
    "No": "Not screened: FAS left to routine clinical recognition, or infants not examined for FAS",
    "Unverified": "Unverified: paper not yet checked",
}


def load():
    """Classes are matched by (country, study) in table order; the two Spanish EUROMAC
    rows share a citation and are taken in sequence."""
    classes = {}
    with open(CLASS_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            classes.setdefault((r["Country"], r["Study (source)"]), []).append(r)
    studies = t11.load_studies()
    for s in studies:
        c = classes[(s["country"], s["study"])].pop(0)
        s["screened"] = c["Screened for FAS"]
        s["ascertainment"] = c["Ascertainment"]
        s["confidence"] = c["Confidence"]
        s["region"] = pooled.region_of(s["country"])
    skipped = {dup for dup, _ in t11.DUPLICATES}
    left = [k for k, v in classes.items() if v and k[1] not in skipped]
    assert not left, f"unmatched class rows: {left}"
    return studies


def line(level, group_name, region, s_or_group):
    group = s_or_group if isinstance(s_or_group, list) else [s_or_group]
    cases, births = sum(s["cases"] for s in group), sum(s["n"] for s in group)
    lo, hi = t11.exact_ci(cases, births)
    one = group[0] if len(group) == 1 and not isinstance(s_or_group, list) else None
    return [level, group_name, region,
            one["country"] if one else "", one["place"] if one else "", one["study"] if one else "",
            one["confidence"] if one else "", one["ascertainment"] if one else "",
            len(group), cases, births, f"{1000 * cases / births:.2f}", f"{lo:.2f}", f"{hi:.2f}"]


def region_colour(s):
    return pooled.REGION_COLOURS[s["region"]]


def study_label(s):
    country = fas.SHORT_NAME.get(s["country"], s["country"])
    if not s["place"]:
        return f'{country}: {s["study"]}'
    if s["place"].endswith(" (state)"):
        return f'{s["place"][:-1]}, {country}): {s["study"]}'
    return f'{s["place"]} ({country}): {s["study"]}'


def continent_legend(ax, marker="o"):
    handles = [Line2D([], [], marker=marker, linestyle="none", markersize=8, color=c, label=r)
               for r, c in pooled.REGION_COLOURS.items()]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9,
              title="Continent", title_fontsize=9)


def chart_by_study(studies):
    rows = []  # (kind, payload): "head" class, "study" s, "pool" group
    for cls in CLASSES:
        group = [s for s in studies if s["screened"] == cls]
        rows.append(("head", cls))
        for s in sorted(group, key=lambda s: (-s["rate"], -s["ci"][1])):
            rows.append(("study", s))
        rows.append(("pool", (cls, group)))

    fig = plt.figure(figsize=(11, 15), facecolor=fas.SURFACE)
    ax = fig.add_axes([0.36, 0.055, 0.6, 0.835])
    fas.style_axes(ax)
    ys = np.arange(len(rows))[::-1]
    labels = []
    for y, (kind, item) in zip(ys, rows):
        if kind == "head":
            ax.axhline(y + 0.5, color=fas.AXIS, linewidth=1)
            labels.append(CLASS_NAME[item])
            continue
        if kind == "study":
            s, c = item, region_colour(item)
            ax.plot(s["ci"], [y, y], color=c, alpha=0.45, linewidth=2.5,
                    solid_capstyle="round", zorder=2)
            ax.scatter(s["rate"], y, s=55, color=c, edgecolor=fas.SURFACE, linewidth=2,
                       zorder=3, clip_on=False)
            ax.annotate(f'{s["cases"]}/{s["n"]:,}', (s["ci"][1], y), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=7.5,
                        color=fas.MUTED, bbox=fas.LABEL_BOX, zorder=4)
            labels.append(study_label(s))
            continue
        cls, group = item
        cases, births = sum(s["cases"] for s in group), sum(s["n"] for s in group)
        rate, ci = 1000 * cases / births, t11.exact_ci(cases, births)
        ax.plot(ci, [y, y], color=fas.INK_2, alpha=0.5, linewidth=4, solid_capstyle="round",
                zorder=2)
        ax.scatter(rate, y, s=90, marker="D", color=fas.INK, edgecolor=fas.SURFACE,
                   linewidth=1.5, zorder=3, clip_on=False)
        ax.annotate(f'{rate:.2f} ({ci[0]:.2f}–{ci[1]:.2f})   {cases}/{births:,}', (ci[1], y),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=8,
                    color=fas.INK_2, bbox=fas.LABEL_BOX, zorder=4)
        labels.append(f"Pooled, {CLASS_NAME[cls].lower()} ({len(group)})")

    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.5)
    for tick, (kind, item) in zip(ax.get_yticklabels(), rows):
        if kind == "head":
            tick.set_fontweight("bold"); tick.set_color(fas.INK); tick.set_fontsize(10)
        elif kind == "pool":
            tick.set_fontweight("bold"); tick.set_color(fas.INK)
        else:
            tick.set_color(region_colour(item))
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlim(0, 18)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Estimated FAS incidence per 1,000 births (dot) with exact 95% CI (bar)",
                  color=fas.INK_2, fontsize=10)
    continent_legend(ax)

    n_ver = sum(s["screened"] != "Unverified" for s in studies)
    fas.titles(fig, "FAS incidence per 1,000 births, by how each study looked for FAS",
               f"{len(studies)} studies from Abel (1998), Table 11.1, grouped by FAS ascertainment "
               f"({n_ver} classified from the papers, {len(studies) - n_ver} not yet checked).\n"
               + CLASS_DESC["Yes"] + ".\n" + CLASS_DESC["No"] + ".\n"
               "Diamonds: pooled rate per group = all cases / all births. Grey numbers: cases / births. "
               "Classification and evidence in 'Table 11.1 - FAS ascertainment.csv'.\n" + t11.duplicates_note())
    fig.savefig(OUT_BY_STUDY, dpi=150, facecolor=fas.SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_BY_STUDY}")


def chart_pooled(studies):
    rows = []
    for cls in CLASSES:
        group = [s for s in studies if s["screened"] == cls]
        rows.append(pooled.pool(CLASS_NAME[cls], group, fas.INK))
        for region, colour in pooled.REGION_COLOURS.items():
            sub = [s for s in group if s["region"] == region]
            if sub:
                rows.append(pooled.pool(region, sub, colour, indent=True))
    rows.append(None)
    rows.append(pooled.pool("All verified studies",
                            [s for s in studies if s["screened"] != "Unverified"], fas.INK_2))
    rows.append(pooled.pool("All studies", studies, fas.INK))

    fig = plt.figure(figsize=(11, 8), facecolor=fas.SURFACE)
    ax = fig.add_axes([0.25, 0.13, 0.48, 0.64])
    fas.style_axes(ax)
    xmax = 5
    ys = np.arange(len(rows))[::-1]
    labels = []
    for y, r in zip(ys, rows):
        if r is None:
            ax.axhline(y, color=fas.AXIS, linewidth=1)
            labels.append("")
            continue
        lo, hi = r["ci"]
        ax.plot([lo, min(hi, xmax)], [y, y], color=r["colour"], alpha=0.45, linewidth=4,
                solid_capstyle="round", zorder=2)
        if hi > xmax:
            ax.annotate("", (xmax, y), xytext=(xmax - 0.18, y),
                        arrowprops=dict(arrowstyle="-|>", color=r["colour"], alpha=0.6, lw=1.5))
        ax.scatter(r["rate"], y, s=80, marker="D", color=r["colour"], edgecolor=fas.SURFACE,
                   linewidth=1.5, zorder=3, clip_on=False)
        labels.append(("    " if r["indent"] else "") + f'{r["name"]} ({r["studies"]})')
        ax.annotate(f'{r["rate"]:.2f}  ({lo:.2f}–{hi:.2f})   {r["cases"]} / {r["births"]:,}',
                    (1.02, y), xycoords=("axes fraction", "data"), va="center", fontsize=8.5,
                    color=fas.INK_2, annotation_clip=False)
    ax.annotate("Pooled rate (95% CI)   cases / births", (1.02, len(rows) - 0.4),
                xycoords=("axes fraction", "data"), va="bottom", fontsize=8.5,
                fontweight="bold", color=fas.INK, annotation_clip=False)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)
    for tick, r in zip(ax.get_yticklabels(), rows):
        if r and not r["indent"]:
            tick.set_fontweight("bold"); tick.set_color(fas.INK)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlim(0, xmax)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("FAS cases per 1,000 births", color=fas.INK_2, fontsize=10)
    continent_legend(ax, marker="D")

    scr = next(r for r in rows if r and r["name"] == "Screened")
    not_scr = next(r for r in rows if r and r["name"] == "Not screened")
    fig.suptitle("FAS incidence pooled by how each study looked for FAS", x=0.03, y=0.965,
                 ha="left", fontsize=15, fontweight="bold", color=fas.INK)
    fig.text(0.03, 0.915,
             f"{len(studies)} studies from Abel (1998), Table 11.1 (number of studies in brackets). "
             "Pooled rate = all FAS cases / all births; bars are exact 95% CIs.\n"
             + CLASS_DESC["Yes"] + ".\n" + CLASS_DESC["No"] + ".\n"
             f"Among studies checked so far, screened studies find {scr['rate']:.1f} per 1,000 and "
             f"unscreened ones {not_scr['rate']:.1f}.",
             ha="left", va="top", fontsize=9.5, color=fas.INK_2)
    clipped = [r for r in rows if r and r["ci"][1] > xmax]
    fig.text(0.03, 0.025, "Classification and evidence in 'Table 11.1 - FAS ascertainment.csv'. "
             + t11.duplicates_note() + " "
             + ("CIs running past the axis: " + "; ".join(f'{r["name"]} ({r["studies"]}) to {r["ci"][1]:.2f}'
                                                           for r in clipped) + "." if clipped else ""),
             ha="left", fontsize=8, color=fas.MUTED)
    fig.savefig(OUT_POOLED, dpi=150, facecolor=fas.SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_POOLED}")


def main():
    studies = load()
    chart_by_study(studies)
    chart_pooled(studies)
    header = ["Level", "Screened for FAS", "Region", "Country", "Place", "Study (source)",
              "Confidence", "Ascertainment", "Studies", "FAS cases", "Births",
              "Rate per 1,000", "95% CI low", "95% CI high"]
    out = [header]
    for cls in CLASSES:
        group = [s for s in studies if s["screened"] == cls]
        for s in sorted(group, key=lambda s: (s["region"], -s["rate"], -s["ci"][1])):
            out.append(line("Study", CLASS_NAME[cls], s["region"], s))
        for region in pooled.REGION_COLOURS:
            sub = [s for s in group if s["region"] == region]
            if sub:
                out.append(line("Class x region pooled", CLASS_NAME[cls], region, sub))
        out.append(line("Class pooled", CLASS_NAME[cls], "", group))
    verified = [s for s in studies if s["screened"] != "Unverified"]
    out.append(line("Overall pooled", "Verified studies", "", verified))
    out.append(line("Overall pooled", "All studies", "", studies))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(out)
    print(f"Saved {OUT_CSV}\n")
    for r in out[1:]:
        if r[0] != "Study":
            print(f"{r[1]:18} {r[2]:14} {r[8]:3} studies {r[9]:3} / {r[10]:6}  {r[11]:>5} ({r[12]}-{r[13]})")


if __name__ == "__main__":
    main()
