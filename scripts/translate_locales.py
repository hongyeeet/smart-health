#!/usr/bin/env python3
"""Fill in the missing Chinese, Malay and Tamil strings of the web app (Joely's request, 2026-10-13).

Usage (from the repository root, after `npm run i18n:extract` in apps/web, which writes en.generated.json):
  python scripts/translate_locales.py --dry-run            count what is missing per language and area, change nothing
  python scripts/translate_locales.py                      translate every missing string (zh, ms, ta) and write the locale files
  python scripts/translate_locales.py --lang zh --limit 40 a small trial for one language

How it works: every key in en.generated.json that has no translation yet is sent to Gemini (gemini-3.8-flash on Vertex) in batches,
with the key path as context and a glossary taken from the translations already written, so the wording stays the same across screens.
Only UI wording is sent: no person's data. A translation is accepted only if it keeps every {{placeholder}} and every <0></0> tag of the
English, is not empty and is not just the English again; a batch that fails is split and retried. The files written are
apps/web/src/i18n/locales/<lang>/<area>.json (the loader picks every file up by name). These are MACHINE translations: they wait for a
native speaker (docs/review/translations.md). English stays the source of truth, and a key with no translation still shows English.
"""
import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.core.settings import get_settings  # noqa: E402
from app.llm.vertex import VertexClient  # noqa: E402

LOCALES = ROOT / "apps" / "web" / "src" / "i18n" / "locales"
MODEL = "gemini-3.8-flash"
BATCH = 40
LANGS = {
    "zh": "Simplified Chinese (as used in Singapore)",
    "ms": "Bahasa Melayu (as used in Singapore and Malaysia)",
    "ta": "Tamil (as used in Singapore)",
}
# which file a key goes to: the three that already exist keep their areas; everything else goes to a new file per area
AREA_FILES = {
    "insights": "insights", "home": "log", "log": "log", "workout": "log", "me": "me",
    "onboarding": "onboarding",
    "addByHand": "meds", "medDetail": "meds", "stock": "meds", "scanReview": "meds", "scanPlan": "meds", "scanFrame": "meds", "scan": "meds",
    "meds": "meds", "refill": "meds",
}
DEFAULT_FILE = "app"

SYSTEM = """You translate the interface text of Smart Health, a companion app for adults with type 2 diabetes in Singapore, many of them older.
Target language: {language}.
Rules:
- Plain, warm, short wording an older adult understands. Use the polite everyday register. No slang.
- Keep every {{{{placeholder}}}} exactly as written (for example {{{{n}}}}) and every numbered tag exactly as written (<0>, </0>, <1>, </1>). Do not translate or reorder the placeholder names.
- Keep numbers, units (kcal, g, mg, mmol/L, kg, min, bpm, %), the emergency number 995, and the product name "Smart Health" as they are. Medicine and food names stay as written.
- Do not add advice, diagnosis or reassurance that is not in the English. Do not soften or strengthen warnings. "associated with" must never become "caused by".
- Text that says the app is not medical advice, or tells the person to see a doctor, must keep that meaning exactly.
- Buttons and labels stay short (a verb or a noun), like the English.
- Use the glossary for these terms so the wording matches the rest of the app.
Return JSON: a list with one item per input, {{"i": the input number, "t": the translation}}."""


def flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, prefix + k + "."))
        else:
            out[prefix + k] = v
    return out


T_CALL = re.compile(r"""\bt\(\s*'([\w.]+)'\s*,\s*('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""")


def scan_sources():
    """Every t('key', 'English') in the web sources. The extractor (npm run i18n:extract) misses some files, so this adds what it missed."""
    out = {}
    for f in (ROOT / "apps" / "web" / "src").rglob("*.ts*"):
        if f.suffix not in (".ts", ".tsx"):
            continue
        for m in T_CALL.finditer(f.read_text(encoding="utf-8")):
            text = m.group(2)[1:-1].replace("\\'", "'").replace('\\"', '"')
            if "${" not in text:
                out.setdefault(m.group(1), text)
    return out


def put(tree, key, value):
    parts = key.split(".")
    for p in parts[:-1]:
        node = tree.get(p)
        if not isinstance(node, dict):
            node = {}
            tree[p] = node
        tree = node
    tree[parts[-1]] = value


def load_existing(lang):
    have = {}
    files = sorted((LOCALES / lang).glob("*.json")) + ([LOCALES / "zh.json"] if lang == "zh" else [])
    for f in files:
        have.update(flat(json.loads(f.read_text(encoding="utf-8"))))
    return have


def file_for(key):
    return AREA_FILES.get(key.split(".")[0], DEFAULT_FILE)


PH = re.compile(r"\{\{\s*[^}]+?\s*\}\}")
TAG = re.compile(r"</?\d+>")


