from __future__ import annotations


class ThuCalSyncError(Exception):
    pass


class AuthenticationError(ThuCalSyncError):
    pass


class BadCredentialsError(AuthenticationError):
    pass


class CaptchaRequiredError(AuthenticationError):
    pass


class TwoFactorRequiredError(AuthenticationError):
    pass


class RoamingError(ThuCalSyncError):
    pass


class OutlookError(ThuCalSyncError):
    pass


class OutlookNotFoundError(OutlookError):
    pass


class CalendarAccountNotFoundError(OutlookError):
    pass


class FetchError(ThuCalSyncError):
    pass
