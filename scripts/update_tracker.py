#!/usr/bin/env python3
"""Refresh the generated parts of the backlog from the three personal backlogs.

Reads docs/backlog/{hongyi,joely,damien}.md and rewrites:
  - the BLOCKERS block inside each personal file
  - docs/backlog/SOT.md (the central tracker; only the NOTES block is hand-written)

Usage:
  python scripts/update_tracker.py          rewrite the generated parts
  python scripts/update_tracker.py --check  exit 1 if they are out of date (used by verify_docs.py)

If a git merge conflict lands in a generated part, take either side and run this again.
It is a consistency tool, not a sign-off.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "docs" / "backlog"
PEOPLE = [("Hong Yi", "hongyi.md"), ("Joely", "joely.md"), ("Damien", "damien.md")]
STATUSES = ["backlog", "in progress", "in review", "blocked", "done"]

HEAD = re.compile(r"^### (\S+) (.+?) · (P\d)( · NEEDS OK)?\s*$", re.M)
NOTES_RE = re.compile(r"(<!-- NOTES:START -->\n)(.*?)(<!-- NOTES:END -->)", re.S)
BLOCKERS_RE = re.compile(r"(<!-- BLOCKERS:START -->\n)(.*?)(<!-- BLOCKERS:END -->)", re.S)


def field(body, name):
    m = re.search(r"^- \*\*%s:\*\*[ \t]*(.*)$" % re.escape(name), body, re.M)
    return m.group(1).strip() if m else ""


def ids(text):
    if not text or text.lower() == "none":
        return []
    return [t.strip() for t in text.split(",") if t.strip()]


def parse():
    tasks = {}
    order = []
    for person, fname in PEOPLE:
        text = (BACKLOG / fname).read_text(encoding="utf-8")
        marks = list(HEAD.finditer(text))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[m.end():end]
            subs = re.findall(r"^  - \[(.)\] ", body, re.M)
            t = dict(
                id=m.group(1), title=m.group(2), pri=m.group(3), needs_ok=bool(m.group(4)),
                owner=person, file=fname,
                status=field(body, "Status").lower() or "backlog",
                hard=ids(field(body, "Needs first")), soft=ids(field(body, "Needed later")),
                reviewer=field(body, "Reviewer"), also=field(body, "Also"), flag=field(body, "Flag"),
                phase=field(body, "Phase"), note=field(body, "Note"),
                ticked=sum(1 for s in subs if s.lower() == "x"), total=len(subs),
            )
            tasks[t["id"]] = t
            order.append(t["id"])
    return tasks, order


def sort_key(tid):
    m = re.match(r"([A-Z]+)(\d+)(?:-(\d+))?", tid)
    return (m.group(1) != "E", m.group(1), int(m.group(2)), int(m.group(3) or 0))


def analyse(tasks):
    problems = []
    for t in tasks.values():
        if t["status"] not in STATUSES:
            problems.append("%s has an unknown status '%s'" % (t["id"], t["status"]))
        for d in t["hard"] + t["soft"]:
            if d not in tasks:
                problems.append("%s refers to unknown task %s" % (t["id"], d))
        if t["total"] and t["ticked"] == t["total"] and t["status"] in ("backlog", "in progress", "blocked"):
            problems.append("%s: every subtask is ticked but Status is '%s'" % (t["id"], t["status"]))
        if t["status"] == "done" and t["ticked"] != t["total"]:
            problems.append("%s: Status is done but %d of %d subtasks are ticked" % (t["id"], t["ticked"], t["total"]))
        if t["status"] == "done" and t["reviewer"] and not re.search(r"Verified by", t["note"]):
            problems.append("%s: has a Reviewer, so Note must say 'Verified by <name> <date>' before done" % t["id"])
    for t in tasks.values():
        t["open_hard"] = [d for d in t["hard"] if d in tasks and tasks[d]["status"] != "done"]
        t["open_soft"] = [d for d in t["soft"] if d in tasks and tasks[d]["status"] != "done"]
        if t["status"] == "done":
            t["state"] = "done"
        elif t["status"] == "in review":
            t["state"] = "in review"
        elif t["open_hard"]:
            t["state"] = "blocked"
        elif t["status"] == "in progress":
            t["state"] = "in progress"
        else:
            t["state"] = "ready"
    # downstream count (transitive over hard links)
    rev = {k: [] for k in tasks}
    for t in tasks.values():
        for d in t["hard"]:
            if d in rev:
                rev[d].append(t["id"])

    def down(tid, seen):
        for n in rev[tid]:
            if n not in seen:
                seen.add(n)
                down(n, seen)
        return seen
    for t in tasks.values():
        t["unblocks"] = len(down(t["id"], set()))
    return problems


def who(tasks, tid):
    t = tasks[tid]
    return "%s (%s, %s)" % (tid, t["owner"], t["status"])


def blockers_block(tasks, order, person):
    mine = [tid for tid in sorted(order, key=sort_key) if tasks[tid]["owner"] == person]
    groups = {"ready": [], "in progress": [], "in review": [], "blocked": [], "done": []}
    for tid in mine:
        groups[tasks[tid]["state"]].append(tid)
    L = []
    L.append("Ready means everything under **Needs first** is done, so you can start. Blocked means you must wait.")
    L.append("")
    ready = sorted(groups["ready"], key=lambda x: -tasks[x]["unblocks"])
    L.append("**Ready now (%d)**" % len(ready))
    L.append("")
    if ready:
        for tid in ready:
            t = tasks[tid]
            extra = ""
            if t["open_soft"]:
                extra = " Later you will need: " + ", ".join(who(tasks, d) for d in t["open_soft"]) + "."
            L.append("- %s %s: unblocks %d other task%s.%s" % (tid, t["title"], t["unblocks"], "" if t["unblocks"] == 1 else "s", extra))
    else:
        L.append("- Nothing is ready right now.")
    L.append("")
    if groups["in progress"] or groups["in review"]:
        L.append("**In progress or in review**")
        L.append("")
        for tid in groups["in progress"] + groups["in review"]:
            L.append("- %s %s (%s)" % (tid, tasks[tid]["title"], tasks[tid]["status"]))
        L.append("")
    L.append("**Blocked (%d)**" % len(groups["blocked"]))
    L.append("")
    if groups["blocked"]:
        for tid in groups["blocked"]:
            t = tasks[tid]
            L.append("- %s %s: waiting for %s" % (tid, t["title"], ", ".join(who(tasks, d) for d in t["open_hard"])))
    else:
        L.append("- Nothing is blocked.")
    L.append("")
    L.append("Done: %d of %d tasks." % (len(groups["done"]), len(mine)))
    return "\n".join(L) + "\n"


def bar(done, total, width=20):
    if not total:
        return ""
    n = round(width * done / total)
    return "[" + "#" * n + "-" * (width - n) + "] %d%%" % round(100 * done / total)


def esc(s):
    return s.replace("|", "/")


def sot_generated(tasks, order, problems):
    ids_sorted = sorted(order, key=sort_key)
    L = []
    tot = len(tasks)
    done = sum(1 for t in tasks.values() if t["state"] == "done")
    st, sd = sum(t["total"] for t in tasks.values()), sum(t["ticked"] for t in tasks.values())
    L.append("## Progress")
    L.append("")
    L.append("| | Tasks done | Subtasks ticked | Progress |")
    L.append("|---|---|---|---|")
    L.append("| **Whole project** | %d of %d | %d of %d | `%s` |" % (done, tot, sd, st, bar(sd, st)))
    for person, _ in PEOPLE:
        mine = [t for t in tasks.values() if t["owner"] == person]
        a = sum(1 for t in mine if t["state"] == "done")
        b, c = sum(x["ticked"] for x in mine), sum(x["total"] for x in mine)
        L.append("| %s | %d of %d | %d of %d | `%s` |" % (person, a, len(mine), b, c, bar(b, c)))
    L.append("")
    L.append("## Gates")
    L.append("")
    L.append("| Gate | Status | Still waiting for |")
    L.append("|---|---|---|")
    for tid in ids_sorted:
        if tid.startswith("CP"):
            t = tasks[tid]
            wait = ", ".join(t["open_hard"]) or "nothing"
            L.append("| %s %s | %s | %s |" % (tid, esc(t["title"]), t["state"], wait))
    L.append("")
    L.append("## Who can start now")
    L.append("")
    L.append("Tasks whose **Needs first** are all done. Sorted by how many other tasks they unblock.")
    L.append("")
    L.append("| Person | Ready now | Blocked | In progress or review | Done |")
    L.append("|---|---|---|---|---|")
    for person, _ in PEOPLE:
        mine = [t for t in tasks.values() if t["owner"] == person]
        ready = sorted([t for t in mine if t["state"] == "ready"], key=lambda t: -t["unblocks"])
        rtxt = ", ".join("%s (%d)" % (t["id"], t["unblocks"]) for t in ready) or "none"
        busy = sum(1 for t in mine if t["state"] in ("in progress", "in review"))
        L.append("| %s | %s | %d | %d | %d |" % (person, rtxt, sum(1 for t in mine if t["state"] == "blocked"), busy,
                                               sum(1 for t in mine if t["state"] == "done")))
    L.append("")
    L.append("The number in brackets is how many other tasks are waiting, directly or indirectly, on that task.")
    L.append("")
    L.append("## All tasks")
    L.append("")
    L.append("| ID | Task | Owner | Priority | State | Subtasks | Waiting for | Reviewer |")
    L.append("|---|---|---|---|---|---|---|---|")
    for tid in ids_sorted:
        t = tasks[tid]
        owner = t["owner"] + (" + " + t["also"] if t["also"] and t["also"] != "the whole team" else "")
        if t["also"] == "the whole team":
            owner += " (team task)"
        title = esc(t["title"]) + (" (needs OK)" if t["needs_ok"] else "")
        L.append("| %s | %s | %s | %s | %s | %d/%d | %s | %s |" % (
            tid, title, owner, t["pri"], t["state"], t["ticked"], t["total"],
            ", ".join(t["open_hard"]) or "none", t["reviewer"] or ""))
    L.append("")
    flagged = [t for t in tasks.values() if t["flag"]]
    L.append("## Open flags")
    L.append("")
    if flagged:
        for t in sorted(flagged, key=lambda t: sort_key(t["id"])):
            L.append("- **%s** (%s): %s" % (t["id"], t["owner"], t["flag"]))
    else:
        L.append("- None.")
    L.append("")
    needs = [t for t in tasks.values() if t["needs_ok"] and t["state"] != "done"]
    L.append("## Needs the owner's OK before work starts")
    L.append("")
    if needs:
        for t in sorted(needs, key=lambda t: sort_key(t["id"])):
            L.append("- %s %s (%s)" % (t["id"], t["title"], t["owner"]))
    else:
        L.append("- None.")
    L.append("")
    L.append("## Consistency warnings")
    L.append("")
    if problems:
        for p in problems:
            L.append("- " + p)
    else:
        L.append("- None.")
    return "\n".join(L) + "\n"


SOT_HEAD = """# Equinox: central tracker

