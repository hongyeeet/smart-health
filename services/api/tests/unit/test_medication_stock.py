"""The medicine warehouse rules (app/services/medication_stock.py): days left, the status thresholds, the decrement and the restore,
never below 0, as-needed medicines left out, and the "stock tracking is being set up" path. No database here: see tests/db/test_medication_stock.py.
"""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.routers import med_stock
from app.api.routers.medications import refill_with_stock
from app.core.errors import ValidationFailed
from app.schemas.med_stock import StockIn
from app.schemas.medicines import Refill
from app.services import medication_stock as ms

D = Decimal


# ------------------------------------------------------------------ days left and status
@pytest.mark.parametrize("stock, per_day, days", [
    (D(60), D(2), 30),          # 60 tablets, two a day
    (D(15), D(4), 3),           # 15 / 4 = 3.75 days: whole days, rounded down
    (D("0.5"), D(1), 0),        # half a tablet left
    (D(0), D(2), 0),            # none left
    (D(30), D(0), None),        # no doses per day: unknown, never a guess
    (None, D(2), None),         # the count is not set: unknown
])
def test_days_left_is_the_count_over_doses_per_day_in_whole_days(stock, per_day, days):
    assert ms.days_left_of(stock, per_day) == days


@pytest.mark.parametrize("stock, days, status", [
    (None, None, "unknown"),        # not set yet
    (None, 5, "unknown"),           # not set yet, even with days (cannot happen, but the rule holds)
    (D(0), 0, "out"),               # nothing left
    (D(0), None, "out"),            # nothing left, whatever the schedule says
    (D("0.5"), 0, "low"),           # some left, under a day: low, not out
    (D(14), 7, "low"),              # 7 days or fewer is low
    (D(8), 1, "low"),
    (D(16), 8, "ok"),               # 8 days is not low
    (D(30), None, "unknown"),       # a count with no doses per day cannot say how many days
])
def test_status_thresholds(stock, days, status):
    assert ms.status_of(stock, days) == status


def test_the_low_stock_threshold_is_one_named_constant_of_seven_days():
    assert ms.LOW_STOCK_DAYS == 7


# ------------------------------------------------------------------ decrement and restore
def test_a_taken_dose_takes_its_amount_off_the_count():
    assert ms.count_after_dose(D(60), ms.dose_amount(D(2)), as_needed=False) == D(58)


def test_a_dose_with_no_amount_takes_one_unit_and_that_is_the_only_default():
    assert ms.dose_amount(None) == D(1)
    assert ms.dose_amount(D(0)) == D(1)
    assert ms.dose_amount(D("1.5")) == D("1.5")


def test_the_count_never_goes_below_zero():
    assert ms.count_after_dose(D("0.5"), D(1), as_needed=False) == D(0)
    assert ms.count_after_dose(D(0), D(1), as_needed=False) == D(0)


def test_no_count_set_means_nothing_changes_it_is_not_taken_as_zero():
    assert ms.count_after_dose(None, D(1), as_needed=False) is None
    assert ms.count_after_untake(None, D(1), as_needed=False) is None


def test_an_as_needed_medicine_is_never_changed_by_a_dose():
    assert ms.count_after_dose(D(20), D(1), as_needed=True) is None
    assert ms.count_after_untake(D(20), D(1), as_needed=True) is None


def test_taking_a_dose_back_adds_back_exactly_what_it_took():
    taken = ms.count_after_dose(D(10), D("0.5"), as_needed=False)
    assert taken == D("9.5")
    assert ms.count_after_untake(taken, D("0.5"), as_needed=False) == D(10)


def test_a_restore_is_capped_at_the_largest_allowed_count():
    assert ms.count_after_untake(D(9999), D(5), as_needed=False) == ms.MAX_COUNT


def test_a_count_typed_in_must_be_from_0_to_10000():
    assert ms.check_amount(D(0)) == D(0)
    assert ms.check_amount(D(10000)) == D(10000)
    for bad in (D(-1), D(10001), D("NaN"), D("Infinity")):
        with pytest.raises(ValidationFailed):
            ms.check_amount(bad)


def test_the_unit_word_follows_the_label_of_the_dose():
    assert ms.stock_unit_for("Tab") == "tablets"
    assert ms.stock_unit_for("Capsule") == "capsules"
    assert ms.stock_unit_for("Something new") == "doses"


