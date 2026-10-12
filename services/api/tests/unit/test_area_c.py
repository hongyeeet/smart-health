"""Fix wave, area C: data windows, slow endpoints, GETs that write, unknown stays unknown. No database: small fakes stand in for it."""
import contextlib
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.api.routers import home
from app.core.errors import InvalidTransition, ValidationFailed
from app.db import logstore, memorystore, nutritionstore
from app.services import care, dose_store, insights, medication_stock, onboarding

TZ = ZoneInfo("Asia/Singapore")
NOW = datetime(2026, 10, 12, 19, 0, tzinfo=TZ)


class Cur:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.rowcount = 1

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class Fake:
    """Records every statement; `answers` maps a word in the SQL to the rows to return."""

    def __init__(self, answers=None):
        self.sql, self.params, self.answers = [], [], answers or {}

    def execute(self, sql, params=None):
        self.sql.append(sql)
        self.params.append(params)
        for word, rows in self.answers.items():
            if word in sql:
                return Cur(rows)
        return Cur([])


# ---------------------------------------------------------------- 1. the anchor
MR_TAN_DAYS = {"glucose": date(2026, 10, 2), "steps": date(2026, 10, 2), "sleep": date(2026, 10, 2), "answered": date(2026, 10, 2), "logged": date(2026, 10, 10)}


def test_a_sensor_screen_ends_on_its_last_sensor_day_not_on_a_stray_log():
    conn = Fake({"daily_summary": [MR_TAN_DAYS]})
    today = date(2026, 10, 12)
    assert insights.anchor(conn, "u", today, "glucose") == date(2026, 10, 2)
    assert insights.anchor(conn, "u", today, "sleep") == date(2026, 10, 2)
    assert insights.anchor(conn, "u", today) == date(2026, 10, 2)          # the overall end ignores the stray meal and check-in on 10 Oct


def test_the_overall_end_ignores_doses_that_are_only_waiting_for_a_tap():
    conn = Fake({"daily_summary": [{"glucose": date(2026, 10, 2), "steps": None, "sleep": None, "answered": None, "logged": None}]})
    assert insights.anchor(conn, "u", date(2026, 10, 12)) == date(2026, 10, 2)
    assert "doses_scheduled" not in conn.sql[0]                           # a scheduled (pending) dose is never data


def test_a_metric_with_no_sensor_falls_back_to_the_last_log_and_then_to_today():
    only_logs = Fake({"daily_summary": [{"glucose": None, "steps": None, "sleep": None, "answered": None, "logged": date(2026, 10, 9)}]})
    assert insights.anchor(only_logs, "u", date(2026, 10, 12), "glucose") == date(2026, 10, 9)
    nothing = Fake({"daily_summary": [{"glucose": None, "steps": None, "sleep": None, "answered": None, "logged": None}]})
    assert insights.anchor(nothing, "u", date(2026, 10, 12)) == date(2026, 10, 12)


def test_every_insights_screen_asks_for_its_own_metric(monkeypatch):
    asked = []
    monkeypatch.setattr(insights, "anchor", lambda conn, user, today, metric=None: asked.append(metric) or date(2026, 10, 2))
    for fn in (insights.glucose, insights.activity, insights.sleep):
        with contextlib.suppress(Exception):
            fn(Fake(), "u", 7, date(2026, 10, 12))
    assert asked == ["glucose", "steps", "sleep"]


# ---------------------------------------------------------------- 4. daily_summary writes NULL, not 0
def test_a_day_with_nothing_logged_is_stored_as_unknown():
    c = Fake({"from food_logs": [{"n": 0, "carbs": None, "protein": None, "fat": None, "sugar": None, "fibre": None, "sodium": None}],
              "from exercise_logs": [{"n": 0, "mins": 0}], "from symptom_logs": [{"n": 0, "worst": None}],
              "from wellbeing_logs": [{"mood": None, "stress": None, "energy": None, "sleepq": None}]})
    logstore.refresh_day(c, date(2026, 10, 10))
    values = c.params[-1]
    assert values["mn"] is None and values["emin"] is None and values["en"] is None and values["sn"] is None


