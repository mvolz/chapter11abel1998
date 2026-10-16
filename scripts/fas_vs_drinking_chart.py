"""Pooled FAS incidence vs. drinking during pregnancy, by region (Abel 1998,
Tables 11.1, 11.2 and 11.3).

Only studies that have BOTH a during-pregnancy drinking rate (Table 11.2 or
11.3) and an FAS count with births (Table 11.1) are used. Each study is linked
by citation; a few links join the same site/cohort published under different
citations - these are flagged "extended" and the analysis is shown both with
and without them.

For each region:
  - FAS incidence = all FAS cases / all births (exact 95% CI);
  - drinking rate = births-weighted mean of the studies' during-pregnancy %.

Writes "Table 11.1-11.3 - FAS vs drinking during pregnancy.csv" (the matched
studies) and a chart PNG of the same name.

Usage: python3 fas_vs_drinking_chart.py
"""
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from matplotlib.lines import Line2D

import drinking_rates_chart as drc
import fas_rates_chart as fas
import table_11_1_chart as t11

from paths import CHARTS, TABLES
STEM = "Table 11.1-11.3 - FAS vs drinking during pregnancy"
OUT_CSV, OUT_PNG = TABLES / f"{STEM}.csv", CHARTS / f"{STEM}.png"

REGION_COLOURS = {"Europe": "#4a3aa7", "North America": "#1baf7a", "Australia": "#eb6834"}

# Table 11.1 study -> (Table 11.2/11.3 site, reference, link type, note).
# "exact": same citation. "extended": same site or cohort, different citation.
LINKS = {
    ("Australia", "Bell & Lumley, 1989"): ("Melbourne (Australia)", "Bell & Lumley, 1989", "exact", ""),
    ("Australia", "Lumley et al., 1985"): ("Tasmania (Australia)", "Lumley et al., 1985", "exact", ""),
    ("Denmark", "Ogston & Parry, 1992"): ("Odense (Denmark)", "Ogston & Parry, 1992", "exact",
                                          "Sample selected for drinking (Bolumar 1992)"),
    ("Germany", "Ogston & Parry, 1992"): ("Berlin (Germany)", "Ogston & Parry, 1992", "exact",
                                          "Verified against Ogston & Parry 1992 (not swapped)"),
    ("Italy", "Primatesta et al., 1993"): ("Milan (Italy)", "Primatesta et al., 1993", "exact", ""),
    ("Portugal", "Ogston & Parry, 1992"): ("Porto (Portugal)", "Ogston & Parry, 1992", "exact", ""),
    ("Spain", "Bolumar et al., 1994"): ("Valencia (Spain)", "Bolumar et al., 1994", "exact", ""),
    ("United Kingdom", "Waterson & Murray-Lyon, 1989"): ("London (UK)", "Waterson & Murray-Lyon, 1989",
                                                         "exact", "Overall London figure (88/56)"),
    ("United Kingdom", "Primatesta et al., 1993"): ("Southampton (UK)", "Primatesta et al., 1993", "exact", ""),
    ("United Kingdom", "Sulaiman et al., 1988"): ("Dundee (UK)", "Sulaiman et al., 1988", "exact", ""),
    ("United States", "Hingson et al., 1982"): ("Boston, Massachusetts (USA)", "Hingson et al., 1982", "exact", ""),
    ("United States", "Ouellette et al., 1977"): ("Boston, Massachusetts (USA)", "Ouellette et al., 1977", "exact", ""),
    ("United States", "Tennes & Blackard, 1980"): ("Denver, Colorado (USA)", "Tennes & Blackard, 1980", "exact", ""),
    ("United States", "Cornelius et al., 1994"): ("Pittsburgh, Pennsylvania (USA)", "Cornelius et al., 1994", "exact", ""),
    # Same site / cohort, different citation:
    ("United States", "Sokol et al., 1993"): ("Detroit, Michigan (USA)", "Sokol et al., 1989", "extended",
                                              "Same Detroit (Hutzel) cohort; drinking from Sokol 1989"),
    ("Netherlands", "Verkerk et al., 1993"): ("Netherlands", "Ogston & Parry, 1992", "extended",
                                              "Same 3,447-woman national survey (Bolumar 1992); drinking from Ogston & Parry"),
    ("France", "Rostand et al., 1990"): ("Roubaix (France)", "Ogston & Parry, 1992", "extended",
                                         "Same Roubaix maternity hospital, INSERM, 1985-86; drinking from Ogston & Parry"),
}
# Table 11.1's two Spanish EUROMAC rows are told apart by sample size: Ogston &
# Parry (1992, Tables 6-7) give 866 women for Vizcaya and 793 for Guipuzcoa.
SPAIN_BY_BIRTHS = {866: "Vizcaya (Spain)", 793: "Guipuzcoa (Spain)"}


