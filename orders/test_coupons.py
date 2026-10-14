import threading
from datetime import timedelta
from unittest import skipUnless

from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from onlineshop.testing import FakeCart, make_address, make_product, make_user

from .models import Coupon, CouponUse
from .services import (
    OrderCreationError,
    cancel_order,
    create_order_from_cart,
    expire_order_if_needed,
    mark_order_paid,
)


class CouponTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.product = make_product(price=99999, off=10)
        self.coupon = Coupon.objects.create(code=" save ", kind="percent", value=15, total_limit=1)

    def checkout(self, code="save", user=None):
        user = user or self.user
        return create_order_from_cart(
            FakeCart([(self.product, 2)]), make_address(user), user, coupon_code=code
        )

    def pay(self, order):
        with transaction.atomic():
            return mark_order_paid(order, "ref")

    def test_discount_rounding_snapshot_and_shipping_excluded(self):
        order = self.checkout()
        self.assertEqual(order.coupon_code, "SAVE")
        self.assertEqual(order.coupon_discount, 27000)
        self.assertEqual(order.total_price, 252998)
        self.assertEqual(order.coupon_use.state, CouponUse.RESERVED)
        self.coupon.value = 90
        self.coupon.save()
        paid = self.pay(order)
        self.pay(paid)
        paid.coupon_use.refresh_from_db()
        self.assertEqual(paid.total_price, 252998)
        self.assertEqual(paid.coupon_use.state, CouponUse.USED)
        self.assertEqual(CouponUse.objects.count(), 1)

    def test_cancel_and_expire_release_quota_idempotently(self):
        order = self.checkout()
        cancel_order(order)
        cancel_order(order)
        order = self.checkout(user=make_user())
        order.reserved_until = timezone.now() - timedelta(seconds=1)
        order.save()
        self.assertTrue(expire_order_if_needed(order))
        self.assertFalse(expire_order_if_needed(order))
        self.assertEqual(CouponUse.objects.filter(state=CouponUse.RESERVED).count(), 0)

    def test_invalid_coupon_rolls_back_replacement_and_stock(self):
        old = self.checkout()
        self.product.refresh_from_db()
        stock = self.product.inventory
        with self.assertRaises(OrderCreationError):
            self.checkout(code="invalid")
        old.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(old.status, "pending")
        self.assertEqual(self.product.inventory, stock)
        self.assertEqual(old.coupon_use.state, CouponUse.RESERVED)

    def test_capacity_and_per_user_limits(self):
        self.pay(self.checkout())
        with self.assertRaises(OrderCreationError):
            self.checkout(user=make_user())
        self.coupon.total_limit = 10
        self.coupon.save()
        with self.assertRaises(OrderCreationError):
            self.checkout()

    def test_late_payment_records_money_even_if_quota_reused(self):
        first = self.checkout()
        cancel_order(first)
        second = self.checkout(user=make_user())
        self.pay(second)
        first = self.pay(first)
        self.assertTrue(first.is_paid)
        self.assertEqual(first.status, "needs_review")
        self.assertTrue(first.coupon_use.over_capacity)
        self.assertEqual(first.coupon_use.state, CouponUse.USED)
        self.assertEqual(first.coupon_discount, 27000)
        cancel_order(first)
        self.assertEqual(CouponUse.objects.get(order=first).state, CouponUse.USED)

    def test_fixed_clamp_maximum_minimum_and_dates(self):
        self.coupon.kind = "fixed"
        self.coupon.value = 999999
        self.coupon.save()
        order = self.checkout()
        self.assertEqual(order.total_price, 100000)
        cancel_order(order)
        self.coupon.maximum_discount = 1000
        self.coupon.save()
        order = self.checkout()
        self.assertEqual(order.coupon_discount, 1000)
        cancel_order(order)
        for changes in [
            dict(minimum_subtotal=999999),
            dict(ends_at=timezone.now() - timedelta(seconds=1)),
            dict(is_active=False),
        ]:
            for key, value in changes.items():
                setattr(self.coupon, key, value)
            self.coupon.save()
            with self.assertRaises(OrderCreationError):
                self.checkout()
            self.coupon.minimum_subtotal = 0
            self.coupon.ends_at = None
            self.coupon.is_active = True


@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL row locking")
class ConcurrentCouponTests(TransactionTestCase):
    def test_last_coupon_slot_reserved_once(self):
        Coupon.objects.create(code="LAST", kind="fixed", value=100, total_limit=1)
        users = [make_user(), make_user()]
        addresses = [make_address(u) for u in users]
        products = [make_product(), make_product()]
        barrier = threading.Barrier(2)
        results = []

        def checkout(n):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                create_order_from_cart(
                    FakeCart([(products[n], 1)]), addresses[n], users[n], coupon_code="LAST"
                )
                results.append("ok")
            except Exception as exc:
                results.append("quota" if isinstance(exc, OrderCreationError) else type(exc).__name__)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=checkout, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(15)
        self.assertEqual(sorted(results), ["ok", "quota"])
        self.assertEqual(CouponUse.objects.filter(state=CouponUse.RESERVED).count(), 1)