def test_a_day_with_a_logged_meal_keeps_its_count():
    c = Fake({"from food_logs": [{"n": 2, "carbs": 80, "protein": 20, "fat": 10, "sugar": 5, "fibre": 3, "sodium": 900}],
              "from exercise_logs": [{"n": 1, "mins": 30.0}], "from symptom_logs": [{"n": 0, "worst": None}],
              "from wellbeing_logs": [{"mood": None, "stress": None, "energy": None, "sleepq": None}]})
    logstore.refresh_day(c, date(2026, 10, 10))
    assert c.params[-1]["mn"] == 2 and c.params[-1]["emin"] == 30 and c.params[-1]["en"] == 1


def test_the_calendar_shows_a_dash_for_an_unknown_meal_count():
    rows = insights.measure_grid({date(2026, 10, 10): {"meals_n": None, "exercise_min": None}}, [date(2026, 10, 10)], {})
    cells = {r["key"]: r["cells"][0] for r in rows}
    assert cells["meals"]["label"] == "–" and cells["activity"]["label"] == "–"


# ---------------------------------------------------------------- 2. GETs that do not write
def sched(at: time, ended=None):
    return ("s1", "m1", at, datetime(2026, 1, 1, tzinfo=TZ), "Metformin", "500 mg", "prescription", None, Decimal(1), ended)


def test_nothing_is_stored_for_mr_tan():
    c = Fake()
    assert dose_store.ensure_rows(c, str(logstore.MR_TAN_USER), NOW) == 0
    assert c.sql == []


def test_only_todays_open_doses_are_stored_for_other_people():
    c = Fake({"medication_schedule": [sched(time(20, 0)), sched(time(8, 0))]})
    made = dose_store.ensure_rows(c, "someone-else", NOW)
    inserts = [p for s, p in zip(c.sql, c.params) if s.startswith("insert into medication_log")]
    assert made == 1 and len(inserts) == 1                                  # 8 am is over; tomorrow is not stored
    assert inserts[0][3] == datetime(2026, 10, 12, 20, 0, tzinfo=TZ)
    assert "as_needed is not true" in c.sql[0] and "end_date" in c.sql[0] and "deleted_at is null" in c.sql[0]


def test_the_next_dose_is_worked_out_in_memory_without_a_row():
    c = Fake({"medication_schedule s": [sched(time(8, 0))]})
    up = dose_store._upcoming_in_memory(c, "u", NOW, set())
    assert [a for a, _ in up] == [datetime(2026, 10, 13, 8, 0, tzinfo=TZ)]
    assert not any(s.startswith("insert") for s in c.sql)


def test_an_ended_medicine_has_no_next_dose():
    c = Fake({"medication_schedule s": [sched(time(8, 0), ended=date(2026, 9, 19))]})
    assert dose_store._upcoming_in_memory(c, "u", NOW, set()) == []


def test_taking_a_dose_back_gives_the_pill_back(monkeypatch):
    calls = []
    monkeypatch.setattr(dose_store, "_load", lambda conn, user, did: ("lid", "taken", NOW, "mid", "n", "s"))
    monkeypatch.setattr(medication_stock, "stock_ready", lambda conn: True)
    monkeypatch.setattr(medication_stock, "dose_untaken", lambda *a: calls.append(a))
    c = Fake()
    assert dose_store.mark_untaken(c, "u", "lid", NOW) == "pending"
    assert len(calls) == 1 and any("status = 'pending'" in s for s in c.sql)


def test_only_a_taken_dose_can_be_taken_back(monkeypatch):
    monkeypatch.setattr(dose_store, "_load", lambda conn, user, did: ("lid", "pending", NOW, "mid", "n", "s"))
    with pytest.raises(InvalidTransition):
        dose_store.mark_untaken(Fake(), "u", "lid", NOW)


