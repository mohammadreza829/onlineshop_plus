"""
Order business logic. Views/API call these functions; they never touch stock directly.

Stock model
-----------
`Product.inventory` is the *available* stock. It is decremented when an order is
created (reservation) and given back if the order is canceled or expires.
Every change is a single conditional UPDATE:

    UPDATE product SET inventory = inventory - q WHERE id = X AND inventory >= q

so two concurrent checkouts can never oversell the last item: the second UPDATE
matches 0 rows. Rows are always touched in primary-key order to avoid deadlocks.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from shop.models import Product

from .models import Order, OrderItem

logger = logging.getLogger(__name__)


class OrderCreationError(Exception):
    pass


class InsufficientStock(OrderCreationError):
    def __init__(self, product_name):
        self.product_name = product_name
        super().__init__(f"موجودی «{product_name}» کافی نیست.")


class OrderActionError(Exception):
    pass


POST_PAYMENT_STATUSES = {
    Order.STATUS_PAID,
    Order.STATUS_PREPARING,
    Order.STATUS_SENT,
    Order.STATUS_DELIVERED,
    Order.STATUS_NEEDS_REVIEW,
}


def reservation_deadline():
    return timezone.now() + timedelta(minutes=settings.ORDER_RESERVATION_MINUTES)


# ----------------------------------------------------------------------
# Stock primitives (must run inside transaction.atomic)
# ----------------------------------------------------------------------

def _reserve(lines):
    """lines: iterable of (product_id, quantity, product_name). Raises InsufficientStock."""
    for product_id, quantity, name in sorted(lines, key=lambda line: line[0]):
        updated = Product.objects.filter(
            pk=product_id, is_active=True, inventory__gte=quantity
        ).update(inventory=F("inventory") - quantity)
        if updated != 1:
            raise InsufficientStock(name)


def _release(lines):
    for product_id, quantity, _name in sorted(lines, key=lambda line: line[0]):
        Product.objects.filter(pk=product_id).update(inventory=F("inventory") + quantity)


def _order_lines(order):
    return [
        (item.product_id, item.quantity, item.product_name)
        for item in order.items.all()
        if item.product_id is not None
    ]


def _lock(order_or_id):
    order_id = getattr(order_or_id, "pk", order_or_id)
    return Order.objects.select_for_update().get(pk=order_id)


# ----------------------------------------------------------------------
# Checkout
# ----------------------------------------------------------------------

def build_shipping_snapshot(address, user):
    """Copy address data into the order so later address edits don't change history."""
    name_parts = (address.receiver_name or "").split()
    return {
        "first_name": name_parts[0] if name_parts else user.first_name,
        "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else user.last_name,
        "phone": address.receiver_phone,
        "address": f"{address.get_province_display()} - {address.city} - {address.full_address}",
        "postal_code": address.postal_code,
    }


def create_order_from_cart(cart, address, user):
    """
    Create a PENDING order from the session cart and reserve its stock.

    Prices are read from the locked product rows (not from the session), so a price
    change between "add to cart" and "checkout" can't be abused.
    Any previous unpaid order of the same user is canceled first, so double
    submits / abandoned checkouts don't hold stock twice.
    """
    cart.clean()
    if cart.is_empty:
        raise OrderCreationError("سبد خرید خالی است.")

    validation = cart.validate()
    if not validation["valid"]:
        raise OrderCreationError("\n".join(validation["errors"]))

    quantities = {item["product"].id: item["quantity"] for item in cart}
    if not quantities:
        raise OrderCreationError("سبد خرید خالی است.")
    post_price = cart.get_post_price()
    snapshot = build_shipping_snapshot(address, user)

    with transaction.atomic():
        for old_order in Order.objects.filter(user=user, status=Order.STATUS_PENDING, is_paid=False):
            cancel_order(old_order, reason="replaced by a new checkout")

        products = list(
            Product.objects.select_for_update().filter(id__in=quantities.keys()).order_by("pk")
        )
        if len(products) != len(quantities):
            raise OrderCreationError("یکی از محصولات حذف شده است.")

        _reserve([(p.pk, quantities[p.pk], p.name) for p in products])

        order = Order.objects.create(
            user=user,
            address_obj=address,
            post_price=post_price,
            total_price=0,
            stock_reserved=True,
            reserved_until=reservation_deadline(),
            **snapshot,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku,
                    price=product.final_price,
                    quantity=quantities[product.pk],
                    total_price=product.final_price * quantities[product.pk],
                )
                for product in products
            ]
        )
        order.total_price = order.calculate_total()
        order.save(update_fields=["total_price"])

    logger.info("Order %s created, stock reserved until %s", order.order_number, order.reserved_until)
    return order


