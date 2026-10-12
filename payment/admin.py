from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "user", "amount", "status", "needs_refund", "ref_id", "created_at")
    list_filter = ("status", "needs_refund", "gateway", "created_at")
    search_fields = ("authority", "ref_id", "order__order_number", "user__phone")
    list_select_related = ("order", "user")
    # Payments are an audit log: nothing here should be editable by hand.
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