# ---------------------------------------------------------------- 3. the banner
def _stub_banner(monkeypatch, calls):
    monkeypatch.setattr(home.logstore, "one_connection", contextlib.nullcontext)
    monkeypatch.setattr(home.logstore, "progress", lambda: {"items": [{"key": "meals", "status": "later"}]})
    monkeypatch.setattr(home.logstore, "current_user", lambda: "u")
    monkeypatch.setattr(home.logstore, "current_user_key", lambda: "key-1")
    home._cache.clear()

    def habits(uid, **kw):
        calls.append(kw)
        return []

    monkeypatch.setattr(home.nutritionstore, "food_habits", habits)


def test_the_banner_never_asks_for_swaps(monkeypatch):
    calls = []
    _stub_banner(monkeypatch, calls)
    home.cached_banner(now=0.0)
    assert calls[0]["swaps"] is False and calls[0]["classify_budget"] == home.FOOD_TYPE_BUDGET


def test_the_banner_is_reused_for_a_minute_and_until_the_person_logs(monkeypatch):
    calls = []
    _stub_banner(monkeypatch, calls)
    home.cached_banner(now=0.0)
    home.cached_banner(now=30.0)
    assert len(calls) == 1
    home.cached_banner(now=61.0)
    assert len(calls) == 2
    logstore._log_epoch["key-1"] = logstore.log_epoch("key-1") + 1        # what refresh_day does when a meal is logged
    home.cached_banner(now=62.0)
    assert len(calls) == 3


def test_an_unfinished_food_type_lookup_gives_no_flag_and_is_retried_soon(monkeypatch):
    _stub_banner(monkeypatch, [])

    def pending(uid, **kw):
        raise nutritionstore.HabitsPending()

    monkeypatch.setattr(home.nutritionstore, "food_habits", pending)
    assert home.cached_banner(now=0.0) == {"meal": None, "flag": None}
    assert home._cache["key-1"][0] == home.PENDING_RETRY_SECONDS            # not kept for a minute


def test_habits_without_swaps_make_no_shelf_search(monkeypatch):
    rows = [{"food": "Chicken rice", "n": 5, "carbs_g": 60, "protein_g": 25, "fat_g": 15, "sugar_g": 3, "fibre_g": 2, "sodium_mg": 1500, "rise": None}]
    c = Fake({"from food_logs": rows, "percentile": [{"m": None}]})

    @contextlib.contextmanager
    def tx():
        yield c

    monkeypatch.setattr(nutritionstore, "tx", tx)
    monkeypatch.setattr(nutritionstore.foodagent, "classify_foods", lambda names: {nutritionstore.foodagent.normalise(n): "rice_dish" for n in names})
    monkeypatch.setattr(nutritionstore.foodagent, "better_alternatives", lambda *a, **k: pytest.fail("no shelf search for the banner"))
    monkeypatch.setattr(nutritionstore, "swap_outcome", lambda *a, **k: pytest.fail("no swap outcome for the banner"))
    monkeypatch.setattr(nutritionstore, "excluded_keys", lambda *a, **k: pytest.fail("no policy read for the banner"))
    out = nutritionstore.food_habits("u", anchor=NOW, swaps=False)
    assert out and out[0]["alternatives"] == [] and out[0]["outcome"] is None and out[0]["n"] == 5


def test_a_slow_food_type_lookup_raises_pending_instead_of_holding_the_caller(monkeypatch):
    import threading

    gate = threading.Event()
    monkeypatch.setattr(nutritionstore.foodagent, "classify_foods", lambda names: gate.wait(5) and {})
    try:
        with pytest.raises(nutritionstore.HabitsPending):
            nutritionstore._types_within(["slow dish xyz"], 0.05)
    finally:
        gate.set()


def test_one_connection_is_shared_by_nested_transactions(monkeypatch):
    opened = []

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def transaction(self):
            return contextlib.nullcontext()

    monkeypatch.setattr(logstore.settings, "database_url", "postgresql://x")
    monkeypatch.setattr(logstore.psycopg, "connect", lambda *a, **k: opened.append(1) or Conn())
    with logstore.one_connection() as outer:
        with logstore.tx() as a, logstore.tx() as b:
            assert a is outer and b is outer
    assert len(opened) == 1


