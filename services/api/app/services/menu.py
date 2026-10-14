"""The Meal suggestions menu (docs/specs/menu.md): dishes for one meal, in three sections, each with a picture slot.

Sections, in this order:
  own      the person's OWN meals of this kind with a lower measured glucose rise than their typical meal (needs 2 times eaten)
  swap     a lighter dish for a food habit the memory loop noticed (from the Singapore food database, compared with the person's own numbers)
  general  database dishes that suit a steady day, shown only to fill the menu: clearly general, not personal

Numbers are computed here, in code. A glucose rise is MEASURED only for the person's own meals. For the other dishes it is an ESTIMATE worked out
from the dish's carbohydrate and the person's own typical rise per gram of carbohydrate; with no such history there is no number at all (never a guess).
The cut-offs for the tags (lower salt, lower carbs) are placeholders pending the clinical owner. Everything the person is shown is also stored in
`food_suggestions`, and every dish gets a `food_images` row so its picture is made once (app/services/food_images.py).
"""
from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime
from typing import Any

from app.agents import food as foodagent
from app.db import nutritionstore as ns
from app.db.logstore import TZ, tx
from app.services import food_images, texts

logger = logging.getLogger(__name__)

MEALS = ("breakfast", "lunch", "dinner", "snack")
PER_SECTION = 3
LOW_SALT_MG = 700          # placeholder: at or below this a dish is tagged "lower salt"
LOW_CARB_G = 45            # placeholder: at or below this a dish is tagged "lower carbs"
_DEFAULT_TIME = {"breakfast": 7 * 60 + 30, "lunch": 12 * 60 + 15, "dinner": 18 * 60 + 30, "snack": 16 * 60}

_SHELF = {
    "lunch": "subgroup in ('Rice-based dishes', 'Noodle/Pasta-based dishes', 'Soup-based dishes') and kcal between 350 and 600 and carbs_g <= 60 and sodium_mg <= 900 and protein_g >= 15",
    "dinner": ("subgroup in ('Rice-based dishes', 'Noodle/Pasta-based dishes', 'Soup-based dishes') and kcal between 300 and 550 and carbs_g <= 60 and sodium_mg <= 900 and protein_g >= 15"
               " and name not ilike '%%breakfast%%' and name not ilike '%%porridge%%' and name not ilike '%%congee%%' and name not ilike '%%cereal%%' and name not ilike '%%oat%%'"),
    "breakfast": "name ilike any (array['%%toast%%','%%egg%%','%%porridge%%','%%oat%%','%%congee%%','%%yoghurt%%','%%cereal%%']) and kcal between 120 and 450 and carbs_g <= 55 and sodium_mg <= 900",
    "snack": "subgroup in ('Fresh fruit', 'Nuts and seeds', 'Local ethnic snacks') and kcal <= 250 and sodium_mg <= 300",
}
_COMMON = "name not ilike '%%raw%%' and sodium_mg is not null and carbs_g is not null and kcal is not null"


def tags_for(carbs: float | None, sodium: float | None, hawker: bool | None) -> list[str]:
    """Filter tags. `hawker` is True/False for database dishes and None for the person's own meals (unknown: no hawker or home tag)."""
    t: list[str] = []
    if sodium is not None and sodium <= LOW_SALT_MG:
        t.append("lowSalt")
    if carbs is not None and carbs <= LOW_CARB_G:
        t.append("lowCarb")
    if hawker is True:
        t.append("hawker")
    elif hawker is False:
        t.append("home")
    return t


def estimate_rise(carbs: float | None, slope: float | None) -> tuple[float, float] | None:
    """Estimated rise range (mmol/L) from the dish's carbohydrate and the person's own typical rise per gram. None when either is missing."""
    if carbs is None or slope is None or carbs <= 0:
        return None
    mid = carbs * slope
    return (max(0.0, round(mid - 0.5, 1)), round(mid + 0.5, 1))


def typical_time(user_id: Any, meal: str) -> int:
    """Minutes since midnight: the median time this person logs this meal (last 20, needs 5), otherwise a default."""
    with tx() as c:
        rows = c.execute(
            """select (extract(hour from start_at at time zone 'Asia/Singapore') * 60 + extract(minute from start_at at time zone 'Asia/Singapore'))::int m
               from food_logs where user_id=%s and meal_type=%s::meal_type and deleted_at is null order by start_at desc limit 20""",
            (user_id, meal),
        ).fetchall()
    mins = [r["m"] for r in rows]
    return int(statistics.median(mins)) if len(mins) >= 5 else _DEFAULT_TIME[meal]


def _clock(mins: int) -> str:
    h, m = divmod(mins % 1440, 60)
    return f"{(h % 12) or 12}:{m:02d} {'am' if h < 12 else 'pm'}"


