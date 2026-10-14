from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from addresses.models import Address
from onlineshop.testing import FakeGateway, make_product, make_user
from orders.models import Coupon, CouponUse, Order
from payment.gateway import VerifyStatus
from payment.models import Payment
from shop.models import ProductVariant


class ClientBootstrapTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client = APIClient(enforce_csrf_checks=True)

    def test_options_only_expose_documented_public_constraints(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer deliberately-invalid")
        response = self.client.get("/api/v1/client-options/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data),
            {
                "currency",
                "time_zone",
                "cart_quantity_max",
                "cart_lines_max",
                "pagination_default",
                "pagination_max",
                "provinces",
            },
        )
        self.assertEqual(
            response.data["provinces"],
            [{"value": value, "label": label} for value, label in Address.PROVINCE_CHOICES],
        )
        self.assertEqual(response.data["currency"], "TOMAN")
        self.assertEqual(response.data["cart_lines_max"], settings.CART_MAX_LINES)
        self.assertNotIn("Access-Control-Allow-Origin", response)

    @override_settings(CSRF_COOKIE_HTTPONLY=True)
    def test_csrf_bootstrap_sets_cookie_and_allows_protected_session_write(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.patch("/api/v1/me/", {"first_name": "QA"}, format="json").status_code, 403
        )
        response = self.client.get("/api/v1/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies[settings.CSRF_COOKIE_NAME]["httponly"])
        token = response.data["csrf_token"]
        result = self.client.patch("/api/v1/me/", {"first_name": "QA"}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["first_name"], "QA")
        evil = self.client.patch(
            "/api/v1/me/",
            {"first_name": "evil"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="https://untrusted.example",
        )
        self.assertEqual(evil.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "QA")

    def test_dynamic_canonical_legacy_and_error_responses_are_no_store(self):
        for path in [
            "/api/v1/products/",
            "/api/v1/csrf/",
            "/api/v1/cart/",
            "/orders/api/v1/cart/",
            "/api/v1/orders/",
        ]:
            response = self.client.get(path)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertIn("private", response["Cache-Control"])
        self.assertIn("Cookie", self.client.get("/api/v1/csrf/")["Vary"])


class CartQuantityContractTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.product = make_product(inventory=5)
        self.path = f"/api/v1/cart/items/{self.product.pk}/"
        self.client.post("/api/v1/cart/", {"product_id": self.product.pk, "quantity": 2})

    def test_absolute_set_decrease_and_repeat_do_not_increment(self):
        for quantity in [4, 4, 1]:
            response = self.client.patch(self.path, {"quantity": quantity}, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["items"][0]["quantity"], quantity)
            self.assertFalse(response.data["quantity_clamped"])

    def test_stock_clamp_and_client_price_is_ignored(self):
        response = self.client.patch(
            self.path, {"quantity": 100, "price": 1, "total_price": 1}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["items"][0]["quantity"], 5)
        self.assertEqual(response.data["items"][0]["price"], "100000")
        self.assertTrue(response.data["quantity_clamped"])

    def test_zero_removal_is_repeatable_and_nonzero_does_not_create_line(self):
        self.assertEqual(self.client.patch(self.path, {"quantity": 0}).data["items"], [])
        self.assertEqual(self.client.patch(self.path, {"quantity": 0}).status_code, 200)
        self.assertEqual(self.client.patch(self.path, {"quantity": 2}).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/cart/").data["items"], [])

    def test_invalid_quantities_and_legacy_method_contract(self):
        for quantity in [-1, 101, True, 1.5, "bad"]:
            self.assertEqual(
                self.client.patch(self.path, {"quantity": quantity}, format="json").status_code, 400
            )
        self.assertEqual(self.client.patch(self.path, {}, format="json").status_code, 400)
        self.assertEqual(self.client.get(self.path).status_code, 405)
        self.assertEqual(self.client.post(self.path, {"quantity": 1}).status_code, 405)
        self.assertEqual(
            self.client.patch(
                reverse("orders:api_cart_delete_item", args=[self.product.pk]), {"quantity": 1}
            ).status_code,
            405,
        )

    def test_variant_updates_one_line_and_rejects_other_products_variant(self):
        self.client.delete("/api/v1/cart/")
        red = ProductVariant.objects.create(
            product=self.product, sku="front-red", color="red", price=50, inventory=4
        )
        blue = ProductVariant.objects.create(
            product=self.product, sku="front-blue", color="blue", price=60, inventory=3
        )
        for v in [red, blue]:
            self.client.post(
                "/api/v1/cart/", {"product_id": self.product.pk, "variant_id": v.pk, "quantity": 1}
            )
        response = self.client.patch(self.path, {"variant_id": red.pk, "quantity": 3})
        self.assertEqual(
            {i["variant_id"]: i["quantity"] for i in response.data["items"]}, {red.pk: 3, blue.pk: 1}
        )
        other = ProductVariant.objects.create(product=make_product(), sku="front-other", price=1, inventory=5)
        self.assertEqual(
            self.client.patch(self.path, {"variant_id": other.pk, "quantity": 1}).status_code, 404
        )

    def test_inactive_line_can_be_removed_without_active_add_validation(self):
        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.client.delete(self.path).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/cart/").data["items"], [])


class BrowserClientJourneyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.product = make_product(inventory=100, off=10)
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="journey-variant", color="blue", size="M", price=150000, inventory=4
        )
        self.client = APIClient()
        self.coupon = Coupon.objects.create(code="JOURNEY", kind="percent", value=10, total_limit=1)

    def login(self):
        # Only SMS transport is mocked; generation/HMAC/burn and JWT issuance are real.
        with patch("account.otp.send_otp") as delivery:
            self.assertEqual(
                self.client.post("/api/v1/auth/otp/request/", {"phone": self.user.phone}).status_code, 202
            )
        code = delivery.call_args.args[1]
        result = self.client.post("/api/v1/auth/otp/verify/", {"phone": self.user.phone, "code": code})
        self.assertEqual(result.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + result.data["access"])
        self.assertEqual(self.client.get("/api/v1/me/").data["id"], self.user.pk)
        return result.data

    def checkout(self):
        self.client.post("/api/v1/cart/", {"product_id": self.product.pk, "variant_id": self.variant.pk})
        self.client.patch(
            f"/api/v1/cart/items/{self.product.pk}/", {"variant_id": self.variant.pk, "quantity": 2}
        )
        tokens = self.login()
        address = self.client.post(
            "/api/v1/addresses/",
            {
                "title": "QA",
                "receiver_name": "QA Buyer",
                "receiver_phone": self.user.phone,
                "province": "tehran",
                "city": "QA",
                "full_address": "Synthetic QA only",
                "postal_code": "1234567890",
            },
            format="json",
        )
        self.assertEqual(address.status_code, 201)
        result = self.client.post(
            "/api/v1/orders/create/", {"address_id": address.data["id"], "coupon_code": "JOURNEY"}
        )
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["order"]["total_price"], "343000")
        self.assertEqual(result.data["order"]["items"][0]["variant_sku"], "journey-variant")
        return result.data["order"]["id"], tokens

    def test_guest_cookie_otp_jwt_coupon_payment_tracking_and_isolation(self):
        order_id, tokens = self.checkout()
        gateway = FakeGateway()
        with patch("payment.services.get_gateway", return_value=gateway):
            self.assertEqual(self.client.get(f"/api/v1/orders/{order_id}/payment/").status_code, 405)
            payment = self.client.post(f"/api/v1/orders/{order_id}/payment/")
            self.assertEqual(payment.status_code, 200)
            authority = Payment.objects.get(order_id=order_id).authority
            # Gateway return deliberately has no shop session; even NOK is not financial truth.
            callback_client = APIClient()
            callback_client.get("/payment/verify/", {"Authority": authority, "Status": "NOK"})
            callback_client.get("/payment/verify/", {"Authority": authority, "Status": "OK"})
        self.assertEqual(gateway.verify_calls, 1)
        order = self.client.get(f"/api/v1/orders/{order_id}/")
        self.assertTrue(order.data["is_paid"])
        self.assertEqual(order.data["status"], "paid")
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.inventory, 2)
        self.assertEqual(CouponUse.objects.get(order_id=order_id).state, CouponUse.USED)
        self.assertEqual(self.client.get(f"/api/v1/orders/{order_id}/tracking/").data["count"], 2)
        self.assertEqual(self.client.get("/api/v1/notifications/").data["count"], 2)
        self.assertEqual(self.client.get("/api/v1/cart/").data["item_count"], 2)
        self.client.delete("/api/v1/cart/")
        self.assertTrue(self.client.get("/api/v1/cart/").data["is_empty"])
        other = APIClient()
        other.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(make_user())}")
        self.assertEqual(other.get(f"/api/v1/orders/{order_id}/").status_code, 404)
        self.assertEqual(other.get("/api/v1/notifications/").data["count"], 0)
        self.assertEqual(other.get("/api/v1/staff/sales/").status_code, 403)
        refresh = self.client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]})
        self.assertEqual(refresh.status_code, 200)
        self.assertNotEqual(refresh.data["refresh"], tokens["refresh"])
        self.assertEqual(
            self.client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}).status_code, 401
        )
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + refresh.data["access"])
        self.assertEqual(
            self.client.post("/api/v1/auth/logout/", {"refresh": refresh.data["refresh"]}).status_code, 204
        )
        self.assertEqual(
            self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh.data["refresh"]}).status_code,
            401,
        )

    def test_unknown_payment_keeps_record_and_recovers_without_recheckout(self):
        order_id, _tokens = self.checkout()
        gateway = FakeGateway(verify_status=VerifyStatus.UNKNOWN)
        with patch("payment.services.get_gateway", return_value=gateway):
            self.client.post(f"/api/v1/orders/{order_id}/payment/")
            payment = Payment.objects.get(order_id=order_id)
            self.client.get("/payment/verify/", {"Authority": payment.authority, "Status": "OK"})
            payment.refresh_from_db()
            self.assertEqual(payment.status, Payment.STATUS_UNKNOWN)
            self.assertFalse(Order.objects.get(pk=order_id).is_paid)
            gateway.verify_status = VerifyStatus.SUCCESS
            self.client.get("/payment/verify/", {"Authority": payment.authority})
        self.assertTrue(Order.objects.get(pk=order_id).is_paid)
        self.assertEqual(Order.objects.count(), 1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.inventory, 2)
