"""
Thin Zarinpal (REST v4) client.

Why not the `zarinpal-py-sdk` package?
- it sends requests without a timeout (a slow gateway can hang a worker forever);
- it turns every non-2xx answer into a bare RuntimeError, so a definitive
  "payment failed" (-51) is indistinguishable from a network error.
Both matter for money, so we talk to the documented REST endpoints directly
and classify every answer as SUCCESS / FAILED / UNKNOWN.

Docs: https://www.zarinpal.com/docs/paymentGateway/
"""

import logging
from dataclasses import dataclass, field
from enum import StrEnum

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Shop prices are stored in Toman, Zarinpal's default currency is Rial.
# We convert explicitly instead of relying on the optional `currency` param,
# so request and verify always use the same unit.
TOMAN_TO_RIAL = 10

# Verify codes that are a definitive "no money was captured".
# -51: payment failed / canceled by user, -53: authority belongs to another merchant,
# -54: invalid authority, -55: transaction not found, -50: amount mismatch.
DEFINITIVE_FAILURE_CODES = {-50, -51, -53, -54, -55}
SUCCESS_CODES = {100, 101}  # 101 = already verified (idempotent repeat)


class VerifyStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RequestResult:
    ok: bool
    authority: str = ""
    payment_url: str = ""
    code: int | None = None
    error: str = ""
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class VerifyResult:
    status: VerifyStatus
    ref_id: str = ""
    card_pan: str = ""
    code: int | None = None
    raw: dict = field(default_factory=dict)


class GatewayUnavailable(Exception):
    """Network error, timeout, 5xx or a non-JSON body."""


def _extract_code(body):
    data = body.get("data")
    if isinstance(data, dict) and data.get("code") is not None:
        return data.get("code")
    errors = body.get("errors")
    if isinstance(errors, dict) and errors.get("code") is not None:
        return errors.get("code")
    return None


class ZarinpalGateway:
    def __init__(self, merchant_id, sandbox=False, timeout=(5, 20)):
        self.merchant_id = merchant_id
        self.timeout = timeout
        self.base_url = "https://sandbox.zarinpal.com" if sandbox else "https://payment.zarinpal.com"

    def _post(self, path, payload):
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(
                url,
                json={"merchant_id": self.merchant_id, **payload},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise GatewayUnavailable(str(exc)) from exc

        if response.status_code >= 500:
            raise GatewayUnavailable(f"HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise GatewayUnavailable(f"non-JSON response (HTTP {response.status_code})") from exc
        if not isinstance(body, dict):
            raise GatewayUnavailable("unexpected response shape")
        return body

    def payment_url(self, authority):
        return f"{self.base_url}/pg/StartPay/{authority}"

    def request_payment(self, amount_toman, description, callback_url, mobile=""):
        payload = {
            "amount": int(amount_toman) * TOMAN_TO_RIAL,
            "description": description,
            "callback_url": callback_url,
        }
        if mobile:
            payload["metadata"] = {"mobile": mobile}
        try:
            body = self._post("/pg/v4/payment/request.json", payload)
        except GatewayUnavailable as exc:
            logger.warning("Zarinpal request unavailable: %s", exc)
            return RequestResult(ok=False, error="درگاه پرداخت در دسترس نیست.")

        code = _extract_code(body)
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        if code == 100 and data.get("authority"):
            authority = data["authority"]
            return RequestResult(
                ok=True, authority=authority, payment_url=self.payment_url(authority), code=code, raw=body
            )
        logger.error("Zarinpal request rejected: code=%s body=%s", code, body)
        return RequestResult(ok=False, code=code, error="درخواست پرداخت توسط درگاه رد شد.", raw=body)

    def verify(self, amount_toman, authority):
        payload = {"amount": int(amount_toman) * TOMAN_TO_RIAL, "authority": authority}
        try:
            body = self._post("/pg/v4/payment/verify.json", payload)
        except GatewayUnavailable as exc:
            logger.warning("Zarinpal verify unavailable for %s: %s", authority, exc)
            return VerifyResult(status=VerifyStatus.UNKNOWN, raw={"error": str(exc)})

        code = _extract_code(body)
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        if code in SUCCESS_CODES and data.get("ref_id"):
            return VerifyResult(
                status=VerifyStatus.SUCCESS,
                ref_id=str(data["ref_id"]),
                card_pan=str(data.get("card_pan") or ""),
                code=code,
                raw=body,
            )
        if code in DEFINITIVE_FAILURE_CODES:
            if code == -50:
                logger.error("Zarinpal amount mismatch for authority %s", authority)
            return VerifyResult(status=VerifyStatus.FAILED, code=code, raw=body)

        logger.error("Zarinpal verify returned unexpected code=%s for %s", code, authority)
        return VerifyResult(status=VerifyStatus.UNKNOWN, code=code, raw=body)


def get_gateway():
    conf = settings.ZARINPAL
    return ZarinpalGateway(
        merchant_id=conf["merchant_id"],
        sandbox=conf["sandbox"],
        timeout=(conf.get("connect_timeout", 5), conf.get("read_timeout", 20)),
    )
