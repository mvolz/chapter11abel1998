"""Chart drinking before and during pregnancy (Abel 1998, Tables 11.2 and 11.3).

Writes three images to output/charts/:
  1. Table 11.2 (countries other than the US and Canada): each study's
     prepregnancy and during-pregnancy percentages, joined by a line.
  2. Table 11.3 (United States and Canada): the same chart.
  3. Both tables together: during-pregnancy % against prepregnancy % for the
     studies that report both, with a "no change" diagonal.

The CSVs copy the book's layout, where a blank site or reference means "same
as the row above" (e.g. the ethnic-group rows of Waterson & Murray-Lyon, 1989,
and the second rows of several US studies). Those blanks are filled in from
the row above. Rows that give neither percentage are listed in a footnote.

The CSVs hold corrected data (misprinted names fixed, averages recomputed);
the Corrections column records each change, and the charts footnote the name fixes.
Each Corrections entry records what the book originally printed.

Usage: python3 drinking_rates_chart.py   (reads the CSVs in data/)
"""
import csv
import re
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from paths import CHARTS, DATA
CSV_11_2 = DATA / "Table 11.2.csv"
CSV_11_3 = DATA / "Table 11.3.csv"
OUT_11_2 = CHARTS / "Table 11.2 - drinking before and during pregnancy, outside US and Canada.png"
OUT_11_3 = CHARTS / "Table 11.3 - drinking before and during pregnancy, US and Canada.png"
OUT_BOTH = CHARTS / "Tables 11.2 and 11.3 - during vs before pregnancy.png"

# Chart chrome (light mode), shared with fas_rates_chart.py.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
LABEL_BOX = dict(boxstyle="square,pad=0.1", facecolor=SURFACE, edgecolor="none")

PRE_COLOUR = "#2a78d6"     # prepregnancy
DURING_COLOUR = "#eb6834"  # during pregnancy
# Scatter: which table a study comes from.
TABLE_COLOURS = {"Table 11.2": "#4a3aa7", "Table 11.3": "#1baf7a"}

SOURCE = "Abel (1998)"


def number(text):
    return float(text) if text.strip() else None


# Averages as printed in the book; the CSVs hold the recomputed means.
PRINTED_AVERAGES = {"Table 11.2": (69.0, 49.0), "Table 11.3": (68.0, 49.0)}


# Rows whose before- and during-pregnancy figures were measured differently: the
# EUROMAC questionnaire took during-pregnancy drinking from a diary of the week
# before interview, while before-pregnancy drinking was asked more crudely (Ogston
# & Parry 1992; Bolumar 1992). Their before-pregnancy figures are left out of the
# charts so before and during are never compared across methods.
BEFORE_NOT_COMPARABLE = {
    ("Berlin (Germany)", "Ogston & Parry, 1992"),
    ("Odense (Denmark)", "Ogston & Parry, 1992"),
    ("Porto (Portugal)", "Ogston & Parry, 1992"),
    ("Vizcaya (Spain)", "Ogston & Parry, 1992"),
    ("Guipuzcoa (Spain)", "Ogston & Parry, 1992"),
    ("Valencia (Spain)", "Bolumar et al., 1994"),
}


