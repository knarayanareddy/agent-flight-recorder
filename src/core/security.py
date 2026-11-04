"""Security, token parsing, and metadata redaction utilities."""
from typing import Dict, Any, Optional, Set
from pydantic import BaseModel, field_validator

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
    org_role: str = "member"  # "member" or "admin"
    project_roles: Dict[str, Set[str]] = {}  # project_id -> Set[role]

    @field_validator("project_roles", mode="before")
    @classmethod
    def normalize_project_roles(cls, v):
        if not isinstance(v, dict):
            return {}
        normalized = {}
        for proj_id, roles in v.items():
            if isinstance(roles, str):
                normalized[str(proj_id)] = {roles}
            elif isinstance(roles, (list, tuple, set)):
                normalized[str(proj_id)] = {str(r) for r in roles}
            else:
                normalized[str(proj_id)] = set()
        return normalized

    def has_project_capability(self, project_id: str, required_capability: str) -> bool:
        """Check if user holds the required capability for the specified project.
        Supports union of multiple granted roles (e.g., analyst + operator).
        Capability hierarchy:
          - viewer: granted by viewer, analyst, operator, maintainer
          - analyst: granted by analyst, maintainer
          - operator: granted by operator, maintainer
          - maintainer: granted by maintainer
        """
        roles = self.project_roles.get(str(project_id), set())
        CAPABILITY_EXPANSION = {
            "viewer": {"viewer"},
            "analyst": {"viewer", "analyst"},
            "operator": {"viewer", "operator"},
            "maintainer": {"viewer", "analyst", "operator", "maintainer"}
        }
        user_caps: Set[str] = set()
        for r in roles:
            user_caps.update(CAPABILITY_EXPANSION.get(r, {r}))
        return required_capability in user_caps


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


def verify_token(token: str) -> Optional[UserContext]:
    """Verify bearer token against cryptographic signature / OIDC claims.
    Fail-closed: Returns None in production runtime until B03 identity
    integration is configured. Never accepts static test bypass credentials.
    Synthetic identities are injected exclusively via test dependency overrides.
    """
    return None
