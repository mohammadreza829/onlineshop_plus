import json
from unittest.mock import patch

from django.db import connection
from django.http import JsonResponse
from django.test import RequestFactory, TestCase, override_settings

from .observability import JSONFormatter, RequestLogMiddleware


class RequestPerformanceLogTests(TestCase):
    @override_settings(SLOW_QUERY_MS=1)
    def test_counts_queries_without_logging_sql_params_query_or_slug(self):
        request = RequestFactory().get("/api/v1/products/private-customer-slug/?secret=private-token")
        request.resolver_match = type("Match", (), {"route": "api/v1/products/<slug:slug>/"})()

        def response(request):
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s", ["sensitive-sql-parameter"])
            return JsonResponse({"ok": True})

        with patch("onlineshop.observability.logging.getLogger") as logger:
            result = RequestLogMiddleware(response)(request)
        extra = logger.return_value.info.call_args.kwargs["extra"]
        self.assertEqual(result.status_code, 200)
        self.assertEqual(extra["db_queries"], 1)
        self.assertGreaterEqual(extra["db_duration_ms"], 0)
        self.assertNotIn("private-customer-slug", str(extra))
        self.assertNotIn("private-token", str(extra))
        self.assertNotIn("sensitive-sql-parameter", str(extra))
        self.assertEqual(extra["route"], "api/v1/products/<slug:slug>/")

    def test_json_formatter_preserves_numerical_performance_fields(self):
        import logging

        record = logging.makeLogRecord(
            {
                "msg": "request_completed",
                "levelname": "INFO",
                "db_queries": 2,
                "db_duration_ms": 3.5,
                "slow_query_count": 0,
            }
        )
        data = json.loads(JSONFormatter().format(record))
        self.assertEqual(data["db_queries"], 2)
        self.assertEqual(data["db_duration_ms"], 3.5)
        self.assertEqual(data["slow_query_count"], 0)
