from types import SimpleNamespace

from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase, override_settings

from onlineshop.testing import make_product

from .cart import Cart


class CartQueryBudgetTests(TestCase):
    def test_read_once_request_local_and_constant_query_budget(self):
        products = [make_product() for _ in range(12)]
        session = SessionStore()
        session["cart"] = {str(p.pk): {"quantity": 1} for p in products}
        cart = Cart(SimpleNamespace(session=session))
        with self.assertNumQueries(2):
            cart.clean()
            list(cart)
            cart.summary()
            cart.validate()
        self.assertEqual(cart.summary()["item_count"], 12)
        # A new request must read current prices instead of sharing the local memo.
        type(products[0]).objects.filter(pk=products[0].pk).update(price=5)
        next_request = Cart(SimpleNamespace(session=session))
        self.assertEqual(
            next(item for item in next_request if item["product"].pk == products[0].pk)["price"], 5
        )

    def test_mutations_clear_request_local_cache(self):
        product = make_product()
        cart = Cart(SimpleNamespace(session=SessionStore()))
        cart.add(product)
        self.assertEqual(cart.summary()["item_count"], 1)
        cart.add(product)
        self.assertEqual(cart.summary()["item_count"], 2)
        cart.decrease(product)
        self.assertEqual(cart.summary()["item_count"], 1)
        cart.remove(product)
        self.assertEqual(cart.summary()["item_count"], 0)
        cart.add(product)
        cart.clear()
        self.assertEqual(list(cart), [])

    @override_settings(CART_MAX_LINES=1)
    def test_cart_line_limit_does_not_prevent_editing_existing_line(self):
        first, second = make_product(), make_product()
        cart = Cart(SimpleNamespace(session=SessionStore()))
        self.assertTrue(cart.add(first).success)
        self.assertFalse(cart.add(second).success)
        self.assertTrue(cart.add(first).success)
