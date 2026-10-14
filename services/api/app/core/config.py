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

    # AI use per day, one cap per kind of call (services/usage.py): photo and label reads, text generation, embeddings and JEV.
    # Each kind is counted and blocked on its own, so one kind used up never blocks another.
    ai_cap_vertex_vision: int = 300      # photo and label reads
    ai_cap_vertex_generate: int = 500    # text the person sees: brief findings, medicine explainer, clash checker, chat, onboarding answers
    ai_cap_vertex_image: int = 60        # dish pictures for the menu page (one per new dish, ever)
    ai_cap_vertex_embed: int = 2000      # background embeddings for food search (fall back to text search when blocked)
    ai_cap_jev: int = 500                # JEV typed decisions (guards and checks)
    # Any AI provider without a cap of its own above uses this call cap.
    ai_daily_call_cap: int = 500
    # Cost limit in USD, checked per provider against that provider's own cost (only JEV reports cost today).
    ai_daily_budget_usd: float = 5.0

    # How much the app may say (docs/specs/learning-loop.md 12.4): at most this many new extras a day (food swaps, lunch ideas, the walk,
    # preventive nudges, check-ins and log reminders). Dose reminders and urgent messages are exempt. Quiet hours: nothing new is created
    # from the start hour until the end hour (24-hour clock, Singapore time), except the exempt kinds.
    nudge_daily_cap: int = 3
    quiet_start_hour: int = 22
    quiet_end_hour: int = 7

    # Timers (docs/specs/learning-loop.md 12.4): the reminder tick and the nightly reflection, for these people only
    # reminder emails through a Workato recipe (docs/specs/email-notifications.md). Blank webhook = not set up: nothing is sent and nothing is lost.
    workato_email_webhook_url: str = ""
    workato_email_webhook_token: str = ""
    workato_email_token_header: str = "API-TOKEN"
    app_base_url: str = "http://localhost:5174"     # where the button in an email opens the app
    api_public_url: str = ""                          # where the unsubscribe link points (this API, as the internet sees it); blank = no link
    notify_secret: str = ""                           # signs unsubscribe links; blank = no link
    email_daily_cap: int = 3                          # reminder emails per person per day (an urgent alert to the contact is exempt)
    email_max_attempts: int = 3
    scheduler_enabled: bool = True
    scheduler_users: str = "mr-tan"              # people the jobs always serve; every person who finished set-up is added (scheduler_persons)
    scheduler_persons: bool = True

    # Demo mode
    demo_mode: bool = True

    # App
    app_name: str = "Equinox"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # Storage
    storage_bucket: str = "smart-health-originals"
    food_image_bucket: str = "food-images"      # private bucket of dish pictures, served through the API
    food_image_model: str = "gemini-2.5-flash-image"   # the only image model this project can reach (checked 2026-10-14: Imagen and the Gemini 3 image models answer 404)

    # The repo .env also holds keys for other services (Supabase, ElevenLabs, ...) that this app does not read.
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), env_file_encoding="utf-8-sig", extra="ignore")


_load_env()
settings = Settings()
