'''API routes for Shared Foundation -- real, database-backed where implemented.

Unimplemented storage paths (uploads, artifact bytes, jobs) remain 501 until
their B04/B05 backing is connected; project creation and listing are implemented
against PostgreSQL with scoped idempotency and RLS context set transactionally.
'''

from typing import List

from fastapi import APIRouter, Depends, Header, Path as PathParam, status
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import (
    get_current_user,
    require_object_capability,
    require_project_capability,
    require_org_admin,
    verify_idempotency_key,
)
from src.core.database import get_db_session
from src.core.security import UserContext
from src.services.artifact import ArtifactService, FilesystemArtifactStore
from src.services.afr import FlightRecorderService

router = APIRouter()

_artifact_store = FilesystemArtifactStore()


def _artifact_service(db: AsyncSession = Depends(get_db_session)) -> ArtifactService:
    return ArtifactService(db, _artifact_store)


def _afr_service(db: AsyncSession = Depends(get_db_session)) -> FlightRecorderService:
    return FlightRecorderService(db, artifact_store=_artifact_store)


async def _set_context(db: AsyncSession, user: UserContext, project_id: str | None = None):
    """Set transaction-local RLS context; local=true resets at commit/rollback."""
    await db.execute(
        text("SELECT set_config('baseline.organization_id', :oid, true)"),
        {'oid': user.organization_id},
    )
    if project_id:
        await db.execute(
            text("SELECT set_config('baseline.project_id', :pid, true)"),
            {'pid': project_id},
        )


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    content_capture: str = Field(default='metadata_only')
    external_transfer: bool = False


class Project(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    name: str
    content_capture: str
    external_transfer: bool
    revision: int
    created_at: str


class UploadCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    filename: str = Field(min_length=1, max_length=200)
    media_type: str = 'application/octet-stream'
    byte_size: int = Field(ge=1)
    expected_sha256: str
    classification: str = 'synthetic'


class Upload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    artifact_id: str
    put_path: str
    expires_at: str
    maximum_bytes: int


class UploadFinalize(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sha256: str
    byte_size: int = Field(ge=1)


class Artifact(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    project_id: str
    sha256: str
    byte_size: int
    media_type: str
    status: str
    classification: str
    created_at: str


class Job(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    project_id: str
    kind: str
    state: str
    attempt: int = Field(ge=0)
    revision: int = Field(ge=1)
    created_at: str
    result_id: str | None = None
    error_code: str | None = None


@router.post(
    '/projects', response_model=Project, status_code=status.HTTP_201_CREATED,
)
async def foundation_create_project(
    body: ProjectCreate,
    user: UserContext = Depends(require_org_admin),
    idemp: str = Depends(verify_idempotency_key),
    svc: FlightRecorderService = Depends(_afr_service),
    db: AsyncSession = Depends(get_db_session),
):
    await _set_context(db, user)
    project = await svc.create_project(
        user.organization_id, user.user_id, idemp, body.name,
        body.content_capture, body.external_transfer,
    )
    return Project(
        id=project['id'], name=project['name'],
        content_capture=project['content_capture'],
        external_transfer=project['external_transfer'],
        revision=project['revision'], created_at=project['created_at'],
    )


@router.get('/projects', response_model=List[Project])
async def foundation_list_projects(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    svc: FlightRecorderService = Depends(_afr_service),
):
    await _set_context(db, user)
    from sqlalchemy import select
    from src.models.foundation import Project as ProjectRow
    rows = (await db.scalars(select(ProjectRow))).all()
    return [
        Project(
            id=str(r.id), name=r.name, content_capture=r.content_capture,
            external_transfer=r.external_transfer, revision=r.revision,
            created_at=r.created_at.isoformat(),
        ) for r in rows
    ]


@router.post(
    '/projects/{project_id}/uploads', response_model=Upload,
    status_code=status.HTTP_201_CREATED,
)
async def foundation_create_upload(
    project_id: str = PathParam(...),
    body: UploadCreate = ...,
    user: UserContext = Depends(require_project_capability('analyst')),
    idemp: str = Depends(verify_idempotency_key),
    svc: ArtifactService = Depends(_artifact_service),
    db: AsyncSession = Depends(get_db_session),
):
    await _set_context(db, user, project_id)
    created = await svc.create_upload(
        project_id, user.user_id, idemp, body.filename, body.media_type,
        body.byte_size, body.expected_sha256, body.classification,
    )
    return Upload(
        id=created['upload_id'], artifact_id=created['artifact_id'],
        put_path=created['put_path'], expires_at=created['expires_at'],
        maximum_bytes=created['maximum_bytes'],
    )


@router.put('/uploads/{upload_id}/bytes', status_code=status.HTTP_200_OK)
async def foundation_put_upload(
    upload_id: str = PathParam(...),
    body: bytes = ...,
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('analyst')),
    db: AsyncSession = Depends(get_db_session),
    svc: ArtifactService = Depends(_artifact_service),
):
    if not x_project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    await _set_context(db, user, x_project_id)
    from sqlalchemy import select
    from src.models.foundation import Upload as UploadRow
    upload = await db.scalar(select(UploadRow).where(UploadRow.id == upload_id))
    if upload is None or str(upload.project_id) != x_project_id:
        raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'upload not found'})
    await svc.put_upload_bytes(upload_id, body)
    return {'status': 'stored'}


@router.post('/uploads/{upload_id}:finalize', status_code=status.HTTP_200_OK)
async def foundation_finalize_upload(
    upload_id: str = PathParam(...),
    body: UploadFinalize = ...,
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('analyst')),
    idemp: str = Depends(verify_idempotency_key),
    db: AsyncSession = Depends(get_db_session),
    svc: ArtifactService = Depends(_artifact_service),
):
    if not x_project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    await _set_context(db, user, x_project_id)
    from sqlalchemy import select
    from src.models.foundation import Upload as UploadRow
    upload = await db.scalar(select(UploadRow).where(UploadRow.id == upload_id))
    if upload is None or str(upload.project_id) != x_project_id:
        raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'upload not found'})
    return await svc.finalize_upload(upload_id, user.user_id, idemp, body.sha256, body.byte_size)


