"""The /scans route end to end against the real tables, with the model and the storage replaced by fakes.

Everything runs inside one transaction that is rolled back, so the shared database is left untouched.
Run from services/api:  python -m pytest tests/db/test_scans_route.py -q       Needs DATABASE_URL in the private .env.
"""
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import psycopg
import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.agents import scan_pipeline  # noqa: E402
from app.api.routers import medications, scans  # noqa: E402
from app.db import logstore  # noqa: E402
from app.schemas.medicine_scan import (  # noqa: E402
    ScanOutcome,
    ScoredField,
    ScoredItem,
)
from app.schemas.medicines import NewMedicationIn  # noqa: E402
from app.schemas.scan import ScanConfirmRequest  # noqa: E402
from app.services.scan_privacy import MaskResult  # noqa: E402


@pytest.fixture()
def db(monkeypatch):
    load_env()
    conn = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    stored = []

    @contextmanager
    def fake_tx():
        yield conn

    monkeypatch.setattr(logstore, "tx", fake_tx)
    monkeypatch.setattr("app.integrations.storage.upload_object", lambda key, data, ctype, settings=None: stored.append(key))
    monkeypatch.setattr(scans, "_unsaved", scans._unsaved.__class__())
    try:
        yield conn, stored
    finally:
        conn.rollback()
        conn.close()


def field(value, conf=0.97):
    return ScoredField(value=value, confidence=conf, model_confidence=conf, source_text=value, needs_confirmation=conf < 0.85)


def outcome(mode="confirm", reasons=(), **over):
    fields = {"name": field("PARACETAMOL"), "strength": field("500 mg"), "dose_amount": field("2"), "times_per_day": field("4"),
              "meal_relation": field("after_meal"), "directions": field("TAKE 2 TAB/S 4 times a day TAKE AFTER FOOD"),
              "start_date": field("2026-04-13"), "total_quantity": field("30")}
    fields.update(over)
    item = ScoredItem(item_type="prescription_label", min_confidence=0.97, fields=fields)
    return ScanOutcome(status="needs_review", review_mode=mode, reasons=list(reasons), items=[item], prompt_version="3", model_id="gemini-3.8-flash",
                       mask_summary={"nric": 1})


def fake_pipeline(monkeypatch, out, photo=b"photo-1"):
    masked = MaskResult(image=b"\xff\xd8" + photo, mime_type="image/jpeg", lines=[], ocr_text="")
    monkeypatch.setattr(scan_pipeline, "run", lambda image, conn, user: (out, masked))


def test_a_clean_scan_is_stored_and_returned_as_confirm(db, monkeypatch):
    conn, stored = db
    fake_pipeline(monkeypatch, outcome())
    r = scans._upload(b"any")
    assert (r.review_mode, r.status.value, r.drug, r.notice) == ("confirm", "extracted", "PARACETAMOL", None)
    assert [f.key for f in r.fields][:3] == ["name", "strength", "dose_amount"] and all(f.level.value == "high" for f in r.fields)
    assert [s.time for s in r.schedule] == ["08:00", "12:00", "16:00", "20:00"]
    assert len(stored) == 1 and stored[0].endswith(".jpg")
    row = conn.execute("select status::text, quality_ok from prescription_scans where id = %s", (r.scan_id,)).fetchone()
    assert row == ("needs_review", True)
    assert scans._get(r.scan_id).drug == "PARACETAMOL"           # the review screen can reload it


def test_confirming_saves_the_checked_values_with_the_chosen_times(db, monkeypatch):
    conn, _ = db
    fake_pipeline(monkeypatch, outcome())
    r = scans._upload(b"any")
    med = scans._confirm(r.scan_id, ScanConfirmRequest(fields={"total_quantity": "28"}, times=["07:30", "12:00", "17:00", "21:00"]))
    assert (med.name, med.times, med.with_food) == ("PARACETAMOL", ["7:30 am", "12:00 pm", "5:00 pm", "9:00 pm"], True)
    assert med.refill is not None and med.refill.units_left <= 28
    row = conn.execute("select total_quantity, source, frequency, start_date from medications where id = %s", (med.id,)).fetchone()
    assert row[:3] == (28, "scan", 4) and str(row[3]) == "2026-04-13"
    assert conn.execute("select status::text from prescription_scans where id = %s", (r.scan_id,)).fetchone() == ("confirmed",)
    with pytest.raises(HTTPException) as e:                       # a second tap does not save a second medicine
        scans._confirm(r.scan_id, ScanConfirmRequest(times=["08:00"]))
    assert e.value.status_code == 409


