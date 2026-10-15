"""What Equinox has learned (PRD F16): list, confirm, edit and delete facts; the weekly digest; the progress view.

Every action by the person is written to the append-only `event_log` (actor `user`). Editing never overwrites: it creates a new
version that supersedes the old one. Deleting marks the fact `rejected`, and a rejected fact is never proposed again with the same
value (adherence._propose_fact). The agent can only propose; this module is where a person turns a proposal into knowledge.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from app.agents import adherence
from app.agents.trace import audit
from app.db.logstore import TZ, current_user, is_read_only, tx
from app.services.day import kcal as kcal_of

TABLE_LABEL = {"medication_log": "your dose log", "food_logs": "your meal log", "exercise_logs": "your workouts", "symptom_logs": "your symptoms",
               "wellbeing_logs": "your check-ins", "notifications": "your reminders"}
CATEGORY_LABEL = {"routine": "Your routines", "barrier": "What gets in the way", "preference": "What you like", "food_response": "How food affects you",
                  "goal": "Your goals", "context": "Other things"}
# Ideas that are not shown on the screen. "Some missed doses were because of running out" was proposed from scripted miss reasons in
# Mr Tan's data (see the flags in the G2 report) and is hidden until the rule in agents/adherence.py is fixed. Rows are not deleted.
HIDDEN_FACT_KEYS = ("barrier.ran_out",)    # hidden for the scripted demo patient only: see hidden_keys()


def hidden_keys(user_id: Any) -> list[str]:
    """The fact keys not shown for this person. The "ran out" idea came from Mr Tan's scripted miss reasons, so it is hidden for him
    only; for anybody else it comes from their own dose log and is shown like any other idea."""
    return list(HIDDEN_FACT_KEYS) if is_read_only(user_id) else []


def _why(refs: Any) -> str:
    """'Why I think this', in plain words, from the evidence references."""
    parts = []
    for r in refs or []:
        t = TABLE_LABEL.get(r.get("table"), r.get("table") or "your records")
        if r.get("meals"):
            parts.append(f"{r['meals']} meals in the last {r.get('window_days', 14)} days ({t})")
        elif r.get("n"):
            parts.append(f"{r['n']} entries in {t}")
        else:
            parts.append(t)
    return "Based on " + "; ".join(parts) + "." if parts else "Based on your records."


def list_facts(user: Any = None) -> dict[str, Any]:
    """The facts the agent proposed or the person confirmed. For the signed-in person unless `user` is given (the shared doctor link reads the owner's)."""
    uid = user if user is not None else current_user()
    with tx() as c:
        rows = c.execute(
            """select id, key, category::text cat, statement, confidence, status::text st, version, evidence_refs, user_confirmed_at, source, updated_at
               from memory_facts where user_id=%s and status in ('proposed','active') and key <> all(%s) order by category, confidence desc""",
            (uid, hidden_keys(uid)),
        ).fetchall()
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r["cat"], []).append({
            "id": str(r["id"]), "key": r["key"], "statement": r["statement"] or r["key"], "confidence": round(float(r["confidence"]), 2),
            "status": r["st"], "version": r["version"], "why": _why(r["evidence_refs"]), "confirmed": r["user_confirmed_at"] is not None,
            "source": r["source"], "updatedAt": r["updated_at"].astimezone(TZ).isoformat(),
        })
    return {"groups": [{"category": k, "label": CATEGORY_LABEL.get(k, k), "facts": v} for k, v in groups.items()], "total": len(rows),
            "toConfirm": sum(1 for r in rows if r["st"] == "proposed")}


class NotFound(Exception):
    pass