def _slope(c: Any, user_id: Any) -> float | None:
    """The person's typical glucose rise per gram of carbohydrate (median over their own meals with 10 g of carbs or more), or None."""
    r = c.execute(
        """select percentile_cont(0.5) within group (order by m.rise_mmol / f.carbs_g) s
           from food_logs f join meal_response m on m.food_log_id = f.id
           where f.user_id=%s and f.deleted_at is null and f.carbs_g >= 10 and m.rise_mmol is not null""",
        (user_id,),
    ).fetchone()
    return float(r["s"]) if r and r["s"] is not None else None


def _own(c: Any, user_id: Any, meal: str, med: float | None) -> list[dict[str, Any]]:
    rows = c.execute(
        """select lower(f.food) key, min(f.food) food, count(*) n, avg(m.rise_mmol) rise, avg(f.carbs_g) carbs, avg(f.protein_g) protein, avg(f.fat_g) fat, avg(f.sodium_mg) sodium
           from food_logs f join meal_response m on m.food_log_id = f.id
           where f.user_id=%s and f.deleted_at is null and f.meal_type=%s::meal_type and f.start_at > now() - interval '60 days' and m.rise_mmol is not null
           group by 1 having count(*) >= 2 order by avg(m.rise_mmol)""",
        (user_id, meal),
    ).fetchall()
    out = []
    for r in rows:
        if med is None or float(r["rise"]) >= med:
            continue
        carbs, protein, fat = (float(r[k]) if r[k] is not None else None for k in ("carbs", "protein", "fat"))
        out.append({"key": f"own:{r['key']}", "name": r["food"], "section": "own", "why": f"After this {meal} your glucose rose {float(r['rise']):.1f} mmol/L on average (you had it {int(r['n'])} times), less than after your typical meal ({med:.1f}).", "serving": None, "kcal": foodagent.kcal_from({"carbs_g": carbs, "protein_g": protein, "fat_g": fat}),
                    "carbs": carbs, "sodium": float(r["sodium"]) if r["sodium"] is not None else None, "rise": round(float(r["rise"]), 1), "seen": int(r["n"]), "tags": tags_for(carbs, float(r["sodium"]) if r["sodium"] is not None else None, None),
                    "extra": {"typical": round(med, 1)}})
    return out[:PER_SECTION]


def _swap(user_id: Any, slope: float | None, lang: str) -> list[dict[str, Any]]:
    try:
        habits = ns.food_habits(user_id)
    except Exception:
        logger.exception("food habits unavailable; the menu goes on without the swap section")
        return []
    out: list[dict[str, Any]] = []
    for h in habits:
        for alt in h["alternatives"][:2]:
            with tx() as c:
                f = c.execute("select kcal, carbs_g, sodium_mg, 'hawker' = any(flags) hawker from foods where id=%s", (alt["foodId"],)).fetchone()
            carbs = float(f["carbs_g"]) if f and f["carbs_g"] is not None else next((c2["to"] for c2 in alt["changes"] if c2["nutrient"] == "carbs_g"), None)
            sodium = float(f["sodium_mg"]) if f and f["sodium_mg"] is not None else next((c2["to"] for c2 in alt["changes"] if c2["nutrient"] == "sodium_mg"), None)
            est = estimate_rise(carbs, slope)
            out.append({"key": f"swap:{alt['foodId']}", "name": alt["name"], "section": "swap", "why": texts.tr(lang, "lunch.why_swap", dish=h["topDish"], saving=ns.saving_phrase(alt, lang)),
                        "serving": alt.get("serving"), "kcal": round(float(f["kcal"])) if f and f["kcal"] is not None else None, "carbs": carbs, "sodium": sodium,
                        "rise": None, "est": est, "seen": None, "tags": tags_for(carbs, sodium, bool(f["hawker"]) if f else None), "extra": {"instead": h["topDish"]}})
    return out[:PER_SECTION]


def _general(c: Any, meal: str, slope: float | None, lang: str) -> list[dict[str, Any]]:
    rows = c.execute(
        f"select {foodagent._COLS}, 'hawker' = any(flags) hawker from foods where source=%s and {_COMMON} and {_SHELF[meal]} "
        "order by (sodium_mg / 900.0 + carbs_g / 60.0 - coalesce(fibre_g, 0) / 10.0) limit 24",
        (foodagent.SOURCE,),
    ).fetchall()
    out = []
    for r in rows:
        f = foodagent._row(r)
        carbs, sodium = f.n["carbs_g"], f.n["sodium_mg"]
        out.append({"key": f"db:{f.id}", "name": f.name, "section": "general", "why": texts.tr(lang, "lunch.why_general", carbs=round(carbs), salt=round(sodium)),
                    "serving": f.serving_desc, "kcal": round(f.n["kcal"]) if f.n["kcal"] is not None else None, "carbs": carbs, "sodium": sodium, "rise": None, "est": estimate_rise(carbs, slope),
                    "seen": None, "tags": tags_for(carbs, sodium, bool(r["hawker"])), "extra": {}})
    return out


