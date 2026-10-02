#!/usr/bin/env python3
"""Bronze layer helpers: keep every original exactly as received and log it in ingestion_events.

Usage:
  python scripts/bronze.py --init       create (or update) the private storage bucket
  python scripts/bronze.py --selftest   upload a tiny file twice, prove the 2nd is refused, delete it, leave no rows

In code (later tasks, for example meal photos in E7-2 and prescription scans in E3-1):
  from bronze import store_original, delete_original
  event_id, created = store_original(conn, user_id, "meal_photo", "manual", data, "lunch.jpg")

Rules (schema.md consistency rule 17): an original and its ingestion_events row are never modified;
a better analysis is a new record that points at the same original. The only exception is a deletion
the user asked for: delete_original() removes the object and marks the row deleted.
The caller owns the database transaction (commit or roll back).
"""
import argparse
import hashlib
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

SCHEMA_VERSION = "v1"
BUCKET_LIMIT_BYTES = 10 * 1024 * 1024  # rules.md section 8: 10 MB
# rules.md section 8 allow-list: jpeg, png, heic, csv, zip, xml
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".heic": "image/heic",
        ".csv": "text/csv", ".zip": "application/zip", ".xml": "application/xml"}
ALLOWED_MIME = sorted(set(MIME.values()) | {"text/xml"})
# bucket layout (architecture.md section 1): {user_id}/meals|medications|documents|exports/
FOLDER = {"meal_photo": "meals", "meal_text": "meals", "prescription_image": "medications",
          "medication_image": "medications", "supplement_image": "medications",
          "wearable_export": "exports", "dataset_import": "exports", "document": "documents"}


def settings():
    load_env()
    url, key = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    return url, key, os.environ.get("STORAGE_BUCKET", "smart-health-originals")


def headers(key, **extra):
    return {"Authorization": f"Bearer {key}", "apikey": key, **extra}


def ensure_bucket():
    """Create the private bucket if missing; if it exists, make sure it is private with the limits."""
    url, key, bucket = settings()
    body = {"id": bucket, "name": bucket, "public": False, "file_size_limit": BUCKET_LIMIT_BYTES,
            "allowed_mime_types": ALLOWED_MIME}
    r = requests.get(f"{url}/storage/v1/bucket/{bucket}", headers=headers(key), timeout=30)
    if r.status_code == 200:
        r = requests.put(f"{url}/storage/v1/bucket/{bucket}", headers=headers(key), json=body, timeout=30)
        action = "updated"
    else:
        r = requests.post(f"{url}/storage/v1/bucket", headers=headers(key), json=body, timeout=30)
        action = "created"
    r.raise_for_status()
    print(f"bucket '{bucket}' {action}: private, limit {BUCKET_LIMIT_BYTES // 1024 // 1024} MB, types {', '.join(ALLOWED_MIME)}")


def _upload(key_path, data, content_type):
    url, key, bucket = settings()
    return requests.post(f"{url}/storage/v1/object/{bucket}/{key_path}", data=data,
                         headers=headers(key, **{"Content-Type": content_type, "x-upsert": "false"}), timeout=120)


def _remove(key_path):
    url, key, bucket = settings()
    r = requests.delete(f"{url}/storage/v1/object/{bucket}", headers=headers(key), json={"prefixes": [key_path]}, timeout=30)
    r.raise_for_status()


def store_original(conn, user_id, source_type, entry_source, data, filename=None, *, content_type=None,
                   source_recorded_at=None, source_timezone=None):
    """Keep `data` (bytes) untouched and log it. Returns (ingestion_event_id, created).

    Repeat-safe: the same bytes for the same user return the existing row (created=False) and upload nothing.
    meal_text has no file: pass the text as bytes and filename=None; object_key stays NULL.
    """
    checksum = hashlib.sha256(data).hexdigest()
    row = conn.execute("select id from ingestion_events where user_id = %s and checksum = %s", (user_id, checksum)).fetchone()
    if row:
        return row[0], False
    object_key = None
    if source_type != "meal_text":
        ext = Path(filename or "").suffix.lower()
        content_type = content_type or MIME.get(ext)
        if not content_type or content_type not in ALLOWED_MIME:
            raise ValueError(f"file type not allowed: {ext or content_type}")
        if len(data) > BUCKET_LIMIT_BYTES:
            raise ValueError("file is over the 10 MB limit")
        object_key = f"{user_id}/{FOLDER[source_type]}/{checksum}{ext}"
        r = _upload(object_key, data, content_type)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload refused (HTTP {r.status_code}): {r.text[:120]}")
    event_id = conn.execute(
        """insert into ingestion_events (user_id, source_type, object_key, checksum, received_at, source_recorded_at,
                                         source_timezone, content_type, schema_version, entry_source)
           values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id""",
        (user_id, source_type, object_key, checksum, datetime.now(timezone.utc), source_recorded_at, source_timezone,
         content_type, SCHEMA_VERSION, entry_source)).fetchone()[0]
    return event_id, True


def delete_original(conn, event_id):
    """Only for a deletion the user asked for: remove the object and mark the row deleted.

    TODO(decision): write the deletion to event_log (schema.md rule 17). event_log is created in E1-3.
    """
    row = conn.execute("select object_key, processing_status from ingestion_events where id = %s", (event_id,)).fetchone()
    if row is None:
        raise LookupError("no such ingestion event")
    key_path, status = row
    if status == "deleted":
        return
    if key_path:
        _remove(key_path)
    conn.execute("update ingestion_events set processing_status = 'deleted', object_key = null where id = %s", (event_id,))


def selftest():
    ensure_bucket()
    url, key, bucket = settings()
    with psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20) as conn:
        user_id = conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0]
        data = b"id,value\n1,selftest " + uuid.uuid4().hex.encode()
        ev, created = store_original(conn, user_id, "dataset_import", "system", data, "selftest.csv")
        assert created, "first store should create"
        ev2, created2 = store_original(conn, user_id, "dataset_import", "system", data, "selftest.csv")
        assert ev2 == ev and not created2, "the same bytes must not create a second row"
        object_key = conn.execute("select object_key from ingestion_events where id = %s", (ev,)).fetchone()[0]
        again = _upload(object_key, data, "text/csv")
        assert again.status_code in (400, 409), f"an overwrite must be refused, got HTTP {again.status_code}"
        bad = _upload(f"{user_id}/exports/x.exe", b"x", "application/x-msdownload")
        assert bad.status_code >= 400, "a type outside the allow-list must be refused"
        pub = requests.get(f"{url}/storage/v1/object/public/{bucket}/{object_key}", timeout=30)
        assert pub.status_code in (400, 404), f"the bucket must be private, public URL gave HTTP {pub.status_code}"
        delete_original(conn, ev)
        status = conn.execute("select processing_status, object_key from ingestion_events where id = %s", (ev,)).fetchone()
        assert status == ("deleted", None), status
        gone = requests.get(f"{url}/storage/v1/object/{bucket}/{object_key}", headers=headers(key), timeout=30)
        assert gone.status_code in (400, 404), "the object must be removed"
        conn.rollback()  # leaves no test rows behind
    print("selftest OK: stored once, repeat created nothing, overwrite refused, bad type refused, bucket private, deletion removed the object")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.init:
        ensure_bucket()
    elif a.selftest:
        selftest()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
