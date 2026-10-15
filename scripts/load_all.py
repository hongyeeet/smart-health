#!/usr/bin/env python3
"""Run every E1-4 loader in dependency order and report how many rows each inserted (E1-4).

Safe to run any time: the first run loads everything, every later run must insert 0 rows (that is the
"imports are safe to run twice" check). Does NOT call the openFDA service: run `python scripts/fetch_openfda.py --run`
first if data/raw/openfda is missing. The medicine knowledge index (ingest_knowledge.py) waits for the AI gateway (E0-3).
Usage: python scripts/load_all.py [--verify]
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["seed_data_sources.py", "import_nhanes_priors.py", "seed_reference.py", "import_cgmacros.py", "import_bigideas.py",
         "import_fitbit_kaggle.py", "seed_demo.py"]


def main():
    total = 0
    for s in STEPS:
        p = subprocess.run([sys.executable, "-u", str(HERE / s)], capture_output=True, text=True, encoding="utf-8")
        if p.returncode:
            print(f"FAILED {s}\n{p.stdout[-800:]}\n{p.stderr[-1500:]}")
            sys.exit(1)
        inserted = sum(int(x.replace(",", "")) for x in re.findall(r"inserted[= ]([\d,]+)", p.stdout))
        total += inserted
        print(f"{s:<26} inserted {inserted:>9,} rows")
    print(f"\ntotal inserted this run: {total:,}" + ("   (a repeat run: nothing new, as expected)" if total == 0 else ""))
    if "--verify" in sys.argv:
        sys.exit(subprocess.call([sys.executable, str(HERE / "verify_loaded.py")]))


if __name__ == "__main__":
    main()
