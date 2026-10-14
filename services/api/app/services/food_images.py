"""Dish pictures for the Meal suggestions page (docs/specs/menu.md).

One picture per DISH, shared by everyone and made ONCE: `food_images.dish_key` is the dish name made lower case with letters and digits
joined by dashes. A dish seen for the first time gets a `pending` row; a background worker makes the picture with a Gemini image model,
shrinks it to a small JPEG and keeps it in the private `food-images` bucket. A `ready` row is never generated again, and a page visit
never generates anything: it only reads the row. A failed picture is tried again later, at most 3 times; the daily cap (`vertex_image`)
stops the worker when it is used up, and the dish simply keeps its plain placeholder until tomorrow.

Only the dish NAME goes into the prompt: no person, no health value, no photo of a person's meal.
"""
from __future__ import annotations

import hashlib
import io
import logging
import re
from typing import Any, Callable

from app.core.config import settings
from app.core.errors import ExternalServiceError
from app.db.logstore import tx
from app.integrations import storage
from app.llm import gateway

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_AFTER = "15 minutes"          # a failed picture waits this long before the next try
STUCK_AFTER = "10 minutes"          # a row left in 'generating' by a crashed worker is taken again after this
SIZE = (800, 600)

PROMPT = (
    "Overhead photo of {name}, a dish eaten in Singapore, served plated on a plain light grey background. "
    "Natural soft light, appetising and realistic, the whole dish in the middle of the frame. "
    "No text, no people, no hands, no logos, no watermark."
)


def dish_key(name: str) -> str:
    """The dish name as a stable key: lower case, letters and digits, joined by single dashes, at most 80 characters."""
    key = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return key[:80].strip("-")


def prompt_for(name: str) -> str:
    return PROMPT.format(name=re.sub(r"\s+", " ", name).strip())


def prompt_hash(name: str) -> str:
    return hashlib.sha256(prompt_for(name).encode("utf-8")).hexdigest()[:16]


def ensure_rows(items: list[tuple[str, str]]) -> dict[str, dict[str, Any]]:
    """Make sure every (dish_key, name) has a row; return {dish_key: {status}} for them all. Makes no picture and never touches a ready row."""
    keys = {k: n for k, n in items if k}
    if not keys:
        return {}
    with tx() as c:
        for k, n in keys.items():
            c.execute("insert into food_images (dish_key, name) values (%s, %s) on conflict (dish_key) do nothing", (k, n))
        rows = c.execute("select dish_key, status from food_images where dish_key = any(%s)", (list(keys),)).fetchall()
    return {r["dish_key"]: {"status": r["status"]} for r in rows}


def to_jpeg(png: bytes) -> bytes:
    """The model's picture as a 4:3 JPEG of 800 by 600: centre crop, then shrink. Keeps the stored file small."""
    from PIL import Image

    img = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = img.size
    want = SIZE[0] / SIZE[1]
    if w / h > want:
        nw = int(h * want)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / want)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    img = img.resize(SIZE, Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=84, optimize=True)
    return out.getvalue()


def _claim() -> dict[str, Any] | None:
    """Take one dish that needs a picture. SKIP LOCKED so two workers never take the same dish."""
    with tx() as c:
        return c.execute(
            f"""update food_images set status='generating', attempts = attempts + 1, updated_at = now()
                where dish_key = (select dish_key from food_images
                                  where status = 'pending'
                                     or (status = 'failed' and attempts < {MAX_ATTEMPTS} and updated_at < now() - interval '{RETRY_AFTER}')
                                     or (status = 'generating' and updated_at < now() - interval '{STUCK_AFTER}' and attempts < {MAX_ATTEMPTS})
                                  order by requested_at limit 1 for update skip locked)
                returning dish_key, name, attempts"""
        ).fetchone()


def _finish(key: str, *, ok: bool, error: str | None = None, storage_key: str | None = None, name: str = "") -> None:
    with tx() as c:
        if ok:
            c.execute(
                "update food_images set status='ready', storage_key=%s, content_type='image/jpeg', model=%s, prompt_hash=%s, last_error=null, generated_at=now(), updated_at=now() where dish_key=%s",
                (storage_key, settings.food_image_model, prompt_hash(name), key),
            )
        else:
            c.execute("update food_images set status='failed', last_error=%s, updated_at=now() where dish_key=%s", ((error or "failed")[:60], key))


def _release(key: str) -> None:
    """Put a dish back to waiting without counting the try (the daily limit was reached, which is not the dish's fault)."""
    with tx() as c:
        c.execute("update food_images set status='pending', attempts = greatest(attempts - 1, 0), updated_at=now() where dish_key=%s", (key,))


def generate_one(row: dict[str, Any], *, make: Callable[[str], bytes] = gateway.generate_image, put: Callable[..., None] = storage.upload_object) -> str:
    """Make and store the picture for one claimed dish. Returns 'ready', 'failed' or 'limit' (daily cap reached; the dish stays waiting)."""
    key, name = row["dish_key"], row["name"]
    try:
        png = make(prompt_for(name))
        jpeg = to_jpeg(png)
        storage_key = f"{key}.jpg"
        put(storage_key, jpeg, "image/jpeg", bucket=settings.food_image_bucket)
    except gateway.LLMUnavailable as e:
        if e.code == "daily_limit":
            _release(key)
            return "limit"
        logger.warning("dish picture failed code=%s", e.code)
        _finish(key, ok=False, error=e.code)
        return "failed"
    except ExternalServiceError as e:
        logger.warning("dish picture not stored code=%s", e.code)
        _finish(key, ok=False, error=e.code)
        return "failed"
    except Exception as e:  # a bad image or any other surprise: the dish is marked failed, the worker goes on
        logger.warning("dish picture error type=%s", type(e).__name__)
        _finish(key, ok=False, error=type(e).__name__)
        return "failed"
    _finish(key, ok=True, storage_key=storage_key, name=name)
    return "ready"


def generate_pending(limit: int = 3, **kw: Any) -> dict[str, int]:
    """Work through waiting dishes, at most `limit` pictures. Stops early when the daily cap is reached. Safe to call from several places."""
    out = {"ready": 0, "failed": 0, "limit": 0}
    for _ in range(limit):
        row = _claim()
        if row is None:
            break
        result = generate_one(row, **kw)
        out[result] += 1
        if result == "limit":
            break
    return out


def read_picture(key: str) -> bytes | None:
    """The stored picture of a READY dish; None when the dish has none (yet)."""
    with tx() as c:
        r = c.execute("select storage_key from food_images where dish_key=%s and status='ready'", (key,)).fetchone()
    if not r or not r["storage_key"]:
        return None
    return storage.download_object(r["storage_key"], bucket=settings.food_image_bucket)
