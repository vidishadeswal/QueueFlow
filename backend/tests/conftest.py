import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.redis import redis_client
from app.main import app
from app import models  # noqa: F401  (registers all models on Base.metadata)

TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/queueflow_test"

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    async def create():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()

    asyncio.run(create())
    yield
    asyncio.run(drop())


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def clean_redis_test_keys():
    yield
    for prefix in ("ratelimit:*", "revoked_token:*", "idempotency:*"):
        keys = [key async for key in redis_client.scan_iter(match=prefix)]
        if keys:
            await redis_client.delete(*keys)

    # redis-py's connection pool binds connections to the event loop they were
    # created in. pytest-asyncio gives each test function a fresh loop, so without
    # this the *next* test reuses a connection tied to a now-closed loop and dies
    # with "RuntimeError: Event loop is closed".
    await redis_client.connection_pool.disconnect()
