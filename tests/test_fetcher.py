import pytest
from thu_calendar_sync.fetcher import _parse_jsonp, _raw_to_calendar_event, _chunk_date_range


def test_parse_jsonp():
    text = 'callback([{"nr":"数学","dd":"教室","nq":"2026-02-17","kssj":"08:00","jssj":"09:35","fl":""}])'
    result = _parse_jsonp(text)
    assert len(result) == 1
    assert result[0]["nr"] == "数学"


def test_parse_jsonp_empty():
    text = "callback([])"
    result = _parse_jsonp(text)
    assert result == []


def test_raw_to_calendar_event():
    item = {"nr": "高等数学", "dd": "六教6A013", "nq": "2026-02-17", "kssj": "08:00", "jssj": "09:35", "fl": ""}
    ev = _raw_to_calendar_event(item)
    assert ev.course_name == "高等数学"
    assert ev.date == "2026-02-17"
    assert ev.start_time == "08:00"
    assert ev.end_time == "09:35"
    assert ev.location == "六教6A013"


def test_chunk_date_range_single_chunk():
    chunks = _chunk_date_range("2026-02-17", "2026-02-20", days=28)
    assert len(chunks) == 1
    assert chunks[0] == ("20260217", "20260220")


def test_chunk_date_range_multiple_chunks():
    chunks = _chunk_date_range("2026-02-17", "2026-03-20", days=28)
    assert len(chunks) == 2
    assert chunks[0][0] == "20260217"
    assert chunks[1][0] == "20260317"


def test_chunk_date_range_exact_boundary():
    chunks = _chunk_date_range("2026-02-17", "2026-03-16", days=28)
    assert len(chunks) == 1
    assert chunks[0] == ("20260217", "20260316")


def test_chunk_date_range_empty():
    chunks = _chunk_date_range("2026-03-01", "2026-02-01", days=28)
    assert chunks == []
