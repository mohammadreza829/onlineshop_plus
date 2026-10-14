"""Only for local synthetic benchmarks. Never use this settings module in deployment."""

from django.core.exceptions import ImproperlyConfigured

from . import settings as base
from .settings import *  # noqa: F403

if not base.DEBUG:
    raise ImproperlyConfigured("Synthetic benchmark settings require DEBUG=True")
if base.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql" or not str(
    base.DATABASES["default"]["NAME"]
).endswith("_benchmark"):
    raise ImproperlyConfigured("Use a separate PostgreSQL database ending in _benchmark")

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
BENCHMARK_ALLOW_SEED = True
# Isolated local read capacity test; keep ordinary auth/checkout/cart scopes unchanged.
REST_FRAMEWORK = {
    **base.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **base.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "anon": "100000/min",
        "user": "100000/min",
    },
}
SMS_BACKEND = "console"
SMS_ASYNC = False
MIDDLEWARE = ["onlineshop.loadtest_settings.LoadSafetyMiddleware", *base.MIDDLEWARE]


class LoadSafetyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Load-Test"] = "synthetic-only"
        return response
