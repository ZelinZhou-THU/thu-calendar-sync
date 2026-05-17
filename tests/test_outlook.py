from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from thu_calendar_sync.models import CalendarEvent
from thu_calendar_sync.outlook import (
    _find_calendar_folder,
    _create_appointment,
    sync_events_to_outlook,
)


def _make_event():
    return CalendarEvent("高等数学", "2026-02-17", "08:00", "09:35", "六教6A013", "")


def test_create_appointment():
    folder = MagicMock()
    item = MagicMock()
    item.EntryID = "ENTRY_001"
    folder.Items.Add.return_value = item

    ev = _make_event()
    entry_id = _create_appointment(folder, ev)

    assert entry_id == "ENTRY_001"
    folder.Items.Add.assert_called_once_with(1)
    item.Save.assert_called_once()
    assert item.Subject == "高等数学"
    assert item.Location == "六教6A013"


@patch("thu_calendar_sync.outlook._get_outlook_app")
@patch("thu_calendar_sync.outlook._find_calendar_folder")
@patch("thu_calendar_sync.outlook.load_state")
@patch("thu_calendar_sync.outlook.save_state")
@patch("thu_calendar_sync.outlook._clear_folder_in_range")
def test_sync_events(mock_clear, mock_save, mock_load, mock_find, mock_getapp, tmp_path):
    mock_load.return_value = {}
    folder = MagicMock()
    item = MagicMock()
    item.EntryID = "EID_1"
    folder.Items.Add.return_value = item
    mock_find.return_value = folder

    ev = _make_event()
    count = sync_events_to_outlook([ev], "qq.com", "2026-02-17", "2026-06-20", state_path=tmp_path / "state.json")

    assert count == 1
    mock_save.assert_called_once()
    mock_clear.assert_called_once()
