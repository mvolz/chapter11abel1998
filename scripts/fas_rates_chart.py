"""Chart FAS incidence per 1,000 heavy drinkers by study (Abel 1998, Table 11.4).

Writes two images to output/charts/:
  1. Rate by study: every study's rate, grouped under country headings.
  2. Rate vs. the percentage of heavy drinkers in each study, with two
     linear trend lines: one fitted to all studies that give a percentage
     and one excluding studies that reported zero cases. The rate is Abel's
     estimate: ALL FAS cases in the study divided by its estimated number of
     heavy drinkers (heavy-drinker % x sample size). It is a study-level
     ratio, not a rate observed in heavy-drinking women followed individually,
     and the trends across studies are an ecological comparison.

Every country gets its own colour. Dots are labelled with the place name.

The book's printed total of 3,761 heavy drinkers does not match its own
column (which sums to 3,712), so the summary rows are ignored and the
pooled rate is recomputed from the study rows.

Usage: python3 fas_rates_chart.py   (reads data/Table 11.4.csv)
"""
import csv
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy import stats

from paths import CHARTS, DATA
CSV_PATH = DATA / "Table 11.4.csv"
OUT_BY_STUDY = CHARTS / "Table 11.4 - FAS rate by study.png"
OUT_BY_HEAVY = CHARTS / "Table 11.4 - FAS rate by heavy drinkers with trends.png"

# Chart chrome (light mode).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
# Surface-coloured box so labels stay readable over reference and trend lines.
LABEL_BOX = dict(boxstyle="square,pad=0.1", facecolor=SURFACE, edgecolor="none")

# The five countries with non-zero rates come first, in colours that stay
# distinguishable for colour-blind readers. The countries that only report
# zeros follow; every dot is also labelled with its place name.
COUNTRY_COLOURS = {
    "United States": "#2a78d6",
    "Finland": "#eb6834",
    "Sweden": "#4a3aa7",
    "France": "#1baf7a",
    "Hungary": "#8a5a2b",
    "Denmark": "#e87ba4",
    "United Kingdom": "#e34948",
    "Germany": "#eda100",
    "Italy": "#008300",
    "Netherlands": "#17becf",
    "Portugal": "#a3a300",
    "Spain": "#9085e9",
    "Switzerland": "#5c6f82",
    "Canada": "#7a2048",
    "Australia": "#b5b3ab",
}
COUNTRY_ORDER = ["United States", "Canada", "Finland", "Sweden", "Denmark",
                 "United Kingdom", "France", "Germany", "Hungary", "Italy",
                 "Netherlands", "Portugal", "Spain", "Switzerland", "Australia"]
SHORT_NAME = {"United States": "US", "United Kingdom": "UK"}


def colour(country):
    return COUNTRY_COLOURS[country]


def load_studies(csv_path=CSV_PATH):
    studies = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Country"] not in COUNTRY_ORDER:
                continue  # summary rows (TOTAL, rates) - not used
            year = int(re.search(r"(\d{4})", row["Study (source)"]).group(1))
            n = row["Number of heavy drinkers"]
            pct = row["Heavy drinkers (%)"]
            # One study gives a range ("13.0-19.0"); use its midpoint.
            bounds = [float(v) for v in pct.split("-")] if pct else []
            country = row["Country"]
            studies.append({
                "country": country,
                "place": row["City"] or SHORT_NAME.get(country, country),
                "study": row["Study (source)"],
                "year": year,
                "heavy": int(n) if n else None,
                "heavy_pct": float(np.mean(bounds)) if bounds else None,
                "cases": int(row["Number of FAS cases"]),
                "rate": float(row["Estimated incidence per 1,000"]),
            })
    return studies


def pooled_rate(studies):
    cases = sum(s["cases"] for s in studies)
    heavy = sum(s["heavy"] for s in studies if s["heavy"])
    return cases, heavy, 1000 * cases / heavy


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def country_handles(studies):
    present = {s["country"] for s in studies}
    return [Line2D([], [], marker="o", linestyle="", markersize=8,
                   markerfacecolor=c, markeredgecolor=SURFACE,
                   label=SHORT_NAME.get(name, name))
            for name, c in COUNTRY_COLOURS.items() if name in present]


def titles(fig, title, subtitle):
    fig.suptitle(title, x=0.03, y=0.975, ha="left", fontsize=15, fontweight="bold", color=INK)
    fig.text(0.03, 0.948, subtitle, ha="left", va="top", fontsize=9.5, color=INK_2)


