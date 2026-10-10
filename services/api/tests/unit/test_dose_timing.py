"""Dose-time reminders: the window test, the offset choice, the prior from history, the success and miss rules, and the planning of
reminders (no database, no network). Both sides of the 7 and 14 usable-delay thresholds are tested."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.agents import dose_timing as D
from app.db import logstore

TZ = ZoneInfo("Asia/Singapore")
DAY = date(2026, 10, 9)
MED_A = "11111111-1111-1111-1111-111111111111"
MED_B = "22222222-2222-2222-2222-222222222222"
CREATED = datetime(2026, 1, 1, tzinfo=TZ)


def at(hh, mm=0):
    return datetime.combine(DAY, time(hh, mm), tzinfo=TZ)


def ident(*args):
    """A rank that keeps the given order: takes (keys) for choose_offset or (seed, keys) for plan."""
    return list(args[-1])


def sched(mid=MED_A, sid="s-a", t=time(20, 0), name="Metformin", strength="500 mg", directions=None, meal=None, end=None):
    return {"sid": sid, "mid": mid, "dose_time": t, "created_at": CREATED, "name": name, "strength": strength,
            "directions": directions, "meal": meal, "end_date": end}


def slots_for(*rows):
    return D.make_slots(rows, [DAY])


def run_plan(slots, now, logs=None, notes=None, tries=None, delays=None, have=None, max_new=99):
    return D.plan(slots, logs or {}, notes or {}, tries or {}, delays or {}, have or set(), now, ident, max_new)


def fifteen_delays(n, minutes=25):
    return [float(minutes)] * n


# ───────────────────────────────────────────────────────────────── the window
def test_window_opens_at_dose_time_and_closes_60_minutes_later():
    t = at(20)
    assert not D.in_window(t, t - timedelta(minutes=1))
    assert D.in_window(t, t)
    assert D.in_window(t, t + timedelta(minutes=60))
    assert not D.in_window(t, t + timedelta(minutes=61))
    assert D.window_end(t) == t + timedelta(minutes=60)


def test_only_untaken_slots_are_open():
    assert D.is_open(None) and D.is_open("pending")
    assert not D.is_open("taken") and not D.is_open("missed")


def test_as_needed_and_ended_medicines_get_no_slots():
    assert slots_for(sched(t=None)) == []                                          # as needed: no dose time
    assert slots_for(sched(end=DAY - timedelta(days=1))) == []                     # ended yesterday
    assert len(slots_for(sched(end=DAY))) == 1                                     # ends today: still due today
    early = dict(sched(), created_at=datetime(2026, 10, 9, 21, 0, tzinfo=TZ))
    assert slots_for(early) == []                                                  # the 20:00 dose was before the medicine existed


# ───────────────────────────────────────────────────────────────── the person's own history
def test_taken_doses_give_delays_but_took_it_and_early_do_not():
    s = at(20)
    pairs = [(s, s + timedelta(minutes=25)), (s, s), (s, s - timedelta(minutes=5)), (s, None)]
    assert D.usable_delays(pairs) == [25.0]


def test_prior_needs_seven_usable_delays_and_fact_needs_fourteen():
    assert len(fifteen_delays(6)) < D.PRIOR_MIN_DOSES
    assert len(fifteen_delays(7)) >= D.PRIOR_MIN_DOSES
    assert not D.has_fact_history(fifteen_delays(13))
    assert D.has_fact_history(fifteen_delays(14))


def test_history_keeps_the_most_recent_thirty():
    s = at(20)
    pairs = [(s - timedelta(days=i), s - timedelta(days=i) + timedelta(minutes=10)) for i in range(40)]
    assert len(D.usable_delays(pairs)) == D.PRIOR_HISTORY


def test_preferred_offset_is_nearest_to_median_minus_ten():
    assert D.preferred_offset(25) == 15      # 25 - 10 = 15
    assert D.preferred_offset(40) == 30      # 40 - 10 = 30
    assert D.preferred_offset(5) == 0        # target -5 is closest to 0
    assert D.preferred_offset(200) == 45     # clamped to the menu


def test_usual_delay_is_rounded_to_five_minutes_and_never_zero():
    assert D.usual_rounded(21) == 20
    assert D.usual_rounded(23) == 25
    assert D.usual_rounded(1) == 5


# ───────────────────────────────────────────────────────────────── the offset choice
def test_below_seven_doses_starts_at_zero_and_explores_evenly():
    assert D.choose_offset(MED_A, fifteen_delays(6), set(), {}, ident) == 0
    assert D.choose_offset(MED_A, fifteen_delays(6), set(), {f"{MED_A}:0": 1}, ident) == 15
    assert D.choose_offset(MED_A, [], set(), {f"{MED_A}:0": 1, f"{MED_A}:15": 1, f"{MED_A}:30": 1}, ident) == 45


def test_from_seven_doses_the_prior_is_first_and_the_policy_decides():
    assert D.choose_offset(MED_A, fifteen_delays(7, 40), set(), {}, ident) == 30   # prior 30, rank keeps it first
    seen = []

    def rank(keys):
        seen.append(keys[0])
        return keys[::-1]                                                          # the policy picks the last one

    assert D.choose_offset(MED_A, fifteen_delays(7, 40), set(), {}, rank) == 0
    assert seen[0] == f"{MED_A}:30"


def test_a_dismissed_offset_is_skipped_and_all_dismissed_means_none():
    assert D.choose_offset(MED_A, [], {f"{MED_A}:0"}, {}, ident) == 15
    assert D.choose_offset(MED_A, fifteen_delays(7, 40), {f"{MED_A}:30"}, {}, ident) == 15
    assert D.choose_offset(MED_A, [], {f"{MED_A}:{o}" for o in D.MENU}, {}, ident) is None


def test_a_dismissal_of_one_medicine_does_not_touch_another():
    assert D.choose_offset(MED_B, [], {f"{MED_A}:0"}, {}, ident) == 0


def test_offset_is_read_back_from_when_the_reminder_was_made():
    t = at(20)
    assert D.offset_of(t, t) == 0
    assert D.offset_of(t, t + timedelta(minutes=16)) == 15
    assert D.offset_of(t, t + timedelta(minutes=44)) == 30         # a tick a little late still belongs to 30
    assert D.offset_of(t, t + timedelta(minutes=60)) is None       # made after the window: cannot be attributed
    assert D.offset_of(t, t - timedelta(minutes=1)) is None


# ───────────────────────────────────────────────────────────────── success and miss
def test_success_needs_a_reminder_then_a_dose_taken_inside_the_window():
    t = at(20)
    reminded = t + timedelta(minutes=15)
    assert D.is_success(reminded, t + timedelta(minutes=30), t)
    assert D.is_success(reminded, t + timedelta(minutes=60), t)
    assert not D.is_success(reminded, t + timedelta(minutes=61), t)          # after the window
    assert not D.is_success(reminded, t + timedelta(minutes=10), t)          # taken before the reminder was sent
    assert not D.is_success(reminded, None, t)                               # untaken: a miss


def test_renudge_comes_thirty_minutes_after_the_reminder_while_inside_the_window():
    t = at(20)
    reminded = t + timedelta(minutes=15)
    assert not D.renudge_due(reminded, t, t + timedelta(minutes=44))
    assert D.renudge_due(reminded, t, t + timedelta(minutes=45))
    assert not D.renudge_due(reminded, t, t + timedelta(minutes=61))


# ───────────────────────────────────────────────────────────────── wording and the fact
def test_fact_text_matches_the_example_and_names_the_period():
    assert D.fact_text("Metformin", "evening", 20, 15) == (
        "You usually take your evening Metformin about 20 minutes after the set time. We remind you 15 minutes after it.")
    assert D.fact_text("Metformin", "", 20, 15).startswith("You usually take your Metformin about 20 minutes")


def test_period_needs_one_dose_time():
    assert D.period_for({time(20, 0)}) == "evening"
    assert D.period_for({time(8, 0)}) == "morning"
    assert D.period_for({time(8, 0), time(20, 0)}) == ""


def test_reminder_body_uses_only_what_the_record_says():
    assert D.reminder_body("Take with a full glass of water.", "after_meal") == "Take with a full glass of water."
    assert D.reminder_body(None, "before_meal") == "Take it before a meal."
    assert D.reminder_body(None, "na") == ""
    assert D.reminder_body(None, "mixed") == ""


def test_key_is_unique_per_medicine_and_slot_and_has_the_dose_prefix():
    k = D.dose_key(MED_A, at(20))
    assert k == f"dose-{MED_A}-2026-10-09-20:00"
    assert k != D.dose_key(MED_B, at(20))
    assert D.parse_key(k) == (MED_A, at(20), False)
    assert D.parse_key(k + D.RENUDGE_SUFFIX) == (MED_A, at(20), True)
    assert D.parse_key("meal-1-2026-10-09") is None


# ───────────────────────────────────────────────────────────────── planning reminders
def test_a_reminder_is_made_only_inside_the_window_and_only_when_untaken():
    s = slots_for(sched())
    assert run_plan(s, at(19, 59))["rows"] == []                       # before the window
    r = run_plan(s, at(20, 0))["rows"]
    assert len(r) == 1 and r[0]["kind"] == "dose_reminder" and r[0]["title"] == "Time for your Metformin"
    assert run_plan(s, at(21, 1))["rows"] == []                        # window over
    assert run_plan(s, at(20, 5), logs={("s-a", at(20)): ("taken", at(20))})["rows"] == []   # already taken
    assert run_plan(s, at(20, 5), logs={("s-a", at(20)): ("missed", None)})["rows"] == []


def test_the_first_reminder_waits_for_the_chosen_offset_and_records_the_try():
    s = slots_for(sched())
    res = run_plan(s, at(20, 10), tries={f"{MED_A}:0": 1})                       # least tried is 15
    assert res["rows"] == [] and res["tried"] == []
    res = run_plan(s, at(20, 15), tries={f"{MED_A}:0": 1})
    assert len(res["rows"]) == 1 and res["tried"] == [f"{MED_A}:15"]
    assert res["rows"][0]["arm"] == f"{MED_A}:15"


def test_a_dose_at_2200_still_gets_its_reminder_and_is_exempt_from_quiet_hours():
    s = slots_for(sched(t=time(22, 0)))
    rows = run_plan(s, at(22, 0))["rows"]
    assert len(rows) == 1
    assert rows[0]["key"].startswith("dose-") and logstore.is_exempt(rows[0]["key"])
    assert logstore.in_quiet_hours(at(22, 0))


def test_two_medicines_at_the_same_time_each_get_their_own_reminder():
    s = slots_for(sched(mid=MED_A, sid="s-a"), sched(mid=MED_B, sid="s-b", name="Gliclazide", strength="30 mg"))
    rows = run_plan(s, at(20, 0))["rows"]
    assert len(rows) == 2
    assert len({r["key"] for r in rows}) == 2
    assert {r["title"] for r in rows} == {"Time for your Metformin", "Time for your Gliclazide"}


def test_the_daily_cap_of_the_plan_is_respected():
    s = slots_for(sched(mid=MED_A, sid="s-a"), sched(mid=MED_B, sid="s-b"))
    assert len(run_plan(s, at(20, 0), max_new=1)["rows"]) == 1


def test_a_renudge_comes_only_when_untaken_and_inside_the_window():
    s = slots_for(sched())
    first = dict(scheduled_for=at(20, 15), acted_at=None, action=None, id=1)
    notes = {D.dose_key(MED_A, at(20)): first}
    have = {D.dose_key(MED_A, at(20))}
    assert run_plan(s, at(20, 44), notes=notes, have=have)["rows"] == []
    rows = run_plan(s, at(20, 45), notes=notes, have=have)["rows"]
    assert len(rows) == 1 and rows[0]["kind"] == "dose_renudge" and rows[0]["key"].endswith("-renudge")
    assert rows[0]["title"] == "Still time for your Metformin"
    assert run_plan(s, at(21, 1), notes=notes, have=have)["rows"] == []


def test_a_reminder_that_was_acted_on_gets_no_renudge():
    s = slots_for(sched())
    notes = {D.dose_key(MED_A, at(20)): dict(scheduled_for=at(20, 15), acted_at=at(20, 20), action="taken", id=1)}
    assert run_plan(s, at(20, 50), notes=notes, have={D.dose_key(MED_A, at(20))})["rows"] == []


def test_a_dose_taken_after_the_reminder_is_a_success_once():
    s = slots_for(sched())
    key = D.dose_key(MED_A, at(20))
    notes = {key: dict(scheduled_for=at(20, 15), acted_at=None, action=None, id=1)}
    logs = {("s-a", at(20)): ("taken", at(20, 30))}
    res = run_plan(s, at(20, 31), logs=logs, notes=notes, have={key})
    assert res["acts"] == [{"key": key, "arm": f"{MED_A}:15"}]
    assert res["rows"] == []
    # after the write marks the reminder acted, the next tick records nothing
    notes[key]["acted_at"] = at(20, 31)
    assert run_plan(s, at(20, 32), logs=logs, notes=notes, have={key})["acts"] == []


def test_an_untaken_reminder_records_nothing_and_stays_a_miss():
    s = slots_for(sched())
    key = D.dose_key(MED_A, at(20))
    notes = {key: dict(scheduled_for=at(20, 15), acted_at=None, action=None, id=1)}
    res = run_plan(s, at(21, 30), notes=notes, have={key})
    assert res == {"rows": [], "tried": [], "acts": [], "rejects": []}


def test_a_dismissed_reminder_is_recorded_once_and_its_offset_is_not_used_again():
    s = slots_for(sched())
    key = D.dose_key(MED_A, at(20))
    notes = {key: dict(scheduled_for=at(20, 15), acted_at=at(20, 16), action="dismissed", id=1)}
    res = run_plan(s, at(20, 40), notes=notes, have={key}, tries={f"{MED_A}:0": 5})
    assert res["rejects"] == [{"key": key, "arm": f"{MED_A}:15"}]
    # the next day's choice avoids 15 even though it is the least tried
    tomorrow = D.make_slots([sched()], [DAY + timedelta(days=1)])
    nxt = D.plan(tomorrow, {}, notes, {f"{MED_A}:0": 5}, {}, set(), at(20, 30).replace(day=10), ident)["rows"]
    assert nxt[0]["arm"] == f"{MED_A}:30"
    notes[key]["action"] = "dismissed_learned"
    assert run_plan(s, at(20, 41), notes=notes, have={key})["rejects"] == []


def test_guard_blocks_drop_the_title_and_clear_the_body_only():
    d = D._draft(slots_for(sched(directions="Take with food."))[0], D.dose_key(MED_A, at(20)), False, f"{MED_A}:0")
    assert D._vet(d, lambda text, rule: True)[3] == "Take with food."
    assert D._vet(d, lambda text, rule: rule != "dose_reminder_body")[3] == ""
    assert D._vet(d, lambda text, rule: rule != "dose_reminder_title") is None
    assert D._vet(d, lambda text, rule: True)[4] == "B1"
