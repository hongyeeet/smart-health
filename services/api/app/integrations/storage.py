"""Private object storage for the Bronze originals (Supabase Storage). Allow-listed types and size are set on the bucket
by `python scripts/bronze.py --init`. The bucket is private; nothing here ever builds a public URL."""
from __future__ import annotations

import requests

from app.core.errors import ExternalServiceError
from app.core.settings import Settings, get_settings


def upload_object(key: str, data: bytes, content_type: str, settings: Settings | None = None, bucket: str | None = None) -> None:
    """Store one object. An existing key is refused (x-upsert false): originals are never overwritten."""
    s = settings or get_settings()
    secret = s.supabase_service_key.get_secret_value()
    if not s.supabase_url or not secret:
        raise ExternalServiceError("storage is not configured", code="storage_not_configured")
    try:
        r = requests.post(f"{s.supabase_url.rstrip('/')}/storage/v1/object/{bucket or s.storage_bucket}/{key}", data=data, timeout=60,
                          headers={"Authorization": f"Bearer {secret}", "apikey": secret, "Content-Type": content_type, "x-upsert": "false"})
    except requests.RequestException as e:
        raise ExternalServiceError(f"upload failed ({type(e).__name__})", code="storage_unavailable") from None
    if r.status_code in (200, 201):
        return
    if r.status_code in (400, 409) and "exists" in r.text.lower():
        return                       # the same bytes were stored before: the key is the hash of the bytes
    raise ExternalServiceError(f"upload refused (HTTP {r.status_code})", code="storage_refused")


def download_object(key: str, settings: Settings | None = None, bucket: str | None = None) -> bytes | None:
    """Read one object; None when it does not exist."""
    s = settings or get_settings()
    secret = s.supabase_service_key.get_secret_value()
    if not s.supabase_url or not secret:
        raise ExternalServiceError("storage is not configured", code="storage_not_configured")
    try:
        r = requests.get(f"{s.supabase_url.rstrip('/')}/storage/v1/object/{bucket or s.storage_bucket}/{key}", timeout=30,
                         headers={"Authorization": f"Bearer {secret}", "apikey": secret})
    except requests.RequestException as e:
        raise ExternalServiceError(f"download failed ({type(e).__name__})", code="storage_unavailable") from None
    if r.status_code == 200:
        return r.content
    if r.status_code in (400, 404):
        return None
    raise ExternalServiceError(f"download refused (HTTP {r.status_code})", code="storage_refused")


def ensure_bucket(bucket: str, settings: Settings | None = None) -> str:
    """Create a PRIVATE bucket when it does not exist. Returns 'created' or 'exists'."""
    s = settings or get_settings()
    secret = s.supabase_service_key.get_secret_value()
    if not s.supabase_url or not secret:
        raise ExternalServiceError("storage is not configured", code="storage_not_configured")
    headers = {"Authorization": f"Bearer {secret}", "apikey": secret, "Content-Type": "application/json"}
    try:
        r = requests.post(f"{s.supabase_url.rstrip('/')}/storage/v1/bucket", headers=headers, timeout=30,
                          json={"id": bucket, "name": bucket, "public": False, "file_size_limit": 2_000_000, "allowed_mime_types": ["image/jpeg", "image/png"]})
    except requests.RequestException as e:
        raise ExternalServiceError(f"bucket call failed ({type(e).__name__})", code="storage_unavailable") from None
    if r.status_code in (200, 201):
        return "created"
    if r.status_code in (400, 409) and "exist" in r.text.lower():
        return "exists"
    raise ExternalServiceError(f"bucket refused (HTTP {r.status_code})", code="storage_refused")
