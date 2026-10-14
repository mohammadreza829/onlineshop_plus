from django.contrib import admin, messages
from django.db import IntegrityError

from .models import Payment, RefundRequest
from .refunds import confirm_bank_refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "user",
        "amount",
        "status",
        "needs_refund",
        "needs_reconciliation",
        "ref_id",
    )
    list_filter = ("status", "needs_refund", "needs_reconciliation")
    search_fields = ("authority", "ref_id", "order__order_number", "user__phone")
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ("payment", "amount", "reason", "status", "confirmed_at")
    list_filter = ("status",)

    def get_readonly_fields(self, request, obj=None):
        fields = [f.name for f in RefundRequest._meta.fields]
        if obj and obj.status == "requested" and request.user.has_perm("payment.confirm_refundrequest"):
            fields.remove("bank_reference")
        return fields

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.has_perm("payment.confirm_refundrequest")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        try:
            confirm_bank_refund(refund=obj, actor=request.user, bank_reference=obj.bank_reference)
        except (ValueError, IntegrityError) as exc:
            self.message_user(request, str(exc), messages.ERROR)