def region_of(country):
    if country in ("United States", "Canada"):
        return "North America"
    return "Australia" if country == "Australia" else "Europe"


def matched_studies():
    studies = t11.load_studies()
    rows_2, _ = drc.load_11_2()
    rows_3, _ = drc.load_11_3()
    during = {(r["site"], r["reference"]): r["during"] for r in rows_2 + rows_3
              if r["during"] is not None}

    out = []
    for s in studies:
        key = (s["country"], s["study"])
        if s["country"] == "Spain" and s["study"] == "Ogston & Parry, 1992":
            site, ref, link = SPAIN_BY_BIRTHS[s["n"]], "Ogston & Parry, 1992", "exact"
            rate, note = during[(site, ref)], "Centre identified by sample size (Ogston & Parry 1992)"
            s = {**s, "place": site.split(" (")[0]}
        elif key in LINKS:
            site, ref, link, note = LINKS[key]
            rate = during[(site, ref)]
        else:
            continue
        out.append({**s, "region": region_of(s["country"]), "during": rate, "link": link,
                    "drink_site": site, "drink_ref": ref, "note": note})
    return studies, out


def pool(group):
    cases, births = sum(s["cases"] for s in group), sum(s["n"] for s in group)
    drink = sum(s["during"] * s["n"] for s in group) / births
    return {"cases": cases, "births": births, "studies": len(group), "drink": drink,
            "rate": 1000 * cases / births, "ci": t11.exact_ci(cases, births)}


def fit(group):
    """Births-weighted linear fit of FAS per 1,000 on drinking %, plus a Poisson model of
    cases with log(births) offset (rate ratio per 10 percentage points of drinking)."""
    x = np.array([s["during"] for s in group])
    y = np.array([s["rate"] for s in group])
    w = np.array([s["n"] for s in group], float)
    X = sm.add_constant(x)
    wls = sm.WLS(y, X, weights=w).fit()
    pois = sm.GLM(np.array([s["cases"] for s in group]), X, family=sm.families.Poisson(),
                  offset=np.log(w)).fit()
    b, (lo, hi) = pois.params[1], pois.conf_int()[1]
    return {"n": len(group), "x": x, "intercept": wls.params[0], "slope": wls.params[1],
            "slope_ci": wls.conf_int()[1], "p": wls.pvalues[1],
            "rr10": np.exp(10 * b), "rr10_ci": (np.exp(10 * lo), np.exp(10 * hi)),
            "p_pois": pois.pvalues[1]}


def write_csv(matched):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Region", "Country", "Place", "FAS study (Table 11.1)", "FAS cases", "Births",
                    "FAS per 1,000", "Drinking during pregnancy %", "Drinking source (Table 11.2/11.3)",
                    "Link", "Note"])
        for s in sorted(matched, key=lambda s: (s["region"], s["country"], s["study"])):
            w.writerow([s["region"], s["country"], s["place"], s["study"], s["cases"], s["n"],
                        f'{s["rate"]:.2f}', f'{s["during"]:g}', f'{s["drink_site"]}: {s["drink_ref"]}',
                        s["link"], s["note"]])
    print(f"Saved {OUT_CSV}")


