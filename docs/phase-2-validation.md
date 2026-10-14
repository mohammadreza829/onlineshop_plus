# Phase 2 validation

Local validation on 2026-10-14 using Python 3.13, Django 6.0.9, DRF 3.18.3, SimpleJWT 5.5.1 and PostgreSQL 16.14. Base: main commit `6e3c07b6ebd2bf2c475eba79ea3a5919283264f2`.

## Scope

Shared services/selectors/policies, OTP-to-JWT authentication, refresh rotation and blacklist logout, default-private API permissions, bounded pagination and cache-backed throttling, public catalog API, private profile/address/order/payment initiation API, and canonical `/api/v1/` routes with OpenAPI documentation. Existing HTML and legacy cart/order aliases remain functional; no frontend redesign.

## Results

- Full suite on PostgreSQL: **108 passed, no skips**.
- Full suite on SQLite: **105 passed, 3 PostgreSQL-only concurrency tests skipped**.
- All three concurrency scenarios passed in **five consecutive targeted runs**: last item checkout, parallel callbacks, and parallel checkouts by one customer.
- `ruff check .` and every configured pre-commit hook passed.
- `manage.py check`, `makemigrations --check --dry-run`, and `pip check` passed.
- `manage.py spectacular --validate --fail-on-warn` passed with no schema warnings/errors.
- SimpleJWT blacklist migrations applied successfully to an existing isolated phase-1 QA database; no new application-model migration is required.

## Covered behaviors

- Catalog inactive-product exclusion, exact category/stock/base-price filters, search, allowed ordering, invalid query handling, stable pagination and real maximum page-size enforcement.
- Category search, root/parent filtering, read-only access, product features and category serialization.
- Catalog list query count remains two queries as more products are added (count + joined list).
- OTP registration with unusable password, correct/wrong/reused codes, invalid phone, cooldown 429, provider outage 503 and disabled accounts.
- Valid/invalid/expired JWT, refresh rotation/blacklisting, inactive-user refresh rejection, own-device logout and rejection of another user's refresh token.
- No privilege/phone writes via profile update; session-authenticated unsafe requests still require CSRF.
- Anonymous, user and scoped rate limits return 429; Retry-After tested.
- Cookie cart + JWT checkout/payment initiation/cancellation; owner isolation for order/address reads and mutations, foreign address rejection and service-boundary authorization.
- Paid-order cancellation rejection, rechecking pending state after lock acquisition, and user-row serialization for simultaneous checkouts.
- Shared address normalization, default-address behavior, and CSRF-safe POST-only web default-address action.
- Compatibility aliases and canonical OpenAPI paths/JWT security scheme.

## Reproduce

Configure a disposable PostgreSQL database, install `requirements-dev.txt`, and use local development settings:

```bash
pre-commit run --all-files
ruff check .
DJANGO_DB_ENGINE=postgresql python manage.py test --noinput
DJANGO_DB_ENGINE=sqlite python manage.py test --noinput
DJANGO_DB_ENGINE=postgresql python manage.py test api.tests.ConcurrentCustomerCheckoutTests orders.tests.ConcurrentCheckoutTests payment.tests.ConcurrentCallbackTests --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate --fail-on-warn --file schema.yaml
pip check
```

## Limits / release work

These are local results, not a claim that remote CI, penetration testing, load testing or production deployment passed. The previously connected GitHub token did not permit check-runs/status reads; this phase does not introduce CI (planned for phase 3).

New API tests use mocked SMS/gateway adapters. No real SMS or new live payment was sent in this phase; phase-1 real sandbox results remain documented separately. See [API v1 contract](api-v1.md) for cookie-bound cart semantics, callback behavior for bearer-only clients, token lifetime/logout scope, best-effort rate limiting, current province coverage and cross-origin limitations.

Before deployment: rotate historical secrets; configure a strong JWT signing key, shared cache and trusted proxy handling; back up/migrate the database; schedule blacklist cleanup and reservation/payment reconciliation; validate real SMS/gateway/HTTPS settings. Refresh rotation does not provide atomic concurrent-refresh or all-device access-token revocation guarantees.
