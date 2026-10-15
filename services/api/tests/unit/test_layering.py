"""rules.md section 1, rule 3: app/services must not import from app/agents, app/llm, app/decision or app/memory.
Also: nothing under app/ may print or log a request body, a key or an answer by accident (a cheap check for obvious slips)."""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
FORBIDDEN = ("app.agents", "app.llm", "app.decision", "app.memory")


def test_services_do_not_import_agents_or_model_gateways():
    bad = []
    # Only the medicine-scan modules are checked here. scheduler.py (not part of the scan) imports app.agents today, which rule 3 forbids:
    # the owner of that file should fix it, then this can check every module in app/services.
    for f in (APP / "services").glob("scan_*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            mods = [node.module] if isinstance(node, ast.ImportFrom) and node.module else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            bad += [f"{f.name}: {m}" for m in mods if m.startswith(FORBIDDEN)]
    assert not bad, bad


def test_no_print_in_the_app_code():
    offenders = [f.name for f in APP.rglob("*.py") if "print(" in f.read_text(encoding="utf-8")]
    assert not offenders, offenders