def act(fact_id: str, action: str, text: str | None = None) -> dict[str, Any]:
    uid = current_user()
    fid = uuid.UUID(fact_id)
    with tx() as c:
        f = c.execute("select * from memory_facts where id=%s and user_id=%s and status in ('proposed','active')", (fid, uid)).fetchone()
        if not f:
            raise NotFound(fact_id)
        if action == "confirm":
            c.execute("update memory_facts set status='active', user_confirmed_at=now(), updated_at=now() where id=%s", (fid,))
            new_id = fid
        elif action == "delete":
            c.execute("update memory_facts set status='rejected', updated_at=now() where id=%s", (fid,))
            new_id = fid
        elif action == "edit":
            t = (text or "").strip()
            if not (3 <= len(t) <= 300):
                raise ValueError("The text must be between 3 and 300 characters.")
            c.execute("update memory_facts set status='superseded', updated_at=now() where id=%s", (fid,))
            value = dict(f["value"] or {})
            value["edited_by_user"] = True
            new_id = c.execute(
                """insert into memory_facts (user_id, key, category, value, statement_key, statement, confidence, evidence_status, evidence_refs, status, version,
                                             supersedes_id, source, user_confirmed_at, last_evidence_at)
                   values (%s,%s,%s,%s::jsonb,%s,%s,1.0,'observed'::evidence_status,%s::jsonb,'active'::fact_status,%s,%s,'user',now(),now()) returning id""",
                (uid, f["key"], f["category"], json.dumps(value), f["statement_key"], t, json.dumps(f["evidence_refs"]), f["version"] + 1, fid),
            ).fetchone()["id"]
        else:
            raise ValueError("Unknown action.")
    audit(uid, "user", f"memory.{action}", "memory_facts", new_id, {"key": f["key"], "from_status": f["status"]})
    return {"id": str(new_id), "action": action}


def digest(days: int = 7) -> dict[str, Any]:
    """What the agent did for this person over the last `days`, in plain counts and lines, with the facts the person can still veto."""
    uid = current_user()
    since = f"now() - interval '{int(days)} days'"
    with tx() as c:
        new = c.execute(f"select id, statement, status::text st, key from memory_facts where user_id=%s and created_at > {since} order by created_at desc", (uid,)).fetchall()
        pol = c.execute("select arm_kind, arm_key, tries, acts from nudge_policy where user_id=%s order by acts desc, tries desc limit 12", (uid,)).fetchall()
        names = {str(r["id"]): r["name"] for r in c.execute("select id, name from foods where id::text = any(%s)", ([k.split(":", 1)[1] for k in (p["arm_key"] for p in pol) if ":" in k and k.split(":")[0] in ("db", "swap")],)).fetchall()}
        n = c.execute(
            f"""select count(*) sent, count(*) filter (where opened_at is not null) opened, count(*) filter (where acted_at is not null) acted
                from notifications where user_id=%s and scheduled_for > {since}""", (uid,)).fetchone()
        g = c.execute(f"select count(*) total, count(*) filter (where verdict='pass') passed from guardrail_events where user_id=%s and created_at > {since}", (uid,)).fetchone()
        runs = c.execute(f"select trigger, count(*) n from agent_runs where user_id=%s and started_at > {since} group by 1", (uid,)).fetchall()
        sug = c.execute("select coalesce(sum(tries),0) tries, coalesce(sum(acts),0) acts from nudge_policy where user_id=%s and arm_kind='suggestion'", (uid,)).fetchone()
    def label(p: dict) -> str:
        k = p["arm_key"]
        if ":" in k and k.split(":")[0] in ("db", "swap"):
            return names.get(k.split(":", 1)[1], "a suggestion")
        return k.split(":", 1)[1] if k.startswith("own:") else k.replace("_", " ")
    lines = []
    for r in new[:6]:
        lines.append({"kind": "fact", "id": str(r["id"]), "text": r["statement"] or r["key"], "status": r["st"]})
    return {
        "days": days, "newFacts": len(new), "lines": lines,
        "reminders": {"sent": n["sent"], "opened": n["opened"], "acted": n["acted"]},
        "suggestions": {"shown": int(sug["tries"]), "chosen": int(sug["acts"])},
        "topSuggestions": [{"name": label(p), "kind": p["arm_kind"], "shown": p["tries"], "chosen": p["acts"]} for p in pol[:3]],
        "guard": {"checked": g["total"], "passed": g["passed"], "blocked": g["total"] - g["passed"]},
        "agentRuns": {r["trigger"]: r["n"] for r in runs},
    }


