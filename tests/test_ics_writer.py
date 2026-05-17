import os
from pathlib import Path
from thu_calendar_sync.models import CalendarEvent
from thu_calendar_sync.ics_writer import generate_ics, save_ics


def _make_event():
    return CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教6A013", "")


def test_generate_ics_basic():
    events = [_make_event()]
    data = generate_ics(events, semester_label="2026春季")
    text = data.decode("utf-8")
    assert "BEGIN:VCALENDAR" in text
    assert "BEGIN:VEVENT" in text
    assert "高等数学" in text
    assert "六教6A013" in text
    assert "END:VCALENDAR" in text


def test_generate_ics_uid():
    events = [_make_event()]
    data = generate_ics(events)
    text = data.decode("utf-8")
    assert "thu-cal-" in text
    assert "@sync" in text


def test_generate_ics_multiple_events():
    ev1 = CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教", "")
    ev2 = CalendarEvent("线性代数", "2026-02-17", "10:00", "11:35", "四教", "")
    data = generate_ics([ev1, ev2])
    text = data.decode("utf-8")
    assert text.count("BEGIN:VEVENT") == 2
    assert "高等数学" in text
    assert "线性代数" in text


def test_save_ics_creates_file(tmp_path: Path):
    events = [_make_event()]
    out = tmp_path / "sub" / "test.ics"
    result = save_ics(events, out, semester_label="test")
    assert result.exists()
    content = result.read_bytes().decode("utf-8")
    assert "BEGIN:VCALENDAR" in content