def sig(text):
    return sorted(re.sub(r"\s+", "", m) for m in PH.findall(text)), sorted(TAG.findall(text))


def acceptable(en, tr):
    if not isinstance(tr, str) or not tr.strip():
        return False
    if sig(en) != sig(tr):
        return False
    if tr.strip() == en.strip() and re.search(r"[A-Za-z]{4,}", PH.sub("", TAG.sub("", en))) and not re.fullmatch(r"[\w .,'&/+%()-]{0,24}", en):
        return False                                   # the English again: not translated
    return True


def glossary(lang, have, en):
    """Up to 60 short English/translated pairs already in the app, so terms stay the same."""
    pairs = [(en[k], v) for k, v in have.items() if k in en and isinstance(v, str) and 6 <= len(en[k]) <= 48 and "{{" not in en[k]]
    pairs.sort(key=lambda p: len(p[0]))
    step = max(1, len(pairs) // 60)
    return pairs[::step][:60]


def translate(client, lang, items, gloss):
    """items: list of (key, english). Returns {key: translation} for the ones accepted."""
    system = SYSTEM.format(language=LANGS[lang])
    glossary_text = "\n".join(f"- {a} = {b}" for a, b in gloss)
    lines = "\n".join(f"{i}. [{k}] {e}" for i, (k, e) in enumerate(items))
    prompt = f"Glossary (English = {lang}):\n{glossary_text}\n\nTranslate each numbered string. The text in [brackets] is only the place it appears; do not translate it.\n\n{lines}"
    schema = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"i": {"type": "INTEGER"}, "t": {"type": "STRING"}}, "required": ["i", "t"]}}
    last = None
    for attempt in range(3):
        try:
            res = client.generate_json(model=MODEL, system=system, parts=[prompt], response_schema=schema, max_output_tokens=16000)
            got = {int(x["i"]): x["t"] for x in json.loads(res.text)}
            out = {}
            for i, (k, e) in enumerate(items):
                if i in got and acceptable(e, got[i]):
                    out[k] = got[i].strip()
            return out
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 + attempt * 3)
    print(f"  batch failed ({type(last).__name__}): {str(last)[:100]}", flush=True)
    return {}


def run_lang(client, lang, en, limit, dry):
    have = load_existing(lang)
    missing = [(k, v) for k, v in en.items() if k not in have and isinstance(v, str)]
    by_file = {}
    for k, _ in missing:
        by_file[file_for(k)] = by_file.get(file_for(k), 0) + 1
    print(f"[{lang}] translated {len(en) - len(missing)}, missing {len(missing)}  by file: {by_file}", flush=True)
    if dry or not missing:
        return
    if limit:
        missing = missing[:limit]
    gloss = glossary(lang, have, en)
    batches = [missing[i:i + BATCH] for i in range(0, len(missing), BATCH)]
    done = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n, got in enumerate(pool.map(lambda b: translate(client, lang, b, gloss), batches), 1):
            done.update(got)
            print(f"[{lang}] batch {n}/{len(batches)}: {len(got)} accepted", flush=True)
    # a second pass for what was refused: smaller batches
    retry = [(k, e) for k, e in missing if k not in done]
    if retry:
        small = [retry[i:i + 8] for i in range(0, len(retry), 8)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for got in pool.map(lambda b: translate(client, lang, b, gloss), small):
                done.update(got)
    still = [k for k, _ in missing if k not in done]
    print(f"[{lang}] translated {len(done)} of {len(missing)}; left in English: {len(still)}", flush=True)
    for k in still[:20]:
        print(f"    left: {k}", flush=True)
    # write: each file is read, the new keys are added, and it is written back
    per_file = {}
    for k, v in done.items():
        per_file.setdefault(file_for(k), {})[k] = v
    for name, kv in per_file.items():
        path = LOCALES / lang / f"{name}.json"
        tree = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        for k, v in kv.items():
            put(tree, k, v)
        path.write_text(json.dumps(tree, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[{lang}] wrote {len(kv)} keys to {path.relative_to(ROOT)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=list(LANGS), help="one language (default: all three)")
    ap.add_argument("--limit", type=int, default=0, help="translate only the first N missing strings (a trial)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    en = flat(json.loads((LOCALES / "en.generated.json").read_text(encoding="utf-8")))
    for k, v in scan_sources().items():
        en.setdefault(k, v)
    s = get_settings()
    client = VertexClient(s.google_api_key.get_secret_value(), s.google_cloud_project, s.google_cloud_region)
    for lang in ([args.lang] if args.lang else list(LANGS)):
        run_lang(client, lang, en, args.limit, args.dry_run)


if __name__ == "__main__":
    main()
