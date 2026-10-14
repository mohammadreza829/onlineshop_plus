from django.db import transaction
from django.test import TestCase
from rest_framework.test import APIClient

from onlineshop.testing import FakeCart, make_address, make_product, make_user
from orders.services import create_order_from_cart, mark_order_paid
from shop.models import Favorite, Review


class ShopFeatureTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user()
        self.product = make_product()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/v1/products/{self.product.slug}/reviews/mine/"

    def purchase(self):
        order = create_order_from_cart(FakeCart([(self.product, 1)]), make_address(self.user), self.user)
        with transaction.atomic():
            return mark_order_paid(order, "ref")

    def test_only_paid_buyer_may_review_and_status_cannot_be_spoofed(self):
        self.assertEqual(
            self.client.put(self.url, {"rating": 5, "text": "خوب", "status": "approved"}).status_code, 403
        )
        self.purchase()
        response = self.client.put(self.url, {"rating": 5, "text": "خوب", "status": "approved"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(self.client.put(self.url, {"rating": 6, "text": "bad"}).status_code, 400)

    def test_public_list_and_rating_include_only_approved_reviews(self):
        self.purchase()
        self.client.put(self.url, {"rating": 4, "text": "خوب"})
        public = APIClient()
        url = f"/api/v1/products/{self.product.slug}/reviews/"
        self.assertEqual(public.get(url).json()["count"], 0)
        Review.objects.update(status=Review.APPROVED)
        rows = public.get(url).json()["results"]
        self.assertEqual(len(rows), 1)
        self.assertNotIn("user", rows[0])
        self.assertNotIn(self.user.phone, str(rows))
        data = public.get(f"/api/v1/products/{self.product.slug}/").json()
        self.assertEqual(data["rating_average"], 4)
        self.assertEqual(data["rating_count"], 1)
        self.client.put(self.url, {"rating": 2, "text": "ویرایش"})
        self.assertEqual(public.get(url).json()["count"], 0)
        self.assertEqual(Review.objects.count(), 1)
        self.assertIsNone(public.get(f"/api/v1/products/{self.product.slug}/").json()["rating_average"])

    def test_review_owner_isolation_and_idempotent_delete(self):
        self.purchase()
        self.client.put(self.url, {"rating": 4, "text": "نظر"})
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertEqual(Review.objects.count(), 1)
        self.client.force_authenticate(self.user)
        self.client.delete(self.url)
        self.client.delete(self.url)
        self.assertEqual(Review.objects.count(), 0)

    def test_favorites_are_private_idempotent_and_hide_inactive_products(self):
        url = f"/api/v1/products/{self.product.pk}/favorite/"
        self.assertEqual(self.client.put(url).status_code, 200)
        self.client.put(url)
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertEqual(self.client.get("/api/v1/favorites/").json()["count"], 1)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/favorites/").json()["count"], 0)
        self.client.delete(url)
        self.assertEqual(Favorite.objects.count(), 1)
        self.client.force_authenticate(self.user)
        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.client.get("/api/v1/favorites/").json()["count"], 0)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_guest_cannot_write_favorites_or_reviews(self):
        client = APIClient()
        self.assertIn(client.put(self.url, {"rating": 5, "text": "نظر"}).status_code, [401, 403])
        self.assertIn(client.get("/api/v1/favorites/").status_code, [401, 403])
