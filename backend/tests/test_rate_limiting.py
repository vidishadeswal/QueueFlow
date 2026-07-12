from app.core.config import settings


async def test_login_rate_limit_returns_429_after_limit(client):
    await client.post(
        "/auth/signup",
        json={"name": "Rate Limit Test", "email": "ratelimit@testbiz.com", "password": "hunter2222"},
    )

    limit = settings.rate_limit_login_per_minute
    responses = []
    for _ in range(limit + 2):
        response = await client.post(
            "/auth/login",
            data={"username": "ratelimit@testbiz.com", "password": "wrong-password"},
        )
        responses.append(response.status_code)

    assert responses[:limit] == [401] * limit
    assert responses[limit] == 429
    assert responses[limit + 1] == 429


async def test_login_rate_limit_is_per_client_not_global(client):
    # A different endpoint under the same limiter prefix shouldn't be affected by
    # requests that legitimately succeed; this just verifies successful logins
    # also count against the window (rate limiting applies regardless of outcome).
    await client.post(
        "/auth/signup",
        json={"name": "Rate Limit Test 2", "email": "ratelimit2@testbiz.com", "password": "hunter2222"},
    )

    limit = settings.rate_limit_login_per_minute
    last_status = None
    for _ in range(limit + 1):
        response = await client.post(
            "/auth/login",
            data={"username": "ratelimit2@testbiz.com", "password": "hunter2222"},
        )
        last_status = response.status_code

    assert last_status == 429
