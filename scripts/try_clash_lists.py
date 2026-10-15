"""Try the AI half of the clash check on made-up medicine lists with known answers. Saves nothing; sends only the medicine names to the model.

  python scripts/try_clash_lists.py

Each list says what a careful pharmacist would be expected to flag. A line starting with "MISS" means the model did not flag a known clash,
"EXTRA" means it flagged a pair that was not expected (not necessarily wrong, but worth a look).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from download_data import load_env  # noqa: E402

load_env()

from app.agents import clash_checker as ck  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.llm.vertex import VertexClient  # noqa: E402

# (label, medicines as (name, strength, kind), the pairs a careful pharmacist would flag, by name)
CASES = [
    ("warfarin and aspirin", [("Warfarin", "3 mg", "prescription"), ("Aspirin", "100 mg", "otc"), ("Metformin", "500 mg", "prescription")], {("Warfarin", "Aspirin")}),
    ("simvastatin and clarithromycin", [("Simvastatin", "20 mg", "prescription"), ("Clarithromycin", "500 mg", "prescription"), ("Amlodipine", "5 mg", "prescription")],
     {("Simvastatin", "Clarithromycin")}),
    ("a plain diabetes list", [("Metformin", "500 mg", "prescription"), ("Amlodipine", "5 mg", "prescription"), ("Atorvastatin", "20 mg", "prescription")], set()),
    ("herbal with a drug", [("Warfarin", "3 mg", "prescription"), ("Ginkgo biloba", None, "supplement"), ("Metformin", "500 mg", "prescription")], {("Warfarin", "Ginkgo biloba")}),
    ("brand name", [("CRESTOR", "10 mg", "prescription"), ("Gemfibrozil", "600 mg", "prescription"), ("Metformin", "500 mg", "prescription")], {("CRESTOR", "Gemfibrozil")}),
    ("unreadable product", [("Herbal tonic (label not readable)", None, "tcm"), ("Metformin", "500 mg", "prescription")], set()),
    ("nothing to compare", [("Fish oil", None, "supplement"), ("Vitamin D3", None, "supplement"), ("Paracetamol", "500 mg", "otc")], set()),
]


def main() -> None:
    s = get_settings()
    client = VertexClient(s.google_api_key.get_secret_value(), s.google_cloud_project, s.google_cloud_region)
    for label, items, expected in CASES:
        meds = [ck.Medicine(str(i), n, st, k) for i, (n, st, k) in enumerate(items)]
        name = {m.id: m.name for m in meds}
        out = ck.check(client, model=s.llm_vision_model, meds=meds)
        got = {frozenset((name[p.a], name[p.b])) for p in out.pairs}
        want = {frozenset(e) for e in expected}
        print(f"\n== {label}: AI {out.status}{' (' + out.reason + ')' if out.reason else ''}, {len(out.pairs)} flagged, sources {[x.title for x in out.sources][:4]}")
        for p in out.pairs:
            print(f"   {name[p.a]} + {name[p.b]}: {p.summary}")
        for w in want - got:
            print("   MISS", sorted(w))
        for g in got - want:
            print("   EXTRA", sorted(g))
        if got == want:
            print("   as expected")


if __name__ == "__main__":
    main()
