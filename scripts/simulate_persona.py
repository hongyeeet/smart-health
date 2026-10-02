#!/usr/bin/env python3
"""Simulated 60-day history for the demo patient "Mr Tan" (CGMacros participant 046). Pure generator: no database access.

Built from cited data only (docs/specs/prd.md A8): his real CGM, heart-rate and meal data are loaded by import_cgmacros.py;
this module adds what no cited dataset has (doses and miss reasons, mood, sleep, steps, workouts, blood pressure,
symptoms, lab history, appointments, ...) following the persona in docs/mockup/mockup-prompt.md. Everything uses a
fixed seed, so the same end date gives identical data. scripts/seed_demo.py loads it and writes data/demo/DISCLOSURE.md.

Persona targets (from the mock): 4 scheduled doses a day (metformin twice with food, amlodipine, atorvastatin); last
completed week 24 of 28 doses taken (one missed evening metformin "forgot", one "away from home", two unconfirmed);
an evening-and-weekend miss pattern and one 4-day streak; moderate minutes per week 140, 120, 95, 70 and 55 so far;
7-night sleep average about 6 h 10 min (last night 5 h 50 min); steps today 5,840 so far; fasting glucose rising over the
last 3 weeks; a fish-oil supplement and a herbal tonic that stay "not checked".
"""
import calendar
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta

import numpy as np

from etl_common import DEMO_SOURCE, local_to_utc, uid

USER_KEY = "cgmacros-046"
SEED = 42
WINDOW_DAYS = 60
REAL_DAYS = 10          # the real sensor window is the last ~10 days
SIM = "sim:"


