#!/usr/bin/env python3
"""Fill in zh, ms and ta for the server's fixed wording in services/api/app/services/texts_ui.json (Joely's request, 2026-10-13).

Usage (from the repository root):
  python scripts/translate_server_texts.py              translate every entry that has no zh, ms or ta yet and write the file
  python scripts/translate_server_texts.py --dry-run    count only

Each entry is {"en": "...", "zh": "...", "ms": "...", "ta": "..."}; English is the source. The placeholders are Python format fields ({name}); a
translation is accepted only if it has exactly the same fields as the English. Same prompt rules as translate_locales.py (plain wording,
no added advice, numbers, units and 995 unchanged). MACHINE translations: listed for native review in docs/review/translations.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.core.settings import get_settings  # noqa: E402
from app.llm.vertex import VertexClient  # noqa: E402
from translate_locales import LANGS, MODEL, SYSTEM  # noqa: E402

FILE = ROOT / "services" / "api" / "app" / "services" / "texts_ui.json"
FIELD = re.compile(r"\{(\w+)\}")


def fields(text):
    return sorted(FIELD.findall(text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = json.loads(FILE.read_text(encoding="utf-8"))
    s = get_settings()
    client = VertexClient(s.google_api_key.get_secret_value(), s.google_cloud_project, s.google_cloud_region)
    schema = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"i": {"type": "INTEGER"}, "t": {"type": "STRING"}}, "required": ["i", "t"]}}
    for lang, name in LANGS.items():
        todo = [k for k, v in data.items() if lang not in v]
        print(f"[{lang}] to translate: {len(todo)}", flush=True)
        if args.dry_run or not todo:
            continue
        system = SYSTEM.format(language=name).replace("{{placeholder}}", "{placeholder}").replace("{{n}}", "{n}")
        system += "\nIn this task the placeholders are written {name} with single braces; keep them exactly. Short words (a unit, a day, a period of the day) stay short and are used inside longer sentences."
        for start in range(0, len(todo), 40):
            chunk = todo[start:start + 40]
            lines = "\n".join(f"{i}. [{k}] {data[k]['en']}" for i, k in enumerate(chunk))
            prompt = f"Translate each numbered string. The text in [brackets] is only the place it appears; do not translate it.\n\n{lines}"
            for attempt in range(3):
                try:
                    res = client.generate_json(model=MODEL, system=system, parts=[prompt], response_schema=schema, max_output_tokens=8000)
                    got = {int(x["i"]): x["t"].strip() for x in json.loads(res.text)}
                    break
                except Exception as exc:  # noqa: BLE001
                    got = {}
                    print("  retry:", type(exc).__name__, flush=True)
            for i, k in enumerate(chunk):
                t = got.get(i)
                if t and fields(t) == fields(data[k]["en"]):
                    data[k][lang] = t
                else:
                    print(f"  refused {k}: {t!r}", flush=True)
    if not args.dry_run:
        FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("written", FILE)


if __name__ == "__main__":
    main()
