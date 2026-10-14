"""Read-only check of the Ask Equinox retrieval planner against live data. NO model call, NO write.

For each question it prints: the extra views the planner picks, whether guidance search would run, the context size in characters now
(with the planned views) against the default 14-day context, and which sections have lines. Run it when the database is reachable:

    cd services/api
    python scripts/chat_before_after.py demo "What was my last HbA1c?" "Do I have allergies?" "How was my glucose this week?"
    python scripts/chat_before_after.py mr-tan --show "Is my fasting glucose different from usual?"

--show also prints the context text that would be sent. The guidance search is not run (it would make an embedding call).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import logstore  # noqa: E402
from app.services import chat as C  # noqa: E402
from app.services import chat_planner as P  # noqa: E402


def main(argv: list[str]) -> int:
    show = "--show" in argv
    args = [a for a in argv[1:] if a != "--show"]
    if len(args) < 2:
        sys.stdout.write(__doc__ + "\n")
        return 2
    key, questions = args[0], args[1:]
    logstore.set_user(key)
    uid = str(logstore.current_user())
    today = C.datetime.now(C.TZ).date()
    out = sys.stdout.write
    # the guidance search is skipped here: it would call the embedding model
    C.passages = lambda conn, text, names=None: []       # type: ignore[assignment]
    with logstore.one_connection():
        with logstore.tx() as c:
            for q in questions:
                views = P.plan(q)
                base = C.build_context(c, uid, today, q, frozenset())
                full = C.build_context(c, uid, today, q, views)
                base_chars, full_chars = len(base.text()), len(full.text())
                extra_chars = sum(len(x) for s in full.sections if s.key in views for x in s.lines)
                used = [f"{s.key}({len(s.lines)})" for s in full.sections if s.lines]
                out(f"\nQUESTION: {q}\n")
                out(f"  views planned:    {sorted(views) or 'none'}" + (f" (history reaches {P.history_days(q)} days)" if "longer_history" in views else "") + "\n")
                out(f"  guidance search:  {'would run' if P.needs_guidance(q) else 'skipped (plain question about own data)'}\n")
                out(f"  context size:     {full_chars} characters (default 14-day context {base_chars}; extra views {extra_chars}; caps {C.MAX_VIEW_LINES} lines per view, {C.MAX_VIEW_CHARS} characters for all views)\n")
                out(f"  sections used:    {', '.join(used) or 'none'}\n")
                empty = [v for v in sorted(views) if not any(s.key == v and s.lines for s in full.sections)]
                if empty:
                    out(f"  planned but empty: {', '.join(empty)} (nothing on record, or the view could not be read; see the log)\n")
                if show:
                    out("  ---- context ----\n" + full.text() + "\n  -----------------\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
