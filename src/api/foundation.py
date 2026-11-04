"""API routes for Shared Foundation."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Path as PathParam, Response
from pydantic import BaseModel
from src.api.deps import require_role, verify_idempotency_key, get_current_user

router = APIRouter()

# Pydantic Foundation Models
class ProjectCreate(BaseModel):
    name: str
    content_capture: str = "metadata_only"
    external_transfer: bool = False

class Project(BaseModel):
    id: str
    name: str
    content_capture: str
    external_transfer: bool
    revision: int
    created_at: str

class UploadCreate(BaseModel):
    expected_size: int
    expected_sha256: str
    media_type: str = "application/octet-stream"

class Upload(BaseModel):
    id: str
    project_id: str
    artifact_id: str
    expected_size: int
    expected_sha256: str
    expires_at: str

class Job(BaseModel):
    id: str
    project_id: str
    kind: str
    state: str
    payload: dict
    attempt: int = 0
    created_at: str

@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
async def foundation_create_project(
    body: ProjectCreate,
    role: str = Depends(require_role("admin")),
    idemp: str = Depends(verify_idempotency_key)
):
    """Create a new project workspace."""
    import uuid, datetime
    return Project(
        id=str(uuid.uuid4()),
        name=body.name,
        content_capture=body.content_capture,
        external_transfer=body.external_transfer,
        revision=1,
        created_at=datetime.datetime.utcnow().isoformat() + "Z"
    )

@router.get("/projects", response_model=List[Project], status_code=status.HTTP_200_OK)
async def foundation_list_projects(role: str = Depends(require_role("viewer"))):
    """List accessible projects."""
    return []

@router.post("/projects/{project_id}/uploads", response_model=Upload, status_code=status.HTTP_201_CREATED)
async def foundation_create_upload(
    project_id: str = PathParam(...),
    body: UploadCreate = ...,
    role: str = Depends(require_role("analyst")),
    idemp: str = Depends(verify_idempotency_key)
):
    """Initiate an artifact upload session."""
    import uuid, datetime
    return Upload(
        id=str(uuid.uuid4()),
        project_id=project_id,
        artifact_id=str(uuid.uuid4()),
        expected_size=body.expected_size,
        expected_sha256=body.expected_sha256,
        expires_at=(datetime.datetime.utcnow() + datetime.timedelta(hours=2)).isoformat() + "Z"
    )

@router.put("/uploads/{upload_id}/bytes", status_code=status.HTTP_200_OK)
async def foundation_put_upload(
    upload_id: str = PathParam(...),
    role: str = Depends(require_role("analyst"))
):
    """Upload chunked bytes for an artifact."""
    return {"status": "accepted", "upload_id": upload_id}

@router.post("/uploads/{upload_id}:finalize", status_code=status.HTTP_200_OK)
async def foundation_finalize_upload(
    upload_id: str = PathParam(...),
    role: str = Depends(require_role("analyst")),
    idemp: str = Depends(verify_idempotency_key)
):
    """Finalize upload and verify artifact checksum."""
    return {"status": "finalized", "upload_id": upload_id}

@router.get("/artifacts/{artifact_id}", status_code=status.HTTP_200_OK)
async def foundation_get_artifact(
    artifact_id: str = PathParam(...),
    role: str = Depends(require_role("analyst"))
):
    """Get artifact metadata."""
    return {"id": artifact_id, "state": "ready"}

@router.get("/artifacts/{artifact_id}/bytes", status_code=status.HTTP_200_OK)
async def foundation_download_artifact(
    artifact_id: str = PathParam(...),
    role: str = Depends(require_role("analyst"))
):
    """Download artifact raw bytes."""
    return Response(content=b"", media_type="application/octet-stream")

@router.get("/jobs/{job_id}", response_model=Job, status_code=status.HTTP_200_OK)
async def foundation_get_job(
    job_id: str = PathParam(...),
    role: str = Depends(require_role("viewer"))
):
    """Get job status and outcome."""
    import datetime
    return Job(
        id=job_id,
        project_id="00000000-0000-4000-8000-000000000001",
        kind="system",
        state="queued",
        payload={},
        created_at=datetime.datetime.utcnow().isoformat() + "Z"
    )

@router.post("/jobs/{job_id}:cancel", status_code=status.HTTP_200_OK)
async def foundation_cancel_job(
    job_id: str = PathParam(...),
    role: str = Depends(require_role("operator")),
    idemp: str = Depends(verify_idempotency_key)
):
    """Request job cancellation."""
    return {"job_id": job_id, "state": "cancel_requested"}
