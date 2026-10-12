"""Insights heart rate, SpO2 and blood pressure (C4 and C5): the pure parts. Gaps stay gaps, nights follow the brief's rule,
and blood pressure is shaped without any judgement wording. The database reads are covered in tests/db/test_insights_heart.py."""
import uuid
from datetime import date, datetime, timezone

from app.services import insights as I
from app.services import insights_heart as H

END = date(2026, 10, 3)
D1, D2, D3 = date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3)


def at(d: date, h: int, m: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m, tzinfo=I.TZ)


def bucket(when: datetime, hr=None, o2=None, sleep: int = 0) -> dict:
    return {"recorded_at": when, "heart_rate_bpm": hr, "spo2_pct": o2, "sleep_minutes": sleep}


def by_date(out: dict) -> dict:
    return {d["date"]: d for d in out["days"]}


def test_days_without_watch_data_are_gaps_not_zero():
    out = H.summarize([bucket(at(D2, 10), hr=80)], {}, END, 3)
    days = by_date(out)
    assert days["2026-10-01"]["avg"] is None
    assert days["2026-10-02"]["avg"] == 80.0
    assert days["2026-10-03"]["avg"] is None
    assert out["days_with_data"] == 1
    assert out["has_data"] is True


def test_no_watch_data_at_all_says_so_and_every_number_is_empty():
    out = H.summarize([], {}, END, 7)
    assert out["has_data"] is False
    assert out["period"]["has_data"] is False
    assert out["days_with_data"] == 0
    assert out["heart_rate"] == {"avg": None, "high": None, "low": None, "resting_avg": None, "asleep_avg": None}
    assert out["spo2"] == {"avg": None, "low": None, "asleep_avg": None, "asleep_low": None}
    assert len(out["days"]) == 7 and all(d["avg"] is None and d["resting"] is None and d["asleep"] is None for d in out["days"])


def test_highest_and_lowest_are_single_readings_in_the_period():
    rows = [bucket(at(D1, 9), hr=70), bucket(at(D2, 9), hr=95), bucket(at(D2, 10), hr=65)]
    hr = H.summarize(rows, {}, END, 3)["heart_rate"]
    assert hr["high"] == 95 and hr["low"] == 65
    assert hr["avg"] == round((70 + 95 + 65) / 3, 1)


def test_a_night_belongs_to_the_morning_it_ends_on():
    # 23:00 on 1 Oct and 01:00 on 2 Oct are the same night, filed under 2 Oct (the brief's rule)
    rows = [bucket(at(D1, 23), hr=70, sleep=5), bucket(at(D2, 1), hr=60, sleep=5), bucket(at(D2, 14), hr=100, sleep=0)]
    out = H.summarize(rows, {}, END, 3)
    days = by_date(out)
    assert days["2026-10-02"]["asleep"] == 65.0          # the two asleep buckets only
    assert days["2026-10-01"]["asleep"] is None           # nothing filed under 1 Oct
    assert out["heart_rate"]["asleep_avg"] == 65.0
    assert out["heart_rate"]["high"] == 100               # the awake reading still counts in the period high


def test_a_bucket_with_too_few_sleep_minutes_is_not_asleep():
    rows = [bucket(at(D2, 2), hr=90, sleep=3)]            # 3 minutes is below the brief's 4-minute rule
    assert H.summarize(rows, {}, END, 3)["heart_rate"]["asleep_avg"] is None


def test_spo2_period_and_asleep_are_separate():
    rows = [bucket(at(D2, 2), o2=95.0, sleep=5), bucket(at(D2, 3), o2=89.0, sleep=5), bucket(at(D2, 14), o2=98.0, sleep=0)]
    s = H.summarize(rows, {}, END, 3)["spo2"]
    assert s["low"] == 89.0
    assert s["avg"] == round((95 + 89 + 98) / 3, 1)
    assert s["asleep_low"] == 89.0
    assert s["asleep_avg"] == 92.0


def test_resting_heart_rate_comes_from_the_daily_summary_inside_the_period_only():
    daily = {D2: {"resting_hr_bpm": 62}, D3: {"resting_hr_bpm": 64}, date(2026, 9, 1): {"resting_hr_bpm": 40}}
    out = H.summarize([bucket(at(D2, 10), hr=80)], daily, END, 3)
    assert out["heart_rate"]["resting_avg"] == 63.0
    assert by_date(out)["2026-10-02"]["resting"] == 62.0
    assert by_date(out)["2026-10-01"]["resting"] is None


def test_a_day_with_no_resting_value_stays_empty():
    daily = {D1: {"resting_hr_bpm": None}}
    out = H.summarize([], daily, END, 3)
    assert out["heart_rate"]["resting_avg"] is None
    assert by_date(out)["2026-10-01"]["resting"] is None


