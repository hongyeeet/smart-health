"""The add screens' scope note (implementation-plan section 4.2): a name outside the drug list gets a gentle note, never a block.

The database is replaced by a small fake: the list is read with two queries, generic names and aliases.
"""
from app.services import medicine_scope as scope


class FakeConn:
    def __init__(self, generics, aliases):
        self.generics, self.aliases = generics, aliases

    def execute(self, sql):
        rows = self.generics if "drug_reference" in sql else self.aliases
        return _Rows([(r,) for r in rows])


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


CONN = FakeConn(generics=["metformin", "glimepiride", "sitagliptin"], aliases=["glucophage"])


def test_a_listed_generic_name_is_found_even_with_strength_and_wording_around_it():
    assert scope.is_listed("Metformin 500 mg", ["metformin"]) is True
    assert scope.is_listed("METFORMIN HCL tablets", ["metformin"]) is True


def test_a_brand_name_without_its_generic_is_not_listed_and_a_longer_word_does_not_match():
    assert scope.is_listed("Crestor 10 mg", ["metformin", "rosuvastatin"]) is False
    assert scope.is_listed("Metformins", ["metformin"]) is False


def test_very_short_terms_are_ignored_so_they_cannot_match_by_accident():
    assert scope.is_listed("Asp 100", ["asp"]) is False


def test_an_alias_on_the_list_counts_as_listed():
    assert scope.out_of_scope(CONN, "Glucophage 500", "prescription") is False


def test_an_unlisted_medicine_is_a_gentle_note_not_a_block():
    assert scope.out_of_scope(CONN, "Amlodipine 5 mg", "prescription") is True
    assert scope.out_of_scope(CONN, "Amoxicillin 500 mg", "otc") is True


def test_supplements_and_herbal_products_are_never_out_of_scope():
    assert scope.out_of_scope(CONN, "Fish oil 1000 mg", "supplement") is False
    assert scope.out_of_scope(CONN, "Herbal tonic", "tcm") is False


def test_an_empty_name_is_not_out_of_scope():
    assert scope.out_of_scope(CONN, "   ", "prescription") is False
