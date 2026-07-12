async def register_and_login(client, email: str) -> str:
    await client.post(
        "/auth/signup",
        json={"name": "Revocation Test", "email": email, "password": "hunter2222"},
    )
    response = await client.post("/auth/login", data={"username": email, "password": "hunter2222"})
    return response.json()["access_token"]


async def test_logout_revokes_token(client):
    token = await register_and_login(client, "revoke1@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}

    before = await client.get("/auth/me", headers=headers)
    assert before.status_code == 200

    logout_response = await client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == 204

    after = await client.get("/auth/me", headers=headers)
    assert after.status_code == 401


async def test_logout_does_not_affect_other_tokens(client):
    token_a = await register_and_login(client, "revoke2a@testbiz.com")
    token_b = await register_and_login(client, "revoke2b@testbiz.com")

    await client.post("/auth/logout", headers={"Authorization": f"Bearer {token_a}"})

    still_valid = await client.get("/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert still_valid.status_code == 200


async def test_logout_without_token_is_a_no_op(client):
    response = await client.post("/auth/logout")
    assert response.status_code == 401
