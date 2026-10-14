import time
from uuid import UUID

from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command

from .health import WORKER_HEARTBEAT_KEY


@shared_task(ignore_result=True)
def worker_heartbeat():
    cache.set(WORKER_HEARTBEAT_KEY, time.time(), timeout=120)


@shared_task(ignore_result=True)
def worker_probe(probe_id):
    # Only UUID keys, not arbitrary cache writes from task arguments.
    key = f"infra:worker_probe:{UUID(probe_id)}"
    cache.set(key, "ok", timeout=60)


@shared_task(ignore_result=True)
def clean_expired_tokens():
    call_command("flushexpiredtokens", verbosity=0)
