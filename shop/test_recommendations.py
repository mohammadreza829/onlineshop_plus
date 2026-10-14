from unittest.mock import patch

from django.core.cache import cache
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from onlineshop.testing import FakeCart, make_address, make_product, make_user
from orders.services import create_order_from_cart, mark_order_paid

from .models import Category, Product, ProductVariant
from .recommendations import recommended_products


class RecommendationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.anchor = make_product()
        self.same = make_product()
        self.other = make_product()
        self.other.category = Category.objects.create(name="other", slug="other")
        self.other.save()

    def test_same_category_first_exclude_anchor_inactive_and_empty(self):
        inactive = make_product(is_active=False)
        empty = make_product(inventory=0)
        ids = [p.pk for p in recommended_products(self.anchor)]
        self.assertEqual(ids, [self.same.pk, self.other.pk])
        self.assertNotIn(inactive.pk, ids)
        self.assertNotIn(empty.pk, ids)
        self.assertNotIn(self.anchor.pk, ids)

    def test_paid_popularity_breaks_category_tie(self):
        newer = make_product()
        user = make_user()
        order = create_order_from_cart(FakeCart([(self.same, 2)]), make_address(user), user)
        with transaction.atomic():
            mark_order_paid(order, "ref")
        products = recommended_products(self.anchor)
        self.assertEqual(products[0].pk, self.same.pk)
        self.assertIn(newer.pk, [p.pk for p in products])

    def test_api_is_public_bounded_and_anchor_must_be_active(self):
        client = APIClient()
        url = f"/api/v1/products/{self.anchor.slug}/recommendations/"
        self.assertEqual(len(client.get(url + "?limit=1").json()), 1)
        for limit in ["0", "21", "nope"]:
            self.assertEqual(client.get(url + "?limit=" + limit).status_code, 400)
        self.anchor.is_active = False
        self.anchor.save()
        self.assertEqual(client.get(url).status_code, 404)


class RecommendationCacheTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.anchor = make_product()
        self.choice = make_product()

    def test_warm_cache_one_live_query_and_never_caches_money_stock(self):
        first = recommended_products(self.anchor)
        self.assertEqual(first[0].price, 100000)
        # Raw UPDATE bypasses signals: warm candidate cache must still hydrate current state.
        Product.objects.filter(pk=self.choice.pk).update(price=123, inventory=2)
        with self.assertNumQueries(1):
            choices = recommended_products(self.anchor)
        self.assertEqual(choices[0].price, 123)
        self.assertEqual(choices[0].inventory, 2)
        Product.objects.filter(pk=self.choice.pk).update(is_active=False)
        self.assertEqual(recommended_products(self.anchor), [])

    def test_variants_use_live_availability_even_if_cache_warmed(self):
        ProductVariant.objects.create(product=self.choice, sku="cached-variant", price=50, inventory=1)
        self.assertEqual(len(recommended_products(self.anchor)), 1)
        ProductVariant.objects.filter(product=self.choice).update(inventory=0)
        self.assertEqual(recommended_products(self.anchor), [])

    def test_cache_outage_fails_open_for_public_recommendations(self):
        with patch("shop.recommendations.cache.get", side_effect=ConnectionError("QA redis down")):
            self.assertEqual(recommended_products(self.anchor)[0].pk, self.choice.pk)

    def test_rollback_never_invalidates_or_publishes_uncommitted_cache(self):
        from .recommendations import GENERATION_KEY

        recommended_products(self.anchor)
        version = cache.get(GENERATION_KEY)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.choice.is_active = False
                self.choice.save()
                recommended_products(self.anchor)
                raise RuntimeError("rollback")
        self.assertEqual(cache.get(GENERATION_KEY), version)
        self.assertEqual(recommended_products(self.anchor)[0].pk, self.choice.pk)

    def test_committed_save_invalidates_candidate_ranking(self):
        from .recommendations import GENERATION_KEY

        recommended_products(self.anchor)
        version = cache.get(GENERATION_KEY)
        make_product()
        self.assertNotEqual(cache.get(GENERATION_KEY), version)
