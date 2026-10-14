import uuid

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from addresses.models import Address as AddressModel
from shop.models import Product


class InvalidTransition(Exception):
    """Raised when an order is moved to a status that is not allowed from its current one."""


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_PREPARING = "preparing"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_NEEDS_REVIEW = "needs_review"

    STATUS_CHOICES = (
        (STATUS_PENDING, "در انتظار پرداخت"),
        (STATUS_PAID, "پرداخت شده"),
        (STATUS_PREPARING, "در حال آماده‌سازی"),
        (STATUS_SENT, "ارسال شده"),
        (STATUS_DELIVERED, "تحویل داده شده"),
        (STATUS_CANCELED, "لغو شده"),
        (STATUS_EXPIRED, "منقضی شده"),
        (STATUS_NEEDS_REVIEW, "نیازمند بررسی"),
    )

    # State machine: which statuses are reachable from each status.
    # - EXPIRED/CANCELED -> PAID/NEEDS_REVIEW exists because a gateway callback can
    #   arrive after the reservation expired (or after the user canceled). The money
    #   has already been taken, so we must record it instead of rejecting it.
    # - NEEDS_REVIEW = paid, but stock could not be re-reserved -> admin must ship
    #   (after restocking) or refund.
    TRANSITIONS = {
        STATUS_PENDING: {STATUS_PAID, STATUS_NEEDS_REVIEW, STATUS_CANCELED, STATUS_EXPIRED},
        STATUS_EXPIRED: {STATUS_PAID, STATUS_NEEDS_REVIEW},
        STATUS_CANCELED: {STATUS_PAID, STATUS_NEEDS_REVIEW},
        STATUS_NEEDS_REVIEW: {STATUS_PREPARING, STATUS_CANCELED},
        STATUS_PAID: {STATUS_PREPARING, STATUS_CANCELED},
        STATUS_PREPARING: {STATUS_SENT, STATUS_CANCELED},
        STATUS_SENT: {STATUS_DELIVERED},
        STATUS_DELIVERED: set(),
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.CASCADE, null=True, blank=True
    )
    # اضافه کردن فیلد زیر:
    address_obj = models.ForeignKey(
        AddressModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="آدرس انتخاب‌شده",
    )
    first_name = models.CharField(max_length=100, verbose_name="نام")
    last_name = models.CharField(max_length=100, verbose_name="نام خانوادگی")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    address = models.TextField(verbose_name="آدرس")
    postal_code = models.CharField(max_length=20, verbose_name="کد پستی")

    order_number = models.CharField(max_length=32, unique=True, editable=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    post_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="هزینه ارسال")

    total_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="مبلغ کل")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    authority = models.CharField(max_length=255, blank=True, default="")
    is_paid = models.BooleanField(default=False)
    ref_id = models.CharField(max_length=255, blank=True)
    stock_reserved = models.BooleanField(
        default=False,
        verbose_name="موجودی رزرو شده",
        help_text="True while this order holds (has deducted) stock for its items.",
    )
    reserved_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="مهلت پرداخت",
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پرداخت")

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created"]),
            models.Index(fields=["status", "reserved_until"], name="order_status_reserved_idx"),
        ]
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # تولید شماره سفارش یکتا (مثال: ORD-8F2A1C)
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # State machine helpers
    # ------------------------------------------------------------------

    def can_transition_to(self, new_status):
        return new_status in self.TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status):
        """Change status in memory after validating the transition. Caller saves."""
        if not self.can_transition_to(new_status):
            raise InvalidTransition(f"{self.status} -> {new_status}")
        self.status = new_status

    @property
    def is_reservation_expired(self):
        return self.reserved_until is not None and self.reserved_until <= timezone.now()

    @property
    def is_payable(self):
        return (
            self.status == self.STATUS_PENDING
            and not self.is_paid
            and self.stock_reserved
            and not self.is_reservation_expired
        )

    @property
    def is_cancelable_by_user(self):
        return self.status == self.STATUS_PENDING and not self.is_paid

    def calculate_total(self):
        items_total = self.items.aggregate(total=Sum("total_price"))["total"] or 0
        return items_total + self.post_price


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)

    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.SET_NULL, null=True)

    product_name = models.CharField(max_length=250, verbose_name="نام محصول")

    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="قیمت واحد")

    quantity = models.PositiveIntegerField(default=1)

    total_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="قیمت کل")

    product_sku = models.CharField(max_length=50, verbose_name="کد محصول")
    address_obj = models.ForeignKey(
        "addresses.Address", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="آدرس ثبت‌شده"
    )

    class Meta:
        verbose_name = "آیتم سفارش"

        verbose_name_plural = "آیتم‌های سفارش"

    def __str__(self):
        return self.product_name
