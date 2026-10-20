"""Pool Table 11.1 FAS incidence by how each study looked for FAS (Abel 1998).

Reads "Table 11.1 - FAS ascertainment.csv", which classifies each study as
screened (a systematic FAS or dysmorphology examination of the infants), not
screened (FAS left to routine clinical recognition, or infants not examined for
FAS at all) or unverified (paper not yet checked), with the evidence.

Writes "Table 11.1 - pooled by FAS ascertainment.csv": every study with its
class, then pooled rows per class and per class x region, with exact 95% CIs.

Usage: python3 fas_ascertainment_table.py
"""
import csv

import fas_pooled_chart as pooled
import table_11_1_chart as t11

from paths import DATA, TABLES
CLASS_PATH = DATA / "Table 11.1 - FAS ascertainment.csv"
OUT_CSV = TABLES / "Table 11.1 - pooled by FAS ascertainment.csv"

CLASSES = ["Yes", "No", "Unverified"]
CLASS_NAME = {"Yes": "Screened", "No": "Not screened", "Unverified": "Unverified"}


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
    assert not any(classes.values()), "unmatched class rows"
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


def main():
    studies = load()
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
