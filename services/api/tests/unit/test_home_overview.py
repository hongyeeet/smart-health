"""GET /home/overview (app/services/home_overview.py): the status rules, the nutrient and calorie handling, today's plan, the cache,
and the read-only rule for Mr Tan. Plain rows stand in for the database."""
import contextlib
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.agents import dose_timing
from app.api.routers import home
from app.db import logstore
from app.schemas.home import HomeOverview
from app.services import home_overview as H

TZ = ZoneInfo("Asia/Singapore")
TODAY = date(2026, 10, 13)


def at(h: int, m: int = 0) -> datetime:
    return datetime(2026, 10, 13, h, m, tzinfo=TZ)


# ───────────────────────────────────────────── status
PRIOR = [float(x) for x in range(1, 11)]          # p25 = 3.25, p50 = 5.5, p75 = 7.75


@pytest.mark.parametrize(("window", "state"), [([5.0, 6.0, 7.0], "within"), ([9.0, 9.0, 9.0], "above"), ([1.0, 2.0, 2.0], "below")])
def test_status_within_above_below(window, state):
    s = H.range_status(window, PRIOR)
    assert s["state"] == state
    assert (s["usual_low"], s["usual_high"], s["usual_median"]) == (3.2, 7.8, 5.5)
    assert s["delta"] == round(sum(window) / 3 - 5.5, 1)


def test_status_edges_are_within():
    assert H.range_status([3.25, 3.25, 3.25], PRIOR)["state"] == "within"
    assert H.range_status([7.75, 7.75, 7.75], PRIOR)["state"] == "within"


def test_status_needs_three_window_days():
    s = H.range_status([9.0, 9.0], PRIOR)
    assert s["state"] == "unknown" and s["delta"] is None
    assert s["usual_low"] is not None                  # the usual range is still known; only the comparison is not


def test_status_needs_seven_prior_days():
    s = H.range_status([9.0, 9.0, 9.0], PRIOR[:6])
    assert s == {"state": "unknown", "usual_low": None, "usual_high": None, "usual_median": None, "delta": None}
    assert H.range_status([9.0, 9.0, 9.0], PRIOR[:7])["state"] == "above"
    assert H.range_status([], [])["state"] == "unknown"


def test_constants_reuse_insights_and_dose_timing():
    assert H.I.BASELINE_DAYS == 60 and H.DOSE_WINDOW_MIN == dose_timing.WINDOW_MIN == 60


# ───────────────────────────────────────────── KPI cards
def test_glucose_card_value_day_spark_and_status():
    end = date(2026, 10, 2)
    daily = {end - timedelta(days=i): {"glucose_mean_mmol": 8.0, "tir_pct": 60} for i in range(7, 40)}
    daily.update({end - timedelta(days=i): {"glucose_mean_mmol": 11.0, "tir_pct": 55} for i in range(0, 7)})
    daily[end]["glucose_mean_mmol"] = 10.5
    g = H.build_glucose(daily, end)
    assert g["value"] == 10.5 and g["day"] == "2026-10-02" and g["in_range_pct"] == 55 and g["unit"] == "mmol/L"
    assert len(g["spark"]) == 7 and g["spark"][-1] == 10.5
    assert g["status"]["state"] == "above" and g["status"]["usual_median"] == 8.0


def test_glucose_null_without_data_and_gaps_stay_null():
    assert H.build_glucose({}, TODAY) is None
    assert H.build_steps({TODAY: {"steps_total": None}}, TODAY) is None
    g = H.build_glucose({TODAY: {"glucose_mean_mmol": 9.0, "tir_pct": None}}, TODAY)
    assert g["spark"] == [None] * 6 + [9.0] and g["in_range_pct"] is None
    assert g["status"]["state"] == "unknown"           # one day, no history


def test_steps_card_mean_and_below_status():
    daily = {TODAY - timedelta(days=i): {"steps_total": 8000} for i in range(7, 30)}
    daily.update({TODAY - timedelta(days=i): {"steps_total": 4000} for i in range(0, 7)})
    s = H.build_steps(daily, TODAY)
    assert s["avg"] == 4000 and s["status"]["state"] == "below" and s["status"]["delta"] == -4000
    assert s["spark"] == [4000.0] * 7


def meal(sugar=None, sodium=None):
    return {"sugar_g": sugar, "sodium_mg": sodium}


def diet_day(d: date, meals: list[dict], kcal=None):
    return {"date": d.isoformat(), "meals": len(meals), "totals": {"kcal": kcal}, "meal_list": meals}