@router.get('/artifacts/{artifact_id}', response_model=Artifact)
async def foundation_get_artifact(
    artifact_id: str = PathParam(...),
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('analyst')),
    db: AsyncSession = Depends(get_db_session),
    svc: ArtifactService = Depends(_artifact_service),
):
    if not x_project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    await _set_context(db, user, x_project_id)
    artifact = await svc.get_artifact(artifact_id)
    if str(artifact['project_id']) != x_project_id:
        raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'artifact not found'})
    return Artifact(**artifact)


@router.get('/artifacts/{artifact_id}/bytes')
async def foundation_download_artifact(
    artifact_id: str = PathParam(...),
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('analyst')),
    db: AsyncSession = Depends(get_db_session),
    svc: ArtifactService = Depends(_artifact_service),
):
    from fastapi.responses import Response
    if not x_project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    await _set_context(db, user, x_project_id)
    artifact = await svc.get_artifact(artifact_id)
    if str(artifact['project_id']) != x_project_id:
        raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'artifact not found'})
    data = await svc.get_artifact_bytes(artifact_id)
    return Response(
        content=data, media_type=artifact['media_type'],
        headers={'Content-Disposition': 'attachment', 'X-Content-Type-Options': 'nosniff'},
    )


@router.get('/jobs/{job_id}', response_model=Job)
async def foundation_get_job(
    job_id: str = PathParam(...),
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('viewer')),
    db: AsyncSession = Depends(get_db_session),
):
    if not x_project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    await _set_context(db, user, x_project_id)
    from sqlalchemy import select
    from src.models.foundation import Job as JobRow
    job = await db.scalar(select(JobRow).where(JobRow.id == job_id))
    if job is None or str(job.project_id) != x_project_id:
        raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'job not found'})
    return Job(
        id=str(job.id), project_id=str(job.project_id), kind=job.kind, state=job.state,
        attempt=job.attempt, revision=job.revision, created_at=job.created_at.isoformat(),
        result_id=str(job.result_id) if job.result_id else None,
        error_code=job.error_code,
    )


@router.post('/jobs/{job_id}:cancel', status_code=status.HTTP_200_OK)
async def foundation_cancel_job(
    job_id: str = PathParam(...),
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('operator')),
    idemp: str = Depends(verify_idempotency_key),
    db: AsyncSession = Depends(get_db_session),
):
    if not x_project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    await _set_context(db, user, x_project_id)
    from sqlalchemy import select
    from src.models.foundation import Job as JobRow
    job = await db.scalar(select(JobRow).where(JobRow.id == job_id))
    if job is None or str(job.project_id) != x_project_id:
        raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'job not found'})
    if job.state not in {'queued', 'leased', 'running'}:
        raise HTTPException(status_code=409, detail={'code': 'conflict', 'message': 'job already terminal'})
    job.state = 'cancel_requested'
    job.revision = (job.revision or 1) + 1
    await db.commit()
    return Job(
        id=str(job.id), project_id=str(job.project_id), kind=job.kind, state=job.state,
        attempt=job.attempt, revision=job.revision, created_at=job.created_at.isoformat(),
        result_id=str(job.result_id) if job.result_id else None,
        error_code=job.error_code,
    )
