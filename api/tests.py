import threading
from datetime import timedelta
from unittest import mock, skipUnless

from django.core.cache import cache
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from account.models import ShopUser
from addresses.models import Address
from onlineshop.testing import FakeCart, FakeGateway, make_address, make_product, make_user
from orders.models import Order
from orders.services import OrderCreationError, create_order_from_cart
from payment.models import Payment
from payment.services import PaymentError, start_payment
from shop.models import Category, ProductFeatures


def url(name, *args):
    return reverse("api_v1:" + name, args=args)


class APITestBase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = make_user()

    def authenticate(self, user=None):
        user = user or self.user
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")


class CatalogTests(APITestBase):
    def setUp(self):
        super().setUp()
        self.low = make_product(price=100, off=20)
        self.high = make_product(price=500, inventory=0)
        self.hidden = make_product(price=200, is_active=False)

    def test_public_list_has_discount_category_and_hides_inactive(self):
        response = self.client.get(url("product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        row = next(r for r in response.data["results"] if r["id"] == self.low.pk)
        self.assertEqual(row["final_price"], "80")
        self.assertEqual(row["category"]["slug"], "cat")

    def test_filters_and_ordering(self):
        for params, expected in [
            ({"stock": "available"}, [self.low.pk]),
            ({"stock": "out"}, [self.high.pk]),
            ({"min_price": 200}, [self.high.pk]),
            ({"max_price": 200}, [self.low.pk]),
            ({"search": self.low.sku}, [self.low.pk]),
            ({"category": "missing"}, []),
            ({"ordering": "price"}, [self.low.pk, self.high.pk]),
            ({"ordering": "-price"}, [self.high.pk, self.low.pk]),
        ]:
            with self.subTest(params=params):
                response = self.client.get(url("product_list"), params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([p["id"] for p in response.data["results"]], expected)

    def test_invalid_filters_return_400_not_500(self):
        for params in [
            {"min_price": "oops"},
            {"min_price": -1},
            {"min_price": 20, "max_price": 10},
            {"stock": "bad"},
            {"ordering": "user__password"},
        ]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get(url("product_list"), params).status_code, 400)

    def test_pagination_is_bounded_and_offset_is_deterministic(self):
        response = self.client.get(url("product_list"), {"limit": 1, "offset": 1, "ordering": "price"})
        self.assertEqual(response.data["results"][0]["id"], self.high.pk)
        from api.pagination import BoundedPagination

        self.assertEqual(BoundedPagination.max_limit, 100)

    def test_detail_features_and_inactive_404(self):
        ProductFeatures.objects.create(product=self.low, name="Color", value="Blue")
        response = self.client.get(url("product_detail", self.low.slug))
        self.assertEqual(response.data["features"][0]["value"], "Blue")
        self.assertEqual(self.client.get(url("product_detail", self.hidden.slug)).status_code, 404)

    def test_categories_are_public_read_only(self):
        response = self.client.get(url("category_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(url("category_detail", "cat")).status_code, 200)
        self.assertEqual(self.client.post(url("category_list"), {}).status_code, 405)
        self.assertEqual(self.client.post(url("product_list"), {}).status_code, 405)

    def test_list_does_not_add_queries_per_product(self):
        for _ in range(5):
            make_product()
        with self.assertNumQueries(2):  # count + products joined to category
            self.client.get(url("product_list"))

    def test_html_and_api_share_catalog_visibility(self):
        response = self.client.get(reverse("shop:home"))
        self.assertNotContains(response, self.hidden.name)


@override_settings(SMS_BACKEND="console")
class AuthenticationTests(APITestBase):
    phone = "09121234567"

    def send(self):
        with mock.patch("account.otp.send_otp") as sms:
            response = self.client.post(url("otp_request"), {"phone": self.phone}, format="json")
            self.assertEqual(response.status_code, 202, response.data)
            return sms.call_args.args[1]

    def verify(self, code):
        return self.client.post(url("otp_verify"), {"phone": self.phone, "code": code}, format="json")

    def test_otp_creates_unusable_password_and_issues_tokens_once(self):
        code = self.send()
        response = self.verify(code)
        self.assertEqual(response.status_code, 200, response.data)
        user = ShopUser.objects.get(phone=self.phone)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(int(AccessToken(response.data["access"])["user_id"]), user.pk)
        self.assertEqual(self.verify(code).status_code, 400)

    def test_invalid_phone_and_wrong_code(self):
        self.assertEqual(self.client.post(url("otp_request"), {"phone": "123"}).status_code, 400)
        code = self.send()
        self.assertEqual(self.verify("000000" if code != "000000" else "111111").status_code, 400)

    def test_send_cooldown_returns_429_and_retry_after(self):
        self.send()
        response = self.client.post(url("otp_request"), {"phone": self.phone})
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_inactive_user_cannot_get_tokens(self):
        ShopUser.objects.create_user(phone=self.phone, is_active=False)
        self.assertEqual(self.verify(self.send()).status_code, 400)

    def test_bearer_profile_cannot_change_phone_or_privileges(self):
        self.authenticate()
        response = self.client.patch(
            url("profile"), {"first_name": "Ali", "phone": "09999999999", "is_staff": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ali")
        self.assertFalse(self.user.is_staff)
        self.assertNotEqual(self.user.phone, "09999999999")

    def test_authentication_required_invalid_and_expired_tokens(self):
        self.assertEqual(self.client.get(url("profile")).status_code, 401)
        for token in ["invalid", self.expired_access()]:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            self.assertEqual(self.client.get(url("profile")).status_code, 401)

    def expired_access(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(from_time=timezone.now() - timedelta(hours=1), lifetime=timedelta(minutes=5))
        return str(token)

    def test_deactivated_user_is_rejected_with_existing_access(self):
        self.authenticate()
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get(url("profile")).status_code, 401)

    def test_refresh_rotation_blacklists_old_refresh(self):
        refresh = str(RefreshToken.for_user(self.user))
        response = self.client.post(url("token_refresh"), {"refresh": refresh})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["refresh"], refresh)
        self.assertEqual(self.client.post(url("token_refresh"), {"refresh": refresh}).status_code, 401)
        self.assertEqual(
            self.client.post(url("token_refresh"), {"refresh": response.data["refresh"]}).status_code, 200
        )

    def test_refresh_rejects_inactive_user(self):
        token = str(RefreshToken.for_user(self.user))
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.post(url("token_refresh"), {"refresh": token}).status_code, 401)

    def test_logout_blacklists_own_refresh_but_not_another_customers(self):
        self.authenticate()
        other_token = str(RefreshToken.for_user(make_user()))
        self.assertEqual(self.client.post(url("logout"), {"refresh": other_token}).status_code, 400)
        own = str(RefreshToken.for_user(self.user))
        self.assertEqual(self.client.post(url("logout"), {"refresh": own}).status_code, 204)
        self.assertEqual(self.client.post(url("token_refresh"), {"refresh": own}).status_code, 401)
        self.assertEqual(self.client.post(url("token_refresh"), {"refresh": other_token}).status_code, 200)

    def test_scoped_rate_limit_returns_429(self):
        rates = {**ScopedRateThrottle.THROTTLE_RATES, "auth": "1/min"}
        with mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates):
            self.client.post(url("otp_verify"), {"phone": self.phone, "code": "000000"})
            response = self.client.post(url("otp_verify"), {"phone": self.phone, "code": "000000"})
        self.assertEqual(response.status_code, 429)

    def test_session_auth_still_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.patch(url("profile"), {"first_name": "Ali"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_sms_outage_returns_503_without_issuing_tokens(self):
        from account.sms import SMSError

        with mock.patch("account.otp.send_otp", side_effect=SMSError("down")):
            response = self.client.post(url("otp_request"), {"phone": self.phone})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(ShopUser.objects.filter(phone=self.phone).exists())


class CheckoutAPITests(APITestBase):
    def setUp(self):
        super().setUp()
        self.address = make_address(self.user)
        self.product = make_product(inventory=5)
        self.authenticate()

    def add_cart(self):
        response = self.client.post(
            url("cart"), {"product_id": self.product.pk, "quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def create(self):
        self.add_cart()
        response = self.client.post(url("order_create"), {"address_id": self.address.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_jwt_cookie_cart_checkout_payment_and_cancel(self):
        response = self.create()
        order_id = response.data["order"]["id"]
        self.assertIn("/api/v1/orders/", response.data["payment_api_url"])
        self.assertEqual(self.client.get(url("order_detail", order_id)).status_code, 200)
        with mock.patch("payment.services.get_gateway", return_value=FakeGateway()):
            payment = self.client.post(url("order_payment", order_id))
        self.assertTrue(payment.data["payment_url"].startswith("https://gw.test/"))
        canceled = self.client.post(url("order_cancel", order_id))
        self.assertEqual(canceled.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 5)

    def test_other_users_data_is_never_read_or_modified(self):
        response = self.create()
        order_id = response.data["order"]["id"]
        self.authenticate(make_user())
        self.assertEqual(self.client.get(url("order_list")).data["count"], 0)
        for endpoint in ["order_detail", "order_cancel", "order_payment"]:
            method = self.client.get if endpoint == "order_detail" else self.client.post
            self.assertEqual(method(url(endpoint, order_id)).status_code, 404)
        self.assertEqual(self.client.get(url("address_detail", self.address.pk)).status_code, 404)
        self.assertEqual(
            self.client.patch(url("address_detail", self.address.pk), {"city": "X"}).status_code, 404
        )
        self.assertEqual(self.client.delete(url("address_detail", self.address.pk)).status_code, 404)

    def test_foreign_address_rejected_at_api_and_service_boundary(self):
        other = make_user()
        address = make_address(other)
        self.add_cart()
        self.assertEqual(self.client.post(url("order_create"), {"address_id": address.pk}).status_code, 400)
        with self.assertRaises(OrderCreationError):
            create_order_from_cart(FakeCart([(self.product, 1)]), address, self.user)

    def test_payment_service_rejects_foreign_user(self):
        self.create()
        with self.assertRaises(PaymentError):
            start_payment(Order.objects.get(), make_user(), "https://shop.test/callback")
        self.assertFalse(Payment.objects.exists())

    def test_paid_order_cannot_be_customer_canceled(self):
        self.create()
        order = Order.objects.get()
        Order.objects.filter(pk=order.pk).update(status=Order.STATUS_PAID, is_paid=True)
        self.assertEqual(self.client.post(url("order_cancel", order.pk)).status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)

    def test_empty_cart_and_invalid_quantities(self):
        self.assertEqual(
            self.client.post(url("order_create"), {"address_id": self.address.pk}).status_code, 400
        )
        for qty in [-1, 0, 101, "abc", 1.5]:
            with self.subTest(qty=qty):
                self.assertEqual(
                    self.client.post(
                        url("cart"), {"product_id": self.product.pk, "quantity": qty}, format="json"
                    ).status_code,
                    400,
                )

    def test_order_filter_validation_and_legacy_aliases(self):
        self.create()
        self.assertEqual(self.client.get(url("order_list"), {"status": "not-real"}).status_code, 400)
        self.assertEqual(self.client.get(reverse("orders:api_order_list")).data["count"], 1)
        self.assertEqual(self.client.get(reverse("orders:api_cart")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("orders:api_cart_delete_item", args=[self.product.pk])).status_code, 405
        )

    def test_address_creation_validates_and_does_not_accept_owner(self):
        other = make_user()
        data = {
            "title": "Work",
            "receiver_name": "Ali",
            "receiver_phone": "۰۹۱۲۱۲۳۴۵۶۷",
            "province": "tehran",
            "city": "Tehran",
            "full_address": "Test",
            "postal_code": "۱۲۳۴۵۶۷۸۹۰",
            "is_default": True,
            "user": other.pk,
        }
        response = self.client.post(url("address_list"), data, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        address = Address.objects.get(pk=response.data["id"])
        self.assertEqual(address.user_id, self.user.pk)
        self.assertEqual(address.receiver_phone, "09121234567")
        self.address.refresh_from_db()
        self.assertFalse(self.address.is_default)
        data["postal_code"] = "abc"
        self.assertEqual(self.client.post(url("address_list"), data, format="json").status_code, 400)

    def test_bearer_alone_does_not_identify_the_session_cart(self):
        self.add_cart()
        second = APIClient()
        second.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}")
        self.assertEqual(second.get(url("cart")).data["items"], [])


class SchemaTests(APITestBase):
    def test_schema_lists_canonical_endpoints_and_bearer_auth(self):
        response = self.client.get(reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json")
        self.assertEqual(response.status_code, 200)
        paths = response.data["paths"]
        for path in [
            "/api/v1/products/",
            "/api/v1/auth/otp/verify/",
            "/api/v1/orders/create/",
            "/api/v1/addresses/",
        ]:
            self.assertIn(path, paths)
        self.assertFalse(any(p.startswith("/orders/api/") for p in paths))
        self.assertIn("jwtAuth", response.data["components"]["securitySchemes"])


class AdditionalSecurityTests(APITestBase):
    def test_anon_throttle_returns_retry_after(self):
        from rest_framework.throttling import AnonRateThrottle

        rates = {**AnonRateThrottle.THROTTLE_RATES, "anon": "1/min"}
        with mock.patch.object(AnonRateThrottle, "THROTTLE_RATES", rates):
            self.assertEqual(self.client.get(url("product_list")).status_code, 200)
            response = self.client.get(url("product_list"))
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_page_limit_is_actually_capped(self):
        category = Category.objects.create(name="Limit", slug="limit")
        from shop.models import Product

        Product.objects.bulk_create(
            [
                Product(category=category, sku=f"bulk-{i}", name=f"Bulk {i}", slug=f"bulk-{i}")
                for i in range(105)
            ]
        )
        response = self.client.get(url("product_list"), {"limit": 10000})
        self.assertEqual(response.data["count"], 105)
        self.assertEqual(len(response.data["results"]), 100)

    def test_cancel_service_enforces_owner_even_without_a_view(self):
        from orders.services import OrderActionError, cancel_order_by_customer

        product = make_product(inventory=5)
        order = create_order_from_cart(FakeCart([(product, 1)]), make_address(self.user), self.user)
        with self.assertRaises(OrderActionError):
            cancel_order_by_customer(order, make_user())
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PENDING)

    def test_shared_address_validation_matches_forms_and_api(self):
        from addresses.forms import AddressForm

        data = {
            "title": "Home",
            "receiver_name": "Ali",
            "receiver_phone": "+989121234567",
            "province": "tehran",
            "city": "Tehran",
            "full_address": "Test",
            "postal_code": "۱۲۳۴۵۶۷۸۹۰",
        }
        form = AddressForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.authenticate()
        response = self.client.post(url("address_list"), data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["receiver_phone"], form.cleaned_data["receiver_phone"])
        self.assertEqual(response.data["postal_code"], form.cleaned_data["postal_code"])

    def test_default_address_web_action_requires_post(self):
        address = make_address(self.user)
        self.client.force_login(self.user)
        endpoint = reverse("addresses:set_default", args=[address.pk])
        self.assertEqual(self.client.get(endpoint).status_code, 405)
        self.assertEqual(self.client.post(endpoint).status_code, 302)
        address.refresh_from_db()
        self.assertTrue(address.is_default)

    def test_authenticated_user_throttle_is_applied(self):
        from rest_framework.throttling import UserRateThrottle

        self.authenticate()
        rates = {**UserRateThrottle.THROTTLE_RATES, "user": "1/min"}
        with mock.patch.object(UserRateThrottle, "THROTTLE_RATES", rates):
            self.assertEqual(self.client.get(url("profile")).status_code, 200)
            self.assertEqual(self.client.get(url("profile")).status_code, 429)

    def test_category_search_parent_and_root_filters(self):
        parent = Category.objects.create(name="Root", slug="root")
        child = Category.objects.create(name="Shoes", slug="shoes", parent=parent)
        for params, expected in [
            ({"search": "shoe"}, [child.pk]),
            ({"parent": parent.pk}, [child.pk]),
            ({"roots_only": "true"}, [parent.pk]),
        ]:
            response = self.client.get(url("category_list"), params)
            self.assertEqual([r["id"] for r in response.data["results"]], expected)

    def test_category_filters_reject_invalid_values(self):
        for params in [
            {"parent": "bad"},
            {"parent": -1},
            {"roots_only": "invalid"},
            {"roots_only": True, "parent": 1},
        ]:
            self.assertEqual(self.client.get(url("category_list"), params).status_code, 400)

    def test_checkout_rechecks_old_order_after_acquiring_its_lock(self):
        from orders import services

        product = make_product(inventory=5)
        address = make_address(self.user)
        old = create_order_from_cart(FakeCart([(product, 1)]), address, self.user)
        original_lock = services._lock

        def pay_before_lock(order):
            Order.objects.filter(pk=old.pk).update(status=Order.STATUS_PAID, is_paid=True)
            return original_lock(order)

        with mock.patch("orders.services._lock", side_effect=pay_before_lock):
            create_order_from_cart(FakeCart([(product, 1)]), address, self.user)
        old.refresh_from_db()
        self.assertEqual(old.status, Order.STATUS_PAID)
        self.assertTrue(old.stock_reserved)
        product.refresh_from_db()
        self.assertEqual(product.inventory, 3)


@skipUnless(connection.vendor == "postgresql", "row locking needs PostgreSQL")
class ConcurrentCustomerCheckoutTests(TransactionTestCase):
    def test_parallel_checkouts_leave_only_one_pending_order(self):
        user = make_user()
        address = make_address(user)
        product = make_product(inventory=5)
        barrier = threading.Barrier(2)
        errors = []

        def checkout():
            try:
                barrier.wait(timeout=5)
                create_order_from_cart(FakeCart([(product, 1)]), address, user)
            except Exception as exc:
                errors.append(repr(exc))
            finally:
                close_old_connections()
                connection.close()

        threads = [threading.Thread(target=checkout) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(Order.objects.filter(user=user, status=Order.STATUS_PENDING).count(), 1)
        product.refresh_from_db()
        self.assertEqual(product.inventory, 4)
