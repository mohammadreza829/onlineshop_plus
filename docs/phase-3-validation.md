# Phase 3 validation

Validated locally on 2026-10-14. Phase 2 was first merged to main as `2385a44c98cdc77a5a46dd9ce4f5f11351c2f091`; infrastructure is a separate branch/PR, not a production deployment.

## Evidence

- PostgreSQL + real shared Redis: **134 tests passed, no skips**.
- SQLite + LocMem fallback: **129 passed, 5 skipped** (three PostgreSQL row-lock cases and two real-Redis concurrency cases).
- The complete **134-test suite also passed inside the Docker web image** using the Compose PostgreSQL and Redis services, with an isolated test cache DB.
- Docker image built successfully; Compose configuration validated; db/redis/migrate/web/worker/beat started, migrate exited 0 and web became healthy.
- HTTP liveness/readiness returned 200; readiness reported database/cache/worker up. Responses had request IDs.
- `check_infrastructure --with-worker` succeeded through the real broker/worker, not eager execution.
- An encrypted OTP task traversed the broker and was processed by a real worker using the **console-only test backend**; its challenge was then verified once. No real SMS was sent.
- A real queued expiration task changed an overdue order to EXPIRED and restored available stock.
- A beat-generated heartbeat was present, proving scheduler→broker→worker processing.
- Web container UID was 10001 (non-root).
- Ruff, all configured pre-commit hooks, dependency check, migration check and OpenAPI validation passed.
- Strict `check --deploy --fail-level WARNING` passed using generated check-only secret and explicit secure settings; this is configuration validation, not certification of a live HTTPS deployment.

## Environment detail

Docker Engine 25.0.16, Compose 2.39.4, PostgreSQL 16, Redis 7 in Compose; host Redis 6.2 was also used in tests. The sandbox daemon has no default bridge, so ordinary Compose build failed with `network bridge not found`. The application image was instead built with `docker build --network host`, then the **unmodified Compose runtime stack** was started with `up --no-build --wait`. No application network setting was changed to hide that build-environment limitation.

## Added coverage

Health dependency failure/503, worker heartbeat requirement, real probe keys, JSON redaction/correlation, encrypted/tampered/expired/superseded OTP tasks, broker failure, repeat delivery suppression, terminal failure preserving newer challenges, synchronous fallback, Redis-locked simultaneous sends/verifications, cache outage, scheduled expiration/reconciliation/blacklist cleanup, and rejecting eager execution as proof of a real worker.

An older OTP expiry unit test was made cache-backend independent by expiring the key through `cache.touch(..., timeout=0)`: Redis uses its own clock, so patching Python time is not a valid Redis expiry test.

## Limits

- A CI workflow is included; hosted GitHub Actions outcome must be checked separately. Local/container success is not a remote CI result.
- No real SMS/provider delivery, production payment, public TLS setup, backup restore drill, penetration/load test or production release was performed.
- Optional Sentry is not connected; no external monitoring credentials or destinations were invented. Customer status notifications remain phase 4.
- Celery/SMS delivery is at-least-once; a crash around provider delivery can duplicate an SMS. Money/stock state remains in PostgreSQL and is protected by idempotent services.
- Redis/cache/broker must be secured and capacity-planned. Shared cache, queue persistence and health probes do not by themselves provide high availability.

See [infrastructure runbook](infrastructure.md) for reproduction and deployment obligations. Do not run the old cron schedules alongside beat, and do not interpret these checks as a zero-bug guarantee.
