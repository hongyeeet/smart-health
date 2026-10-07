#!/usr/bin/env python3
"""Read a medicine photo with the scan service (prd F2) and print what it found. Nothing is saved unless you ask.

Usage:
  python scripts/scan_label.py path/to/photo.jpg                 read it, print fields and confidence (no database writes)
  python scripts/scan_label.py --sample metformin_prescription   use a made-up label from the test fixtures
  python scripts/scan_label.py photo.jpg --save --user-id <uuid>  also store the masked photo and a scan row for that user
  python scripts/scan_label.py photo.jpg --out masked.jpg         write the blacked-out copy the model saw, to check the masking
  --name "Tan Ah Kow"                                             the user's own name, so any line with it is also blacked out

Only the blacked-out copy of the photo leaves this computer (see app/services/scan_privacy.py). Uses GOOGLE_API_KEY from .env.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "services" / "api" / "tests" / "fixtures"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.agents.scan_extractor import extract_scan  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.llm.vertex import VertexClient  # noqa: E402
from app.services.scan_store import load_drug_index  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?")
    ap.add_argument("--sample")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--user-id")
    ap.add_argument("--name", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--no-db", action="store_true", help="skip loading the drug list (names are then not checked against it)")
    a = ap.parse_args()
    s = get_settings()
    if a.sample:
        import make_label_images
        data = make_label_images.ALL[a.sample]()
    elif a.image:
        data = Path(a.image).read_bytes()
    else:
        ap.error("give an image path or --sample")

    import psycopg
    from check_supabase import clean_url
    conn = None if a.no_db else psycopg.connect(clean_url(s.database_url.get_secret_value()), connect_timeout=20)
    index = load_drug_index(conn) if conn else None
    client = VertexClient(s.google_api_key.get_secret_value(), s.google_cloud_project, s.google_cloud_region)
    outcome, masked = extract_scan(data, client=client, model=s.llm_vision_model, index=index, known_names=a.name,
                                   threshold=s.scan_confidence_threshold)
    if a.out and masked:
        Path(a.out).write_bytes(masked.image)
        print(f"masked photo written to {a.out}")
    print(f"status={outcome.status} review_mode={outcome.review_mode} reasons={outcome.reasons}")
    print(f"masked={outcome.mask_summary} model={outcome.model_id} prompt=v{outcome.prompt_version} "
          f"tokens={outcome.input_tokens}/{outcome.output_tokens} latency={outcome.latency_ms}ms")
    for n, it in enumerate(outcome.items, 1):
        m = it.drug_match
        print(f"\nitem {n}: {it.item_type}  recognised={it.recognised}  min_confidence={it.min_confidence:.2f}"
              + (f"  drug_list={m.generic_name} ({m.score:.0f})" if m else ""))
        for name, f in it.fields.items():
            if f.value is None:
                continue
            mark = "TYPE IT" if f.needs_confirmation else "ok"
            print(f"  {name:<18}{f.value!r:<44} {f.confidence:.2f} (model {f.model_confidence:.2f}) {mark} {f.flags or ''}")
    if a.save:
        if not a.user_id or conn is None:
            sys.exit("--save needs --user-id and a database connection")
        from app.services.scan_store import save_scan
        scan_id = save_scan(conn, a.user_id, masked, outcome)
        conn.commit()
        print(f"\nsaved scan {scan_id} (status {outcome.status})")
    if conn:
        conn.close()


if __name__ == "__main__":
    main()
