from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from onlineshop.testing import make_product

from . import otp
from .sms import SMSError

OTP_SETTINGS = dict(
    SMS_BACKEND="console",
    OTP_TTL_SECONDS=120,
    OTP_RESEND_COOLDOWN_SECONDS=60,
    OTP_MAX_ATTEMPTS=5,
    OTP_MAX_SENDS_PER_PHONE_PER_HOUR=5,
    OTP_MAX_SENDS_PER_IP_PER_HOUR=20,
)


class NormalizePhoneTests(TestCase):
    def test_accepts_common_formats(self):
        for raw in [
            "09121234567",
            "9121234567",
            "+989121234567",
            "00989121234567",
            "989121234567",
            "۰۹۱۲۱۲۳۴۵۶۷",
            "0912 123 4567",
            "0912-123-4567",
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(otp.normalize_phone(raw), "09121234567")

    def test_rejects_invalid(self):
        for raw in ["", "0912123456", "091212345678", "08121234567", "abc", "+1 555 123 4567", None]:
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                otp.normalize_phone(raw)


@override_settings(**OTP_SETTINGS)
class OTPServiceTests(TestCase):
    phone = "09121234567"

    def setUp(self):
        cache.clear()
        patcher = mock.patch("account.otp.send_otp")
        self.send_otp = patcher.start()
        self.addCleanup(patcher.stop)

    def sent_code(self):
        return self.send_otp.call_args.args[1]

    def test_correct_code_logs_in_once(self):
        otp.send_code(self.phone)
        code = self.sent_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(otp.verify_code(self.phone, code))
        with self.assertRaises(otp.OTPError):  # burned after use
            otp.verify_code(self.phone, code)

    def test_code_is_generated_with_secrets_and_stored_hashed(self):
        with mock.patch("account.otp.secrets.randbelow", return_value=42):
            otp.send_code(self.phone)
        self.assertEqual(self.sent_code(), "000042")
        stored = cache.get("otp:code:09121234567")
        self.assertNotIn("000042", stored)

    def test_wrong_code_and_attempt_limit(self):
        otp.send_code(self.phone)
        code = self.sent_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(4):
            self.assertFalse(otp.verify_code(self.phone, wrong))
        with self.assertRaises(otp.OTPError):  # 5th wrong attempt burns the code
            otp.verify_code(self.phone, wrong)
        with self.assertRaises(otp.OTPError):  # even the right code is now useless
            otp.verify_code(self.phone, code)

    def test_code_expires(self):
        otp.send_code(self.phone)
        code = self.sent_code()
        # Expire through the cache API: Redis uses server time, not Python's clock.
        cache.touch(otp._key("code", self.phone), timeout=0)
        with self.assertRaises(otp.OTPError):
            otp.verify_code(self.phone, code)

    def test_persian_digits_in_code_are_accepted(self):
        with mock.patch("account.otp.secrets.randbelow", return_value=123456):
            otp.send_code(self.phone)
        self.assertTrue(otp.verify_code(self.phone, "۱۲۳۴۵۶"))

    def test_resend_cooldown(self):
        otp.send_code(self.phone)
        with self.assertRaises(otp.OTPError) as ctx:
            otp.send_code(self.phone)
        self.assertGreater(ctx.exception.retry_after, 0)
        self.assertEqual(self.send_otp.call_count, 1)

    @override_settings(OTP_RESEND_COOLDOWN_SECONDS=0)
    def test_hourly_limit_per_phone(self):
        for _ in range(5):
            otp.send_code(self.phone)
        with self.assertRaises(otp.OTPError):
            otp.send_code(self.phone)
        self.assertEqual(self.send_otp.call_count, 5)

    @override_settings(OTP_RESEND_COOLDOWN_SECONDS=0, OTP_MAX_SENDS_PER_IP_PER_HOUR=3)
    def test_hourly_limit_per_ip(self):
        for i in range(3):
            otp.send_code(f"0912000000{i}", ip="1.2.3.4")
        with self.assertRaises(otp.OTPError):
            otp.send_code("09120000009", ip="1.2.3.4")
        otp.send_code("09120000009", ip="5.6.7.8")  # other IPs unaffected

    def test_sms_failure_does_not_lock_user_out(self):
        self.send_otp.side_effect = SMSError("down")
        with self.assertRaises(otp.OTPError):
            otp.send_code(self.phone)
        self.assertEqual(otp.cooldown_remaining(self.phone), 0)
        self.send_otp.side_effect = None
        otp.send_code(self.phone)  # retry allowed immediately


@override_settings(**OTP_SETTINGS)
class LoginViewTests(TestCase):
    def setUp(self):
        cache.clear()
        patcher = mock.patch("account.otp.send_otp")
        self.send_otp = patcher.start()
        self.addCleanup(patcher.stop)

    def request_code(self, phone="۰۹۱۲۱۲۳۴۵۶۷", next_url=""):
        response = self.client.post(reverse("account:login"), {"phone": phone, "next": next_url})
        self.assertRedirects(response, reverse("account:verify_code"), fetch_redirect_response=False)
        return self.send_otp.call_args.args[1]

    def test_full_login_registers_user_and_redirects_to_next(self):
        code = self.request_code(next_url="/orders/create/")
        self.assertNotIn(code, str(dict(self.client.session)))  # code never in the session
        response = self.client.post(reverse("account:verify_code"), {"code": code, "action": "verify"})
        self.assertRedirects(response, "/orders/create/", fetch_redirect_response=False)
        user = get_user_model().objects.get(phone="09121234567")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_open_redirect_is_blocked(self):
        code = self.request_code(next_url="https://evil.example/")
        response = self.client.post(reverse("account:verify_code"), {"code": code, "action": "verify"})
        self.assertRedirects(response, reverse("shop:home"), fetch_redirect_response=False)

    def test_wrong_code(self):
        code = self.request_code()
        wrong = "000000" if code != "000000" else "111111"
        response = self.client.post(reverse("account:verify_code"), {"code": wrong, "action": "verify"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "اشتباه")

    def test_invalid_phone_shows_form_error(self):
        response = self.client.post(reverse("account:login"), {"phone": "12345"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "معتبر نیست")
        self.send_otp.assert_not_called()

    def test_inactive_user_cannot_log_in(self):
        get_user_model().objects.create_user(phone="09121234567", password=None, is_active=False)
        code = self.request_code()
        self.client.post(reverse("account:verify_code"), {"code": code, "action": "verify"})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_cart_survives_login(self):
        product = make_product()
        self.client.post(reverse("cart:cart_add", args=[product.id]), {"quantity": 2})
        code = self.request_code()
        self.client.post(reverse("account:verify_code"), {"code": code, "action": "verify"})
        self.assertEqual(self.client.session["cart"], {str(product.id): {"quantity": 2}})

    def test_verify_page_without_phone_redirects(self):
        response = self.client.get(reverse("account:verify_code"))
        self.assertRedirects(response, reverse("account:login"), fetch_redirect_response=False)

    def test_logout_requires_post(self):
        user = get_user_model().objects.create_user(phone="09121234567", password=None)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("account:logout")).status_code, 405)
        self.client.post(reverse("account:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_required_redirects_to_otp_login(self):
        response = self.client.get(reverse("orders:order_create"))
        self.assertRedirects(
            response, reverse("account:login") + "?next=/orders/create/", fetch_redirect_response=False
        )
