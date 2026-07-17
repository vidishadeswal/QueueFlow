# QueueFlow

[![CI](https://github.com/vidishadeswal/QueueFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/vidishadeswal/QueueFlow/actions/workflows/ci.yml)

Intelligent workflow & reminder automation platform. A dentist, gym, salon, or clinic
creates a reminder; QueueFlow reliably delivers it — with retries, backoff, and a
dead letter queue when delivery keeps failing.

The reminder is just the first job type. The underlying pieces (scheduler, queue,
worker, retry/DLQ) are generic enough to run any kind of scheduled job later
(invoice emails, subscription renewals, onboarding tasks).

## Architecture

```
Business Owner
      |
      v
Create Reminder (FastAPI)
      |
      v
Postgres  (reminder stored with status=pending, send_at)
      |
      v
Scheduler (polls every 10s for due reminders, SELECT ... FOR UPDATE SKIP LOCKED)
      |
      v
Redis Queue (reminders:queue)
      |
      v
Worker (BRPOP, sends via Brevo email API)
      |
      v
   Success? -- yes --> status = sent
      |
      no
      v
   Retry count <= 3?
      |                     \
     yes                     no
      |                       |
status=pending           status=dead_letter
send_at = now + backoff  (dashboard shows a warning,
(1min / 5min / 15min)     staff can manually retry)
      |
      v
(scheduler picks it back up when send_at arrives)
```

Retries reuse the scheduler instead of a separate delayed-queue mechanism: a failed
job just goes back to `pending` with a future `send_at`.

### Why email instead of SMS

Twilio and similar SMS APIs don't have a real free tier for sending to arbitrary
phone numbers (trial accounts only send to pre-verified numbers). QueueFlow uses
[Brevo](https://www.brevo.com)'s free transactional email API instead — 300
emails/day, no paid account required, and it reaches any contact by email without
requiring them to install an app or opt into a bot first. The architecture doesn't
care what channel is used; swapping in a paid SMS provider later is a change
localized to `app/core/email.py` and `app/worker.py`.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React + TypeScript (Vite), React Router |
| Backend API | FastAPI, SQLAlchemy (async), Alembic |
| Database | PostgreSQL 16 |
| Queue | Redis 7 (list-based queue + worker heartbeat) |
| Auth | JWT (python-jose), bcrypt password hashing |
| Email delivery | Brevo transactional email API |
| Tests | pytest, pytest-asyncio, httpx |

## Services

Six containers, defined in [`docker-compose.yml`](docker-compose.yml):

- **postgres** — primary database
- **redis** — job queue + worker heartbeat
- **backend** — FastAPI REST API (port 8000)
- **scheduler** — polls Postgres for due reminders, pushes them to Redis
- **worker** — consumes the Redis queue, sends email, handles retry/backoff/DLQ
- **frontend** — React dashboard (Vite dev server, port 5173)

## Data model

- **Business** — a tenant account (signup/login)
- **Contact** — a business's customer/patient (email required — the delivery channel)
- **Appointment** — links a contact to a scheduled event
- **Reminder** — the job itself: `message`, `send_at`, `status`
  (`pending` → `queued` → `sent` / `failed` → `dead_letter`), `retry_count`, `last_error`

All data is scoped to the authenticated business — every query filters by
`business_id`, and cross-tenant access returns 404.

## Running it

1. Copy `.env.example` to `.env` and `frontend/.env.example` to `frontend/.env`,
   filling in a `JWT_SECRET_KEY` and your Brevo credentials
   (`BREVO_API_KEY`, `BREVO_SENDER_EMAIL` — must be a verified sender in Brevo).
2. `docker compose up -d --build`
3. Apply migrations: `docker compose exec backend alembic upgrade head`
4. Open the app: http://localhost:5173
5. API docs (Swagger): http://localhost:8000/docs

Host ports are remapped to avoid clashing with other local services:
Postgres → `5433`, Redis → `6380`. Everything talks to each other over the
internal Docker network on the standard ports.

## Running tests

```
docker compose exec backend pytest -v
```

Tests run against a separate `queueflow_test` database (create once with
`docker compose exec postgres psql -U queueflow -d queueflow -c "CREATE DATABASE queueflow_test OWNER queueflow;"`)
so they never touch dev data. Coverage: auth (signup/login/JWT), full CRUD +
cross-tenant isolation for contacts/appointments/reminders, and the worker's
retry → backoff → dead-letter state machine (mocked email client, no real
network calls).

## Load testing & horizontal scaling

`scripts/load_test.py` drives 1,000 reminders through the full pipeline
(API → Postgres → scheduler → Redis → worker) and measures end-to-end drain
throughput. Run it with `EMAIL_DRY_RUN=true` so it exercises every hop without
spending real Brevo quota:

```
docker compose exec backend python scripts/load_test.py --count 1000 --concurrency 50
```

To test with more workers, scale the `worker` service — no code changes
needed, since dispatch already uses `SELECT ... FOR UPDATE SKIP LOCKED` to let
multiple workers pull from the same queue safely:

```
docker compose up -d --scale worker=3
```

Results from a local run (1,000 reminders, `EMAIL_DRY_RUN=true`, Docker Desktop
on macOS):

| Workers | Drain time | End-to-end throughput | Send latency (p50 / p95 / p99) |
|---|---|---|---|
| 1 | 70.17s | 14.3 reminders/sec | 54ms / 81ms / 85ms |
| 3 | 21.27s | 47.0 reminders/sec | 51ms / 79ms / 83ms |

3x the workers produced a **3.3x** throughput gain — close to linear scaling,
with per-send latency essentially unchanged (each worker still processes one
job at a time; adding workers adds parallel lanes, not per-job speed). This is
the payoff of the `claimed_at`/visibility-timeout design: workers can be added
or removed at will with no coordination between them beyond the shared
Postgres row locks and the Redis queue.

## API surface

- `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`
- `GET|POST /contacts`, `GET|PATCH|DELETE /contacts/{id}`
- `GET|POST /appointments`, `GET|PATCH|DELETE /appointments/{id}`
- `GET|POST /reminders`, `GET|PATCH|DELETE /reminders/{id}`, `POST /reminders/{id}/retry`
- `GET /analytics/summary` — dashboard metrics (today's/upcoming reminders,
  delivery %, avg retry count, queue size, worker health)
- `GET /health`, `GET /queue/status`

### Pagination

`GET /contacts`, `GET /appointments`, and `GET /reminders` all accept `limit`
(default 50, max 200) and `offset` (default 0) query params, and return:

```json
{ "items": [...], "total": 123, "limit": 50, "offset": 0 }
```

### Idempotent reminder creation

`POST /reminders` accepts an optional `Idempotency-Key` header. Retrying the
same request with the same key (e.g. after a dropped connection) returns the
original reminder instead of creating a duplicate; a second request with a key
still being processed gets `409 Conflict`. Keys are scoped per business and
expire after 24h.
