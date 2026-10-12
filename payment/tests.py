import threading
from datetime import timedelta
from unittest import mock, skipUnless

import requests
from django.db import close_old_connections, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from onlineshop.testing import FakeCart, FakeGateway, make_address, make_product, make_user
from orders.models import Order
from orders.services import cancel_order, create_order_from_cart

from .gateway import VerifyStatus, ZarinpalGateway
from .models import Payment
from .services import PaymentError, process_callback, reconcile_stale_payments, start_payment

CALLBACK = "https://shop.test/payment/verify/"


def fake_response(status_code=200, json_body=None, raises=None):
    response = mock.Mock(status_code=status_code)
    if raises:
        response.json.side_effect = raises
    else:
        response.json.return_value = json_body
    return response


class ZarinpalGatewayTests(SimpleTestCase):
    def setUp(self):
        self.gw = ZarinpalGateway(merchant_id="m", sandbox=True)

    @mock.patch("payment.gateway.requests.post")
    def test_request_success_converts_toman_to_rial(self, post):
        post.return_value = fake_response(json_body={"data": {"code": 100, "authority": "A1"}, "errors": []})
        result = self.gw.request_payment(150_000, "desc", CALLBACK, mobile="09121234567")
        self.assertTrue(result.ok)
        self.assertEqual(result.payment_url, "https://sandbox.zarinpal.com/pg/StartPay/A1")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], 1_500_000)
        self.assertEqual(payload["merchant_id"], "m")
        self.assertIsNotNone(post.call_args.kwargs["timeout"])

    @mock.patch("payment.gateway.requests.post")
    def test_request_rejected(self, post):
        post.return_value = fake_response(422, {"data": [], "errors": {"code": -9, "message": "validation"}})
        result = self.gw.request_payment(1000, "d", CALLBACK)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, -9)

    @mock.patch("payment.gateway.requests.post", side_effect=requests.Timeout("slow"))
    def test_request_timeout(self, post):
        self.assertFalse(self.gw.request_payment(1000, "d", CALLBACK).ok)

    @mock.patch("payment.gateway.requests.post")
    def test_verify_classification(self, post):
        cases = [
            (fake_response(json_body={"data": {"code": 100, "ref_id": 201, "card_pan": "5022****1234"}}), VerifyStatus.SUCCESS),
            (fake_response(json_body={"data": {"code": 101, "ref_id": 201}}), VerifyStatus.SUCCESS),
            (fake_response(422, {"data": [], "errors": {"code": -51}}), VerifyStatus.FAILED),
            (fake_response(422, {"data": [], "errors": {"code": -54}}), VerifyStatus.FAILED),
            (fake_response(422, {"data": [], "errors": {"code": -9}}), VerifyStatus.UNKNOWN),
            (fake_response(json_body={"data": {"code": 100}}), VerifyStatus.UNKNOWN),  # success without ref_id
            (fake_response(502, raises=ValueError()), VerifyStatus.UNKNOWN),
            (fake_response(200, raises=ValueError()), VerifyStatus.UNKNOWN),
            (fake_response(200, ["not", "a", "dict"]), VerifyStatus.UNKNOWN),
        ]
        for response, expected in cases:
            with self.subTest(expected=expected, body=response.json.return_value):
                post.return_value = response
                self.assertEqual(self.gw.verify(1000, "A1").status, expected)
        self.assertEqual(post.call_args.kwargs["json"]["amount"], 10_000)

    @mock.patch("payment.gateway.requests.post", side_effect=requests.ConnectionError("down"))
    def test_verify_network_error_is_unknown_not_failed(self, post):
        self.assertEqual(self.gw.verify(1000, "A1").status, VerifyStatus.UNKNOWN)


