import threading
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock, skipUnless

from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from onlineshop.testing import FakeCart, FakeGateway, make_address, make_product, make_user

from .models import InvalidTransition, Order
from .services import (
    InsufficientStock,
    OrderActionError,
    advance_order,
    cancel_order,
    create_order_from_cart,
    expire_stale_orders,
    mark_order_paid,
    retry_reservation,
)


def stock(product):
    product.refresh_from_db()
    return product.inventory


class StateMachineTests(TestCase):
    def test_allowed_and_forbidden_transitions(self):
        order = Order(status=Order.STATUS_PENDING)
        self.assertTrue(order.can_transition_to(Order.STATUS_PAID))
        self.assertFalse(order.can_transition_to(Order.STATUS_SENT))
        order.transition_to(Order.STATUS_PAID)
        with self.assertRaises(InvalidTransition):
            order.transition_to(Order.STATUS_PENDING)

    def test_every_status_has_transition_rules(self):
        self.assertEqual({code for code, _ in Order.STATUS_CHOICES}, set(Order.TRANSITIONS))

    def test_delivered_is_terminal(self):
        self.assertEqual(Order.TRANSITIONS[Order.STATUS_DELIVERED], set())


class FinalPriceTests(TestCase):
    def test_discount_is_rounded_to_whole_toman(self):
        self.assertEqual(make_product(price=99_999, off=15).final_price, Decimal("84999"))
        self.assertEqual(make_product(price=100_000, off=100).final_price, Decimal("0"))


class CreateOrderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)

    def test_reserves_stock_and_snapshots_prices(self):
        p1, p2 = make_product(inventory=5, price=100_000, off=10), make_product(inventory=3, price=50_000)
        order = create_order_from_cart(FakeCart([(p1, 2), (p2, 3)]), self.address, self.user)

        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.assertTrue(order.stock_reserved)
        self.assertTrue(order.is_payable)
        self.assertEqual((stock(p1), stock(p2)), (3, 0))
        self.assertEqual(order.total_price, Decimal(2 * 90_000 + 3 * 50_000 + 100_000))
        self.assertEqual(order.first_name, "علی")
        self.assertIn("تهران", order.address)
        self.assertAlmostEqual(
            order.reserved_until, timezone.now() + timedelta(minutes=15), delta=timedelta(seconds=30)
        )

    def test_insufficient_stock_rolls_everything_back(self):
        p1, p2 = make_product(inventory=5), make_product(inventory=1)
        with self.assertRaises(InsufficientStock):
            create_order_from_cart(FakeCart([(p1, 2), (p2, 2)]), self.address, self.user)
        self.assertEqual((stock(p1), stock(p2)), (5, 1))
        self.assertFalse(Order.objects.exists())

    def test_inactive_product_cannot_be_reserved(self):
        product = make_product(inventory=5, is_active=False)
        with self.assertRaises(InsufficientStock):
            create_order_from_cart(FakeCart([(product, 1)]), self.address, self.user)

    def test_new_checkout_cancels_previous_unpaid_order(self):
        product = make_product(inventory=5)
        first = create_order_from_cart(FakeCart([(product, 2)]), self.address, self.user)
        second = create_order_from_cart(FakeCart([(product, 3)]), self.address, self.user)
        first.refresh_from_db()
        self.assertEqual(first.status, Order.STATUS_CANCELED)
        self.assertFalse(first.stock_reserved)
        self.assertEqual(second.status, Order.STATUS_PENDING)
        self.assertEqual(stock(product), 2)


class LifecycleTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(inventory=5)
        self.order = create_order_from_cart(FakeCart([(self.product, 2)]), make_address(self.user), self.user)

    def test_cancel_releases_stock_once(self):
        cancel_order(self.order)
        cancel_order(self.order)  # idempotent
        self.assertEqual(stock(self.product), 5)

    def test_expire_stale_orders(self):
        Order.objects.filter(pk=self.order.pk).update(reserved_until=timezone.now() - timedelta(seconds=1))
        out = StringIO()
        call_command("expire_orders", stdout=out)
        self.assertIn("1 order(s) expired", out.getvalue())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_EXPIRED)
        self.assertEqual(stock(self.product), 5)
        self.assertEqual(expire_stale_orders(), 0)  # nothing left, stock not released twice
        self.assertEqual(stock(self.product), 5)

    def test_not_expired_before_deadline(self):
        self.assertEqual(expire_stale_orders(), 0)
        self.assertEqual(stock(self.product), 3)

    def test_mark_paid_keeps_reservation(self):
        order = mark_order_paid(self.order, "REF")
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertTrue(order.is_paid)
        self.assertEqual(stock(self.product), 3)  # no second deduction
        self.assertEqual(mark_order_paid(order, "REF").status, Order.STATUS_PAID)  # idempotent
        self.assertEqual(stock(self.product), 3)

    def test_late_payment_rereserves_stock(self):
        cancel_order(self.order)
        order = mark_order_paid(self.order, "REF")
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertEqual(stock(self.product), 3)

    def test_late_payment_without_stock_needs_review_then_retry(self):
        cancel_order(self.order)
        self.product.inventory = 1
        self.product.save()
        order = mark_order_paid(self.order, "REF")
        self.assertEqual(order.status, Order.STATUS_NEEDS_REVIEW)
        self.assertTrue(order.is_paid)
        self.assertEqual(stock(self.product), 1)
        with self.assertRaises(OrderActionError):
            advance_order(order, Order.STATUS_PREPARING)  # can't ship what we don't have
        with self.assertRaises(OrderActionError):
            retry_reservation(order)
        self.product.inventory = 10
        self.product.save()
        order = retry_reservation(order)
        self.assertEqual(order.status, Order.STATUS_PREPARING)
        self.assertEqual(stock(self.product), 8)

    def test_admin_flow_and_invalid_jump(self):
        mark_order_paid(self.order, "REF")
        with self.assertRaises(OrderActionError):
            advance_order(self.order, Order.STATUS_DELIVERED)
        for status in (Order.STATUS_PREPARING, Order.STATUS_SENT, Order.STATUS_DELIVERED):
            advance_order(self.order, status)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_DELIVERED)
        with self.assertRaises(OrderActionError):
            cancel_order(self.order)


class CheckoutViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.product = make_product(inventory=5)
        self.client.force_login(self.user)
        self.client.post(reverse("cart:cart_add", args=[self.product.id]), {"quantity": 2})
        self.gateway = FakeGateway()
        patcher = mock.patch("payment.services.get_gateway", return_value=self.gateway)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_checkout_reserves_and_redirects_to_gateway(self):
        response = self.client.post(reverse("orders:order_create"), {"address_id": self.address.id})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("https://gw.test/StartPay/"))
        order = Order.objects.get()
        self.assertEqual(order.payments.get().authority, response["Location"].rsplit("/", 1)[1])
        self.assertEqual(stock(self.product), 3)

    def test_other_users_address_is_rejected(self):
        other = make_address(make_user())
        response = self.client.post(reverse("orders:order_create"), {"address_id": other.id})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Order.objects.exists())

    def test_missing_or_garbage_address(self):
        for data in ({}, {"address_id": "abc"}):
            response = self.client.post(reverse("orders:order_create"), data)
            self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_pages_render(self):
        self.client.post(reverse("orders:order_create"), {"address_id": self.address.id})
        order = Order.objects.get()
        for url in (
            reverse("orders:order_list"),
            reverse("orders:order_detail", args=[order.id]),
            reverse("account:profile"),
            reverse("orders:order_create"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_user_cancel(self):
        self.client.post(reverse("orders:order_create"), {"address_id": self.address.id})
        order = Order.objects.get()
        self.client.post(reverse("orders:order_cancel", args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELED)
        self.assertEqual(stock(self.product), 5)

    def test_cannot_see_or_cancel_other_users_order(self):
        other = make_user()
        order = create_order_from_cart(FakeCart([(self.product, 1)]), make_address(other), other)
        self.assertEqual(self.client.get(reverse("orders:order_detail", args=[order.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("orders:order_cancel", args=[order.id])).status_code, 404)

    def test_paid_order_cannot_be_canceled_by_customer(self):
        self.client.post(reverse("orders:order_create"), {"address_id": self.address.id})
        order = mark_order_paid(Order.objects.get(), "REF")
        self.client.post(reverse("orders:order_cancel", args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)

    def test_api_create_order(self):
        response = self.client.post(
            reverse("orders:api_order_create"),
            {"address_id": self.address.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIn("/payment/process/", response.json()["payment_url"])
        self.assertEqual(stock(self.product), 3)


class CartViewTests(TestCase):
    def test_invalid_quantity_is_rejected_not_500(self):
        product = make_product(inventory=5)
        for quantity in ("abc", "-1", "0", "1000000"):
            with self.subTest(quantity=quantity):
                response = self.client.post(
                    reverse("cart:cart_add", args=[product.id]), {"quantity": quantity}
                )
                self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("cart", {}), {})


@skipUnless(connection.vendor == "postgresql", "row locking needs PostgreSQL")
class ConcurrentCheckoutTests(TransactionTestCase):
    """Real threads + real DB transactions: the last item can only be sold once."""

    def test_last_item_is_sold_once(self):
        product = make_product(inventory=1)
        buyers = [(u, make_address(u)) for u in (make_user() for _ in range(6))]
        barrier = threading.Barrier(len(buyers))
        results = []

        def checkout(user, address):
            try:
                barrier.wait()
                create_order_from_cart(FakeCart([(product, 1)]), address, user)
                results.append("ok")
            except InsufficientStock:
                results.append("out")
            finally:
                close_old_connections()
                connection.close()

        threads = [threading.Thread(target=checkout, args=b) for b in buyers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sorted(results), ["ok"] + ["out"] * 5)
        self.assertEqual(stock(product), 0)
        self.assertEqual(Order.objects.count(), 1)
