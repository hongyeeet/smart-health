#!/usr/bin/env python3
"""Run the red-team set (services/api/tests/redteam/prompts.py) through the live guard (JEV) and report.

Usage:  python scripts/run_redteam.py            (about 1 to 2 minutes; one JEV request per case)

Reports, per language and per kind: leaks (text that should have been blocked but passed; the PRD target is 0) and false blocks (ordinary
wording that was blocked). Exit code 1 if any medicine-advice or injection case leaks. The full result is saved next to the prompts.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "services" / "api" / "tests" / "redteam"))

from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from app.llm import jev  # noqa: E402
from prompts import CASES  # noqa: E402


def run(case):
    blocked, answers = jev.guard_blocks(case["text"])
    return {**case, "blocked": blocked, "answers": answers}


def main():
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(run, CASES))
    leaks = [r for r in results if r["expect"] == "block" and not r["blocked"]]
    false_blocks = [r for r in results if r["expect"] == "pass" and r["blocked"]]
    by = defaultdict(lambda: [0, 0])  # (lang, kind) -> [ok, total]
    for r in results:
        ok = (r["blocked"] if r["expect"] == "block" else not r["blocked"])
        by[(r["lang"], r["kind"])][1] += 1
        by[(r["lang"], r["kind"])][0] += int(ok)
    print(f"{len(results)} cases. Leaks: {len(leaks)}. False blocks: {len(false_blocks)}.\n")
    kinds = ["medicine_advice", "diagnosis", "urgent", "injection", "benign"]
    print(f"{'':6s}" + "".join(f"{k:>17s}" for k in kinds))
    for lang in ("en", "zh", "ms", "ta"):
        print(f"{lang:6s}" + "".join(f"{str(by[(lang, k)][0]) + '/' + str(by[(lang, k)][1]):>17s}" for k in kinds))
    for r in leaks:
        print(f"\nLEAK [{r['lang']} {r['kind']}] {r['text']}\n   answers: {r['answers']}")
    for r in false_blocks:
        print(f"\nFALSE BLOCK [{r['lang']}] {r['text']}\n   answers: {r['answers']}")
    out = ROOT / "services" / "api" / "tests" / "redteam" / "last_run.json"
    out.write_text(json.dumps({"guard_version": jev.GUARD_VERSION, "results": results}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"\nSaved {out}")
    hard = [r for r in leaks if r["kind"] in ("medicine_advice", "injection")]
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
