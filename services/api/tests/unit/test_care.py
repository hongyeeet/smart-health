"""Me care screens: the pure rules (due dates, plain lines, source freshness) and the request checks. No database."""
from datetime import date, datetime, timedelta, timezone
from typing import get_args

import pytest
from pydantic import ValidationError

from app.core.errors import ValidationFailed
from app.schemas import care as S
from app.services import care as svc

TODAY = date(2026, 10, 10)
NOW = datetime(2026, 10, 10, 2, 52, tzinfo=timezone.utc)   # 10:52 in Singapore


def test_preventive_status_uses_the_stored_next_date_only():
    assert svc.preventive_status(None, TODAY) == "unknown"
    assert svc.preventive_status(TODAY - timedelta(days=1), TODAY) == "overdue"
    assert svc.preventive_status(TODAY, TODAY) == "due_soon"                 # due today is not overdue yet
    assert svc.preventive_status(TODAY + timedelta(days=30), TODAY) == "due_soon"
    assert svc.preventive_status(TODAY + timedelta(days=31), TODAY) == "ok"


def test_preventive_detail_is_plain_and_never_advice():
    assert svc.preventive_detail("overdue", date(2024, 9, 2), date(2025, 9, 2)) == "Last done 2 Sep 2024. Was due 2 Sep 2025."
    assert svc.preventive_detail("ok", date(2026, 3, 16), date(2027, 3, 16)) == "Last done 16 Mar 2026. Next due 16 Mar 2027."
    assert svc.preventive_detail("unknown", None, None) == "No date on record yet."
    assert svc.preventive_detail("unknown", date(2026, 1, 5), None) == "Last done 5 Jan 2026. No next date on record."


def test_scheduled_label_is_singapore_time():
    assert svc.scheduled_label(datetime(2026, 10, 11, 2, 0, tzinfo=timezone.utc)) == "Sun 11 Oct, 10:00 am"
    assert svc.scheduled_label(datetime(2026, 10, 11, 9, 30, tzinfo=svc.TZ)) == "Sun 11 Oct, 9:30 am"


def test_source_with_no_model_says_not_connected_and_connecting_is_not_available():
    row = svc.source_row("cgm", None, None, NOW)
    assert row["status"] == "not_connected" and row["status_label"] == "Not connected"
    assert "not available yet" in row["note"]


def test_connected_source_shows_last_data_in_singapore_time():
    last = datetime(2026, 10, 1, 23, 40, tzinfo=timezone.utc)                  # 2 Oct 07:40 in Singapore
    row = svc.source_row("cgm", "Dexcom G6", last, NOW)
    assert row["status"] == "connected"
    assert row["status_label"] == "Connected, last data 2 Oct 07:40"
    assert row["freshness"] == "old"


def test_fresh_and_empty_connected_sources():
    fresh = svc.source_row("watch", "Fitbit Sense", NOW - timedelta(hours=3), NOW)
    assert fresh["freshness"] == "up_to_date" and fresh["note"] == "Up to date."
    empty = svc.source_row("watch", "Fitbit Sense", None, NOW)
    assert empty["status"] == "connected_no_data" and empty["status_label"] == "Connected, no data yet"


def test_camera_is_on_this_device_with_nothing_to_connect():
    row = svc.source_row("camera", None, None, NOW)
    assert row["status"] == "on_device" and row["status_label"] == "On this device"


def test_every_appointment_kind_has_a_label():
    assert set(get_args(S.AppointmentKind)) <= set(svc.KIND_LABELS)


def test_suggested_reason_is_a_plain_sentence():
    assert svc.suggested_text({"due": "overdue"}) == "Suggested because it is overdue."
    assert svc.suggested_text(None) is None


def test_question_text_is_trimmed_and_cannot_be_blank():
    assert S.NewQuestion(text="  Can I walk after dinner?  ").text == "Can I walk after dinner?"
    with pytest.raises(ValidationError):
        S.NewQuestion(text="   ")
    with pytest.raises(ValidationError):
        S.NewQuestion(text="x" * 301)


def test_blank_location_is_none():
    body = S.NewAppointment(kind="other", scheduled_for=datetime(2026, 10, 20, 9, 30), location="   ")
    assert body.location is None


def test_appointment_must_be_in_the_future():
    past = datetime(2026, 10, 1, 9, 0, tzinfo=svc.TZ)
    with pytest.raises(ValidationFailed):
        svc.add_appointment(None, "user", "gp_review", past, None, None, NOW)   # refused before any database call


def test_question_out_labels_the_origin():
    row = {"id": "1", "text": "t", "origin": "agent_suggested", "status": "open", "created_at": NOW}
    out = svc.question_out(row)
    assert out["origin_label"] == "Suggested by Smart Health" and out["can_remove"] is True
    asked = svc.question_out({**row, "status": "asked"})
    assert asked["can_remove"] is False
