from datetime import timedelta
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from onlineshop.testing import FakeCart, make_address, make_product, make_user
from orders.models import OrderEvent, OrderNotification
from orders.services import (
    advance_order,
    cancel_order,
    create_order_from_cart,
    mark_order_paid,
    update_shipping,
)
from payment.models import Payment


class OperationsTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user()
        self.staff = make_user(is_staff=True, is_superuser=True)
        self.product = make_product()
        self.order = create_order_from_cart(FakeCart([(self.product, 1)]), make_address(self.user), self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def pay(self):
        with transaction.atomic():
            self.order = mark_order_paid(self.order, "ref")

    def test_events_and_notifications_once_per_real_transition(self):
        self.pay()
        self.pay()
        self.order = advance_order(self.order, "preparing")
        self.order = advance_order(self.order, "preparing")
        self.order = update_shipping(self.order, carrier="test", tracking_code="QA-1")
        update_shipping(self.order, carrier="test", tracking_code="QA-1")
        self.order = advance_order(self.order, "sent")
        self.assertEqual(list(self.order.events.values_list("sequence", flat=True)), [1, 2, 3, 4, 5])
        self.assertEqual(OrderNotification.objects.filter(user=self.user).count(), 5)
        data = self.client.get(f"/api/v1/orders/{self.order.pk}/tracking/").json()
        self.assertEqual(data["count"], 5)
        self.assertEqual(data["results"][-1]["tracking_code"], "QA-1")

    def test_owner_isolation_read_idempotence_and_guests(self):
        pk = OrderNotification.objects.get(user=self.user).pk
        read_url = f"/api/v1/notifications/{pk}/read/"
        self.assertEqual(self.client.post(read_url).status_code, 200)
        first = OrderNotification.objects.get(pk=pk).read_at
        self.client.post(read_url)
        self.assertEqual(OrderNotification.objects.get(pk=pk).read_at, first)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/notifications/").json()["count"], 0)
        self.assertEqual(self.client.post(read_url).status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/orders/{self.order.pk}/tracking/").status_code, 404)
        self.assertIn(APIClient().get("/api/v1/notifications/").status_code, [401, 403])

    def test_failed_notification_rolls_back_status_and_stock(self):
        self.product.refresh_from_db()
        stock = self.product.inventory
        with patch(
            "orders.tracking.OrderNotification.objects.create", side_effect=RuntimeError("QA storage failure")
        ):
            with self.assertRaises(RuntimeError):
                cancel_order(self.order)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, "pending")
        self.assertEqual(self.product.inventory, stock)
        self.assertEqual(OrderEvent.objects.count(), 1)

    def test_staff_updates_are_atomic_authorized_and_validate_state(self):
        url = f"/api/v1/staff/orders/{self.order.pk}/"
        self.assertEqual(self.client.post(url, {"status": "preparing"}).status_code, 403)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(url, {"status": "preparing"}).status_code, 400)
        self.pay()
        self.assertEqual(self.client.post(url, {"status": "preparing", "carrier": "test"}).status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(
            self.client.post(
                url, {"status": "preparing", "carrier": "test", "tracking_code": "QA-2"}
            ).status_code,
            200,
        )
        self.assertEqual(self.client.post(url, {"status": "delivered"}).status_code, 400)
        self.assertEqual(self.client.post(url, {"status": "sent"}).status_code, 200)
        self.assertEqual(self.client.post(url, {"status": "delivered"}).status_code, 200)
        self.assertEqual(self.client.post(url, {"status": "canceled"}).status_code, 400)

    def test_sales_distinguishes_order_value_from_actual_payments(self):
        self.pay()
        now = timezone.now()
        Payment.objects.create(
            order=self.order, user=self.user, amount=self.order.total_price, status="success", verified_at=now
        )
        Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=self.order.total_price,
            status="success",
            verified_at=now,
            needs_refund=True,
        )
        Payment.objects.create(order=self.order, user=self.user, amount=999999, status="unknown")
        self.assertEqual(self.client.get("/api/v1/staff/sales/").status_code, 403)
        self.client.force_authenticate(self.staff)
        data = self.client.get("/api/v1/staff/sales/").json()
        self.assertEqual(data["paid_orders_count"], 1)
        self.assertEqual(int(data["paid_orders_value"]), 200000)
        self.assertEqual(int(data["successful_payment_amount"]), 400000)
        self.assertEqual(int(data["duplicate_payment_refund_flag_amount"]), 200000)
        self.assertEqual(data["unknown_payments_all_time"], 1)
        self.assertEqual(data["currency"], "TOMAN")
        cancel_order(self.order)
        data = self.client.get("/api/v1/staff/sales/").json()
        self.assertEqual(int(data["canceled_paid_orders_value"]), 200000)
        self.assertEqual(data["paid_orders_count"], 1)

    def test_dashboard_dates_are_bounded_and_payment_date_not_created_date(self):
        self.pay()
        self.order.paid_at = timezone.now() - timedelta(days=90)
        self.order.save(update_fields=["paid_at"])
        self.client.force_authenticate(self.staff)
        data = self.client.get("/api/v1/staff/sales/").json()
        self.assertEqual(data["orders_created"], 1)
        self.assertEqual(data["paid_orders_count"], 0)
        for query in [
            "from_date=invalid",
            "from_date=9999-12-31&to_date=9999-12-31",
            "from_date=0001-01-01&to_date=0001-01-01",
            "from_date=2025-01-01&to_date=2026-12-31",
            "from_date=2026-10-02&to_date=2026-10-01",
        ]:
            self.assertEqual(self.client.get("/api/v1/staff/sales/?" + query).status_code, 400)


class DashboardQueryBudgetTests(TestCase):
    def test_staff_dashboard_has_fixed_six_query_budget(self):
        staff = make_user(is_staff=True, is_superuser=True)
        client = APIClient()
        client.force_authenticate(staff)
        with self.assertNumQueries(6):
            result = client.get("/api/v1/staff/sales/")
        self.assertEqual(result.status_code, 200)
