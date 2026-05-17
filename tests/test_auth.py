from unittest.mock import MagicMock, patch
import pytest

from thu_calendar_sync.auth import (
    _extract_csrf_token,
    _sm2_encrypt,
    add_csrf_token,
    _save_trusted_device,
)
from thu_calendar_sync.exceptions import (
    BadCredentialsError,
    CaptchaRequiredError,
    AuthenticationError,
)


def test_extract_csrf_token():
    html = '<a href="/api/xxx&_csrf=TOKEN_ABC123">link</a>'
    assert _extract_csrf_token(html) == "TOKEN_ABC123"


def test_extract_csrf_token_missing():
    html = "<html><body>No token here</body></html>"
    with pytest.raises(AuthenticationError, match="CSRF"):
        _extract_csrf_token(html)


def test_add_csrf_token_no_query():
    result = add_csrf_token("https://example.com/api", "TOKEN123")
    assert result == "https://example.com/api?_csrf=TOKEN123"


def test_add_csrf_token_with_query():
    result = add_csrf_token("https://example.com/api?foo=bar", "TOKEN123")
    assert result == "https://example.com/api?foo=bar&_csrf=TOKEN123"


def test_sm2_encrypt_produces_hex_with_04_prefix():
    pubkey = (
        "B9C9A6E04E9C91F7BA880429273747D7EF5DDEB0BB2FF6317EB00BEF331A8308"
        "81A6994B8993F3F5D6EADDDB81872266C87C018FB4162F5AF347B483E24620207"
    )
    result = _sm2_encrypt("test_password", pubkey)
    assert result.startswith("04")
    assert all(c in "0123456789abcdef" for c in result[2:])


def test_sm2_encrypt_deterministic_length():
    pubkey = (
        "B9C9A6E04E9C91F7BA880429273747D7EF5DDEB0BB2FF6317EB00BEF331A8308"
        "81A6994B8993F3F5D6EADDDB81872266C87C018FB4162F5AF347B483E24620207"
    )
    r1 = _sm2_encrypt("password", pubkey)
    assert len(r1) > 10


def test_save_trusted_device_success():
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {"result": "success", "object": "FINGER3_TOKEN_ABC"}
    session.post.return_value = resp

    from thu_calendar_sync.auth import _save_trusted_device
    result = _save_trusted_device(session, "FP_123")
    assert result == "FINGER3_TOKEN_ABC"
    session.post.assert_called_once()
    call_args = session.post.call_args
    assert call_args[0][0].endswith("/saveFinger")
    data = call_args[1]["data"]
    assert data["fingerprint"] == "FP_123"
    assert data["radioVal"] == "是"


def test_save_trusted_device_failure():
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {"result": "error", "msg": "some error"}
    session.post.return_value = resp

    from thu_calendar_sync.auth import _save_trusted_device
    result = _save_trusted_device(session, "FP_123")
    assert result == ""


def test_save_trusted_device_exception():
    session = MagicMock()
    session.post.side_effect = Exception("network error")

    from thu_calendar_sync.auth import _save_trusted_device
    result = _save_trusted_device(session, "FP_123")
    assert result == ""
