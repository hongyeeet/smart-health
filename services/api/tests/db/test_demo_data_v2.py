"""Sanity tests for the loaded demo patient (Mr Tan, about 90 days) in data model v2.
They check what the loader and the Gold builder promise: one user, full lineage to Bronze, the real rows labelled as real,
a timeline with the expected features, a baseline that applies only after its window, and a decline flag that fires only in the
disruption and drift phases (not while he improves). Run:  python -m pytest services/api/tests/db/test_demo_data_v2.py -q
Needs the data loaded (scripts/load_mr_tan_v2.py --yes, then scripts/build_gold_v2.py).
"""
import os
import sys
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

TAN = "dc48e209-5731-5b3d-89d9-986242c54368"


@pytest.fixture(scope="module")
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    yield c
    c.close()


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def test_only_the_demo_patient_remains(conn):
    assert one(conn, "select count(*) from users") == 1
    assert one(conn, "select count(*) from user_profile where user_id = %s", (TAN,)) == 1


def test_there_are_about_three_months_at_five_minutes(conn):
    assert one(conn, "select count(*) from watch_readings") >= 25000
    assert one(conn, "select count(*) from cgm_readings") >= 25000
    assert one(conn, "select count(*) from timeline_5min") == one(conn, "select count(*) from watch_readings")
    assert one(conn, "select (max(recorded_at)::date - min(recorded_at)::date) from watch_readings") >= 89


@pytest.mark.parametrize("silver,bronze", [("watch_readings", "bronze_watch"), ("cgm_readings", "bronze_cgm"), ("food_logs", "bronze_food"),
                                           ("exercise_logs", "bronze_exercise"), ("symptom_logs", "bronze_symptom"), ("wellbeing_logs", "bronze_wellbeing"),
                                           ("blood_pressure_readings", "bronze_blood_pressure"), ("lab_results", "bronze_lab")])
def test_every_silver_row_has_a_bronze_row_of_the_same_user(conn, silver, bronze):
    assert one(conn, f"select count(*) from {silver} s left join {bronze} b on b.id = s.bronze_id and b.user_id = s.user_id where b.id is null") == 0


def test_real_rows_are_labelled_real_and_simulated_rows_are_not(conn):
    real = one(conn, "select count(*) from cgm_readings where source = 'file_import'")
    assert 2800 <= real <= 2900                                   # about 10 days of his real Dexcom G6
    assert one(conn, "select count(*) from food_logs where source = 'file_import'") == 29
    assert one(conn, "select count(*) from watch_readings where source <> 'demo_dataset'") == 0   # every watch row has simulated or derived fields
    assert one(conn, "select count(*) from lab_results where source = 'file_import'") == 2


def test_the_timeline_has_the_expected_overlay_and_chart_columns(conn):
    r = conn.execute("select count(glucose_mmol), count(heart_rate_bpm), count(spo2_pct), count(systolic_mmhg), count(meal_id), count(exercise_id), "
                     "count(dose_status), count(mood), count(symptom_type), count(at_work) from timeline_5min").fetchone()
    assert all(x > 0 for x in r), r
    assert one(conn, "select count(*) from information_schema.columns where table_name = 'timeline_5min'") == 46    # 44 features + the 2-column key


def test_food_and_exercise_columns_exist_only_while_they_happen(conn):
    assert one(conn, "select count(*) from timeline_5min where (meal_id is null) <> (food is null)") == 0
    assert one(conn, "select count(*) from timeline_5min where (exercise_id is null) <> (exercise_type is null)") == 0


def test_baseline_applies_only_after_its_window(conn):
    end = one(conn, "select max(anchor_end) from baselines where metric = 'glucose'")
    assert one(conn, "select count(*) from timeline_5min where glucose_vs_baseline is not null and local_date <= %s", (end,)) == 0
    assert one(conn, "select count(*) from baselines where metric in ('systolic','diastolic') and n_points = 5") == 2
    assert one(conn, "select count(distinct hour_of_day) from baselines where metric = 'glucose'") == 24


def test_the_decline_flag_fires_only_in_the_disruption_and_drift_phases(conn):
    first = one(conn, "select min(local_date) from daily_summary where cardinality(declining_metrics) > 0")
    assert str(first) >= "2026-08-29", first                       # day 57: the disruption phase starts; no flags while he improves
    assert one(conn, "select count(*) from daily_summary where cardinality(declining_metrics) > 0 and local_date >= '2026-09-11'") >= 15
    assert one(conn, "select count(*) from clinical_flags where kind = 'outside_usual_range'") >= 3


def test_the_gold_analysis_finds_the_planted_effects(conn):
    got = {r[0]: float(r[1]) for r in conn.execute("select pattern_key, median_delta from pattern_candidates where user_id = %s", (TAN,)).fetchall()}
    assert got["missed_evening_dose__post_dinner_rise"] > 0.5      # missed evening metformin -> a higher post-dinner rise
    assert got["evening_walk__next_morning_fasting"] < -0.3        # evening walks -> a lower fasting glucose the next morning
    assert got["high_carb_meal__rise"] > 1.0                       # more carbohydrate -> a bigger rise
    assert got["short_sleep__fasting_glucose"] > 0.2               # short sleep -> a higher fasting glucose


def test_the_scripted_low_and_the_interaction_alerts_exist(conn):
    assert one(conn, "select count(*) from glucose_events where event_type = 'low' and started_at::date = '2026-08-15'") == 1
    assert one(conn, "select count(*) from interaction_alerts where status = 'acknowledged'") == 2
    assert one(conn, "select count(*) from interaction_alerts where status = 'not_checked'") == 2


def test_glucose_event_and_meal_response_rows_are_consistent(conn):
    assert one(conn, "select count(*) from meal_response where rise_mmol < 0 or minutes_to_peak > 180") == 0
    assert one(conn, "select count(*) from meal_response mr left join food_logs f on f.id = mr.food_log_id where f.id is null") == 0
    assert one(conn, "select count(*) from glucose_events where ended_at < started_at") == 0
