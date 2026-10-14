from celery import shared_task

from .services import expire_stale_orders


@shared_task(ignore_result=True)
def expire_unpaid_orders():
    return expire_stale_orders()
