#!/usr/bin/env python3
"""Make the reviewer sheet for the lighter-dish suggestions (docs/specs/learning-loop.md 12.6, target: 85% judged reasonable).

For every distinct dish Mr Tan logged, the loop is run the way the app runs it: his own logged average for the dish is the baseline, the
food database is searched for lighter dishes, code compares them and JEV checks they are reasonable substitutes. Each suggestion becomes a
row for a person (a teammate, a dietitian or a clinician) to rate: reasonable, not reasonable, or unsafe.

Usage:  python scripts/make_review_sheet.py             (Mr Tan's dishes; a few minutes; writes docs/review/swap_review_sheet.csv)
        python scripts/make_review_sheet.py --extra 40   (appends typical high-load hawker dishes as stand-in "usual dishes", so the sample
                                                          reaches about 50; their baseline is the published serving, marked in the sheet)
Then:   python scripts/score_review_sheet.py       (reads the ratings back and reports the share judged reasonable)
"""
import csv
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

MR_TAN = uuid.UUID("dc48e209-5731-5b3d-89d9-986242c54368")


def extra(n: int) -> None:
    """Append suggestions for typical heavy hawker dishes, each treated as if a person had logged it at the published serving."""
    from app.agents import food
    from app.db.logstore import tx
    from app.db import nutritionstore as ns

    out = ROOT / "docs" / "review" / "swap_review_sheet.csv"
    existing = list(csv.reader(out.open(encoding="utf-8-sig")))
    next_id = len(existing)  # header counts as one
    with tx() as c:
        rows = c.execute(
            f"select {food._COLS} from foods where source=%s and 'hawker' = any(flags) and category in ('Grains and staples','Mixed','Poultry','Snacks') "
            "and (kcal >= 550 or sodium_mg >= 1200) and carbs_g is not null and protein_g is not null and fat_g is not null "
            "order by md5(name) limit %s", (food.SOURCE, n * 2)).fetchall()
    added = 0
    with out.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        for r in rows:
            if added >= n:
                break
            row = food._row(r)
            base = {k: row.n.get(k) for k in ("carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg")}
            base["kcal"] = food.kcal_from(base)
            alts = food.better_alternatives(row.name, base, limit=2)
            if alts:
                added += 1
            for a in alts:
                to = {c["nutrient"]: c["to"] for c in a["changes"]}
                w.writerow([f"S{next_id:03d}", f"{row.name} (typical serving)", "", base["kcal"], base["protein_g"], base["carbs_g"], base["sodium_mg"], a["name"], a["serving"],
                            to.get("kcal"), to.get("protein_g"), to.get("carbs_g"), to.get("sodium_mg"), ns.saving_phrase(a), a["fit"], "", ""])
                next_id += 1
            print(f"{row.name[:50]:50s} -> {len(alts)} suggestion(s)", flush=True)
    print(f"\nappended suggestions for {added} dishes; the sheet now has {next_id - 1} rows")


def main():
    if "--extra" in sys.argv:
        return extra(int(sys.argv[sys.argv.index("--extra") + 1]))
    from app.agents import food
    from app.db.logstore import tx
    from app.db import nutritionstore as ns

    with tx() as c:
        rows = c.execute(
            """select min(food) food, count(*) n, avg(carbs_g) carbs_g, avg(protein_g) protein_g, avg(fat_g) fat_g, avg(sugar_g) sugar_g,
                      avg(fibre_g) fibre_g, avg(sodium_mg) sodium_mg
               from food_logs where user_id=%s and deleted_at is null and carbs_g is not null and protein_g is not null and fat_g is not null
               group by lower(food) order by count(*) desc""",
            (MR_TAN,),
        ).fetchall()
    out = ROOT / "docs" / "review" / "swap_review_sheet.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    n_rows, n_dishes = 0, 0
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "usual_dish", "times_logged", "logged_kcal", "logged_protein_g", "logged_carbs_g", "logged_salt_mg", "suggested_dish", "suggested_serving",
                    "suggested_kcal", "suggested_protein_g", "suggested_carbs_g", "suggested_salt_mg", "what_it_changes", "jev_fit", "RATING (reasonable / not reasonable / unsafe)", "reviewer_comment"])
        for r in rows:
            base = ns._logged_baseline([r])
            alts = food.better_alternatives(r["food"], base, limit=3)
            if alts:
                n_dishes += 1
            for a in alts:
                to = {c["nutrient"]: c["to"] for c in a["changes"]}
                n_rows += 1
                w.writerow([f"S{n_rows:03d}", r["food"], r["n"], base["kcal"], base["protein_g"], base["carbs_g"], base["sodium_mg"], a["name"], a["serving"],
                            to.get("kcal"), to.get("protein_g"), to.get("carbs_g"), to.get("sodium_mg"), ns.saving_phrase(a), a["fit"], "", ""])
            print(f"{r['food'][:50]:50s} -> {len(alts)} suggestion(s)", flush=True)
    print(f"\n{n_rows} suggestions for {n_dishes} of {len(rows)} dishes written to {out}")


if __name__ == "__main__":
    main()
