"""Reads and writes for the Log feature, against the shared Supabase database (data model v2).

Every write is one transaction in four steps (docs/specs/data-model-v2.md):
  1. Bronze: the entry exactly as received (immutable; only `processing_status` changes afterwards)
  2. Silver: the typed row, pointing back at its Bronze row (`bronze_id`)
  3. Gold `timeline_5min`: the 5-minute buckets the entry covers (a meal spans its eating time, a symptom spans its duration)
  4. Gold `daily_summary`: the day's counts and averages, recomputed from Silver

The app has no sign-in yet, so every request is the one demo user created here (separate from Mr Tan, whose data is not touched).
"""
from __future__ import annotations

import hashlib
import json
import re
import logging
import math
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterator
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings
from app.services import blood_pressure, texts

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Singapore")
NAMESPACE = uuid.UUID("6f1c2d3e-4a5b-5c6d-8e7f-9a0b1c2d3e4f")
APP_USER = uuid.uuid5(NAMESPACE, "user:app-demo")
# Mr Tan is the loaded 90-day patient (scripts/load_mr_tan_v2.py). The app has no sign-in, so a request names who it acts as
# with the `X-User` header; no header means the demo user, exactly as before.
MR_TAN_USER = uuid.UUID("dc48e209-5731-5b3d-89d9-986242c54368")
USERS: dict[str, dict] = {
    "demo": {"id": APP_USER, "label": "Demo user", "sub": "A blank account for trying things"},
    "mr-tan": {"id": MR_TAN_USER, "label": "Mr Tan", "sub": "About 90 days of history"},
}
_current: ContextVar[str] = ContextVar("app_user", default="demo")


def is_read_only(user: object) -> bool:
    """Mr Tan is loaded demo data: nothing may write records for him on its own (a GET must never add rows to his history)."""
    return str(user) == str(MR_TAN_USER)


# A person started in the app ("Start as new person") has a key of this shape. The key is made on the device when set-up opens, and the
# user row is created only when set-up is finished (POST /users, routers/users.py). The user id is derived from the key, so the same key
# always means the same person, and no lookup table is needed. Before the row exists the key can read (it finds nothing) but not write.
PERSON_KEY = re.compile(r"person-[0-9a-f]{12}")


def person_id(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"user:{key}")


def set_user(key: str | None) -> str:
    """Choose who the rest of this request acts as. Unknown keys raise KeyError so a typo never silently falls back."""
    key = (key or "demo").strip().lower()
    if key not in USERS and not PERSON_KEY.fullmatch(key):
        raise KeyError(key)
    _current.set(key)
    return key


def current_user_key() -> str:
    return _current.get()


def current_user() -> uuid.UUID:
    key = _current.get()
    return USERS[key]["id"] if key in USERS else person_id(key)
BUCKET = timedelta(minutes=5)

# Daily goals. Placeholders from the owner (appConfig.goals); clinical review pending, never shown as advice.
GOAL_MEALS = 3
GOAL_MODERATE_MIN = 150
GOAL_STRENGTH = 2

SYMPTOM_TYPE = {
    "More thirsty than usual": "thirst",
    "Passing more urine": "frequent_urination",
    "Numbness": "numbness",
    "Tingling": "tingling",
    "Foot pain": "foot_pain",
    "Blurry vision": "blurred_vision",
    "Tired more than usual": "fatigue",
    "Dizzy": "dizziness",
    "Headache": "headache",
    "Upset stomach": "nausea",
    "Vomiting": "nausea",
    "Night sweats": "shaky_sweaty",
    "Shaky or sweaty": "shaky_sweaty",
    "Slow-healing wound": "slow_healing_wound",
}
INTENSITY_WORD = {1: "Very light", 2: "Light", 3: "Moderate", 4: "Hard", 5: "All-out"}
EXERCISE_WORD = {
    "strength": "Strength", "walking": "Walk", "running": "Run", "cycling": "Cycling", "swimming": "Swimming", "hiit": "HIIT",
    "sports": "Sports", "yoga_pilates": "Yoga or pilates", "stretching_mobility": "Stretching", "dance": "Dance",
    "household_gardening": "Housework or gardening", "other": "Exercise",
}
FELT_TO_FEELING = {"energised": 5, "fine": 4, "tired": 2, "unwell": 1}


# ----------------------------------------------------------------------------------------------- connection
def _dsn() -> str:
    u = urlparse(settings.database_url)
    query = "&".join(p for p in u.query.split("&") if p and not p.startswith("pgbouncer="))
    return u._replace(scheme="postgresql", query=query).geturl()


_shared: ContextVar[psycopg.Connection | None] = ContextVar("shared_connection", default=None)


@contextmanager
def tx() -> Iterator[psycopg.Connection]:
    """One transaction: commits on success, rolls back on any error.

    Inside `one_connection()` this does not open a new connection (each one costs a network round trip): it reuses the open one,
    as a savepoint, so an error in one block is rolled back without spoiling the blocks after it."""
    shared = _shared.get()
    if shared is not None:
        with shared.transaction():
            yield shared
        return
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Add it to the repo .env.")
    with psycopg.connect(_dsn(), row_factory=dict_row, connect_timeout=20) as conn:
        yield conn


@contextmanager
def one_connection() -> Iterator[psycopg.Connection]:
    """Every `tx()` in this block (and in the functions it calls, in this thread) uses ONE connection. For read paths that make
    many small queries; the whole block is one transaction that commits at the end."""
    shared = _shared.get()
    if shared is not None:
        yield shared
        return
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Add it to the repo .env.")
    with psycopg.connect(_dsn(), row_factory=dict_row, connect_timeout=20) as conn:
        token = _shared.set(conn)
        try:
            yield conn
        finally:
            _shared.reset(token)


def ensure_user() -> None:
    with tx() as c:
        c.execute("insert into users (id, is_demo) values (%s, true) on conflict (id) do nothing", (APP_USER,))


# ----------------------------------------------------------------------------------------------- helpers
def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ)