def add_months(d, months):
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def build(end_date, now_local, real_meals, real_morning_mean=7.4):
    """Return (rows_by_table, disclosure_entries). now_local is the demo's "now" (naive Singapore time)."""
    rng = np.random.default_rng(SEED)
    D = end_date
    day = lambda i: D - timedelta(days=i)                        # noqa: E731  (i days before the end date)
    at = lambda d, hh, mm=0: local_to_utc(datetime.combine(d, time(hh, mm)))   # noqa: E731
    U = uid("user", USER_KEY)
    rows, disc = defaultdict(list), []

    def note(table, rule, n, first, last):
        disc.append({"table": table, "rule": rule, "rows": n, "from": str(first), "to": str(last)})

    # ------------------------------------------------------------------ medicines
    meds = [  # key, display name, kind, strength, dose, unit, times_per_day, times, with_food, start_days_ago
        ("metformin", "Metformin 500 mg", "prescription", "500 mg", 1, "tablet", 2, ["08:00", "20:00"], True, 2000),
        ("amlodipine", "Amlodipine 5 mg", "prescription", "5 mg", 1, "tablet", 1, ["08:00"], False, 1400),
        ("atorvastatin", "Atorvastatin 20 mg", "prescription", "20 mg", 1, "tablet", 1, ["22:00"], False, 1200),
        ("fish_oil", "Fish oil", "supplement", None, 1, "capsule", None, [], True, 400),
        ("herbal_tonic", "Herbal tonic (label not readable)", "tcm", None, None, None, None, [], False, 200),
    ]
    med_id = {m[0]: uid("med", USER_KEY, m[0]) for m in meds}
    confirmed = at(day(WINDOW_DAYS), 9)
    for key, name, kind, strength, dose, unit, tpd, times, food, ago in meds:
        ref = uid("drug", key) if kind == "prescription" else None      # supplement and tonic stay unrecognised: "not checked"
        rows["patient_medications"].append((med_id[key], U, ref, name, kind, strength, dose, unit, tpd, [t + ":00" for t in times], food, 120, day(ago), "active", DEMO_SOURCE, confirmed))
    rows["medication_ingredients"] += [(uid("ingredient", USER_KEY, "fish_oil"), med_id["fish_oil"], "fish oil (omega-3)", "user"),
                                       (uid("ingredient", USER_KEY, "herbal_tonic"), med_id["herbal_tonic"], "herbal tonic (ingredients not listed)", "user")]
    note("patient_medications", "5 items from the mock persona; the supplement and tonic have no drug match and no schedule", 5, day(WINDOW_DAYS), D)

    # ------------------------------------------------------------------ doses
    overrides = {(5, "metformin", "20:00"): ("missed", "forgot"), (3, "metformin", "20:00"): ("missed", "away_from_home"),
                 (2, "atorvastatin", "22:00"): ("unconfirmed", None), (1, "metformin", "20:00"): ("unconfirmed", None)}
    reasons = ["forgot", "away_from_home", "other", "felt_fine", "side_effects"]
    reason_p = [0.5, 0.3, 0.1, 0.05, 0.05]
    n_dose = 0
    for i in range(WINDOW_DAYS - 1, -8, -1):                      # 59 days ago ... 7 days ahead
        d = day(i)
        for key, name, kind, strength, dose, unit, tpd, times, food, ago in meds:
            for t in times:
                sched_local = datetime.combine(d, time(int(t[:2]), int(t[3:])))
                sched, end = local_to_utc(sched_local), local_to_utc(sched_local + timedelta(minutes=120))
                u1, u2, u3, u4 = rng.random(), rng.random(), rng.integers(1, 41), rng.random()
                reason = reasons[int(np.searchsorted(np.cumsum(reason_p), u4))] if u4 < 1 else "forgot"
                status, conf, miss, captured = "scheduled", None, None, None
                if i < 0 or (i == 0 and sched_local > now_local):
                    pass
                elif (i, key, t) in overrides:
                    status, miss = overrides[(i, key, t)]
                elif 30 <= i <= 33 and key == "metformin" and t == "20:00":
                    status, miss = "missed", "ran_out"                  # the 4-day streak
                elif i > 7 and u1 < (0.30 if (key == "metformin" and t == "20:00" and d.weekday() >= 5) else 0.06 if (key == "metformin" and t == "20:00") else 0.03):
                    status, miss = "missed", reason
                else:
                    status = "taken_late_logged" if (i > 0 and u2 < 0.08) else "taken"
                if status == "taken":
                    conf = sched + timedelta(minutes=int(u3))
                elif status == "taken_late_logged":
                    conf = sched + timedelta(hours=3, minutes=int(u3))
                elif status == "missed":
                    captured = local_to_utc(datetime.combine(d + timedelta(days=1), time(8, 30)))
                rows["dose_events"].append((uid("dose", med_id[key], sched.isoformat()), U, med_id[key], sched, end, status, conf, miss, captured))
                n_dose += 1
    note("dose_events", "4 doses a day for 60 days plus 7 days ahead; evening-and-weekend miss pattern, a 4-day streak (days 30 to 33 ago), last completed week 24 of 28 taken", n_dose, day(WINDOW_DAYS - 1), day(-7))

    # ------------------------------------------------------------------ glucometer (before the real sensor window)
    real_start = REAL_DAYS + 1
    n = 0
    for i in range(WINDOW_DAYS - 1, real_start - 1, -1):
        d = day(i)
        mean = 6.9 if i >= 22 else 6.9 + (22 - i) / (22 - real_start) * (real_morning_mean - 6.9)     # rising over the last 3 weeks
        v = round(float(np.clip(rng.normal(mean, 0.3), 5.0, 10.0)), 1)
        t = local_to_utc(datetime.combine(d, time(7, 20)) + timedelta(minutes=int(rng.integers(-15, 16))))
        ext = f"{SIM}glucometer:{d}:fasting"
        rows["glucose_readings"].append((uid("glu", ext), U, t, v, "fasting", DEMO_SOURCE, ext, "glucometer", True))
        n += 1
        if rng.random() < 2 / 7:
            v2 = round(float(np.clip(rng.normal(8.8, 1.0), 5.5, 13.0)), 1)
            t2 = local_to_utc(datetime.combine(d, time(14, 30)))
            ext2 = f"{SIM}glucometer:{d}:post_meal_2h"
            rows["glucose_readings"].append((uid("glu", ext2), U, t2, v2, "post_meal_2h", DEMO_SOURCE, ext2, "glucometer", True))
            n += 1
    note("glucose_readings", f"glucometer fasting readings (mean 6.9 rising to {real_morning_mean} over the last 3 weeks before the real sensor days) and about 2 post-meal readings a week", n, day(WINDOW_DAYS - 1), day(real_start))

    # ------------------------------------------------------------------ mood, sleep, steps
    n_mood = n_sleep = n_steps = 0
    for i in range(WINDOW_DAYS - 1, -1, -1):
        d, ramp = day(i), max(0.0, (21 - i) / 21)
        if i >= 1 and rng.random() < 0.8:
            mood = int(np.clip(round(rng.normal(3.7 - 0.7 * ramp, 0.6)), 1, 5))
            stress = int(np.clip(round(rng.normal(2.6 + 1.4 * ramp, 0.6)), 1, 5))
            if i == 1:
                mood, stress = 3, 4                                  # the mock's last evening check-in
            rows["mood_checkins"].append((uid("mood", USER_KEY, d.isoformat()), U, d, mood, stress, int(np.clip(round(rng.normal(3.3 - 0.8 * ramp, 0.7)), 1, 5)), int(np.clip(round(rng.normal(3.2 - 0.6 * ramp, 0.7)), 1, 5))))
            n_mood += 1
        asleep_target = 6.8 if i >= 22 else 6.8 - (22 - i) / 21 * 0.7     # hours, falling to about 6.1
        asleep = 350 if i == 0 else int(np.clip(rng.normal(asleep_target * 60, 25), 270, 540))
        inbed = int(asleep / 0.92)
        end_local = datetime.combine(d, time(6, 50)) + timedelta(minutes=int(rng.integers(-25, 26)))
        start_local = end_local - timedelta(minutes=inbed)
        ext = f"{SIM}sleep:{d}"
        rows["sleep_sessions"].append((uid("sleep", ext), U, local_to_utc(start_local), local_to_utc(end_local), asleep, inbed - asleep, round(100.0 * asleep / inbed, 1), DEMO_SOURCE, ext))
        n_sleep += 1
        if i == 0:
            steps, end_s = 5840, local_to_utc(now_local)
        else:
            base = 8000 if i >= 28 else 8000 - (28 - i) / 21 * 1700 if i >= 7 else 6300
            steps, end_s = int(np.clip(rng.normal(base, 900) * (0.9 if d.weekday() >= 5 else 1.0), 1500, 16000)), at(d + timedelta(days=1), 0)
        ext = f"{SIM}steps:{d}"
        rows["health_samples"].append((uid("hs", ext), U, "steps", at(d, 0), end_s, float(steps), "steps", DEMO_SOURCE, "fitbit_sense", ext))
        n_steps += 1
    note("mood_checkins", "evening check-ins on about 80% of days; mood falling and stress rising over the last 3 weeks", n_mood, day(WINDOW_DAYS - 1), day(1))
    note("sleep_sessions", "one night per day; asleep time falling from about 6.8 h to about 6.1 h, last night 5 h 50 min", n_sleep, day(WINDOW_DAYS - 1), day(0))
    note("health_samples (steps)", "one daily total; about 8,000 falling to about 6,300; today 5,840 so far. Heart rate and active energy are real (import_cgmacros.py)", n_steps, day(WINDOW_DAYS - 1), day(0))

    # ------------------------------------------------------------------ workouts (moderate minutes per 7-day block)
    targets = [55, 70, 95, 120, 140, 140, 150, 145, 150]                        # block 0 is the current week so far
    offsets = [1, 3, 5, 2, 4, 6, 0]
    n_w = 0
    for b, total in enumerate(targets):
        sessions = [5, 3] if b == 0 else offsets[:max(1, round(total / 32))]
        mins = [30, 25] if b == 0 else [total // len(sessions) + (1 if k < total % len(sessions) else 0) for k in range(len(sessions))]
        for off, m in zip(sessions, mins):
            i = 7 * b + off
            if i >= WINDOW_DAYS:
                continue
            d = day(i)
            start = datetime.combine(d, time(18, 40)) + timedelta(minutes=int(rng.integers(-20, 21)))
            ext = f"{SIM}workout:{d}:{off}"
            rows["workouts"].append((uid("workout", ext), U, local_to_utc(start), m * 60, "cycling" if (b >= 5 and off % 3 == 0) else "brisk walk", "moderate", float(int(rng.integers(104, 113))), DEMO_SOURCE, ext))
            n_w += 1
    note("workouts", "moderate minutes per week: 55 so far this week, then 70, 95, 120, 140 and earlier about 145; no strength sessions recently", n_w, day(WINDOW_DAYS - 1), day(0))

    # ------------------------------------------------------------------ blood pressure, symptoms, labs, body
    n_bp = 0
    for i in list(range(1, WINDOW_DAYS, 7)):
        d = day(i)
        recent = max(0.0, (28 - i) / 28)                                # 0 a month ago, 1 today: a slight rise
        sy, di = int(round(rng.normal(128 + 5 * recent, 4))), int(round(rng.normal(80 + 2 * recent, 3)))
        ext = f"{SIM}bp:{d}"
        rows["blood_pressure_readings"].append((uid("bp", ext), U, at(d, 7, 20), sy, min(di, sy - 20), int(round(rng.normal(70, 4))), "home", DEMO_SOURCE, ext))
        n_bp += 1
    note("blood_pressure_readings", "one home reading a week, systolic about 128 to 133, diastolic about 80", n_bp, day(WINDOW_DAYS - 1), day(1))
    chk = [uid("symptom_checkin", USER_KEY, "thirsty"), uid("symptom_checkin", USER_KEY, "foot_tingling")]
    rows["symptom_checkins"] += [(chk[0], U, "checkin.thirsty", at(day(12), 9), at(day(12), 9, 20), json.dumps({"answer": "a_little"}), False),
                                 (chk[1], U, "checkin.foot_tingling", at(day(6), 9), None, None, True)]
    rows["symptom_logs"] += [(uid("symptom", USER_KEY, "headache"), U, at(day(20), 12), "Headache", 1, "user", None),
                             (uid("symptom", USER_KEY, "thirsty"), U, at(day(12), 9, 20), "More thirsty than usual", 2, "checkin", chk[0]),
                             (uid("symptom", USER_KEY, "tired"), U, at(day(5), 15), "Tired in the afternoon", 2, "user", None)]
    note("symptom_logs / symptom_checkins", "3 symptoms and 2 check-in questions (one answered, one skipped)", 5, day(20), day(5))
    for kind, val, unit, ago in (("hba1c", 7.1, "%", 190), ("hba1c", 6.9, "%", 372), ("fasting_glucose", 7.6, "mmol/L", 190)):
        ext = f"{SIM}lab:{kind}:{ago}"
        rows["lab_results"].append((uid("lab", ext), U, kind, val, unit, day(ago), DEMO_SOURCE, ext))
    for kg, ago in ((82.4, 40), (82.9, 70)):
        ext = f"{SIM}body:{ago}"
        rows["body_measurements"].append((uid("body", ext), U, at(day(ago), 7, 30), kg, DEMO_SOURCE, ext))
    note("lab_results / body_measurements", "earlier HbA1c 7.1% and 6.9%, one fasting glucose, two earlier weights (the current labs and weight are real)", 6, day(372), day(40))

    # ------------------------------------------------------------------ meals: earlier days resampled from his own real meals
    by_type = defaultdict(list)
    for r in real_meals:
        by_type[r[0]].append(r)
    n_meal = 0
    for i in range(WINDOW_DAYS - 1, real_start - 1, -1):
        d = day(i)
        for mtype, hh, mm in (("breakfast", 8, 5), ("lunch", 12, 30), ("dinner", 19, 30)):
            pool = by_type.get(mtype) or []
            if not pool:
                continue
            pick = pool[int(rng.integers(0, len(pool)))]
            t = at(d, hh, mm) + timedelta(minutes=int(rng.integers(-15, 16)))
            mid = uid("meal", "sim", USER_KEY, d.isoformat(), mtype)
            rows["meals"].append((mid, U, t, mtype, "Simulated meal: copied from one of this person's real CGMacros meals", DEMO_SOURCE))
            rows["meal_items"].append((uid("mealitem", mid), mid, f"{mtype} (dataset meal, copied)", 1.0, pick[1], pick[2], pick[3], pick[4], pick[5], "dataset", "derived"))
            n_meal += 1
    note("meals / meal_items", "3 meals a day for the days before the real sensor window, each copied from one of his own real meals of the same type (values are real, dates are simulated)", n_meal, day(WINDOW_DAYS - 1), day(real_start))

    # ------------------------------------------------------------------ profile extras, care plan, setup
    rows["conditions"] += [(uid("condition", USER_KEY, "t2d"), U, "Type 2 diabetes", D.year - 6), (uid("condition", USER_KEY, "htn"), U, "High blood pressure", D.year - 4)]
    rows["family_history"].append((uid("family", USER_KEY, "father"), U, "father", "Type 2 diabetes"))
    rows["consents"].append((uid("consent", USER_KEY, "data_processing"), U, "data_processing", "v1", at(day(WINDOW_DAYS), 9)))
    appts = [("diabetes_review", "planned", D + timedelta(days=9), "Polyclinic (demo)", None, at(day(3), 20)),
             ("diabetes_review", "completed", day(125), "Polyclinic (demo)", None, at(day(130), 20)),
             ("foot_screening", "completed", day(344), "Polyclinic (demo)", None, at(day(350), 20)),
             ("eye_screening", "completed", day(760), "Eye clinic (demo)", None, at(day(765), 20)),
             ("kidney_test", "completed", day(200), "Polyclinic (demo)", None, at(day(205), 20)),
             ("eye_screening", "suggested", None, None, json.dumps({"due": "overdue"}), None)]
    for kind, status, when, loc, reason, conf in appts:
        rows["appointments"].append((uid("appointment", USER_KEY, kind, status, str(when)), U, kind, status, None if when is None else at(when, 10), loc, reason, conf))
    intervals = {"eye_screening": 12, "foot_screening": 12, "kidney_test": 12, "hba1c_test": 6, "vaccination": 12, "diabetes_review": 6}
    last_done = {"eye_screening": day(760), "foot_screening": day(344), "kidney_test": day(200), "hba1c_test": day(REAL_DAYS), "vaccination": None, "diabetes_review": day(125)}
    for kind, months in intervals.items():
        last = last_done[kind]
        nxt = add_months(last, months) if last else None
        status = "unknown" if nxt is None else "overdue" if nxt < D else "due_soon" if (nxt - D).days <= 30 else "ok"
        rows["patient_preventive_status"].append((U, uid("preventive", kind), last, nxt, status))
    note("conditions / family_history / consents / appointments / patient_preventive_status", "persona from the mock: eye screening overdue, foot check due in about 3 weeks, next diabetes review in 9 days, flu vaccination not recorded", 20, day(WINDOW_DAYS), day(-9))
    rows["devices"] += [(uid("device", USER_KEY, "watch"), U, "watch", "Smart watch (demo data from a Fitbit Sense)", DEMO_SOURCE, local_to_utc(now_local), "connected"),
                        (uid("device", USER_KEY, "cgm"), U, "cgm", "Glucose sensors (Libre Pro and Dexcom G6, demo data)", DEMO_SOURCE, local_to_utc(now_local), "connected"),
                        (uid("device", USER_KEY, "camera"), U, "phone_camera", "Phone camera", "manual", None, "connected")]
    rows["health_goals"] += [(uid("goal", USER_KEY, "moderate"), U, "weekly_moderate_minutes", 150, "minutes", "default", True),
                             (uid("goal", USER_KEY, "strength"), U, "weekly_strength_sessions", 2, "sessions", "default", True)]
    note("devices / health_goals", "3 connected sources; 2 default goals (150 moderate minutes and 2 strength sessions a week) marked as defaults until a clinician sets them", 5, D, D)
    return rows, disc
