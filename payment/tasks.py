from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .models import Payment
from .services import reconcile_payment


@shared_task(ignore_result=True)
def reconcile_one(payment_id):
    try:
        return reconcile_payment(payment_id)
    except Payment.DoesNotExist:
        return "deleted"


@shared_task(ignore_result=True)
def dispatch_stale_payments():
    ids = (
        Payment.objects.filter(
            Q(
                status__in=[Payment.STATUS_PENDING, Payment.STATUS_UNKNOWN],
                authority__isnull=False,
                updated_at__lte=timezone.now() - timedelta(minutes=15),
            )
            | Q(status=Payment.STATUS_SUCCESS, needs_reconciliation=True),
        )
        .exclude(authority="")
        .order_by("updated_at", "pk")
        .values_list("pk", flat=True)[:500]
    )
    for payment_id in ids:
        reconcile_one.delay(payment_id)
