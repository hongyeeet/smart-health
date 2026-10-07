"""Saving and confirming a medicine scan against the real schema (prd F2, flow J2).

Every test runs inside a transaction that is rolled back, so the shared database is left untouched. Storage is faked.
Run from services/api:  python -m pytest tests/db/test_scan_store.py -q       Needs DATABASE_URL in the private .env.
"""
import os
import sys
from datetime import time
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_supabase import clean_url  # noqa: E402
from download_data import load_env  # noqa: E402

from app.core.errors import InvalidTransition, NotFound  # noqa: E402
from app.schemas.medicine_scan import (  # noqa: E402
    ConfirmedMedication,
    DoseTime,
    DrugMatch,
    ScanOutcome,
    ScoredField,
    ScoredItem,
)
from app.services import scan_store as store  # noqa: E402
from app.services.scan_privacy import MaskResult  # noqa: E402


@pytest.fixture()
def conn():
    load_env()
    c = psycopg.connect(clean_url(os.environ["DATABASE_URL"]), connect_timeout=20)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


@pytest.fixture()
def user(conn):
    return str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def field(value, conf=0.99):
    return ScoredField(value=value, confidence=conf, model_confidence=conf, source_text=value, needs_confirmation=conf < 0.85)


def outcome(mode="confirm", reasons=()):
    item = ScoredItem(item_type="prescription_label", recognised=True, min_confidence=0.99,
                      drug_match=DrugMatch(drug_reference_id="x", generic_name="metformin", matched_text="metformin", score=100),
                      fields={"name": field("METFORMIN"), "strength": field("500 mg"), "times_per_day": field("2"), "total_quantity": field("60"),
                              "directions": field("Take 1 tablet twice daily after meals")})
    return ScanOutcome(status="needs_review", review_mode=mode, reasons=list(reasons), items=[item], prompt_version="1", model_id="gemini-3.8-flash",
                       input_tokens=3000, output_tokens=300, latency_ms=900, mask_summary={"nric": 1})


def masked(tag=b"a"):
    return MaskResult(image=b"\xff\xd8fake-jpeg-" + tag, mime_type="image/jpeg", lines=[], ocr_text="")


class Uploads:
    def __init__(self):
        self.keys = []

    def __call__(self, key, data, content_type):
        self.keys.append((key, content_type))


def entry(**over):
    base = dict(name="Metformin", kind="prescription", strength="500 mg", directions="Take 1 tablet twice daily after meals", total_quantity=60,
                doses=[DoseTime(dose_time=time(8, 0), quantity=Decimal("1"), meal_relation="after_meal"),
                       DoseTime(dose_time=time(20, 0), quantity=Decimal("1"), meal_relation="after_meal")])
    base.update(over)
    return ConfirmedMedication(**base)


def events(conn, user):
    return [r[0] for r in conn.execute("select event from event_log where user_id = %s order by id", (user,))]


# --- saving the scan ---------------------------------------------------------------------------------------

def test_a_scan_is_stored_with_the_masked_photo_and_logged(conn, user):
    up = Uploads()
    sid = store.save_scan(conn, user, masked(), outcome(), uploader=up)
    s = conn.execute("select status, image_key, model_id, prompt_version, item_type, quality_ok, agent_run_id, extraction from prescription_scans where id = %s", (sid,)).fetchone()
    assert s[0] == "needs_review" and s[2] == "gemini-3.8-flash" and s[3] == "1" and s[4] == "prescription_label" and s[5] is True and s[6] is not None
    assert s[1].startswith(f"{user}/medications/") and up.keys == [(s[1], "image/jpeg")]
    assert s[7]["review_mode"] == "confirm" and s[7]["items"][0]["fields"]["name"]["value"] == "METFORMIN"
    assert one(conn, "select count(*) from bronze_medication where user_id = %s and object_key = %s and source = 'scan' and processing_status = 'processed'", (user, s[1])) == 1
    assert one(conn, "select count(*) from agent_runs where id = %s and agent = 'scan_extractor' and input_tokens = 3000", (s[6],)) == 1
    assert events(conn, user) == ["scan.image.uploaded", "scan.extraction.completed"]


def test_the_same_photo_twice_gives_the_same_scan_and_one_upload(conn, user):
    up = Uploads()
    a = store.save_scan(conn, user, masked(), outcome(), uploader=up)
    b = store.save_scan(conn, user, masked(), outcome(), uploader=up)
    assert a == b and len(up.keys) == 1
    assert one(conn, "select count(*) from prescription_scans where user_id = %s", (user,)) == 1


def test_an_unrecognised_drug_is_logged(conn, user):
    store.save_scan(conn, user, masked(b"u"), outcome("manual", ["unrecognised", "low_confidence"]), uploader=Uploads())
    assert "scan.item.unrecognised" in events(conn, user)


