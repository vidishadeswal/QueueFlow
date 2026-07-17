"""Load test the reminder pipeline: creation -> scheduler -> queue -> worker -> terminal state.

Run with EMAIL_DRY_RUN=true on the worker so this doesn't burn real Brevo quota or spam
real inboxes -- it still exercises every hop of the real pipeline (Postgres, Redis,
scheduler polling, worker processing), just with a simulated ~20-80ms email call.

Usage (from the backend container):
    python scripts/load_test.py --count 1000 --concurrency 50
"""

import argparse
import asyncio
import time
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://backend:8000"
LOAD_TEST_EMAIL = "loadtest@queueflow-loadtest.com"
LOAD_TEST_PASSWORD = "loadtest12345"


async def ensure_business(client: httpx.AsyncClient) -> str:
    await client.post(
        "/auth/signup",
        json={"name": "Load Test Co", "email": LOAD_TEST_EMAIL, "password": LOAD_TEST_PASSWORD},
    )
    response = await client.post(
        "/auth/login",
        data={"username": LOAD_TEST_EMAIL, "password": LOAD_TEST_PASSWORD},
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def ensure_appointment(client: httpx.AsyncClient, headers: dict) -> str:
    contact = await client.post(
        "/contacts",
        json={"name": "Load Test Contact", "email": "loadtest-contact@queueflow-loadtest.com"},
        headers=headers,
    )
    contact.raise_for_status()
    contact_id = contact.json()["id"]

    appointment = await client.post(
        "/appointments",
        json={"contact_id": contact_id, "title": "Load Test Appointment", "scheduled_at": "2030-01-01T10:00:00Z"},
        headers=headers,
    )
    appointment.raise_for_status()
    return appointment.json()["id"]


async def create_reminder(client: httpx.AsyncClient, headers: dict, appointment_id: str, sem: asyncio.Semaphore, index: int) -> float:
    async with sem:
        start = time.perf_counter()
        response = await client.post(
            "/reminders",
            json={
                "appointment_id": appointment_id,
                "message": f"Load test reminder #{index}",
                "send_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            },
            headers=headers,
        )
        response.raise_for_status()
        return time.perf_counter() - start


async def count_terminal(client: httpx.AsyncClient, headers: dict) -> dict[str, int]:
    counts = {}
    for status_filter in ("sent", "failed", "dead_letter", "pending", "queued"):
        response = await client.get(f"/reminders?status_filter={status_filter}", headers=headers)
        response.raise_for_status()
        counts[status_filter] = len(response.json())
    return counts


async def main() -> None:
    parser = argparse.ArgumentParser(description="Load test the QueueFlow reminder pipeline")
    parser.add_argument("--count", type=int, default=1000, help="number of reminders to push through")
    parser.add_argument("--concurrency", type=int, default=50, help="concurrent API requests during creation")
    parser.add_argument("--drain-timeout", type=int, default=180, help="max seconds to wait for the queue to drain")
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        print("Setting up load test business and appointment...")
        token = await ensure_business(client)
        headers = {"Authorization": f"Bearer {token}"}
        appointment_id = await ensure_appointment(client, headers)

        print(f"Creating {args.count} reminders (concurrency={args.concurrency})...")
        sem = asyncio.Semaphore(args.concurrency)
        create_start = time.perf_counter()
        durations = await asyncio.gather(
            *[create_reminder(client, headers, appointment_id, sem, i) for i in range(args.count)]
        )
        create_elapsed = time.perf_counter() - create_start
        durations_sorted = sorted(durations)

        print()
        print("=== Creation phase ===")
        print(f"  Created {args.count} reminders in {create_elapsed:.2f}s")
        print(f"  Throughput: {args.count / create_elapsed:.1f} reminders/sec")
        print(f"  Per-request p50: {durations_sorted[len(durations_sorted) // 2] * 1000:.0f}ms")
        print(f"  Per-request p99: {durations_sorted[int(len(durations_sorted) * 0.99)] * 1000:.0f}ms")

        print()
        print("Waiting for the pipeline to drain (scheduler -> queue -> worker)...")
        drain_start = time.perf_counter()
        while time.perf_counter() - drain_start < args.drain_timeout:
            counts = await count_terminal(client, headers)
            in_flight = counts["pending"] + counts["queued"]
            terminal = counts["sent"] + counts["failed"] + counts["dead_letter"]
            print(
                f"  [{time.perf_counter() - drain_start:5.1f}s] "
                f"sent={counts['sent']} failed={counts['failed']} dead_letter={counts['dead_letter']} "
                f"pending={counts['pending']} queued={counts['queued']}"
            )
            if in_flight == 0 and terminal >= args.count:
                break
            await asyncio.sleep(3)
        drain_elapsed = time.perf_counter() - drain_start

        metrics_response = await client.get("/metrics")
        metrics_text = metrics_response.text

        print()
        print("=== Drain phase ===")
        print(f"  Fully drained in {drain_elapsed:.2f}s")
        print(f"  End-to-end throughput: {args.count / drain_elapsed:.1f} reminders/sec")
        print()
        print("=== Send latency (from /metrics, Brevo/dry-run call only) ===")
        for line in metrics_text.splitlines():
            if "send_latency_ms" in line and not line.startswith("#"):
                print(f"  {line}")


if __name__ == "__main__":
    asyncio.run(main())
