from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from gmssl import sm2

from thu_calendar_sync.exceptions import (
    AuthenticationError,
    BadCredentialsError,
    CaptchaRequiredError,
    TwoFactorRequiredError,
    RoamingError,
)

_APP_ID = "bb5df85216504820be7bba2b0ae1535b"
_ID_BASE = "https://id.tsinghua.edu.cn"
_LOGIN_PAGE_URL = f"{_ID_BASE}/do/off/ui/auth/login/form/{_APP_ID}/0"
_LOGIN_CHECK_URL = f"{_ID_BASE}/do/off/ui/auth/login/check"
_DOUBLE_AUTH_URL = f"{_ID_BASE}/b/doubleAuth/login"
_SAVE_FINGER_URL = f"{_ID_BASE}/b/doubleAuth/personal/saveFinger"
_REDIRECT2JSP_URL = f"{_ID_BASE}/do/off/ui/auth/login/redirect2Jsp"
_LEARN_PREFIX = "https://learn.tsinghua.edu.cn"
_LEARN_ROAM_URL = f"{_LEARN_PREFIX}/f/j_spring_security_thauth_roaming_entry"
_LEARN_COURSE_LIST_URL = f"{_LEARN_PREFIX}/f/wlxt/index/course/student/"
_CSRF_REGEX = re.compile(r"&_csrf=(\S*)\"")
_SM2_KEY_REGEX = re.compile(r'id="sm2publicKey"[^>]*>([^<]+)<')

AJAX_HEADERS = {"X-Requested-With": "XMLHttpRequest", "Accept": "*/*"}


def _save_trusted_device(session: requests.Session, fingerprint: str) -> str:
    """调用 saveFinger 信任设备，返回 finger3 token。失败不阻断流程。"""
    try:
        r = session.post(_SAVE_FINGER_URL, data={
            "fingerprint": fingerprint,
            "deviceName": "windows,thu-calendar-sync/0.1",
            "radioVal": "是",
            "singleLogin": "yes",
        }, headers=AJAX_HEADERS)
        result = r.json()
        if result.get("result") == "success":
            return result.get("object", "")
    except Exception:
        pass
    return ""


@dataclass
class AuthSession:
    session: requests.Session
    csrf_token: str
    fingerprint: str = ""
    finger3: str = ""


def _sm2_encrypt(password: str, public_key_hex: str) -> str:
    crypt = sm2.CryptSM2(public_key=public_key_hex, private_key="", mode=1)
    encrypted = crypt.encrypt(password.encode("utf-8"))
    return "04" + encrypted.hex()


def _extract_csrf_token(html: str) -> str:
    matches = _CSRF_REGEX.findall(html)
    if not matches:
        raise AuthenticationError("无法从课程列表页提取 CSRF token")
    return matches[0]


