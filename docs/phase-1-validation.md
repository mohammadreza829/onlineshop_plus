# Phase 1 validation

Validation performed on 2026-10-14 with Python 3.13, Django 6.0.9 and PostgreSQL 16.14.
This is a local validation record, not a CI or production certification. GitHub check-runs and commit-status reads returned HTTP 403 for the connected token, so remote CI status could not be verified.

## Results

- PostgreSQL: 67 tests passed, no skips; includes simultaneous checkout of the last item and simultaneous payment callbacks.
- The two PostgreSQL concurrency tests also passed in five consecutive targeted runs.
- SQLite: 67 tests discovered, 65 passed and the two PostgreSQL-only concurrency tests skipped.
- `ruff check .`, the configured pre-commit hooks, `manage.py check`, `makemigrations --check --dry-run` and `pip check`: passed.
- Existing NULL `Order.authority` and `Payment.ref_id` values migrated to empty strings in a separate PostgreSQL QA database; paid order/payment records retained.
- Amount mismatch (`-50`) remains UNKNOWN rather than terminal FAILED: an incorrect amount is not proof that no money was received.

## Real sandbox validation (no real money)

1. A test product with inventory 5 and an order for quantity 2 were created in an isolated PostgreSQL database using the purchase service.
2. `start_payment` called the real Zarinpal sandbox API and received code 100 and an authority.
3. The sandbox payment page was opened and its simulated payment button completed; the browser returned `Authority` and `Status=OK` to a dummy callback at `example.com`.
4. Those callback parameters were passed to the application's callback view using Django's test client, with the real gateway adapter (no gateway mock for the first verification).
5. The real verify response produced SUCCESS and a reference ID, the order became PAID and stock remained 3.
6. The same callback was replayed with an assertion prohibiting a second gateway call: it returned successfully without deducting stock again.
7. A separate, unpaid sandbox authority returned `-51` and was classified FAILED.

The dummy callback was used because the shared browser cannot reach the local sandbox application. Thus this validates real request/payment/verify plus the application callback, but is not a single-browser end-to-end production deployment test.

## Reproduce automated checks

Install `requirements-dev.txt`, configure a disposable PostgreSQL database with a role permitted to create test databases, then run:

```bash
ruff check .
pre-commit run --all-files
DJANGO_DB_ENGINE=postgresql python manage.py test --noinput
DJANGO_DB_ENGINE=postgresql python manage.py test orders.tests.ConcurrentCheckoutTests payment.tests.ConcurrentCallbackTests --noinput
DJANGO_DB_ENGINE=sqlite python manage.py test --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
pip check
```

Use development settings (`DJANGO_DEBUG=True`) only for local testing; configure all required env variables before running.

## Before any production deployment

- Rotate all secrets previously committed in the initial history (SMS key, database password and Django secret). Moving secrets to env does not revoke old ones.
- Back up the database and apply migrations. Review legacy unpaid orders without a reservation; they require a new checkout, not blind payment initiation.
- Configure and validate real SMS.ir credentials/template with an authorized recipient. No real SMS was sent during this validation.
- Use a shared cache for OTP across workers; the default local-memory cache has per-process limits. Redis deployment is phase 3.
- Schedule `expire_orders` and `reconcile_payments`; verify callback reachability, HTTPS, merchant configuration and currency in the actual deployment.
- Sandbox results do not certify production settlement or eliminate all bugs. Real production payments/refunds require separate operational validation.
