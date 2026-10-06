"""Nutrition agent, code side: spot a food habit and suggest lighter, similar dishes for the NEXT meal.

What this module does NOT do: it never matches a logged meal to the food database and never uses database numbers as the meal's
numbers. The calories and macros of a logged meal come from the photo model (Vertex AI) or from the person, and stay as logged.

What it does (docs/specs/learning-loop.md LL4):
  1. food type   JEV `choice` labels each distinct meal name (fried food, rice dish, noodle dish, ...), so "fried chicken" and
                 "fried chicken wings" count as the same habit
  2. habit       the memory loop (nutritionstore) counts meals per type over two weeks; a type eaten often and high in what the
                 person logged is a candidate to flag
  3. shelf       the Singapore food database is searched for dishes similar to the person's usual meal (text plus embedding search)
  4. better      each candidate is compared with the person's OWN logged average for that meal, in code: what it would save in
                 calories, salt, carbs, sugar, and what happens to protein and fibre
  5. relevance   JEV `noul` checks that a candidate is a reasonable substitute (same kind of meal, similar main ingredient)
The model writes no numbers. Wording is a template filled from these numbers.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.db.logstore import tx
from app.llm import jev
from app.services import usage

logger = logging.getLogger(__name__)

SOURCE = "sgfoodid_2026_07"
NUTRIENTS = ("kcal", "carbs_g", "sugar_g", "fibre_g", "protein_g", "fat_g", "sat_fat_g", "sodium_mg")

# JEV `choice` criteria for the type of a meal (used to group meals into habits)
FOOD_TYPES = {
    "fried_food": "Mainly deep-fried or very oily fried food, for example fried chicken, fritters, fried snacks, fried dumplings",
    "rice_dish": "A rice-based plate, for example chicken rice, nasi lemak, economy rice, claypot rice, fried rice",
    "noodle_dish": "A noodle or pasta dish, dry or in soup, for example laksa, mee goreng, char kway teow, wanton mee",
    "soup_or_porridge": "A soup or porridge as the main dish, for example fish soup, congee, yong tau foo soup",
    "bread_or_pastry": "Bread, toast, pastry, prata, cake or buns, for example kaya toast, roti prata",
    "sweet_drink_or_dessert": "A sweet drink or dessert, for example bubble tea, sweet kopi, ice kachang, cake, sweets",
    "vegetables_or_fruit": "Mostly vegetables, salad or fruit",
    "other": "Anything that does not fit the other types",
}
TYPE_LABEL = {"fried_food": "fried food", "rice_dish": "rice dishes", "noodle_dish": "noodle dishes", "soup_or_porridge": "soup or porridge",
              "bread_or_pastry": "bread or pastry", "sweet_drink_or_dessert": "sweet drinks or desserts", "vegetables_or_fruit": "vegetables or fruit", "other": "other food"}
_TYPE_CACHE: dict[str, str] = {}


def normalise(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", name.lower())).strip()


def classify_foods(names: list[str]) -> dict[str, str]:
    """Food type for each meal name. One JEV request for all new names; a name JEV cannot place with confidence is 'other'."""
    todo = [n for n in dict.fromkeys(normalise(x) for x in names) if n and n not in _TYPE_CACHE]
    for i in range(0, len(todo), 25):
        chunk = todo[i:i + 25]
        qs = {f"q{j}": (f"What type of meal is this: {n}?", FOOD_TYPES) for j, n in enumerate(chunk)}
        res = jev.choice_batch("A meal logged by a person with type 2 diabetes in Singapore.", qs)
        for j, n in enumerate(chunk):
            r = res.get(f"q{j}")
            _TYPE_CACHE[n] = r.choice if (r and r.confidence >= 0.5 and r.choice in FOOD_TYPES) else "other"
    return {normalise(n): _TYPE_CACHE.get(normalise(n), "other") for n in names}


def kcal_from(m: dict[str, float | None]) -> float | None:
    """Energy from logged macros (4 kcal per g of carbs and protein, 9 per g of fat): the same rule for the person and the shelf."""
    c, p, f = m.get("carbs_g"), m.get("protein_g"), m.get("fat_g")
    return None if c is None or p is None or f is None else round(4 * c + 4 * p + 9 * f)


# ----------------------------------------------------------------------------- the shelf: the food database, searched for similar dishes
@dataclass
class FoodRow:
    id: str
    name: str
    category: str | None
    subgroup: str | None
    serving_g: float | None
    serving_desc: str | None
    source_grade: str | None
    n: dict[str, float | None] = field(default_factory=dict)  # per serving, as published


def _row(r: dict) -> FoodRow:
    return FoodRow(
        id=str(r["id"]), name=r["name"], category=r.get("category"), subgroup=r.get("subgroup"),
        serving_g=float(r["serving_g"]) if r.get("serving_g") is not None else None, serving_desc=r.get("serving_desc"),
        source_grade=r.get("source_grade"), n={k: (float(r[k]) if r.get(k) is not None else None) for k in NUTRIENTS},
    )


_COLS = "id, name, category, subgroup, serving_g, serving_desc, source_grade, " + ", ".join(NUTRIENTS)


@lru_cache(maxsize=1)
def _embed_client():
    """One long-lived client: a client created inline is closed when it is garbage-collected, before the request is sent."""
    from google import genai

    for k in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ.pop(k, None)
    return genai.Client(vertexai=True, api_key=os.environ.get("GOOGLE_API_KEY", "") or settings.google_api_key)


@lru_cache(maxsize=512)
def _embed(text: str) -> tuple[float, ...] | None:
    if not usage.allowed("vertex_embed"):
        return None
    try:
        from google.genai import types

        r = _embed_client().models.embed_content(model="gemini-embedding-001", contents=[text], config=types.EmbedContentConfig(output_dimensionality=768))
        usage.record("vertex_embed", len(text.split()), 0)
        return tuple(r.embeddings[0].values)
    except Exception as e:
        logger.warning("embedding failed, using text similarity only: %s", str(e)[:120])
        return None


def similar_dishes(query: str, k: int = 15) -> list[FoodRow]:
    """Dishes in the database that read like `query`: text similarity and embedding similarity fused by reciprocal rank."""
    q = normalise(query)
    vec = _embed(q)
    with tx() as c:
        text = c.execute(
            f"select {_COLS}, similarity(lower(name), %s) sim from foods where source=%s and similarity(lower(name), %s) > 0.12 order by sim desc limit %s",
            (q, SOURCE, q, k),
        ).fetchall()
        emb = []
        if vec:
            lit = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
            emb = c.execute(
                f"select {_COLS} from foods where source=%s and embedding is not null order by embedding <=> %s::vector limit %s", (SOURCE, lit, k)
            ).fetchall()
    fused: dict[str, list] = {}
    for rank, r in enumerate(text):
        fused.setdefault(str(r["id"]), [r, 0.0])[1] += 1 / (60 + rank)
    for rank, r in enumerate(emb):
        fused.setdefault(str(r["id"]), [r, 0.0])[1] += 1 / (60 + rank)
    return [_row(r) for r, _ in sorted(fused.values(), key=lambda e: e[1], reverse=True)[:k]]


# ----------------------------------------------------------------------------- comparing with what the person actually logged
_LABEL = {"kcal": "calories", "sodium_mg": "salt (sodium)", "carbs_g": "carbs", "sugar_g": "sugar"}
# a change smaller than this is noise, not a worsening (a rise from 0.7 g to 1.5 g of sugar is not "100% worse")
_MIN_ABS = {"kcal": 80.0, "sodium_mg": 100.0, "carbs_g": 5.0, "sugar_g": 3.0}
_REPORT = ("kcal", "protein_g", "carbs_g", "fat_g", "sugar_g", "sodium_mg", "fibre_g")


def cand_nutrients(f: FoodRow) -> dict[str, float | None]:
    d = dict(f.n)
    d["kcal"] = kcal_from(d) if kcal_from(d) is not None else d.get("kcal")
    return d


def targets_for(baseline: dict[str, float | None]) -> list[str]:
    """What the person's usual meal is high in, by the logged numbers. A light meal gets no swap pushed at it."""
    t = []
    if (baseline.get("kcal") or 0) >= settings.swap_trigger_kcal:
        t.append("kcal")
    if (baseline.get("sodium_mg") or 0) >= settings.swap_trigger_sodium_mg:
        t.append("sodium_mg")
    if (baseline.get("carbs_g") or 0) >= settings.swap_trigger_carbs_g:
        t.append("carbs_g")
    if (baseline.get("sugar_g") or 0) >= settings.swap_trigger_sugar_g:
        t.append("sugar_g")
    return t