def _handle_2fa(session: requests.Session, fingerprint: str, code_input=None) -> tuple[str, str]:
    def da_post(data):
        r = session.post(_DOUBLE_AUTH_URL, data=data, headers=AJAX_HEADERS)
        return r

    r = da_post({"action": "FIND_APPROACHES"})
    result = r.json()
    if result.get("result") != "success":
        raise AuthenticationError(f"2FA FIND_APPROACHES 失败: {result.get('msg')}")

    obj = result.get("object", {})
    has_wechat = obj.get("hasWeChatBool", False)
    has_totp = obj.get("hasTotp", False)

    send_type = None
    if has_wechat:
        send_type = "wechat"
    elif has_totp:
        send_type = "totp"
    else:
        send_type = "sms"

    r = da_post({"action": "SEND_CODE", "type": send_type})
    send_result = r.json()
    if send_result.get("result") != "success":
        raise AuthenticationError(f"2FA SEND_CODE 失败: {send_result.get('msg')}")

    if code_input is not None:
        code = code_input
    else:
        method_desc = {"wechat": "企业微信", "sms": "手机短信", "totp": "TOTP"}.get(send_type, send_type)
        code = input(f"请输入{method_desc}验证码: ").strip()

    if not code:
        raise AuthenticationError("未输入验证码")

    r = da_post({"action": "VERITY_CODE", "vericode": code})
    try:
        verify_result = r.json()
    except Exception:
        raise AuthenticationError(f"VERITY_CODE 响应不是合法 JSON: {r.text[:200]}")

    obj = verify_result.get("object")
    if not obj:
        raise AuthenticationError(f"VERITY_CODE 验证失败: {verify_result}")

    flow = obj.get("flow", "")

    if flow not in ("VERIFIED", "REDIRECTIDLOGINPAGE"):
        raise AuthenticationError(
            f"2FA 验证失败: {obj.get('msg', verify_result)}"
        )

    # 尝试信任设备
    finger3 = _save_trusted_device(session, fingerprint)

    redirect = obj.get("redirectUrl", "")
    if not redirect:
        raise AuthenticationError("2FA 验证成功但未获取到重定向地址")

    redirect_url = f"{_ID_BASE}{redirect}" if redirect.startswith("/") else redirect
    redir_resp = session.get(redirect_url)
    redir_resp.encoding = "utf-8"

    soup = BeautifulSoup(redir_resp.text, "html.parser")
    a_tag = soup.find("a", href=True)
    if not a_tag or "ticket" not in a_tag.get("href", ""):
        raise AuthenticationError("2FA 重定向页面中未找到 ticket 链接")

    href = a_tag["href"]
    return href.split("ticket=")[-1].split("&")[0], finger3


def login(username: str, password: str, fingerprint="", finger3="", code_input=None) -> AuthSession:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
    })

    page = session.get(_LOGIN_PAGE_URL)
    page.encoding = "utf-8"
    key_match = _SM2_KEY_REGEX.search(page.text)
    if not key_match:
        raise AuthenticationError("无法从登录页获取 SM2 公钥")
    public_key = key_match.group(1).strip()

    enc_pass = _sm2_encrypt(password, public_key)
    fp = fingerprint or uuid.uuid4().hex

    resp = session.post(_LOGIN_CHECK_URL, data={
        "i_user": username,
        "i_pass": enc_pass,
        "singleLogin": "on",
        "fingerPrint": fp,
        "fingerGenPrint": "",
        "fingerGenPrint3": "",  # 固定为空字符串，避免服务器拒绝验证
        "i_captcha": "",
    })
    resp.encoding = "utf-8"

    if "BAD_CREDENTIALS" in resp.text:
        raise BadCredentialsError("用户名或密码错误")
    if "验证码" in resp.text and "c_code" in resp.text:
        raise CaptchaRequiredError("需要验证码，请稍后重试")

    if "二次认证" in resp.text:
        ticket, new_finger3 = _handle_2fa(session, fp, code_input)
    else:
        # 无 2FA：信任设备生效或首次登录
        soup = BeautifulSoup(resp.text, "html.parser")
        a_tag = soup.find("a", href=True)
        if not a_tag:
            raise AuthenticationError("登录响应中未找到重定向链接")
        href = a_tag["href"]
        ticket = href.split("ticket=")[-1].split("&")[0]
        if not ticket:
            raise AuthenticationError("登录响应中未找到有效 ticket")
        new_finger3 = finger3  # 保持原值

    roam_resp = session.get(_LEARN_ROAM_URL, params={"ticket": ticket})
    if not roam_resp.ok:
        raise RoamingError(f"漫游到 learn.tsinghua.edu.cn 失败: HTTP {roam_resp.status_code}")

    course_page = session.get(_LEARN_COURSE_LIST_URL)
    course_page.raise_for_status()
    csrf_token = _extract_csrf_token(course_page.text)

    return AuthSession(session=session, csrf_token=csrf_token, fingerprint=fp, finger3=new_finger3)


def add_csrf_token(url: str, token: str) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}_csrf={token}"