def audit_trail(limit: int = 15) -> list[dict[str, Any]]:
    """The agent's recent runs with their steps: what was routed where, and how long it took."""
    with tx() as c:
        runs = c.execute("select id, agent, trigger, status, latency_ms, started_at from agent_runs where user_id=%s order by started_at desc limit %s", (current_user(), limit)).fetchall()
        steps = c.execute("select agent_run_id, seq, node, tool, latency_ms, output from agent_steps where agent_run_id = any(%s) order by seq", ([r["id"] for r in runs],)).fetchall()
    by: dict[Any, list] = {}
    for s in steps:
        by.setdefault(s["agent_run_id"], []).append({"seq": s["seq"], "node": s["node"], "tool": s["tool"], "ms": s["latency_ms"], "output": s["output"]})
    return [{"id": str(r["id"]), "trigger": r["trigger"], "status": r["status"], "ms": r["latency_ms"], "at": r["started_at"].astimezone(TZ).isoformat(), "steps": by.get(r["id"], [])} for r in runs]


def progress() -> dict[str, Any]:
    """Week by week: what the person logged and how it moved, and the first two weeks against the latest two. What the person did,
    not proof that the app changed it."""
    uid = current_user()
    with tx() as c:
        meals = c.execute(
            """select date_trunc('week', start_at at time zone 'Asia/Singapore')::date wk, count(*) n, avg(carbs_g) carbs, avg(protein_g) protein, avg(fat_g) fat, avg(sodium_mg) sodium
               from food_logs where user_id=%s and deleted_at is null group by 1 order by 1""", (uid,)).fetchall()
    on_time = {w["week_start"]: w for w in adherence.on_time_by_week(uid)}
    weeks = []
    for m in meals:
        kcal = kcal_of(m["carbs"], m["protein"], m["fat"])
        ot = on_time.get(m["wk"])
        weeks.append({"weekStart": m["wk"].isoformat(), "meals": int(m["n"]), "avgKcal": kcal, "avgSodium": round(float(m["sodium"])) if m["sodium"] is not None else None,
                      "doses": ot["doses"] if ot else None, "onTimePct": ot["on_time_pct"] if ot else None})
    full = [w for w in weeks if w["meals"] >= 5]
    return {"weeks": weeks, "fullWeeks": len(full), "baseline": baseline(full), "compare": compare(full),
            "note": "This shows what the person logged and did, week by week. It does not show that the app caused any change."}


def _avg(rows: list[dict], k: str) -> float | None:
    v = [r[k] for r in rows if r[k] is not None]
    return round(sum(v) / len(v), 1) if v else None


def baseline(full: list[dict]) -> dict[str, Any] | None:
    """Pure: the starting point, the first two full weeks (5 or more meals each). None until there are two such weeks."""
    if len(full) < 2:
        return None
    first = full[:2]
    doses = [w["doses"] for w in first if w["doses"] is not None]
    return {"weeks": [w["weekStart"] for w in first], "meals": sum(w["meals"] for w in first), "doses": sum(doses) if doses else None,
            "avgKcal": _avg(first, "avgKcal"), "avgSodium": _avg(first, "avgSodium"), "onTimePct": _avg(first, "onTimePct")}


def compare(full: list[dict]) -> dict[str, Any] | None:
    """The first two full weeks against the latest two (kept in the response for older clients; the screen shows the baseline only)."""
    if len(full) < 4:
        return None
    first, last = full[:2], full[-2:]
    out: dict[str, Any] = {k: {"first": _avg(first, k), "latest": _avg(last, k)} for k in ("avgKcal", "avgSodium", "onTimePct")}
    out["firstWeeks"] = [w["weekStart"] for w in first]
    out["latestWeeks"] = [w["weekStart"] for w in last]
    return out