def test_a_failed_read_is_stored_as_failed_with_the_reason(conn, user):
    out = ScanOutcome(status="failed", review_mode="manual", reasons=["not_a_medicine"], prompt_version="1", model_id="m")
    sid = store.save_scan(conn, user, masked(b"f"), out, uploader=Uploads())
    assert conn.execute("select status, error, quality_ok from prescription_scans where id = %s", (sid,)).fetchone() == ("failed", "not_a_medicine", True)


# --- confirming --------------------------------------------------------------------------------------------

def test_confirming_saves_the_medicine_its_schedule_and_the_audit_trail_together(conn, user):
    sid = store.save_scan(conn, user, masked(), outcome(), uploader=Uploads())
    mid = store.confirm_medication(conn, user, entry(strength="500 mg"), scan_id=sid)
    m = conn.execute("select name, kind, strength, frequency, source, description, drug_reference_id, bronze_id from medications where id = %s", (mid,)).fetchone()
    assert m[:6] == ("Metformin", "prescription", "500 mg", 2, "scan", "Take 1 tablet twice daily after meals")
    assert one(conn, "select count(*) from medication_schedule where medication_id = %s and deleted_at is null", (mid,)) == 2
    assert one(conn, "select count(*) from bronze_medication where id = %s and source = 'scan'", (m[7],)) == 1
    assert conn.execute("select status, extraction_review from prescription_scans where id = %s", (sid,)).fetchone()[0] == "confirmed"
    assert events(conn, user)[-3:] == ["scan.confirmed", "medication.created", "dose.schedule.generated"]


def test_what_the_user_changed_is_recorded_per_field(conn, user):
    sid = store.save_scan(conn, user, masked(), outcome(), uploader=Uploads())
    store.confirm_medication(conn, user, entry(strength="850 mg"), scan_id=sid)
    review = conn.execute("select extraction_review from prescription_scans where id = %s", (sid,)).fetchone()[0]
    assert review["fields"]["strength"] == {"scanned": "500 mg", "confirmed": "850 mg", "changed": True}
    assert review["fields"]["name"]["changed"] is True       # "METFORMIN" vs "Metformin": the user typed it differently
    assert review["fields"]["times_per_day"]["changed"] is False
    assert review["changed_count"] == 2


def test_manual_entry_without_a_scan_saves_as_manual(conn, user):
    mid = store.confirm_medication(conn, user, entry(kind="supplement", name="Fish oil", strength=None, directions=None))
    assert conn.execute("select source, kind, strength, drug_reference_id from medications where id = %s", (mid,)).fetchone() == ("manual", "supplement", None, None)
    assert "scan.confirmed" not in events(conn, user) and "medication.created" in events(conn, user)


def test_the_user_can_type_the_form_after_a_failed_read(conn, user):
    out = ScanOutcome(status="failed", review_mode="manual", reasons=["unreadable"], prompt_version="1")
    sid = store.save_scan(conn, user, masked(b"g"), out, uploader=Uploads())
    store.confirm_medication(conn, user, entry(), scan_id=sid)
    assert one(conn, "select status from prescription_scans where id = %s", (sid,)) == "confirmed"


def test_the_drug_list_id_comes_from_a_name_match_in_code(conn, user):
    index = store.load_drug_index(conn)
    mid = store.confirm_medication(conn, user, entry(name="Metformin 500mg"), index=index)
    ref = conn.execute("select r.generic_name from medications m join drug_reference r on r.id = m.drug_reference_id where m.id = %s", (mid,)).fetchone()
    assert ref == ("metformin",)
    mid2 = store.confirm_medication(conn, user, entry(name="Zorblaxine"), index=index)
    assert one(conn, "select drug_reference_id from medications where id = %s", (mid2,)) is None      # not in the list: "not checked"


def test_a_scan_cannot_be_confirmed_twice_or_by_another_user(conn, user):
    sid = store.save_scan(conn, user, masked(), outcome(), uploader=Uploads())
    store.confirm_medication(conn, user, entry(), scan_id=sid)
    with pytest.raises(InvalidTransition):
        store.confirm_medication(conn, user, entry(), scan_id=sid)
    other = str(conn.execute("insert into users (is_demo) values (true) returning id").fetchone()[0])
    sid2 = store.save_scan(conn, user, masked(b"z"), outcome(), uploader=Uploads())
    with pytest.raises(NotFound):
        store.confirm_medication(conn, other, entry(), scan_id=sid2)


def test_a_rejected_scan_cannot_be_confirmed(conn, user):
    sid = store.save_scan(conn, user, masked(), outcome(), uploader=Uploads())
    store.reject_scan(conn, user, sid)
    with pytest.raises(InvalidTransition):
        store.confirm_medication(conn, user, entry(), scan_id=sid)


