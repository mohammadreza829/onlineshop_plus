"""Owner-scoped reads: never expose another customer's order."""

from .models import Order


def orders_for_user(user, *, status=None):
    if not user.is_authenticated:
        return Order.objects.none()
    qs = (
        Order.objects.filter(user=user)
        .prefetch_related("items", "payments__refund")
        .order_by("-created", "-pk")
    )
    return qs.filter(status=status) if status else qs
