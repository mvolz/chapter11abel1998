"""Combine drinking rates from Tables 11.2 and 11.3 (Abel 1998) into one table per
measure, sorted ascending, and chart them - once for drinking before pregnancy and
once for drinking during pregnancy.

Writes to output/, for each measure ("prepregnancy" and "during pregnancy"):
  - "Tables 11.2 and 11.3 - <measure> drinking.csv": every study row that gives that
    percentage, from both tables, sorted lowest to highest.
  - "Tables 11.2 and 11.3 - <measure> drinking.png": one dot per study, lowest at
    the top, coloured by region, with each region's mean and 95% CI.

Reads the corrected CSVs through drinking_rates_chart.py's loaders (which fill in
the book's "same as above" blanks). Table 11.2 covers countries other than the
US and Canada - mostly Europe, plus Australia; Table 11.3 covers the US and Canada.

Usage: python3 prepregnancy_chart.py   (makes both measures)
"""
import csv
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy import stats

import drinking_rates_chart as drc

from paths import CHARTS, TABLES
# key -> (file name prefix, phrase used in titles and axis labels)
MEASURES = {"pre": ("prepregnancy", "before pregnancy"),
            "during": ("during pregnancy", "during pregnancy")}


def out_paths(key):
    stem = f"Tables 11.2 and 11.3 - {MEASURES[key][0]} drinking"
    return TABLES / f"{stem}.csv", CHARTS / f"{stem}.png"

REGION_COLOURS = {"Europe": "#4a3aa7", "North America": "#1baf7a", "Australia/NZ": "#eb6834"}
DESIGN = {"P": "Prospective", "R": "Retrospective"}


def country_of(site):
    site = site.split(", ")[0] if site.startswith("London (UK),") else site
    m = re.search(r"\(([^)]+)\)\s*$", site)
    country = m.group(1) if m else site
    return {"national": "USA"}.get(country, country)


def region_of(country):
    if country in ("USA", "Canada"):
        return "North America"
    if country in ("Australia", "New Zealand"):
        return "Australia/NZ"
    return "Europe"


def build_rows(key):
    rows_2, _ = drc.load_11_2()
    rows_3, _ = drc.load_11_3()
    out = []
    for table, rows in (("11.2", rows_2), ("11.3", rows_3)):
        for r in rows:
            if r[key] is None:
                continue
            if r["site"].startswith("London (UK), "):
                continue  # ethnic subgroups of Waterson & Murray-Lyon; its overall London row stays
            country = country_of(r["site"])
            out.append({"site": r["site"], "country": country, "region": region_of(country),
                        "reference": r["reference"], "design": DESIGN.get(r["design"], ""),
                        "pre": r["pre"], "during": r["during"], "table": table})
    out.sort(key=lambda r: (r[key], r["site"]))
    return out


def write_csv(rows, key):
    out_csv = out_paths(key)[0]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Rank", "Study site", "Country", "Region", "Reference", "Design",
                    "Prepregnancy %", "During pregnancy %", "Source table"])
        for k, r in enumerate(rows, 1):
            w.writerow([k, r["site"], r["country"], r["region"], r["reference"], r["design"],
                        "" if r["pre"] is None else f'{r["pre"]:g}',
                        "" if r["during"] is None else f'{r["during"]:g}',
                        f'Table {r["table"]}'])
    print(f"Saved {out_csv}")


def mean_ci(values):
    v = np.array(values, float)
    m = v.mean()
    if len(v) < 2:
        return m, None
    h = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
    return m, (m - h, m + h)