def test_a_failure_part_way_rolls_back_everything(conn, user, monkeypatch):
    sid = store.save_scan(conn, user, masked(), outcome(), uploader=Uploads())
    real = store._event
    monkeypatch.setattr(store, "_event", lambda c, u, e, *a, **k: (_ for _ in ()).throw(RuntimeError("forced")) if e == "dose.schedule.generated" else real(c, u, e, *a, **k))
    with pytest.raises(RuntimeError):
        with conn.transaction():
            store.confirm_medication(conn, user, entry(), scan_id=sid)
    assert one(conn, "select count(*) from medications where user_id = %s", (user,)) == 0
    assert one(conn, "select count(*) from medication_schedule where user_id = %s", (user,)) == 0
    assert one(conn, "select status from prescription_scans where id = %s", (sid,)) == "needs_review"
    assert "medication.created" not in events(conn, user)


def test_the_confirmed_values_are_not_the_models_values(conn, user):
    """The medicine saved is exactly what the user confirmed, even if the scan read something else."""
    sid = store.save_scan(conn, user, masked(), outcome(), uploader=Uploads())
    mid = store.confirm_medication(conn, user, entry(strength="1000 mg", name="Metformin XR"), scan_id=sid)
    assert conn.execute("select name, strength from medications where id = %s", (mid,)).fetchone() == ("Metformin XR", "1000 mg")


def test_no_identity_is_stored_in_the_scan_or_the_audit_trail(conn, user):
    sid = store.save_scan(conn, user, masked(), outcome(), uploader=Uploads())
    store.confirm_medication(conn, user, entry(), scan_id=sid)
    text = str(conn.execute("select extraction from prescription_scans where id = %s", (sid,)).fetchone()) \
        + str(conn.execute("select payload from event_log where user_id = %s", (user,)).fetchall())
    assert "S1234567D" not in text and "TAN" not in text


# --- the two label columns (migration 0024) ---------------------------------------------------------------------

def test_total_supplied_and_time_of_day_are_saved(conn, user):
    e = entry(total_quantity=30, doses=[DoseTime(dose_time=time(8, 0), quantity=Decimal("2"), meal_relation="after_meal", when_to_take="morning"),
                                       DoseTime(dose_time=time(20, 0), quantity=Decimal("2"), meal_relation="after_meal")])
    mid = store.confirm_medication(conn, user, e)
    assert one(conn, "select total_quantity from medications where id = %s", (mid,)) == 30
    rows = conn.execute("select dose_time, when_to_take from medication_schedule where medication_id = %s order by dose_time", (mid,)).fetchall()
    assert rows == [(time(8, 0), "morning"), (time(20, 0), None)]       # NULL: the label did not name a time of day for that dose


def test_the_time_of_day_stays_null_when_the_label_gives_none(conn, user):
    mid = store.confirm_medication(conn, user, entry())
    assert one(conn, "select total_quantity from medications where id = %s", (mid,)) == 60
    assert one(conn, "select when_to_take from medication_schedule where medication_id = %s limit 1", (mid,)) is None


def test_the_total_supplied_is_required(conn, user):
    with pytest.raises(ValidationError):
        entry(total_quantity=None)
    with pytest.raises(ValidationError):
        entry(total_quantity=0)
    b = conn.execute("insert into bronze_medication (user_id, source, payload, checksum) values (%s, 'manual', '{}'::jsonb, 'x-required') returning id", (user,)).fetchone()[0]
    with pytest.raises(psycopg.errors.NotNullViolation):
        with conn.transaction():
            conn.execute("insert into medications (user_id, name, frequency, source, bronze_id) values (%s, 'x', 1, 'manual', %s)", (user, b))


def test_the_database_rejects_bad_label_values(conn, user):
    mid = store.confirm_medication(conn, user, entry())
    for sql in ("update medications set total_quantity = -1 where id = %s",
                "update medication_schedule set when_to_take = 'whenever' where medication_id = %s"):
        try:
            with conn.transaction():
                conn.execute(sql, (mid,))
        except psycopg.errors.CheckViolation:
            continue
        raise AssertionError(f"not rejected: {sql}")


def test_the_review_records_a_change_to_the_new_fields(conn, user):
    sid = store.save_scan(conn, user, masked(b"q"), outcome(), uploader=Uploads())
    store.confirm_medication(conn, user, entry(total_quantity=90), scan_id=sid)
    review = conn.execute("select extraction_review from prescription_scans where id = %s", (sid,)).fetchone()[0]
    assert review["fields"]["total_quantity"] == {"scanned": "60", "confirmed": "90", "changed": True}
