"""The doctor report (prd F12): every number on the printable "Diabetes monitoring report", computed in code.

Layout and sections follow Damien's report design (2026-10-09). Nothing here calls a model: the report is counts, percentages
and percentiles of the person's own stored data (rules.md 1.2), and its sentences are fixed templates filled with those numbers.

What the report does not do, on purpose:
  - it does not say why something happened. A symptom is shown next to the glucose reading and the last dose that came before
    it; whether one led to the other is for the clinician (rules.md: "associated with", never "caused by");
  - it does not advise on any medicine (rules.md 1.1);
  - it does not call anything normal, safe or validated (rules.md 1.7, 1.15).

`build()` is pure (lists in, a dict out) so it can be tested without a database. `load()` reads the rows for one person.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from itertools import pairwise
from typing import Any
from zoneinfo import ZoneInfo

import psycopg

from app.services.insights import MISS_LABELS, patterns_for

# clinical validation pending
# Reference values printed in the "Reference" columns. They are the international consensus figures for CGM reports as used in
# Damien's design; no clinician has set them for this project and they are never personal targets. Change them here only.
REFERENCE = {
    "very_low_mmol": 3.0,          # below this is "very low"
    "very_high_mmol": 13.9,        # above this is "very high"
    "in_range_min_pct": 70.0,
    "low_max_pct": 4.0,            # all time below range
    "very_low_max_pct": 1.0,
    "high_max_pct": 25.0,          # all time above range
    "very_high_max_pct": 5.0,
    "cv_max_pct": 36.0,
    "cgm_active_min_pct": 70.0,    # below this the glucose figures are marked as based on too little data
}
ALLOWED_DAYS = (7, 14, 30, 90)
NEAREST_GLUCOSE = timedelta(minutes=15)   # a symptom is matched to a reading at most this far away
NEAREST_WATCH = timedelta(minutes=10)
DOSE_LOOKBACK = timedelta(hours=6)        # "last dose before" looks this far back
MIN_PROFILE_READINGS = 5                  # readings needed in an hour of the day before its percentiles are drawn
MAX_EPISODES = 20
SLEEP_BUCKET_MIN = 4                      # a 5-minute watch bucket counts as asleep from this many minutes
HIGH_STRESS = 4                           # self-rated stress (1 to 5) counted as "high"
WORTH_MAX = 5                             # "Worth discussing" shows at most this many observations
FACT_CATEGORIES = ("barrier", "routine", "food_response")   # memory fact categories shown there (the enum has no "activity")
FACT_LABELS = {"barrier": "Barrier", "routine": "Routine", "food_response": "Food response"}

SYMPTOM_LABELS = {
    "numbness": "Numbness", "tingling": "Tingling", "blurred_vision": "Blurred vision", "fatigue": "Fatigue", "thirst": "Thirst",
    "frequent_urination": "Passing urine often", "dizziness": "Dizziness", "headache": "Headache", "shaky_sweaty": "Shaky or sweaty",
    "nausea": "Nausea", "foot_pain": "Foot pain", "slow_healing_wound": "Slow-healing wound", "other": "Other",
}


@dataclass
class Inputs:
    now: datetime                                   # timezone-aware
    tz: ZoneInfo
    start: date                                     # first local day of the period
    end: date                                       # last local day of the period (inclusive)
    profile: dict[str, Any] | None = None           # display_name, birth_year, gender, has_diabetes, glucose_target_low/high
    cgm: list[tuple[datetime, float]] = field(default_factory=list)                 # quality_ok readings only
    symptoms: list[dict[str, Any]] = field(default_factory=list)                    # occurred_at, symptom_type, severity, note
    medicines: list[dict[str, Any]] = field(default_factory=list)                   # id, name, strength, frequency, as_needed
    doses: list[dict[str, Any]] = field(default_factory=list)                       # medication_id, scheduled_at, taken_at, status
    watch: list[dict[str, Any]] = field(default_factory=list)                       # recorded_at, heart_rate_bpm, spo2_pct, steps, sleep_minutes
    stress: list[tuple[datetime, int]] = field(default_factory=list)                # wellbeing_logs.stress_self
    alerts: list[dict[str, Any]] = field(default_factory=list)                      # med_a_id, med_b_id, med_a, med_b, summary, origin
    questions: list[str] = field(default_factory=list)                              # open doctor questions
    patterns: list[dict[str, Any]] = field(default_factory=list)                    # pattern_key, n_pairs, median_delta (status open)
    facts: list[dict[str, Any]] = field(default_factory=list)                       # statement, category, confidence (confirmed)


# ----------------------------------------------------------------------------------------------- small helpers
def _r1(x: float) -> float:
    return round(x + 1e-9, 1)


def _percentile(sorted_vals: list[float], p: float) -> float:
    """Linear-interpolated percentile of an already sorted list (p from 0 to 100)."""
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def _duration(minutes: float) -> str:
    m = round(minutes)
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d} min"


def _day(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _stamp(dt: datetime) -> str:
    return f"{dt.strftime('%a')} {dt.day} {dt.strftime('%b')} {dt.strftime('%H:%M')}"


def _nearest(points: list[tuple[datetime, float]], at: datetime, within: timedelta) -> tuple[datetime, float] | None:
    best: tuple[datetime, float] | None = None
    for p in points:
        gap = abs(p[0] - at)
        if gap <= within and (best is None or gap < abs(best[0] - at)):
            best = p
    return best


def _span(lo: float, hi: float, fmt: str = "g") -> str:
    """'94–96', or just '94' when both ends are the same."""
    return format(lo, fmt) if lo == hi else f"{format(lo, fmt)}–{format(hi, fmt)}"


def _label(name: str, strength: str | None) -> str:
    n = " ".join(name.split())
    return n if not strength or strength.lower().replace(" ", "") in n.lower().replace(" ", "") else f"{n} {strength.strip()}"


def _origin(origin: str | None) -> str:
    return {"database": "drug-label rules", "ai": "AI web search", "both": "drug-label rules and AI web search"}.get(origin or "", "medicine check")


# ----------------------------------------------------------------------------------------------- the sections
def _glucose(i: Inputs, low: float, high: float) -> dict[str, Any]:
    days = (i.end - i.start).days + 1
    values = [v for _, v in i.cgm]
    if not values:
        return {"has_data": False, "sufficient": False, "bands": [], "metrics": [], "profile": [], "active_pct": 0.0, "readings": 0}
    stamps = sorted(t for t, _ in i.cgm)
    gaps = sorted((b - a).total_seconds() / 60 for a, b in pairwise(stamps) if b > a)
    interval = max(1.0, statistics.median(gaps)) if gaps else 5.0
    expected = days * 1440 / interval
    active = min(100.0, 100.0 * len(values) / expected) if expected else 0.0
    n = len(values)
    vl, vh = REFERENCE["very_low_mmol"], REFERENCE["very_high_mmol"]
    share = {
        "very_high": 100.0 * sum(v > vh for v in values) / n,
        "high": 100.0 * sum(high < v <= vh for v in values) / n,
        "in_range": 100.0 * sum(low <= v <= high for v in values) / n,
        "low": 100.0 * sum(vl <= v < low for v in values) / n,
        "very_low": 100.0 * sum(v < vl for v in values) / n,
    }
    below, above = share["low"] + share["very_low"], share["high"] + share["very_high"]

    def band(key: str, label: str, reference: str, outside: bool) -> dict[str, Any]:
        return {"key": key, "label": label, "pct": _r1(share[key]), "per_day": _duration(share[key] / 100 * 1440), "reference": reference, "outside": outside}

    bands = [
        band("very_high", f"Very high >{vh:g}", f"<{REFERENCE['very_high_max_pct']:g}", share["very_high"] >= REFERENCE["very_high_max_pct"]),
        band("high", f"High {high + 0.1:.1f}–{vh:g}", f"<{REFERENCE['high_max_pct']:g} (all >{high:g})", above >= REFERENCE["high_max_pct"]),
        band("in_range", f"In range {low:g}–{high:.1f}", f">{REFERENCE['in_range_min_pct']:g}", share["in_range"] <= REFERENCE["in_range_min_pct"]),
        band("low", f"Low {vl:.1f}–{low - 0.1:.1f}", f"<{REFERENCE['low_max_pct']:g} (all <{low:g})", below >= REFERENCE["low_max_pct"]),
        band("very_low", f"Very low <{vl:.1f}", f"<{REFERENCE['very_low_max_pct']:g}", share["very_low"] >= REFERENCE["very_low_max_pct"]),
    ]
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if n > 1 else 0.0
    cv = 100.0 * sd / mean if mean else 0.0
    gmi = 3.31 + 0.02392 * mean * 18.016          # Glucose Management Indicator, the published formula (mean in mg/dL)
    metrics = [
        {"label": "Mean glucose", "value": f"{mean:.1f}", "reference": "—", "outside": False},
        {"label": "GMI (estimated from mean glucose)", "value": f"{gmi:.1f}%", "reference": "Individual", "outside": False},
        {"label": "Standard deviation", "value": f"{sd:.1f}", "reference": "—", "outside": False},
        {"label": "Variability (CV)", "value": f"{cv:.0f}%", "reference": f"≤{REFERENCE['cv_max_pct']:g}%", "outside": cv > REFERENCE["cv_max_pct"]},
        {"label": "CGM active", "value": f"{active:.0f}%", "reference": f"≥{REFERENCE['cgm_active_min_pct']:g}%", "outside": active < REFERENCE["cgm_active_min_pct"]},
    ]
    by_hour: dict[int, list[float]] = defaultdict(list)
    for t, v in i.cgm:
        by_hour[t.astimezone(i.tz).hour].append(v)
    profile = []
    for hour in range(24):
        vals = sorted(by_hour.get(hour, []))
        if len(vals) >= MIN_PROFILE_READINGS:
            profile.append({"hour": hour, "p5": _r1(_percentile(vals, 5)), "p25": _r1(_percentile(vals, 25)), "p50": _r1(_percentile(vals, 50)),
                            "p75": _r1(_percentile(vals, 75)), "p95": _r1(_percentile(vals, 95))})
    return {"has_data": True, "sufficient": active >= REFERENCE["cgm_active_min_pct"], "bands": bands, "metrics": metrics, "profile": profile,
            "active_pct": float(round(active)), "readings": n, "in_range_pct": _r1(share["in_range"]), "below_pct": _r1(below), "very_low_pct": _r1(share["very_low"]),
            "cv_pct": round(cv), "low": low, "high": high, "very_low": vl, "very_high": vh}


def _episodes(i: Inputs, low: float, high: float) -> list[dict[str, Any]]:
    """One row per symptom entry: the nearest reading, the change over the 30 minutes before, the last dose taken before it, and the watch."""
    names = {str(m["id"]): _label(str(m["name"]), m.get("strength")) for m in i.medicines}
    taken = sorted((d["taken_at"], str(d["medication_id"])) for d in i.doses if d.get("status") == "taken" and d.get("taken_at"))
    hr = [(w["recorded_at"], float(w["heart_rate_bpm"])) for w in i.watch if w.get("heart_rate_bpm") is not None]
    spo2 = [(w["recorded_at"], float(w["spo2_pct"])) for w in i.watch if w.get("spo2_pct") is not None]
    out = []
    for s in sorted(i.symptoms, key=lambda x: x["occurred_at"]):
        at: datetime = s["occurred_at"]
        g = _nearest(i.cgm, at, NEAREST_GLUCOSE)
        before = _nearest(i.cgm, at - timedelta(minutes=30), timedelta(minutes=10)) if g else None
        last = next(((t, mid) for t, mid in reversed(taken) if timedelta(0) <= at - t <= DOSE_LOOKBACK), None)
        h, o = _nearest(hr, at, NEAREST_WATCH), _nearest(spo2, at, NEAREST_WATCH)
        zone = None if g is None else "very_low" if g[1] < REFERENCE["very_low_mmol"] else "low" if g[1] < low else "high" if g[1] > high else "in_range"
        out.append({
            "at": at.astimezone(i.tz), "when": _stamp(at.astimezone(i.tz)), "type": str(s["symptom_type"]), "symptom": SYMPTOM_LABELS.get(str(s["symptom_type"]), str(s["symptom_type"])),
            "severity": s.get("severity"), "glucose": None if g is None else _r1(g[1]), "zone": zone,
            "change_30": None if g is None or before is None else _r1(g[1] - before[1]),
            "last_dose": None if last is None else f"{names.get(last[1], 'A medicine')}, {_duration((at - last[0]).total_seconds() / 60)} before",
            "heart_rate": None if h is None else round(h[1]), "spo2": None if o is None else round(o[1]),
            "note": (str(s.get("note") or "").strip()[:80] or None),
        })
    return out


def _symptom_table(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for e in episodes:
        r = rows.setdefault(e["type"], {"symptom": e["symptom"], "logged": 0, "low": 0, "high": 0, "in_range": 0, "no_reading": 0, "times": []})
        r["logged"] += 1
        key = "no_reading" if e["zone"] is None else "low" if e["zone"] in ("low", "very_low") else e["zone"]
        r[key] += 1
        if key == "low":
            r["times"].append(e["at"])
    out = []
    for r in sorted(rows.values(), key=lambda x: (-x["low"], -x["logged"], x["symptom"])):
        times = r.pop("times")
        r["note"] = "—"
        if times:
            clock = sorted(t.strftime("%H:%M") for t in times)
            r["note"] = f"Low readings at {clock[0]}" if len(clock) == 1 else f"Low readings between {clock[0]} and {clock[-1]}"
        elif r["logged"] >= 2 and r["in_range"] == r["logged"]:
            r["note"] = "Glucose in range at every entry"
        out.append(r)
    return out


def _medicines(i: Inputs) -> tuple[list[dict[str, Any]], str | None]:
    flagged = {str(a[k]) for a in i.alerts for k in ("med_a_id", "med_b_id") if a.get(k)}
    by_med: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in i.doses:
        by_med[str(d["medication_id"])].append(d)
    rows, missed_notes = [], []
    for m in i.medicines:
        mid = str(m["id"])
        due = [d for d in by_med.get(mid, []) if d.get("scheduled_at") and d["scheduled_at"] <= i.now]
        extra = sum(1 for d in by_med.get(mid, []) if not d.get("scheduled_at") and d.get("status") == "taken")
        taken = sum(d["status"] == "taken" for d in due)
        missed = [d for d in due if d["status"] == "missed"]
        not_logged = sum(d["status"] == "pending" for d in due)
        counted = [d for d in due if d["status"] != "skipped"]
        freq = int(m.get("frequency") or 0)
        regimen = "Only when needed" if m.get("as_needed") else {1: "Once a day", 2: "Twice a day", 3: "3 times a day"}.get(freq, f"{freq} times a day" if freq else "—")
        if not due and not extra and m.get("as_needed") is None and not freq:
            continue
        rows.append({
            "name": _label(str(m["name"]), m.get("strength")), "regimen": regimen, "scheduled": len(counted) if counted else None,
            "taken": taken + extra if (counted or extra) else None, "missed": len(missed) if counted else None, "not_logged": not_logged if counted else None,
            "adherence_pct": round(100.0 * taken / len(counted)) if counted else None, "interaction": mid in flagged,
        })
        if missed:
            when = ", ".join(f"{_day(d['scheduled_at'].astimezone(i.tz).date())} {d['scheduled_at'].astimezone(i.tz).strftime('%H:%M')}" for d in sorted(missed, key=lambda x: x["scheduled_at"])[:8])
            missed_notes.append(f"{_label(str(m['name']), m.get('strength'))}: {when}{' and more' if len(missed) > 8 else ''}")
    note = None
    if rows:
        note = ("Doses marked missed: " + "; ".join(missed_notes) + ". " if missed_notes else "") + \
            '"Not logged" means no answer was recorded; it is counted separately from doses marked missed. Adherence is doses marked taken out of doses scheduled.'
    return rows, note


def _mornings(i: Inputs) -> list[date]:
    return [i.start + timedelta(days=k) for k in range((i.end - i.start).days + 1)]


def _nights(i: Inputs) -> dict[str, dict[date, list[float]]]:
    """Watch readings while asleep, grouped by the morning the night ends on (a night belongs to the day it started).
    Only the period's mornings are kept, so the widened watch read at the start of the period does not leak in."""
    keep = set(_mornings(i))
    hr: dict[date, list[float]] = defaultdict(list)
    o2: dict[date, list[float]] = defaultdict(list)
    for w in i.watch:
        local = w["recorded_at"].astimezone(i.tz)
        morning = (local - timedelta(hours=12)).date() + timedelta(days=1)
        if (w.get("sleep_minutes") or 0) < SLEEP_BUCKET_MIN or morning not in keep:
            continue
        if w.get("heart_rate_bpm") is not None:
            hr[morning].append(float(w["heart_rate_bpm"]))
        if w.get("spo2_pct") is not None:
            o2[morning].append(float(w["spo2_pct"]))
    return {"hr": hr, "o2": o2}


