#!/usr/bin/env python3
"""Fetch the openFDA drug label for each drug in data/processed/nhanes_top_drugs.csv (E1-4 step 3).

openFDA is public domain (CC0 1.0). The raw answer for each drug is saved untouched in data/raw/openfda/<drug>.json
(the Bronze original); data/raw/openfda/_index.csv summarises what was found. Nothing is written to the database here.

Choosing the label for a drug: single-ingredient prescription labels whose generic name contains the drug name and
that have a drug_interactions section; the most recently revised one wins. Combination products are never used.
Polite use: about 3 requests a second (the limit without a key is 240 a minute, 1,000 a day). A re-run skips drugs
already saved.

Usage:
  python scripts/fetch_openfda.py            show the plan (no network)
  python scripts/fetch_openfda.py --run      fetch
"""
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import PROCESSED, RAW  # noqa: E402
import download_data  # noqa: E402

OUT = RAW / "openfda"
API = "https://api.fda.gov/drug/label.json"
UA = {"User-Agent": "smart-health data load (E1-4)"}


def safe(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def single_ingredient(r, drug):
    names = [n.lower() for n in r.get("openfda", {}).get("generic_name", [])]
    if len(names) != 1 or any(x in names[0] for x in (" and ", ",", ";", "/", " with ")):
        return False
    return drug.split()[0] in names[0]


def pick(results, drug):
    ok = [r for r in results if single_ingredient(r, drug) and r.get("drug_interactions")
          and "HUMAN PRESCRIPTION DRUG" in r.get("openfda", {}).get("product_type", [])]
    if not ok:
        ok = [r for r in results if single_ingredient(r, drug) and r.get("drug_interactions")]
    return max(ok, key=lambda r: r.get("effective_time", "0")) if ok else None


def get(url):
    for attempt in range(5):
        try:
            r = requests.get(url, headers=UA, timeout=45)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"openFDA did not answer for {url}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    drugs = [r["generic_name"] for r in csv.DictReader(open(PROCESSED / "nhanes_top_drugs.csv", encoding="utf-8"))]
    print(f"{len(drugs)} drugs; one search request each (limit 25 labels), saved to data/raw/openfda/")
    if not a.run:
        print("Nothing fetched. Add --run to fetch.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for i, drug in enumerate(drugs, 1):
        path = OUT / f"{safe(drug)}.json"
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            index.append((drug, saved.get("_status"), saved.get("id"), saved.get("_label_generic"), saved.get("_url")))
            continue
        url = f'{API}?search={quote("openfda.generic_name:" + chr(34) + drug + chr(34))}&limit=25'
        data = get(url)
        label = pick(data["results"], drug) if data else None
        if label is None:
            record = {"_status": "not_found", "_url": url, "_drug": drug}
        else:
            record = dict(label)
            record.update({"_status": "found", "_url": url, "_drug": drug, "_label_generic": label["openfda"]["generic_name"][0]})
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        index.append((drug, record["_status"], record.get("id"), record.get("_label_generic"), url))
        print(f"  [{i}/{len(drugs)}] {drug}: {record['_status']}")
        time.sleep(0.35)
    with open(OUT / "_index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["drug", "status", "label_id", "label_generic_name", "url"])
        w.writerows(index)
    log = download_data.read_log()      # the raw answers are originals too: log size and checksum
    for p in sorted(OUT.glob("*")):
        download_data.record(log, "openFDA drug labels", "", p.resolve(), API, "CC0 1.0 Universal (public domain)")
    download_data.write_log(log)
    found = sum(1 for x in index if x[1] == "found")
    print(f"done: {found} labels found, {len(index) - found} not found. Index: data/raw/openfda/_index.csv")


if __name__ == "__main__":
    main()
