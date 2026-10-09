"""Application configuration via pydantic-settings (rules.md 4: config from env).

Every new variable is added here and to .env.example with a comment. The private .env
is loaded by alembic/env.py and by the load_dotenv() call in main.py.
"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]


def _load_env() -> None:
    """Load the repo .env so DATABASE_URL and other secrets are available."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Settings(BaseSettings):
    """All settings come from environment variables. Defaults are for local dev only."""

    # Database
    database_url: str = ""

    # LLM gateway: Gemini on Vertex AI (docs/specs/ai-models.md)
    llm_vision_model: str = "gemini-3.8-flash"
    llm_vision_challenger: str = "gemini-2.5-pro"
    google_cloud_project: str = ""
    google_cloud_region: str = "global"
    # Vertex AI express-mode key; used when no service-account file is configured
    google_api_key: str = ""
    llm_timeout_s: int = 45
    llm_max_retries: int = 1

    # JEV decision gateway (typed yes/no, choice and score answers; docs/specs/memory.md section 5)
    jev_base_url: str = "https://openrouter.ai/api/alpha/decisions"
    jev_model: str = "typesafe/jev-1.13"
    jev_timeout_s: int = 10
    # below this confidence a guard takes the conservative path; a dish match is dropped (placeholders, tune on the labelled set)
    jev_guard_floor: float = 0.8
    # a database dish is only offered as a substitute when JEV is at least this sure it is a reasonable one
    jev_substitute_floor: float = 0.6

    # Placeholder thresholds for the meal flags and swaps; clinical review pending, never shown as advice
    meal_high_sodium_mg: int = 1000
    meal_high_sugar_g: int = 25
    day_high_sodium_mg: int = 2000
    swap_trigger_kcal: int = 600
    swap_trigger_sodium_mg: int = 600
    swap_trigger_carbs_g: int = 60
    swap_trigger_sugar_g: int = 20
    swap_min_improvement: float = 0.20
    swap_max_worsening: float = 0.15
    # a swap may have much less energy but not much more (ratio of the original serving's kcal)
    swap_kcal_min_ratio: float = 0.55
    swap_kcal_max_ratio: float = 1.10
    food_flag_min_meals: int = 4
    # the habit is only flagged when the person's own logged average is high in at least one of these (placeholders, clinical review pending)
    habit_kcal: int = 600
    habit_sodium_mg: int = 900
    habit_sugar_g: int = 25
    food_flag_min_excess_rise: float = 1.0

    # AI use per day (all providers together). Cost is only known for JEV; Gemini is not priced yet, so the call cap does the work.
    ai_daily_call_cap: int = 500
    ai_daily_budget_usd: float = 5.0

    # How much the app may say (docs/specs/learning-loop.md 12.4): at most this many new extras a day (food swaps, lunch ideas, the walk,
    # preventive nudges, check-ins and log reminders). Dose reminders and urgent messages are exempt. Quiet hours: nothing new is created
    # from the start hour until the end hour (24-hour clock, Singapore time), except the exempt kinds.
    nudge_daily_cap: int = 3
    quiet_start_hour: int = 22
    quiet_end_hour: int = 7

    # Timers (docs/specs/learning-loop.md 12.4): the reminder tick and the nightly reflection, for these people only
    scheduler_enabled: bool = True
    scheduler_users: str = "mr-tan,demo"

    # Demo mode
    demo_mode: bool = True

    # App
    app_name: str = "Smart Health"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # Storage
    storage_bucket: str = "smart-health-originals"

    # The repo .env also holds keys for other services (Supabase, ElevenLabs, ...) that this app does not read.
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), env_file_encoding="utf-8-sig", extra="ignore")


_load_env()
settings = Settings()