# ---------------------------------------------------------------- 5. onboarding save
def test_the_save_refuses_what_the_chat_setup_refuses():
    for bad in ({"display_name": "S1234567D"}, {"display_name": "    "}, {"emergency_contact_phone": "abc"}):
        assert onboarding.check_profile(bad, {}, 2026, date(2026, 10, 12)), bad
    assert not onboarding.check_profile({"display_name": "Tan Ah Kow", "emergency_contact_phone": "+65 9123 4567"}, {}, 2026, date(2026, 10, 12))


def test_a_diagnosis_year_before_birth_is_refused_even_when_the_birth_year_was_saved_earlier(monkeypatch):
    monkeypatch.setattr(onboarding, "email_column_present", lambda c: True)
    monkeypatch.setattr(onboarding, "history_ready", lambda c: True)
    c = Fake({"select 1 from user_profile": [(1,)], "select birth_year": [{"birth_year": 1965}]})
    with pytest.raises(onboarding.OnboardingError, match="before the year you were born"):
        onboarding.save_profile(c, "u", {"diagnosed_year": 1950}, {}, 2026, date(2026, 10, 12))


def test_completing_twice_writes_the_event_once():
    state = {"events": 0}

    class C(Fake):
        def execute(self, sql, params=None):
            if "from user_profile" in sql or "from consents" in sql:
                return Cur([(1,)])
            if "select 1 from event_log" in sql:
                return Cur([(1,)] if state["events"] else [])
            if sql.lstrip().startswith("insert into event_log"):
                state["events"] += 1
            return Cur([])

    c = C()
    onboarding.complete(c, "u", NOW)
    onboarding.complete(c, "u", NOW)
    assert state["events"] == 1


# ---------------------------------------------------------------- 6. stock
def test_ended_medicines_are_left_out_of_my_stock():
    c = Fake()
    medication_stock.stock_list(c, "u", today=date(2026, 10, 12))
    assert "end_date is null or m.end_date >=" in c.sql[0] and c.params[0] == ("u", date(2026, 10, 12))


def test_the_refill_key_does_not_move_when_doses_are_missed():
    assert medication_stock.refill_key("m1", "first") == "refill-m1-first"
    assert medication_stock.refill_key("m1", "2026-10-01") != medication_stock.refill_key("m1", "first")


def test_refill_cycles_default_to_first_and_follow_the_last_restock():
    a, b = uuid.uuid4(), uuid.uuid4()
    c = Fake({"event_log": [(a, date(2026, 10, 1))]})
    assert medication_stock.refill_cycles(c, "u", [a, b]) == {str(a): "2026-10-01", str(b): "first"}


def test_a_pack_size_without_a_count_stays_unknown():
    assert medication_stock.status_of(None, None) == "unknown"
    assert medication_stock.days_left_of(None, Decimal(1)) is None


# ---------------------------------------------------------------- 7. hidden idea
def test_the_running_out_idea_is_hidden_for_mr_tan_only():
    assert memorystore.hidden_keys(logstore.MR_TAN_USER) == ["barrier.ran_out"]
    assert memorystore.hidden_keys(logstore.APP_USER) == []


# ---------------------------------------------------------------- 8. junk doctor questions
@pytest.mark.parametrize("text", ["", "   ", "hello", "Hi", "hello there", "good morning", "ok", "About Metformin 500 mg: hello", "what??", "a b c d"])
def test_junk_doctor_questions_are_refused(text):
    with pytest.raises(ValidationFailed):
        care.check_question_text(text)


@pytest.mark.parametrize("text", ["Should I change when I take my tablets?", "About Metformin 500 mg: does this cause tiredness?", "Is my HbA1c ok?"])
def test_real_doctor_questions_pass(text):
    assert care.check_question_text(text) == " ".join(text.split())