def test_blood_pressure_is_newest_first_in_singapore_time_and_capped_for_the_table(monkeypatch):
    rows = [
        {"measured_at": datetime(2026, 10, 2, 0, 31, tzinfo=timezone.utc), "systolic": 144, "diastolic": 87, "pulse": None},
        {"measured_at": datetime(2026, 9, 30, 13, 22, tzinfo=timezone.utc), "systolic": 137, "diastolic": 84, "pulse": 72},
    ]
    monkeypatch.setattr(H, "recent_bp", lambda conn, uid, days: rows)
    _ends_on(monkeypatch, END)
    out = H.blood_pressure(None, str(uuid.uuid4()), 30, END)
    assert out["count"] == 2
    assert out["latest"] == "2026-10-02"
    assert out["readings"][0] == {"date": "2026-10-02", "time": "08:31", "systolic": 144, "diastolic": 87, "pulse": None}
    assert out["readings"][1]["pulse"] == 72 and out["readings"][1]["time"] == "21:22"


def test_blood_pressure_returns_every_reading_of_the_period_for_the_chart(monkeypatch):
    rows = [{"measured_at": datetime(2026, 10, 1, 1, tzinfo=timezone.utc), "systolic": 120 + i, "diastolic": 80, "pulse": None} for i in range(41)]
    monkeypatch.setattr(H, "recent_bp", lambda conn, uid, days: rows)
    _ends_on(monkeypatch, END)
    out = H.blood_pressure(None, str(uuid.uuid4()), 90, END)
    assert out["count"] == 41 and len(out["readings"]) == 41            # a 90-day chart draws all of them, not the newest 30
    assert H.BP_MAX_READINGS >= 400


def test_blood_pressure_stops_at_the_safety_cap_but_the_count_uses_every_reading(monkeypatch):
    rows = [{"measured_at": datetime(2026, 10, 1, 1, tzinfo=timezone.utc), "systolic": 120, "diastolic": 80, "pulse": None}] * (H.BP_MAX_READINGS + 5)
    monkeypatch.setattr(H, "recent_bp", lambda conn, uid, days: rows)
    _ends_on(monkeypatch, END)
    out = H.blood_pressure(None, str(uuid.uuid4()), 90, END)
    assert out["count"] == H.BP_MAX_READINGS + 5
    assert len(out["readings"]) == H.BP_MAX_READINGS


def test_no_blood_pressure_gives_an_empty_list_not_zero(monkeypatch):
    monkeypatch.setattr(H, "recent_bp", lambda conn, uid, days: [])
    _ends_on(monkeypatch, END)
    assert H.blood_pressure(None, str(uuid.uuid4()), 7, END) == {"count": 0, "latest": None, "readings": []}


def test_a_reading_after_the_period_end_is_still_listed(monkeypatch):
    # the watch data ends on 2 Oct but a reading was logged on 3 Oct: the newest reading must not be hidden
    rows = [{"measured_at": datetime(2026, 10, 3, 1, tzinfo=timezone.utc), "systolic": 130, "diastolic": 82, "pulse": None}]
    monkeypatch.setattr(H, "recent_bp", lambda conn, uid, days: rows)
    _ends_on(monkeypatch, D2)
    out = H.blood_pressure(None, str(uuid.uuid4()), 30, END)
    assert out["latest"] == "2026-10-03" and out["count"] == 1


def _ends_on(monkeypatch, end: date) -> None:
    """Stands in for the database read of the period end: the person's last watch day, which is `end` here."""
    monkeypatch.setattr(H, "period_end", lambda conn, user, today: (end, end < today, end))


# ── the end day of the heart block and blood pressure ──
def test_a_person_with_no_watch_data_ends_today_without_a_note():
    assert H.pick_end(None, END, END) == (END, False)


def test_watch_data_ending_today_has_no_note():
    assert H.pick_end(END, END, END) == (END, False)


def test_watch_data_ending_earlier_than_today_is_noted():
    assert H.pick_end(D2, END, END) == (D2, True)


def test_watch_data_ending_earlier_than_the_other_tabs_is_noted_too():
    today = date(2026, 10, 11)
    other_end = date(2026, 10, 10)
    assert H.pick_end(D2, today, other_end) == (D2, True)
    assert H.pick_end(today, today, other_end) == (today, False)


def test_routes_refuse_other_periods_and_send_camel_case(monkeypatch):
    from fastapi.testclient import TestClient

    from app.db import logstore
    from app.main import app

    monkeypatch.setattr(logstore, "tx", lambda: _NoDb())
    monkeypatch.setattr(logstore, "current_user", lambda: uuid.uuid4())
    monkeypatch.setattr(H, "heart", lambda conn, user, days, today: {**H.summarize([], {}, END, days), "watch_end": None, "end_note": False})
    monkeypatch.setattr(H, "blood_pressure", lambda conn, user, days, today: {"count": 0, "latest": None, "readings": []})
    client = TestClient(app)
    assert client.get("/api/v1/insights/heart?days=5").status_code == 422
    assert client.get("/api/v1/insights/blood-pressure?days=5").status_code == 422
    heart = client.get("/api/v1/insights/heart?days=7")
    assert heart.status_code == 200
    body = heart.json()
    assert body["hasData"] is False and body["heartRate"]["avg"] is None and len(body["days"]) == 7
    assert body["spo2"]["asleepLow"] is None
    assert body["watchEnd"] is None and body["endNote"] is False
    assert client.get("/api/v1/insights/blood-pressure?days=30").json() == {"count": 0, "latest": None, "readings": []}


class _NoDb:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False