def chart(matched, all_studies):
    fig = plt.figure(figsize=(12.5, 9.5), facecolor=fas.SURFACE)
    ax = fig.add_axes([0.08, 0.36, 0.58, 0.47])
    fas.style_axes(ax)

    # Individual matched studies: dot area proportional to births.
    for st in matched:
        c = REGION_COLOURS[st["region"]]
        ax.scatter(st["during"], st["rate"], s=12 + st["n"] / 60, color=c, alpha=0.35,
                   edgecolor=c, linewidth=0.8, zorder=2)
    # Label the studies with cases; offsets keep them clear of the pooled markers.
    offsets = {"Detroit": (-10, 8, "right"), "Boston": (8, 6, "left")}
    for st in matched:
        if st["cases"]:
            dx, dy, ha = offsets.get(st["place"], (8, 6, "left"))
            if st["study"].startswith("Hingson"):
                dx, dy, ha = (-8, -12, "left")
            ax.annotate(f'{st["place"]} {st["study"].split(",")[1].strip()} ({st["cases"]}/{st["n"]:,})',
                        (st["during"], st["rate"]), xytext=(dx, dy), textcoords="offset points",
                        ha=ha, fontsize=7.5, color=fas.MUTED, bbox=fas.LABEL_BOX, zorder=6)

    # Pooled regions.
    summary = []
    for region, c in REGION_COLOURS.items():
        for link_set, filled in ((("exact",), False), (("exact", "extended"), True)):
            group = [st for st in matched if st["region"] == region and st["link"] in link_set]
            p = pool(group)
            summary.append((region, filled, p))
            ax.plot([p["drink"]] * 2, p["ci"], color=c, linewidth=3, alpha=0.8,
                    solid_capstyle="round", zorder=3)
            ax.scatter(p["drink"], p["rate"], s=110, marker="D" if filled else "o",
                       facecolor=c if filled else fas.SURFACE, edgecolor=c, linewidth=2, zorder=5)

    fits = []
    for label, link_set, style in (("All 19 matched studies", ("exact", "extended"), "-"),
                                   ("Exact matches only (16)", ("exact",), (0, (5, 3)))):
        f = fit([st for st in matched if st["link"] in link_set])
        xx = np.array([f["x"].min(), f["x"].max()])
        ax.plot(xx, f["intercept"] + f["slope"] * xx, color=fas.INK, linestyle=style,
                linewidth=1.8, zorder=4)
        fits.append((label, style, f))

    ax.set_xlim(30, 95)
    ax.set_ylim(-0.25, 4.6)
    ax.axhline(0, color=fas.AXIS, linewidth=0.8, zorder=1)
    ax.set_xlabel("Drinking during pregnancy (% of women)", color=fas.INK_2, fontsize=10)
    ax.set_ylabel("FAS per 1,000 births", color=fas.INK_2, fontsize=10)

    handles = [Line2D([], [], marker="s", linestyle="", markersize=9, markerfacecolor=c,
                      markeredgecolor=c, label=name) for name, c in REGION_COLOURS.items()]
    handles += [Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor="none",
                       markeredgecolor=fas.INK_2, alpha=0.6, label="Single study (area = births)"),
                Line2D([], [], marker="o", linestyle="", markersize=9, markerfacecolor=fas.SURFACE,
                       markeredgecolor=fas.INK_2, markeredgewidth=2, label="Region pooled: exact matches"),
                Line2D([], [], marker="D", linestyle="", markersize=9, markerfacecolor=fas.INK_2,
                       markeredgecolor=fas.INK_2, label="Region pooled: + same-site links")]
    handles += [Line2D([], [], color=fas.INK, linestyle=style, linewidth=1.8,
                       label=f"Fit: {label.lower()}") for label, style, _ in fits]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False,
              fontsize=9, labelcolor=fas.INK_2)

    # Results table under the chart.
    rows = ["Region          Links            Studies  Drinking   FAS per 1,000 (95% CI)   Cases / births"]
    for region, filled, p in summary:
        rows.append(f'{region:15} {"+ same-site" if filled else "exact only":16} {p["studies"]:4}     '
                    f'{p["drink"]:5.1f}%     {p["rate"]:.2f} ({p["ci"][0]:.2f}–{p["ci"][1]:.2f})'
                    f'{"":10}{p["cases"]} / {p["births"]:,}')
    rows.append("")
    for label, _, f in fits:
        rows.append(f'Fit, {label.lower()}: {f["slope"]:+.3f} FAS per 1,000 per point of drinking '
                    f'(95% CI {f["slope_ci"][0]:+.3f} to {f["slope_ci"][1]:+.3f}, '
                    f'{"p<0.001" if f["p"] < 0.001 else f"p={f[chr(112)]:.2f}"})')
        rows.append(f'    Poisson rate ratio per +10 points of drinking: {f["rr10"]:.2f} '
                    f'(95% CI {f["rr10_ci"][0]:.2f}–{f["rr10_ci"][1]:.2f}, '
                    f'{"p<0.001" if f["p_pois"] < 0.001 else "p=%.2f" % f["p_pois"]})')
    fig.text(0.08, 0.27, "\n".join(rows), ha="left", va="top", fontsize=8.5, color=fas.INK_2,
             family="DejaVu Sans Mono", linespacing=1.4)

    n_exact = sum(st["link"] == "exact" for st in matched)
    fig.suptitle("FAS incidence vs. drinking during pregnancy, pooled by region",
                 x=0.03, y=0.97, ha="left", fontsize=15, fontweight="bold", color=fas.INK)
    fig.text(0.03, 0.93,
             f"The {len(matched)} of {len(all_studies)} Table 11.1 studies that also report a "
             "during-pregnancy drinking rate (Tables 11.2/11.3).\nPooled FAS = all cases / all births; "
             f"drinking = births-weighted mean. Exact matches: same citation ({n_exact} studies). "
             "Same-site links add Detroit\n(Sokol 1993 FAS with Sokol 1989 drinking), the Netherlands "
             "(Verkerk) and Roubaix (Rostand). Bars: exact 95% CIs.",
             ha="left", va="top", fontsize=9.5, color=fas.INK_2)
    fig.text(0.03, 0.012,
             "Drinking = any drinking during pregnancy, not heavy drinking. No matching drinking rate: "
             "Sweden, Switzerland, Canada; Cleveland (Sokol 1980, 1986), Kuzma & Sokol, Rosett, Day, "
             "Hanson, Little;\nGibson, Walpole; Wright, Plant. Spain's two EUROMAC rows are matched to Vizcaya and "
             "Guipuzcoa by sample size. Odense's sample was selected for drinking; its rate is the "
             "corrected 78% (Abel printed 68%).",
             ha="left", fontsize=8, color=fas.MUTED)
    fig.savefig(OUT_PNG, dpi=150, facecolor=fas.SURFACE)
    plt.close(fig)
    print(f"Saved {OUT_PNG}")
    for label, _, f in fits:
        print(f'{label}: slope {f["slope"]:+.4f}/pp ({f["slope_ci"][0]:+.4f} to {f["slope_ci"][1]:+.4f}), '
              f'p={f["p"]:.4f}; Poisson RR/10pp {f["rr10"]:.2f} ({f["rr10_ci"][0]:.2f}-{f["rr10_ci"][1]:.2f}), '
              f'p={f["p_pois"]:.3g}')
    return [(r, "exact + extended" if f else "exact only", p) for r, f, p in summary]


def main():
    all_studies, matched = matched_studies()
    write_csv(matched)
    for region, version, p in chart(matched, all_studies):
        print(f'{region:14} {version:17} n={p["studies"]:2}  drink {p["drink"]:5.1f}%  '
              f'FAS {p["cases"]:2}/{p["births"]:6} = {p["rate"]:.2f} ({p["ci"][0]:.2f}-{p["ci"][1]:.2f})')


if __name__ == "__main__":
    main()