def chart(rows, key):
    phrase = MEASURES[key][1]
    out_png = out_paths(key)[1]
    # Summary rows (each region's mean and 95% CI, then all studies) go below the studies.
    summary = []
    for region, c in REGION_COLOURS.items():
        vals = [r[key] for r in rows if r["region"] == region]
        m, ci = mean_ci(vals)
        summary.append((f"{region} mean (n={len(vals)})", m, ci, c))
    m, ci = mean_ci([r[key] for r in rows])
    summary.append((f"All studies mean (n={len(rows)})", m, ci, drc.INK))

    n_rows = len(rows) + 1 + len(summary)  # one blank row as a divider
    height = 2.6 + 0.3 * n_rows
    fig = plt.figure(figsize=(11, height), facecolor=drc.SURFACE)
    top, bottom = 1 - 1.9 / height, 1.25 / height
    ax = fig.add_axes([0.42, bottom, 0.54, top - bottom])
    drc.style_axes(ax)

    labels, ys = [], []
    y = n_rows - 1  # lowest rate at the top
    for r in rows:
        c = REGION_COLOURS[r["region"]]
        ax.plot([0, r[key]], [y, y], color=drc.GRID, linewidth=2, zorder=1)
        ax.scatter(r[key], y, s=60, color=c, edgecolor=drc.SURFACE, linewidth=2, zorder=3)
        ax.annotate(f'{r[key]:g}', (r[key], y), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=8, color=drc.INK_2, bbox=drc.LABEL_BOX, zorder=4)
        labels.append(f'{r["site"]}: {r["reference"]}'); ys.append(y)
        y -= 1
    ax.axhline(y, color=drc.AXIS, linewidth=1)  # divider before the summary rows
    y -= 1
    for name, m, ci, c in summary:
        lo, hi = ci
        ax.plot([max(lo, 0), min(hi, 100)], [y, y], color=c, alpha=0.45, linewidth=3,
                solid_capstyle="round", zorder=2)
        ax.scatter(m, y, s=70, marker="D", color=c, edgecolor=drc.SURFACE, linewidth=1.5, zorder=3)
        note = " (CI capped at 100)" if hi > 100 else ""
        ax.annotate(f"{m:.1f}  (95% CI {lo:.1f}–{min(hi, 100):.1f}){note}", (min(hi, 100), y),
                    xytext=(8, 0), textcoords="offset points", va="center", fontsize=8,
                    color=drc.INK_2, bbox=drc.LABEL_BOX, zorder=4)
        labels.append(name); ys.append(y)
        y -= 1

    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.5)
    for tick in ax.get_yticklabels()[len(rows):]:
        tick.set_fontweight("bold")
        tick.set_color(drc.INK)
    ax.set_ylim(-0.7, n_rows - 0.3)
    ax.set_xlim(0, 125)
    ax.set_xticks(range(0, 101, 10))
    ax.spines["bottom"].set_bounds(0, 100)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel(f"Percent of women who drank {phrase}", color=drc.INK_2, fontsize=10)

    drc.titles(fig, f"Women who drank {phrase}: Tables 11.2 and 11.3 combined",
               f"{len(rows)} studies from {drc.SOURCE} that give a {phrase} figure, sorted "
               "lowest to highest.\nBottom rows: mean of each region's studies with a 95% CI.",
               top=1 - 0.35 / height)
    fig.legend(handles=[Line2D([], [], marker="o", linestyle="", markersize=8,
                               markerfacecolor=c, markeredgecolor=drc.SURFACE, label=name)
                        for name, c in REGION_COLOURS.items()],
               loc="upper left", bbox_to_anchor=(0.025, 1 - 1.15 / height), ncol=3,
               frameon=False, fontsize=9.5, labelcolor=drc.INK_2, handletextpad=0.2,
               columnspacing=1.2)
    fig.text(0.03, 0.25 / height, "Europe and Australia/NZ from Table 11.2 (countries other than the "
             "US and Canada); North America from Table 11.3. Excluded: the European, Afro-Caribbean, "
             "East Asian and South Asian\nethnic subgroups of Waterson & Murray-Lyon, 1989 (its overall "
             "London figure is kept). Corrected data - see the Corrections columns in Table 11.2.csv and Table 11.3.csv.",
             ha="left", fontsize=8, color=drc.MUTED)
    fig.savefig(out_png, dpi=150, facecolor=drc.SURFACE)
    plt.close(fig)
    print(f"Saved {out_png}")
    return [f"{n}: {m:.1f} (95% CI {ci[0]:.1f}-{ci[1]:.1f})" for n, m, ci, _ in summary]


def main():
    for key in MEASURES:
        rows = build_rows(key)
        write_csv(rows, key)
        for line in chart(rows, key):
            print("  " + line)


if __name__ == "__main__":
    main()
