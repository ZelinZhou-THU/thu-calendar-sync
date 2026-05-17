from thu_calendar_sync.models import CalendarEvent, SyncState


def test_calendar_event_start_dt():
    ev = CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教6A013", "")
    assert ev.start_dt.year == 2026
    assert ev.start_dt.month == 2
    assert ev.start_dt.hour == 8


def test_calendar_event_end_dt():
    ev = CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教6A013", "")
    assert ev.end_dt.hour == 9
    assert ev.end_dt.minute == 35


def test_calendar_event_uid_deterministic():
    ev1 = CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教6A013", "")
    ev2 = CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教6A013", "")
    assert ev1.uid == ev2.uid


def test_calendar_event_uid_unique_for_different_events():
    ev1 = CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教", "")
    ev2 = CalendarEvent("线性代数", "2026-02-17", "08:00", "09:35", "六教", "")
    assert ev1.uid != ev2.uid


def test_calendar_event_str():
    ev = CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教6A013", "")
    s = str(ev)
    assert "高等数学" in s
    assert "08:00" in s
    assert "六教6A013" in s


def test_sync_state_to_dict():
    state = SyncState(
        last_sync="2026-05-07",
        semester_start="2026-02-17",
        semester_end="2026-06-20",
        events={"abc123": "ENTRY_ID_1"},
    )
    d = state.to_dict()
    assert d["last_sync"] == "2026-05-07"
    assert d["events"]["abc123"] == "ENTRY_ID_1"
