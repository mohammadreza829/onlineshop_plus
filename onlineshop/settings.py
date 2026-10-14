"""
Django settings for onlineshop project.

All secrets and environment-specific values are read from environment
variables (or a local `.env` file). See `.env.example` for the full list.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

try:  # python-dotenv is optional in production (real env vars are used there)
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


def env(name, default=""):
    return os.environ.get(name, default).strip()


def env_bool(name, default=False):
    return env(name, "true" if default else "false").lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


def env_int(name, default):
    try:
        return int(env(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer.") from exc


# ==========================================
# Core
# ==========================================

DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required when DEBUG is False.")
    # Development only: a throw-away key so the project runs out of the box.
    SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ==========================================
# Applications
# ==========================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "shop",
    "cart",
    "orders",
    "account",
    "addresses",
    "payment",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "onlineshop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cart.context_processors.cart",
            ],
        },
    },
]

WSGI_APPLICATION = "onlineshop.wsgi.application"


# ==========================================
# Database
# ==========================================

if env("DJANGO_DB_ENGINE", "postgresql").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DJANGO_DB_NAME", "onlineshop"),
            "USER": env("DJANGO_DB_USER", "onlineshop_admin"),
            "PASSWORD": env("DJANGO_DB_PASSWORD"),
            "HOST": env("DJANGO_DB_HOST", "localhost"),
            "PORT": env("DJANGO_DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DJANGO_DB_CONN_MAX_AGE", 0 if DEBUG else 60),
            "CONN_HEALTH_CHECKS": True,
        }
    }


# ==========================================
# Auth
# ==========================================

AUTH_USER_MODEL = "account.ShopUser"
LOGIN_URL = "account:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ==========================================
# I18N
# ==========================================

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True


# ==========================================
# Static & media
# ==========================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ==========================================
# Third-party providers
# ==========================================

# "console" logs the OTP instead of sending it (development only).
SMS_BACKEND = env("SMS_BACKEND", "console" if DEBUG else "smsir")
SMS_IR_API_KEY = env("SMS_IR_API_KEY")
SMS_IR_LINE_NUMBER = env("SMS_IR_LINE_NUMBER")
# Template-based "verify" API (recommended for OTP). Template text e.g. "کد ورود: #CODE#"
SMS_IR_TEMPLATE_ID = env("SMS_IR_TEMPLATE_ID")
SMS_IR_TEMPLATE_PARAM = env("SMS_IR_TEMPLATE_PARAM", "CODE")

if not DEBUG and SMS_BACKEND == "console":
    raise ImproperlyConfigured("SMS_BACKEND=console is not allowed in production.")
if SMS_BACKEND == "smsir" and not SMS_IR_API_KEY:
    raise ImproperlyConfigured("SMS_IR_API_KEY is required when SMS_BACKEND=smsir.")

ZARINPAL = {
    "merchant_id": env("ZARINPAL_MERCHANT_ID", "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"),
    "sandbox": env_bool("ZARINPAL_SANDBOX", True),
    "connect_timeout": env_int("ZARINPAL_CONNECT_TIMEOUT", 5),
    "read_timeout": env_int("ZARINPAL_READ_TIMEOUT", 20),
}

if not DEBUG and ZARINPAL["sandbox"]:
    raise ImproperlyConfigured("ZARINPAL_SANDBOX must be False in production.")


# ==========================================
# Checkout & OTP
# ==========================================

# How long stock is held for an unpaid order (run `manage.py expire_orders` every minute).
ORDER_RESERVATION_MINUTES = env_int("ORDER_RESERVATION_MINUTES", 15)

OTP_LENGTH = 6
OTP_TTL_SECONDS = env_int("OTP_TTL_SECONDS", 120)
OTP_RESEND_COOLDOWN_SECONDS = env_int("OTP_RESEND_COOLDOWN_SECONDS", 60)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
OTP_MAX_SENDS_PER_PHONE_PER_HOUR = env_int("OTP_MAX_SENDS_PER_PHONE_PER_HOUR", 5)
OTP_MAX_SENDS_PER_IP_PER_HOUR = env_int("OTP_MAX_SENDS_PER_IP_PER_HOUR", 20)

# OTP codes and rate-limit counters live in the cache. LocMem is per-process;
# use Redis in production (phase 4) so limits are shared between workers.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "onlineshop",
    }
}


# ==========================================
# Logging
# ==========================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}


# ==========================================
# Django REST framework
# ==========================================

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Online Shop API",
    "DESCRIPTION": "API documentation for Cart, Orders and Payment integration",
    "VERSION": "1.0.0",
}
