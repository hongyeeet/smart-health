"""Diet tracking, day by day (K10 calendar): the meals logged on each Singapore day and their macro totals. Read only.

A day's total for a macro is shown only when every meal that day has that value. One meal with an unknown value makes the day's
total unknown (None), never a lower number. Energy is the 4, 4 and 9 kcal rule (`day.kcal`, the same rule the Day view uses), except
that a kcal the person typed themselves is kept and used instead (`meal_kcal`). Those meals are marked `numbers_from` "you".
The pure part (`summarise_days`) takes plain rows, so the rules are tested without the database.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.db.logstore import TZ, current_user, tx
from app.services import day as D

MAX_RANGE_DAYS = 92  # three calendar months (the Insights 90-day period fits); longer ranges are refused, not truncated
MACROS = ("carbs", "protein", "fat", "sugar", "fibre", "sodium")


def _num(x: Any, digits: int = 1) -> float | None:
    return None if x is None else round(float(x), digits)


def _total(values: list[Any], digits: int = 1) -> float | None:
    """Sum of one macro over a day's meals; None unless every meal has the value."""
    if not values or any(v is None for v in values):
        return None
    return round(sum(float(v) for v in values), digits)


def _clock(ts: datetime) -> str:
    return f"{ts.astimezone(TZ):%I:%M %p}".lstrip("0").lower()


def _response(m: dict[str, Any]) -> dict[str, Any] | None:
    """The sensor's reading after the meal (meal_response). None when there is no sensor data for it at all; otherwise each value,
    and a value that is not known stays None."""
    vals = [m["pre_glucose_mmol"], m["peak_glucose_mmol"], m["minutes_to_peak"], m["rise_mmol"]]
    if all(v is None for v in vals):
        return None
    return {
        "pre_mmol": _num(m["pre_glucose_mmol"]),
        "peak_mmol": _num(m["peak_glucose_mmol"]),
        "minutes_to_peak": None if m["minutes_to_peak"] is None else int(m["minutes_to_peak"]),
        "rise_mmol": _num(m["rise_mmol"]),
    }


def meal_kcal(m: dict[str, Any]) -> tuple[int | None, str]:
    """(kcal, numbers_from). A kcal the person typed (their Bronze payload, read as `typed_kcal`, when they entered the numbers) wins
    over the 4, 4 and 9 rule; otherwise the rule, which is None unless carbs, protein and fat are all known."""
    own = m.get("estimated_by") == "user"
    if own and m.get("typed_kcal") is not None:
        return round(float(m["typed_kcal"])), "you"
    return D.kcal(m["carbs_g"], m["protein_g"], m["fat_g"]), ("you" if own else "estimate")


def meal_detail(m: dict[str, Any]) -> dict[str, Any]:
    """One meal with its macros (unknown stays None, never 0), the salt and sugar flags, and the sensor response. The same kcal
    and flag rules as the Day view and the calendar."""
    kcal, source = meal_kcal(m)
    return {
        "id": str(m["id"]),
        "when": _clock(m["start_at"]),
        "name": m["food"] or None,
        "meal_type": m["meal_type"],
        "kcal": kcal,
        "numbers_from": source,
        "carbs_g": _num(m["carbs_g"]), "protein_g": _num(m["protein_g"]), "fat_g": _num(m["fat_g"]),
        "sugar_g": _num(m["sugar_g"]), "fibre_g": _num(m["fibre_g"]), "sodium_mg": _num(m["sodium_mg"], 0),
        "flags": D.meal_flags(m["sodium_mg"], m["sugar_g"]),
        "response": _response(m),
    }


