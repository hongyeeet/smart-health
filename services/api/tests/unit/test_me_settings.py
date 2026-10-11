"""Me settings (K5, K6, K8, K9): validation, the export shape, the deletion promise, and the SQL choices made with a fake connection.

No database here. The fake connection answers the few queries the service makes, so the tests check which columns are written and
which event is recorded, not the SQL text as a whole.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from app.services import me_settings as M

USER = UUID("dc48e209-5731-5b3d-89d9-986242c54368")
NOW = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _fresh_column_cache():
    M.reset_column_cache()
    yield
    M.reset_column_cache()


class Cur:
    def __init__(self, rows=(), rowcount=0):
        self.rows = list(rows)
        self.rowcount = rowcount

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class FakeConn:
    """Routes each SQL statement to a handler by a fragment of its text, and keeps every statement for the asserts."""

    def __init__(self, handlers=None):
        self.handlers = handlers or {}
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.calls.append((" ".join(sql.split()), tuple(params)))
        for fragment, handler in self.handlers.items():
            if fragment in sql:
                return handler(params)
        return Cur()

    def statements(self, fragment):
        return [(s, p) for s, p in self.calls if fragment in s]


def columns_handler(names):
    return lambda _p: Cur([{"column_name": n} for n in names])


PROFILE_COLS = ("emergency_contact_name", "emergency_contact_relation", "emergency_contact_phone")


# ───────────────────────────────────────────────────────────── phone and email
@pytest.mark.parametrize("raw, want", [("+6598765432", "+6598765432"), ("+65 5550 0142", "+6555500142"), ("91234567", "91234567"), ("", None), (None, None), ("   ", None)])
def test_phone_accepts_digits_with_optional_plus(raw, want):
    assert M.clean_phone(raw) == want


@pytest.mark.parametrize("raw", ["+", "12345", "1234567890123456", "+65-abc-1234", "65 (555)", "++6598765432"])
def test_phone_rejects_everything_else(raw):
    with pytest.raises(ValueError):
        M.clean_phone(raw)


@pytest.mark.parametrize("raw", ["mei@example.com", " mei.lim@gmail.com "])
def test_email_accepts_a_plain_address(raw):
    assert M.clean_email(raw) == raw.strip()


@pytest.mark.parametrize("raw", ["mei", "mei@", "@example.com", "mei lim@example.com", "mei@example", "a" * 250 + "@x.com"])
def test_email_rejects_what_does_not_look_like_one(raw):
    with pytest.raises(ValueError):
        M.clean_email(raw)


# ───────────────────────────────────────────────────────────── contact rules
def test_empty_contact_is_allowed_and_clears_the_saved_one():
    assert M.clean_contact("  ", "", None, "") == {"name": None, "relation": None, "phone": None, "email": None}


def test_contact_with_name_and_phone_is_cleaned():
    got = M.clean_contact(" Mdm Lim ", "spouse", "+65 5550 0142", None)
    assert got == {"name": "Mdm Lim", "relation": "spouse", "phone": "+6555500142", "email": None}


def test_contact_with_name_and_email_only_is_enough():
    assert M.clean_contact("Mei", None, None, "mei@example.com")["email"] == "mei@example.com"


@pytest.mark.parametrize(
    "args",
    [
        (None, "spouse", "91234567", None),        # no name
        ("Mei", "spouse", None, None),             # name but no way to reach them
        (None, None, None, "mei@example.com"),     # email but no name
        (None, "spouse", None, None),              # relation alone
    ],
)
def test_contact_needs_a_name_and_a_phone_or_email(args):
    with pytest.raises(ValueError):
        M.clean_contact(*args)


# ───────────────────────────────────────────────────────────── export and promise
def test_export_counts_match_the_sections_in_the_file():
    sections = {"meals": [{"food": "rice"}, {"food": "fish"}], "workouts": [], "doses": [{"status": "taken"}]}
    out = M.build_export(None, sections, [], NOW)
    assert out["counts"] == {"meals": 2, "workouts": 0, "doses": 1}
    assert out["meals"] == sections["meals"] and out["profile"] is None
    assert out["exported_at"] == NOW.isoformat() and out["format"] == "smart-health-export"


def test_plain_turns_money_dates_and_ids_into_json_values():
    row = M._plain({"n": Decimal("6.50"), "at": NOW, "d": NOW.date(), "id": UUID(int=1), "t": None})
    assert row == {"n": 6.5, "at": NOW.isoformat(), "d": "2026-10-10", "id": str(UUID(int=1)), "t": None}


def test_deletion_is_promised_within_thirty_days():
    assert M.deletion_promise(NOW) == NOW + timedelta(days=30)


def test_every_export_query_is_limited_to_the_person():
    for name, sql in M.EXPORT_SECTIONS.items():
        assert "user_id=%s" in sql, name
        assert sql.count("%s") == 1, name


# ───────────────────────────────────────────────────────────── language
def test_language_defaults_to_english_without_a_profile():
    conn = FakeConn({"select language": lambda p: Cur()})
    assert M.get_language(conn, USER) == "en"


def test_saving_language_without_a_profile_says_setup_is_needed():
    conn = FakeConn({"update user_profile set language": lambda p: Cur(rowcount=0)})
    with pytest.raises(M.ProfileMissing):
        M.set_language(conn, USER, "zh")


# ───────────────────────────────────────────────────────────── consents
def test_grant_inserts_a_row_and_logs_the_event():
    conn = FakeConn({
        "select id from consents": lambda p: Cur(),
        "insert into consents": lambda p: Cur([{"id": UUID(int=7)}]),
        "from consents where user_id": lambda p: Cur(),
    })
    M.set_consent(conn, USER, "brief_sharing", True)
    inserts = conn.statements("insert into consents")
    assert len(inserts) == 1 and inserts[0][1][1] == "brief_sharing" and inserts[0][1][2] == M.CONSENT_VERSION
    events = conn.statements("insert into event_log")
    assert len(events) == 1 and "consent.granted" in events[0][1]


def test_revoke_sets_revoked_at_and_keeps_the_row():
    conn = FakeConn({
        "select id from consents": lambda p: Cur([{"id": UUID(int=9)}]),
        "from consents where user_id": lambda p: Cur(),
    })
    M.set_consent(conn, USER, "research_use", False)
    assert conn.statements("update consents set revoked_at")
    assert not conn.statements("delete from consents")
    events = conn.statements("insert into event_log")
    assert len(events) == 1 and "consent.revoked" in events[0][1]


def test_setting_the_same_state_again_writes_nothing():
    conn = FakeConn({
        "select id from consents": lambda p: Cur([{"id": UUID(int=9)}]),
        "from consents where user_id": lambda p: Cur(),
    })
    M.set_consent(conn, USER, "brief_sharing", True)
    assert not conn.statements("insert into consents") and not conn.statements("insert into event_log")


def test_list_shows_each_kind_once_and_the_history_newest_first():
    old = {"kind": "data_processing", "version": "v1", "granted_at": NOW - timedelta(days=30), "revoked_at": NOW - timedelta(days=10)}
    now_row = {"kind": "data_processing", "version": "v1", "granted_at": NOW - timedelta(days=5), "revoked_at": None}
    conn = FakeConn({"from consents where user_id": lambda p: Cur([now_row, old])})
    got = M.list_consents(conn, USER)
    assert [c["kind"] for c in got["consents"]] == list(M.KINDS)
    dp = got["consents"][0]
    assert dp["granted"] is True and dp["granted_at"] == now_row["granted_at"]
    assert got["consents"][1]["granted"] is False
    assert [h["revoked_at"] for h in got["history"]] == [None, old["revoked_at"]]


# ───────────────────────────────────────────────────────────── deletion request (K8)
def test_deletion_needs_the_word_delete_typed_in_capitals():
    conn = FakeConn()
    with pytest.raises(ValueError):
        M.request_deletion(conn, USER, "delete")
    assert not conn.calls


def test_deletion_request_is_recorded_not_carried_out():
    conn = FakeConn({"event_log where user_id": lambda p: Cur(), "insert into event_log": lambda p: Cur([{"occurred_at": NOW}])})
    got = M.request_deletion(conn, USER, "DELETE")
    assert got == {"status": "received", "requested_at": NOW, "process_by": NOW + timedelta(days=30)}
    assert len(conn.statements("insert into event_log")) == 1 and "'account.deletion.requested'" in conn.statements("insert into event_log")[0][0]
    assert not conn.statements("delete ") and not conn.statements("update users") and not conn.statements("update medications")


def test_a_second_deletion_request_does_not_add_a_row():
    earlier = NOW - timedelta(days=2)
    conn = FakeConn({"event_log where user_id": lambda p: Cur([{"occurred_at": earlier}])})
    got = M.request_deletion(conn, USER, "DELETE")
    assert got["requested_at"] == earlier
    assert not conn.statements("insert into event_log")


# ───────────────────────────────────────────────────────────── emergency contact (K9), with and without the email column
def contact_handlers(columns, stored=None):
    stored = stored or {}
    row = {c: stored.get(c) for c in PROFILE_COLS + (("emergency_contact_email",) if "emergency_contact_email" in columns else ())}
    return {
        "information_schema.columns": columns_handler(columns),
        "update user_profile set emergency": lambda p: Cur(rowcount=1),
        "select emergency_contact_name": lambda p: Cur([row]),
    }


def test_save_without_the_email_column_writes_name_relation_and_phone_only():
    conn = FakeConn(contact_handlers(columns=list(PROFILE_COLS)))
    got = M.save_contact(conn, USER, "Mdm Lim", "spouse", "+65 5550 0142", None)
    update = conn.statements("update user_profile set emergency")[0][0]
    assert "emergency_contact_email" not in update and "emergency_contact_phone=%s" in update
    assert got["email_supported"] is False and got["email"] is None


def test_save_with_an_email_but_no_column_is_refused_with_a_reason():
    conn = FakeConn(contact_handlers(columns=list(PROFILE_COLS)))
    with pytest.raises(M.EmailNotSupported):
        M.save_contact(conn, USER, "Mdm Lim", "spouse", "91234567", "lim@example.com")
    assert not conn.statements("update user_profile")


def test_save_with_the_email_column_writes_it_too():
    cols = list(PROFILE_COLS) + ["emergency_contact_email"]
    conn = FakeConn(contact_handlers(columns=cols, stored={"emergency_contact_email": "lim@example.com", "emergency_contact_name": "Mdm Lim"}))
    got = M.save_contact(conn, USER, "Mdm Lim", "spouse", None, "lim@example.com")
    update = conn.statements("update user_profile set emergency")[0][0]
    assert "emergency_contact_email=%s" in update
    assert got["email_supported"] is True and got["email"] == "lim@example.com"


def test_saving_a_contact_without_a_profile_row_says_setup_is_needed():
    cols = list(PROFILE_COLS)
    handlers = contact_handlers(columns=cols)
    handlers["update user_profile set emergency"] = lambda p: Cur(rowcount=0)
    conn = FakeConn(handlers)
    with pytest.raises(M.ProfileMissing):
        M.save_contact(conn, USER, "Mdm Lim", "spouse", "91234567", None)


def test_column_check_runs_once_and_is_cached():
    conn = FakeConn({"information_schema.columns": columns_handler(list(PROFILE_COLS))})
    M.has_contact_email(conn)
    M.has_contact_email(conn)
    assert len(conn.statements("information_schema.columns")) == 1


def test_a_contact_with_a_bad_phone_is_refused_before_any_write():
    conn = FakeConn(contact_handlers(columns=list(PROFILE_COLS)))
    with pytest.raises(ValueError):
        M.save_contact(conn, USER, "Mdm Lim", "spouse", "12", None)
    assert not conn.statements("update user_profile")


# ───────────────────────────────────────────────────────────── withdrawing consent to share stops the live links
def test_revoking_brief_sharing_also_revokes_the_live_share_links():
    conn = FakeConn({"from consents where user_id=%s and kind=%s": lambda p: Cur([{"id": "c1"}]),
                     "update brief_shares set revoked_at": lambda p: Cur(rowcount=2)})
    M.set_consent(conn, "u1", "brief_sharing", False)
    assert conn.statements("update brief_shares set revoked_at")                      # the links were switched off
    assert any("brief.shares_revoked_with_consent" in str(p) for _s, p in conn.statements("insert into event_log"))


def test_revoking_another_consent_leaves_share_links_alone():
    conn = FakeConn({"from consents where user_id=%s and kind=%s": lambda p: Cur([{"id": "c1"}])})
    M.set_consent(conn, "u1", "research_use", False)
    assert not conn.statements("update brief_shares")


def test_the_demo_patient_profile_is_protected():
    import uuid
    import pytest
    from fastapi import HTTPException
    from app.api.guards import MR_TAN, not_the_demo_patient
    with pytest.raises(HTTPException) as e:
        not_the_demo_patient(MR_TAN)
    assert e.value.status_code == 409
    not_the_demo_patient(uuid.uuid4())                                                   # anyone else is fine


# ───────────────────────────────────────────────────────────── the export's new sections (what the app stores about the person)
from app.services import blood_pressure as BP  # noqa: E402

NEW_SECTIONS = ("blood_pressure", "body_measurements", "conditions", "allergies", "devices", "lab_results", "medicine_stock",
                "doctor_questions", "appointments")
ONBOARDING_PROFILE = ("diagnosed_year", "care_setting", "healthier_sg", "hypo_last_3m", "hypo_symptoms")


def schema_handler(tables):
    """information_schema.columns: the columns of the table named in the first parameter (empty when the table is not in `tables`)."""
    return lambda params: Cur([{"column_name": c} for c in tables.get(params[0], ())])


def all_tables():
    tables = {table: needs for (table, needs, _s) in M.EXTRA_SECTIONS.values()}
    tables["user_profile"] = tuple(M.PROFILE_COLUMNS) + M.OPTIONAL_PROFILE_COLUMNS
    tables["blood_pressure_readings"] = ("user_id", "recorded_at", "systolic_mmhg", "diastolic_mmhg", "deleted_at")
    return tables


def export_conn(tables, rows_by_fragment=None):
    handlers = {"information_schema.columns": schema_handler(tables), "from user_profile where user_id": lambda p: Cur([{"display_name": "Mr Tan", "diagnosed_year": 2019}])}
    handlers.update({frag: (lambda rows: (lambda p: Cur(rows)))(rows) for frag, rows in (rows_by_fragment or {}).items()})
    return FakeConn(handlers)


def test_every_extra_query_is_limited_to_the_person_and_to_live_rows():
    for name, (table, needs, sql) in M.EXTRA_SECTIONS.items():
        assert sql.count("%s") == 1 and "user_id=%s" in sql, name
        assert table in sql, name
        if name == "doctor_questions":
            assert "status <> 'archived'" in sql and "deleted_at" not in sql, name
        elif name == "appointments":   # a visit is closed by its status (cancelled), not by deleted_at: every status is kept
            assert "deleted_at" not in sql, name
        else:
            assert "deleted_at is null" in sql, name


def test_export_adds_every_new_section_with_its_rows_and_counts(monkeypatch):
    readings = [  # newest first, as recent_bp returns them
        {"id": "b-2", "measured_at": NOW, "systolic": 128, "diastolic": 82, "pulse": 70, "note": "after a walk"},
        {"id": "b-1", "measured_at": NOW - timedelta(days=1), "systolic": 118, "diastolic": 76, "pulse": None, "note": None},
    ]
    seen = []
    monkeypatch.setattr(BP, "recent_bp", lambda conn, user, days: seen.append((user, days)) or readings)
    rows = {
        "from body_measurements": [{"measured_at": NOW, "weight_kg": Decimal("62.5"), "waist_cm": Decimal("88.0"), "source": "onboarding"}],
        "from conditions": [{"name": "High blood pressure", "code": "hbp", "source": "onboarding", "created_at": NOW}],
        "from allergies": [{"substance": "Penicillin", "reaction": "rash", "source": "onboarding", "created_at": NOW}],
        "from devices": [{"kind": "watch", "label": "Apple Watch", "status": None, "source": "onboarding", "created_at": NOW}],
        "from lab_results": [{"test": "hba1c", "value": Decimal("7.2"), "unit": "%", "measured_at": NOW, "source": "file_import"}],
        "from medications": [{"medicine": "Metformin", "stock_count": Decimal("24"), "stock_unit": "tablets", "stock_updated_at": NOW}],
        "from doctor_questions": [{"text": "Can I stop the gliclazide?", "origin": "user", "status": "open", "created_at": NOW}],
        "from appointments": [{"kind": "gp", "status": "planned", "scheduled_for": NOW, "location": None, "suggested_reason": {"due": "overdue"},
                               "confirmed_by_user_at": NOW, "created_at": NOW}],
    }
    conn = export_conn(all_tables(), rows)
    out = M.export_for(conn, USER, NOW)
    for key in NEW_SECTIONS:
        assert isinstance(out[key], list), key
        assert out["counts"][key] == len(out[key]), key
    assert seen == [(USER, M.ALL_READINGS_DAYS)]
    assert [r["systolic"] for r in out["blood_pressure"]] == [118, 128]           # oldest first, like the other sections
    assert out["blood_pressure"][1] == {"measured_at": NOW.isoformat(), "systolic": 128, "diastolic": 82, "pulse": 70, "note": "after a walk"}
    assert all("id" not in r for r in out["blood_pressure"])
    assert out["body_measurements"][0]["weight_kg"] == 62.5 and out["body_measurements"][0]["waist_cm"] == 88.0
    assert out["medicine_stock"][0]["stock_count"] == 24.0 and out["medicine_stock"][0]["medicine"] == "Metformin"
    assert out["lab_results"][0]["value"] == 7.2 and out["lab_results"][0]["source"] == "file_import"


def test_onboarding_answers_are_in_the_profile_part_of_the_export(monkeypatch):
    monkeypatch.setattr(BP, "recent_bp", lambda conn, user, days: [])
    conn = export_conn(all_tables())
    out = M.export_for(conn, USER, NOW)
    assert out["profile"]["diagnosed_year"] == 2019
    (profile_sql, _), = conn.statements("from user_profile where user_id")
    for col in ONBOARDING_PROFILE:
        assert col in profile_sql


def test_a_new_empty_person_gets_empty_lists_for_every_new_section(monkeypatch):
    monkeypatch.setattr(BP, "recent_bp", lambda conn, user, days: [])
    out = M.export_for(export_conn(all_tables()), UUID(int=99), NOW)
    assert all(out[key] == [] and out["counts"][key] == 0 for key in NEW_SECTIONS)


def test_a_missing_table_or_column_gives_an_empty_section_and_no_query(monkeypatch):
    tables = all_tables()
    del tables["conditions"]                       # table not there (before migration 0032)
    tables["doctor_questions"] = ("text", "origin", "created_at")   # no status column
    monkeypatch.setattr(BP, "recent_bp", lambda conn, user, days: (_ for _ in ()).throw(AssertionError("must not be read")))
    tables.pop("blood_pressure_readings")
    conn = export_conn(tables, {"from conditions": [{"name": "x"}], "from doctor_questions": [{"text": "x"}]})
    out = M.export_for(conn, USER, NOW)
    assert out["conditions"] == [] and out["doctor_questions"] == [] and out["blood_pressure"] == []
    assert not conn.statements("from conditions") and not conn.statements("from doctor_questions")
    assert out["counts"]["conditions"] == 0


def test_a_table_that_appears_later_is_read_without_a_restart():
    # an empty answer from information_schema is not cached, so a later migration shows up on the next export
    conn = FakeConn({"information_schema.columns": lambda p: Cur()})
    assert M._columns(conn, "conditions") == frozenset()
    conn.handlers["information_schema.columns"] = schema_handler({"conditions": ("name", "deleted_at")})
    assert M._columns(conn, "conditions") == frozenset({"name", "deleted_at"})