def chart_by_study(studies):
    cases, heavy, pooled = pooled_rate(studies)
    rows = []  # (label, study or None for a country heading)
    for country in COUNTRY_ORDER:
        group = sorted((s for s in studies if s["country"] == country),
                       key=lambda s: (s["place"], s["year"]))
        if not group:
            continue
        rows.append((country, None))
        for s in group:
            label = f'{s["place"]}: {s["study"]}' if s["place"] != SHORT_NAME.get(
                country, country) else s["study"]
            rows.append((label, s))

    fig = plt.figure(figsize=(10, 14), facecolor=SURFACE)
    ax = fig.add_axes([0.33, 0.05, 0.62, 0.82])
    style_axes(ax)

    ys = np.arange(len(rows))[::-1]
    for y, (_, s) in zip(ys, rows):
        if s is None:
            ax.axhline(y + 0.5, color=GRID, linewidth=0.8)
            continue
        ax.plot([0, s["rate"]], [y, y], color=GRID, linewidth=2, zorder=1)
        ax.scatter(s["rate"], y, s=60, color=colour(s["country"]), edgecolor=SURFACE,
                   linewidth=2, zorder=3)
        ax.annotate(f'{s["rate"]:g}', (s["rate"], y), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color=INK_2,
                    bbox=LABEL_BOX, zorder=4)

    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows])
    for tick, (_, s) in zip(ax.get_yticklabels(), rows):
        if s is None:
            tick.set_fontweight("bold")
            tick.set_color(INK)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlim(0, 370)
    ax.grid(axis="y", visible=False)

    ax.axvline(pooled, color=INK_2, linestyle=(0, (4, 3)), linewidth=1.2, zorder=2)
    ax.annotate(f"Pooled rate {pooled:.1f}", (pooled, len(rows) - 0.6),
                xytext=(5, 0), textcoords="offset points", fontsize=8.5, color=INK_2,
                va="top", bbox=LABEL_BOX)
    ax.set_xlabel("Estimated FAS incidence per 1,000 heavy drinkers\n"
                  "(all FAS cases in the study / its estimated number of heavy drinkers)",
                  color=INK_2, fontsize=10)

    titles(fig, "Estimated FAS incidence per 1,000 heavy drinkers, by study",
           f"{len(studies)} studies from Abel (1998), Table 11.4. Each rate is all FAS cases in the "
           "study divided by its estimated number of heavy drinkers\n(Abel's study-level estimate; "
           "not a rate observed in heavy-drinking women followed individually). Pooled rate = "
           f"{cases} cases /\n{heavy:,} estimated heavy drinkers = {pooled:.1f} per 1,000 "
           "(recomputed; the book's printed total of 3,761 does not match its column).")
    fig.legend(handles=country_handles(studies), loc="upper left", bbox_to_anchor=(0.025, 0.905),
               ncol=8, frameon=False, fontsize=9, labelcolor=INK_2, handletextpad=0.2,
               columnspacing=1.0)
    fig.savefig(OUT_BY_STUDY, dpi=150, facecolor=SURFACE)
    print(f"Saved {OUT_BY_STUDY}")


# Label offsets (points) for the non-zero studies, tuned to avoid overlaps.
LABEL_OFFSETS = {
    "Sokol et al., 1980": (0, 11, "center"),
    "Hingson et al., 1982": (8, -6),
    "Sokol et al., 1986": (-8, 0, "right"),
    "Hanson et al., 1978": (-8, 0, "right"),
}


def spread_labels(xs, gap):
    """Return label positions near xs, at least gap apart, centred on each cluster."""
    order = np.argsort(xs, kind="stable")
    clusters = [[i] for i in order]
    merged = True
    while merged:
        merged = False
        out = [clusters[0]]
        for c in clusters[1:]:
            prev = out[-1]
            prev_end = np.mean([xs[i] for i in prev]) + (len(prev) - 1) * gap / 2
            start = np.mean([xs[i] for i in c]) - (len(c) - 1) * gap / 2
            if start - prev_end < gap:
                out[-1] = prev + c
                merged = True
            else:
                out.append(c)
        clusters = out
    pos = np.empty(len(xs))
    for c in clusters:
        centre = np.mean([xs[i] for i in c])
        for k, i in enumerate(c):
            pos[i] = centre + (k - (len(c) - 1) / 2) * gap
    return pos


