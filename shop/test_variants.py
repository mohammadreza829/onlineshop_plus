import threading
from types import SimpleNamespace
from unittest import skipUnless

from django.contrib.sessions.backends.db import SessionStore
from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from cart.cart import Cart
from onlineshop.testing import FakeCart, make_address, make_product, make_user
from orders.services import InsufficientStock, cancel_order, create_order_from_cart, mark_order_paid
from shop.models import ProductVariant


def variant(product, **kwargs):
    return ProductVariant.objects.create(
        product=product,
        sku=f"V-{product.pk}-{kwargs.get('color', 'red')}",
        color=kwargs.pop("color", "red"),
        price=150000,
        inventory=3,
        **kwargs,
    )


def cart_for(product, choice):
    cart = Cart(SimpleNamespace(session=SessionStore()))
    cart.add(product, variant=choice)
    return cart


class VariantTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.product = make_product(inventory=100, off=10)
        self.red = variant(self.product)
        self.blue = variant(self.product, color="blue")

    def test_separate_lines_and_server_prices(self):
        cart = cart_for(self.product, self.red)
        self.assertTrue(cart.add(self.product, quantity=2, variant=self.blue).success)
        self.assertFalse(cart.add(self.product).success)
        order = create_order_from_cart(cart, self.address, self.user)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.total_price, 605000)
        self.product.refresh_from_db()
        self.red.refresh_from_db()
        self.blue.refresh_from_db()
        self.assertEqual((self.product.inventory, self.red.inventory, self.blue.inventory), (100, 2, 1))
        self.assertEqual(order.items.get(variant=self.red).variant_sku, self.red.sku)
        cancel_order(order)
        cancel_order(order)
        self.red.refresh_from_db()
        self.blue.refresh_from_db()
        self.assertEqual((self.red.inventory, self.blue.inventory), (3, 3))

    def test_variant_must_belong_to_product_and_be_active(self):
        other = make_product()
        self.assertFalse(cart_for(other, self.red).add(other, variant=self.red).success)
        self.red.is_active = False
        self.red.save()
        self.assertFalse(cart_for(self.product, self.red).add(self.product, variant=self.red).success)
        with self.assertRaises(InsufficientStock):
            create_order_from_cart(FakeCart([(self.product, 1)]), self.address, self.user)

    def test_catalog_stock_and_variant_details(self):
        client = APIClient()
        data = client.get(f"/api/v1/products/{self.product.slug}/").json()
        self.assertEqual(data["inventory"], 6)
        self.assertEqual(len(data["variants"]), 2)
        self.red.is_active = False
        self.red.save()
        self.blue.inventory = 0
        self.blue.save()
        rows = client.get("/api/v1/products/?stock=available").json()["results"]
        self.assertNotIn(self.product.pk, [row["id"] for row in rows])

    def test_api_add_delete_variant(self):
        client = APIClient()
        self.assertEqual(
            client.post(
                "/api/v1/cart/", {"product_id": self.product.pk, "variant_id": self.red.pk}
            ).status_code,
            200,
        )
        self.assertEqual(client.get("/api/v1/cart/").json()["items"][0]["variant_id"], self.red.pk)
        self.assertEqual(
            client.delete(f"/api/v1/cart/items/{self.product.pk}/?variant_id={self.red.pk}").status_code, 200
        )
        self.assertEqual(client.get("/api/v1/cart/").json()["items"], [])

    def test_late_payment_does_not_touch_base_stock(self):
        order = create_order_from_cart(cart_for(self.product, self.red), self.address, self.user)
        cancel_order(order)
        ProductVariant.objects.filter(pk=self.red.pk).update(inventory=0)
        with transaction.atomic():
            order = mark_order_paid(order, "late")
        self.assertTrue(order.is_paid)
        self.assertEqual(order.status, "needs_review")
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 100)

    def test_cart_discards_malformed_and_obsolete_entries(self):
        cart = cart_for(self.product, self.red)
        cart._cart.update({"broken": {"quantity": 1}, str(self.product.pk): {"quantity": 1}})
        cart.clean()
        self.assertEqual(len(cart), 1)
        ProductVariant.objects.filter(pk=self.red.pk).update(is_active=False)
        cart.clean()
        self.assertTrue(cart.is_empty)


@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL row locking")
class ConcurrentVariantTests(TransactionTestCase):
    def test_last_variant_sold_once(self):
        product = make_product(inventory=100)
        choice = variant(product)
        ProductVariant.objects.filter(pk=choice.pk).update(inventory=1)
        users = [make_user(), make_user()]
        addresses = [make_address(u) for u in users]
        barrier = threading.Barrier(2)
        results = []

        def checkout(n):
            close_old_connections()
            try:
                cart = cart_for(product, ProductVariant.objects.get(pk=choice.pk))
                barrier.wait(timeout=10)
                create_order_from_cart(cart, addresses[n], users[n])
                results.append("ok")
            except (InsufficientStock, Exception) as exc:
                # Fail the test for anything except a stock/cart availability rejection.
                from orders.services import OrderCreationError

                results.append("stock" if isinstance(exc, OrderCreationError) else type(exc).__name__)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=checkout, args=(n,)) for n in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(15)
        self.assertEqual(sorted(results), ["ok", "stock"])
        choice.refresh_from_db()
        self.assertEqual(choice.inventory, 0)
