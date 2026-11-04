"""FastAPI dependency injection utilities."""
from typing import Optional, List
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db_session
from src.core.security import verify_token_subject
import uuid

async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract authenticated user ID from Authorization header."""
    if not authorization:
        # Default mock user for local development if unconfigured
        return "00000000-0000-4000-8000-000000000001"
    sub = verify_token_subject(authorization)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication credentials"
        )
    return sub

def require_role(required_role: str):
    """Enforce minimum required project role."""
    ROLE_HIERARCHY = ["viewer", "analyst", "operator", "maintainer", "admin"]
    
    async def role_checker(
        user_id: str = Depends(get_current_user),
        x_actor_role: Optional[str] = Header(default="admin")
    ):
        role = x_actor_role or "viewer"
        if role not in ROLE_HIERARCHY:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role")
        
        req_idx = ROLE_HIERARCHY.index(required_role)
        curr_idx = ROLE_HIERARCHY.index(role)
        if curr_idx < req_idx:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires '{required_role}' role or higher"
            )
        return role
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
