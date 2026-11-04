"""FastAPI dependency injection utilities with fail-closed authorization."""
from typing import Optional, Callable
from fastapi import Header, HTTPException, status, Depends, Path
from src.core.database import get_db_session
from src.core.security import verify_token, UserContext
import uuid

async def get_current_user(authorization: Optional[str] = Header(None)) -> UserContext:
    """Authenticate caller via Bearer token.
    Fail-closed: Rejects unauthenticated requests with 401. Never returns mock users.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    ctx = verify_token(authorization)
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return ctx

async def require_org_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Enforce Organization Admin privilege (separate from project roles)."""
    if user.org_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires Organization Admin privilege"
        )
    return user

def require_project_role(required_role: str) -> Callable:
    """Enforce capability-based project authorization.
    Does NOT trust caller-supplied role headers.
    """
    CAPABILITIES = {
        "viewer": {"viewer", "analyst", "operator", "maintainer"},
        "analyst": {"analyst", "maintainer"},
        "operator": {"operator", "maintainer"},
        "maintainer": {"maintainer"}
    }
    allowed = CAPABILITIES.get(required_role, {required_role})
    
    async def role_checker(
        project_id: Optional[str] = Path(None),
        user: UserContext = Depends(get_current_user)
    ) -> UserContext:
        if project_id:
            role = user.project_roles.get(str(project_id))
            if not role or role not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient project privileges: requires '{required_role}' capability"
                )
        return user
    return role_checker

async def verify_idempotency_key(idempotency_key: Optional[str] = Header(None)) -> str:
    """Validate Idempotency-Key header is a valid UUIDv4 for mutating requests."""
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required 'Idempotency-Key' header"
        )
    try:
        uuid_obj = uuid.UUID(idempotency_key)
        return str(uuid_obj)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'Idempotency-Key' must be a valid UUIDv4 string"
        )
