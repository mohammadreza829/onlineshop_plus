"""
SMS sending. Backend is chosen by settings.SMS_BACKEND:
- "console": log the message (development / tests, never in production)
- "smsir":   SMS.ir REST API v1 (https://app.sms.ir/developer)

We call the REST API with `requests` directly instead of `smsir-python`
because that package sends without a timeout and adds a new log handler on
every instantiation.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SMSIR_BASE_URL = "https://api.sms.ir/v1"


class SMSError(Exception):
    pass


def _smsir_post(path, payload):
    try:
        response = requests.post(
            f"{SMSIR_BASE_URL}{path}",
            json=payload,
            headers={"X-API-KEY": settings.SMS_IR_API_KEY, "Accept": "application/json"},
            timeout=(5, 10),
        )
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise SMSError(f"sms.ir unreachable: {exc}") from exc
    if response.status_code != 200 or body.get("status") != 1:
        raise SMSError(f"sms.ir rejected: HTTP {response.status_code} {body.get('message')}")
    return body


def deliver_otp(phone, code):
    backend = settings.SMS_BACKEND
    if backend == "console":
        logger.warning("[console SMS] OTP for %s: %s", phone, code)
        if settings.DEBUG and getattr(settings, "SMS_CONSOLE_SHOW_OTP", False):
            # Explicit local development transport, not a global log-filter bypass.
            # Omit the phone and never enable on shared/public environments.
            print(f"[local development OTP] {code}", flush=True)
        return
    if backend != "smsir":
        raise SMSError(f"unknown SMS_BACKEND {backend!r}")

    if settings.SMS_IR_TEMPLATE_ID:
        # Recommended: the "verify" (template) API is delivered even to numbers
        # that blocked advertising SMS, and needs no line number.
        _smsir_post(
            "/send/verify",
            {
                "mobile": phone,
                "templateId": int(settings.SMS_IR_TEMPLATE_ID),
                "parameters": [{"name": settings.SMS_IR_TEMPLATE_PARAM, "value": code}],
            },
        )
    else:
        _smsir_post(
            "/send/bulk",
            {
                "lineNumber": int(settings.SMS_IR_LINE_NUMBER),
                "messageText": f"کد ورود شما: {code}\nاین کد را در اختیار دیگران قرار ندهید.",
                "mobiles": [phone],
            },
        )


def send_otp(phone, code):
    if not settings.SMS_ASYNC:
        return deliver_otp(phone, code)
    from .tasks import deliver_otp_task, encrypt_payload

    try:
        deliver_otp_task.apply_async(
            args=[encrypt_payload(phone, code)],
            expires=settings.OTP_TTL_SECONDS,
            argsrepr="('<encrypted OTP>',)",
        )
    except Exception as exc:
        raise SMSError("SMS queue unavailable") from exc