def load_11_2():
    rows, prev = [], None
    with open(CSV_11_2, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            site = r["City/Country"]
            if site == "Average":
                average = (number(r["Prepregnancy %"]), number(r["During pregnancy %"]))
                continue
            ref = r["Reference"]
            if not ref:
                # Ethnic-group rows belong to the London study above them.
                ref = prev["reference"]
                site = f"London (UK), {site} ethnic group"
            elif site == "European":
                site = "London (UK), European ethnic group"
            row = {"site": site, "reference": ref, "design": "", "note": r["Corrections"],
                   "pre": number(r["Prepregnancy %"]),
                   "during": number(r["During pregnancy %"])}
            if (site, ref) in BEFORE_NOT_COMPARABLE:
                row["pre_dropped"], row["pre"] = row["pre"], None
            rows.append(row)
            prev = row
    # Averages of the figures actually charted (the CSV's Average row covers all rows).
    average = tuple(round(sum(v) / len(v), 1) for v in
                    ([r[k] for r in rows if r[k] is not None] for k in ("pre", "during")))
    return rows, average


def load_11_3():
    rows, prev = [], None
    with open(CSV_11_3, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            site = r["Study site"]
            if site == "Average":
                average = (number(r["Prepregnancy %"]), number(r["During pregnancy %"]))
                continue
            design = r["Design (P=Prospective, R=Retrospective)"]
            if not site:  # continuation of the study site above
                site, design = prev["site"], design or prev["design"]
            row = {"site": site, "reference": r["Reference"] or prev["reference"],
                   "design": design, "note": r["Corrections"],
                   "pre": number(r["Prepregnancy %"]),
                   "during": number(r["During pregnancy %"])}
            rows.append(row)
            prev = row
    return rows, average


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def titles(fig, title, subtitle, top=0.975):
    fig.suptitle(title, x=0.03, y=top, ha="left", fontsize=15, fontweight="bold", color=INK)
    fig.text(0.03, top - 0.027, subtitle, ha="left", va="top", fontsize=9.5, color=INK_2)


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values), len(values)


def printed_value(note):
    """What the book printed, from a 'Misprint: ...' correction (a quoted name or a number)."""
    m = re.search(r'printed "([^"]+)"', note) or re.search(r"printed ([\d.]+)", note)
    return f'printed "{m.group(1)}"' if m else "corrected"


def dumbbell(rows, average, table, title, out_path, sort_by_during=False):
    shown = [r for r in rows if r["pre"] is not None or r["during"] is not None]
    order = "in the book's order"
    if sort_by_during:
        # Highest during-pregnancy % first; rows without one go last, by prepregnancy %.
        shown.sort(key=lambda r: (r["during"] is None, -(r["during"] or 0), -(r["pre"] or 0)))
        order = ("sorted by during-pregnancy %, highest first (rows without one at the "
                 "bottom)")
    empty = [r for r in rows if r not in shown]

    notes = []
    if empty:
        listed = "; ".join(f'{r["site"]} ({r["reference"]})' for r in empty)
        notes.append(f"Not shown: {len(empty)} rows with no percentage printed — {listed}.")
    fixes = "; ".join(
        f'{r["site"]} — {r["reference"]} ({printed_value(r["note"])})'
        for r in rows if r["note"].startswith(("Misprint", "Term updated")))
    if fixes:
        notes.append(f"Corrected from the book: {fixes}.")
    dropped = [r for r in rows if r.get("pre_dropped") is not None]
    if dropped:
        notes.append("Before-pregnancy figure left out (measured differently from the during-pregnancy "
                     "figure - EUROMAC questionnaire): " +
                     "; ".join(f'{r["site"]} ({r["pre_dropped"]:g}%)' for r in dropped) + ".")
    wrapped = [textwrap.fill(n, 170) for n in notes]
    note_text = "\n".join(wrapped)
    note_lines = sum(w.count("\n") + 1 for w in wrapped)

    height = 2.6 + 0.3 * len(shown) + 0.15 * note_lines
    fig = plt.figure(figsize=(11.5, height), facecolor=SURFACE)
    top = 1 - 1.95 / height
    bottom = (0.85 + 0.17 * note_lines) / height
    ax = fig.add_axes([0.43, bottom, 0.53, top - bottom])
    style_axes(ax)

    ys = np.arange(len(shown))[::-1]
    for y, r in zip(ys, shown):
        if r["pre"] is not None and r["during"] is not None:
            ax.plot([r["pre"], r["during"]], [y, y], color=AXIS, linewidth=2, zorder=1)
        for key, c in (("pre", PRE_COLOUR), ("during", DURING_COLOUR)):
            if r[key] is not None:
                ax.scatter(r[key], y, s=60, color=c, edgecolor=SURFACE, linewidth=2, zorder=3)
        # Value labels sit outside the pair: the lower value to the left.
        vals = [(r[k], k) for k in ("pre", "during") if r[k] is not None]
        lo, hi = min(vals), max(vals)
        ax.annotate(f"{hi[0]:g}", (hi[0], y), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK_2, bbox=LABEL_BOX, zorder=4)
        if lo is not hi:
            ax.annotate(f"{lo[0]:g}", (lo[0], y), xytext=(-8, 0), textcoords="offset points",
                        va="center", ha="right", fontsize=8, color=INK_2, bbox=LABEL_BOX,
                        zorder=4)

    labels = []
    for r in shown:
        design = f' ({"prospective" if r["design"] == "P" else "retrospective"})' \
            if r["design"] in ("P", "R") else ""
        labels.append(f'{r["site"]}: {r["reference"]}{design}')
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_ylim(-0.7, len(shown) - 0.3)
    ax.set_xlim(0, 105)
    ax.set_xticks(range(0, 101, 10))
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Percent of women who drink", color=INK_2, fontsize=10)

    # The tables' averages (recomputed), as reference lines.
    for value, c, name, dx, ha in ((average[0], PRE_COLOUR, "prepregnancy", 4, "left"),
                                   (average[1], DURING_COLOUR, "during", -4, "right")):
        ax.axvline(value, color=c, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.8, zorder=2)
        ax.annotate(f"Avg. {name} {value:g}%", (value, len(shown) - 0.4), xytext=(dx, 0),
                    textcoords="offset points", fontsize=8, color=INK_2, va="bottom", ha=ha,
                    bbox=LABEL_BOX, annotation_clip=False)

    _, n_pre = mean(r["pre"] for r in rows)
    _, n_dur = mean(r["during"] for r in rows)
    printed = PRINTED_AVERAGES[table]
    titles(fig, title,
           f"{len(shown)} rows from {SOURCE}, {table}, {order}.\nDashed lines are the "
           f"unweighted means of the rows: {average[0]:g}% prepregnancy (n={n_pre}) and "
           f"{average[1]:g}% during pregnancy (n={n_dur}).\nThe book prints these averages as "
           f"{printed[0]:g}% and {printed[1]:g}%.", top=1 - 0.35 / height)
    fig.legend(handles=[
        Line2D([], [], marker="o", linestyle="", markersize=8, markerfacecolor=PRE_COLOUR,
               markeredgecolor=SURFACE, label="Prepregnancy"),
        Line2D([], [], marker="o", linestyle="", markersize=8, markerfacecolor=DURING_COLOUR,
               markeredgecolor=SURFACE, label="During pregnancy"),
    ], loc="upper left", bbox_to_anchor=(0.025, 1 - 1.25 / height), ncol=2, frameon=False,
        fontsize=9.5, labelcolor=INK_2, handletextpad=0.2, columnspacing=1.2)

    if notes:
        fig.text(0.03, 0.25 / height, note_text, ha="left", va="bottom", fontsize=8,
                 color=MUTED)
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {out_path}")


def short_site(site):
    """Scatter label: city only for US and Canadian sites ("Seattle")."""
    if site.endswith(("(USA)", "(Canada)", "(national)")):
        return site.split(",")[0].replace(" (USA)", "").replace(" (national)", "")
    return site.replace("London (UK), ", "London, ")


# Label positions (data coordinates: during %, before %) for crowded points; a leader line joins
# each label to its dot. Unlisted points are labelled just to their right.
SCATTER_LABELS = {
    # (site, reference): (label x = during %, label y = before %, alignment)
    ("Dundee (UK)", "Sulaiman et al., 1988"): (50, 94, "right"),
    ("London (UK), European ethnic group", "Waterson & Murray-Lyon, 1989"): (62, 92, "left"),
    ("London (UK)", "Waterson & Murray-Lyon, 1989"): (50, 88.5, "right"),
    ("London (UK)", "Grisso et al., 1984"): (62, 82.5, "left"),
    ("Southampton (UK)", "Primatesta et al., 1993"): (59, 75.5, "left"),
    ("Netherlands", "Ogston & Parry, 1992"): (50, 76, "right"),
    ("Valencia (Spain)", "Bolumar et al., 1994"): (56, 69.5, "left"),
    ("Guipuzcoa (Spain)", "Ogston & Parry, 1992"): (40.5, 71, "right"),
    ("Sydney (Australia)", "Kesby et al., 1991"): (41.5, 79, "right"),
    ("London (UK), Afro-Caribbean ethnic group", "Waterson & Murray-Lyon, 1989"): (29.5, 75, "right"),
    ("Roubaix (France)", "Ogston & Parry, 1992"): (50, 63, "left"),
    ("London (UK), East Asian ethnic group", "Waterson & Murray-Lyon, 1989"): (27.5, 56, "right"),
    ("Jackson, Mississippi (USA)", "Stephens, 1985"): (26.5, 52.5, "right"),
    ("London (UK), South Asian ethnic group", "Waterson & Murray-Lyon, 1989"): (20.5, 42, "left"),
    ("Milan (Italy)", "Primatesta et al., 1993"): (76.5, 78.5, "right"),
    ("Ottawa, Ontario (Canada)", "Fried et al., 1980"): (80.5, 94.5, "right"),
}


def scatter_both(rows_2, avg_2, rows_3, avg_3):
    groups = {"Table 11.2": rows_2, "Table 11.3": rows_3}
    fig = plt.figure(figsize=(11, 10.5), facecolor=SURFACE)
    ax = fig.add_axes([0.08, 0.1, 0.86, 0.76])
    style_axes(ax)

    ax.plot([0, 100], [0, 100], color=AXIS, linewidth=1.2, zorder=1)
    ax.annotate("No change (before = during)", (18, 18), rotation=45, rotation_mode="anchor",
                xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8.5,
                color=MUTED)

    counts = {}
    for table, rows in groups.items():
        both = [r for r in rows if r["pre"] is not None and r["during"] is not None]
        counts[table] = len(both)
        for r in both:
            ax.scatter(r["during"], r["pre"], s=60, color=TABLE_COLOURS[table],
                       edgecolor=SURFACE, linewidth=2, zorder=3)
            place = SCATTER_LABELS.get((r["site"], r["reference"]))
            if place:
                x, y, ha = place
                ax.plot([r["during"], x], [r["pre"], y], color=AXIS, linewidth=0.8, zorder=1)
                ax.annotate(short_site(r["site"]), (x, y), ha=ha, va="center", fontsize=8,
                            color=INK_2, bbox=LABEL_BOX, zorder=4)
            else:
                ax.annotate(short_site(r["site"]), (r["during"], r["pre"]), xytext=(7, 0),
                            textcoords="offset points", va="center", fontsize=8,
                            color=INK_2, bbox=LABEL_BOX, zorder=4)

    for table, (pre, during) in (("Table 11.2", avg_2), ("Table 11.3", avg_3)):
        ax.scatter(during, pre, s=90, marker="D", facecolor=SURFACE,
                   edgecolor=TABLE_COLOURS[table], linewidth=2, zorder=5)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks(range(0, 101, 10))
    ax.set_yticks(range(0, 101, 10))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Percent who drink during pregnancy", color=INK_2, fontsize=10)
    ax.set_ylabel("Percent who drink before pregnancy", color=INK_2, fontsize=10)

    handles = [Line2D([], [], marker="o", linestyle="", markersize=8, markerfacecolor=c,
                      markeredgecolor=SURFACE, label=name)
               for name, c in (("Other countries (Table 11.2)", TABLE_COLOURS["Table 11.2"]),
                               ("US and Canada (Table 11.3)", TABLE_COLOURS["Table 11.3"]))]
    handles.append(Line2D([], [], marker="D", linestyle="", markersize=8,
                          markerfacecolor=SURFACE, markeredgecolor=INK_2,
                          label="Table average"))
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=9.5,
              labelcolor=INK_2, handletextpad=0.3)

    titles(fig, "Drinking before pregnancy vs. during pregnancy",
           f"{counts['Table 11.2'] + counts['Table 11.3']} rows from {SOURCE}, Tables 11.2 "
           f"({counts['Table 11.2']}) and 11.3 ({counts['Table 11.3']}) that give both "
           "percentages. Points above the diagonal are studies where\nfewer women drank during "
           "pregnancy than before it.", top=0.965)
    fig.text(0.03, 0.025, "Diamonds: each table's average (recomputed), taken over all rows "
             "including those with only one percentage.", ha="left", fontsize=8, color=MUTED)
    fig.savefig(OUT_BOTH, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_BOTH}")


def main():
    rows_2, avg_2 = load_11_2()
    rows_3, avg_3 = load_11_3()
    dumbbell(rows_2, avg_2, "Table 11.2",
             "Women who drink before and during early pregnancy, outside the US and Canada",
             OUT_11_2, sort_by_during=True)
    dumbbell(rows_3, avg_3, "Table 11.3",
             "Women who drink before and during pregnancy, US and Canada", OUT_11_3,
             sort_by_during=True)
    scatter_both(rows_2, avg_2, rows_3, avg_3)


if __name__ == "__main__":
    main()
