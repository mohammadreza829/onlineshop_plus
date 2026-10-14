from argparse import Namespace
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from scripts.load_backend import run


class BenchmarkSafetyTests(SimpleTestCase):
    def test_seed_command_rejects_normal_shop_settings_before_querying(self):
        with TemporaryDirectory() as path:
            with self.assertRaises(CommandError):
                call_command("seed_backend_benchmark", products=10000, output=path + "/fixtures.json")

    def test_load_runner_refuses_external_targets_without_network_calls(self):
        args = Namespace(
            base_url="https://not-our-shop.example",
            fixtures="unused",
            workers=8,
            requests=10,
            output="unused",
        )
        with patch("scripts.load_backend.requests.get") as get:
            with self.assertRaises(ValueError):
                run(args)
        get.assert_not_called()

    def test_load_runner_refuses_excessive_concurrency_before_reading_fixture(self):
        args = Namespace(
            base_url="http://127.0.0.1:18001", fixtures="unused", workers=1000, requests=10, output="unused"
        )
        with self.assertRaises(ValueError):
            run(args)

    def test_benchmark_settings_boot_only_with_isolated_database(self):
        import os
        import subprocess
        import sys

        from django.conf import settings

        environment = os.environ.copy()
        environment.update(
            DJANGO_DEBUG="True",
            DJANGO_DB_ENGINE="postgresql",
            DJANGO_DB_NAME="safety_benchmark",
            SMS_BACKEND="console",
            SMS_ASYNC="False",
        )
        command = [sys.executable, "manage.py", "check", "--settings", "onlineshop.loadtest_settings"]
        valid = subprocess.run(
            command, cwd=settings.BASE_DIR, env=environment, capture_output=True, text=True, timeout=20
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        environment["DJANGO_DB_NAME"] = "normal_shop"
        invalid = subprocess.run(
            command, cwd=settings.BASE_DIR, env=environment, capture_output=True, text=True, timeout=20
        )
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("separate PostgreSQL database", invalid.stderr)
