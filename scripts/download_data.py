#!/usr/bin/env python3
"""Download the allowed datasets into data/raw (gitignored) and log sizes and checksums.

Only the sources listed in SOURCES are fetched (rules.md 1b, data/README.md): the manifest
datasets used by E1-1, plus GlucoBench. Originals are never edited: a file that is already
present with the right size is skipped, so a second run changes nothing.

Usage:
  python scripts/download_data.py                      show the plan (no download)
  python scripts/download_data.py --batch nhanes --run download one batch
  python scripts/download_data.py --verify             re-check files against the log

Batches: nhanes, cgmacros, bigideas, kaggle. The Kaggle batch needs KAGGLE_API_TOKEN in the
private .env file (never printed, never committed).
"""
import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
LOG = ROOT / "data" / "download_log.csv"
NHANES_LIST = ROOT / "data" / "plan" / "nhanes_files.csv"
UA = {"User-Agent": "Mozilla/5.0 (smart-health data download)"}
LOG_FIELDS = ["dataset", "manifest_no", "file", "bytes", "sha256", "source_url", "licence", "downloaded_at"]

PHYSIONET = "https://physionet-open.s3.amazonaws.com"  # PhysioNet's official S3 mirror: much faster than physionet.org/files from here; same files, checked against SHA256SUMS.txt
CGMACROS_FILES = [
    "CGMacros_dateshifted365.zip", "DataDictionary.pdf", "DataDictionary_Bio.csv",
    "DataDictionary_CGMacros-00X.csv", "DataDictionary_Gut_Health_Test.csv",
    "DataDictionary_Microbes.csv", "LICENSE.txt", "SHA256SUMS.txt",
]
# BIG IDEAs: per participant only these files. ACC (about 0.9 GB) and BVP (about 1.4 GB) are not needed.
BIGIDEAS_PER_PERSON = ["Dexcom", "EDA", "Food_Log", "HR", "IBI", "TEMP"]
BIGIDEAS_COMMON = ["Demographics.csv", "LICENSE.txt", "SHA256SUMS.txt"]

KAGGLE = [  # (dataset, manifest no, slug, licence)
    ("Fitbit", "14", "arashnic/fitbit", "CC0: Public Domain"),
    ("250k Medicines", "20", "shudhanshusingh/250k-medicines-usage-side-effects-and-substitutes", "CC BY-SA 4.0"),
    ("Open Food Facts", "17", "openfoodfacts/world-food-facts", "Database Contents License (DbCL 1.0)"),
    ("Doctor Specialty", "37", "ebrahimelgazar/doctor-specialist-recommendation-system", "CC BY-SA 4.0"),
    ("GlucoBench", "", "omenkj/glucobench-glucose-monitoring-and-lifestyle-data", "Apache 2.0 (fixture only, source not cited)"),
]
LICENCES = {
    "NHANES": "US public domain (CDC data user agreement)",
    "CGMacros": "CC BY-NC-SA 4.0",
    "BIG IDEAs": "Open Data Commons Attribution License v1.0",
}


def load_env():
    """Read KEY=VALUE lines from the repo's .env into os.environ (never prints values)."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_size(url):
    r = requests.head(url, headers=UA, allow_redirects=True, timeout=60)
    return int(r.headers["Content-Length"]) if r.ok and "Content-Length" in r.headers else None


def fetch(url, dest, tries=10):
    """Download url to dest, retrying dropped connections (the partial file is resumed)."""
    for attempt in range(1, tries + 1):  # 10 tries: the servers drop long downloads now and then
        try:
            return _fetch_once(url, dest)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as e:
            if attempt == tries:
                raise
            wait = 5 * attempt
            print(f"  connection problem ({type(e).__name__}), retry {attempt}/{tries - 1} in {wait}s: {dest.name}")
            time.sleep(wait)


def _fetch_once(url, dest):
    """Download url to dest with resume. Skips a file that is already complete."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = remote_size(url)
    if dest.exists() and total is not None and dest.stat().st_size == total:
        return "skipped"
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = dict(UA)
    if have:
        headers["Range"] = f"bytes={have}-"
    with requests.get(url, headers=headers, stream=True, timeout=120) as r:
        if r.status_code == 416:  # already complete
            part.rename(dest)
            return "downloaded"
        r.raise_for_status()
        mode = "ab" if have and r.status_code == 206 else "wb"
        with open(part, mode) as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    part.replace(dest)
    return "downloaded"


def read_log():
    if not LOG.exists():
        return {}
    with open(LOG, newline="", encoding="utf-8") as f:
        return {r["file"]: r for r in csv.DictReader(f)}


def write_log(rows):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])


