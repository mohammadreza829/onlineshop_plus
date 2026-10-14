"""Explicit single-process, loopback-only demo; never deploy this settings module."""

import os

for name, value in {
    "DJANGO_DEBUG": "True",
    "DJANGO_DB_ENGINE": "sqlite",
    "CACHE_URL": "",
    "SMS_BACKEND": "console",
    "SMS_ASYNC": "False",
    "ZARINPAL_SANDBOX": "True",
    "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost",
    "HEALTHCHECK_REQUIRE_WORKER": "False",
}.items():
    os.environ[name] = value

from .settings import *  # noqa: F403, E402

LOCAL_DEMO = True
PAYMENT_PUBLIC_ORIGIN = "http://127.0.0.1:8000"
STOREFRONT_ORIGIN = "http://127.0.0.1:3000"
DATABASES["default"]["NAME"] = BASE_DIR / ".local-demo" / "db.sqlite3"  # noqa: F405
CELERY_TASK_ALWAYS_EAGER = True