The single place to see where the project stands. **Everything between the generated markers is rewritten by `python scripts/update_tracker.py`. Do not edit it by hand.** Progress comes from the three personal backlogs: [Hong Yi](hongyi.md), [Joely](joely.md) and [Damien](damien.md). Each person edits only their own file, then runs the script.

How a task moves: `backlog`, then `in progress`, then `in review` (only if it has a Reviewer) or straight to `done`. A task is **ready** when everything in its "Needs first" list is done. Details for the data foundation are in [details/e1-data-foundation.md](details/e1-data-foundation.md). Only the owner promotes `dev` to `uat` and `main`.

The text in the notes block below is written by hand (by the owner or an AI assistant at the owner's request) and survives regeneration.

<!-- NOTES:START -->
{notes}<!-- NOTES:END -->

<!-- GENERATED:START -->
{generated}<!-- GENERATED:END -->
"""

DEFAULT_NOTES = "(no notes yet)\n"


def build(write):
    tasks, order = parse()
    problems = analyse(tasks)
    stale = []
    # personal files
    for person, fname in PEOPLE:
        p = BACKLOG / fname
        text = p.read_text(encoding="utf-8")
        new_inner = blockers_block(tasks, order, person)
        m = BLOCKERS_RE.search(text)
        if not m:
            problems.append("%s has no BLOCKERS markers" % fname)
            continue
        new = text[:m.start(2)] + new_inner + text[m.end(2):]
        if new != text:
            stale.append(fname)
            if write:
                p.write_text(new, encoding="utf-8", newline="\n")
    sot = BACKLOG / "SOT.md"
    notes = DEFAULT_NOTES
    if sot.exists():
        m = NOTES_RE.search(sot.read_text(encoding="utf-8"))
        if m:
            notes = m.group(2)
    new_sot = SOT_HEAD.format(notes=notes, generated=sot_generated(tasks, order, problems))
    old_sot = sot.read_text(encoding="utf-8") if sot.exists() else ""
    if new_sot != old_sot:
        stale.append("SOT.md")
        if write:
            sot.write_text(new_sot, encoding="utf-8", newline="\n")
    return tasks, problems, stale


def main():
    check = "--check" in sys.argv
    tasks, problems, stale = build(write=not check)
    if check:
        if stale:
            print("FAIL: generated parts are out of date in: " + ", ".join(stale) + ". Run python scripts/update_tracker.py")
            return 1
        print("OK: generated parts are up to date (%d tasks)" % len(tasks))
        return 0
    done = sum(1 for t in tasks.values() if t["state"] == "done")
    print("Tracker updated: %d tasks, %d done. Rewrote: %s" % (len(tasks), done, ", ".join(stale) or "nothing (already current)"))
    for p in problems:
        print("WARNING: " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
