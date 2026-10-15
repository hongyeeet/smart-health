#!/usr/bin/env python3
"""Medicine knowledge index (backlog task E1-6; chunking was done in E1-4): chunk the medicine text, embed it, prove 20 test names find the right drug.

Stages (the last two need the AI gateway from backlog task E0-3, which does not exist yet):
  --stage   (default; reads the database but writes nothing)  build data/processed/knowledge_chunks_staging.jsonl from
            250k Medicines (uses, classes, side effects of each drug's single-ingredient products) and the openFDA label
            (indications and patient information), and data/demo/knowledge_test_names.csv (20 test names)
  --embed   embed every chunk with the gateway and insert knowledge_chunks (embedding vectors of size EMBED_DIM)
  --test    embed each test name, find the nearest chunk by cosine distance and check it belongs to the expected drug

The gateway must provide: embed(texts: list[str]) -> list[list[float]] with len(vector) == EMBED_DIM. Until E0-3 provides it,
--embed and --test stop with a clear message. Substitute columns are never read. Drug facts are general information,
not medical advice, and are cited to their source document (knowledge_documents).
Usage: python scripts/ingest_knowledge.py [--stage | --embed | --test]
"""
import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_common import DEMO_DIR, PROCESSED, RAW, bulk_insert, connect, count, uid  # noqa: E402
from seed_reference import load_drug_list, load_labels  # noqa: E402

STAGING = PROCESSED / "knowledge_chunks_staging.jsonl"
TESTS = DEMO_DIR / "knowledge_test_names.csv"
SHARE = 0.30
MAX_CHARS = 900
USE_COLS = [f"use{i}" for i in range(5)]
SIDE_COLS = [f"sideEffect{i}" for i in range(42)]
CLASS_COLS = ["Chemical Class", "Therapeutic Class", "Action Class", "Habit Forming"]
MISSPELLINGS = {"metformin": "metformn", "atorvastatin": "atorvastatine", "amlodipine": "amlodipin", "lisinopril": "lisinopirl", "simvastatin": "simvastatn"}


def split_text(text, limit=MAX_CHARS):
    parts, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip()):
        if len(cur) + len(sent) + 1 > limit and cur:
            parts.append(cur)
            cur = ""
        cur = (cur + " " + sent).strip()
    return parts + ([cur] if cur else [])


