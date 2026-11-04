"""API Route Integration Tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.mark.asyncio
async def test_healthz_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "pass"
        assert "version" in data

@pytest.mark.asyncio
async def test_list_projects_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/projects")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

@pytest.mark.asyncio
async def test_mutating_endpoint_requires_idempotency_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Omitting Idempotency-Key header must return 400
        res = await ac.post("/api/v1/projects", json={"name": "Test Project"})
        assert res.status_code == 400
