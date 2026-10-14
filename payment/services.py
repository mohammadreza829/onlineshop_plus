"""
Payment flow.

start_payment()     -> creates a Payment row, asks the gateway for an authority.
process_callback()  -> verifies a payment exactly once and updates the order.
reconcile_payment() -> re-checks payments stuck in PENDING/UNKNOWN (cron).

Idempotency: the Payment row is locked with SELECT ... FOR UPDATE for the whole
verification, so two concurrent callbacks (double click, browser retry, our
reconcile job) serialize; the second one sees SUCCESS/FAILED and returns the
stored result without calling the gateway or touching stock again.
The lock is held during one bounded HTTP call (timeout in settings.ZARINPAL);
that trade-off is deliberate: correctness of money > a few seconds of waiting.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from orders.models import Order
from orders.services import expire_order_if_needed, mark_order_paid

from .gateway import VerifyStatus, get_gateway
from .models import Payment

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    pass


@dataclass(frozen=True)
class CallbackOutcome:
    status: str  # one of Payment.STATUS_*
    payment: Payment
    order: Order

    @property
    def succeeded(self):
        return self.status == Payment.STATUS_SUCCESS


def start_payment(order, user, callback_url):
    """Return the gateway URL the customer must be redirected to."""
    expire_order_if_needed(order)
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.is_paid:
            raise PaymentError("این سفارش قبلاً پرداخت شده است.")
        if not order.is_payable:
            raise PaymentError("مهلت پرداخت این سفارش به پایان رسیده یا سفارش لغو شده است.")
        payment = Payment.objects.create(order=order, user=user, amount=order.total_price)

    # HTTP call outside the transaction: no row lock is held while the gateway answers.
    result = get_gateway().request_payment(
        amount_toman=payment.amount,
        description=f"پرداخت سفارش {order.order_number}",
        callback_url=callback_url,
        mobile=getattr(user, "phone", ""),
    )
    if not result.ok:
        payment.status = Payment.STATUS_FAILED
        payment.gateway_code = result.code
        payment.raw_response = result.raw
        payment.save(update_fields=["status", "gateway_code", "raw_response", "updated_at"])
        raise PaymentError(result.error or "خطا در اتصال به درگاه پرداخت.")

    payment.authority = result.authority
    payment.save(update_fields=["authority", "updated_at"])
    return result.payment_url


def _verify_locked(payment):
    """payment must be locked (select_for_update) by the caller's transaction."""
    if payment.status in (Payment.STATUS_SUCCESS, Payment.STATUS_FAILED):
        return payment.status

    # Always ask the gateway: the `Status` query param of the callback is user
    # controlled, the verify endpoint is the only source of truth.
    result = get_gateway().verify(amount_toman=payment.amount, authority=payment.authority)
    payment.gateway_code = result.code
    payment.raw_response = result.raw

    if result.status == VerifyStatus.SUCCESS:
        payment.status = Payment.STATUS_SUCCESS
        payment.ref_id = result.ref_id
        payment.card_pan = result.card_pan
        payment.verified_at = timezone.now()
        order = Order.objects.select_for_update().get(pk=payment.order_id)
        if order.is_paid and order.ref_id and order.ref_id != result.ref_id:
            # Customer paid the same order twice (two tabs). Keep the money on record.
            payment.needs_refund = True
            logger.critical(
                "Duplicate payment %s for already-paid order %s -> refund needed",
                payment.pk,
                order.order_number,
            )
        else:
            mark_order_paid(order, result.ref_id)
    elif result.status == VerifyStatus.FAILED:
        payment.status = Payment.STATUS_FAILED
    else:
        payment.status = Payment.STATUS_UNKNOWN

    payment.save()
    return payment.status


def process_callback(authority):
    """Handle the browser coming back from the gateway. Raises Payment.DoesNotExist."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(authority=authority)
        status = _verify_locked(payment)
    payment.refresh_from_db()
    order = Order.objects.get(pk=payment.order_id)
    return CallbackOutcome(status=status, payment=payment, order=order)


def reconcile_payment(payment_id):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment_id)
        if not payment.authority:
            return payment.status
        return _verify_locked(payment)


def reconcile_stale_payments(older_than_minutes=15):
    """Verify payments whose callback never arrived (closed tab) or ended UNKNOWN."""
    cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
    ids = list(
        Payment.objects.filter(
            status__in=[Payment.STATUS_PENDING, Payment.STATUS_UNKNOWN],
            authority__isnull=False,
            created_at__lte=cutoff,
        ).values_list("pk", flat=True)
    )
    results = {}
    for payment_id in ids:
        status = reconcile_payment(payment_id)
        results[status] = results.get(status, 0) + 1
    return results