def stage():
    drugs, labels = load_drug_list(), None
    labels = load_labels(drugs)
    generics = [d["generic_name"] for d in drugs]
    pattern = re.compile(r"\b(" + "|".join(re.escape(g) for g in sorted(generics, key=len, reverse=True)) + r")\b")
    df = pd.read_csv(RAW / "250k-medicines-usage-side-effects-and-substitutes" / "medicine_dataset.csv", usecols=["name"] + USE_COLS + SIDE_COLS + CLASS_COLS, low_memory=False)
    names = df["name"].fillna("").str.lower()
    single = defaultdict(list)
    for idx, nm in enumerate(names):
        if "+" not in nm:
            hit = set(pattern.findall(nm))
            if len(hit) == 1:
                single[hit.pop()].append(idx)
    chunks = []
    for d in drugs:
        g = d["generic_name"]
        lab = labels[g]
        doc = str(uid("knowledge_document", g)) if lab.get("_status") == "found" else None
        rows = single.get(g, [])
        seq = 0

        def add(text, source):
            nonlocal seq
            for piece in split_text(text):
                chunks.append({"drug": g, "document_id": doc, "seq": seq, "locale": "en", "content": piece, "tokens": max(1, len(piece) // 4), "source": source})
                seq += 1
        if rows:
            def common(cols):
                c = Counter()
                for idx in rows:
                    for v in set(df.loc[idx, cols].dropna().astype(str).str.strip()):
                        if v:
                            c[v] += 1
                need = max(1, math.ceil(SHARE * len(rows)))
                return [v for v, n in c.most_common() if n >= need]
            uses, effects = common(USE_COLS), common(SIDE_COLS)
            classes = [f"{c.lower()}: {df.loc[rows[0], c]}" for c in CLASS_COLS if pd.notna(df.loc[rows[0], c])]
            if uses:
                add(f"{g.title()} is listed for: {'; '.join(uses)}." + (f" Classes ({'; '.join(classes)})." if classes else ""), "250k Medicines")
            if effects:
                add(f"Common side effects listed for {g}: {', '.join(effects)}.", "250k Medicines")
        if lab.get("_status") == "found":
            for field in ("indications_and_usage", "information_for_patients"):
                if lab.get(field):
                    add(" ".join(lab[field]), "openFDA drug labels")
    STAGING.parent.mkdir(parents=True, exist_ok=True)
    STAGING.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n", encoding="utf-8")
    print(f"staged {len(chunks):,} chunks for {len({c['drug'] for c in chunks})} drugs -> {STAGING.relative_to(PROCESSED.parent.parent)}")
    write_test_names(drugs, labels)


def write_test_names(drugs, labels):
    """20 test names: 8 generic names, 7 brand or product names, 5 common misspellings. Expected drug for each."""
    have = {c["drug"] for c in map(json.loads, STAGING.read_text(encoding="utf-8").splitlines() if STAGING.exists() else [])}
    gen = [d["generic_name"] for d in drugs if d["generic_name"] in have]
    rows = [(g, g, "generic") for g in ["metformin", "atorvastatin", "amlodipine", "lisinopril", "glipizide", "losartan", "simvastatin", "metoprolol"] if g in have]
    brands, used = [], {r[1] for r in rows}
    with connect() as conn:    # read-only: real brand names (openFDA) that differ from the generic, then 250k product names
        for alias, g in conn.execute("""select a.alias, d.generic_name from drug_aliases a join drug_reference d on d.id = a.drug_reference_id
                                        where a.kind = 'brand' and a.source = 'openFDA drug labels' and position(split_part(d.generic_name, ' ', 1) in lower(a.alias)) = 0
                                        order by d.generic_name, a.alias""").fetchall():
            if g in gen and g not in used and len(brands) < 4:
                brands.append((alias.title(), g, "brand (openFDA)"))
                used.add(g)
        for alias, g in conn.execute("""select a.alias, d.generic_name from drug_aliases a join drug_reference d on d.id = a.drug_reference_id
                                        where a.source = '250k Medicines' order by d.generic_name, a.alias""").fetchall():
            if g in gen and g not in used and len(brands) < 7:
                brands.append((alias, g, "product name (250k Medicines)"))
                used.add(g)
    rows += brands[:7] + [(m, g, "misspelling") for g, m in MISSPELLINGS.items() if g in have]
    rows = rows[:20]
    with open(TESTS, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["query", "expected_drug", "kind"])
        w.writerows(rows)
    print(f"wrote {len(rows)} test names -> {TESTS.relative_to(PROCESSED.parent.parent)}" + ("" if len(rows) == 20 else "  (fewer than 20: check staging)"))


def need_gateway():
    try:
        from app.llm.gateway import embed  # noqa: F401  (built in E0-3)
    except Exception:
        raise SystemExit("The AI gateway (backlog task E0-3) does not exist yet, so nothing can be embedded. "
                         "Run --stage now; run --embed and --test after E0-3 provides embed(texts) -> vectors of size EMBED_DIM.")
    return embed


def embed_all():
    embed = need_gateway()
    chunks = [json.loads(x) for x in STAGING.read_text(encoding="utf-8").splitlines() if x.strip()]
    with connect() as conn:
        for i in range(0, len(chunks), 64):
            batch = chunks[i:i + 64]
            vecs = embed([c["content"] for c in batch])
            rows = [(uid("chunk", c["drug"], c["seq"], c["source"]), c["document_id"], c["seq"], c["content"], c["locale"], "[" + ",".join(f"{x:.6f}" for x in v) + "]", c["tokens"]) for c, v in zip(batch, vecs) if c["document_id"]]
            bulk_insert(conn, "knowledge_chunks", ["id", "document_id", "seq", "content", "locale", "embedding", "tokens"], rows)
            conn.commit()
        print("knowledge_chunks:", count(conn, "knowledge_chunks"))


def test_names():
    embed = need_gateway()
    rows = list(csv.DictReader(open(TESTS, encoding="utf-8")))
    vecs = embed([r["query"] for r in rows])
    ok = 0
    with connect() as conn:
        for r, v in zip(rows, vecs):
            top = conn.execute("""select d.generic_name from knowledge_chunks k join knowledge_documents kd on kd.id = k.document_id
                                  join drug_reference d on d.knowledge_doc_id = kd.id order by k.embedding <=> %s::extensions.vector limit 1""", ("[" + ",".join(f"{x:.6f}" for x in v) + "]",)).fetchone()
            hit = top and top[0] == r["expected_drug"]
            ok += bool(hit)
            print(f"{'PASS' if hit else 'FAIL'}  {r['query']:<28} -> {top[0] if top else None} (expected {r['expected_drug']})")
    print(f"{ok} of {len(rows)} test names found the right drug")
    sys.exit(0 if ok == len(rows) else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("--embed", action="store_true")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    if a.embed:
        embed_all()
    elif a.test:
        test_names()
    else:
        stage()


if __name__ == "__main__":
    main()
