"""Explicit, isolated development profile. NEVER deploy this profile."""

import copy
import os
import secrets
from pathlib import Path

_data = Path(os.environ.get("LAPTOP_DATA_DIR", Path(__file__).resolve().parent.parent / ".local")).resolve()
_data.mkdir(parents=True, exist_ok=True)
_secret_file = _data / "django-secret"
try:
    # Exclusive creation avoids replacing a secret on reload/concurrent startup.
    with _secret_file.open("x", encoding="utf-8") as _handle:
        _handle.write(secrets.token_urlsafe(48))
    _secret_file.chmod(0o600)
except FileExistsError:
    pass

# Set BEFORE importing base settings: stale .env production values cannot select
# PostgreSQL, SMS.ir or Redis in this explicitly requested local profile.
os.environ.update(
    DJANGO_DEBUG="true",
    DJANGO_SECRET_KEY=_secret_file.read_text(encoding="utf-8").strip(),
    DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost",
    DJANGO_DB_ENGINE="sqlite",
    CACHE_URL="",
    SMS_BACKEND="console",
    SMS_ASYNC="false",
    ZARINPAL_SANDBOX="true",
    HEALTHCHECK_REQUIRE_WORKER="false",
    JWT_SIGNING_KEY="",
    DJANGO_LOG_LEVEL="INFO",
)

from .settings import *  # noqa: E402,F403
from .settings import LOGGING as _base_logging  # noqa: E402

LOCAL_DEMO_MODE = True
LOCAL_PAYMENT_DISABLED = True
DEMO_DATABASE_PATH = _data / "laptop.sqlite3"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DEMO_DATABASE_PATH,
        "OPTIONS": {"timeout": 20},
    }
}
MEDIA_ROOT = _data / "media"
STATIC_ROOT = _data / "static"
# No worker/broker is required. Do not eagerly execute scheduled expiration jobs.
CELERY_BROKER_URL = "memory://"
CELERY_TASK_ALWAYS_EAGER = False

# Production JSON logs deliberately redact all six-digit values. Only the
# isolated console-SMS logger may reveal the dev OTP to the local operator.
# Keep every other log redacted and do not forward this handler to a collector.
LOGGING = copy.deepcopy(_base_logging)
LOGGING["formatters"]["local_otp"] = {
    "format": "LOCAL DEVELOPMENT ONLY — %(message)s",
}
LOGGING["handlers"]["local_otp"] = {
    "class": "logging.StreamHandler",
    "formatter": "local_otp",
}
LOGGING["loggers"]["account.sms"] = {
    "handlers": ["local_otp"],
    "level": "WARNING",
    "propagate": False,
}
