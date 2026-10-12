# from email.headerregistry import Address
import uuid
from django.db import models
from django.conf import settings
from shop.models import Product
from django.db.models import Sum
from addresses.models import Address as AddressModel


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_PREPARING = "preparing"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "در انتظار پرداخت"),
        (STATUS_PAID, "پرداخت شده"),
        (STATUS_PREPARING, "در حال آماده‌سازی"),
        (STATUS_SENT, "ارسال شده"),
        (STATUS_DELIVERED, "تحویل داده شده"),
        (STATUS_CANCELED, "لغو شده"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="orders",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    # اضافه کردن فیلد زیر:
    address_obj = models.ForeignKey(AddressModel,
                                    on_delete=models.SET_NULL,
                                    null=True,
                                    blank=True,
                                    related_name='orders',
                                    verbose_name='آدرس انتخاب‌شده'
                                    )
    first_name = models.CharField(max_length=100, verbose_name="نام")
    last_name = models.CharField(max_length=100, verbose_name="نام خانوادگی")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    address = models.TextField(verbose_name="آدرس")
    postal_code = models.CharField(max_length=20, verbose_name="کد پستی")

    order_number = models.CharField(
        max_length=32,
        unique=True,
        editable=False
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    post_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="هزینه ارسال"
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="مبلغ کل"
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    authority = models.CharField(max_length=255, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    ref_id = models.CharField(max_length=255, blank=True)
    stock_updated = models.BooleanField(
        default=False,
        verbose_name="موجودی بروزرسانی شده"
    )

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created"]),
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

    def calculate_total(self):
        items_total = (
            self.items.aggregate(
                total=Sum("total_price")
            )["total"] or 0
        )
        return items_total + self.post_price


class OrderItem(models.Model):

    order = models.ForeignKey(

        Order,

        related_name="items",

        on_delete=models.CASCADE

    )

    product = models.ForeignKey(

        Product,

        related_name="order_items",

        on_delete=models.SET_NULL,

        null=True

    )

    product_name = models.CharField(

        max_length=250,

        verbose_name="نام محصول"

    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="قیمت واحد"
    )

    quantity = models.PositiveIntegerField(

        default=1

    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="قیمت کل"
    )

    product_sku = models.CharField(
        max_length=50,
        verbose_name="کد محصول"
    )
    address_obj = models.ForeignKey(
        'addresses.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="آدرس ثبت‌شده"
    )

    class Meta:

        verbose_name = "آیتم سفارش"

        verbose_name_plural = "آیتم‌های سفارش"

    def __str__(self):

        return self.product_name
