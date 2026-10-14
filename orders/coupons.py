"""Coupon capacity is serialized by its DB row, including release and late payment."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Coupon, CouponUse


class CouponError(Exception):
    pass


def _capacity(coupon, order):
    uses = CouponUse.objects.filter(coupon=coupon, state__in=[CouponUse.RESERVED, CouponUse.USED]).exclude(
        order=order
    )
    return (coupon.total_limit is None or uses.count() < coupon.total_limit) and uses.filter(
        order__user_id=order.user_id
    ).count() < coupon.per_user_limit


@transaction.atomic
def reserve_coupon(order, code):
    try:
        coupon = Coupon.objects.select_for_update().get(code=code.strip().upper())
    except Coupon.DoesNotExist as exc:
        raise CouponError("کد تخفیف قابل استفاده نیست.") from exc
    now = timezone.now()
    subtotal = order.items.aggregate(total=Sum("total_price"))["total"] or Decimal(0)
    if (
        not coupon.is_active
        or (coupon.starts_at and now < coupon.starts_at)
        or (coupon.ends_at and now >= coupon.ends_at)
        or subtotal < coupon.minimum_subtotal
        or not _capacity(coupon, order)
    ):
        raise CouponError("کد تخفیف قابل استفاده نیست.")
    discount = (
        coupon.value
        if coupon.kind == Coupon.FIXED
        else (subtotal * coupon.value / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    if coupon.maximum_discount is not None:
        discount = min(discount, coupon.maximum_discount)
    order.coupon_code = coupon.code
    order.coupon_discount = min(subtotal, max(Decimal(0), discount))
    CouponUse.objects.create(coupon=coupon, order=order, state=CouponUse.RESERVED)
    order.save(update_fields=["coupon_code", "coupon_discount"])


@transaction.atomic
def release_coupon(order):
    if order.is_paid:
        return
    use = CouponUse.objects.filter(order=order).first()
    if use is None:
        return
    Coupon.objects.select_for_update().get(pk=use.coupon_id)
    CouponUse.objects.filter(pk=use.pk, state=CouponUse.RESERVED).update(state=CouponUse.RELEASED)


@transaction.atomic
def consume_coupon(order):
    """Never reject verified money. Late callbacks over capacity require staff review."""
    use = CouponUse.objects.filter(order=order).first()
    if use is None or use.state == CouponUse.USED:
        return True
    coupon = Coupon.objects.select_for_update().get(pk=use.coupon_id)
    # Order lock held by caller; refresh after acquiring shared coupon lock.
    use.refresh_from_db()
    available = use.state == CouponUse.RESERVED or _capacity(coupon, order)
    use.state = CouponUse.USED
    use.over_capacity = not available
    use.save(update_fields=["state", "over_capacity"])
    return available
