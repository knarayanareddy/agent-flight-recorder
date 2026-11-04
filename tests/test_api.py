"""API Route Integration Tests (Fail-Closed & Authorization Enforcement)."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.core.security import verify_token

TEST_PROJ = "00000000-0000-4000-8000-000000000001"
OTHER_PROJ = "00000000-0000-4000-8000-000000000999"

AUTH_ADMIN = {"Authorization": "Bearer test-token-admin"}
AUTH_MAINTAINER = {"Authorization": "Bearer test-token-maintainer"}
AUTH_OPERATOR = {"Authorization": "Bearer test-token-operator"}
AUTH_ANALYST = {"Authorization": "Bearer test-token-analyst"}
AUTH_VIEWER = {"Authorization": "Bearer test-token-viewer"}
AUTH_MULTI = {"Authorization": "Bearer test-token-analyst-operator"}
AUTH_INVALID = {"Authorization": "Bearer invalid-token"}
IDEMP_HEADER = {"Idempotency-Key": "00000000-0000-4000-8000-000000000001"}


def test_production_verifier_rejects_test_tokens():
    """Verify runtime verifier fails closed and never accepts synthetic test tokens."""
    assert verify_token("Bearer test-token-admin") is None
    assert verify_token("Bearer test-token-maintainer") is None
    assert verify_token("Bearer test-token-operator") is None
    assert verify_token("Bearer test-token-analyst") is None
    assert verify_token("Bearer test-token-viewer") is None
    assert verify_token("Bearer nonsense") is None


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
        assert res.status_code == 501

# --- Project-Path Route Denial & Capability Tests ---


@pytest.mark.asyncio
async def test_project_route_unauthenticated_denied():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/projects/{TEST_PROJ}/afr/runs")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_project_route_insufficient_capability_denied():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # afr/cases requires analyst capability; viewer must be rejected with 403
        headers = {**AUTH_VIEWER, **IDEMP_HEADER}
        res = await ac.post(
            f"/api/v1/projects/{TEST_PROJ}/afr/cases",
            json={"run_id": "00000000-0000-4000-8000-000000000002", "run_revision": 1, "name": "c", "checks": []},
            headers=headers
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_project_route_unauthorized_project_denied():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User has role on TEST_PROJ, but not OTHER_PROJ
        res = await ac.get(f"/api/v1/projects/{OTHER_PROJ}/afr/runs", headers=AUTH_VIEWER)
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_project_route_authorized_capability_passes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/projects/{TEST_PROJ}/afr/runs", headers=AUTH_VIEWER)
        assert res.status_code == 200

# --- Object-ID Route Denial & Capability Tests ---


@pytest.mark.asyncio
async def test_object_route_unauthenticated_denied():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/artifacts/00000000-0000-4000-8000-000000000009")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_object_route_absent_scope_denied():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Calling object endpoint without X-Project-Id header must fail closed with 403
        res = await ac.get("/api/v1/artifacts/00000000-0000-4000-8000-000000000009", headers=AUTH_ANALYST)
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_object_route_unauthorized_scope_denied():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {**AUTH_ANALYST, "X-Project-Id": OTHER_PROJ}
        res = await ac.get("/api/v1/artifacts/00000000-0000-4000-8000-000000000009", headers=headers)
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_object_route_insufficient_capability_denied():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Artifacts require analyst; viewer must be rejected with 403 even with project header
        headers = {**AUTH_VIEWER, "X-Project-Id": TEST_PROJ}
        res = await ac.get("/api/v1/artifacts/00000000-0000-4000-8000-000000000009", headers=headers)
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_object_route_authorized_scope_passes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {**AUTH_ANALYST, "X-Project-Id": TEST_PROJ}
        res = await ac.get("/api/v1/artifacts/00000000-0000-4000-8000-000000000009", headers=headers)
        # Auth passed, returns 404 in baseline (artifact not found) rather than 401/403
        assert res.status_code == 404

# --- Multi-Capability Union Tests ---


@pytest.mark.asyncio
async def test_multi_capability_union_grant():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User with analyst + operator roles can access both analyst and operator routes
        headers_analyst = {**AUTH_MULTI, "X-Project-Id": TEST_PROJ}
        res_a = await ac.get("/api/v1/artifacts/00000000-0000-4000-8000-000000000009", headers=headers_analyst)
        assert res_a.status_code == 404  # Passes auth (analyst cap satisfied)

        headers_op = {**AUTH_MULTI, **IDEMP_HEADER, "X-Project-Id": TEST_PROJ}
        res_b = await ac.post("/api/v1/jobs/00000000-0000-4000-8000-000000000010:cancel", headers=headers_op)
        assert res_b.status_code == 501  # Passes auth (operator cap satisfied)
