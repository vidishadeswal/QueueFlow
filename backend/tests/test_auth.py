async def test_signup_creates_business(client):
    response = await client.post(
        "/auth/signup",
        json={"name": "Test Salon", "email": "owner@testsalon.com", "password": "hunter2222"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "owner@testsalon.com"
    assert "id" in body


async def test_signup_duplicate_email_rejected(client):
    payload = {"name": "Test Salon", "email": "dupe@testsalon.com", "password": "hunter2222"}
    await client.post("/auth/signup", json=payload)
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 400


async def test_login_success_and_me(client):
    await client.post(
        "/auth/signup",
        json={"name": "Test Salon", "email": "login@testsalon.com", "password": "hunter2222"},
    )
    response = await client.post(
        "/auth/login",
        data={"username": "login@testsalon.com", "password": "hunter2222"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "login@testsalon.com"


async def test_login_wrong_password_rejected(client):
    await client.post(
        "/auth/signup",
        json={"name": "Test Salon", "email": "wrongpw@testsalon.com", "password": "hunter2222"},
    )
    response = await client.post(
        "/auth/login",
        data={"username": "wrongpw@testsalon.com", "password": "not-the-password"},
    )
    assert response.status_code == 401


async def test_me_without_token_rejected(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401
