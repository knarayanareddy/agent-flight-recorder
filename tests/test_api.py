"""API Route Integration Tests (Fail-Closed & Authorization Enforcement)."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

AUTH_ADMIN = {"Authorization": "Bearer test-token-admin"}
AUTH_VIEWER = {"Authorization": "Bearer test-token-viewer"}
AUTH_OPERATOR = {"Authorization": "Bearer test-token-operator"}
AUTH_INVALID = {"Authorization": "Bearer invalid-token"}
IDEMP_HEADER = {"Idempotency-Key": "00000000-0000-4000-8000-000000000001"}

@pytest.mark.asyncio
async def test_healthz_endpoint_is_public():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "pass"

@pytest.mark.asyncio
async def test_unauthenticated_request_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/projects")
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_invalid_bearer_token_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/projects", headers=AUTH_INVALID)
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_authenticated_list_projects_passes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/projects", headers=AUTH_VIEWER)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

@pytest.mark.asyncio
async def test_create_project_requires_idempotency_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/projects", json={"name": "Test"}, headers=AUTH_ADMIN)
        assert res.status_code == 400

@pytest.mark.asyncio
async def test_create_project_requires_org_admin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {**AUTH_VIEWER, **IDEMP_HEADER}
        res = await ac.post("/api/v1/projects", json={"name": "Test"}, headers=headers)
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_create_project_fails_closed_in_b00():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {**AUTH_ADMIN, **IDEMP_HEADER}
        res = await ac.post("/api/v1/projects", json={"name": "Test"}, headers=headers)
        # B00 baseline fails closed rather than fabricating project success
        assert res.status_code == 501