def _floor(dt: datetime) -> datetime:
    """The start of the 5-minute bucket (clock time in Singapore), as UTC."""
    local = _aware(dt).astimezone(TZ)
    local = local.replace(minute=local.minute - local.minute % 5, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


def _span(start: datetime, end: datetime) -> list[datetime]:
    """Bucket starts from the bucket of `start` up to (not including) `end`; always at least one."""
    first = _floor(start)
    out, t = [first], first + BUCKET
    end = _aware(end).astimezone(timezone.utc)
    while t < end:
        out.append(t)
        t += BUCKET
    return out


def _local_date(dt: datetime) -> date:
    return _aware(dt).astimezone(TZ).date()


def _num(v: Any) -> Any:
    return float(v) if isinstance(v, Decimal) else v


def _bronze(c: psycopg.Connection, table: str, payload: dict, source: str = "manual") -> uuid.UUID:
    body = json.dumps(payload, sort_keys=True, default=str)
    # Bronze is unique per person and content, so the same submission twice (a retry, or deleting and logging identical times) reuses
    # its row instead of failing. Only `processing_status` may change on Bronze, so the no-op update is on that column.
    row = c.execute(
        f"insert into {table} (user_id, source, payload, checksum) values (%s, %s::entry_source, %s::jsonb, %s) "
        f"on conflict (user_id, checksum) do update set processing_status = {table}.processing_status returning id",
        (current_user(), source, body, hashlib.sha256(body.encode()).hexdigest()),
    ).fetchone()
    return row["id"]


def _processed(c: psycopg.Connection, table: str, bronze_id: uuid.UUID) -> None:
    c.execute(f"update {table} set processing_status='processed' where id=%s", (bronze_id,))


def _upsert_timeline(c: psycopg.Connection, buckets: list[datetime], cols: dict[str, Any], casts: dict[str, str] | None = None) -> None:
    """Write `cols` into each bucket's row, creating the row if the person has no data there yet."""
    casts = casts or {}
    names = list(cols)
    ph = ", ".join("%s" + (f"::{casts[n]}" if n in casts else "") for n in names)
    sets = ", ".join(f"{n} = excluded.{n}" for n in names)
    sql = (
        f"insert into timeline_5min (user_id, bucket_start, local_date, hour_of_day, {', '.join(names)}) "
        f"values (%s, %s, %s, %s, {ph}) on conflict (user_id, bucket_start) do update set {sets}"
    )
    rows = []
    for b in buckets:
        local = b.astimezone(TZ)
        rows.append((current_user(), b, local.date(), local.hour, *[cols[n] for n in names]))
    with c.cursor() as cur:
        cur.executemany(sql, rows)


_log_epoch: dict[str, int] = {}


def log_epoch(user_key: str) -> int:
    """A number that goes up each time that person's meals, workouts, symptoms or check-ins change. For caches that must not outlive a log."""
    return _log_epoch.get(user_key, 0)


def refresh_day(c: psycopg.Connection, d: date) -> None:
    """Recompute the log-driven columns of that day's Gold `daily_summary` row from Silver. A day with nothing logged keeps NULL
    (unknown), never 0."""
    _log_epoch[current_user_key()] = log_epoch(current_user_key()) + 1
    day = (d, current_user())
    f = c.execute(
        """select count(*) n, sum(carbs_g) carbs, sum(protein_g) protein, sum(fat_g) fat, sum(sugar_g) sugar, sum(fibre_g) fibre, sum(sodium_mg) sodium
           from food_logs where deleted_at is null and user_id=%(u)s and (start_at at time zone 'Asia/Singapore')::date=%(d)s""",
        {"u": current_user(), "d": d},
    ).fetchone()
    e = c.execute(
        """select count(*) n, coalesce(sum(extract(epoch from end_at-start_at)/60),0) mins
           from exercise_logs where deleted_at is null and user_id=%(u)s and (start_at at time zone 'Asia/Singapore')::date=%(d)s""",
        {"u": current_user(), "d": d},
    ).fetchone()
    s = c.execute(
        """select count(*) n, max(severity) worst from symptom_logs
           where deleted_at is null and user_id=%(u)s and (occurred_at at time zone 'Asia/Singapore')::date=%(d)s""",
        {"u": current_user(), "d": d},
    ).fetchone()
    w = c.execute(
        """select avg(mood) mood, avg(stress_self) stress, avg(energy) energy, avg(sleep_quality) sleepq from wellbeing_logs
           where deleted_at is null and user_id=%(u)s and (recorded_at at time zone 'Asia/Singapore')::date=%(d)s""",
        {"u": current_user(), "d": d},
    ).fetchone()
    c.execute(
        """insert into daily_summary (user_id, local_date, meals_n, carbs_g, protein_g, fat_g, sugar_g, fibre_g, sodium_mg,
                                      exercise_min, exercise_sessions_n, symptoms_n, symptom_worst_severity,
                                      mood_avg, stress_self_avg, energy_avg, sleep_quality_avg, built_at)
           values (%(u)s, %(d)s, %(mn)s, %(carbs)s, %(protein)s, %(fat)s, %(sugar)s, %(fibre)s, %(sodium)s,
                   %(emin)s, %(en)s, %(sn)s, %(sw)s, %(mood)s, %(stress)s, %(energy)s, %(sleepq)s, now())
           on conflict (user_id, local_date) do update set
             meals_n=excluded.meals_n, carbs_g=excluded.carbs_g, protein_g=excluded.protein_g, fat_g=excluded.fat_g,
             sugar_g=excluded.sugar_g, fibre_g=excluded.fibre_g, sodium_mg=excluded.sodium_mg,
             exercise_min=excluded.exercise_min, exercise_sessions_n=excluded.exercise_sessions_n,
             symptoms_n=excluded.symptoms_n, symptom_worst_severity=excluded.symptom_worst_severity,
             mood_avg=excluded.mood_avg, stress_self_avg=excluded.stress_self_avg, energy_avg=excluded.energy_avg,
             sleep_quality_avg=excluded.sleep_quality_avg, built_at=now()""",
        {
            "u": current_user(), "d": d, "mn": f["n"] or None, "carbs": f["carbs"], "protein": f["protein"], "fat": f["fat"], "sugar": f["sugar"],
            "fibre": f["fibre"], "sodium": f["sodium"], "emin": round(float(e["mins"])) if e["n"] else None, "en": e["n"] or None, "sn": s["n"] or None, "sw": s["worst"],
            "mood": w["mood"], "stress": w["stress"], "energy": w["energy"], "sleepq": w["sleepq"],
        },
    )
    del day


def _meal_type_for(dt: datetime) -> str:
    h = _aware(dt).astimezone(TZ).hour
    if h < 11:
        return "breakfast"
    if h < 15:
        return "lunch"
    if h < 18:
        return "snack"
    return "dinner"


# ----------------------------------------------------------------------------------------------- meal photo (Bronze only)
def save_meal_analysis(payload: dict) -> str:
    """The photo's checksum, the description and the model's raw answer, stored as received when the photo is analysed."""
    with tx() as c:
        return str(_bronze(c, "bronze_food", payload, source="llm_estimate"))


# ----------------------------------------------------------------------------------------------- writes
def create_meal(i: Any) -> dict:
    with tx() as c:
        payload = i.model_dump(mode="json", by_alias=True)
        end = max(_aware(i.end_at), _aware(i.start_at))
        estimated_by = "user" if (i.edited or i.values_from == "user" or not i.analysis_id) else "llm_photo"
        if i.analysis_id and estimated_by == "user":
            # the person changed the photo's numbers: this meal's own Bronze row keeps what they typed (food_logs has no kcal column,
            # so a typed kcal lives only in the payload). Its analysisId links back to the photo's Bronze row, which is kept as it was.
            analysis = uuid.UUID(i.analysis_id)
            bronze_id = _bronze(c, "bronze_food", payload)
            _processed(c, "bronze_food", analysis)
        else:
            bronze_id = uuid.UUID(i.analysis_id) if i.analysis_id else _bronze(c, "bronze_food", payload)
        row = c.execute(
            """insert into food_logs (user_id, start_at, end_at, meal_type, food, protein_g, carbs_g, fat_g, sugar_g, fibre_g, sodium_mg,
                                      estimated_by, source, bronze_id)
               values (%s,%s,%s,%s::meal_type,%s,%s,%s,%s,%s,%s,%s,%s::estimated_by_kind,'manual',%s) returning id""",
            (current_user(), _aware(i.start_at), end, _meal_type_for(i.start_at), i.name, i.protein_g, i.carbs_g, i.fat_g, i.sugar_g,
             i.fibre_g, i.sodium_mg, estimated_by, bronze_id),
        ).fetchone()
        fid = row["id"]
        _upsert_timeline(
            c, _span(i.start_at, end),
            {"meal_id": fid, "meal_type": _meal_type_for(i.start_at), "food": i.name, "carbs_g": i.carbs_g, "protein_g": i.protein_g,
             "fat_g": i.fat_g, "sugar_g": i.sugar_g, "fibre_g": i.fibre_g, "sodium_mg": i.sodium_mg},
            {"meal_type": "meal_type"},
        )
        _processed(c, "bronze_food", bronze_id)
        refresh_day(c, _local_date(i.start_at))
        return {"id": str(fid), "day": _local_date(i.start_at).isoformat(), "meal_type": _meal_type_for(i.start_at)}


# The "How hard did it feel?" rating is optional once migration 0036 has made exercise_logs.intensity nullable.
# Until that migration is applied the API still asks for it, with this message (the app shows the same sentence).
RATING_REQUIRED = "Pick a number from 1 to 5 to save this workout."
_rating_optional_known = False  # cached once the column reads nullable (it cannot go back); a "no" is checked every time


def _intensity_nullable(c: psycopg.Connection) -> bool:
    row = c.execute(
        "select is_nullable from information_schema.columns where table_schema = current_schema() and table_name = 'exercise_logs' and column_name = 'intensity'"
    ).fetchone()
    return row is not None and row["is_nullable"] == "YES"


def rating_optional(c: psycopg.Connection | None = None) -> bool:
    """True when exercise_logs.intensity allows null (migration 0036 applied). A yes is remembered; a no is read again each time."""
    global _rating_optional_known
    if _rating_optional_known:
        return True
    if c is None:
        with tx() as conn:
            nullable = _intensity_nullable(conn)
    else:
        nullable = _intensity_nullable(c)
    if nullable:
        _rating_optional_known = True
    return nullable


def create_workout(i: Any, sets: list[dict] | None = None, note: str | None = None, payload: dict | None = None) -> dict:
    start = _aware(i.start_at)
    end = start + timedelta(minutes=i.minutes)
    with tx() as c:
        bronze_id = _bronze(c, "bronze_exercise", payload or i.model_dump(mode="json", by_alias=True))
        row = c.execute(
            """insert into exercise_logs (user_id, start_at, end_at, type, intensity, feeling, note, source, bronze_id)
               values (%s,%s,%s,%s::exercise_kind,%s,%s,%s,'manual',%s) returning id""",
            (current_user(), start, end, i.type, i.intensity, i.feeling, (note or i.activity or None), bronze_id),
        ).fetchone()
        eid = row["id"]
        for s in sets or []:
            c.execute(
                """insert into exercise_sets (exercise_log_id, user_id, exercise, exercise_order, set_no, reps, weight_kg, performed_at)
                   values (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (eid, current_user(), s["exercise"], s["exercise_order"], s["set_no"], s["reps"], s["weight_kg"], s["performed_at"]),
            )
        _upsert_timeline(c, _span(start, end), {"exercise_id": eid, "exercise_type": i.type, "exercise_intensity": i.intensity}, {"exercise_type": "exercise_kind"})
        _processed(c, "bronze_exercise", bronze_id)
        refresh_day(c, _local_date(start))
        return {"id": str(eid), "day": _local_date(start).isoformat(), "end": end}


def get_workout(entry_id: str) -> dict | None:
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        return None
    with tx() as c:
        r = c.execute(
            """select id, type::text t, note, intensity, feeling, start_at, greatest(1, round(extract(epoch from end_at-start_at)/60)::int) m
               from exercise_logs where id=%s and user_id=%s and deleted_at is null""", (eid, current_user())).fetchone()
    if not r:
        return None
    return {"id": str(r["id"]), "type": r["t"], "activity": r["note"] or "", "intensity": r["intensity"], "start_at": r["start_at"].isoformat(), "minutes": int(r["m"]), "feeling": r["feeling"]}


def update_workout(entry_id: str, i: Any) -> dict | None:
    """Edit a logged workout in place (start, length, kind, effort, feeling, note). Its timeline marks move with it.
    None when there is no such live workout. Raises ValueError for a malformed id."""
    eid = uuid.UUID(entry_id)
    start = _aware(i.start_at)
    end = start + timedelta(minutes=i.minutes)
    with tx() as c:
        old = c.execute("select start_at from exercise_logs where id=%s and user_id=%s and deleted_at is null", (eid, current_user())).fetchone()
        if old is None:
            return None
        c.execute(
            "update exercise_logs set start_at=%s, end_at=%s, type=%s::exercise_kind, intensity=%s, feeling=%s, note=%s where id=%s and user_id=%s",
            (start, end, i.type, i.intensity, i.feeling, (i.activity or None), eid, current_user()),
        )
        c.execute("update timeline_5min set exercise_id=null, exercise_type=null, exercise_intensity=null where user_id=%s and exercise_id=%s", (current_user(), eid))
        _upsert_timeline(c, _span(start, end), {"exercise_id": eid, "exercise_type": i.type, "exercise_intensity": i.intensity}, {"exercise_type": "exercise_kind"})
        _log_event(c, "log.workout.edited", eid)
        for d in {_local_date(old["start_at"]), _local_date(start)}:
            refresh_day(c, d)
    return {"id": str(eid), "day": _local_date(start).isoformat()}


def create_symptom(i: Any) -> dict:
    stype = SYMPTOM_TYPE.get(i.label, "other")
    parts = [i.label, i.side, i.feel, i.relation, (i.note or "").strip() or None]
    note = " · ".join(p for p in parts if p)
    when = _aware(i.occurred_at)
    with tx() as c:
        bronze_id = _bronze(c, "bronze_symptom", i.model_dump(mode="json", by_alias=True))
        row = c.execute(
            """insert into symptom_logs (user_id, occurred_at, symptom_type, severity, duration_min, note, source, bronze_id)
               values (%s,%s,%s::symptom_kind,%s,%s,%s,'manual',%s) returning id""",
            (current_user(), when, stype, i.severity, i.duration_min, note, bronze_id),
        ).fetchone()
        n = math.ceil(i.duration_min / 5) if i.duration_min else 1
        first = _floor(when)
        buckets = [first + BUCKET * k for k in range(max(n, 1))]
        _upsert_timeline(
            c, buckets,
            {"symptom_type": stype, "symptom_severity": i.severity, "symptom_duration_min": i.duration_min, "symptom_note": note},
            {"symptom_type": "symptom_kind"},
        )
        _processed(c, "bronze_symptom", bronze_id)
        refresh_day(c, _local_date(when))
        return {"id": str(row["id"]), "day": _local_date(when).isoformat(), "type": stype, "buckets": len(buckets)}


def create_checkin(i: Any) -> dict:
    """A mood and sleep check-in. Each question may be left unanswered (stored as null); at least one answer is required."""
    now = datetime.now(timezone.utc)
    with tx() as c:
        bronze_id = _bronze(c, "bronze_wellbeing", i.model_dump(mode="json", by_alias=True))
        row = c.execute(
            """insert into wellbeing_logs (user_id, recorded_at, mood, stress_self, sleep_quality, energy, source, bronze_id)
               values (%s,%s,%s,%s,%s,%s,'manual',%s) returning id""",
            (current_user(), now, i.mood, i.stress, i.sleep, i.energy, bronze_id),
        ).fetchone()
        # only the answers given go to the timeline, so a partial check-in never blanks an answer already in that 5-minute bucket
        answers = {"mood": i.mood, "stress_self": i.stress, "sleep_quality": i.sleep, "energy": i.energy}
        _upsert_timeline(c, [_floor(now)], {k: v for k, v in answers.items() if v is not None})
        _processed(c, "bronze_wellbeing", bronze_id)
        refresh_day(c, _local_date(now))
        return {"id": str(row["id"]), "day": _local_date(now).isoformat()}


# ----------------------------------------------------------------------------------------------- blood pressure
class DuplicateReading(Exception):
    """A live reading is already saved for that exact time. The router answers 409 with a plain sentence."""


def _bp_time(i: Any) -> datetime:
    return _aware(i.measured_at).astimezone(timezone.utc) if i.measured_at else datetime.now(timezone.utc)


def _bp_payload(i: Any, when: datetime) -> dict:
    """The entry as received, with the time filled in and the note tidied. The time is in the payload so two readings never
    share one Bronze row by accident (Bronze is unique per person and content). The pulse and note stay here as received; the
    Silver row has them as columns from migration 0035, and before it they were only here."""
    payload = i.model_dump(mode="json", by_alias=True)
    payload["measuredAt"] = when.isoformat()
    payload["note"] = (i.note or "").strip() or None
    return payload


def _bp_note(i: Any) -> str | None:
    return (i.note or "").strip() or None


def _write_bp(c: psycopg.Connection, i: Any, when: datetime, payload: dict) -> uuid.UUID:
    """Bronze, then the Silver row. Returns the entry id. A live reading at the same time raises DuplicateReading."""
    bronze_id = _bronze(c, "bronze_blood_pressure", payload)
    if blood_pressure.columns_ready(c):
        entry_id = _insert_bp(c, i, when, bronze_id)
    else:
        entry_id = _insert_bp_bronze(c, i, when, bronze_id)
    _processed(c, "bronze_blood_pressure", bronze_id)
    return entry_id


def _insert_bp(c: psycopg.Connection, i: Any, when: datetime, bronze_id: uuid.UUID) -> uuid.UUID:
    """The Silver row after migration 0035: its own id, pulse and note. Silver allows one row per person and time, so a soft-deleted
    reading at the same time is brought back as a new reading (a new id) with the new values; a live one raises DuplicateReading."""
    row = c.execute(
        """insert into blood_pressure_readings (user_id, recorded_at, systolic_mmhg, diastolic_mmhg, pulse, note, source, bronze_id)
           values (%s,%s,%s,%s,%s,%s,'manual',%s)
           on conflict (user_id, recorded_at) do update set id=gen_random_uuid(), systolic_mmhg=excluded.systolic_mmhg,
             diastolic_mmhg=excluded.diastolic_mmhg, pulse=excluded.pulse, note=excluded.note, source=excluded.source,
             bronze_id=excluded.bronze_id, updated_at=null, deleted_at=null
           where blood_pressure_readings.deleted_at is not null
           returning id""",
        (current_user(), when, i.systolic, i.diastolic, i.pulse, _bp_note(i), bronze_id),
    ).fetchone()
    if row is None:
        raise DuplicateReading()
    return row["id"]


def _insert_bp_bronze(c: psycopg.Connection, i: Any, when: datetime, bronze_id: uuid.UUID) -> uuid.UUID:
    """The Silver row before migration 0035 (no id, pulse or note columns). The entry id is the Bronze row's id. A soft-deleted reading
    at the same time is brought back with the new numbers; a live one raises DuplicateReading."""
    row = c.execute(
        """insert into blood_pressure_readings (user_id, recorded_at, systolic_mmhg, diastolic_mmhg, source, bronze_id)
           values (%s,%s,%s,%s,'manual',%s)
           on conflict (user_id, recorded_at) do update set systolic_mmhg=excluded.systolic_mmhg, diastolic_mmhg=excluded.diastolic_mmhg,
             source=excluded.source, bronze_id=excluded.bronze_id, deleted_at=null
           where blood_pressure_readings.deleted_at is not null
           returning bronze_id""",
        (current_user(), when, i.systolic, i.diastolic, bronze_id),
    ).fetchone()
    if row is None:
        raise DuplicateReading()
    return row["bronze_id"]


def _edit_bp_in_place(c: psycopg.Connection, old: uuid.UUID, i: Any, when: datetime, payload: dict) -> uuid.UUID | None:
    """Edit after migration 0035: the same row is updated, so the entry keeps its id. None when there is no live reading with that id.

    A new time that a live reading already holds is refused (DuplicateReading). A new time that only a soft-deleted reading holds
    is taken over: that deleted row takes this entry's id and the new values, and this row is soft-deleted under a fresh id, so the
    entry's id never changes and no reading is lost (the Bronze rows keep every version as received)."""
    row = c.execute(
        "select recorded_at from blood_pressure_readings where id=%s and user_id=%s and deleted_at is null for update",
        (old, current_user()),
    ).fetchone()
    if row is None:
        return None
    bronze_id = _bronze(c, "bronze_blood_pressure", payload)
    values = (i.systolic, i.diastolic, i.pulse, _bp_note(i), bronze_id)
    if when != row["recorded_at"]:
        holder = c.execute(
            "select id, deleted_at from blood_pressure_readings where user_id=%s and recorded_at=%s", (current_user(), when),
        ).fetchone()
        if holder is not None and holder["deleted_at"] is None:
            raise DuplicateReading()
        if holder is not None:
            c.execute("update blood_pressure_readings set id=gen_random_uuid(), deleted_at=now() where id=%s and user_id=%s", (old, current_user()))
            c.execute(
                """update blood_pressure_readings set id=%s, systolic_mmhg=%s, diastolic_mmhg=%s, pulse=%s, note=%s, source='manual',
                   bronze_id=%s, deleted_at=null, updated_at=now() where id=%s""",
                (old, *values, holder["id"]),
            )
            _processed(c, "bronze_blood_pressure", bronze_id)
            return old
    try:
        c.execute(
            """update blood_pressure_readings set recorded_at=%s, systolic_mmhg=%s, diastolic_mmhg=%s, pulse=%s, note=%s, source='manual',
               bronze_id=%s, updated_at=now() where id=%s and user_id=%s""",
            (when, *values, old, current_user()),
        )
    except psycopg.errors.UniqueViolation:
        # another reading took this time between the check and the update
        raise DuplicateReading()
    _processed(c, "bronze_blood_pressure", bronze_id)
    return old


def _log_event(c: psycopg.Connection, event: str, entry_id: uuid.UUID) -> None:
    """The event log records that something happened: the kind and the id, never the values."""
    c.execute(
        "insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s,'user',%s,'blood_pressure_readings',%s,%s::jsonb)",
        (current_user(), event, entry_id, json.dumps({"kind": "blood_pressure"})),
    )


def _bp_entry(r: dict) -> dict:
    return {"id": str(r["id"]), "measured_at": r["measured_at"].isoformat(), "systolic": r["systolic"], "diastolic": r["diastolic"],
            "pulse": r["pulse"], "note": r["note"]}


def create_blood_pressure(i: Any) -> dict:
    when = _bp_time(i)
    with tx() as c:
        entry_id = _write_bp(c, i, when, _bp_payload(i, when))
        _log_event(c, "log.blood_pressure.saved", entry_id)
    return {"id": str(entry_id), "day": _local_date(when).isoformat(), "measured_at": when}


def update_blood_pressure(entry_id: str, i: Any) -> dict | None:
    """Edit a reading. The entry keeps its id after migration 0035 (the row is updated in place). Before 0035 the old reading is
    soft-deleted and the new one saved, so the entry gets its new Bronze id, as it always did.
    None when there is no such live reading. Raises ValueError for a malformed id."""
    old = uuid.UUID(entry_id)
    when = _bp_time(i)
    payload = _bp_payload(i, when)
    with tx() as c:
        if blood_pressure.columns_ready(c):
            kept = _edit_bp_in_place(c, old, i, when, payload)
        else:
            gone = c.execute(
                "update blood_pressure_readings set deleted_at=now() where bronze_id=%s and user_id=%s and deleted_at is null returning 1",
                (old, current_user()),
            ).fetchone()
            kept = None if gone is None else _write_bp(c, i, when, payload)
        if kept is None:
            return None
        _log_event(c, "log.blood_pressure.edited", kept)
    return {"id": str(kept), "day": _local_date(when).isoformat(), "measured_at": when}


def get_blood_pressure(entry_id: str) -> dict | None:
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        return None
    with tx() as c:
        row = blood_pressure.get_reading(c, current_user(), eid)
    return _bp_entry(row) if row else None


def delete_entry(entry_id: str) -> bool:
    """Soft-delete (the row stays, `deleted_at` is set) and take the entry off the Gold timeline."""
    eid = uuid.UUID(entry_id)
    with tx() as c:
        r = c.execute("update food_logs set deleted_at=now() where id=%s and user_id=%s and deleted_at is null returning start_at, end_at", (eid, current_user())).fetchone()
        if r:
            c.execute(
                "update timeline_5min set meal_id=null, meal_type=null, food=null, carbs_g=null, protein_g=null, fat_g=null, sugar_g=null, fibre_g=null, sodium_mg=null where user_id=%s and meal_id=%s",
                (current_user(), eid),
            )
            refresh_day(c, _local_date(r["start_at"]))
            return True
        r = c.execute("update exercise_logs set deleted_at=now() where id=%s and user_id=%s and deleted_at is null returning start_at", (eid, current_user())).fetchone()
        if r:
            c.execute("update timeline_5min set exercise_id=null, exercise_type=null, exercise_intensity=null where user_id=%s and exercise_id=%s", (current_user(), eid))
            refresh_day(c, _local_date(r["start_at"]))
            return True
        r = c.execute(
            "update symptom_logs set deleted_at=now() where id=%s and user_id=%s and deleted_at is null returning occurred_at, duration_min, symptom_type, severity",
            (eid, current_user()),
        ).fetchone()
        if r:
            first = _floor(r["occurred_at"])
            n = math.ceil(r["duration_min"] / 5) if r["duration_min"] else 1
            buckets = [first + BUCKET * k for k in range(max(n, 1))]
            c.execute(
                """update timeline_5min set symptom_type=null, symptom_severity=null, symptom_duration_min=null, symptom_note=null
                   where user_id=%s and bucket_start = any(%s) and symptom_type=%s::symptom_kind and symptom_severity=%s""",
                (current_user(), buckets, r["symptom_type"], r["severity"]),
            )
            refresh_day(c, _local_date(r["occurred_at"]))
            return True
        r = c.execute("update wellbeing_logs set deleted_at=now() where id=%s and user_id=%s and deleted_at is null returning recorded_at", (eid, current_user())).fetchone()
        if r:
            c.execute(
                "update timeline_5min set mood=null, stress_self=null, sleep_quality=null, energy=null where user_id=%s and bucket_start=%s",
                (current_user(), _floor(r["recorded_at"])),
            )
            refresh_day(c, _local_date(r["recorded_at"]))
            return True
        # a blood pressure entry's id is its Silver id (after migration 0035) or its Bronze row's id (before it); its Bronze row stays as received
        r = c.execute(
            f"update blood_pressure_readings set deleted_at=now() where {blood_pressure.id_column(c)}=%s and user_id=%s and deleted_at is null returning recorded_at",
            (eid, current_user()),
        ).fetchone()
        if r:
            _log_event(c, "log.blood_pressure.deleted", eid)
            return True
    return False


# ----------------------------------------------------------------------------------------------- reads
def _when_label(dt: datetime) -> str:
    local = _aware(dt).astimezone(TZ)
    today = datetime.now(TZ).date()
    clock = local.strftime("%I:%M %p").lstrip("0").lower()
    if local.date() == today:
        return clock
    if local.date() == today - timedelta(days=1):
        return "Yesterday"
    return local.strftime("%d %b")


def recent(limit: int = 30) -> list[dict]:
    with tx() as c:
        bp = blood_pressure.recent_select(c)
        rows = c.execute(
            """select * from (
                 select id, 'meal' kind, start_at at, food title, carbs_g n1, null::numeric n2, estimated_by::text t1 from food_logs where user_id=%(u)s and deleted_at is null
                 union all
                 select id, 'workout', start_at, type::text, intensity, extract(epoch from end_at-start_at)/60, note from exercise_logs where user_id=%(u)s and deleted_at is null
                 union all
                 select id, 'symptom', occurred_at, symptom_type::text, severity, duration_min, note from symptom_logs where user_id=%(u)s and deleted_at is null
                 union all
                 select id, 'checkin', recorded_at, 'checkin', mood, stress_self, null from wellbeing_logs where user_id=%(u)s and deleted_at is null
                 union all
                 """ + bp + """
               ) x order by at desc limit %(l)s""",
            {"u": current_user(), "l": limit},
        ).fetchall()
    out = []
    for r in rows:
        k, at = r["kind"], r["at"]
        if k == "meal":
            title = r["title"]
            # the person's own numbers are labelled "Your numbers"; photo-reading numbers are labelled "Estimated"
            typed = r["t1"] == "user"
            if typed:
                detail = f"Your numbers, {round(_num(r['n1']))} g carbs" if r["n1"] is not None else "Your numbers"
            else:
                detail = f"Estimated {round(_num(r['n1']))} g carbs" if r["n1"] is not None else "Logged"
        elif k == "workout":
            mins = round(_num(r["n2"]))
            title = f"{r['t1'] or EXERCISE_WORD.get(r['title'], 'Exercise')}, {mins} min"
            detail = INTENSITY_WORD.get(int(r["n1"]), "") if r["n1"] is not None else "Not rated"
        elif k == "symptom":
            title = (r["t1"] or r["title"]).split(" · ")[0]
            dur = f", {r['n2']} min" if r["n2"] else ""
            detail = f"Severity {r['n1']} of 5{dur}"
        elif k == "blood_pressure":
            title = f"{r['title']} over {round(_num(r['n1']))} mmHg"
            detail = f"Pulse {round(_num(r['n2']))} a minute" if r["n2"] is not None else "No pulse entered"
        else:
            title = "Mood and sleep check-in"
            answers = [f"Mood {r['n1']}" if r["n1"] is not None else None, f"stress {r['n2']}" if r["n2"] is not None else None]
            detail = ", ".join(a for a in answers if a) or "No answers recorded"
        out.append({"id": str(r["id"]), "kind": k, "title": title, "detail": detail, "when": _when_label(at), "date": _local_date(at).isoformat()})
    return out


def _day_counts(c: psycopg.Connection, d: date) -> dict[str, int]:
    q = lambda sql: c.execute(sql, {"u": current_user(), "d": d}).fetchone()["n"]  # noqa: E731
    return {
        "meals": q("select count(*) n from food_logs where user_id=%(u)s and deleted_at is null and (start_at at time zone 'Asia/Singapore')::date=%(d)s"),
        "workout": q("select count(*) n from exercise_logs where user_id=%(u)s and deleted_at is null and (start_at at time zone 'Asia/Singapore')::date=%(d)s"),
        "symptom": q("select count(*) n from symptom_logs where user_id=%(u)s and deleted_at is null and (occurred_at at time zone 'Asia/Singapore')::date=%(d)s"),
        "checkin": q("select count(*) n from wellbeing_logs where user_id=%(u)s and deleted_at is null and (recorded_at at time zone 'Asia/Singapore')::date=%(d)s"),
    }


# When each log is worth asking for (Singapore clock, decimal hours). A prompt appears only inside its window, so it
# never nags at the wrong time of day: sleep and mood are fresh in the morning, meals are asked for around mealtimes,
# a workout in the late afternoon and evening. Outside its window an item is simply "later" with a quiet hint.
MEAL_WINDOWS = [
    (7.0, 10.5, "breakfast", "7 to 10:30 am"),
    (11.5, 14.5, "lunch", "11:30 am to 2:30 pm"),
    (18.0, 21.5, "dinner", "6 to 9:30 pm"),
]
CHECKIN_WINDOW = (6.0, 11.0, "6 to 11 am")
WORKOUT_WINDOW = (16.5, 21.0, "4:30 to 9 pm")


def _hour(now: datetime) -> float:
    return now.hour + now.minute / 60


def _meal_window(h: float) -> tuple[int, tuple] | None:
    """(meal number 1..3, window) when `h` is inside a mealtime window, else None."""
    for i, w in enumerate(MEAL_WINDOWS, start=1):
        if w[0] <= h < w[1]:
            return i, w
    return None


def _until(now: datetime, end_hour: float) -> datetime:
    return now.replace(hour=int(end_hour), minute=int(round((end_hour % 1) * 60)), second=0, microsecond=0)


def _clock(dt: datetime) -> str:
    return _aware(dt).astimezone(TZ).strftime("%I:%M %p").lstrip("0").lower()


def _bp_today(c: psycopg.Connection, day: date) -> dict:
    """Today's blood pressure readings, newest first, with the latest one in plain words for the Log hub."""
    rows = blood_pressure.reading_on_day(c, current_user(), day)
    latest = f"{rows[0]['systolic']} over {rows[0]['diastolic']} at {_clock(rows[0]['measured_at'])}" if rows else None
    return {"count": len(rows), "latest": latest, "readings": [_bp_entry(r) for r in rows]}


def progress() -> dict:
    now = datetime.now(TZ)
    today = now.date()
    with tx() as c:
        n = _day_counts(c, today)
        wk_start = today - timedelta(days=today.weekday())
        wk = c.execute(
            """select coalesce(sum(extract(epoch from end_at-start_at)/60) filter (where intensity>=3),0) mod_min,
                      count(*) filter (where type='strength') strength
               from exercise_logs where user_id=%(u)s and deleted_at is null and (start_at at time zone 'Asia/Singapore')::date >= %(s)s""",
            {"u": current_user(), "s": wk_start},
        ).fetchone()
        bp = _bp_today(c, today)
        days = c.execute(
            """select d from (
                 select (start_at at time zone 'Asia/Singapore')::date d from food_logs where user_id=%(u)s and deleted_at is null
                 union select (start_at at time zone 'Asia/Singapore')::date from exercise_logs where user_id=%(u)s and deleted_at is null
                 union select (occurred_at at time zone 'Asia/Singapore')::date from symptom_logs where user_id=%(u)s and deleted_at is null
                 union select (recorded_at at time zone 'Asia/Singapore')::date from wellbeing_logs where user_id=%(u)s and deleted_at is null) x""",
            {"u": current_user()},
        ).fetchall()
    logged = {r["d"] for r in days}
    streak, d = 0, today if today in logged else today - timedelta(days=1)
    while d in logged:
        streak += 1
        d -= timedelta(days=1)

    h = _hour(now)
    mod_min, strength = int(wk["mod_min"]), int(wk["strength"])

    # meals: due only inside a mealtime window, and only if that meal has not been logged yet
    meals_done = n["meals"] >= GOAL_MEALS
    in_meal = _meal_window(h)
    meal_due = in_meal is not None and n["meals"] < in_meal[0]
    upcoming = next((w for w in MEAL_WINDOWS if w[0] > h), None)
    if meals_done:
        meal_hint, meal_window, meal_prompt = "All three logged", None, None
    elif meal_due:
        _, w = in_meal
        meal_hint, meal_window = f"Usually {w[3]}", w[3]
        meal_prompt = f"Time for {w[2]}. Take a photo before you eat."
    else:
        meal_hint = f"Next: {upcoming[2]}, around {upcoming[3]}" if upcoming else "Photo of each meal, and tap when you finish eating"
        meal_window, meal_prompt = (upcoming[3] if upcoming else None), None

    # mood and sleep: morning only (how you slept is freshest on waking)
    ck_done = n["checkin"] >= 1
    ck_due = (not ck_done) and CHECKIN_WINDOW[0] <= h < CHECKIN_WINDOW[1]
    if ck_done:
        ck_hint, ck_prompt = "Done for today", None
    elif ck_due:
        ck_hint, ck_prompt = "Thirty seconds, best in the morning", "How did you sleep? A thirty-second check-in."
    elif h < CHECKIN_WINDOW[0]:
        ck_hint, ck_prompt = f"Opens at {CHECKIN_WINDOW[0]:.0f} am", None
    else:
        ck_hint, ck_prompt = f"Best done in the morning, {CHECKIN_WINDOW[2]}", None

    # workout: late afternoon and evening, only while the week's goal is still open
    wo_done = n["workout"] >= 1
    wo_due = (not wo_done) and WORKOUT_WINDOW[0] <= h < WORKOUT_WINDOW[1] and mod_min < GOAL_MODERATE_MIN
    wo_hint = f"Logged today. {mod_min} of {GOAL_MODERATE_MIN} min this week" if wo_done else f"{mod_min} of {GOAL_MODERATE_MIN} active min this week"
    wo_prompt = "A good time to move. A walk counts." if wo_due else None

    items = [
        {"key": "meals", "label": "Meals", "count": n["meals"], "target": GOAL_MEALS, "done": meals_done, "to": "E2",
         "hint": meal_hint, "window": meal_window, "prompt": meal_prompt, "status": "done" if meals_done else ("due" if meal_due else "later")},
        {"key": "checkin", "label": "Mood and sleep", "count": n["checkin"], "target": 1, "done": ck_done, "to": "E5",
         "hint": ck_hint, "window": CHECKIN_WINDOW[2] if not ck_done else None, "prompt": ck_prompt, "status": "done" if ck_done else ("due" if ck_due else "later")},
        {"key": "workout", "label": "Workout", "count": n["workout"], "target": 1, "done": wo_done, "to": "F1",
         "hint": wo_hint, "window": WORKOUT_WINDOW[2] if not wo_done else None, "prompt": wo_prompt, "status": "done" if wo_done else ("due" if wo_due else "later")},
        {"key": "symptom", "label": "Symptoms", "count": n["symptom"], "target": None, "done": n["symptom"] >= 1, "to": "E4",
         "hint": "Only if you felt something" if n["symptom"] < 1 else f"{n['symptom']} logged today", "window": None, "prompt": None,
         "status": "done" if n["symptom"] >= 1 else "later"},
    ]
    core = items[:3]
    # "next up": whatever is due now; otherwise the next thing that can still be done today (a morning check-in or an
    # evening workout whose window has passed is not offered as "next")
    still_open = {"meals": True, "checkin": h < CHECKIN_WINDOW[1], "workout": h < WORKOUT_WINDOW[1]}
    nxt = next((i for i in core if i["status"] == "due"), None) or next((i for i in core if not i["done"] and still_open[i["key"]]), None)
    return {
        "date": today.isoformat(), "items": items, "done": sum(1 for i in core if i["done"]), "total": len(core),
        "streak_days": streak, "week_activity_min": mod_min, "week_activity_goal": GOAL_MODERATE_MIN,
        "week_strength_sessions": strength, "week_strength_goal": GOAL_STRENGTH, "next_up": nxt, "blood_pressure": bp,
    }


def week_workouts() -> dict:
    today = datetime.now(TZ).date()
    wk_start = today - timedelta(days=today.weekday())
    with tx() as c:
        agg = c.execute(
            """select coalesce(sum(extract(epoch from end_at-start_at)/60) filter (where intensity>=3),0) mod_min,
                      count(*) filter (where type='strength') strength, count(*) n
               from exercise_logs where user_id=%(u)s and deleted_at is null and (start_at at time zone 'Asia/Singapore')::date >= %(s)s""",
            {"u": current_user(), "s": wk_start},
        ).fetchone()
    rec = [e for e in recent(60) if e["kind"] == "workout"][:6]
    return {"activeMin": int(agg["mod_min"]), "goalMin": GOAL_MODERATE_MIN, "strengthSessions": int(agg["strength"]), "goalStrength": GOAL_STRENGTH, "sessions": int(agg["n"]), "recent": rec}


def heart_rate_and_age(start: datetime, end: datetime) -> tuple[list[tuple[datetime, float]], float | None]:
    """Watch heart-rate samples in a window and the person's age; empty and None when there is no watch data or profile."""
    with tx() as c:
        rows = c.execute(
            "select recorded_at, heart_rate_bpm from watch_readings where user_id=%s and recorded_at between %s and %s and heart_rate_bpm is not null",
            (current_user(), _aware(start), _aware(end)),
        ).fetchall()
        prof = c.execute("select birth_year from user_profile where user_id=%s", (current_user(),)).fetchone()
    age = float(datetime.now(TZ).year - prof["birth_year"]) if prof and prof["birth_year"] else None
    return [(r["recorded_at"], float(r["heart_rate_bpm"])) for r in rows], age


def medicine_names(c: psycopg.Connection, user_id: Any) -> list[str]:
    """Names of the person's medicines that are not deleted. Read only; used for the beta-blocker rule in workout effort."""
    rows = c.execute("select name from medications where user_id=%s and deleted_at is null", (user_id,)).fetchall()
    return [r["name"] for r in rows]


def active_medicine_names() -> list[str]:
    with tx() as c:
        return medicine_names(c, current_user())


def glucose_context() -> dict | None:
    """The newest sensor reading, so a symptom can be saved with the glucose at that moment. None if no sensor data."""
    with tx() as c:
        rows = c.execute(
            "select recorded_at, glucose_mmol from cgm_readings where user_id=%s and quality_ok order by recorded_at desc limit 4", (current_user(),)
        ).fetchall()
    if not rows:
        return None
    latest = _num(rows[0]["glucose_mmol"])
    delta = latest - _num(rows[-1]["glucose_mmol"]) if len(rows) > 1 else 0
    trend = "rising" if delta > 0.5 else "falling" if delta < -0.5 else "steady"
    return {"v": latest, "trend": trend, "at": rows[0]["recorded_at"].isoformat()}


def food_response(food: str) -> dict:
    """How this person's glucose rose after meals with similar names, from the Gold `meal_response` table."""
    words = [w for w in "".join(ch.lower() if ch.isalpha() else " " for ch in food).split() if len(w) > 2]
    if not words:
        return {"kind": "learning", "text": "Still learning how you respond to this meal.", "n": 0, "range": None}
    with tx() as c:
        rows = c.execute(
            """select m.rise_mmol from meal_response m join food_logs f on f.id=m.food_log_id
               where m.user_id=%s and f.deleted_at is null and m.rise_mmol is not null and f.food ilike any(%s)""",
            (current_user(), [f"%{w}%" for w in words]),
        ).fetchall()
        allrises = c.execute("select rise_mmol from meal_response where user_id=%s and rise_mmol is not null", (current_user(),)).fetchall()
    rises = sorted(_num(r["rise_mmol"]) for r in rows)
    if len(rises) < 2:
        return {"kind": "learning", "text": "Still learning how you respond to this meal. We need at least 2 times.", "n": len(rises), "range": None}
    pool = sorted(_num(r["rise_mmol"]) for r in allrises)
    avg = sum(rises) / len(rises)
    rank = sum(1 for v in pool if v <= avg) / len(pool)
    rng = [round(rises[0], 1), round(rises[-1], 1)]
    if rank >= 0.66:
        return {"kind": "higher", "text": "After this kind of meal your glucose rose more than after most of your meals.", "n": len(rises), "range": rng}
    if rank <= 0.33:
        return {"kind": "lower", "text": "After this kind of meal your glucose rose less than after most of your meals.", "n": len(rises), "range": rng}
    return {"kind": "similar", "text": "After this kind of meal your glucose rose about as much as after most of your meals.", "n": len(rises), "range": rng}


# ----------------------------------------------------------------------------------------------- notifications
EXEMPT_PREFIXES = ("dose-", "urgent-", "start-")  # dose reminders (inside their window), urgent messages and the first "get started" notices never count towards the cap or wait for quiet hours
# The first notifications a new person sees, in this order: how to get started. Each is made once, stays on top of the Reminders page until the
# thing is done, and is then marked done. key -> (order, thing to log, screen)
STARTERS = {"start-medication": (0, "medication", "H1"), "start-meal": (1, "meal", "E2"), "start-checkin": (2, "checkin", "E5")}


def is_exempt(key: str) -> bool:
    return key.startswith(EXEMPT_PREFIXES)


def in_quiet_hours(now: datetime) -> bool:
    return now.hour >= settings.quiet_start_hour or now.hour < settings.quiet_end_hour


def slots_left(created_today: int) -> int:
    return max(0, settings.nudge_daily_cap - created_today)


# The lunch reminder has one slot a day. The "Log your lunch" reminder (meal-2-<day>, from MEAL_WINDOWS) and the lunch ideas
# (lunch-<day>, from nutritionstore.nutrition_nudges) are written by two code paths; whichever is stored first takes the slot.
LUNCH_MEAL_INDEX = 2


def lunch_slot_keys(today: str) -> set[str]:
    return {f"meal-{LUNCH_MEAL_INDEX}-{today}", f"lunch-{today}"}


def reminder_time(key: str, day: date, lunch_start_min: int) -> datetime | None:
    """The time a reminder is due, so the time it shows is the same on every request. None for a reminder with no fixed time
    (it then keeps the moment it was written)."""
    hour: float | None = None
    m = re.match(r"^meal-(\d+)-", key)
    if m and 1 <= int(m.group(1)) <= len(MEAL_WINDOWS):
        hour = MEAL_WINDOWS[int(m.group(1)) - 1][0]
    elif key.startswith("lunch-"):
        return datetime(day.year, day.month, day.day, tzinfo=TZ) + timedelta(minutes=lunch_start_min)
    elif key.startswith("checkin-"):
        hour = CHECKIN_WINDOW[0]
    elif key.startswith("workout-"):
        hour = WORKOUT_WINDOW[0]
    if hour is None:
        return None
    return datetime(day.year, day.month, day.day, tzinfo=TZ) + timedelta(minutes=round(hour * 60))


def notifications(create: bool = True, history: bool = False) -> list[dict]:
    """Reminders from the day's progress, kept in the `notifications` table so opening them is recorded. A reminder is only
    created inside its time window and is hidden again once the window has passed, so nothing nags at the wrong time.
    With create=False nothing is written (used for a GET about a person whose reminders must not change from a page view).
    With history=True (the Reminders page) nothing is hidden for being old, done or past its window: the last 45 days of in-app reminders
    come back newest first, each with its local `date` and `current` (still waiting and inside its window). Home keeps the short list.
    The whole call shares ONE database connection."""
    with one_connection():
        return _notifications(create, history)


def _notifications(create: bool, history: bool = False) -> list[dict]:
    p = progress()
    now = datetime.now(TZ)
    h = _hour(now)
    today = p["date"]
    lang = texts.person_language(current_user())   # the wording follows the person's language; keys and routes do not
    from app.db import nutritionstore

    lunch_start_min = nutritionstore.lunch_window(current_user())[0]
    lunch_slot = lunch_slot_keys(today)
    want: list[tuple[str, str, str, str, str, datetime]] = []  # key, kind, title, body, route, valid until
    items = {i["key"]: i for i in p["items"]}
    m = items["meals"]
    win = _meal_window(h)
    if m["status"] == "due" and win is not None:
        i, w = win
        want.append((f"meal-{i}-{today}", "nudge", texts.tr(lang, "nudge.meal.title", meal=texts.label(lang, "meal.word", w[2])),
                     texts.tr(lang, "nudge.meal.body"), "E2", _until(now, w[1])))
    if items["checkin"]["status"] == "due":
        want.append((f"checkin-{today}", "checkin", texts.tr(lang, "nudge.checkin.title"), texts.tr(lang, "nudge.checkin.body"), "E5", _until(now, CHECKIN_WINDOW[1])))
    if items["workout"]["status"] == "due":
        want.append((f"workout-{today}", "nudge", texts.tr(lang, "nudge.workout.title"),
                     texts.tr(lang, "nudge.workout.body", done=p["week_activity_min"], goal=p["week_activity_goal"]), "F1", _until(now, WORKOUT_WINDOW[1])))
    # nutrition and activity nudges: templates over the person's own data, guarded before they are stored (nutritionstore)
    with tx() as c:
        have_keys = {r["k"] for r in c.execute("select payload->>'key' k from notifications where user_id=%s", (current_user(),)).fetchall()}
        lunch_today = c.execute(
            "select count(*) n from food_logs where user_id=%s and deleted_at is null and meal_type='lunch' and (start_at at time zone 'Asia/Singapore')::date=%s",
            (current_user(), now.date()),
        ).fetchone()["n"]
        created_today = sum(
            1 for r in c.execute("select payload->>'key' k from notifications where user_id=%s and (scheduled_for at time zone 'Asia/Singapore')::date=%s", (current_user(), now.date())).fetchall()
            if r["k"] and not is_exempt(r["k"])
        )
        # has the person ever logged each of the first things? (a medicine saved, a meal, a mood and sleep check-in)
        logged_ever = {
            "medication": c.execute("select count(*) n from medications where user_id=%s and deleted_at is null", (current_user(),)).fetchone()["n"] > 0,
            "meal": c.execute("select count(*) n from food_logs where user_id=%s and deleted_at is null", (current_user(),)).fetchone()["n"] > 0,
            "checkin": c.execute("select count(*) n from wellbeing_logs where user_id=%s and deleted_at is null", (current_user(),)).fetchone()["n"] > 0,
        }
    # the daily cap and quiet hours apply to new items only; what is already there stays until it is acted on or expires
    # dose reminders inside their window come from the learning loop and are exempt from the cap and quiet hours (their keys start "dose-")
    from app.agents import hooks

    if create:
        try:
            hooks.close_taken_anchors(current_user(), now)
        except Exception:
            logger.exception("could not close anchored reminders whose dose is done")
        want += hooks.dose_nudges(current_user(), now, have_keys)
        # the "get started" notices: one for each first thing not logged yet, made once (a person who already has it is never given it again)
        for skey, (_order, what, route) in STARTERS.items():
            if not logged_ever[what] and skey not in have_keys:
                want.append((skey, "nudge", texts.tr(lang, f"nudge.start.{what}.title"), texts.tr(lang, f"nudge.start.{what}.body"), route, now + timedelta(days=365)))
    else:
        want = []
    if lunch_slot & have_keys:
        want = [w for w in want if w[0] not in lunch_slot]   # today's lunch reminder is already there
    if create and any(w[0] in lunch_slot for w in want):
        # the plain "Log your lunch" reminder is due now: when there are lunch ideas that suit the person, the ideas (which also lead to
        # logging the lunch) take its place, so the lunch reminder, and its email, is the personalised one. One item for one item.
        try:
            idea = nutritionstore.lunch_ideas_nudge(current_user(), have_keys, lunch_today, now)
        except Exception:
            logger.exception("lunch ideas failed; the plain lunch reminder stays")
            idea = None
        if idea:
            want = [w for w in want if w[0] not in lunch_slot] + [idea]
    quiet, left, keep = in_quiet_hours(now), slots_left(created_today), []
    for w in want:
        if w[0] in have_keys or is_exempt(w[0]):
            keep.append(w)
        elif not quiet and left > 0:
            keep.append(w)
            left -= 1
    want = keep
    if create and not quiet and left > 0:
        try:
            # a lunch reminder in this same pass also takes the lunch slot, so the lunch ideas do not add a second one
            lunch_taken = have_keys | (lunch_slot if any(w[0] in lunch_slot for w in want) else set())
            want += nutritionstore.nutrition_nudges(current_user(), lunch_taken, lunch_today, now, max_new=left)
            want += hooks.extra_nudges(current_user(), now, have_keys, max(0, left - len([w for w in want if not is_exempt(w[0])])))
        except Exception:
            logger.exception("nutrition nudges failed; the other reminders are unaffected")
    with tx() as c:
        # two requests (or a request and the minute tick) can write at the same time: the lock makes each check-then-insert one step
        if create:
            c.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"notifications:{current_user()}",))
        for key, kind, title, body, to, until in want:
            have = c.execute("select 1 from notifications where user_id=%s and payload->>'key'=%s", (current_user(), key)).fetchone()
            if not have and key in lunch_slot:
                have = c.execute("select 1 from notifications where user_id=%s and payload->>'key' = any(%s) limit 1", (current_user(), sorted(lunch_slot))).fetchone()
            if not have:
                at = reminder_time(key, now.astimezone(TZ).date(), lunch_start_min) or now
                c.execute(
                    "insert into notifications (user_id, kind, scheduled_for, sent_at, channel, payload) values (%s,%s::notification_kind,%s,now(),'in_app',%s::jsonb)",
                    (current_user(), kind, at, json.dumps({"key": key, "title": title, "body": body, "to": to, "until": until.isoformat()})),
                )
        # a reminder is done once the thing it asked for is logged
        for row in c.execute("select id, payload from notifications where user_id=%s and acted_at is null and payload ? 'key'", (current_user(),)).fetchall():
            key = row["payload"]["key"]
            done = (key in STARTERS and logged_ever[STARTERS[key][1]]) or \
                   (key.startswith("meal-") and key.endswith(today) and m["count"] >= int(key.split("-")[1])) or \
                   (key.startswith("checkin-") and key.endswith(today) and items["checkin"]["done"]) or \
                   (key.startswith("workout-") and key.endswith(today) and items["workout"]["done"]) or                    (key.startswith("activity-") and key.endswith(today) and items["workout"]["done"]) or                    (key.startswith("lunch-") and key.endswith(today) and lunch_today >= 1)
            if done and create:
                c.execute("update notifications set acted_at=now(), action='logged' where id=%s", (row["id"],))
        if history:
            rows = c.execute(
                "select id, kind, scheduled_for, opened_at, acted_at, payload from notifications where user_id=%s and channel='in_app' and kind <> 'urgent' "
                "and scheduled_for > now() - interval '45 days' and scheduled_for <= now() + interval '2 hours' order by scheduled_for desc limit 80", (current_user(),)
            ).fetchall()
        else:
            rows = c.execute(
                "select id, kind, scheduled_for, opened_at, acted_at, payload from notifications where user_id=%s and acted_at is null order by scheduled_for desc limit 30", (current_user(),)
            ).fetchall()

    def live(r) -> bool:
        until = r["payload"].get("until")
        if until:
            return now < datetime.fromisoformat(until)
        # no expiry stored (older rows): a reminder belongs to the day in its key, so it is not shown on a later day
        key = r["payload"].get("key", "")
        return not key[-10:].count("-") == 2 or key[-10:] >= today

    def text(r) -> tuple[str, str]:
        p = r["payload"]
        title, body = p.get("title", ""), p.get("body", "")
        # older records (the seeded history) carry no wording: a refill row names the medicine, anything else with no words is not shown
        if not title and r["kind"] == "refill" and p.get("medication"):
            return texts.tr(lang, "refill.title", name=p["medication"]), texts.tr(lang, "refill.low")
        # a reminder stored in English is shown in the language of this request, using the catalog's reviewed wording
        return texts.retranslate(texts.request_lang(), title), texts.retranslate(texts.request_lang(), body)

    out = []
    for r in rows:
        if not history and not live(r):
            continue
        title, body = text(r)
        if not title and not body:
            continue
        item = {"id": str(r["id"]), "kind": r["kind"], "title": title, "body": body,
                "when": _when_label(r["scheduled_for"]), "to": r["payload"].get("to"), "unread": r["opened_at"] is None}
        if history:
            local = _aware(r["scheduled_for"]).astimezone(TZ)
            item["when"] = local.strftime("%I:%M %p").lstrip("0").lower()      # the day is the heading above it, so the row shows only the time
            item["date"] = local.date().isoformat()
            item["pinned"] = STARTERS[r["payload"]["key"]][0] if r["payload"].get("key") in STARTERS else None
            item["current"] = r["acted_at"] is None and live(r)
        out.append(item)
    return out


