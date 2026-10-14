"""OTP payloads are encrypted before entering the broker. Never log plaintext codes."""

import base64
import hashlib
import json
import time

from celery import Task, shared_task
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import constant_time_compare
from redis.exceptions import RedisError

from .sms import SMSError, deliver_otp


def cipher():
    key = hashlib.sha256(("otp-task-v1:" + settings.SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_payload(phone, code):
    return (
        cipher()
        .encrypt(
            json.dumps(
                {"phone": phone, "code": code, "expires_at": time.time() + settings.OTP_TTL_SECONDS}
            ).encode()
        )
        .decode()
    )


def decode_payload(payload):
    try:
        data = json.loads(cipher().decrypt(payload.encode(), ttl=settings.OTP_TTL_SECONDS))
        if data["expires_at"] <= time.time():
            return None
        return data
    except (InvalidToken, ValueError, KeyError, TypeError):
        return None


def current_challenge(data):
    from .otp import _hash, _key

    expected = _hash(data["phone"], data["code"])
    actual = cache.get(_key("code", data["phone"]))
    return bool(actual and constant_time_compare(actual, expected))


class OTPDeliveryTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from .otp import _key, _phone_lock

        data = decode_payload(args[0]) if args else None
        if data:
            with _phone_lock(data["phone"]):
                if current_challenge(data):
                    cache.delete_many([_key("code", data["phone"]), _key("cooldown", data["phone"])])


@shared_task(
    bind=True,
    base=OTPDeliveryTask,
    autoretry_for=(SMSError, RedisError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    ignore_result=True,
)
def deliver_otp_task(self, encrypted_payload):
    data = decode_payload(encrypted_payload)
    if not data or not current_challenge(data):
        return "stale"
    delivered_key = "otp:delivered:" + hashlib.sha256(encrypted_payload.encode()).hexdigest()
    if cache.get(delivered_key):
        return "already_delivered"
    deliver_otp(data["phone"], data["code"])
    cache.set(delivered_key, True, timeout=settings.OTP_TTL_SECONDS)
    return "sent"
