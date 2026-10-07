"""Private object storage for the Bronze originals (Supabase Storage). Allow-listed types and size are set on the bucket
by `python scripts/bronze.py --init`. The bucket is private; nothing here ever builds a public URL."""
from __future__ import annotations

import requests

from app.core.errors import ExternalServiceError
from app.core.settings import Settings, get_settings


def upload_object(key: str, data: bytes, content_type: str, settings: Settings | None = None) -> None:
    """Store one object. An existing key is refused (x-upsert false): originals are never overwritten."""
    s = settings or get_settings()
    secret = s.supabase_service_key.get_secret_value()
    if not s.supabase_url or not secret:
        raise ExternalServiceError("storage is not configured", code="storage_not_configured")
    try:
        r = requests.post(f"{s.supabase_url.rstrip('/')}/storage/v1/object/{s.storage_bucket}/{key}", data=data, timeout=60,
                          headers={"Authorization": f"Bearer {secret}", "apikey": secret, "Content-Type": content_type, "x-upsert": "false"})
    except requests.RequestException as e:
        raise ExternalServiceError(f"upload failed ({type(e).__name__})", code="storage_unavailable") from None
    if r.status_code in (200, 201):
        return
    if r.status_code in (400, 409) and "exists" in r.text.lower():
        return                       # the same bytes were stored before: the key is the hash of the bytes
    raise ExternalServiceError(f"upload refused (HTTP {r.status_code})", code="storage_refused")
