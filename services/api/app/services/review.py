"""The reviewer screen (K11): the suggestions the app made, and the ratings a reviewer gave them.

A suggestion is a lighter dish from the food database (app/agents/food.py `better_alternatives`) for one of the person's own most-logged
dishes, compared with that person's own logged numbers. Suggestions are computed each time and never stored. Only ratings are written,
as append-only `event_log` rows (event `review.rated`); the latest rating for a suggestion wins.

Target (docs/specs/learning-loop.md 12.6): at least 85% of suggestions judged reasonable, and no unsafe verdict. Fewer than 20 ratings
gives no result. The score rates the suggestion and the swap, never the person, and the target is a placeholder pending review.
It will not write to the person's record or change any suggestion.
"""
from __future__ import annotations

import hashlib
import time
import json
from typing import Any, Callable, Iterable

from app.agents import food
from app.services import texts
from app.db import nutritionstore as ns

RATED_EVENT = "review.rated"
VERDICTS = ("reasonable", "not_reasonable", "unsafe")
TARGET_PERCENT = 85                     # the share is compared in whole percent, so exactly 85% passes
MIN_RATINGS = 20                        # below this the share means little, so no result is given
COMMENT_MAX = 300
MIN_TIMES_LOGGED = 2                    # a dish eaten once is not a habit to offer a swap for
MAX_DISHES_SCANNED = 12                 # each dish costs a search and a model check, so the queue scans at most this many
SAMPLE_SCAN = 30                        # sample dishes looked at, in a stable order, when "mine" is empty
ALT_PER_DISH = 3


# ───────────────────────────────────────────────────────────────── pure rules
def suggestion_key(usual: str, suggested: str) -> str:
    """A stable key for one suggestion: the usual dish and the dish offered instead, normalised so case and spacing do not matter."""
    raw = f"{food.normalise(usual)}|{food.normalise(suggested)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def check_rating(verdict: str, comment: str | None) -> tuple[str, str | None]:
    """Refuses an unknown verdict, a comment over the limit, and an unsafe verdict with no comment saying why."""
    if verdict not in VERDICTS:
        raise ValueError("Choose reasonable, not reasonable or unsafe.")
    text = (comment or "").strip() or None
    if text and len(text) > COMMENT_MAX:
        raise ValueError(f"The comment can be at most {COMMENT_MAX} characters.")
    if verdict == "unsafe" and text is None:
        raise ValueError("Say what makes this unsafe in the comment box.")
    return verdict, text


