"""Medicine clash alerts (prd F5, docs/specs/f5-clash.md): the database half of the check, and saving, listing and answering alerts.

Two things can raise an alert for a pair of the person's medicines:
  - the drug-pair rules from the drug labels (`interaction_rules`), looked up here in code after matching each medicine to a drug by name
  - the AI model with a web search (`app/agents/clash_checker.py`), passed in here as plain pairs
An alert is raised if either finds the pair. Saving only ever adds or strengthens an alert; nothing found by the database is removed because
the model did not repeat it. The patient message is always "Possible interaction between X and Y. Please check with your pharmacist or
doctor before continuing." and never says to stop a medicine. This module never imports the agents. Event payloads hold ids, counts and
enums only, never names or health values (rules.md section 3).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import psycopg
from psycopg.types.json import Jsonb

from app.core.errors import NotFound
from app.services.web_sources import OPENFDA_TITLE, clean, is_openfda

DB_SOURCE_TITLE = OPENFDA_TITLE                     # the drug-label source: named as data, with no link (see web_sources)
DB_SUMMARY = "The drug label information for one of these medicines mentions the other."
GENERIC_SUMMARY = "These two medicines may interact."


@dataclass(frozen=True)
class DbPair:
    a: str
    b: str
    rule_id: str
    source_url: str | None


def patient_text(a: str, b: str) -> str:
    """The only wording a patient is shown for a clash (prd F5). It never says to stop, skip or change anything."""
    return f"Possible interaction between {a} and {b}. Please check with your pharmacist or doctor before continuing."


def list_medicines(conn: psycopg.Connection, user_id: str, only_ids: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """The person's saved medicines, in the order they were started (the order they would have been added)."""
    rows = conn.execute(
        "select id, name, strength, kind::text, drug_reference_id from medications where user_id = %s and deleted_at is null "
        "order by start_date nulls last, created_at, name", (user_id,)).fetchall()
    keep = {str(i) for i in only_ids} if only_ids is not None else None
    return [{"id": str(r[0]), "name": r[1], "strength": r[2], "kind": r[3], "drug_reference_id": str(r[4]) if r[4] else None}
            for r in rows if keep is None or str(r[0]) in keep]