def chart_by_heavy(studies, out_path=OUT_BY_HEAVY,
                   place_note="Dots show where each study was done:\nthe city, or the state "
                              "where a study covered a whole state; the country where unknown; "
                              "'?' = unverified (see 'Table 11.4 - study locations.csv')."):
    plotted = [s for s in studies if s["heavy_pct"] is not None]
    missing = [s for s in studies if s["heavy_pct"] is None]

    fig = plt.figure(figsize=(14, 10), facecolor=SURFACE)
    ax = fig.add_axes([0.08, 0.15, 0.74, 0.72])
    style_axes(ax)

    for s in plotted:
        x = s["heavy_pct"]
        ax.scatter(x, s["rate"], s=60, color=colour(s["country"]),
                   edgecolor=SURFACE, linewidth=2, zorder=3)
        if s["rate"] > 0:
            dx, dy, *ha = LABEL_OFFSETS.get(s["study"], (8, 0))
            ax.annotate(f'{s["place"]} ({s["rate"]:g})', (x, s["rate"]),
                        xytext=(dx, dy), textcoords="offset points",
                        ha=ha[0] if ha else "left", va="center", fontsize=8.5,
                        color=INK_2, bbox=LABEL_BOX, zorder=4)

    # Zero-rate studies pile up at low percentages, so their labels are fanned
    # out below the zero line with a leader line back to each dot.
    zeros = sorted((s for s in plotted if s["rate"] == 0), key=lambda s: s["heavy_pct"])
    label_x = spread_labels([s["heavy_pct"] for s in zeros], gap=0.42)
    for s, lx in zip(zeros, label_x):
        ax.plot([s["heavy_pct"], lx], [-1.5, -9], color=AXIS, linewidth=0.8, zorder=1)
        ax.annotate(s["place"], (lx, -10), rotation=90, ha="center", va="top",
                    fontsize=7.5, color=INK_2)

    fits = []
    for subset, style, name in (
        (plotted, "-", "All studies with a heavy-drinker %"),
        ([s for s in plotted if s["rate"] > 0], (0, (5, 3)), "Excluding zero-case studies"),
    ):
        x = np.array([s["heavy_pct"] for s in subset])
        y = np.array([s["rate"] for s in subset])
        r = stats.linregress(x, y)
        xx = np.array([x.min(), x.max()])
        ax.plot(xx, r.slope * xx + r.intercept, color=INK, linestyle=style, linewidth=2, zorder=2)
        fits.append((name, style, len(subset), r))

    ax.set_xlim(-2.5, 38)
    ax.set_xticks(range(0, 37, 5))
    ax.set_ylim(-26, 82)
    ax.set_yticks(range(0, 81, 10))
    ax.axhline(0, color=AXIS, linewidth=1, zorder=1)
    ax.set_xlabel("Percent of pregnant women in the study who drank heavily", color=INK_2,
                  fontsize=10)
    ax.set_ylabel("Estimated FAS incidence per 1,000 heavy drinkers\n(all FAS cases in the study "
                  "/ its estimated number of heavy drinkers)", color=INK_2, fontsize=10)

    def signed(v):
        return f"{'+' if v >= 0 else '\u2212'}{abs(v):.2f}"

    trend_handles = []
    for name, style, n, r in fits:
        half = stats.t.ppf(0.975, n - 2) * r.stderr
        trend_handles.append(Line2D([], [], color=INK, linestyle=style, linewidth=2, label=(
            f"{name} (n={n}): slope {signed(r.slope)} per 1,000 per percentage point "
            f"(95% CI {signed(r.slope - half)} to {signed(r.slope + half)}), p={r.pvalue:.2f}")))
    ax.legend(handles=trend_handles, loc="upper right", frameon=False, fontsize=9,
              labelcolor=INK_2, handlelength=3)
    fig.legend(handles=country_handles(plotted), loc="upper left",
               bbox_to_anchor=(0.835, 0.87), frameon=False, fontsize=9.5,
               labelcolor=INK_2, handletextpad=0.3, title="Country",
               title_fontproperties={"size": 10, "weight": "bold"}, alignment="left")

    n_zero = sum(s["rate"] == 0 for s in plotted)
    titles(fig, "Estimated FAS incidence per 1,000 heavy drinkers vs. percent drinking heavily "
           "in pregnancy, across studies",
           f"{len(plotted)} of {len(studies)} studies from Abel (1998), Table 11.4; "
           f"{n_zero} of these reported no cases. Each dot is one study. y: all FAS cases in the "
           "study divided by its estimated number of heavy drinkers (Abel's estimate;\nnot a rate "
           "observed in heavy-drinking women followed individually). x: the share of the study's "
           "pregnant women who drank heavily. The trends relate these study-level\nfigures to each "
           "other - an ecological comparison - and do not link any woman's own drinking to her own "
           f"outcome. {place_note}")
    left_out = "; ".join(f'{s["place"]} ({s["study"]}, rate {s["rate"]:g})' for s in missing)
    fig.text(0.03, 0.022,
             f"Not shown: {len(missing)} studies that give no heavy-drinker percentage — "
             f"{left_out}.\nCornelius et al., 1994 (Pittsburgh) gives a range of 13–19%; it is "
             "plotted at the midpoint (16%), and the fits use 16%.\n"
             "Linear least-squares fits across studies (ecological); with so few studies and "
             "many zeros the trends are descriptive only.",
             ha="left", fontsize=8, color=MUTED, wrap=True)
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    print(f"Saved {out_path}")
    return fits


def main():
    studies = load_studies()
    chart_by_study(studies)
    fits = chart_by_heavy(studies)
    for name, _, n, r in fits:
        print(f"{name}: n={n}, slope={r.slope:.2f}/pp, intercept={r.intercept:.1f}, "
              f"R2={r.rvalue ** 2:.3f}, p={r.pvalue:.3f}")
    cases, heavy, pooled = pooled_rate(studies)
    print(f"Pooled: {cases}/{heavy} = {pooled:.2f} per 1,000")


if __name__ == "__main__":
    main()