def _usual(c: Any, user_id: Any, meal: str) -> dict[str, Any] | None:
    r = c.execute(
        """select min(f.food) food, count(*) n, avg(m.rise_mmol) rise, avg(f.carbs_g) carbs, avg(f.protein_g) protein, avg(f.fat_g) fat
           from food_logs f left join meal_response m on m.food_log_id = f.id
           where f.user_id=%s and f.deleted_at is null and f.meal_type=%s::meal_type and f.start_at > now() - interval '60 days'
           group by lower(f.food) order by count(*) desc limit 1""",
        (user_id, meal),
    ).fetchone()
    if not r:
        return None
    carbs, protein, fat = (float(r[k]) if r[k] is not None else None for k in ("carbs", "protein", "fat"))
    return {"name": r["food"], "kcal": foodagent.kcal_from({"carbs_g": carbs, "protein_g": protein, "fat_g": fat}), "rise": round(float(r["rise"]), 1) if r["rise"] is not None else None}


def build(user_id: Any, meal: str, *, store: bool = True) -> dict[str, Any]:
    """The menu for one meal. Reads the person's data, picks the dishes, makes sure each has a picture row, and stores what is shown."""
    if meal not in MEALS:
        raise ValueError("meal must be breakfast, lunch, dinner or snack")
    lang = texts.person_language(user_id)
    with tx() as c:
        med = c.execute("select percentile_cont(0.5) within group (order by rise_mmol) m from meal_response where user_id=%s and rise_mmol is not null", (user_id,)).fetchone()["m"]
        med = float(med) if med is not None else None
        slope = _slope(c, user_id)
        own = _own(c, user_id, meal, med)
        general = _general(c, meal, slope, lang)
        usual = _usual(c, user_id, meal)
    swap = _swap(user_id, slope, lang) if meal in ("lunch", "dinner") else []
    gone = ns.excluded_keys(user_id)
    seen_names: set[str] = set()
    sections: dict[str, list[dict[str, Any]]] = {"own": [], "swap": [], "general": []}
    for it in own + swap + general:
        if it["key"] in gone or it["name"].lower() in seen_names:
            continue
        if len(sections[it["section"]]) >= PER_SECTION:
            continue
        seen_names.add(it["name"].lower())
        it["dishKey"] = food_images.dish_key(it["name"])
        it["meal"] = meal
        sections[it["section"]].append(it)
    flat = [it for s in sections.values() for it in s]
    pics = food_images.ensure_rows([(it["dishKey"], it["name"]) for it in flat])
    for it in flat:
        status = pics.get(it["dishKey"], {}).get("status", "pending")
        it["image"] = {"status": status, "url": f"/nutrition/food-image/{it['dishKey']}" if status == "ready" else None}
        est = it.pop("est", None)
        it["riseKind"] = "measured" if it["rise"] is not None else ("estimate" if est else "none")
        it["riseLow"], it["riseHigh"] = (est if est else (None, None))
    if store:
        _store(user_id, meal, flat)
    pending = sum(1 for it in flat if it["image"]["status"] != "ready")
    return {"meal": meal, "time": _clock(typical_time(user_id, meal)), "sections": [{"key": k, "items": v} for k, v in sections.items()], "usual": usual, "picturesWaiting": pending}


def build_all(user_id: Any, *, store: bool = True) -> dict[str, Any]:
    """Every dish for every meal, in the same three sections (each dish says which meal it is for). The time shown is the current meal's."""
    merged: dict[str, list[dict[str, Any]]] = {"own": [], "swap": [], "general": []}
    waiting, usual = 0, None
    seen: set[str] = set()
    for m in MEALS:
        one = build(user_id, m, store=store)
        waiting += one["picturesWaiting"]
        for sec in one["sections"]:
            for it in sec["items"]:
                if it["name"].lower() in seen:         # the same dish can suit two meals: show it once
                    continue
                seen.add(it["name"].lower())
                merged[sec["key"]].append(it)
    return {"meal": "all", "time": None, "sections": [{"key": k, "items": v} for k, v in merged.items()], "usual": usual, "picturesWaiting": waiting}


def _store(user_id: Any, meal: str, items: list[dict[str, Any]]) -> None:
    day = datetime.now(TZ).date()
    with tx() as c:
        for it in items:
            payload = {k: it[k] for k in ("why", "serving", "kcal", "carbs", "sodium", "rise", "riseLow", "riseHigh", "riseKind", "seen", "tags", "extra")}
            c.execute(
                """insert into food_suggestions (user_id, day, meal, suggestion_key, section, dish_key, name, payload)
                   values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                   on conflict (user_id, day, meal, suggestion_key) do update set payload = excluded.payload, section = excluded.section""",
                (user_id, day, meal, it["key"], it["section"], it["dishKey"], it["name"], json.dumps(payload)),
            )


def mark_picked(user_id: Any, meal: str, key: str) -> None:
    """The person added this dish to their picks: stamp it, and count it as acted on for the learning policy."""
    day = datetime.now(TZ).date()
    with tx() as c:
        c.execute("update food_suggestions set picked_at = now() where user_id=%s and day=%s and meal=%s and suggestion_key=%s and picked_at is null", (user_id, day, meal, key))
    ns.policy_act(user_id, "suggestion", key)
