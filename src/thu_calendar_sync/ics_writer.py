from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from icalendar import Calendar, Event, Alarm
import pytz

from thu_calendar_sync.models import CalendarEvent

_TZ = pytz.timezone("Asia/Shanghai")
_PRODID = "-//thu-calendar-sync//EN"


def generate_ics(events: list[CalendarEvent], semester_label: str = "", reminder_minutes: int | None = None) -> bytes:
    cal = Calendar()
    cal.add("prodid", _PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"清华课表 {semester_label}".strip())
    cal.add("x-wr-timezone", "Asia/Shanghai")

    for ev in events:
        evt = Event()
        evt.add("summary", ev.course_name)
        evt.add("location", ev.location or "")
        evt.add("dtstart", _TZ.localize(ev.start_dt))
        evt.add("dtend", _TZ.localize(ev.end_dt))
        evt.add("dtstamp", _TZ.localize(datetime.now()))
        evt["uid"] = f"thu-cal-{ev.uid}@sync"
        if ev.location:
            evt.add("description", f"教室: {ev.location}")
        if reminder_minutes is not None:
            al = Alarm()
            al.add("trigger", timedelta(minutes=-reminder_minutes))
            al.add("action", "DISPLAY")
            al.add("description", ev.course_name)
            evt.add_component(al)
        cal.add_component(evt)

    return cal.to_ical()


def save_ics(events: list[CalendarEvent], output_path: Path, semester_label: str = "", reminder_minutes: int | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ics_data = generate_ics(events, semester_label, reminder_minutes)
    output_path.write_bytes(ics_data)
    return output_path
