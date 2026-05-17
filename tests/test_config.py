import json
from pathlib import Path
from thu_calendar_sync.config import SyncConfig, load_config, load_state, save_state


def test_sync_config_validate_ok():
    cfg = SyncConfig(username="2023010001", password="test123")
    assert cfg.validate() == []


def test_sync_config_validate_missing_username():
    cfg = SyncConfig(password="test123")
    errors = cfg.validate()
    assert len(errors) == 1
    assert "学号" in errors[0]


def test_sync_config_validate_missing_password():
    cfg = SyncConfig(username="2023010001")
    errors = cfg.validate()
    assert len(errors) == 1
    assert "密码" in errors[0]


def test_resolve_credential_from_value():
    result = SyncConfig._resolve_credential("direct_value", "NONEXISTENT_ENV")
    assert result == "direct_value"


def test_load_state_missing_file(tmp_path: Path):
    state = load_state(tmp_path / "nonexistent.json")
    assert state == {}


def test_save_and_load_state(tmp_path: Path):
    state_file = tmp_path / "state.json"
    data = {"last_sync": "2026-05-07", "events": {"hash1": "eid1"}}
    save_state(data, state_file)
    loaded = load_state(state_file)
    assert loaded["last_sync"] == "2026-05-07"
    assert loaded["events"]["hash1"] == "eid1"
