from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CalendarEvent:
    course_name: str
    date: str          # "2026-02-17"
    start_time: str    # "08:00"
    end_time: str      # "09:35"
    location: str      # "六教6A013"
    status: str        # 原始 status 字段

    @property
    def start_dt(self) -> datetime:
        return datetime.strptime(f"{self.date} {self.start_time}", "%Y-%m-%d %H:%M")

    @property
    def end_dt(self) -> datetime:
        return datetime.strptime(f"{self.date} {self.end_time}", "%Y-%m-%d %H:%M")

    @property
    def uid(self) -> str:
        raw = f"{self.course_name}|{self.date}|{self.start_time}|{self.end_time}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def __str__(self) -> str:
        return f"{self.course_name} {self.date} {self.start_time}-{self.end_time} @{self.location}"


@dataclass
class SyncState:
    last_sync: str = ""
    semester_start: str = ""
    semester_end: str = ""
    events: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "last_sync": self.last_sync,
            "semester_start": self.semester_start,
            "semester_end": self.semester_end,
            "events": self.events,
        }
