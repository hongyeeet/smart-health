"""Settings from the environment and the private `.env` at the repo root (rules.md section 4). Never print these values."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = (lambda ps: ps[4] if len(ps) > 4 else ps[-1])(Path(__file__).resolve().parents)      # in the container the code sits at /srv, with no repo above it


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / ".env"), extra="ignore")

    google_api_key: SecretStr = SecretStr("")
    google_cloud_project: str = "smart-health-510414"
    google_cloud_region: str = "global"
    llm_vision_model: str = "gemini-3.8-flash"
    llm_vision_challenger: str = "gemini-2.5-pro"
    database_url: SecretStr = SecretStr("")
    supabase_url: str = ""
    supabase_service_key: SecretStr = SecretStr("")
    storage_bucket: str = "smart-health-originals"
    # Workato: the recipe that puts a medicine's dose times on Google Calendar (docs/specs/f4-calendar.md). Blank = not set up, and the
    # calendar step is skipped. The token goes in the header named below; neither value is ever logged.
    workato_webhook_url: str = ""
    workato_webhook_token: SecretStr = SecretStr("")
    workato_token_header: str = "API-TOKEN"
    workato_calendar_remove_url: str = ""      # the recipe that removes one dose's event again (blank: events are never removed or moved)
    # Fields the scanner is less sure of than this must be typed in by the user (backlog E3-1 used 0.85).
    scan_confidence_threshold: float = 0.85
    # True (the default): the local text reader blacks out name, ID, phone and address on a label photo before it leaves the machine, and
    # its text checks what the model quotes. False (SCAN_OCR_ENABLED=false): the photo is sent as it is. Joely's test switch, 2026-10-12.
    scan_ocr_enabled: bool = True
    # Threads the offline text reader may use. 0 = automatic (6, or fewer on a smaller machine). The reader's own default, every core, was slower and
    # got slower with use on a 20-core machine (about 7 s a photo against 0.6 s with 6 threads, 2026-10-14).
    scan_ocr_threads: int = 0
    # Which text reader the scanner uses first. "local" (the default): the offline reader only, so the photo never leaves the machine (D-063).
    # "vision": Google Cloud Vision reads the ORIGINAL photo (name and ID still on it), then they are blacked out before the AI model sees it;
    # falls back to the offline reader when Vision cannot be used. Turned on by SCAN_OCR_ENGINE=vision, a decision that changes D-063.
    scan_ocr_engine: str = "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
