"""The orchestrator: the main agent (docs/specs/learning-loop.md section 11).

A LangGraph graph with one routing node and one node per sub-agent. An event goes in, it is routed to exactly one sub-agent, the
sub-agent's code runs, and every step is logged to `agent_runs` and `agent_steps`. Routing is by rule for the events the app
raises itself; for free text from the person, JEV `choice` picks the skill, and below the confidence floor the message goes to no
skill (conservative path). Sub-agents propose and report; none of them activates a memory fact or edits a guard.

Event kinds:  tick (reminders), nightly (reflection), habit_scan (nutrition), dose_review (adherence), salt_check (activity),
              preventive_due (preventive), message (free text, routed by JEV)
"""
from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import adherence, hooks, preventive as preventive_agent
from app.agents.trace import Run, audit
from app.db import logstore, nutritionstore
from app.llm import jev
from app.services import usage

logger = logging.getLogger(__name__)

ROUTES = {"tick": "reminders", "nightly": "reflection", "habit_scan": "nutrition", "dose_review": "adherence", "salt_check": "activity", "preventive_due": "preventive"}
TRIGGER = {"tick": "tick", "nightly": "nightly", "message": "chat"}
SKILLS = {"adherence": "medicines, doses, reminders or missed tablets", "nutrition": "food, meals, eating or what to cook",
          "activity": "exercise, walking, movement or workouts", "preventive": "screenings, check-ups or vaccines", "none": "anything else"}
_RUN: ContextVar[Run | None] = ContextVar("agent_run", default=None)
_LAST_TICK: dict[str, str] = {}  # per person: what the last quiet tick reported, so an unchanged tick is not written to the audit trail


class State(TypedDict, total=False):
    event: dict[str, Any]
    route: str
    out: dict[str, Any]


def _run() -> Run:
    r = _RUN.get()
    assert r is not None
    return r


def _uid(state: State):
    return state["event"]["user_id"]


# ----------------------------------------------------------------------------- nodes
def route_node(state: State) -> State:
    ev = state["event"]
    run = _run()

    def decide() -> str:
        if ev["kind"] in ROUTES:
            return ROUTES[ev["kind"]]
        if ev["kind"] == "message":
            ch = jev.choice(ev.get("text") or "A person using a diabetes self-care app wrote a message.", "Which skill does this message need?", SKILLS)
            # the text itself is not stored here; JEV sees a de-identified copy and the route is all that is kept
            if ch is None or ch.confidence < 0.6 or ch.choice == "none":
                return "unrouted"
            return ch.choice
        return "unrouted"

    return {"route": run.step("route", "jev.choice" if ev["kind"] == "message" else "rules", {"kind": ev["kind"]}, decide)}


def _wrap(name: str, tool: str, fn):
    def node(state: State) -> State:
        ev = state["event"]
        return {"out": _run().step(name, tool, {"kind": ev["kind"], "write": ev.get("write", False)}, lambda: fn(state))}

    return node


def reminders(state: State) -> dict:
    items = logstore.notifications()
    return {"reminders": len(items), "unread": sum(1 for i in items if i["unread"])}


def reflection(state: State) -> dict:
    """The nightly job: what the person's logs say about barriers, anchors and food habits, proposed as facts."""
    uid, write = _uid(state), state["event"].get("write", True)
    out: dict[str, Any] = {"adherence": {}, "nutrition": {}}
    a = adherence.run(uid, write=write)
    out["adherence"] = {"barrier_weeks": len(a["barriers"]), "proposals": [(p["key"], p["result"]) for p in a["proposals"]], "morning_anchor": bool(a["morning_anchor"])}
    n = nutritionstore.reflect_habits(uid, write=write)
    out["nutrition"] = {"proposals": [(p["key"], p["result"]) for p in n]}
    for key, result in out["adherence"]["proposals"] + out["nutrition"]["proposals"]:
        if result in ("proposed", "superseded_and_proposed"):
            audit(uid, "agent", "memory.fact_proposed", "memory_facts", None, {"key": key, "result": result}, _run().id)
    out["learning"] = hooks.reflect(uid, write)
    return out


def nutrition(state: State) -> dict:
    uid, write = _uid(state), state["event"].get("write", False)
    return {"habits": [(h["type"], h["n"], len(h["alternatives"])) for h in nutritionstore.food_habits(uid)], "proposals": [(p["key"], p["result"]) for p in nutritionstore.reflect_habits(uid, write=write)]}


def adherence_node(state: State) -> dict:
    a = adherence.run(_uid(state), write=state["event"].get("write", False))
    return {"barrier_weeks": len(a["barriers"]), "proposals": [(p["key"], p["result"]) for p in a["proposals"]]}


def activity(state: State) -> dict:
    n = nutritionstore.salt_nudge(_uid(state))
    return {"prompt": bool(n), "walk_allowed": bool(n and n["walk"]), "gates": n["gates"] if n else None}


def preventive(state: State) -> dict:
    return preventive_agent.run(_uid(state), write=state["event"].get("write", False))


def unrouted(state: State) -> dict:
    return {"skipped": "no skill was sure enough: nothing was run"}


def build_graph():
    g = StateGraph(State)
    g.add_node("route", route_node)
    nodes = {"reminders": reminders, "reflection": reflection, "nutrition": nutrition, "adherence": adherence_node, "activity": activity,
             "preventive": preventive, "unrouted": unrouted}
    tools = {"reminders": "logstore.notifications", "reflection": "adherence.run + nutritionstore.reflect_habits", "nutrition": "nutritionstore.food_habits",
             "adherence": "adherence.run", "activity": "nutritionstore.salt_nudge", "preventive": "preventive.run", "unrouted": "none"}
    for name, fn in nodes.items():
        g.add_node(name, _wrap(name, tools[name], fn))
        g.add_edge(name, END)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda s: s["route"], {k: k for k in nodes})
    return g.compile()


_GRAPH = None


def run_event(user_key: str, kind: str, quiet: bool = False, **payload: Any) -> dict[str, Any]:
    """Run one event for one person through the graph. Returns the run id, where it was routed and what the sub-agent reported.

    With `quiet=True` (the once-a-minute tick) the trace is kept only when the result differs from the previous quiet run."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    logstore.set_user(user_key, internal=True)
    uid = logstore.current_user()
    run = Run(uid, "orchestrator", TRIGGER.get(kind, "memory"), lazy=quiet)
    token = _RUN.set(run)
    acc: dict[str, Any] = {}
    acc_token = usage.RUN_TOKENS.set(acc)
    try:
        res = _GRAPH.invoke({"event": {"kind": kind, "user_id": uid, **payload}})
        keep = True
        if quiet:
            digest = repr(sorted((res.get("out") or {}).items(), key=lambda kv: kv[0]))
            keep = _LAST_TICK.get(user_key) != digest
            _LAST_TICK[user_key] = digest
        run.finish("ok", keep=keep, tokens=acc, model_id=("jev" if acc.get("calls") else None))
        return {"run_id": str(run.id), "route": res.get("route"), "out": res.get("out"), "logged": keep}
    except Exception as e:
        logger.exception("agent run failed")
        run.finish("error", str(e)[:300], keep=True, tokens=acc)
        raise
    finally:
        _RUN.reset(token)
        usage.RUN_TOKENS.reset(acc_token)
