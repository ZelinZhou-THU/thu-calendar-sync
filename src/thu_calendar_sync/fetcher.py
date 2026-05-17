from __future__ import annotations

import json
from datetime import datetime, timedelta

import requests

from thu_calendar_sync.auth import AuthSession, add_csrf_token
from thu_calendar_sync.models import CalendarEvent
from thu_calendar_sync.exceptions import FetchError

_REGISTRAR_PREFIX = "https://zhjw.cic.tsinghua.edu.cn"
_REGISTRAR_TICKET_URL = "https://learn.tsinghua.edu.cn/b/wlxt/common/auth/gnt"
_REGISTRAR_AUTH_URL = f"{_REGISTRAR_PREFIX}/j_acegi_login.do"
_SEMESTER_URL = "https://learn.tsinghua.edu.cn/b/kc/zhjw_v_code_xnxq/getCurrentAndNextSemester"

_CHUNK_DAYS = 28


def _parse_jsonp(text: str) -> list[dict]:
    start = text.index("(")
    end = text.rindex(")")
    json_str = text[start + 1 : end]
    return json.loads(json_str)


def _raw_to_calendar_event(item: dict) -> CalendarEvent:
    return CalendarEvent(
        course_name=item.get("nr", ""),
        date=item.get("nq", ""),
        start_time=item.get("kssj", ""),
        end_time=item.get("jssj", ""),
        location=item.get("dd", ""),
        status=item.get("fl", ""),
    )


def _chunk_date_range(start: str, end: str, days: int = _CHUNK_DAYS) -> list[tuple[str, str]]:
    fmt = "%Y-%m-%d"
    start_dt = datetime.strptime(start, fmt)
    end_dt = datetime.strptime(end, fmt)
    chunks = []
    current = start_dt
    while current <= end_dt:
        chunk_end = min(current + timedelta(days=days - 1), end_dt)
        chunks.append((current.strftime("%Y%m%d"), chunk_end.strftime("%Y%m%d")))
        current = chunk_end + timedelta(days=1)
    return chunks


def get_current_semester(session: requests.Session, csrf_token: str) -> dict:
    url = add_csrf_token(_SEMESTER_URL, csrf_token)
    resp = session.get(url)
    resp.raise_for_status()
    data = resp.json()
    if data.get("message") != "success":
        raise FetchError(f"获取学期信息失败: {data}")
    result = data["result"]
    return {
        "id": result["id"],
        "start_date": result["kssj"],
        "end_date": result["jssj"],
    }


def fetch_calendar(auth: AuthSession, start_date: str, end_date: str, graduate: bool = False) -> list[CalendarEvent]:
    session = auth.session
    prefix = "yjs" if graduate else "bks"

    ticket_resp = session.post(
        add_csrf_token(_REGISTRAR_TICKET_URL, auth.csrf_token),
        data={"appId": "ALL_ZHJW"},
    )
    ticket_resp.raise_for_status()
    registrar_ticket = ticket_resp.text.strip().strip('"')

    auth_url = f"{_REGISTRAR_AUTH_URL}?url=/&ticket={registrar_ticket}"
    session.get(auth_url).raise_for_status()

    chunks = _chunk_date_range(start_date, end_date)
    all_events: list[CalendarEvent] = []

    for chunk_start, chunk_end in chunks:
        callback = "thu_calendar_sync_cb"
        cal_url = (
            f"{_REGISTRAR_PREFIX}/jxmh_out.do"
            f"?m={prefix}_jxrl_all"
            f"&p_start_date={chunk_start}"
            f"&p_end_date={chunk_end}"
            f"&jsoncallback={callback}"
        )
        resp = session.get(cal_url)
        resp.raise_for_status()
        raw_items = _parse_jsonp(resp.text)
        for item in raw_items:
            all_events.append(_raw_to_calendar_event(item))

    return all_events
