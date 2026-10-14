"""Loopback-only fake provider. This module never calls a bank or sends money."""

import secrets

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .gateway import RequestResult, VerifyResult, VerifyStatus


class DemoGateway:
    name = "demo"

    def __init__(self):
        if not settings.DEBUG or not getattr(settings, "LOCAL_DEMO", False):
            raise ImproperlyConfigured("The demo gateway is only available in local demo settings.")

    def payment_url(self, authority):
        return f"{settings.PAYMENT_PUBLIC_ORIGIN}/payment/demo/{authority}/"

    def request_payment(self, amount_toman, description, callback_url, mobile=""):
        authority = "DEMO-" + secrets.token_hex(16)
        return RequestResult(ok=True, authority=authority, payment_url=self.payment_url(authority), code=100)

    def verify(self, amount_toman, authority):
        from .models import Payment

        payment = Payment.objects.get(authority=authority)
        if payment.gateway != "demo" or payment.amount != amount_toman:
            return VerifyResult(status=VerifyStatus.UNKNOWN)
        outcome = payment.raw_response.get("demo_outcome", "unknown")
        if outcome == "success":
            return VerifyResult(
                status=VerifyStatus.SUCCESS, code=100, ref_id="DEMO-" + str(payment.pk), raw={"demo": True}
            )
        if outcome == "failed":
            return VerifyResult(status=VerifyStatus.FAILED, code=-51, raw={"demo": True})
        return VerifyResult(status=VerifyStatus.UNKNOWN, raw={"demo": True, "demo_outcome": "unknown"})
