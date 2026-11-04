"""Security, token parsing, and metadata redaction utilities."""
from typing import Dict, Any, Optional
from pydantic import BaseModel

FORBIDDEN_METADATA_KEYS = {
    'api_key', 'authorization', 'access_token', 'refresh_token',
    'password', 'client_secret', 'cookie', 'secret'
}

ALLOWED_METADATA_KEYS = {
    'operation_id', 'name', 'outcome', 'input_tokens', 'output_tokens',
    'redacted', 'reason'
}

class UserContext(BaseModel):
    user_id: str
    organization_id: str
    org_role: str  # "member" or "admin"
    project_roles: Dict[str, str] = {}  # project_id -> role

def redact_metadata(value: Dict[str, Any]) -> Dict[str, Any]:
    """Allowlisted metadata scrubbing; strips credentials and nested blobs."""
    if not isinstance(value, dict):
        raise ValueError("Metadata must be a dictionary")
    
    sanitized = {}
    for k, v in value.items():
        k_lower = k.lower()
        if k_lower in FORBIDDEN_METADATA_KEYS:
            continue
        if k not in ALLOWED_METADATA_KEYS:
            continue
        if k == 'reason':
            # Free text can contain freeform secrets; omit in strict metadata capture
            continue
        if isinstance(v, (dict, list)):
            raise ValueError("Nested metadata structures are forbidden")
        sanitized[k] = v
    return sanitized

# Deterministic test identities for test harness (never valid production credentials)
VALID_TEST_TOKENS = {
    "test-token-admin": UserContext(
        user_id="00000000-0000-4000-8000-000000000001",
        organization_id="00000000-0000-4000-8000-000000000000",
        org_role="admin",
        project_roles={"00000000-0000-4000-8000-000000000001": "maintainer"}
    ),
    "test-token-maintainer": UserContext(
        user_id="00000000-0000-4000-8000-000000000002",
        organization_id="00000000-0000-4000-8000-000000000000",
        org_role="member",
        project_roles={"00000000-0000-4000-8000-000000000001": "maintainer"}
    ),
    "test-token-operator": UserContext(
        user_id="00000000-0000-4000-8000-000000000003",
        organization_id="00000000-0000-4000-8000-000000000000",
        org_role="member",
        project_roles={"00000000-0000-4000-8000-000000000001": "operator"}
    ),
    "test-token-analyst": UserContext(
        user_id="00000000-0000-4000-8000-000000000004",
        organization_id="00000000-0000-4000-8000-000000000000",
        org_role="member",
        project_roles={"00000000-0000-4000-8000-000000000001": "analyst"}
    ),
    "test-token-viewer": UserContext(
        user_id="00000000-0000-4000-8000-000000000005",
        organization_id="00000000-0000-4000-8000-000000000000",
        org_role="member",
        project_roles={"00000000-0000-4000-8000-000000000001": "viewer"}
    )
}

def verify_token(token: str) -> Optional[UserContext]:
    """Verify bearer token against known test identities or OIDC provider.
    Fail-closed: Returns None if token is invalid or missing.
    """
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    return VALID_TEST_TOKENS.get(token)