def _overnight(i: Inputs) -> list[dict[str, Any]]:
    """One column per morning: fasting glucose (05:00 to 07:00, the insights definition) beside the night's heart rate and SpO2.
    A morning with no reading is None, never zero."""
    fasting: dict[date, list[float]] = defaultdict(list)
    for t, v in i.cgm:
        local = t.astimezone(i.tz)
        if local.hour in (5, 6):
            fasting[local.date()].append(v)
    nights = _nights(i)
    out = []
    for m in _mornings(i):
        f = fasting.get(m)
        hr = nights["hr"].get(m)
        o2 = nights["o2"].get(m)
        out.append({"day": _day(m), "fasting": None if not f else _r1(statistics.fmean(f)),
                    "heart_rate": None if not hr else round(statistics.fmean(hr)), "spo2": None if not o2 else round(statistics.fmean(o2))})
    return out


def _worth_discussing(i: Inputs, days: int) -> list[dict[str, Any]]:
    """Up to WORTH_MAX observations from the person's own data, most important first. Worded as what was recorded, never as advice."""
    clash = [{"text": f"A possible interaction is flagged between {a['med_a']} and {a['med_b']}.",
              "evidence": f"Open alert · source: {_origin(a.get('origin'))}, not clinically reviewed", "kind": "clash"} for a in i.alerts]
    missed = [d for d in i.doses if d.get("status") == "missed"]
    reasons = Counter(str(d["miss_reason"]) for d in missed if d.get("miss_reason"))
    adherence = []
    if reasons:
        reason, n = reasons.most_common(1)[0]
        adherence = [{"text": f"Missed doses marked '{MISS_LABELS.get(reason, reason)}': {n} in {days} days.",
                      "evidence": f"{n} of {len(missed)} doses marked missed in the period", "kind": "adherence"}]
    patterns = [{"text": p["text"], "evidence": f"{p['n']} matched events · an association, not checked yet", "kind": "pattern"}
                for p in patterns_for(i.patterns)]
    facts = [{"text": str(f["statement"]), "evidence": f"Confirmed by you · {FACT_LABELS.get(str(f['category']), str(f['category']))}", "kind": "fact"}
             for f in sorted(i.facts, key=lambda x: -float(x.get("confidence") or 0)) if str(f.get("category")) in FACT_CATEGORIES]
    return [*clash, *adherence, *patterns, *facts][:WORTH_MAX]


