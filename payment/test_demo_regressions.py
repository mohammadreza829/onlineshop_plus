"""Regression tests use an isolated DB and fake gateway; no SMS/bank I/O."""

from unittest.mock import patch
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from cart.cart import Cart
from onlineshop.testing import FakeCart, FakeGateway, make_address, make_product, make_user
from orders.models import Coupon, Order
from orders.services import (
    OrderActionError,
    OrderCreationError,
    advance_order,
    cancel_order,
    create_order_from_cart,
    mark_order_paid,
    resolve_coupon_review,
    retry_reservation,
)

from .models import Payment, RefundRequest
from .refunds import confirm_bank_refund
from .services import PaymentError, process_callback, reconcile_payment, start_payment


class DemoRegressionTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.product = make_product(inventory=5)
        self.cart = FakeCart([(self.product, 2)])
        self.order = create_order_from_cart(self.cart, self.address, self.user)
        self.gateway = FakeGateway()
        self.patcher = patch("payment.services.get_gateway", return_value=self.gateway)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def start(self):
        return start_payment(self.order, self.user, "http://127.0.0.1:8000/payment/verify/").rsplit("/", 1)[1]

    def test_active_attempt_reused(self):
        self.assertEqual(self.start(), self.start())
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(self.gateway.request_calls, 1)

    def test_unknown_blocks_new_attempt(self):
        authority = self.start()
        Payment.objects.filter(authority=authority).update(status="unknown")
        with self.assertRaises(PaymentError):
            self.start()
        self.assertEqual(self.gateway.request_calls, 1)

    def test_success_survives_notification_failure_and_recovers(self):
        authority = self.start()
        with patch("orders.tracking.OrderNotification.objects.create", side_effect=RuntimeError("test")):
            outcome = process_callback(authority)
        self.assertTrue(outcome.succeeded)
        payment = Payment.objects.get(authority=authority)
        self.assertEqual(payment.status, "success")
        self.assertTrue(payment.needs_reconciliation)
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)
        reconcile_payment(payment.pk)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertFalse(payment.needs_reconciliation)
        self.assertEqual(self.gateway.verify_calls, 1)

    def test_paid_cancellation_creates_refund_and_replay_does_not_reopen(self):
        authority = self.start()
        process_callback(authority)
        cancel_order(self.order)
        refund = RefundRequest.objects.get()
        self.assertEqual(refund.amount, self.order.total_price)
        process_callback(authority)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "canceled")
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_financial_history_protected(self):
        process_callback(self.start())
        with self.assertRaises(ProtectedError):
            self.user.delete()
        with self.assertRaises(ProtectedError):
            self.order.delete()

    def test_deleted_simple_product_requires_review(self):
        authority = self.start()
        cancel_order(self.order)
        self.product.delete()
        process_callback(authority)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "needs_review")
        self.assertFalse(self.order.stock_reserved)
        self.assertTrue(self.order.is_paid)

    def test_checkout_key_replays_without_new_reservation(self):
        key = str(uuid4())
        first = create_order_from_cart(self.cart, self.address, self.user, checkout_key=key)
        second = create_order_from_cart(self.cart, self.address, self.user, checkout_key=key)
        self.assertEqual(first.pk, second.pk)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 3)
        with self.assertRaises(OrderCreationError):
            create_order_from_cart(FakeCart([(self.product, 1)]), self.address, self.user, checkout_key=key)

    def test_cart_does_not_silently_reduce_selection(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): {"quantity": 4}}
        session.save()
        request = RequestFactory().get("/")
        request.session = session
        cart = Cart(request)
        cart.clean()
        self.assertEqual(cart.get_quantity(self.product), 4)
        self.assertFalse(cart.validate()["valid"])

    def test_staff_without_permissions_rejected(self):
        client = APIClient()
        client.force_authenticate(make_user(is_staff=True))
        self.assertEqual(client.get("/api/v1/staff/sales/").status_code, 403)
        self.assertEqual(
            client.post(f"/api/v1/staff/orders/{self.order.pk}/", {"status": "canceled"}).status_code, 403
        )

    def test_view_only_admin_cannot_run_mutation_actions(self):
        staff = make_user(is_staff=True)
        staff.user_permissions.add(
            Permission.objects.get(content_type__app_label="orders", codename="view_order")
        )
        request = RequestFactory().get("/admin/orders/order/")
        request.user = staff
        actions = admin.site._registry[Order].get_actions(request)
        self.assertNotIn("mark_canceled", actions)
        self.assertNotIn("mark_preparing", actions)

    def test_refund_confirmation_requires_finance_and_unique_bank_evidence(self):
        process_callback(self.start())
        cancel_order(self.order)
        refund = RefundRequest.objects.get()
        with self.assertRaises(PermissionDenied):
            confirm_bank_refund(refund=refund, actor=self.user, bank_reference="BANK-REFUND")
        finance = make_user(is_staff=True, is_superuser=True)
        with self.assertRaises(ValueError):
            confirm_bank_refund(refund=refund, actor=finance, bank_reference=refund.payment.ref_id)
        current = confirm_bank_refund(refund=refund, actor=finance, bank_reference="BANK-REFUND")
        self.assertEqual(current.status, "confirmed")
        current.payment.refresh_from_db()
        self.assertFalse(current.payment.needs_refund)
        self.assertEqual(
            confirm_bank_refund(refund=current, actor=finance, bank_reference="BANK-REFUND").pk, current.pk
        )

    def test_coupon_review_needs_explicit_financial_resolution(self):
        cancel_order(self.order)
        Coupon.objects.create(code="ONE", kind="fixed", value=1000, total_limit=1)
        first = create_order_from_cart(self.cart, self.address, self.user, coupon_code="ONE")
        cancel_order(first)
        other = make_user()
        second = create_order_from_cart(
            FakeCart([(self.product, 1)]), make_address(other), other, coupon_code="ONE"
        )
        with transaction.atomic():
            mark_order_paid(second, "SECOND")
            first = mark_order_paid(first, "FIRST")
        self.assertEqual(first.review_reason, "coupon_capacity")
        self.assertEqual(retry_reservation(first).status, "needs_review")
        with self.assertRaises(OrderActionError):
            advance_order(first, "preparing")
        finance = make_user(is_staff=True, is_superuser=True)
        first = resolve_coupon_review(first, actor=finance, reason="Honor demo discount")
        self.assertEqual(first.status, "preparing")
        self.assertIn(str(finance.pk), first.review_resolution)

    @override_settings(STOREFRONT_ORIGIN="http://127.0.0.1:3000")
    def test_callback_redirects_to_storefront_without_clearing_cart(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["cart"] = {str(self.product.pk): {"quantity": 1}}
        session.save()
        authority = self.start()
        response = self.client.get(reverse("payment:verify"), {"Authority": authority})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"http://127.0.0.1:3000/payment/result?order={self.order.pk}")
        self.assertTrue(self.client.session.get("cart"))

    @override_settings(LOCAL_DEMO=False)
    def test_demo_endpoint_disabled_in_normal_settings(self):
        self.assertEqual(self.client.get("/payment/demo/DEMO-" + "a" * 32 + "/").status_code, 404)

    @override_settings(
        LOCAL_DEMO=True,
        DEBUG=True,
        PAYMENT_PUBLIC_ORIGIN="http://127.0.0.1:8000",
        STOREFRONT_ORIGIN="http://127.0.0.1:3000",
    )
    def test_fake_gateway_complete_local_round_trip(self):
        self.patcher.stop()
        url = start_payment(self.order, self.user, "http://127.0.0.1:8000/payment/verify/")
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.gateway, "demo")
        self.assertContains(self.client.get(url), "هیچ پولی برداشت نمی‌شود")
        response = self.client.post(url, {"outcome": "success"})
        response = self.client.get(response["Location"])
        self.assertEqual(response["Location"], f"http://127.0.0.1:3000/payment/result?order={self.order.pk}")
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)

    @override_settings(LOCAL_DEMO=True, DEBUG=True)
    def test_demo_endpoint_rejects_non_loopback_client(self):
        self.assertEqual(self.client.get("/payment/demo/nope/", REMOTE_ADDR="203.0.113.9").status_code, 404)
