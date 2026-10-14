"""Durable settlement first, recoverable fulfillment second.

Verification serializes on Payment. It never locks Order or emits notifications.
After that transaction commits, fulfillment locks Order -> Payment. A notification
failure cannot roll back the already committed external financial fact.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from orders.models import Order
from orders.services import expire_order_if_needed, mark_order_paid

from .gateway import VerifyStatus, get_gateway
from .models import Payment

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    pass


def callback_url_for_request(request):
    path = reverse("payment:verify")
    origin = getattr(settings, "PAYMENT_PUBLIC_ORIGIN", "")
    return origin + path if origin else request.build_absolute_uri(path)


@dataclass(frozen=True)
class CallbackOutcome:
    status: str
    payment: Payment
    order: Order

    @property
    def succeeded(self):
        return self.status == Payment.STATUS_SUCCESS


def start_payment(order, user, callback_url):
    if order.user_id != user.pk:
        raise PaymentError("سفارش متعلق به این کاربر نیست.")
    expire_order_if_needed(order)
    gateway = get_gateway()
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.user_id != user.pk:
            raise PaymentError("سفارش متعلق به این کاربر نیست.")
        if order.is_paid:
            raise PaymentError("این سفارش قبلاً پرداخت شده است.")
        if not order.is_payable:
            raise PaymentError("مهلت پرداخت این سفارش تمام شده یا سفارش لغو شده است.")
        active = (
            order.payments.filter(status__in=[Payment.STATUS_PENDING, Payment.STATUS_UNKNOWN])
            .order_by("pk")
            .first()
        )
        if active:
            if active.status == Payment.STATUS_UNKNOWN:
                raise PaymentError("نتیجه پرداخت قبلی نامشخص است؛ ابتدا آن را پیگیری کنید.")
            if not active.authority:
                raise PaymentError("درخواست قبلی هنوز در حال پردازش است؛ پرداخت تازه آغاز نشد.")
            return gateway.payment_url(active.authority)
        payment = Payment.objects.create(
            order=order,
            user=user,
            amount=order.total_price,
            gateway=getattr(gateway, "name", Payment.GATEWAY_ZARINPAL),
        )

    result = gateway.request_payment(
        amount_toman=payment.amount,
        description=f"پرداخت سفارش {order.order_number}",
        callback_url=callback_url,
        mobile=getattr(user, "phone", ""),
    )
    if not result.ok:
        payment.status = Payment.STATUS_UNKNOWN if result.unknown else Payment.STATUS_FAILED
        payment.gateway_code, payment.raw_response = result.code, result.raw
        payment.save(update_fields=["status", "gateway_code", "raw_response", "updated_at"])
        raise PaymentError(result.error or "خطا در اتصال به درگاه.")
    payment.authority = result.authority
    payment.save(update_fields=["authority", "updated_at"])
    return result.payment_url


def _verify_locked(payment):
    if payment.status in (Payment.STATUS_SUCCESS, Payment.STATUS_FAILED):
        return payment.status
    result = get_gateway().verify(amount_toman=payment.amount, authority=payment.authority)
    payment.gateway_code, payment.raw_response = result.code, result.raw
    if result.status == VerifyStatus.SUCCESS:
        payment.status, payment.ref_id = Payment.STATUS_SUCCESS, result.ref_id
        payment.card_pan, payment.verified_at = result.card_pan, timezone.now()
        payment.needs_reconciliation = True
    elif result.status == VerifyStatus.FAILED:
        payment.status = Payment.STATUS_FAILED
    else:
        payment.status = Payment.STATUS_UNKNOWN
    payment.save()
    return payment.status


def fulfill_settled_payment(payment_id):
    """Safe to retry; only succeeds after fulfillment/refund obligation is committed."""
    try:
        scope = Payment.objects.values("order_id").get(pk=payment_id)
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=scope["order_id"])
            payment = Payment.objects.select_for_update().get(pk=payment_id)
            if payment.status != Payment.STATUS_SUCCESS or not payment.needs_reconciliation:
                return
            if order.is_paid and order.ref_id != payment.ref_id:
                from .refunds import request_refund

                request_refund(payment, reason="duplicate payment")
            else:
                mark_order_paid(order, payment.ref_id)
                # Paid cancellation remains terminal; replay never reopens fulfillment.
                if order.status == Order.STATUS_CANCELED:
                    from .refunds import request_refund

                    request_refund(payment, reason="settlement on canceled paid order")
            payment.needs_reconciliation = False
            # request_refund may have updated needs_refund separately; do not overwrite it.
            payment.save(update_fields=["needs_reconciliation", "updated_at"])
    except Exception:
        logger.exception("Settled payment %s still needs fulfillment reconciliation", payment_id)


def process_callback(authority):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(authority=authority)
        _verify_locked(payment)
    # The settlement transaction has exited before any optional order side effects.
    fulfill_settled_payment(payment.pk)
    payment.refresh_from_db()
    return CallbackOutcome(payment.status, payment, Order.objects.get(pk=payment.order_id))


def reconcile_payment(payment_id):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment_id)
        if payment.authority:
            _verify_locked(payment)
    fulfill_settled_payment(payment_id)
    payment.refresh_from_db()
    return payment.status


def reconcile_stale_payments(older_than_minutes=15):
    cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
    ids = (
        Payment.objects.filter(
            Q(
                status__in=[Payment.STATUS_PENDING, Payment.STATUS_UNKNOWN],
                authority__isnull=False,
                created_at__lte=cutoff,
            )
            | Q(status=Payment.STATUS_SUCCESS, needs_reconciliation=True)
        )
        .exclude(authority="")
        .values_list("pk", flat=True)
    )
    results = {}
    for pk in list(ids):
        state = reconcile_payment(pk)
        results[state] = results.get(state, 0) + 1
    return results
