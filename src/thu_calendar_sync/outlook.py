from __future__ import annotations

from datetime import datetime
from pathlib import Path

import win32com.client

from thu_calendar_sync.models import CalendarEvent
from thu_calendar_sync.config import load_state, save_state
from thu_calendar_sync.exceptions import (
    OutlookError,
    OutlookNotFoundError,
    CalendarAccountNotFoundError,
)

_OL_FOLDER_CALENDAR = 9
_OL_APPOINTMENT_ITEM = 1
_CAL_FOLDER_NAME = "清华课表"


def _get_outlook_app():
    try:
        return win32com.client.Dispatch("Outlook.Application")
    except Exception as e:
        raise OutlookNotFoundError(f"无法连接 Outlook: {e}")


def _find_calendar_folder(outlook, account_keyword: str):
    namespace = outlook.GetNamespace("MAPI")
    for store in namespace.Stores:
        display_name = store.DisplayName.lower()
        if account_keyword.lower() in display_name:
            try:
                default_cal = store.GetDefaultFolder(_OL_FOLDER_CALENDAR)
                return _get_or_create_subfolder(default_cal)
            except Exception:
                continue
    raise CalendarAccountNotFoundError(
        f"在 Outlook 中未找到匹配 '{account_keyword}' 的日历账户。"
        f"请确认 QQ 邮箱已在 Outlook 中配置。"
    )


def _get_or_create_subfolder(parent_folder):
    for i in range(1, parent_folder.Folders.Count + 1):
        if parent_folder.Folders.Item(i).Name == _CAL_FOLDER_NAME:
            return parent_folder.Folders.Item(i)
    return parent_folder.Folders.Add(_CAL_FOLDER_NAME)


def _clear_folder_in_range(folder, start_dt: datetime, end_dt: datetime):
    items = folder.Items
    items.Sort("[Start]")
    items.IncludeRecurrences = True
    restriction = f"[Start] >= '{start_dt.strftime('%m/%d/%Y %H:%M %p')}' AND [End] <= '{end_dt.strftime('%m/%d/%Y %H:%M %p')}'"
    filtered = items.Restrict(restriction)
    to_delete = []
    for item in filtered:
        to_delete.append(item)
    for item in to_delete:
        item.Delete()


def _create_appointment(folder, event: CalendarEvent):
    item = folder.Items.Add(_OL_APPOINTMENT_ITEM)
    item.Subject = event.course_name
    item.Start = event.start_dt.strftime("%m/%d/%Y %H:%M")
    item.End = event.end_dt.strftime("%m/%d/%Y %H:%M")
    item.Location = event.location
    item.Body = f"教室: {event.location}"
    item.ReminderSet = False
    item.Save()
    return item.EntryID


def sync_events_to_outlook(
    events: list[CalendarEvent],
    account_keyword: str,
    start_date: str,
    end_date: str,
    state_path: Path | None = None,
) -> int:
    outlook = _get_outlook_app()
    folder = _find_calendar_folder(outlook, account_keyword)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59)

    _clear_folder_in_range(folder, start_dt, end_dt)

    state = load_state(state_path)
    event_map = {}
    count = 0

    for event in events:
        entry_id = _create_appointment(folder, event)
        event_map[event.uid] = entry_id
        count += 1

    state.update({
        "last_sync": datetime.now().isoformat(),
        "semester_start": start_date,
        "semester_end": end_date,
        "events": event_map,
    })
    save_state(state, state_path)
    return count


def clean_synced_events(account_keyword: str, state_path: Path | None = None):
    outlook = _get_outlook_app()
    folder = _find_calendar_folder(outlook, account_keyword)
    state = load_state(state_path)
    events = state.get("events", {})

    namespace = outlook.GetNamespace("MAPI")
    deleted = 0
    for uid, entry_id in events.items():
        try:
            item = namespace.GetItemFromID(entry_id)
            item.Delete()
            deleted += 1
        except Exception:
            pass

    state["events"] = {}
    save_state(state, state_path)
    return deleted
