"""Loopback-only isolated Django integration harness. NEVER a production entrypoint.
Real API/business logic; only OTP randomness/SMS transport and gateway are test doubles.
No real account, message or money. Existing project DB/settings files are untouched.
"""

import json
import os
import secrets
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from wsgiref.simple_server import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.update(
    DJANGO_DEBUG="True",
    FRONTEND_ORIGIN="http://127.0.0.1:3100",
    DJANGO_DB_ENGINE="sqlite",
    DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
    DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,testserver",
    CACHE_URL="",
    SMS_ASYNC="False",
    SMS_BACKEND="console",
    ZARINPAL_SANDBOX="True",
    HEALTHCHECK_REQUIRE_WORKER="False",
)
from django.conf import settings  # noqa: E402

from onlineshop import settings as base  # noqa: E402

config = {name: getattr(base, name) for name in dir(base) if name.isupper()}
temp = tempfile.TemporaryDirectory(prefix="shop-front-django-")
config["DATABASES"] = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(Path(temp.name) / "qa.sqlite3")}
}
config["CACHES"] = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "frontend-isolated"}
}
config["LOGGING"] = {"version": 1, "disable_existing_loggers": True}
config["REST_FRAMEWORK"] = {
    **config["REST_FRAMEWORK"],
    "DEFAULT_THROTTLE_RATES": {k: "10000/minute" for k in config["REST_FRAMEWORK"]["DEFAULT_THROTTLE_RATES"]},
}
settings.configure(**config)
import django  # noqa: E402

django.setup()
from django.core.management import call_command  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402

from onlineshop.testing import FakeGateway  # noqa: E402
from orders.models import Coupon  # noqa: E402
from shop.models import Category, Product, ProductVariant  # noqa: E402

call_command("migrate", verbosity=0, interactive=False)
cat = Category.objects.create(name="لباس‌های تست ایزوله", slug="qa-clothes")
Product.objects.create(
    category=cat,
    sku="QA-SIMPLE",
    name="پیراهن تست ساده",
    slug="qa-simple",
    price=120000,
    inventory=30,
    weight=400,
    description="این محصول فقط fixture آزمایش است؛ داده production نیست.",
)
p = Product.objects.create(
    category=cat,
    sku="QA-VARIANT",
    name="پیراهن تست متنوع",
    slug="qa-variant",
    price=200000,
    inventory=0,
    weight=400,
    description="دادهٔ ایزولهٔ تست اتصال Django. <script>این متن اجرا نمی‌شود</script>",
)
ProductVariant.objects.create(product=p, sku="QA-BLACK-M", color="مشکی", size="M", price=210000, inventory=20)
ProductVariant.objects.create(product=p, sku="QA-BLACK-L", color="مشکی", size="L", price=220000, inventory=0)
ProductVariant.objects.create(product=p, sku="QA-CREAM-L", color="کرم", size="L", price=230000, inventory=20)
Coupon.objects.create(code="QA10", kind=Coupon.PERCENT, value=10, per_user_limit=20)

gateway = FakeGateway()
app = get_wsgi_application()


def application(environ, start_response):
    if environ.get("PATH_INFO") == "/__test__/health/":
        start_response("200 OK", [("Content-Type", "application/json")])
        return [json.dumps({"test_only": True}).encode()]
    return app(environ, start_response)


class Quiet(WSGIRequestHandler):
    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    with (
        patch("account.otp.secrets.randbelow", return_value=123456),
        patch("account.otp.send_otp"),
        patch("payment.services.get_gateway", return_value=gateway),
    ):
        print("Isolated Django QA ready on 127.0.0.1:8100 (test doubles; no external sends)", flush=True)
        with make_server("127.0.0.1", 8100, application, handler_class=Quiet) as server:
            try:
                server.serve_forever()
            finally:
                temp.cleanup()
