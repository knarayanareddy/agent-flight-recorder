"""Test fixtures and synthetic authorization overrides.

Auth is layered so the production verifier stays fail-closed:

* ``get_current_user`` is overridden by the synthetic test-user map below
  (explicit test override, never used in production).
* ``verify_token`` (production entry point) delegates to an OIDC verifier only
  when ``configure_oidc_verifier`` is called in a test; by default it is None
  and every token is rejected. See tests/test_oidc_stub.py.
"""
import os
from typing import Optional
import pytest
from fastapi import Header, HTTPException, status
from src.main import app
from src.api.deps import get_current_user
from src.core.security import UserContext
from src.core.oidc import OidcStubProvider

os.environ['DEBUG'] = 'true'

TEST_PROJECT_ID = "00000000-0000-4000-8000-000000000001"
TEST_ORG_ID = "00000000-0000-4000-8000-000000000000"

SYNTHETIC_TEST_USERS = {
    "test-token-admin": UserContext(
        user_id="00000000-0000-4000-8000-000000000001",
        organization_id=TEST_ORG_ID,
        org_role="admin",
        project_roles={TEST_PROJECT_ID: {"maintainer"}}
    ),
    "test-token-maintainer": UserContext(
        user_id="00000000-0000-4000-8000-000000000002",
        organization_id=TEST_ORG_ID,
        org_role="member",
        project_roles={TEST_PROJECT_ID: {"maintainer"}}
    ),
    "test-token-operator": UserContext(
        user_id="00000000-0000-4000-8000-000000000003",
        organization_id=TEST_ORG_ID,
        org_role="member",
        project_roles={TEST_PROJECT_ID: {"operator"}}
    ),
    "test-token-analyst": UserContext(
        user_id="00000000-0000-4000-8000-000000000004",
        organization_id=TEST_ORG_ID,
        org_role="member",
        project_roles={TEST_PROJECT_ID: {"analyst"}}
    ),
    "test-token-viewer": UserContext(
        user_id="00000000-0000-4000-8000-000000000005",
        organization_id=TEST_ORG_ID,
        org_role="member",
        project_roles={TEST_PROJECT_ID: {"viewer"}}
    ),
    "test-token-analyst-operator": UserContext(
        user_id="00000000-0000-4000-8000-000000000006",
        organization_id=TEST_ORG_ID,
        org_role="member",
        project_roles={TEST_PROJECT_ID: {"analyst", "operator"}}
    )
}


async def override_get_current_user(authorization: Optional[str] = Header(None)) -> UserContext:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]
    user = SYNTHETIC_TEST_USERS.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


@pytest.fixture(autouse=True)
def setup_test_auth():
    """Inject synthetic identities into FastAPI dependency overrides during test runs."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def oidc_stub_provider():
    """Fresh local test OIDC IdP stub (not the production verifier)."""
    return OidcStubProvider()


@pytest.fixture
def oidc_verifier(oidc_stub_provider):
    """Configure the OIDC verifier for a single test, then restore fail-closed.

    Use only for tests that exercise OIDC-stub token verification through
    ``verify_token``. Guarantees the global verifier is reset to None afterward
    so the production fail-closed behavior is not leaked between tests.
    """
    from src.core.oidc import configure_oidc_verifier, _oidc_verifier

    previous = _oidc_verifier
    configure_oidc_verifier(oidc_stub_provider)
    try:
        yield oidc_stub_provider
    finally:
        configure_oidc_verifier(previous)
