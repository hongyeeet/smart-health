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
    assert set(get_args(S.StoredAppointmentKind)) <= set(svc.KIND_LABELS)
    assert set(get_args(S.AppointmentKind)) <= set(svc.APPOINTMENT_KIND_LABELS)


def test_vaccination_and_dental_are_no_longer_offered_for_a_visit():
    offered = set(get_args(S.AppointmentKind))
    assert "vaccination" not in offered and "dental" not in offered
    assert offered == set(svc.NEW_APPOINTMENT_KINDS)
    assert svc.APPOINTMENT_KIND_LABELS["hba1c_test"] == "Blood test"


def test_an_old_visit_of_a_removed_kind_still_reads_with_its_old_label():
    row = {"id": "1", "kind": "dental", "status": "planned", "scheduled_for": NOW + timedelta(days=5), "location": "Clinic",
           "suggested_reason": None, "confirmed_by_user_at": NOW}
    out = S.AppointmentOut.model_validate(svc.appointment_out(row))
    assert out.kind_label == "Dental check" and out.kind == "dental"
    old = svc.appointment_out({**row, "kind": "vaccination"})
    assert old["kind_label"] == "Vaccination"


def test_a_new_visit_of_a_removed_kind_is_refused_before_any_database_call():
    future = datetime(2026, 10, 20, 9, 30, tzinfo=svc.TZ)
    with pytest.raises(ValidationFailed):
        svc.add_appointment(None, "user", "dental", future, None, NOW)
    with pytest.raises(ValidationFailed):
        svc.add_appointment(None, "user", "vaccination", future, None, NOW)


def test_the_place_is_no_longer_asked_on_a_new_visit():
    body = S.NewAppointment(kind="other", scheduled_for=datetime(2026, 10, 20, 9, 30))
    assert not hasattr(body, "location")


def test_question_done_body_is_a_flag():
    assert S.QuestionDone(done=True).done is True
    with pytest.raises(ValidationError):
        S.QuestionDone(done="maybe")


def test_suggested_reason_is_a_plain_sentence():
    assert svc.suggested_text({"due": "overdue"}) == "Suggested because it is overdue."
    assert svc.suggested_text(None) is None


def test_question_text_is_trimmed_and_cannot_be_blank():
    assert S.NewQuestion(text="  Can I walk after dinner?  ").text == "Can I walk after dinner?"
    with pytest.raises(ValidationError):
        S.NewQuestion(text="   ")
    with pytest.raises(ValidationError):
        S.NewQuestion(text="x" * 301)


def test_appointment_must_be_in_the_future():
    past = datetime(2026, 10, 1, 9, 0, tzinfo=svc.TZ)
    with pytest.raises(ValidationFailed):
        svc.add_appointment(None, "user", "gp_review", past, None, NOW)   # refused before any database call


def test_question_out_labels_the_origin():
    row = {"id": "1", "text": "t", "origin": "agent_suggested", "status": "open", "created_at": NOW}
    out = svc.question_out(row)
    assert out["origin_label"] == "Suggested by Equinox" and out["can_remove"] is True
    done = svc.question_out({**row, "status": "asked"})
    assert done["can_remove"] is True and done["origin_label"] == "Suggested by Equinox"


# ----------------------------------------------------------------------------------------------- one rule for the next appointment
def visit(vid: str, status: str, when: datetime | None, kind: str = "diabetes_review") -> dict:
    return {"id": vid, "kind": kind, "status": status, "scheduled_for": when, "location": None,
            "suggested_reason": None, "confirmed_by_user_at": NOW}


def test_next_visit_is_the_earliest_planned_visit_still_to_come():
    later, sooner = visit("a", "planned", NOW + timedelta(days=9)), visit("b", "planned", NOW + timedelta(days=2))
    assert svc.pick_next_visit([later, sooner], NOW)["id"] == "b"


def test_a_visit_whose_time_has_passed_is_not_next():
    past = visit("p", "planned", NOW - timedelta(hours=1))
    assert svc.pick_next_visit([past], NOW) is None
    assert svc.is_next_visit("planned", NOW, NOW) is True                    # the same minute is still to come


def test_a_cancelled_or_suggested_visit_is_never_next():
    future = NOW + timedelta(days=3)
    assert svc.pick_next_visit([visit("c", "cancelled", future), visit("s", "suggested", future)], NOW) is None
    assert svc.is_next_visit("missed", future, NOW) is False and svc.is_next_visit("completed", future, NOW) is False


def test_no_visits_means_no_next_visit():
    assert svc.pick_next_visit([], NOW) is None


def test_past_visits_are_listed_as_past_and_newest_first_and_future_ones_as_upcoming():
    rows = [visit("old", "planned", NOW - timedelta(days=30)), visit("older", "planned", NOW - timedelta(days=60)),
            visit("soon", "planned", NOW + timedelta(days=1)), visit("sug", "suggested", None), visit("gone", "planned", NOW - timedelta(days=1))]
    upcoming, earlier = svc.split_visits(rows, NOW)
    assert [v["id"] for v in upcoming] == ["soon", "sug"]
    assert [v["id"] for v in earlier] == ["gone", "old", "older"]
    assert all(v["status"] == "past" for v in earlier)
    S.CarePlan.model_validate({"next_appointment": None, "upcoming": upcoming, "earlier": earlier, "preventive": [], "questions": []})
