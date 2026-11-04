"""Security, token parsing, and metadata redaction utilities."""
import re
from typing import Dict, Any, Optional

FORBIDDEN_METADATA_KEYS = {
    'api_key', 'authorization', 'access_token', 'refresh_token',
    'password', 'client_secret', 'cookie', 'secret'
}

ALLOWED_METADATA_KEYS = {
    'operation_id', 'name', 'outcome', 'input_tokens', 'output_tokens',
    'redacted', 'reason'
}

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
            # Reason text can contain freeform secrets; omit in strict mode
            continue
        if isinstance(v, (dict, list)):
            raise ValueError("Nested metadata structures are forbidden")
        sanitized[k] = v
    return sanitized

def verify_token_subject(token: str) -> Optional[str]:
    """Verify bearer token and return user ID subject (stub for OIDC / JWT)."""
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    # In dev/testing, support test tokens or synthetic user UUIDs
    return "00000000-0000-4000-8000-000000000001"