def test_nutrient_unknown_ok_high():
    assert H.nutrient([meal(), meal()], "sugar_g", 25) == {"state": "unknown", "high_meals": None, "meals": 2}
    assert H.nutrient([], "sugar_g", 25) == {"state": "unknown", "high_meals": None, "meals": 0}
    assert H.nutrient([meal(sugar=10), meal(sugar=30), meal()], "sugar_g", 25) == {"state": "ok", "high_meals": 1, "meals": 3}
    assert H.nutrient([meal(sugar=30), meal(sugar=25)], "sugar_g", 25)["state"] == "high"
    assert H.nutrient([meal(sodium=1200), meal(sodium=1000), meal(sodium=100)], "sodium_mg", 1000) == {"state": "high", "high_meals": 2, "meals": 3}


def test_calories_logged_day_mean_and_unknown_days_left_out():
    end = TODAY
    diet = []
    for i in range(66, -1, -1):
        d = end - timedelta(days=i)
        if i >= 7:
            diet.append(diet_day(d, [meal()], kcal=1500))
        elif i == 0:
            diet.append(diet_day(d, [meal()], kcal=None))       # a meal with an unknown value: the day is left out
        elif i == 1:
            diet.append(diet_day(d, [], kcal=None))              # nothing logged
        else:
            diet.append(diet_day(d, [meal(sugar=30, sodium=1100)], kcal=2000))
    c = H.build_calories(diet, end)
    assert c["avg_kcal"] == 2000 and c["spark"] == [2000.0] * 5 + [None, None]
    assert c["status"]["state"] == "above" and c["status"]["usual_median"] == 1500
    assert c["sugar"]["state"] == "high" and c["salt"]["state"] == "high" and c["sugar"]["meals"] == 6
    assert H.build_calories([diet_day(end, [])], end) is None


def test_calories_with_too_few_days_is_unknown_not_zero():
    diet = [diet_day(TODAY - timedelta(days=i), [], kcal=None) for i in range(6, 0, -1)] + [diet_day(TODAY, [meal()], kcal=1800)]
    c = H.build_calories(diet, TODAY)
    assert c["avg_kcal"] == 1800 and c["status"]["state"] == "unknown" and c["sugar"]["state"] == "unknown"


def watch(d: date, hr: float, o2: float, n: int = 2):
    return [{"recorded_at": datetime.combine(d, time(10, 5 * i), TZ), "heart_rate_bpm": hr, "spo2_pct": o2, "sleep_minutes": 0} for i in range(n)]


def test_heart_card_two_statuses():
    end = TODAY
    rows = [r for i in range(7) for r in watch(end - timedelta(days=i), 90, 95)]
    prior_hr = {end - timedelta(days=7 + i): 80.0 + (i % 3) for i in range(40)}
    prior_o2 = {end - timedelta(days=7 + i): 97.0 for i in range(40)}
    h = H.build_heart(rows, {}, prior_hr, prior_o2, end)
    assert h["bpm"] == 90 and h["spo2"] == 95 and h["resting_bpm"] is None
    assert h["status"]["state"] == "above" and h["spo2_status"]["state"] == "below"
    assert h["spo2_status"]["delta"] == -2
    assert H.build_heart([], {}, prior_hr, prior_o2, end) is None
    few = [r for i in range(2) for r in watch(end - timedelta(days=i), 90, 95)]
    assert H.build_heart(few, {}, prior_hr, prior_o2, end)["status"]["state"] == "unknown"


def test_chart_has_seven_aligned_days_with_gaps():
    end = date(2026, 10, 2)
    daily = {end: {"glucose_mean_mmol": 9.0, "steps_total": 100}}
    ch = H.build_chart(end, daily, [diet_day(end - timedelta(days=1), [meal()], kcal=1800)], {end: 80.0})
    assert ch["days"][-1] == "2026-10-02" and ch["days"][0] == "2026-09-26" and len(ch["days"]) == 7
    for k in ("glucose", "steps", "calories", "heart_rate"):
        assert len(ch[k]) == 7
    assert ch["glucose"][-1] == 9.0 and ch["glucose"][0] is None
    assert ch["calories"][-2] == 1800 and ch["heart_rate"][-1] == 80.0 and ch["steps"][-1] == 100


# ───────────────────────────────────────────── today's plan
def dose(h, m=0, title="Metformin 500 mg", status=None, id_="d1"):
    return {"time": time(h, m), "title": title, "status": status, "id": id_}


def plan(now, logged=(), doses=()):
    return H.build_plan(TODAY, now, set(logged), list(doses))


def test_meal_times_are_the_reminder_windows():
    p = plan(at(6, 0))
    assert [(s["time"], s["items"][0]["meal_type"]) for s in p["steps"]] == [("07:00", "breakfast"), ("11:30", "lunch"), ("18:00", "dinner")]
    assert [s["label"] for s in p["steps"]] == ["7:00 am", "11:30 am", "6:00 pm"]


