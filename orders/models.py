import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
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
        settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.PROTECT, null=True, blank=True
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

    checkout_key = models.UUIDField(null=True, blank=True, editable=False)
    checkout_fingerprint = models.CharField(max_length=64, blank=True, editable=False)
    review_reason = models.CharField(max_length=40, blank=True, editable=False)
    review_resolution = models.CharField(max_length=255, blank=True, editable=False)
    event_sequence = models.PositiveIntegerField(default=0, editable=False)
    carrier = models.CharField(max_length=80, blank=True)
    tracking_code = models.CharField(max_length=100, blank=True)

    coupon_code = models.CharField(max_length=40, blank=True)
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=0, default=0)

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
        permissions = [
            ("view_sales", "Can view financial sales dashboard"),
            ("cancel_paid_order", "Can cancel a paid order"),
            ("resolve_order_review", "Can resolve fulfillment/coupon review"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "checkout_key"], name="unique_customer_checkout_key")
        ]
        indexes = [
            models.Index(fields=["is_paid", "paid_at"], name="order_paid_at_idx"),
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
        return items_total - self.coupon_discount + self.post_price


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)

    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.SET_NULL, null=True)

    variant = models.ForeignKey("shop.ProductVariant", on_delete=models.PROTECT, null=True, blank=True)
    variant_sku = models.CharField(max_length=50, blank=True)
    variant_color = models.CharField(max_length=60, blank=True)
    variant_size = models.CharField(max_length=60, blank=True)

    product_name = models.CharField(max_length=250, verbose_name="نام محصول")

    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="قیمت واحد")

    quantity = models.PositiveIntegerField(default=1)

    total_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="قیمت کل")

    product_sku = models.CharField(max_length=50, verbose_name="کد محصول")
    address_obj = models.ForeignKey(
        "addresses.Address", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="آدرس ثبت‌شده"
    )

    class Meta:
        indexes = [models.Index(fields=["product", "order"], name="item_product_order_idx")]
        verbose_name = "آیتم سفارش"

        verbose_name_plural = "آیتم‌های سفارش"

    def __str__(self):
        return self.product_name


class Coupon(models.Model):
    PERCENT = "percent"
    FIXED = "fixed"
    code = models.CharField(max_length=40, unique=True)
    kind = models.CharField(max_length=10, choices=[(PERCENT, "درصد"), (FIXED, "مبلغ ثابت")])
    value = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    minimum_subtotal = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)]
    )
    maximum_discount = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    total_limit = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    per_user_limit = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(value__gt=0), name="coupon_positive_value"),
            models.CheckConstraint(
                condition=models.Q(kind="fixed") | models.Q(kind="percent", value__lte=100),
                name="coupon_valid_kind_value",
            ),
            models.CheckConstraint(
                condition=models.Q(minimum_subtotal__gte=0), name="coupon_min_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(maximum_discount__isnull=True) | models.Q(maximum_discount__gte=0),
                name="coupon_max_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(total_limit__isnull=True) | models.Q(total_limit__gte=1),
                name="coupon_total_positive",
            ),
            models.CheckConstraint(condition=models.Q(per_user_limit__gte=1), name="coupon_user_positive"),
            models.CheckConstraint(
                condition=models.Q(starts_at__isnull=True)
                | models.Q(ends_at__isnull=True)
                | models.Q(ends_at__gt=models.F("starts_at")),
                name="coupon_valid_dates",
            ),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError

        self.code = self.code.strip().upper()
        if not self.code or not all(c.isascii() and (c.isalnum() or c in "-_") for c in self.code):
            raise ValidationError({"code": "فقط حروف لاتین، عدد، خط تیره و زیرخط مجاز است."})
        super().clean()


class CouponUse(models.Model):
    RESERVED = "reserved"
    USED = "used"
    RELEASED = "released"
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name="uses")
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="coupon_use")
    state = models.CharField(max_length=10, choices=[(RESERVED, "رزرو"), (USED, "مصرف"), (RELEASED, "آزاد")])
    over_capacity = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["coupon", "state"])]

    def __str__(self):
        return f"{self.coupon_id}/{self.order_id}: {self.state}"


class OrderEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    sequence = models.PositiveIntegerField()
    previous_status = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    kind = models.CharField(
        max_length=20,
        choices=[
            ("created", "ایجاد"),
            ("status", "وضعیت"),
            ("tracking", "اطلاعات ارسال"),
            ("payment", "تایید پرداخت"),
        ],
    )
    carrier = models.CharField(max_length=80, blank=True)
    tracking_code = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(fields=["order", "sequence"], name="unique_order_event_sequence")
        ]

    def __str__(self):
        return f"{self.order_id}/{self.sequence}: {self.status}"


class OrderNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="order_notifications"
    )
    event = models.OneToOneField(OrderEvent, on_delete=models.CASCADE, related_name="notification")
    read_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created", "-pk"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self):
        return f"{self.user_id}/{self.event_id}"