def _activity(i: Inputs) -> list[dict[str, Any]]:
    steps: dict[date, int] = defaultdict(int)
    for w in i.watch:
        local = w["recorded_at"].astimezone(i.tz)
        if w.get("steps") is not None and i.start <= local.date() <= i.end:
            steps[local.date()] += int(w["steps"])
    nights = _nights(i)
    cells: list[dict[str, Any]] = []
    if steps:
        vals = list(steps.values())
        cells.append({"label": "Steps", "value": f"{round(statistics.fmean(vals)):,}/day", "sub": f"range {min(vals):,}–{max(vals):,}"})
    else:
        cells.append({"label": "Steps", "value": "No data", "sub": ""})
    for label, key, unit in (("Heart rate while asleep", "hr", " bpm"), ("SpO2 while asleep", "o2", "%")):
        nightly = [statistics.fmean(v) for v in nights[key].values() if v]
        if nightly:
            cells.append({"label": label, "value": f"{round(statistics.fmean(nightly))}{unit}", "sub": f"nightly {_span(round(min(nightly)), round(max(nightly)))}{unit}"})
        else:
            cells.append({"label": label, "value": "No data", "sub": ""})
    worst: dict[date, int] = {}
    for t, s in i.stress:
        d = t.astimezone(i.tz).date()
        worst[d] = max(worst.get(d, 0), s)
    if worst:
        high = sorted(d for d, s in worst.items() if s >= HIGH_STRESS)
        cells.append({"label": "Stress (self-rated)", "value": f"High on {len(high)} of {len(worst)} logged days", "sub": ", ".join(_day(d) for d in high[:6])})
    else:
        cells.append({"label": "Stress (self-rated)", "value": "No data", "sub": ""})
    return cells


