"""API routes for Shared Foundation."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Path as PathParam, Response, HTTPException
from pydantic import BaseModel
from src.api.deps import require_org_admin, require_project_role, verify_idempotency_key
from src.core.security import UserContext

router = APIRouter()

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
    user: UserContext = Depends(require_org_admin),
    idemp: str = Depends(verify_idempotency_key)
):
    """Create a new project workspace.
    Fail-closed: In B00 contract baseline, database persistence is not active.
    Raises 501 until B02 database migrations are connected.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Project creation persistence is not implemented in B00 baseline. Awaiting B02 migration integration."
    )

@router.get("/projects", response_model=List[Project], status_code=status.HTTP_200_OK)
async def foundation_list_projects(user: UserContext = Depends(require_project_role("viewer"))):
    """List accessible projects for authenticated user."""
    return []

@router.post("/projects/{project_id}/uploads", response_model=Upload, status_code=status.HTTP_201_CREATED)
async def foundation_create_upload(
    project_id: str = PathParam(...),
    body: UploadCreate = ...,
    user: UserContext = Depends(require_project_role("analyst")),
    idemp: str = Depends(verify_idempotency_key)
):
    """Initiate an artifact upload session."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Artifact storage is not configured in B00 baseline. Awaiting B04 artifact integration."
    )

@router.put("/uploads/{upload_id}/bytes", status_code=status.HTTP_200_OK)
async def foundation_put_upload(
    upload_id: str = PathParam(...),
    user: UserContext = Depends(require_project_role("analyst"))
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Artifact storage is not configured in B00 baseline."
    )

@router.post("/uploads/{upload_id}:finalize", status_code=status.HTTP_200_OK)
async def foundation_finalize_upload(
    upload_id: str = PathParam(...),
    user: UserContext = Depends(require_project_role("analyst")),
    idemp: str = Depends(verify_idempotency_key)
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Artifact storage is not configured in B00 baseline."
    )

@router.get("/artifacts/{artifact_id}", status_code=status.HTTP_200_OK)
async def foundation_get_artifact(
    artifact_id: str = PathParam(...),
    user: UserContext = Depends(require_project_role("analyst"))
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

@router.get("/artifacts/{artifact_id}/bytes", status_code=status.HTTP_200_OK)
async def foundation_download_artifact(
    artifact_id: str = PathParam(...),
    user: UserContext = Depends(require_project_role("analyst"))
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

@router.get("/jobs/{job_id}", response_model=Job, status_code=status.HTTP_200_OK)
async def foundation_get_job(
    job_id: str = PathParam(...),
    user: UserContext = Depends(require_project_role("viewer"))
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

@router.post("/jobs/{job_id}:cancel", status_code=status.HTTP_200_OK)
async def foundation_cancel_job(
    job_id: str = PathParam(...),
    user: UserContext = Depends(require_project_role("operator")),
    idemp: str = Depends(verify_idempotency_key)
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Jobs engine unconfigured in B00 baseline.")
