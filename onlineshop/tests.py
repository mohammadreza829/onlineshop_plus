import json
import logging
import threading
import uuid
from unittest import mock, skipUnless

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from account import otp
from account.sms import SMSError, send_otp
from account.tasks import cipher, decode_payload, deliver_otp_task, encrypt_payload
from onlineshop.health import WORKER_HEARTBEAT_KEY
from onlineshop.observability import JSONFormatter
from onlineshop.tasks import worker_heartbeat, worker_probe


class HealthTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_live_is_process_only_and_read_only(self):
        self.assertEqual(self.client.get(reverse("health_live")).json(), {"status": "ok"})
        self.assertEqual(self.client.post(reverse("health_live")).status_code, 405)

    def test_ready_checks_database_and_cache(self):
        response = self.client.get(reverse("health_ready"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"], {"database": "up", "cache": "up"})

    def test_cache_failure_returns_503_without_error_detail(self):
        with mock.patch("onlineshop.health.cache.set", side_effect=RuntimeError("private-credentials")):
            response = self.client.get(reverse("health_ready"))
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "private-credentials", status_code=503)

    def test_database_failure_returns_503(self):
        with mock.patch("onlineshop.health.connection.cursor", side_effect=RuntimeError("down")):
            self.assertEqual(self.client.get(reverse("health_ready")).status_code, 503)

    @override_settings(HEALTHCHECK_REQUIRE_WORKER=True)
    def test_worker_is_required_when_enabled(self):
        self.assertEqual(self.client.get(reverse("health_ready")).status_code, 503)
        worker_heartbeat.run()
        self.assertTrue(cache.get(WORKER_HEARTBEAT_KEY))
        self.assertEqual(self.client.get(reverse("health_ready")).status_code, 200)

    def test_probe_only_accepts_uuid(self):
        probe = str(uuid.uuid4())
        worker_probe.run(probe)
        self.assertEqual(cache.get(f"infra:worker_probe:{probe}"), "ok")
        with self.assertRaises(ValueError):
            worker_probe.run("arbitrary-cache-key")

    def test_check_command(self):
        call_command("check_infrastructure", verbosity=0)


class LoggingTests(TestCase):
    def test_request_id_is_validated_and_queries_are_not_logged(self):
        supplied = str(uuid.uuid4())
        with self.assertLogs("onlineshop.http", level="INFO") as logs:
            response = self.client.get(
                reverse("health_live") + "?secret=do-not-log", HTTP_X_REQUEST_ID=supplied
            )
        self.assertEqual(response["X-Request-ID"], supplied)
        self.assertNotIn("do-not-log", str(logs.output))
        response = self.client.get(reverse("health_live"), HTTP_X_REQUEST_ID="bad\nheader")
        uuid.UUID(response["X-Request-ID"])

    def test_json_redacts_phone_otp_credentials_and_bearer(self):
        record = logging.LogRecord(
            "test",
            logging.WARNING,
            "",
            1,
            "OTP for 09121234567: 123456 redis://user:password@host redis://:another-secret@host Bearer abcdef",
            (),
            None,
        )
        data = json.loads(JSONFormatter().format(record))
        for secret in ["09121234567", "123456", "password", "another-secret", "abcdef"]:
            self.assertNotIn(secret, data["message"])
        self.assertEqual(data["level"], "WARNING")


class AsyncOTPTests(TestCase):
    phone = "09121234567"
    code = "123456"

    def setUp(self):
        cache.clear()
        cache.set(otp._key("code", self.phone), otp._hash(self.phone, self.code), timeout=120)

    def payload(self):
        return encrypt_payload(self.phone, self.code)

    def test_broker_payload_is_encrypted_and_tamper_proof(self):
        payload = self.payload()
        self.assertNotIn(self.phone, payload)
        self.assertNotIn(self.code, payload)
        self.assertEqual(decode_payload(payload)["code"], self.code)
        self.assertIsNone(decode_payload(payload[:-5] + "wrong"))

    def test_expired_payload_is_ignored(self):
        payload = (
            cipher()
            .encrypt(json.dumps({"phone": self.phone, "code": self.code, "expires_at": 1}).encode())
            .decode()
        )
        self.assertIsNone(decode_payload(payload))

    @override_settings(SMS_ASYNC=True)
    def test_dispatch_enqueues_encrypted_payload_with_expiry(self):
        with mock.patch("account.tasks.deliver_otp_task.apply_async") as publish:
            send_otp(self.phone, self.code)
        payload = publish.call_args.kwargs["args"][0]
        self.assertNotIn(self.code, payload)
        self.assertEqual(publish.call_args.kwargs["expires"], settings.OTP_TTL_SECONDS)

    @override_settings(SMS_ASYNC=True)
    def test_broker_failure_is_sms_error(self):
        with mock.patch("account.tasks.deliver_otp_task.apply_async", side_effect=OSError("down")):
            with self.assertRaises(SMSError):
                send_otp(self.phone, self.code)

    def test_delivery_drops_stale_and_repeated_payloads(self):
        payload = self.payload()
        with mock.patch("account.tasks.deliver_otp") as deliver:
            self.assertEqual(deliver_otp_task.run(payload), "sent")
            self.assertEqual(deliver_otp_task.run(payload), "already_delivered")
            deliver.assert_called_once_with(self.phone, self.code)
        cache.delete(otp._key("code", self.phone))
        self.assertEqual(deliver_otp_task.run(self.payload()), "stale")

    def test_superseded_code_is_not_delivered(self):
        payload = self.payload()
        cache.set(otp._key("code", self.phone), otp._hash(self.phone, "999999"), timeout=120)
        with mock.patch("account.tasks.deliver_otp") as deliver:
            self.assertEqual(deliver_otp_task.run(payload), "stale")
            deliver.assert_not_called()

    def test_terminal_failure_does_not_delete_newer_challenge(self):
        payload = self.payload()
        cache.set(otp._key("code", self.phone), otp._hash(self.phone, "999999"), timeout=120)
        deliver_otp_task.on_failure(SMSError("down"), "id", [payload], {}, None)
        self.assertEqual(cache.get(otp._key("code", self.phone)), otp._hash(self.phone, "999999"))

    def test_terminal_failure_releases_current_challenge_for_resend(self):
        deliver_otp_task.on_failure(SMSError("down"), "id", [self.payload()], {}, None)
        self.assertIsNone(cache.get(otp._key("code", self.phone)))

    @override_settings(SMS_ASYNC=False)
    def test_sync_delivery_remains_available(self):
        with mock.patch("account.sms.deliver_otp") as deliver:
            send_otp(self.phone, self.code)
        deliver.assert_called_once_with(self.phone, self.code)


@skipUnless(bool(settings.CACHE_URL), "requires real shared Redis")
class RedisConcurrencyTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_parallel_code_verification_succeeds_only_once(self):
        phone, code = "09121234567", "123456"
        cache.set(otp._key("code", phone), otp._hash(phone, code), timeout=120)
        barrier = threading.Barrier(4)
        results = []

        def verify():
            barrier.wait(timeout=5)
            try:
                results.append(otp.verify_code(phone, code))
            except otp.OTPError:
                results.append(False)

        threads = [threading.Thread(target=verify) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(results.count(True), 1)

    def test_parallel_sends_share_cooldown(self):
        barrier = threading.Barrier(4)
        results = []

        def send():
            barrier.wait(timeout=5)
            try:
                otp.send_code("09121234567")
                results.append(True)
            except otp.OTPError:
                results.append(False)

        with mock.patch("account.otp.send_otp") as deliver:
            threads = [threading.Thread(target=send) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertEqual(deliver.call_count, 1)
        self.assertEqual(results.count(True), 1)


class PeriodicTaskTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_expiration_task_calls_idempotent_service(self):
        from orders.tasks import expire_unpaid_orders

        with mock.patch("orders.tasks.expire_stale_orders", return_value=3) as expire:
            self.assertEqual(expire_unpaid_orders.run(), 3)
        expire.assert_called_once()

    def test_reconcile_one_handles_deleted_payment(self):
        from payment.tasks import reconcile_one

        self.assertEqual(reconcile_one.run(-1), "deleted")

    def test_reconcile_dispatches_old_payments_not_fresh_or_finalized(self):
        from datetime import timedelta

        from django.utils import timezone

        from onlineshop.testing import FakeCart, make_address, make_product, make_user
        from orders.services import create_order_from_cart
        from payment.models import Payment
        from payment.tasks import dispatch_stale_payments

        user = make_user()
        order = create_order_from_cart(FakeCart([(make_product(), 1)]), make_address(user), user)
        old = Payment.objects.create(order=order, user=user, amount=order.total_price, authority="OLD")
        Payment.objects.filter(pk=old.pk).update(updated_at=timezone.now() - timedelta(minutes=20))
        Payment.objects.create(order=order, user=user, amount=order.total_price, authority="FRESH")
        final = Payment.objects.create(
            order=order, user=user, amount=order.total_price, authority="FINAL", status=Payment.STATUS_SUCCESS
        )
        Payment.objects.filter(pk=final.pk).update(updated_at=timezone.now() - timedelta(minutes=20))
        with mock.patch("payment.tasks.reconcile_one.delay") as enqueue:
            dispatch_stale_payments.run()
        enqueue.assert_called_once_with(old.pk)

    def test_blacklist_cleanup_is_scheduled(self):
        self.assertIn("blacklist-cleanup", settings.CELERY_BEAT_SCHEDULE)
        from onlineshop.tasks import clean_expired_tokens

        with mock.patch("onlineshop.tasks.call_command") as command:
            clean_expired_tokens.run()
        command.assert_called_once_with("flushexpiredtokens", verbosity=0)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_eager_mode_is_not_mistaken_for_a_real_worker(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("check_infrastructure", with_worker=True)

    def test_cache_outage_is_explicit_auth_unavailability(self):
        from redis.exceptions import ConnectionError

        with mock.patch("account.otp._phone_lock", side_effect=ConnectionError("down")):
            with self.assertRaises(otp.OTPUnavailable):
                otp.verify_code("09121234567", "123456")