def test_meal_status_by_clock_and_log():
    def st(p):
        return [s["items"][0]["status"] for s in p["steps"]]
    assert st(plan(at(6, 0))) == ["later"] * 3
    assert st(plan(at(8, 0))) == ["due", "later", "later"]
    assert st(plan(at(8, 0), logged={"breakfast"})) == ["done", "later", "later"]
    assert st(plan(at(15, 0), logged={"breakfast"})) == ["done", "missed", "later"]
    assert st(plan(at(22, 0), logged={"dinner"})) == ["missed", "missed", "done"]


def test_dose_inside_its_window_is_due_and_window_edges():
    p = plan(at(12, 0), doses=[dose(12, 0, status="pending", id_="row1")])
    s = next(s for s in p["steps"] if s["time"] == "12:00")
    assert s["state"] == "now" and s["items"][0]["status"] == "due" and s["items"][0]["dose_id"] == "row1"

    def status_at(now):
        return next(i for s in plan(now, doses=[dose(9, 0, status="pending")])["steps"] for i in s["items"] if i["kind"] == "dose")["status"]
    assert status_at(at(8, 59)) == "later"
    assert status_at(at(9, 0)) == "due"
    assert status_at(at(10, 0)) == "due"
    assert status_at(at(10, 1)) == "missed"             # window passed, not answered


def test_dose_answers_and_missing_rows():
    def one(**kw):
        return next(i for s in plan(at(20, 0), doses=[dose(9, 0, **kw)])["steps"] for i in s["items"] if i["kind"] == "dose")
    assert one(status="taken")["status"] == "done" and one(status="taken")["dose_id"] is None
    assert one(status="missed")["status"] == "missed" and one(status="missed")["dose_id"] is None
    assert one(status="pending", id_="x")["dose_id"] == "x"            # still answerable
    assert one(status=None, id_=None)["status"] == "missed" and one(status=None, id_=None)["dose_id"] is None


def test_grouping_order_counts_and_now_index():
    p = plan(at(8, 10), logged={"breakfast"}, doses=[
        dose(8, 0, "Metformin 500 mg", "taken"), dose(8, 0, "Amlodipine 5 mg", "pending"), dose(7, 0, "Vitamin D", "taken"), dose(21, 0, "Statin", None, None)])
    assert [s["time"] for s in p["steps"]] == ["07:00", "08:00", "11:30", "18:00", "21:00"]
    first = p["steps"][0]
    assert [(i["kind"], i["title"]) for i in first["items"]] == [("meal", "Breakfast"), ("dose", "Vitamin D")] and first["state"] == "done"
    eight = p["steps"][1]
    assert [i["status"] for i in eight["items"]] == ["due", "done"]          # Amlodipine (waiting) then Metformin (taken)
    assert eight["state"] == "now"
    assert p["now_index"] == 1 and p["done"] == 3 and p["total"] == 7


def test_now_index_is_first_later_step_when_nothing_is_due_and_none_at_the_end():
    p = plan(at(10, 0), logged={"breakfast"})
    assert p["now_index"] == 1 and p["steps"][1]["state"] == "later"
    p = plan(at(23, 0), logged={"breakfast", "lunch", "dinner"})
    assert p["now_index"] is None and p["done"] == 3 and all(s["state"] == "done" for s in p["steps"])
    assert plan(at(23, 0))["now_index"] is None


def test_dose_label_uses_the_persons_own_label():
    assert H.dose_label("Metformin", "500 mg") == "Metformin 500 mg"
    assert H.dose_label("Metformin 500 mg", "500 mg") == "Metformin 500 mg"
    assert H.dose_label("Fish oil", None) == "Fish oil"


# ───────────────────────────────────────────── the loader: filters, read-only, cache
class Cur:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConn:
    """Answers the plan's two queries and records every statement, so a test can assert that nothing was written."""

    def __init__(self, doses, meals=()):
        self.row_factory = None
        self.sql: list[str] = []
        self.doses, self.meals = doses, meals

    def execute(self, sql, params=()):
        self.sql.append(" ".join(sql.split()).lower())
        if self.sql[-1].startswith("select s.dose_time"):
            return Cur(self.doses)
        if "from food_logs" in self.sql[-1]:
            return Cur([{"mt": m} for m in self.meals])
        return Cur([])


def writes(conn):
    return [s for s in conn.sql if s.startswith(("insert", "update", "delete"))]


def test_mr_tan_plan_writes_nothing(monkeypatch):
    made = []
    monkeypatch.setattr(H.dose_store, "ensure_rows", lambda *a, **k: made.append(a) or 0)
    conn = FakeConn([{"dose_time": time(8), "created_at": at(0) - timedelta(days=90), "name": "Metformin", "strength": "500 mg", "lid": None, "lstatus": None}])
    p = H.load_plan(conn, str(logstore.MR_TAN_USER), at(8, 30))
    assert made == [] and writes(conn) == []                         # no dose rows are made for him, no insert is issued
    assert p["steps"][1]["items"][0]["title"] == "Metformin 500 mg" and p["steps"][1]["items"][0]["status"] == "due"


