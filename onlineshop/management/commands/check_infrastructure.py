import time
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

from onlineshop.health import dependency_status
from onlineshop.tasks import worker_probe


class Command(BaseCommand):
    help = "Check DB/cache; optionally send a real task and wait for a worker to execute it."

    def add_arguments(self, parser):
        parser.add_argument("--with-worker", action="store_true")
        parser.add_argument("--timeout", type=int, default=20)

    def handle(self, *args, **options):
        checks = dependency_status()
        if any(value != "up" for value in checks.values()):
            raise CommandError(f"Infrastructure unavailable: {checks}")
        if options["with_worker"]:
            if settings.CELERY_TASK_ALWAYS_EAGER:
                raise CommandError("Eager mode cannot verify a real worker.")
            probe_id = str(uuid.uuid4())
            key = f"infra:worker_probe:{probe_id}"
            worker_probe.delay(probe_id)
            deadline = time.monotonic() + options["timeout"]
            while time.monotonic() < deadline:
                if cache.get(key) == "ok":
                    cache.delete(key)
                    self.stdout.write("DB/cache/real Celery worker: OK")
                    return
                time.sleep(0.2)
            raise CommandError("Worker did not execute probe before timeout.")
        self.stdout.write("DB/cache: OK")
