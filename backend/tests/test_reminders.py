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
    assert len(list_response.json()) == 1


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
    assert len(pending.json()) == 1

    sent = await client.get("/reminders?status_filter=sent", headers=headers)
    assert len(sent.json()) == 0


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
    assert other_business_list.json() == []


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

    await client.patch(f"/reminders/{reminder_id}", json={"status": "dead_letter"}, headers=headers)

    retry_response = await client.post(f"/reminders/{reminder_id}/retry", headers=headers)
    assert retry_response.status_code == 200
    body = retry_response.json()
    assert body["status"] == "pending"
    assert body["retry_count"] == 0