def evaluate_swap(baseline: dict[str, float | None], cand: dict[str, float | None], targets: list[str]) -> tuple[bool, float, float]:
    """Pure rule. Returns (acceptable, score, best improvement % on a target).

    Not acceptable if a target cannot be compared, if the candidate is not a meal-sized replacement (about half to the same energy), or if any compared nutrient is
    more than the allowed share worse by a meaningful absolute amount."""
    ok, score, best = True, 0.0, 0.0
    for k in ("kcal", "sodium_mg", "carbs_g", "sugar_g"):
        a, b = baseline.get(k), cand.get(k)
        if a is None or b is None or a <= 0:
            if k in targets:
                ok = False  # cannot prove the target improves
            continue
        change = (a - b) / a  # positive = lower than the usual meal
        if change < -settings.swap_max_worsening and (b - a) >= _MIN_ABS[k]:
            ok = False
        if k == "kcal" and not (a * settings.swap_kcal_min_ratio <= b <= a * settings.swap_kcal_max_ratio):
            ok = False  # a swap replaces the meal: not a side dish or a snack (too little energy), and not heavier
        if k in targets:
            score += change
            best = max(best, change * 100)
    return ok, score, best


def savings(baseline: dict[str, float | None], cand: dict[str, float | None]) -> list[dict[str, Any]]:
    """What changes if the person has the candidate instead, for every nutrient we can compare. Protein and fibre may go either way."""
    out = []
    for k in _REPORT:
        a, b = baseline.get(k), cand.get(k)
        if a is None or b is None:
            continue
        out.append({"nutrient": k, "from": round(a, 1), "to": round(b, 1), "change": round(b - a, 1)})
    return out


