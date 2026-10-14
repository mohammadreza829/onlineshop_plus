import logging
import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)
WORKER_HEARTBEAT_KEY = "infra:worker_heartbeat"


def dependency_status():
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
        checks["database"] = "up"
    except Exception:
        checks["database"] = "down"
        logger.error("dependency_check_failed", extra={"dependency": "database"})
    key = f"infra:probe:{uuid.uuid4().hex}"
    try:
        cache.set(key, "ok", timeout=10)
        if cache.get(key) != "ok":
            raise RuntimeError("cache round trip failed")
        cache.delete(key)
        checks["cache"] = "up"
        if settings.HEALTHCHECK_REQUIRE_WORKER:
            checks["worker"] = "up" if cache.get(WORKER_HEARTBEAT_KEY) else "down"
    except Exception:
        checks["cache"] = "down"
        if settings.HEALTHCHECK_REQUIRE_WORKER:
            checks["worker"] = "down"
        logger.error("dependency_check_failed", extra={"dependency": "cache"})
    return checks


@require_GET
def live(request):
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request):
    checks = dependency_status()
    healthy = all(value == "up" for value in checks.values())
    return JsonResponse(
        {"status": "ok" if healthy else "unavailable", "checks": checks}, status=200 if healthy else 503
    )