def _words(name: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", name.lower()).strip() + " "


def match_drugs(conn: psycopg.Connection, meds: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """medicine id -> drug id. A medicine already linked keeps its link; otherwise the drug's generic name (or a short alias of it) must
    appear in the medicine's name as whole words. A brand name that contains no generic (CRESTOR) is not matched: the AI check covers it."""
    out = {m["id"]: m["drug_reference_id"] for m in meds if m["drug_reference_id"]}
    todo = [m for m in meds if m["id"] not in out]
    if not todo:
        return out
    names = [(str(r[0]), r[1]) for r in conn.execute("select id, generic_name from drug_reference").fetchall()]
    names += [(str(r[0]), r[1]) for r in conn.execute("select drug_reference_id, alias from drug_aliases where alias !~ '\\s.*\\s.*\\s'").fetchall()]
    for m in todo:
        hay = _words(m["name"])
        for drug_id, term in names:
            t = _words(term).strip()
            if len(t) >= 5 and f" {t} " in hay:
                out[m["id"]] = drug_id
                break
    return out


def database_pairs(conn: psycopg.Connection, meds: Sequence[Mapping[str, Any]]) -> list[DbPair]:
    """Pairs of the person's medicines that the drug-pair rules list, in either order."""
    refs = match_drugs(conn, meds)
    found: list[DbPair] = []
    ids = [m["id"] for m in meds]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            da, db = refs.get(a), refs.get(b)
            if not da or not db or da == db:
                continue
            r = conn.execute(
                "select id, source_url from interaction_rules where (drug_a_id = %s and drug_b_id = %s) or (drug_a_id = %s and drug_b_id = %s) limit 1",
                (da, db, db, da)).fetchone()
            if r:
                found.append(DbPair(a, b, str(r[0]), r[1]))
    return found


def save_alerts(conn: psycopg.Connection, user_id: str, db_pairs: Sequence[DbPair], ai_pairs: Sequence[tuple[str, str, str]],
                ai_sources: Sequence[Mapping[str, str]], model_id: str | None) -> dict[str, int]:
    """Add or strengthen one alert per pair. ai_pairs are (medicine a, medicine b, reason). Returns counts of new and updated alerts."""
    pairs: dict[frozenset[str], dict[str, Any]] = {}
    for p in db_pairs:
        pairs[frozenset((p.a, p.b))] = {"a": p.a, "b": p.b, "rule": p.rule_id, "url": p.source_url, "ai": None}
    for a, b, summary in ai_pairs:
        slot = pairs.setdefault(frozenset((a, b)), {"a": a, "b": b, "rule": None, "url": None, "ai": None})
        slot["ai"] = summary or ""
    new = updated = 0
    for slot in pairs.values():
        a, b = sorted((slot["a"], slot["b"]))
        has_db, has_ai = slot["rule"] is not None, slot["ai"] is not None
        db_source = clean([{"title": DB_SOURCE_TITLE, "url": slot["url"]}]) if has_db and slot["url"] else []
        row = conn.execute(
            "select id, origin, sources from interaction_alerts where user_id = %s and med_b_id is not null "
            "and least(med_a_id::text, med_b_id::text) = %s and greatest(med_a_id::text, med_b_id::text) = %s", (user_id, a, b)).fetchone()
        if row is None:
            origin = "both" if has_db and has_ai else "database" if has_db else "ai"
            summary = slot["ai"] or (DB_SUMMARY if has_db else GENERIC_SUMMARY)
            sources = clean(db_source + (list(ai_sources) if has_ai else []))
            r = conn.execute(
                "insert into interaction_alerts (user_id, med_a_id, med_b_id, interaction_rule_id, status, origin, summary, sources, model_id) "
                "values (%s, %s, %s, %s, 'open', %s, %s, %s, %s) returning id",
                (user_id, a, b, slot["rule"], origin, summary, Jsonb(sources), model_id if has_ai else None)).fetchone()
            conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'agent', 'interaction.alert.raised', "
                         "'interaction_alerts', %s, %s)", (user_id, r[0] if r else None, Jsonb({"origin": origin})))
            new += 1
            continue
        keep_db = row[1] in ("database", "both") or has_db
        keep_ai = row[1] in ("ai", "both") or has_ai
        origin = "both" if keep_db and keep_ai else "database" if keep_db else "ai"
        if has_ai:                                    # the model's newest reason and pages replace its older ones; the label link stays
            kept = [s for s in (row[2] or []) if is_openfda(s.get("title"), s.get("url"))]
            conn.execute("update interaction_alerts set origin = %s, interaction_rule_id = coalesce(interaction_rule_id, %s), summary = %s, "
                         "sources = %s, model_id = %s where id = %s",
                         (origin, slot["rule"], slot["ai"] or (DB_SUMMARY if keep_db else GENERIC_SUMMARY), Jsonb(clean((db_source or kept) + list(ai_sources))), model_id, row[0]))
        else:                                         # the database found it again: never overwrite what the model said
            conn.execute("update interaction_alerts set origin = %s, interaction_rule_id = coalesce(interaction_rule_id, %s), "
                         "summary = coalesce(summary, %s) where id = %s", (origin, slot["rule"], DB_SUMMARY, row[0]))
        updated += 1
    return {"new": new, "updated": updated}


def question_text(a: str, b: str) -> str:
    return f"Is it OK to take {a} and {b} together? They may interact."


def list_open(conn: psycopg.Connection, user_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "select a.id, a.origin, a.summary, a.sources, ma.name, ma.strength, mb.name, mb.strength, a.created_at from interaction_alerts a "
        "join medications ma on ma.id = a.med_a_id and ma.deleted_at is null join medications mb on mb.id = a.med_b_id and mb.deleted_at is null "
        "where a.user_id = %s and a.status = 'open' and a.med_b_id is not null order by a.created_at, a.id", (user_id,)).fetchall()
    asked = {r[0] for r in conn.execute("select text from doctor_questions where user_id = %s and status = 'open' and text like 'Is it OK to take %%'", (user_id,)).fetchall()}
    out = []
    for aid, origin, summary, sources, na, sa, nb, sb, raised_at in rows:
        la, lb = _label(na, sa), _label(nb, sb)
        out.append({"id": str(aid), "med_a": la, "med_b": lb, "text": patient_text(la, lb), "summary": summary or "", "origin": origin,
                    "sources": clean(sources), "question_added": question_text(la, lb) in asked or question_text(lb, la) in asked,
                    "raised_at": raised_at})
    return out


def _label(name: str, strength: str | None) -> str:
    n = " ".join(name.split())
    return n if not strength or strength.lower().replace(" ", "") in n.lower().replace(" ", "") else f"{n} {strength.strip()}"


def _owned(conn: psycopg.Connection, user_id: str, alert_id: str) -> tuple[Any, ...]:
    try:
        row = conn.execute("select id, med_a_id, med_b_id from interaction_alerts where id = %s and user_id = %s", (alert_id, user_id)).fetchone()
    except psycopg.errors.InvalidTextRepresentation:
        conn.rollback()
        raise NotFound("Alert not found") from None
    if row is None:
        raise NotFound("Alert not found")
    return row


def acknowledge(conn: psycopg.Connection, user_id: str, alert_id: str) -> None:
    """'I have checked with my doctor': the alert stops showing. Nothing else changes."""
    row = _owned(conn, user_id, alert_id)
    conn.execute("update interaction_alerts set status = 'acknowledged', acknowledged_at = now() where id = %s and status = 'open'", (row[0],))
    conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'interaction.alert.acknowledged', "
                 "'interaction_alerts', %s, '{}'::jsonb)", (user_id, row[0]))


