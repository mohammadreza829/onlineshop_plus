"""Audit bookkeeping only: no gateway refund API and no transfer of money."""

import unicodedata

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .models import Payment, RefundRequest


def request_refund(payment, *, actor=None, reason):
    """Caller holds the order lock; acquire payment second, consistently."""
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != Payment.STATUS_SUCCESS:
        return None
    refund, _ = RefundRequest.objects.get_or_create(
        payment=payment,
        defaults={"amount": payment.amount, "reason": reason[:255], "requested_by": actor},
    )
    payment.needs_refund = refund.status != "confirmed"
    payment.save(update_fields=["needs_refund", "updated_at"])
    return refund


@transaction.atomic
def confirm_bank_refund(*, refund, actor, bank_reference):
    if not actor.is_active or not actor.has_perm("payment.confirm_refundrequest"):
        raise PermissionDenied("مجوز تایید مالی لازم است.")
    reference = str(bank_reference or "").strip()
    if (
        not reference
        or len(reference) > 128
        or any(unicodedata.category(c).startswith("C") for c in reference)
    ):
        raise ValueError("سند معتبر بازپرداخت انجام‌شده را وارد کنید.")
    # Order -> Payment -> Refund, same lock ordering as cancellation/recovery.
    from orders.models import Order

    Order.objects.select_for_update().get(pk=refund.payment.order_id)
    payment = Payment.objects.select_for_update().get(pk=refund.payment_id)
    current = RefundRequest.objects.select_for_update().get(pk=refund.pk)
    if current.status == "confirmed":
        if current.bank_reference != reference:
            raise ValueError("این بازپرداخت قبلاً با سند دیگری ثبت شده است.")
        return current
    if payment.status != Payment.STATUS_SUCCESS or current.amount != payment.amount:
        raise ValueError("ارتباط یا مبلغ پرداخت نیازمند تطبیق است.")
    if reference == payment.ref_id:
        raise ValueError("شناسه برداشت اولیه، سند بازپرداخت نیست.")
    current.bank_reference = reference
    current.confirmed_by = actor
    current.confirmed_at = timezone.now()
    current.status = "confirmed"
    current.save(update_fields=["bank_reference", "confirmed_by", "confirmed_at", "status"])
    payment.needs_refund = False
    payment.save(update_fields=["needs_refund", "updated_at"])
    return current
