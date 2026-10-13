"""Who the app can act as: only the demo user and Mr Tan. "Start as new person" (POST /api/v1/users) was removed on 2026-10-13."""
from __future__ import annotations

import pytest

from app.db import logstore


def test_the_known_users_are_the_demo_user_and_mr_tan():
    assert set(logstore.USERS) == {"demo", "mr-tan"}
    assert logstore.USERS["mr-tan"]["id"] == logstore.MR_TAN_USER


@pytest.mark.parametrize("bad", ["salary", "person-0123456789ab", "person-XYZ", "../mr-tan", "someone-else"])
def test_any_other_key_is_refused_and_never_changes_who_is_acting(bad):
    token = logstore._current.set("demo")
    try:
        with pytest.raises(KeyError):
            logstore.set_user(bad)
        assert logstore.current_user_key() == "demo"
    finally:
        logstore._current.reset(token)


def test_there_is_no_route_to_start_a_new_person():
    from fastapi.testclient import TestClient

    from app.main import app

    res = TestClient(app).post("/api/v1/users")
    assert res.status_code in (404, 405)
