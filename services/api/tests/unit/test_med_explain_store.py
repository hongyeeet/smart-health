"""The explanation store when migration 0033 (the `parts` column) is not applied yet (the database may be at 0031).

The connection is a small fake that records each statement and answers the column check, so no database is needed.
With the column missing the store must read and write without `parts`, and the explanation shows in the older layout.
"""
import pytest

from app.services import med_explain_store as store


class FakeConn:
    def __init__(self, parts_column: bool, load_row=None):
        self.parts_column = parts_column
        self.load_row = load_row
        self.statements: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.statements.append((sql, tuple(params)))
        return _Result(self._answer(sql))

    def _answer(self, sql):
        if "information_schema.columns" in sql:
            return (self.parts_column,)
        if sql.lstrip().startswith("select status"):
            return self.load_row
        return None

    def queries(self, needle):
        return [s for s, _ in self.statements if needle in s]


class _Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


@pytest.fixture(autouse=True)
def fresh_cache():
    store.reset_parts_cache()
    yield
    store.reset_parts_cache()


def test_without_the_column_the_store_does_not_ask_for_or_write_parts():
    conn = FakeConn(parts_column=False, load_row=("ready", "Old text.", [], "", [], "k", None))
    assert store.parts_column_present(conn) is False
    saved = store.load(conn, "u", "m")
    assert saved["parts"] is None and saved["purpose"] == "Old text."
    assert not any("parts" in s for s in conn.queries("select status"))            # the select leaves parts out
    store.save(conn, "u", "m", status="ready", purpose="x", side_effects=[], tell_doctor="", sources=[], input_key="k", model_id="m",
               prompt_version="2", parts={"for_diabetes": "x"})                     # parts are dropped, the save still works
    insert = conn.queries("insert into medication_explanations")[0]
    assert "parts" not in insert and "generated_at, parts" not in insert


def test_with_the_column_the_store_reads_and_writes_the_four_parts():
    conn = FakeConn(parts_column=True, load_row=("ready", "x", [], "", [], "k", None, {"for_diabetes": "x"}))
    saved = store.load(conn, "u", "m")
    assert saved["parts"] == {"for_diabetes": "x"}
    assert ", parts" in conn.queries("select status")[0]
    store.save(conn, "u", "m", status="ready", purpose="x", side_effects=[], tell_doctor="", sources=[], input_key="k", model_id="m",
               prompt_version="2", parts={"for_diabetes": "x"})
    assert "generated_at, parts" in conn.queries("insert into medication_explanations")[0]


def test_a_missing_column_is_checked_again_next_time_and_a_found_one_is_remembered():
    missing = FakeConn(parts_column=False)
    assert store.parts_column_present(missing) is False
    assert store.parts_column_present(missing) is False
    assert len(missing.queries("information_schema.columns")) == 2                 # not remembered: a later migration is seen

    found = FakeConn(parts_column=True)
    assert store.parts_column_present(found) is True
    assert store.parts_column_present(found) is True
    assert len(found.queries("information_schema.columns")) == 1                   # remembered once it exists


def test_an_old_layout_explanation_is_recognised_so_it_can_be_made_again():
    assert store.is_old_shape({"status": "ready", "parts": None}) is True
    assert store.is_old_shape({"status": "ready", "parts": {"for_diabetes": "x"}}) is False
    assert store.is_old_shape({"status": "not_identified", "parts": None}) is False
    assert store.is_old_shape(None) is False