def test_a_scan_that_needs_typing_cannot_be_confirmed_by_a_tap(db, monkeypatch):
    fake_pipeline(monkeypatch, outcome("manual", ["low_confidence"], strength=field("500 mg", 0.5)))
    r = scans._upload(b"any")
    assert r.review_mode == "manual" and "hard to read" in r.notice and r.reasons == ["low_confidence"]
    with pytest.raises(HTTPException) as e:
        scans._confirm(r.scan_id, ScanConfirmRequest(times=["08:00"]))
    assert e.value.status_code == 409 and "typed in" in e.value.detail


def test_the_typed_form_completes_a_manual_scan(db, monkeypatch):
    conn, _ = db
    fake_pipeline(monkeypatch, outcome("manual", ["low_confidence"], strength=field("500 mg", 0.5)))
    r = scans._upload(b"any")
    body = NewMedicationIn.model_validate({"name": "Zorblaxine", "totalQuantity": 14, "scanId": r.scan_id, "doses": [{"time": "09:00", "quantity": 1}]})
    out = medications.create_medication(conn, str(logstore.current_user()), body)
    assert out.badge is None                       # nothing is matched to a medicine list yet
    assert conn.execute("select status::text from prescription_scans where id = %s", (r.scan_id,)).fetchone() == ("confirmed",)
    assert conn.execute("select source::text from medications where id = %s", (out.id,)).fetchone() == ("scan",)


def test_a_photo_that_was_refused_stores_nothing_but_still_explains(db, monkeypatch):
    conn, stored = db
    monkeypatch.setattr(scan_pipeline, "run", lambda image, conn, user: (ScanOutcome(status="failed", review_mode="manual", reasons=["ocr_empty"]), None))
    before = conn.execute("select count(*) from prescription_scans").fetchone()[0]
    r = scans._upload(b"blank")
    assert r.review_mode == "manual" and r.status.value == "failed" and "text" in r.notice
    assert stored == [] and conn.execute("select count(*) from prescription_scans").fetchone()[0] == before
    assert scans._get(r.scan_id).reasons == ["ocr_empty"]
    with pytest.raises(HTTPException) as e:
        scans._confirm(r.scan_id, ScanConfirmRequest(times=["08:00"]))
    assert e.value.status_code == 409


def test_if_storage_is_down_nothing_pretends_to_be_saved(db, monkeypatch):
    from app.core.errors import ExternalServiceError

    def broken(key, data, ctype, settings=None):
        raise ExternalServiceError("down", code="storage_unavailable")

    monkeypatch.setattr("app.integrations.storage.upload_object", broken)
    fake_pipeline(monkeypatch, outcome())
    r = scans._upload(b"any")
    assert r.review_mode == "manual" and r.reasons == ["service_unavailable"] and r.status.value == "failed"


def test_one_persons_scan_is_not_visible_to_another(db, monkeypatch):
    fake_pipeline(monkeypatch, outcome())
    r = scans._upload(b"any")
    logstore.set_user("mr-tan")
    try:
        with pytest.raises(HTTPException) as e:
            scans._get(r.scan_id)
        assert e.value.status_code == 404
    finally:
        logstore.set_user("demo")


def test_unknown_or_malformed_scan_ids_are_404_not_500(db):
    for bad in ("nope", "00000000-0000-0000-0000-000000000000"):
        with pytest.raises(HTTPException) as e:
            scans._get(bad)
        assert e.value.status_code == 404


def test_the_response_uses_the_names_the_app_reads(db, monkeypatch):
    fake_pipeline(monkeypatch, outcome())
    j = scans._upload(b"any").model_dump(by_alias=True)
    assert {"scanId", "itemType", "reviewMode", "reasons", "notice", "fields", "schedule"} <= set(j)
    assert "sourceText" in j["fields"][0] and j["fields"][0]["level"] in ("high", "check", "unreadable")


def test_an_as_needed_label_is_saved_without_a_dose_time(db, monkeypatch):
    conn, _ = db
    fake_pipeline(monkeypatch, outcome(when_to_take=field("as_needed"), times_per_day=ScoredField(value=None, confidence=0.0, model_confidence=0.0,
                                                                                                  source_text=None, needs_confirmation=False)))
    r = scans._upload(b"any")
    assert r.review_mode == "confirm" and r.as_needed is True and r.schedule == []
    assert "times_per_day" not in [f.key for f in r.fields]
    med = scans._confirm(r.scan_id, ScanConfirmRequest(times=[]))
    assert med.as_needed and med.times == [] and med.refill is None
    assert conn.execute("select dose_time from medication_schedule where medication_id = %s", (med.id,)).fetchall() == [(None,)]
