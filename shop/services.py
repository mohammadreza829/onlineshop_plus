"""Customer write policies, reused by APIs and future frontend."""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from account.models import ShopUser
from orders.models import Order

from .models import Review


@transaction.atomic
def save_review(*, user, product, rating, text):
    # One review per customer/product; serialize concurrent edits from this customer.
    ShopUser.objects.select_for_update().get(pk=user.pk)
    purchased = Order.objects.filter(
        user=user,
        is_paid=True,
        status__in=[Order.STATUS_PAID, Order.STATUS_PREPARING, Order.STATUS_SENT, Order.STATUS_DELIVERED],
        items__product=product,
    ).exists()
    if not purchased:
        raise PermissionDenied("ثبت نظر فقط برای خریداران پرداخت‌شده مجاز است.")
    review, _ = Review.objects.update_or_create(
        user=user, product=product, defaults={"rating": rating, "text": text, "status": Review.PENDING}
    )
    return review
