from django.core.management.base import BaseCommand

from payment.services import reconcile_stale_payments


class Command(BaseCommand):
    help = "Re-verify PENDING/UNKNOWN payments with the gateway (callback lost, timeout, ...)."

    def add_arguments(self, parser):
        parser.add_argument("--older-than", type=int, default=15, help="minutes (default 15)")

    def handle(self, *args, **options):
        results = reconcile_stale_payments(older_than_minutes=options["older_than"])
        self.stdout.write(self.style.SUCCESS(f"reconciled: {results or 'nothing to do'}"))