def add_question(conn: psycopg.Connection, user_id: str, alert_id: str, text: str | None = None) -> str:
    """Save 'Is it OK to take X and Y together?' to the doctor-question list, or the person's own words when they typed a question."""
    row = _owned(conn, user_id, alert_id)
    if text and text.strip():                           # their own question about this alert: saved as written, every time
        own = conn.execute("insert into doctor_questions (user_id, text, origin, status) values (%s, %s, 'user', 'open') returning id",
                           (user_id, text.strip())).fetchone()
        if own is None:
            raise RuntimeError("the database returned no row for an insert")
        conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'doctor_question.added', "
                     "'doctor_questions', %s, %s)", (user_id, own[0], Jsonb({"from": "interaction_alert", "own_words": True})))
        return str(own[0])
    names = [_label(r[0], r[1]) for r in (conn.execute("select name, strength from medications where id = %s", (m,)).fetchone() for m in (row[1], row[2])) if r]
    text = question_text(names[0], names[1]) if len(names) == 2 else "Can you check my medicines for interactions?"
    same = conn.execute("select id from doctor_questions where user_id = %s and text = %s and status = 'open' limit 1", (user_id, text)).fetchone()
    if same:                                            # asking twice saves it once
        return str(same[0])
    q = conn.execute("insert into doctor_questions (user_id, text, origin, status) values (%s, %s, 'agent_suggested', 'open') returning id", (user_id, text)).fetchone()
    if q is None:
        raise RuntimeError("the database returned no row for an insert")
    conn.execute("insert into event_log (user_id, actor, event, entity_table, entity_id, payload) values (%s, 'user', 'doctor_question.added', "
                 "'doctor_questions', %s, %s)", (user_id, q[0], Jsonb({"from": "interaction_alert"})))
    return str(q[0])
