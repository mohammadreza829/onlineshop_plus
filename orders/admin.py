from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Order, OrderItem


# ==========================================
# Order Item Inline
# ==========================================

class OrderItemInline(admin.TabularInline):

    model = OrderItem

    extra = 0

    can_delete = False

    readonly_fields = (
        "product",
        "product_name",
        "price",
        "quantity",
        "total_price",
    )



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
        "created",
        "user",
    )

    search_fields = (
        "id",
        "first_name",
        "last_name",
        "phone",
        "postal_code",
    )

    ordering = (
        "-created",
    )

    date_hierarchy = "created"

    readonly_fields = (
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
            }
        ),

        (
            "وضعیت سفارش",
            {
                "fields": (
                    "status",
                )
            }
        ),

        (
            "مبالغ",
            {
                "fields": (
                    "post_price",
                    "total_price",
                    "items_count",
                )
            }
        ),

        (
            "تاریخ‌ها",
            {
                "fields": (
                    "created",
                    "updated",
                )
            }
        ),

    )

    inlines = [
        OrderItemInline,
    ]

    actions = (
        "mark_paid",
        "mark_sent",
        "mark_canceled",
    )

    def get_queryset(self, request):

        queryset = super().get_queryset(request)

        return (
            queryset
            .select_related("user")
            .prefetch_related("items")
            .annotate(
                items_total=Count("items")
            )
        )

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

    @admin.action(description="تغییر وضعیت به پرداخت شده")
    def mark_paid(self, request, queryset):

        queryset.update(status="paid")

    @admin.action(description="تغییر وضعیت به ارسال شده")
    def mark_sent(self, request, queryset):

        queryset.update(status="sent")

    @admin.action(description="لغو سفارش")
    def mark_canceled(self, request, queryset):

        queryset.update(status="canceled")