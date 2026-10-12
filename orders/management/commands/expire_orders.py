from django.core.management.base import BaseCommand

from orders.services import expire_stale_orders


class Command(BaseCommand):
    help = "Expire unpaid orders past their reservation deadline and release their stock (run every minute)."

    def handle(self, *args, **options):
        count = expire_stale_orders()
        self.stdout.write(self.style.SUCCESS(f"{count} order(s) expired."))