def _alerts(i: Inputs, glucose: dict[str, Any], episodes: list[dict[str, Any]], symptoms: list[dict[str, Any]], meds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    vl = REFERENCE["very_low_mmol"]
    very_low = [(t, v) for t, v in i.cgm if v < vl]
    if very_low:
        t, v = min(very_low, key=lambda p: p[1])
        days = len({x[0].astimezone(i.tz).date() for x in very_low})
        out.append({"priority": "urgent", "title": f"Glucose below {vl:.1f} mmol/L",
                    "detail": f"{len(very_low)} reading{'s' if len(very_low) != 1 else ''} on {days} day{'s' if days != 1 else ''} · lowest {v:.1f} mmol/L on {_stamp(t.astimezone(i.tz))}"})
    for e in episodes:
        if e["zone"] == "very_low":
            out.append({"priority": "urgent", "title": f"{e['symptom']} logged with very low glucose",
                        "detail": f"{e['when']} · glucose {e['glucose']:.1f} mmol/L" + (f" · last dose before: {e['last_dose']}" if e["last_dose"] else "")})
    for a in i.alerts:
        summary = " ".join(str(a.get("summary") or "").split())
        out.append({"priority": "interaction", "title": f"{a['med_a']} + {a['med_b']}",
                    "detail": f"Possible interaction. {summary + ' ' if summary else ''}Source: {_origin(a.get('origin'))}, not clinically reviewed."})
    for s in symptoms:
        if s["low"] >= 2:
            out.append({"priority": "review", "title": f"{s['symptom']} with low glucose", "detail": f"{s['low']} of {s['logged']} entries · {s['note']}"})
        elif s["logged"] >= 2 and s["in_range"] == s["logged"]:
            rows = [e for e in episodes if e["symptom"] == s["symptom"]]
            g = [e["glucose"] for e in rows if e["glucose"] is not None]
            hr = [e["heart_rate"] for e in rows if e["heart_rate"] is not None]
            o2 = [e["spo2"] for e in rows if e["spo2"] is not None]
            parts = [f"{s['logged']}×", f"glucose {_span(min(g), max(g), '.1f')} mmol/L"]
            if o2:
                parts.append(f"SpO2 {_span(min(o2), max(o2))}%")
            if hr:
                parts.append(f"HR {_span(min(hr), max(hr))} bpm")
            out.append({"priority": "review", "title": f"{s['symptom']} with glucose in range", "detail": " · ".join(parts)})
    for m in meds:
        if m["missed"]:
            out.append({"priority": "review", "title": f"Missed doses: {m['name']}", "detail": f"{m['missed']} of {m['scheduled']} scheduled doses marked missed"})
    if glucose["has_data"] and not glucose["sufficient"]:
        out.append({"priority": "review", "title": "Little sensor data", "detail": f"CGM active {glucose['active_pct']:.0f}% of the period; the glucose figures may not be representative"})
    return out


def _findings(glucose: dict[str, Any], episodes: list[dict[str, Any]], meds: list[dict[str, Any]], n_interactions: int) -> list[str]:
    out: list[str] = []
    if glucose["has_data"]:
        out.append(f"Time in range {glucose['in_range_pct']:.0f}% (reference >{REFERENCE['in_range_min_pct']:g}%); time below range {glucose['below_pct']:.0f}% "
                   f"(reference <{REFERENCE['low_max_pct']:g}%), including {glucose['very_low_pct']:.1f}% below {glucose['very_low']:.1f} mmol/L; CV {glucose['cv_pct']}%.")
    else:
        out.append("No sensor glucose readings in this period.")
    matched = [e for e in episodes if e["zone"] is not None]
    lows = [e for e in matched if e["zone"] in ("low", "very_low")]
    if lows:
        clock = sorted(e["at"].strftime("%H:%M") for e in lows)
        span = f"at {clock[0]}" if len(clock) == 1 else f"between {clock[0]} and {clock[-1]}"
        out.append(f"{len(lows)} of {len(episodes)} symptom entries were logged with glucose below {glucose['low']:g} mmol/L, {span}.")
    elif episodes:
        out.append(f"{len(episodes)} symptom entries were logged; none with glucose below {glucose.get('low', 3.9):g} mmol/L" + ("." if matched else " (no sensor reading near them)."))
    else:
        out.append("No symptoms were logged in this period.")
    with_pct = [m for m in meds if m["adherence_pct"] is not None]
    if with_pct:
        text = "Doses marked taken: " + ", ".join(f"{m['name']} {m['adherence_pct']}%" for m in with_pct[:4]) + "."
        if n_interactions:
            text += f" {n_interactions} possible medicine interaction{'s' if n_interactions != 1 else ''} flagged."
        out.append(text)
    elif n_interactions:
        out.append(f"{n_interactions} possible medicine interaction{'s' if n_interactions != 1 else ''} flagged.")
    return out


def build(i: Inputs) -> dict[str, Any]:
    p = i.profile or {}
    low = float(p.get("glucose_target_low") or 3.9)
    high = float(p.get("glucose_target_high") or 10.0)
    start_dt = datetime.combine(i.start, time.min, i.tz)
    end_dt = datetime.combine(i.end + timedelta(days=1), time.min, i.tz)
    i.cgm = sorted((t, float(v)) for t, v in i.cgm if start_dt <= t < end_dt)
    glucose = _glucose(i, low, high)
    episodes = _episodes(i, low, high)
    symptoms = _symptom_table(episodes)
    meds, med_note = _medicines(i)
    alerts = _alerts(i, glucose, episodes, symptoms, meds)
    days = (i.end - i.start).days + 1
    sources = [s for s, has in (("CGM", bool(i.cgm)), ("wrist wearable", bool(i.watch)), ("patient logs", bool(i.symptoms or i.doses or i.stress))) if has]
    birth = p.get("birth_year")
    gender = {"female": "Female", "male": "Male", "other": "Other"}.get(str(p.get("gender") or ""), "")
    age = f"{i.now.astimezone(i.tz).year - int(birth)}" if birth else ""
    diabetes = {"yes": "Diabetes (self-reported)", "not_sure": "Diabetes: not sure (self-reported)", "no": "No diabetes (self-reported)"}.get(str(p.get("has_diabetes") or ""), "Not recorded")
    return {
        "generated_on": _day(i.now.astimezone(i.tz).date()) + f" {i.now.astimezone(i.tz).year}",
        "period": {"start": i.start.isoformat(), "end": i.end.isoformat(), "days": days, "label": f"{_day(i.start)} – {_day(i.end)} {i.end.year} ({days} days)"},
        "patient": {"name": str(p.get("display_name") or "Not recorded"), "sex_age": ", ".join(x for x in (gender, age) if x) or "Not recorded", "diagnosis": diabetes},
        "cgm_wear": f"{glucose['active_pct']:.0f}% of period" if glucose["has_data"] else "No sensor data",
        "sources": " · ".join(sources) if sources else "No data in this period",
        "key_findings": _findings(glucose, episodes, meds, len(i.alerts)),
        "alerts": alerts,
        "glucose": {k: glucose.get(k) for k in ("has_data", "sufficient", "bands", "metrics", "profile", "low", "high", "very_low", "very_high")},
        "symptoms": symptoms,
        "episodes": [{k: v for k, v in e.items() if k not in ("at", "type")} for e in episodes[-MAX_EPISODES:]],
        "episodes_total": len(episodes),
        "medicines": meds,
        "medicines_note": med_note,
        "activity": _activity(i),
        "overnight": _overnight(i),
        "worth_discussing": _worth_discussing(i, days),
        "questions": i.questions[:12],
    }


# ----------------------------------------------------------------------------------------------- reading the rows
def load(conn: psycopg.Connection[Any], user_id: str, days: int, now: datetime) -> Inputs:
    """The rows for one person and one period. The period ends on the day of their latest sensor reading (today if there is none),
    so a loaded demo patient whose data stops earlier still gets a full report."""
    prof = conn.execute("select display_name, birth_year, gender, has_diabetes, glucose_target_low, glucose_target_high, timezone from user_profile where user_id = %s",
                        (user_id,)).fetchone()
    profile = dict(prof) if prof else None
    tz = ZoneInfo(str(profile["timezone"])) if profile and profile.get("timezone") else ZoneInfo("Asia/Singapore")
    latest = conn.execute("select max(recorded_at) as t from cgm_readings where user_id = %s and quality_ok and recorded_at <= %s", (user_id, now)).fetchone()
    anchor = latest["t"] if latest and latest["t"] else now
    end = anchor.astimezone(tz).date()
    start = end - timedelta(days=days - 1)
    lo = datetime.combine(start, time.min, tz)
    hi = datetime.combine(end + timedelta(days=1), time.min, tz)
    span = (user_id, lo, hi)
    cgm = [(r["recorded_at"], float(r["glucose_mmol"])) for r in conn.execute(
        "select recorded_at, glucose_mmol from cgm_readings where user_id = %s and quality_ok and recorded_at >= %s and recorded_at < %s order by recorded_at", span)]
    symptoms = [dict(r) for r in conn.execute(
        "select occurred_at, symptom_type::text as symptom_type, severity, note from symptom_logs "
        "where user_id = %s and deleted_at is null and occurred_at >= %s and occurred_at < %s order by occurred_at", span)]
    medicines = [dict(r) for r in conn.execute(
        "select id, name, strength, frequency, as_needed from medications where user_id = %s and deleted_at is null order by start_date nulls last, created_at, name", (user_id,))]
    doses = [dict(r) for r in conn.execute(
        "select medication_id, scheduled_at, taken_at, status::text as status, miss_reason::text as miss_reason from medication_log "
        "where user_id = %s and coalesce(scheduled_at, taken_at) >= %s and coalesce(scheduled_at, taken_at) < %s", span)]
    # one day wider at the start, so the first morning's night (which began the evening before) is complete
    watch = [dict(r) for r in conn.execute(
        "select recorded_at, heart_rate_bpm, spo2_pct, steps, sleep_minutes from watch_readings where user_id = %s and recorded_at >= %s and recorded_at < %s",
        (user_id, lo - timedelta(days=1), hi))]
    stress = [(r["recorded_at"], int(r["stress_self"])) for r in conn.execute(
        "select recorded_at, stress_self from wellbeing_logs where user_id = %s and deleted_at is null and stress_self is not null and recorded_at >= %s and recorded_at < %s", span)]
    alerts = [{"med_a_id": r["med_a_id"], "med_b_id": r["med_b_id"], "med_a": _label(r["a_name"], r["a_strength"]), "med_b": _label(r["b_name"], r["b_strength"]),
               "summary": r["summary"], "origin": r["origin"]} for r in conn.execute(
        "select a.med_a_id, a.med_b_id, a.summary, a.origin, ma.name as a_name, ma.strength as a_strength, mb.name as b_name, mb.strength as b_strength "
        "from interaction_alerts a join medications ma on ma.id = a.med_a_id and ma.deleted_at is null join medications mb on mb.id = a.med_b_id and mb.deleted_at is null "
        "where a.user_id = %s and a.status = 'open' and a.med_b_id is not null order by a.created_at, a.id", (user_id,))]
    questions = [str(r["text"]) for r in conn.execute("select text from doctor_questions where user_id = %s and status = 'open' order by created_at", (user_id,))]
    patterns = [dict(r) for r in conn.execute(
        "select pattern_key, n_pairs, median_delta from pattern_candidates where user_id = %s and status = 'open' order by n_pairs desc", (user_id,))]
    facts = [dict(r) for r in conn.execute(
        "select statement, category::text as category, confidence from memory_facts where user_id = %s and status = 'active' "
        "and category::text = any(%s) order by confidence desc nulls last, updated_at desc", (user_id, list(FACT_CATEGORIES)))]
    return Inputs(now=now, tz=tz, start=start, end=end, profile=profile, cgm=cgm, symptoms=symptoms, medicines=medicines, doses=doses, watch=watch,
                  stress=stress, alerts=alerts, questions=questions, patterns=patterns, facts=facts)
