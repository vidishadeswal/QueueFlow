import uuid

from app.core.idempotency import claim_idempotency_key
from app.core.redis import redis_client
from app.models.reminder import Reminder, ReminderStatus
from tests.conftest import TestSession


async def register_business(client, email: str) -> str:
    await client.post(
        "/auth/signup",
        json={"name": "Test Biz", "email": email, "password": "hunter2222"},
    )
    response = await client.post("/auth/login", data={"username": email, "password": "hunter2222"})
    return response.json()["access_token"]


async def create_appointment(client, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    contact = await client.post(
        "/contacts",
        json={"name": "Jane Doe", "email": "jane@example.com"},
        headers=headers,
    )
    contact_id = contact.json()["id"]

    appointment = await client.post(
        "/appointments",
        json={"contact_id": contact_id, "title": "Checkup", "scheduled_at": "2030-01-01T10:00:00Z"},
        headers=headers,
    )
    return appointment.json()["id"]


async def test_create_and_list_reminder(client):
    token = await register_business(client, "reminders1@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    create_response = await client.post(
        "/reminders",
        json={
            "appointment_id": appointment_id,
            "message": "See you tomorrow",
            "send_at": "2030-01-01T09:00:00Z",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    reminder = create_response.json()
    assert reminder["status"] == "pending"

    list_response = await client.get("/reminders", headers=headers)
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


async def test_reminder_status_filter(client):
    token = await register_business(client, "reminders2@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers=headers,
    )

    pending = await client.get("/reminders?status_filter=pending", headers=headers)
    assert pending.json()["total"] == 1

    sent = await client.get("/reminders?status_filter=sent", headers=headers)
    assert sent.json()["total"] == 0


async def test_cross_tenant_isolation(client):
    token1 = await register_business(client, "isolation1@testbiz.com")
    token2 = await register_business(client, "isolation2@testbiz.com")

    appointment_id = await create_appointment(client, token1)
    reminder = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    reminder_id = reminder.json()["id"]

    other_business_access = await client.get(
        f"/reminders/{reminder_id}", headers={"Authorization": f"Bearer {token2}"}
    )
    assert other_business_access.status_code == 404

    other_business_list = await client.get("/reminders", headers={"Authorization": f"Bearer {token2}"})
    assert other_business_list.json()["items"] == []


async def test_retry_endpoint_rejects_non_dead_letter(client):
    token = await register_business(client, "retry1@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    reminder = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers=headers,
    )
    reminder_id = reminder.json()["id"]

    retry_response = await client.post(f"/reminders/{reminder_id}/retry", headers=headers)
    assert retry_response.status_code == 400


async def test_retry_endpoint_resets_dead_letter_reminder(client):
    token = await register_business(client, "retry2@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    reminder = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers=headers,
    )
    reminder_id = reminder.json()["id"]

    async with TestSession() as session:
        db_reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        db_reminder.status = ReminderStatus.dead_letter
        await session.commit()

    retry_response = await client.post(f"/reminders/{reminder_id}/retry", headers=headers)
    assert retry_response.status_code == 200
    body = retry_response.json()
    assert body["status"] == "pending"
    assert body["retry_count"] == 0


async def test_patch_cannot_set_status_directly(client):
    """PATCH only allows editing message/send_at -- status changes must go through
    the dedicated /retry endpoint, which enforces the dead_letter -> pending
    transition and resets retry_count/last_error alongside it."""
    token = await register_business(client, "patchstatus@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    reminder = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers=headers,
    )
    reminder_id = reminder.json()["id"]

    patch_response = await client.patch(
        f"/reminders/{reminder_id}", json={"status": "sent"}, headers=headers
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "pending"


async def test_reminders_pagination(client):
    token = await register_business(client, "pagination@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    for i in range(5):
        await client.post(
            "/reminders",
            json={
                "appointment_id": appointment_id,
                "message": f"test {i}",
                "send_at": f"2030-01-01T09:0{i}:00Z",
            },
            headers=headers,
        )

    page1 = await client.get("/reminders?limit=2&offset=0", headers=headers)
    assert page1.json()["total"] == 5
    assert len(page1.json()["items"]) == 2

    page2 = await client.get("/reminders?limit=2&offset=2", headers=headers)
    assert len(page2.json()["items"]) == 2

    page3 = await client.get("/reminders?limit=2&offset=4", headers=headers)
    assert len(page3.json()["items"]) == 1

    all_ids = [r["id"] for r in page1.json()["items"] + page2.json()["items"] + page3.json()["items"]]
    assert len(set(all_ids)) == 5


async def test_idempotent_reminder_creation_returns_same_reminder(client):
    token = await register_business(client, "idempotent1@testbiz.com")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "retry-of-same-request"}
    appointment_id = await create_appointment(client, token)
    payload = {"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"}

    first = await client.post("/reminders", json=payload, headers=headers)
    assert first.status_code == 201

    second = await client.post("/reminders", json=payload, headers=headers)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    list_response = await client.get("/reminders", headers={"Authorization": f"Bearer {token}"})
    assert list_response.json()["total"] == 1


async def test_idempotency_key_rejects_concurrent_duplicate(client):
    token = await register_business(client, "idempotent2@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    me = await client.get("/auth/me", headers=headers)
    business_id = me.json()["id"]

    # Simulate another request with the same key still being processed.
    await claim_idempotency_key(redis_client, business_id, "in-flight-key")

    response = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers={**headers, "Idempotency-Key": "in-flight-key"},
    )
    assert response.status_code == 409


async def test_idempotency_key_released_on_failed_creation(client):
    """A failed create (bad appointment_id) shouldn't permanently burn the
    Idempotency-Key -- retrying with a valid payload under the same key must
    still succeed rather than getting stuck behind the failed attempt."""
    token = await register_business(client, "idempotent3@testbiz.com")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "retry-after-failure"}
    appointment_id = await create_appointment(client, token)

    failed = await client.post(
        "/reminders",
        json={"appointment_id": str(uuid.uuid4()), "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers=headers,
    )
    assert failed.status_code == 404

    retried = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers=headers,
    )
    assert retried.status_code == 201
