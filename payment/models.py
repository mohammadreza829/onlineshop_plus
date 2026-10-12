from django.db import models
from django.conf import settings
from orders.models import Order


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_PENDING, "در انتظار پرداخت"),
        (STATUS_SUCCESS, "موفق"),
        (STATUS_FAILED, "ناموفق"),
    )

    GATEWAY_ZARINPAL = "zarinpal"
    GATEWAY_CHOICES = (
        (GATEWAY_ZARINPAL, "زرین‌پال"),
    )

    order = models.ForeignKey(
        Order,
        related_name="payments",
        on_delete=models.CASCADE,
        verbose_name="سفارش"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="کاربر"
    )
    gateway = models.CharField(
        max_length=50,
        choices=GATEWAY_CHOICES,
        default=GATEWAY_ZARINPAL,
        verbose_name="درگاه پرداخت"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="مبلغ (تومان)"
    )
    authority = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        verbose_name="کد پیگیری درگاه (Authority)"
    )
    ref_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="شماره مرجع/تراکنش (RefID)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="وضعیت"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"

    def __str__(self):
        return f"Payment #{self.id} for Order #{self.order.order_number}"