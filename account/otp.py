"""
One-time-password login.

Security properties (each one is tested in account/tests.py):
- code is generated with `secrets` (CSPRNG), not `random`;
- only an HMAC of the code is stored (cache), never the code itself, and never in the session;
- code expires after OTP_TTL_SECONDS;
- max OTP_MAX_ATTEMPTS wrong guesses, then the code is burned;
- resend cooldown per phone + hourly send limits per phone and per IP
  (protects the SMS budget and stops SMS bombing a victim's number).

Storage is Django's cache. With LocMemCache limits are per process; in
production use a shared cache (Redis, phase 3) so limits hold across workers.
"""

import logging
import re
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.crypto import constant_time_compare, salted_hmac

from .sms import SMSError, send_otp

logger = logging.getLogger(__name__)

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_MOBILE_RE = re.compile(r"^09\d{9}$")


def normalize_phone(raw):
    """
    Accept 09121234567, 9121234567, +989121234567, 00989121234567, Persian/Arabic digits,
    spaces and dashes. Return the canonical "09xxxxxxxxx" form or raise ValidationError.
    """
    value = re.sub(r"[\s\-()]", "", str(raw or "").translate(_DIGITS))
    if value.startswith("+98"):
        value = "0" + value[3:]
    elif value.startswith("0098"):
        value = "0" + value[4:]
    elif value.startswith("98") and len(value) == 12:
        value = "0" + value[2:]
    elif value.startswith("9") and len(value) == 10:
        value = "0" + value
    if not _MOBILE_RE.match(value):
        raise ValidationError("شمارهٔ موبایل معتبر نیست. مثال: 09121234567")
    return value


class OTPError(Exception):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after = retry_after


def _key(kind, ident):
    return f"otp:{kind}:{ident}"


def _hash(phone, code):
    return salted_hmac("account.otp", f"{phone}:{code}").hexdigest()


def _hit(key, limit, window):
    """Fixed-window counter. Returns True if the limit is exceeded."""
    cache.add(key, 0, timeout=window)
    try:
        count = cache.incr(key)
    except ValueError:  # key expired between add() and incr()
        cache.set(key, 1, timeout=window)
        count = 1
    return count > limit


def cooldown_remaining(phone):
    until = cache.get(_key("cooldown", phone))
    return max(0, int(until - time.time())) if until else 0


def send_code(phone, ip=None):
    """Generate, store and send a code. Raises OTPError when rate limited or SMS fails."""
    remaining = cooldown_remaining(phone)
    if remaining:
        raise OTPError(f"لطفاً {remaining} ثانیه دیگر دوباره تلاش کنید.", retry_after=remaining)

    if ip and _hit(_key("ip", ip), settings.OTP_MAX_SENDS_PER_IP_PER_HOUR, 3600):
        raise OTPError("تعداد درخواست‌ها از این شبکه بیش از حد مجاز است. بعداً تلاش کنید.", retry_after=3600)
    if _hit(_key("sends", phone), settings.OTP_MAX_SENDS_PER_PHONE_PER_HOUR, 3600):
        raise OTPError(
            "تعداد درخواست کد برای این شماره بیش از حد مجاز است. یک ساعت دیگر تلاش کنید.", retry_after=3600
        )

    code = f"{secrets.randbelow(10**settings.OTP_LENGTH):0{settings.OTP_LENGTH}d}"
    cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
    cache.set(_key("code", phone), _hash(phone, code), timeout=settings.OTP_TTL_SECONDS)
    cache.delete(_key("attempts", phone))
    cache.set(_key("cooldown", phone), time.time() + cooldown, timeout=cooldown)

    try:
        send_otp(phone, code)
    except SMSError:
        logger.exception("OTP SMS to %s failed", phone)
        cache.delete_many([_key("code", phone), _key("cooldown", phone)])
        raise OTPError("ارسال پیامک با خطا مواجه شد. لطفاً دوباره تلاش کنید.") from None


def verify_code(phone, code):
    """Return True when the code is correct (and burn it). Raises OTPError when locked/expired."""
    stored = cache.get(_key("code", phone))
    if not stored:
        raise OTPError("کد منقضی شده است. لطفاً کد جدید دریافت کنید.")

    code = str(code or "").translate(_DIGITS).strip()
    if constant_time_compare(stored, _hash(phone, code)):
        cache.delete_many([_key("code", phone), _key("attempts", phone)])
        return True

    if _hit(_key("attempts", phone), settings.OTP_MAX_ATTEMPTS - 1, settings.OTP_TTL_SECONDS):
        cache.delete_many([_key("code", phone), _key("attempts", phone)])
        raise OTPError("تعداد تلاش‌های ناموفق بیش از حد مجاز است. لطفاً کد جدید دریافت کنید.")
    return False
