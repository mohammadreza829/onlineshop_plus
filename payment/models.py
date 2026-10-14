from django.conf import settings
from django.db import models

from orders.models import Order


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    # Gateway did not give a definitive answer (timeout, 5xx, unexpected code).
    # The money may or may not have been taken -> must be re-verified later
    # (see `manage.py reconcile_payments`). Never treat this as failed.
    STATUS_UNKNOWN = "unknown"

    STATUS_CHOICES = (
        (STATUS_PENDING, "در انتظار پرداخت"),
        (STATUS_SUCCESS, "موفق"),
        (STATUS_FAILED, "ناموفق"),
        (STATUS_UNKNOWN, "نامشخص (نیازمند استعلام)"),
    )

    GATEWAY_ZARINPAL = "zarinpal"
    GATEWAY_CHOICES = ((GATEWAY_ZARINPAL, "زرین‌پال"), ("demo", "شبیه‌سازی محلی"))

    order = models.ForeignKey(Order, related_name="payments", on_delete=models.PROTECT, verbose_name="سفارش")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="کاربر"
    )
    gateway = models.CharField(
        max_length=50, choices=GATEWAY_CHOICES, default=GATEWAY_ZARINPAL, verbose_name="درگاه پرداخت"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="مبلغ (تومان)")
    authority = models.CharField(
        max_length=255, blank=True, null=True, unique=True, verbose_name="کد پیگیری درگاه (Authority)"
    )
    ref_id = models.CharField(
        max_length=255, blank=True, default="", verbose_name="شماره مرجع/تراکنش (RefID)"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="وضعیت"
    )
    card_pan = models.CharField(max_length=32, blank=True, verbose_name="شماره کارت (ماسک‌شده)")
    gateway_code = models.IntegerField(null=True, blank=True, verbose_name="کد پاسخ درگاه")
    raw_response = models.JSONField(default=dict, blank=True, verbose_name="پاسخ خام درگاه")
    needs_refund = models.BooleanField(
        default=False,
        verbose_name="نیازمند بازگشت وجه",
        help_text="Set when money was taken but the order was already paid by another payment.",
    )
    needs_reconciliation = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تایید")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="payment_status_created_idx"),
            models.Index(fields=["status", "verified_at"], name="payment_verified_at_idx"),
        ]
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"

    def __str__(self):
        return f"Payment #{self.id} for Order #{self.order.order_number}"


class RefundRequest(models.Model):
    """Bookkeeping of a bank refund; saving this model NEVER transfers money."""

    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="refund")
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    reason = models.CharField(max_length=255)
    status = models.CharField(
        max_length=12,
        choices=[("requested", "در انتظار بازپرداخت"), ("confirmed", "بازپرداخت ثبت‌شده")],
        default="requested",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_refunds",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_refunds",
    )
    bank_reference = models.CharField(max_length=128, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        permissions = [("confirm_refundrequest", "Can record an already completed bank refund")]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="refund_amount_positive"),
        ]

    def __str__(self):
        return f"Refund for payment #{self.payment_id}: {self.status}"
