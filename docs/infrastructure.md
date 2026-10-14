# Phase 3 infrastructure

## Local Compose stack

Docker Engine and Compose v2 are required. Copy `.env.example` to `.env`, generate a strong `DJANGO_SECRET_KEY` and database password, then run:

```bash
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec web python manage.py check_infrastructure --with-worker
docker compose ps
```

The example defaults to development/console-SMS and sandbox payments. It is NOT a production secrets file. Web binds only to `127.0.0.1:8000` (override `WEB_PORT`); PostgreSQL/Redis are not published to the host. Services:

- `db`: PostgreSQL 16 with persistent volume.
- `redis`: Redis 7, AOF enabled, no-eviction policy, private Compose network.
- `migrate`: one-shot schema migration before application services start. It must exit successfully.
- `web`: non-root Gunicorn, WhiteNoise static assets baked into the image; media volume is writable.
- `worker`: Celery worker, concurrency 2, JSON-only messages, late acknowledgements, bounded task time.
- `beat`: **one scheduler only**, dispatches periodic work. Do not scale beat replicas.

Application containers are non-root, read-only except `/tmp` and web media, with no-new-privileges. `.dockerignore` excludes real env files, local databases, media and git history. Build-time placeholder settings are not production credentials. App HTTP logs are JSON; Gunicorn access logging is not enabled, avoiding duplicate query-string logs.

`docker compose down` stops the QA stack but preserves volumes. `down -v` deletes database/media/Redis volumes: do NOT use it against valuable data.

## Native development

Use Redis and PostgreSQL, then configure:

```text
CACHE_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
SMS_ASYNC=True
```

```bash
python manage.py migrate
celery -A onlineshop worker --loglevel=INFO --concurrency=2
# Separate terminal; exactly one beat process:
celery -A onlineshop beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule
python manage.py check_infrastructure --with-worker
```

With DEBUG and no CACHE_URL, LocMem remains available for quick tests. Production refuses to start without a shared CACHE_URL. Sessions use cached_db: PostgreSQL remains the durable session store; Redis accelerates reads. JWT still does not turn the cookie cart into a cross-device cart.

## Queue and scheduling semantics

- Unpaid reservations: scan every 60 seconds, release stock through the idempotent order service.
- Payments: dispatch every 300 seconds, up to 500 pending/unknown payments not updated for 15 minutes; oldest update first. Each payment is verified in its own task/DB lock. UNKNOWN retries cool down and move back in the queue, reducing starvation.
- Expired JWT blacklist tokens: cleanup every 24 hours.
- Worker heartbeat: beat sends every 30 seconds; worker writes a Redis marker with 120-second TTL.

These replace duplicate external cron schedules when beat is enabled. Existing management commands remain available for controlled recovery. Tasks are at-least-once, NOT exactly-once. Money and stock services are idempotent; do not remove their row locks. The queue is not a durable financial ledger: PostgreSQL records and periodic reconciliation are authoritative.

## Async SMS / OTP safety

`SMS_ASYNC=True` accepts a send request after publishing, not after provider delivery. The API's 202 does not guarantee that an SMS has arrived. Publishing failure returns an unavailable error and removes the challenge; worker provider/cache failures retry up to three times with backoff/jitter. A terminal failure clears only its own still-current challenge, never a newer one.

OTP payloads (phone/code) are encrypted with Fernet before entering the broker, using a domain-separated key derived from the Django secret. Codes remain HMAC-only in the cache. Tasks expire with the OTP TTL and skip expired, consumed or superseded challenges. A completed-payload marker suppresses ordinary repeated deliveries; a process crash between provider delivery and marking can still send a duplicate SMS. No exactly-once SMS guarantee is made.

Redis locks serialize send/verify per phone across processes, so a code cannot be consumed twice by simultaneous web requests. DEBUG-only LocMem falls back to a process lock, not a distributed guarantee. Codes and bearer values are redacted from application logs; console SMS is for automated/development diagnostics, not a reliable way to read plaintext login codes.

Rotating the Django secret invalidates pending encrypted OTP tasks and existing code hashes; plan rotation and let users request fresh codes. Web/worker must share matching secrets and cache prefix.

## Health and logs

- GET `/health/live/`: process liveness, no external dependency checks.
- GET `/health/ready/`: real database/cache round trips; with `HEALTHCHECK_REQUIRE_WORKER=True`, a recent beat→broker→worker heartbeat is also required. Returns 503 on failure without credentials/exception details.
- Health paths are exempt from HTTPS redirects for internal probes only. Restrict them at the public reverse proxy. Readiness is not proof that the SMS/payment provider is healthy or that every worker/queue is healthy.
- `check_infrastructure --with-worker` publishes a unique probe and waits for actual worker execution; it rejects eager mode as evidence of a real worker.
- App logs include UTC timestamp, level, logger and message; HTTP events include validated UUID request ID, method, path without query string, status and elapsed time. The response carries `X-Request-ID`.
- Phone numbers, OTP-shaped values, bearer/JWT values, configured secrets and Redis URL credentials are redacted. Redaction is defense in depth: never deliberately log request bodies or provider credentials. Docker log rotation is configured.

Sentry is optional and **not configured** in this phase. No monitoring account/DSN is invented and no error data is sent externally. Customer order-status notifications belong to phase 4; this phase provides the queue/SMS delivery infrastructure, not a new notification product.

## CI

`.github/workflows/ci.yml` defines pre-commit/pip checks, PostgreSQL + real Redis tests, SQLite compatibility, migration/schema/static checks, strict production settings check with ephemeral check-only credentials, a real worker probe, Compose config and image build. Workflow permissions are read-only for repository contents. This definition is not evidence of a successful hosted GitHub Actions run; check the actual run before merging/releasing.

## Production checklist (not automatic deployment)

1. Rotate secrets committed in old history; generate separate strong runtime Django/JWT secrets. Never deploy `.env.example` credentials.
2. Use real PostgreSQL backups and test restores. The Compose database bootstrap user is suitable for local QA; production should use appropriate least-privilege roles.
3. Use private/authenticated Redis; use TLS (`rediss://`) where needed. Separate broker/cache Redis instances for stronger resource/failure isolation. DB numbers alone do not provide security or resource isolation. Size memory and persistence deliberately.
4. Set DEBUG=False, real allowed hosts/CSRF origins, SMS backend/credentials/template, real merchant and ZARINPAL_SANDBOX=False. Configure a trusted TLS reverse proxy and serve uploaded media separately; WhiteNoise handles static, not production media.
5. HSTS preload is opt-in (`DJANGO_HSTS_PRELOAD=True`) only after all relevant hosts are HTTPS-ready. Configure forwarded-proto trust only at a controlled proxy.
6. Back up/migrate once, collect static as part of image build, start worker and one beat, verify readiness and real queue probe.
7. Validate real SMS and payment behavior, backup/restore, load, alerting and security separately. Do not infer these from a green unit suite.
8. Deploy immutable reviewed image tags/digests; health checks do not implement rollback. Avoid blindly rolling back schema changes without a tested plan.