# ----------------------------------------------------------------------
# Lifecycle
# ----------------------------------------------------------------------

def cancel_order(order, reason=""):
    """Cancel an order and give its stock back. Idempotent for already-canceled orders."""
    with transaction.atomic():
        order = _lock(order)
        if order.status == Order.STATUS_CANCELED:
            return order
        if not order.can_transition_to(Order.STATUS_CANCELED):
            raise OrderActionError("این سفارش قابل لغو نیست.")
        if order.stock_reserved:
            _release(_order_lines(order))
            order.stock_reserved = False
        order.transition_to(Order.STATUS_CANCELED)
        order.save(update_fields=["status", "stock_reserved", "updated"])
    logger.info("Order %s canceled (%s)", order.order_number, reason or "-")
    return order


def expire_order_if_needed(order):
    """Expire one pending order whose reservation deadline has passed. Returns True if expired."""
    with transaction.atomic():
        order = _lock(order)
        if order.status != Order.STATUS_PENDING or order.is_paid or not order.is_reservation_expired:
            return False
        if order.stock_reserved:
            _release(_order_lines(order))
            order.stock_reserved = False
        order.transition_to(Order.STATUS_EXPIRED)
        order.save(update_fields=["status", "stock_reserved", "updated"])
    logger.info("Order %s expired, stock released", order.order_number)
    return True


def expire_stale_orders(now=None):
    """Release stock of every unpaid order past its deadline (run from cron / Celery beat)."""
    now = now or timezone.now()
    ids = Order.objects.filter(
        status=Order.STATUS_PENDING, is_paid=False, reserved_until__lte=now
    ).values_list("pk", flat=True)
    return sum(1 for order_id in list(ids) if expire_order_if_needed(order_id))


def mark_order_paid(order, ref_id):
    """
    Record a verified payment on the order. Must be called inside the payment's
    transaction. Never raises because of stock: the customer has already paid.

    Returns the updated order. If the reservation was lost (expired/canceled) and
    stock is no longer available the order goes to NEEDS_REVIEW for the admin.
    """
    order = _lock(order)
    if order.is_paid:
        return order

    if order.status in POST_PAYMENT_STATUSES:
        # Legacy rows: status was moved forward manually without is_paid. Just record it.
        order.is_paid = True
        order.paid_at = timezone.now()
        order.ref_id = ref_id
        order.save(update_fields=["is_paid", "paid_at", "ref_id", "updated"])
        return order

    if not order.stock_reserved:
        try:
            with transaction.atomic():  # savepoint: a failed re-reserve must not roll back the payment
                _reserve(_order_lines(order))
            order.stock_reserved = True
        except InsufficientStock as exc:
            logger.critical(
                "Order %s paid (ref %s) but stock for %s is gone -> needs review/refund",
                order.order_number, ref_id, exc.product_name,
            )

    target = Order.STATUS_PAID if order.stock_reserved else Order.STATUS_NEEDS_REVIEW
    order.transition_to(target)
    order.is_paid = True
    order.paid_at = timezone.now()
    order.ref_id = ref_id
    order.save(update_fields=["status", "is_paid", "paid_at", "ref_id", "stock_reserved", "updated"])
    return order


def retry_reservation(order):
    """For NEEDS_REVIEW orders after restocking: try to take the stock again."""
    with transaction.atomic():
        order = _lock(order)
        if order.stock_reserved:
            return order
        if order.status not in (Order.STATUS_NEEDS_REVIEW, Order.STATUS_PAID):
            raise OrderActionError("فقط برای سفارش‌های پرداخت‌شده قابل انجام است.")
        try:
            with transaction.atomic():
                _reserve(_order_lines(order))
        except InsufficientStock as exc:
            raise OrderActionError(str(exc)) from exc
        order.stock_reserved = True
        if order.status == Order.STATUS_NEEDS_REVIEW:
            order.transition_to(Order.STATUS_PREPARING)
        order.save(update_fields=["status", "stock_reserved", "updated"])
    return order


def advance_order(order, new_status):
    """Admin/back-office transitions (preparing, sent, delivered, canceled)."""
    if new_status == Order.STATUS_CANCELED:
        return cancel_order(order, reason="admin")
    with transaction.atomic():
        order = _lock(order)
        if order.status == new_status:
            return order
        if not order.can_transition_to(new_status):
            raise OrderActionError(
                f"تغییر وضعیت از «{order.get_status_display()}» به این وضعیت مجاز نیست."
            )
        if new_status == Order.STATUS_PREPARING and not order.stock_reserved:
            raise OrderActionError("ابتدا موجودی این سفارش را تامین کنید (سفارش موجودی رزرو‌شده ندارد).")
        order.transition_to(new_status)
        order.save(update_fields=["status", "updated"])
    return order