def test_other_people_get_todays_rows_made_and_nothing_else(monkeypatch):
    made = []
    monkeypatch.setattr(H.dose_store, "ensure_rows", lambda conn, user, now: made.append(user) or 0)
    conn = FakeConn([])
    H.load_plan(conn, "someone-else", at(8, 30))
    assert made == ["someone-else"] and writes(conn) == []


def test_plan_query_excludes_ended_deleted_and_as_needed_medicines():
    conn = FakeConn([])
    H.load_plan(conn, str(logstore.MR_TAN_USER), at(8))
    q = next(s for s in conn.sql if s.startswith("select s.dose_time"))
    for part in ("s.deleted_at is null", "m.deleted_at is null", "m.as_needed is not true", "m.end_date is null or m.end_date >=", "s.dose_time is not null"):
        assert part in q


def test_medicine_that_did_not_exist_yet_is_left_out_unless_it_has_a_row():
    new = at(10)
    rows = [{"dose_time": time(8), "created_at": new, "name": "New", "strength": None, "lid": None, "lstatus": None},
            {"dose_time": time(9), "created_at": new, "name": "Has row", "strength": None, "lid": "r1", "lstatus": "taken"}]
    p = H.load_plan(FakeConn(rows), str(logstore.MR_TAN_USER), at(11))
    assert [i["title"] for s in p["steps"] for i in s["items"] if i["kind"] == "dose"] == ["Has row"]


def test_plan_has_no_as_needed_items_without_doses():
    assert all(i["kind"] == "meal" for s in plan(at(9))["steps"] for i in s["items"])


EPOCH = [0]
PLAN = H.build_plan(TODAY, at(9), set(), [])
KPIS = {"as_of": None, "glucose": None, "steps": None, "calories": None, "heart": None, "chart": H.build_chart(TODAY, {}, [], {})}


def test_overview_cache_keeps_the_cards_but_rereads_the_plan(monkeypatch):
    H._kpi_cache.clear()
    calls = {"kpi": 0, "plan": 0}

    def fake_kpis(conn, user, today):
        calls["kpi"] += 1
        return KPIS

    def fake_plan(conn, user, now):
        calls["plan"] += 1
        return PLAN

    monkeypatch.setattr(H.logstore, "one_connection", lambda: contextlib.nullcontext(object()))
    monkeypatch.setattr(H, "load_kpis", fake_kpis)
    monkeypatch.setattr(H, "load_plan", fake_plan)
    monkeypatch.setattr(H.logstore, "current_user_key", lambda: "k-cache")
    monkeypatch.setattr(H.logstore, "log_epoch", lambda key: EPOCH[0])
    EPOCH[0] = 1
    H.overview(at(9), clock=100.0)
    H.overview(at(9), clock=110.0)
    assert calls == {"kpi": 1, "plan": 2}
    H.overview(at(9), clock=121.0)                                   # 20 s later
    assert calls["kpi"] == 2
    EPOCH[0] = 2                                                      # the person logged a meal
    H.overview(at(9), clock=122.0)
    assert calls["kpi"] == 3
    H._kpi_cache.clear()


# ───────────────────────────────────────────── response shape
def test_response_shape_camel_case_no_identity_and_routes():
    out = HomeOverview.model_validate({"plan": PLAN, **KPIS}).model_dump(by_alias=True)
    assert set(out) == {"asOf", "plan", "glucose", "steps", "calories", "heart", "chart"}
    assert set(out["plan"]) == {"date", "done", "total", "nowIndex", "steps"}
    assert set(out["chart"]) == {"days", "glucose", "steps", "calories", "heartRate"} and len(out["chart"]["days"]) == 7
    assert out["glucose"] is None and out["heart"] is None
    full = H.build_calories([diet_day(TODAY, [meal(1, 2)], 1800)], TODAY)
    d = HomeOverview.model_validate({"plan": PLAN, **{**KPIS, "calories": full}}).model_dump(by_alias=True)
    assert set(d["calories"]) == {"avgKcal", "sugar", "salt", "spark", "status"} and set(d["calories"]["sugar"]) == {"state", "highMeals", "meals"}
    assert set(d["calories"]["status"]) == {"state", "usualLow", "usualHigh", "usualMedian", "delta"}
    step_item = out["plan"]["steps"][0]["items"][0]
    assert set(step_item) == {"kind", "title", "status", "doseId", "mealType"}
    text = str(d).lower()
    for word in ("phone", "email", "nric", "fullname", "full_name"):
        assert word not in text
    paths = {r.path: r.methods for r in home.router.routes}
    assert "GET" in paths["/home/overview"] and "GET" in paths["/home/banner"]     # the banner route is untouched
