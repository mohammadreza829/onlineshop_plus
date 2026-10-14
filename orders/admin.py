from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html

from .models import Coupon, CouponUse, Order, OrderItem
from .services import OrderActionError, advance_order, retry_reservation

# ==========================================
# Order Item Inline
# ==========================================


class OrderItemInline(admin.TabularInline):
    model = OrderItem

    extra = 0

    can_delete = False

    readonly_fields = (
        "product",
        "variant",
        "variant_sku",
        "variant_color",
        "variant_size",
        "product_sku",
        "product_name",
        "price",
        "quantity",
        "total_price",
    )

    def has_add_permission(self, request, obj=None):
        return False


# ==========================================
# Order Admin
# ==========================================


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "colored_status",
        "customer",
        "phone",
        "items_count",
        "total_price",
        "post_price",
        "created",
    )

    list_filter = (
        "status",
        "is_paid",
        "created",
        "user",
    )

    search_fields = (
        "id",
        "order_number",
        "ref_id",
        "first_name",
        "last_name",
        "phone",
        "postal_code",
    )

    ordering = ("-created",)

    date_hierarchy = "created"

    # Status / payment fields are read-only: they may only change through the
    # actions below, which go through the state machine and keep stock consistent.
    readonly_fields = (
        "total_price",
        "post_price",
        "carrier",
        "tracking_code",
        "coupon_code",
        "coupon_discount",
        "order_number",
        "status",
        "is_paid",
        "paid_at",
        "ref_id",
        "stock_reserved",
        "reserved_until",
        "created",
        "updated",
        "items_count",
    )

    fieldsets = (
        (
            "اطلاعات مشتری",
            {
                "fields": (
                    "user",
                    "first_name",
                    "last_name",
                    "phone",
                    "address",
                    "postal_code",
                )
            },
        ),
        (
            "وضعیت سفارش",
            {
                "fields": (
                    "order_number",
                    "status",
                    "is_paid",
                    "paid_at",
                    "ref_id",
                    "stock_reserved",
                    "reserved_until",
                )
            },
        ),
        (
            "مبالغ",
            {
                "fields": (
                    "post_price",
                    "total_price",
                    "items_count",
                )
            },
        ),
        (
            "تاریخ‌ها",
            {
                "fields": (
                    "created",
                    "updated",
                )
            },
        ),
    )

    inlines = [
        OrderItemInline,
    ]

    actions = (
        "mark_preparing",
        "mark_sent",
        "mark_delivered",
        "mark_canceled",
        "retry_stock_reservation",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.select_related("user").prefetch_related("items").annotate(items_total=Count("items"))

    def customer(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    customer.short_description = "مشتری"

    def items_count(self, obj):
        return obj.items_total

    items_count.short_description = "تعداد آیتم"

    def colored_status(self, obj):
        colors = {
            "pending": "#ff9800",
            "paid": "#4caf50",
            "sent": "#2196f3",
            "canceled": "#f44336",
        }

        return format_html(
            '<strong style="color:{};">{}</strong>',
            colors.get(obj.status, "#000"),
            obj.get_status_display(),
        )

    colored_status.short_description = "وضعیت"

    def _apply(self, request, queryset, func, *args):
        done, failed = 0, []
        for order in queryset:
            try:
                func(order, *args)
                done += 1
            except OrderActionError as exc:
                failed.append(f"{order.order_number}: {exc}")
        if done:
            self.message_user(request, f"{done} سفارش بروزرسانی شد.", messages.SUCCESS)
        for line in failed:
            self.message_user(request, line, messages.ERROR)

    @admin.action(description="تغییر وضعیت به در حال آماده‌سازی")
    def mark_preparing(self, request, queryset):
        self._apply(request, queryset, advance_order, Order.STATUS_PREPARING)

    @admin.action(description="تغییر وضعیت به ارسال شده")
    def mark_sent(self, request, queryset):
        self._apply(request, queryset, advance_order, Order.STATUS_SENT)

    @admin.action(description="تغییر وضعیت به تحویل داده شده")
    def mark_delivered(self, request, queryset):
        self._apply(request, queryset, advance_order, Order.STATUS_DELIVERED)

    @admin.action(description="لغو سفارش (و آزادسازی موجودی)")
    def mark_canceled(self, request, queryset):
        self._apply(request, queryset, advance_order, Order.STATUS_CANCELED)

    @admin.action(description="تلاش مجدد برای رزرو موجودی (سفارش‌های نیازمند بررسی)")
    def retry_stock_reservation(self, request, queryset):
        self._apply(request, queryset, retry_reservation)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "kind", "value", "is_active", "ends_at", "total_limit", "per_user_limit"]
    list_filter = ["is_active", "kind"]
    search_fields = ["code"]


@admin.register(CouponUse)
class CouponUseAdmin(admin.ModelAdmin):
    list_display = ["coupon", "order", "state", "over_capacity", "created"]
    readonly_fields = ["coupon", "order", "state", "over_capacity", "created"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