# ------------------------------------------------------------------ the refill figure: stock first, the old estimate otherwise
def test_when_the_stock_is_set_the_refill_figure_comes_from_it_not_the_pack_date():
    estimate = Refill(days_left=3, units_left=6)
    refill, source = refill_with_stock(D(40), D(2), estimate)
    assert (refill.days_left, refill.units_left, source) == (20, 40, "stock")


def test_when_the_stock_is_not_set_the_old_estimate_is_used_and_labelled_as_such():
    estimate = Refill(days_left=6, units_left=12)
    assert refill_with_stock(None, D(2), estimate) == (estimate, "estimate")
    assert refill_with_stock(None, D(2), None) == (None, None)


def test_a_count_with_no_doses_per_day_gives_no_figure():
    assert refill_with_stock(D(40), D(0), Refill(days_left=3, units_left=6)) == (None, None)


def test_a_zero_count_is_a_real_figure_of_zero_days_not_a_missing_one():
    refill, source = refill_with_stock(D(0), D(2), None)
    assert (refill.days_left, refill.units_left, source) == (0, 0, "stock")


# ------------------------------------------------------------------ the request shapes
def test_a_change_is_either_add_or_set_never_both_and_never_neither():
    assert StockIn.model_validate({"add": 30}).add == D(30)
    assert StockIn.model_validate({"set": 12}).set_count == D(12)
    with pytest.raises(ValidationError):
        StockIn.model_validate({"add": 1, "set": 2})
    with pytest.raises(ValidationError):
        StockIn.model_validate({})


@pytest.mark.parametrize("body", [{"add": -1}, {"set": 10001}, {"set": "many"}])
def test_a_number_outside_0_to_10000_is_refused(body):
    with pytest.raises(ValidationError):
        StockIn.model_validate(body)


def test_zero_and_the_largest_number_are_allowed():
    assert StockIn.model_validate({"set": 0}).set_count == D(0)
    assert StockIn.model_validate({"add": 10000}).add == D(10000)


# ------------------------------------------------------------------ stock tracking not applied yet: no 500s
class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _Conn:
    """Answers the one query stock_ready makes: how many of the three stock columns exist."""
    def __init__(self, count):
        self.count = count

    def execute(self, sql, params=()):
        assert "information_schema.columns" in sql
        return _Result((self.count,))


def test_stock_is_not_ready_until_all_three_columns_exist(monkeypatch):
    monkeypatch.setattr(ms, "_ready", False)
    assert ms.stock_ready(_Conn(0)) is False
    assert ms._ready is False                       # a 'not yet' is checked again on the next call
    assert ms.stock_ready(_Conn(3)) is True
    ms.reset_stock_cache()
    assert ms._ready is False


def test_the_list_says_not_ready_with_no_items_and_the_change_is_refused_with_a_503(monkeypatch):
    """The routes answer with the plain sentence, not a 500, while the columns are missing."""
    class Tx:
        def __enter__(self):
            return _Conn(0)

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(med_stock.logstore, "tx", lambda: Tx())
    monkeypatch.setattr(ms, "_ready", False)
    listed = med_stock._stock()
    assert listed.ready is False and listed.items == []
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        med_stock._change("6f1c2d3e-4a5b-4c6d-8e7f-9a0b1c2d3e4f", StockIn.model_validate({"add": 1}))
    assert e.value.status_code == 503 and e.value.detail == ms.NOT_READY


def test_a_medicine_id_that_is_not_an_id_is_not_found_not_an_error():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        med_stock._change("not-an-id", StockIn.model_validate({"set": 3}))
    assert e.value.status_code == 404


def test_a_status_row_becomes_the_api_shape_with_the_unit_and_no_zero_for_unset(monkeypatch):
    row = {"id": "6f1c2d3e-4a5b-4c6d-8e7f-9a0b1c2d3e4f", "name": "Metformin", "strength": None, "kind": "prescription", "description": "Take 1 tab",
           "pack_size": 60, "stock_count": None, "stock_unit": None, "updated_at": None, "per_day": D(2), "days_left": None,
           "status": "unknown", "full_count": None}
    out = med_stock._out(row)
    assert out.stock_count is None and out.stock_unit is None and out.status == "unknown"       # not set: no number, no unit
    assert out.strength == "Strength not entered" and out.pack_size == 60
    row.update(stock_count=D(58), stock_unit=None, days_left=29, status="ok", full_count=D(60))
    out = med_stock._out(row)
    assert (out.stock_count, out.stock_unit, out.days_left, out.full_count) == (58.0, "tablets", 29, 60.0)