def notification_uuid(nid: str) -> uuid.UUID | None:
    """The reminder id as a UUID, or None when the text is not one (the route answers 404, never 500)."""
    try:
        return uuid.UUID(nid)
    except (ValueError, AttributeError, TypeError):
        return None


def dismiss_notification(nid: str) -> None:
    """"Not for me": the reminder leaves the list and the learning loop reads action='dismissed' (an offset or idea the person does not want is excluded)."""
    with tx() as c:
        row = c.execute("update notifications set acted_at = coalesce(acted_at, now()), action = coalesce(action, 'dismissed') where id = %s and user_id = %s "
                        "returning payload->>'key' k", (uuid.UUID(nid), current_user())).fetchone()
    # a dismissed preventive check is remembered as an excluded arm, so that check is not offered again (app/agents/preventive.py)
    m = re.match(r"^preventive-(.+)-\d{4}-W\d{2}$", (row or {}).get("k") or "")
    if m:
        from app.db import nutritionstore

        nutritionstore.policy_reject(current_user(), "template", f"preventive:{m.group(1)}")


def open_notification(nid: str) -> None:
    with tx() as c:
        c.execute("update notifications set opened_at=coalesce(opened_at, now()) where id=%s and user_id=%s", (uuid.UUID(nid), current_user()))