def meal_details(ids: list[str]) -> dict[str, dict[str, Any]]:
    """The meals with these food_logs ids (the current user's, not deleted), keyed by id. Read only."""
    if not ids:
        return {}
    with tx() as c:
        rows = c.execute(
            """select f.id, f.start_at, f.food, f.meal_type::text meal_type, f.carbs_g, f.protein_g, f.fat_g, f.sugar_g, f.fibre_g, f.sodium_mg,
                      f.estimated_by::text estimated_by, b.payload->>'kcal' typed_kcal,
                      mr.pre_glucose_mmol, mr.peak_glucose_mmol, mr.minutes_to_peak, mr.rise_mmol
               from food_logs f left join meal_response mr on mr.food_log_id = f.id
                    left join bronze_food b on b.id = f.bronze_id
               where f.user_id=%s and f.deleted_at is null and f.id = any(%s::uuid[])""",
            (current_user(), ids),
        ).fetchall()
    return {str(r["id"]): meal_detail(r) for r in rows}


def summarise_days(rows: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    """One entry per day from `start` to `end`, inclusive. `rows` are meal rows with keys: id, day, start_at, meal_type, food and
    carbs_g, protein_g, fat_g, sugar_g, fibre_g, sodium_mg. Days with no meals are kept, with meals 0 and every total None."""
    by_day: dict[date, list[dict[str, Any]]] = {}
    for r in rows:
        by_day.setdefault(r["local_day"], []).append(r)
    out = []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        meals = sorted(by_day.get(d, []), key=lambda m: m["start_at"])
        totals = {k: _total([m[f"{k}_g" if k != "sodium" else "sodium_mg"] for m in meals], 0 if k == "sodium" else 1) for k in MACROS}
        kcal_day = _total([meal_kcal(m)[0] for m in meals], 0) if meals else None
        out.append({
            "date": d.isoformat(),
            "meals": len(meals),
            "totals": {
                "kcal": None if kcal_day is None else int(kcal_day),
                "carbs_g": totals["carbs"], "protein_g": totals["protein"], "fat_g": totals["fat"],
                "sugar_g": totals["sugar"], "fibre_g": totals["fibre"], "sodium_mg": totals["sodium"],
            },
            "meal_list": [{
                "id": str(m["id"]),
                "when": f"{m['start_at'].astimezone(TZ):%I:%M %p}".lstrip("0").lower(),
                "name": m["food"] or None,
                "meal_type": m["meal_type"],
                "kcal": meal_kcal(m)[0],
                "numbers_from": meal_kcal(m)[1],
                "carbs_g": _num(m["carbs_g"]), "protein_g": _num(m["protein_g"]), "fat_g": _num(m["fat_g"]),
                "sugar_g": _num(m["sugar_g"]), "fibre_g": _num(m["fibre_g"]), "sodium_mg": _num(m["sodium_mg"], 0),
            } for m in meals],
        })
    return out


def progress_days(start: date, end: date) -> dict[str, Any]:
    """The meals and macro totals for the current user, one entry per Singapore day from `start` to `end`."""
    if end < start or (end - start).days + 1 > MAX_RANGE_DAYS:
        raise ValueError(f"Choose a range of up to {MAX_RANGE_DAYS} days.")
    lo = datetime.combine(start, datetime.min.time(), TZ)
    hi = datetime.combine(end + timedelta(days=1), datetime.min.time(), TZ)
    with tx() as c:
        rows = c.execute(
            f"""select f.id, f.start_at, f.food, f.meal_type::text meal_type, f.carbs_g, f.protein_g, f.fat_g, f.sugar_g, f.fibre_g, f.sodium_mg,
                       f.estimated_by::text estimated_by, b.payload->>'kcal' typed_kcal,
                       {D.SG_DATE % 'f.start_at'} as local_day
                from food_logs f
                     left join bronze_food b on b.id = f.bronze_id
                where f.user_id=%s and f.deleted_at is null and f.start_at >= %s and f.start_at < %s
                order by f.start_at""",
            (current_user(), lo, hi),
        ).fetchall()
    return {"start": start.isoformat(), "end": end.isoformat(), "today": datetime.now(TZ).date().isoformat(), "days": summarise_days(rows, start, end)}