def record(rows, dataset, no, path, url, licence):
    rel = path.relative_to(ROOT).as_posix()
    rows[rel] = {
        "dataset": dataset, "manifest_no": no, "file": rel, "bytes": path.stat().st_size,
        "sha256": sha256(path), "source_url": url, "licence": licence,
        "downloaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    }


def verify_sums(folder, sums_name="SHA256SUMS.txt"):
    """Compare downloaded files with the publisher's checksum file. Returns (ok, bad)."""
    sums = folder / sums_name
    ok = bad = 0
    if not sums.exists():
        return ok, bad
    for line in sums.read_text(encoding="utf-8").splitlines():
        m = re.match(r"([0-9a-f]{64})\s+\*?(.+)$", line.strip())
        if not m:
            continue
        f = folder / m.group(2)
        if f.exists():
            if sha256(f) == m.group(1):
                ok += 1
            else:
                bad += 1
                print(f"  CHECKSUM MISMATCH: {f}")
    return ok, bad


def plan_nhanes():
    rows = list(csv.DictReader(open(NHANES_LIST, encoding="utf-8")))
    return [(r["manifest_no"], r["cycle"], r["file_code"], r["xpt_url"]) for r in rows if r["allowed"] == "yes"]


def batch_nhanes(run, log):
    items = plan_nhanes()
    print(f"NHANES: {len(items)} files (every file marked allowed in data/plan/nhanes_files.csv) -> data/raw/nhanes/<cycle>/")
    if not run:
        return
    for no, cyc, code, url in items:
        dest = RAW / "nhanes" / cyc / f"{code}.xpt"
        status = fetch(url, dest)
        record(log, f"NHANES {cyc}", no, dest, url, LICENCES["NHANES"])
        print(f"  {status}: {cyc}/{code}.xpt ({dest.stat().st_size:,} bytes)")


def batch_cgmacros(run, log):
    base = f"{PHYSIONET}/cgmacros/1.0.0"
    print(f"CGMacros 1.0.0: {len(CGMACROS_FILES)} files (zip is about 657 MB) -> data/raw/cgmacros/")
    if not run:
        return
    folder = RAW / "cgmacros"
    for name in CGMACROS_FILES:
        dest = folder / name
        status = fetch(f"{base}/{name}", dest)
        record(log, "CGMacros", "5", dest, f"{base}/{name}", LICENCES["CGMacros"])
        print(f"  {status}: {name} ({dest.stat().st_size:,} bytes)")
    ok, bad = verify_sums(folder)
    print(f"  publisher checksums: {ok} match, {bad} mismatch")


def batch_bigideas(run, log, people):
    # The S3 mirror stops at version 1.1.2. The data files for the chosen people are byte-identical
    # in 1.1.3 (checked against both SHA256SUMS lists; only Food_Log of 007, 013, 015, 016 differ),
    # so data comes from the fast mirror and is verified against 1.1.3's checksums from physionet.org.
    mirror = f"{PHYSIONET}/big-ideas-glycemic-wearable/1.1.2"
    official = "https://physionet.org/files/big-ideas-glycemic-wearable/1.1.3"
    files = [("Demographics.csv", mirror)]
    for p in people:
        if p in ("007", "013", "015", "016"):
            sys.exit(f"Participant {p}: Food_Log differs between 1.1.2 and 1.1.3. Choose another participant.")
        files += [(f"{p}/{k}_{p}.csv", mirror) for k in BIGIDEAS_PER_PERSON]
    files += [("LICENSE.txt", official), ("SHA256SUMS.txt", official)]
    print(f"BIG IDEAs 1.1.3 data: participants {', '.join(people) or '(none chosen)'}; {len(files)} files")
    if not run:
        return
    folder = RAW / "big-ideas"
    for name, base in files:
        dest = folder / name
        status = fetch(f"{base}/{name}", dest)
        record(log, "BIG IDEAs", "4", dest, f"{base}/{name}", LICENCES["BIG IDEAs"])
        print(f"  {status}: {name} ({dest.stat().st_size:,} bytes)")
    ok, bad = verify_sums(folder)
    print(f"  publisher checksums (1.1.3): {ok} match, {bad} mismatch")


def batch_kaggle(run, log):
    print("Kaggle: " + ", ".join(k[0] for k in KAGGLE) + " -> data/raw/<name>/")
    if not run:
        return
    if not os.environ.get("KAGGLE_API_TOKEN"):
        sys.exit("KAGGLE_API_TOKEN is not set. Put it in the private .env file (see .env.example).")
    for name, no, slug, licence in KAGGLE:
        folder = RAW / slug.split("/")[1]
        if folder.exists() and any(folder.iterdir()):
            print(f"  skipped: {name} (folder already has files)")
        else:
            folder.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "kaggle", "datasets", "download", "-d", slug,
                            "--unzip", "-p", str(folder)], check=True)
            print(f"  downloaded: {name}")
        for f in sorted(p for p in folder.rglob("*") if p.is_file()):
            record(log, name, no, f, f"https://www.kaggle.com/datasets/{slug}", licence)


def verify_all():
    rows = read_log()
    bad = 0
    for rel, r in rows.items():
        p = ROOT / rel
        if not p.exists() or sha256(p) != r["sha256"]:
            bad += 1
            print(f"  CHANGED OR MISSING: {rel}")
    print(f"{len(rows)} files in the log, {bad} problems")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", choices=["nhanes", "cgmacros", "bigideas", "kaggle", "all"], default="all")
    ap.add_argument("--run", action="store_true", help="actually download (without it, only show the plan)")
    ap.add_argument("--people", default="", help="BIG IDEAs participant ids, e.g. 001,004,007")
    ap.add_argument("--verify", action="store_true", help="re-check files against the log and exit")
    a = ap.parse_args()
    load_env()
    if a.verify:
        sys.exit(1 if verify_all() else 0)
    people = [p.strip() for p in a.people.split(",") if p.strip()]
    log = read_log()
    t = time.time()
    try:  # the log is saved even if a batch fails, so finished files are never forgotten
        if a.batch in ("nhanes", "all"):
            batch_nhanes(a.run, log)
        if a.batch in ("cgmacros", "all"):
            batch_cgmacros(a.run, log)
        if a.batch in ("bigideas", "all"):
            batch_bigideas(a.run, log, people)
        if a.batch in ("kaggle", "all"):
            batch_kaggle(a.run, log)
    finally:
        if a.run:
            write_log(log)
            print(f"Log written to {LOG.relative_to(ROOT)} ({time.time() - t:.0f}s)")
    if not a.run:
        print("\nNothing downloaded. Add --run to download.")


if __name__ == "__main__":
    main()