class PaymentFlowTestBase(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(inventory=5, price=100_000)
        self.order = create_order_from_cart(FakeCart([(self.product, 2)]), make_address(self.user), self.user)
        self.gateway = FakeGateway()
        patcher = mock.patch("payment.services.get_gateway", return_value=self.gateway)
        patcher.start()
        self.addCleanup(patcher.stop)

    def stock(self):
        self.product.refresh_from_db()
        return self.product.inventory

    def start(self):
        url = start_payment(self.order, self.user, CALLBACK)
        return url.rsplit("/", 1)[1]


class StartPaymentTests(PaymentFlowTestBase):
    def test_creates_payment_with_order_total(self):
        authority = self.start()
        payment = Payment.objects.get(authority=authority)
        self.assertEqual(payment.amount, self.order.total_price)
        self.assertEqual(payment.status, Payment.STATUS_PENDING)

    def test_expired_order_cannot_be_paid_and_releases_stock(self):
        Order.objects.filter(pk=self.order.pk).update(reserved_until=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(PaymentError):
            self.start()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_EXPIRED)
        self.assertEqual(self.stock(), 5)
        self.assertEqual(self.gateway.request_calls, 0)

    def test_gateway_rejection_marks_payment_failed(self):
        self.gateway.request_ok = False
        with self.assertRaises(PaymentError):
            self.start()
        self.assertEqual(Payment.objects.get().status, Payment.STATUS_FAILED)

    def test_paid_order_cannot_be_paid_again(self):
        process_callback(self.start())
        with self.assertRaises(PaymentError):
            self.start()

    def test_process_view_requires_post_and_owner(self):
        self.client.force_login(self.user)
        url = reverse("payment:process", args=[self.order.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertTrue(self.client.post(url)["Location"].startswith("https://gw.test/"))
        self.client.force_login(make_user())
        self.assertEqual(self.client.post(url).status_code, 404)


class CallbackTests(PaymentFlowTestBase):
    def callback(self, authority, status="OK"):
        return self.client.get(reverse("payment:verify"), {"Authority": authority, "Status": status})

    def test_success_marks_order_paid_once(self):
        self.client.force_login(self.user)
        self.client.post(reverse("cart:cart_add", args=[self.product.id]), {"quantity": 1})
        authority = self.start()

        response = self.callback(authority)
        self.assertContains(response, "REF-1")
        self.assertContains(response, self.order.order_number)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PAID)
        self.assertEqual(self.order.ref_id, "REF-1")
        self.assertEqual(self.stock(), 3)  # reserved at checkout, not deducted again
        self.assertFalse(self.client.session.get("cart"))  # cart cleared

        self.callback(authority)  # refresh / double callback
        self.assertEqual(self.gateway.verify_calls, 1)
        self.assertEqual(self.stock(), 3)
        payment = Payment.objects.get(authority=authority)
        self.assertEqual((payment.status, payment.card_pan), (Payment.STATUS_SUCCESS, "6037****1234"))

    def test_failed_payment_keeps_order_payable(self):
        self.gateway.verify_status = VerifyStatus.FAILED
        authority = self.start()
        response = self.callback(authority, status="NOK")
        self.assertContains(response, "پرداخت انجام نشد")
        self.assertEqual(self.gateway.verify_calls, 1)  # status param is never trusted alone
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_payable)
        self.assertEqual(Payment.objects.get().status, Payment.STATUS_FAILED)

    def test_spoofed_ok_status_does_not_mark_paid(self):
        self.gateway.verify_status = VerifyStatus.FAILED
        self.callback(self.start(), status="OK")
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)

    def test_unknown_result_then_reconcile(self):
        self.gateway.verify_status = VerifyStatus.UNKNOWN
        authority = self.start()
        response = self.callback(authority)
        self.assertContains(response, "هنوز مشخص نیست")
        self.assertEqual(Payment.objects.get().status, Payment.STATUS_UNKNOWN)

        self.gateway.verify_status = VerifyStatus.SUCCESS
        Payment.objects.update(created_at=timezone.now() - timedelta(minutes=20))
        self.assertEqual(reconcile_stale_payments(), {Payment.STATUS_SUCCESS: 1})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PAID)

    def test_reconcile_ignores_recent_payments(self):
        self.start()
        self.assertEqual(reconcile_stale_payments(), {})
        self.assertEqual(self.gateway.verify_calls, 0)

    def test_payment_after_expiry_with_stock_available(self):
        authority = self.start()
        cancel_order(self.order)  # simulates expiry/cancel while the user is on the gateway
        self.assertEqual(self.stock(), 5)
        process_callback(authority)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PAID)
        self.assertEqual(self.stock(), 3)

    def test_payment_after_expiry_without_stock_is_recorded_for_review(self):
        authority = self.start()
        cancel_order(self.order)
        self.product.inventory = 0
        self.product.save()
        outcome = process_callback(authority)
        self.assertTrue(outcome.succeeded)  # money taken -> never rolled back
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_NEEDS_REVIEW)
        self.assertTrue(self.order.is_paid)
        self.assertEqual(Payment.objects.get().status, Payment.STATUS_SUCCESS)

    def test_double_payment_is_flagged_for_refund(self):
        first, second = self.start(), self.start()
        process_callback(first)
        self.gateway.ref_id = "REF-2"
        process_callback(second)
        self.assertTrue(Payment.objects.get(authority=second).needs_refund)
        self.assertFalse(Payment.objects.get(authority=first).needs_refund)
        self.assertEqual(self.stock(), 3)

    def test_callback_without_session_still_verifies_but_hides_order(self):
        authority = self.start()
        response = self.callback(authority)  # anonymous client
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.order.order_number)
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)

    def test_unknown_authority_and_missing_params(self):
        self.assertEqual(self.callback("nope").status_code, 404)
        self.assertEqual(self.client.get(reverse("payment:verify")).status_code, 400)


@skipUnless(connection.vendor == "postgresql", "row locking needs PostgreSQL")
class ConcurrentCallbackTests(TransactionTestCase):
    def test_parallel_callbacks_verify_once(self):
        user = make_user()
        product = make_product(inventory=5)
        order = create_order_from_cart(FakeCart([(product, 2)]), make_address(user), user)
        gateway = FakeGateway()
        barrier = threading.Barrier(4)
        statuses = []

        with mock.patch("payment.services.get_gateway", return_value=gateway):
            authority = start_payment(order, user, CALLBACK).rsplit("/", 1)[1]

            def run():
                try:
                    barrier.wait()
                    statuses.append(process_callback(authority).status)
                finally:
                    close_old_connections()
                    connection.close()

            threads = [threading.Thread(target=run) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(statuses, [Payment.STATUS_SUCCESS] * 4)
        self.assertEqual(gateway.verify_calls, 1)
        product.refresh_from_db()
        self.assertEqual(product.inventory, 3)
