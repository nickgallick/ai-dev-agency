"""Pytest fixtures for MCP tests."""

import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, patch, MagicMock

# Set test environment
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["ENCRYPTION_KEY"] = "0" * 64  # 32-byte key in hex
os.environ["DEBUG"] = "true"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    with patch("backend.config.settings.get_settings") as mock:
        settings = MagicMock()
        settings.database_url = "postgresql://test:test@localhost:5432/test_db"
        settings.redis_url = "redis://localhost:6379/1"
        settings.encryption_key = "0" * 64
        settings.github_token = "test_github_token"
        settings.slack_webhook_url = "https://hooks.slack.com/test"
        settings.notion_token = "test_notion_token"
        settings.mcp_browser_url = "http://localhost:3000"
        settings.debug = True
        mock.return_value = settings
        yield settings


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True)
    return str(project_dir)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for network tests."""
    with patch("httpx.AsyncClient") as mock:
        client = AsyncMock()
        mock.return_value.__aenter__.return_value = client
        mock.return_value = client
        yield client


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("redis.asyncio.from_url") as mock:
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.setex = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=1)
        client.sadd = AsyncMock(return_value=1)
        client.srem = AsyncMock(return_value=1)
        client.smembers = AsyncMock(return_value=set())
        client.close = AsyncMock()
        
        async def scan_iter_mock(*args, **kwargs):
            return iter([])
        client.scan_iter = scan_iter_mock
        
        mock.return_value = client
        yield client


@pytest.fixture
def mock_asyncpg_pool():
    """Mock asyncpg connection pool."""
    with patch("asyncpg.create_pool") as mock:
        pool = AsyncMock()
        
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=1)
        conn.fetch = AsyncMock(return_value=[])
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.close = AsyncMock()
        
        mock.return_value = pool
        yield pool, conn
