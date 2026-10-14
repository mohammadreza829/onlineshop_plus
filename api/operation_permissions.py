from rest_framework.permissions import BasePermission


class CanManageOrders(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated or not user.is_active or not user.has_perm("orders.change_order"):
            return False
        # Paid cancellation is checked with the locked order by the service.
        return True


class CanViewSales(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.has_perm("orders.view_sales")
        )
