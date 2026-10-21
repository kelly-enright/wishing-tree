"""The date helpers the frontend renders with.

These run the real TypeScript module through Node rather than reimplementing
it in Python, because a second copy of the rules is a second thing to get
wrong. Node 24 strips the types on import, so there is nothing to build.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
PROBE = ROOT / "dates_probe.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is needed to run the frontend module"
)


def run(calls, today=None):
    """Call the TypeScript helpers and give back what they returned."""
    payload = {"calls": calls}
    if today:
        y, m, d = today
        payload["today"] = [y, m - 1, d]   # JS months are zero-based
    spec = ROOT / "_dates_cases.json"
    spec.write_text(json.dumps(payload))
    try:
        done = subprocess.run(
            ["node", str(PROBE), str(spec)],
            capture_output=True, text=True, cwd=ROOT,
        )
    finally:
        spec.unlink(missing_ok=True)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


# --------------------------------------------------------------------------
# The shapes the brief asked for
# --------------------------------------------------------------------------

def test_a_dropoff_reads_as_a_sentence():
    assert run([["when", "2026-10-22", "Thursday 4:00 PM-7:00 PM"]]) == [
        "Thursday, Oct 22, 4–7 PM"
    ]


def test_a_deadline_carries_how_long_is_left():
    """The brief's example was "Sat, Oct 25" — October 25th 2026 is a Sunday,
    and the weekday is computed rather than copied, so it says so."""
    assert run([["deadline", "2026-10-25"]], today=(2026, 10, 20)) == [
        "Sun, Oct 25 · 5 days"
    ]


def test_no_iso_date_survives_formatting():
    shown = run([
        ["longDay", "2026-10-22"],
        ["shortDay", "2026-10-22"],
        ["when", "2026-10-24", "Saturday 10:00 AM-1:00 PM"],
        ["deadline", "2026-11-02"],
    ], today=(2026, 10, 20))
    for text in shown:
        assert "2026-" not in text, text


# --------------------------------------------------------------------------
# Hours
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label,expected", [
    ("Thursday 4:00 PM-7:00 PM", "4–7 PM"),
    ("Saturday 10:00 AM-1:00 PM", "10 AM–1 PM"),   # crosses noon, so both say it
    ("Thursday 4:30 PM-7:00 PM", "4:30–7 PM"),     # a real half hour is kept
    ("Monday 9:00 AM-11:30 AM", "9–11:30 AM"),
])
def test_hours_say_each_meridiem_only_when_it_is_needed(label, expected):
    assert run([["hours", label]]) == [expected]


def test_an_unexpected_window_is_passed_through_not_mangled():
    assert run([["hours", "by arrangement"]]) == ["by arrangement"]
    assert run([["hours", ""]]) == [""]


# --------------------------------------------------------------------------
# The timezone trap
# --------------------------------------------------------------------------

def test_a_date_does_not_slip_a_day_west_of_greenwich():
    """`new Date('2026-10-22')` is UTC midnight, which is the 21st in New
    Haven. Every date here is built in local time instead."""
    done = subprocess.run(
        ["node", str(PROBE), str(_case_file())],
        capture_output=True, text=True, cwd=ROOT,
        env={"TZ": "America/New_York", "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == ["Thursday, Oct 22"]


def _case_file():
    spec = ROOT / "_dates_tz.json"
    spec.write_text(json.dumps({"calls": [["longDay", "2026-10-22"]]}))
    return spec


# --------------------------------------------------------------------------
# Relative days
# --------------------------------------------------------------------------

@pytest.mark.parametrize("iso,expected", [
    ("2026-10-20", "today"),
    ("2026-10-21", "tomorrow"),
    ("2026-10-19", "yesterday"),
    ("2026-10-25", "5 days"),
    ("2026-10-18", "2 days ago"),
])
def test_how_far_off_a_date_is(iso, expected):
    assert run([["awayFrom", iso]], today=(2026, 10, 20)) == [expected]


def test_nothing_is_rendered_for_a_missing_date():
    assert run([["longDay", None], ["when", None, None], ["deadline", ""]]) == ["", "", ""]


# --------------------------------------------------------------------------
# A standing weekly window
# --------------------------------------------------------------------------

def test_a_weekly_window_reads_the_way_a_person_says_it():
    """"Thursday 4:00 PM-7:00 PM" is a database row. "Thursdays 4–7 PM" is
    how somebody tells you when to come."""
    assert run([
        ["weekly", "Thursday 4:00 PM-7:00 PM"],
        ["weekly", "Saturday 10:00 AM-1:00 PM"],
    ]) == ["Thursdays 4–7 PM", "Saturdays 10 AM–1 PM"]


def test_the_day_is_plural_because_it_happens_every_week():
    """A singular "Thursday" reads as one particular Thursday, which is the
    opposite of what a standing window means."""
    for said in run([["weekly", "Thursday 4:00 PM-7:00 PM"]]):
        assert said.startswith("Thursdays")


def test_a_window_we_do_not_recognize_comes_back_whole():
    """Better an unformatted truth than a mangled one."""
    assert run([["weekly", "by arrangement"]]) == ["by arrangement"]
    assert run([["weekly", None]]) == [""]
