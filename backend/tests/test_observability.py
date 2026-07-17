import logging
import uuid

from tests.test_reminders import create_appointment, register_business


async def test_response_gets_a_generated_request_id(client):
    response = await client.get("/health")
    assert "X-Request-ID" in response.headers
    # Should parse as a UUID -- proves it's a real generated id, not a placeholder.
    uuid.UUID(response.headers["X-Request-ID"])


async def test_inbound_request_id_is_echoed_back(client):
    response = await client.get("/health", headers={"X-Request-ID": "caller-supplied-trace-id"})
    assert response.headers["X-Request-ID"] == "caller-supplied-trace-id"


async def test_two_requests_get_different_request_ids(client):
    first = await client.get("/health")
    second = await client.get("/health")
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


async def test_reminder_creation_logs_carry_request_id_and_reminder_id(client, caplog):
    token = await register_business(client, "observability1@testbiz.com")
    headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "trace-abc-123"}
    appointment_id = await create_appointment(client, token)

    with caplog.at_level(logging.INFO, logger="api.reminders"):
        response = await client.post(
            "/reminders",
            json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
            headers=headers,
        )
    reminder_id = response.json()["id"]

    matching = [r for r in caplog.records if r.name == "api.reminders" and getattr(r, "reminder_id", None) == reminder_id]
    assert matching, "expected a log record tagged with the created reminder_id"
    assert all(getattr(r, "request_id", None) == "trace-abc-123" for r in matching)


async def test_idempotent_replay_is_logged_distinctly(client, caplog):
    token = await register_business(client, "observability2@testbiz.com")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "obs-replay-key"}
    appointment_id = await create_appointment(client, token)
    payload = {"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"}

    await client.post("/reminders", json=payload, headers=headers)

    with caplog.at_level(logging.INFO, logger="api.reminders"):
        await client.post("/reminders", json=payload, headers=headers)

    replay_logs = [r for r in caplog.records if r.message == "reminder_creation_idempotent_replay"]
    assert replay_logs
    assert getattr(replay_logs[0], "idempotency_key", None) == "obs-replay-key"