def latest_ratings(events: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Events oldest first. The last rating for each suggestion wins; anything malformed is skipped, not guessed at."""
    out: dict[str, dict[str, Any]] = {}
    for e in events:
        p = e.get("payload") or {}
        key, verdict = p.get("suggestionKey"), p.get("verdict")
        if isinstance(key, str) and verdict in VERDICTS:
            out[key] = {"verdict": verdict, "comment": p.get("comment") or None}
    return out


def score(ratings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Counts per verdict, the share judged reasonable, and the status against the target. Integer arithmetic for the comparison."""
    counts = {v: 0 for v in VERDICTS}
    for r in ratings.values():
        counts[r["verdict"]] += 1
    rated = len(ratings)
    reasonable, unsafe = counts["reasonable"], counts["unsafe"]
    if rated < MIN_RATINGS:
        status = "too_few"
    elif reasonable * 100 >= TARGET_PERCENT * rated and unsafe == 0:
        status = "met"
    else:
        status = "not_met"
    return {
        "counts": {"reasonable": reasonable, "not_reasonable": counts["not_reasonable"], "unsafe": unsafe},
        "rated": rated,
        "reasonable_share": round(reasonable / rated, 3) if rated else None,
        "target": TARGET_PERCENT / 100,
        "min_ratings": MIN_RATINGS,
        "unsafe": unsafe,
        "status": status,
    }


def _usual(d: dict[str, Any]) -> dict[str, Any]:
    b = d["base"]
    return {
        "name": d["name"], "times_logged": d["times"], "kcal": b.get("kcal"), "protein_g": b.get("protein_g"), "carbs_g": b.get("carbs_g"),
        "fat_g": b.get("fat_g"), "sugar_g": b.get("sugar_g"), "sodium_mg": b.get("sodium_mg"),
    }


def _item(d: dict[str, Any], alt: dict[str, Any], key: str, change: str, rating: dict[str, Any] | None) -> dict[str, Any]:
    to = {c["nutrient"]: c["to"] for c in alt["changes"]}
    return {
        "suggestion_key": key,
        "usual": _usual(d),
        "suggested": {
            "name": alt["name"], "serving": alt.get("serving"), "kcal": to.get("kcal"), "protein_g": to.get("protein_g"), "carbs_g": to.get("carbs_g"),
            "fat_g": to.get("fat_g"), "sugar_g": to.get("sugar_g"), "sodium_mg": to.get("sodium_mg"),
        },
        "change": change,
        "my_rating": rating,
    }


# Finding lighter dishes searches the food shelf and asks JEV per dish (about 5 seconds each), so the answer is kept for a while. It depends only on the
# dish and its numbers, never on who is asking or their ratings; the ratings are added after. A restart empties it and the scheduler warms it again.
_CACHE: dict[tuple, tuple[float, list[dict[str, Any]]]] = {}
CACHE_SECONDS = 6 * 3600


def cached_suggest(name: str, base: dict[str, Any], limit: int = 3, **kw: Any) -> list[dict[str, Any]]:
    key = (name, tuple(sorted((k, None if v is None else round(float(v), 1)) for k, v in base.items())), limit)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    found = food.better_alternatives(name, base, limit=limit, **kw)
    _CACHE[key] = (time.time(), found)
    return found


def build_queue(dishes: list[dict[str, Any]], rated: dict[str, dict[str, Any]], limit: int,
                suggest: Callable[..., list[dict[str, Any]]] = cached_suggest,
                phrase: Callable[[dict[str, Any]], str] = ns.saving_phrase) -> list[dict[str, Any]]:
    """Walk the dishes in order and collect up to `limit` suggestions, each with this reviewer's latest rating if there is one."""
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for d in dishes:
        if len(items) >= limit:
            break
        for alt in suggest(d["name"], d["base"], limit=ALT_PER_DISH):
            key = suggestion_key(d["name"], alt["name"])
            if key in seen:
                continue
            seen.add(key)
            items.append(_item(d, alt, key, phrase(alt), rated.get(key)))
            if len(items) >= limit:
                break
    return items


def queue_message(source: str, dishes: list[dict[str, Any]], items: list[dict[str, Any]], limit: int) -> str | None:
    """A plain reason when the queue is empty or short. None when it is full enough."""
    if items and len(items) >= limit:
        return None
    if source == "sample":
        return texts.tr(texts.request_lang(), "review.msg.sample_none") if not items else None
    if not dishes:
        return texts.tr(texts.request_lang(), "review.msg.no_dishes", n=MIN_TIMES_LOGGED)
    if not items:
        return texts.tr(texts.request_lang(), "review.msg.no_swaps")
    return None


# ───────────────────────────────────────────────────────────────── loads (SQL, small)
def logged_dishes(conn, user: str) -> list[dict[str, Any]]:
    """The person's most-logged dishes that have a logged baseline, with the same averages the review sheet uses."""
    rows = conn.execute(
        """select min(food) food, count(*) n, avg(carbs_g) carbs_g, avg(protein_g) protein_g, avg(fat_g) fat_g, avg(sugar_g) sugar_g,
                  avg(fibre_g) fibre_g, avg(sodium_mg) sodium_mg
           from food_logs where user_id=%s and deleted_at is null and carbs_g is not null and protein_g is not null and fat_g is not null
           group by lower(food) having count(*) >= %s order by count(*) desc, min(food) limit %s""",
        (user, MIN_TIMES_LOGGED, MAX_DISHES_SCANNED),
    ).fetchall()
    return [{"name": r["food"], "times": int(r["n"]), "base": ns._logged_baseline([r])} for r in rows]


def sample_dishes(conn) -> list[dict[str, Any]]:
    """Typical high-load hawker dishes, treated at their published serving (as the review sheet does). Shared by everyone, same order."""
    rows = conn.execute(
        f"select {food._COLS} from foods where source=%s and 'hawker' = any(flags) "
        "and category in ('Grains and staples','Mixed','Poultry','Snacks') "
        "and (kcal >= 550 or sodium_mg >= 1200) and carbs_g is not null and protein_g is not null and fat_g is not null "
        "order by md5(name) limit %s",
        (food.SOURCE, SAMPLE_SCAN),
    ).fetchall()
    out = []
    for r in rows:
        f = food._row(r)
        base: dict[str, Any] = {k: f.n.get(k) for k in ("carbs_g", "protein_g", "fat_g", "sugar_g", "fibre_g", "sodium_mg")}
        base["kcal"] = food.kcal_from(base)
        out.append({"name": f.name, "times": None, "base": base})
    return out


def load_ratings(conn, user: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute("select payload from event_log where user_id=%s and event=%s order by id", (user, RATED_EVENT)).fetchall()
    return latest_ratings([{"payload": r["payload"]} for r in rows])


def record_rating(conn, user: str, key: str, verdict: str, comment: str | None) -> None:
    payload = json.dumps({"suggestionKey": key, "verdict": verdict, "comment": comment})
    conn.execute("insert into event_log (user_id, actor, event, payload) values (%s, 'user', %s, %s::jsonb)", (user, RATED_EVENT, payload))
