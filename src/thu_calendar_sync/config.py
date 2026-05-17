from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import dataclass

import tomllib

from dotenv import load_dotenv

load_dotenv()

CONFIG_FILENAME = "thu-cal.toml"
STATE_FILENAME = "thu-cal-state.json"


@dataclass
class SyncConfig:
    username: str = ""
    password: str = ""
    graduate: bool = False
    semester_start: str = ""
    semester_end: str = ""
    calendar_account: str = "qq.com"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.username:
            errors.append("未配置学号 (username)")
        if not self.password:
            errors.append("未配置密码 (password)")
        return errors

    @staticmethod
    def _resolve_credential(toml_val: str, env_key: str) -> str:
        if toml_val:
            return toml_val
        return os.environ.get(env_key, "")


def _find_config_path() -> Path | None:
    cwd = Path.cwd()
    candidate = cwd / CONFIG_FILENAME
    if candidate.exists():
        return candidate
    return None


def load_config(config_path: Path | None = None) -> SyncConfig:
    if config_path is None:
        config_path = _find_config_path()
    if config_path is None or not config_path.exists():
        cfg = SyncConfig(
            username=SyncConfig._resolve_credential("", "THU_USERNAME"),
            password=SyncConfig._resolve_credential("", "THU_PASSWORD"),
        )
    else:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        auth = data.get("Auth", {})
        cal = data.get("Calendar", {})
        cfg = SyncConfig(
            username=SyncConfig._resolve_credential(auth.get("username", ""), "THU_USERNAME"),
            password=SyncConfig._resolve_credential(auth.get("password", ""), "THU_PASSWORD"),
            graduate=cal.get("graduate", False),
            semester_start=cal.get("semester_start", ""),
            semester_end=cal.get("semester_end", ""),
            calendar_account=cal.get("calendar_account", "qq.com"),
        )
    return cfg


def load_state(state_path: Path | None = None) -> dict:
    if state_path is None:
        state_path = Path.cwd() / STATE_FILENAME
    if not state_path.exists():
        return {}
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict, state_path: Path | None = None) -> Path:
    if state_path is None:
        state_path = Path.cwd() / STATE_FILENAME
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state_path