_NOISE = {"fried", "crispy", "deep", "battered", "with", "and", "fries", "chips", "set", "regular", "large", "small", "extra", "plate", "bowl", "of", "the", "a", "home"}
_LIGHTER_STYLES = ("steamed", "roasted", "grilled", "soup", "boiled")


def search_queries(name: str) -> list[str]:
    """What to look up on the shelf: the dish itself, then the same main ingredient cooked in lighter ways. Only a way to find
    candidates; every candidate is still compared in code and checked by JEV before it is offered."""
    main = " ".join(w for w in normalise(name).split() if w not in _NOISE)
    return [name] + ([f"{m} {main}" for m in _LIGHTER_STYLES] if main else [])


def better_alternatives(name: str, baseline: dict[str, float | None], limit: int = 3, extra_targets: set[str] | None = None) -> list[dict[str, Any]]:
    """Lighter, similar dishes to have next time instead of `name`, compared with the person's own logged numbers for it."""
    base = dict(baseline)
    base["kcal"] = kcal_from(base) if kcal_from(base) is not None else base.get("kcal")
    targets = sorted(set(targets_for(base)) | set(extra_targets or ()))
    if not targets:
        return []
    own = normalise(name)
    scored = []
    pool: dict[str, FoodRow] = {}
    for q in search_queries(name):
        for f in similar_dishes(q, 8):
            pool.setdefault(f.id, f)
    for f in pool.values():
        if normalise(f.name) == own:
            continue
        cand = cand_nutrients(f)
        ok, score, best = evaluate_swap(base, cand, targets)
        if ok and best >= settings.swap_min_improvement * 100:
            scored.append((score, f, cand))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:8]
    if not top:
        return []
    # JEV: is the candidate a reasonable substitute (same kind of meal, similar main ingredient)? Unsure or unavailable: leave it out.
    qs = {f"c{i}": f"Is the candidate a reasonable substitute for the usual meal: the same kind of meal with a similar main ingredient? Usual meal: {name}. Candidate: {f.name}." for i, (_, f, _) in enumerate(top)}
    rel = jev.noul_batch("A person with type 2 diabetes wants a lighter alternative for their next meal.", qs)
    out = []
    kept = [(score * rel[f"c{i}"], i, f, cand) for i, (score, f, cand) in enumerate(top) if rel.get(f"c{i}") is not None and rel[f"c{i}"] >= settings.jev_substitute_floor]
    kept.sort(key=lambda t: t[0], reverse=True)
    for _, i, f, cand in kept:
        p = rel[f"c{i}"]
        sv = savings(base, cand)
        out.append({
            "foodId": f.id, "name": f.name, "serving": f.serving_desc, "sourceGrade": f.source_grade, "fit": round(p, 2),
            "improves": [_LABEL[k] for k in targets if any(s["nutrient"] == k and s["change"] < 0 for s in sv)],
            "changes": sv, "for": name,
        })
        if len(out) >= limit:
            break
    return out
