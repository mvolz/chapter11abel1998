"""Chart FAS incidence per 1,000 births in prospective studies (Abel 1998, Table 11.1).

Writes one image to output/charts/: each study's FAS rate per 1,000 births
with an exact (Clopper-Pearson) 95% confidence interval, grouped by country,
with the pooled rate across all studies.

Reads the corrected "Table 11.1.csv" (rates recomputed from cases / births).
Places come from the City column of "Table 11.4.csv" (Table 11.1 prints only
countries outside the US); "?" marks an unverified place.

Usage: python3 table_11_1_chart.py   (reads the CSVs in data/)
"""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

import fas_rates_chart as fas

from paths import CHARTS, DATA
CSV_PATH = DATA / "Table 11.1.csv"
CITIES_PATH = DATA / "Table 11.4.csv"
OUT_BY_STUDY = CHARTS / "Table 11.1 - FAS rate per 1,000 births by study.png"

SURFACE, INK, INK_2, MUTED, GRID, AXIS = (fas.SURFACE, fas.INK, fas.INK_2, fas.MUTED,
                                          fas.GRID, fas.AXIS)


def exact_ci(cases, n):
    """Clopper-Pearson 95% interval for cases / n, per 1,000."""
    lo = stats.beta.ppf(0.025, cases, n - cases + 1) if cases else 0.0
    hi = stats.beta.ppf(0.975, cases + 1, n - cases)
    return 1000 * lo, 1000 * hi


def load_places():
    """(country, study) -> list of places, in table order (Spain's EUROMAC rows repeat)."""
    places = {}
    with open(CITIES_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Study (source)"]:
                places.setdefault((r["Country"], r["Study (source)"]), []).append(r["City"])
    return places


def load_studies():
    places = load_places()
    studies = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["Study (source)"]:
                continue  # summary rows
            country = r["Country"]
            found = places.get((country, r["Study (source)"]), [])
            place = found.pop(0) if found else r["City"]
            cases, n = int(r["Number of FAS cases"]), int(r["Sample size"])
            studies.append({
                "country": country,
                "place": place or "",
                "study": r["Study (source)"],
                "cases": cases,
                "n": n,
                "rate": 1000 * cases / n,
                "ci": exact_ci(cases, n),
            })
    return studies


def chart_by_study(studies):
    cases = sum(s["cases"] for s in studies)
    births = sum(s["n"] for s in studies)
    pooled = 1000 * cases / births

    rows = []  # (label, study or None for a country heading)
    for country in fas.COUNTRY_ORDER:
        group = [s for s in studies if s["country"] == country]
        if not group:
            continue
        rows.append((country, None))
        for s in sorted(group, key=lambda s: -s["rate"]):
            label = f'{s["place"]}: {s["study"]}' if s["place"] else s["study"]
            rows.append((label, s))

    fig = plt.figure(figsize=(11, 13.5), facecolor=SURFACE)
    ax = fig.add_axes([0.36, 0.06, 0.6, 0.83])
    fas.style_axes(ax)

    ys = np.arange(len(rows))[::-1]
    for y, (_, s) in zip(ys, rows):
        if s is None:
            ax.axhline(y + 0.5, color=GRID, linewidth=0.8)
            continue
        c = fas.colour(s["country"])
        ax.plot(s["ci"], [y, y], color=c, alpha=0.45, linewidth=2.5,
                solid_capstyle="round", zorder=2)
        ax.scatter(s["rate"], y, s=55, color=c, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.annotate(f'{s["cases"]}/{s["n"]:,}', (s["ci"][1], y), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=7.5, color=MUTED,
                    bbox=fas.LABEL_BOX, zorder=4)

    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    for tick, (_, s) in zip(ax.get_yticklabels(), rows):
        if s is None:
            tick.set_fontweight("bold")
            tick.set_color(INK)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlim(0, 15.5)
    ax.grid(axis="y", visible=False)

    ax.axvline(pooled, color=INK_2, linestyle=(0, (4, 3)), linewidth=1.2, zorder=1)
    ax.annotate(f"Pooled rate {pooled:.2f}", (pooled, len(rows) - 0.6), xytext=(5, 0),
                textcoords="offset points", fontsize=8.5, color=INK_2, va="top",
                bbox=fas.LABEL_BOX)
    ax.set_xlabel("Estimated FAS incidence per 1,000 births (dot) with exact 95% CI (bar)",
                  color=INK_2, fontsize=10)

    fas.titles(fig, "FAS incidence per 1,000 births in prospective studies, by study",
               f"{len(studies)} studies from Abel (1998), Table 11.1. Pooled rate = {cases} cases / "
               f"{births:,} births = {pooled:.2f} per 1,000. Grey numbers: FAS cases / births.\n"
               "Studies with 0 cases still have an upper bound: small samples cannot rule out "
               "rates of several per 1,000.\nPlaces from Table 11.4.csv; '?' = unverified.")
    fig.savefig(OUT_BY_STUDY, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_BY_STUDY}")
    return cases, births, pooled



def main():
    studies = load_studies()
    cases, births, pooled = chart_by_study(studies)
    print(f"Pooled: {cases}/{births} = {pooled:.3f} per 1,000")


if __name__ == "__main__":
    main()
