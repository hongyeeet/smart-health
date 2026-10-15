#!/usr/bin/env python3
"""Check that your .env can reach the shared Supabase project. Prints no secrets.

Usage:  python scripts/check_supabase.py

Checks: DATABASE_URL connects; the vector extension is available; how many tables exist and
whether row-level security is on for each; SUPABASE_URL plus SUPABASE_SERVICE_KEY can list
Storage buckets, and the private originals bucket exists.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_data import load_env  # noqa: E402  (reads .env into os.environ)

OK, BAD = "OK  ", "FAIL"


def need(name):
    v = os.environ.get(name, "")
    print(f"{OK if v else BAD} {name} is {'set' if v else 'missing in .env'}")
    return v


def clean_url(url):
    """Drop settings that Python's Postgres driver rejects (Supabase's Transaction-pooler string adds ?pgbouncer=true)."""
    u = urlparse(url)
    q = "&".join(p for p in u.query.split("&") if p and not p.startswith("pgbouncer="))
    return u._replace(query=q).geturl()


def check_db(url):
    import psycopg
    port = urlparse(url).port
    if port == 6543:
        print("     note: port 6543 is the Transaction pooler. It is fine for the app, but migrations need the Session pooler (port 5432, same host).")
    url = clean_url(url)
    host = urlparse(url).hostname
    try:
        with psycopg.connect(url, connect_timeout=15) as c, c.cursor() as cur:
            cur.execute("select current_database(), split_part(version(), ' ', 2)")
            db, ver = cur.fetchone()
            print(f"{OK} database connection works (host {host}, database {db}, PostgreSQL {ver})")
            cur.execute("select count(*) from pg_available_extensions where name = 'vector'")
            print(f"{OK if cur.fetchone()[0] else BAD} pgvector extension is available")
            cur.execute("select count(*) from pg_extension where extname = 'vector'")
            print(f"     pgvector is {'enabled' if cur.fetchone()[0] else 'not enabled yet (the first migration enables it)'}")
            cur.execute("""select c.relname, c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
                           where n.nspname = 'public' and c.relkind = 'r' order by 1""")
            rows = cur.fetchall()
            print(f"     {len(rows)} tables in the public schema" + (": " + ", ".join(r[0] for r in rows[:12]) if rows else " (empty)"))
            no_rls = [r[0] for r in rows if not r[1]]
            if rows:
                print(f"{OK if not no_rls else BAD} row-level security is on for every table" + (f" (off for: {', '.join(no_rls)})" if no_rls else ""))
    except Exception as e:  # noqa: BLE001
        print(f"{BAD} database connection failed: {type(e).__name__}: {str(e).splitlines()[0][:160]}")
        return False
    return True


def check_storage(url, key, bucket):
    try:
        r = requests.get(f"{url.rstrip('/')}/storage/v1/bucket", headers={"Authorization": f"Bearer {key}", "apikey": key}, timeout=20)
    except requests.RequestException as e:
        print(f"{BAD} could not reach SUPABASE_URL: {type(e).__name__}")
        return False
    if r.status_code != 200:
        print(f"{BAD} Storage API answered HTTP {r.status_code} (check SUPABASE_URL and SUPABASE_SERVICE_KEY)")
        return False
    names = {b["name"]: b for b in r.json()}
    print(f"{OK} Storage API works with the service key; buckets: {', '.join(names) or '(none)'}")
    if bucket in names:
        print(f"{OK if not names[bucket].get('public') else BAD} bucket '{bucket}' exists and is {'public (must be private)' if names[bucket].get('public') else 'private'}")
    else:
        print(f"     bucket '{bucket}' does not exist yet (created in E1-1)")
    return True


def main():
    load_env()
    db, url, key = need("DATABASE_URL"), need("SUPABASE_URL"), need("SUPABASE_SERVICE_KEY")
    bucket = os.environ.get("STORAGE_BUCKET", "smart-health-originals")
    ok = True
    if db:
        ok &= check_db(db)
    if url and key:
        ok &= check_storage(url, key, bucket)
    ok &= all([db, url, key])
    print("\nAll good." if ok else "\nSomething needs fixing (see FAIL lines above).")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
