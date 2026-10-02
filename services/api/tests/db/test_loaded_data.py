"""Tests for the data loaded by E1-4. They call scripts/verify_loaded.py, which recomputes every expected count from the
raw files, so the loaders are not marking their own homework. Run from the repo root:
    python -m pytest services/api/tests/db/test_loaded_data.py -q
Needs DATABASE_URL in the private .env and the data loaded (python scripts/load_all.py).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_loaded  # noqa: E402
from etl_common import connect  # noqa: E402


@pytest.fixture(scope="module")
def results():
    verify_loaded.results.clear()
    with connect() as conn:
        verify_loaded.run(conn)
    return list(verify_loaded.results)


def test_there_are_checks(results):
    assert len(results) >= 70


def test_every_check_passes(results):
    failed = [f"{name} [{detail}]" for name, ok, detail in results if not ok]
    assert not failed, "failed checks:\n" + "\n".join(failed)
