'''API routes for Agent Flight Recorder (AFR) -- real, database-backed.

All mutating routes require Idempotency-Key (UUIDv4). Object routes resolve the
object's actual project and return 404 when it does not match the authorized
project context (never a cross-project oracle).
'''

from typing import Any

from fastapi import APIRouter, Depends, Header, Path as PathParam, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import (
    get_current_user,
    require_object_capability,
    require_project_capability,
    verify_idempotency_key,
)
from src.core.database import get_db_session
from src.core.security import UserContext
from src.services.afr import FlightRecorderService

router = APIRouter()


class Event(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: str = 'afr-event/1'
    event_id: str
    run_id: str
    producer_id: str = Field(min_length=1, max_length=100)
    producer_seq: int = Field(ge=0)
    event_type: str
    observed_at: str
    capture_policy_id: str
    payload: dict[str, Any]


class EventBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    events: list[Event] = Field(min_length=1, max_length=500)


class BatchReceipt(BaseModel):
    model_config = ConfigDict(extra='forbid')
    accepted: list[str]
    duplicates: list[str]
    request_id: str


class Run(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    project_id: str
    state: str
    revision: int = Field(ge=1)
    event_count: int = Field(ge=0)
    completeness: list[str] = []
    verified_outcome: str = 'unscored'
    created_at: str


class ReplayCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    case_id: str
    case_version: int = Field(ge=1)
    mode: str = 'recorded'
    maximum_seconds: int = Field(default=30, ge=1, le=300)


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_id: str
    run_revision: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    mode: str = 'recorded'
    checks: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    fixture_artifact_ids: list[str] = []


class Case(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    project_id: str
    schema_version: str = 'afr-case/1'
    version: int
    manifest_sha256: str
    definition: dict[str, Any]
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


def _service(db: AsyncSession = Depends(get_db_session)) -> FlightRecorderService:
    return FlightRecorderService(db)


@router.post(
    '/projects/{project_id}/afr/events:batch',
    response_model=BatchReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
async def afr_ingest_events(
    project_id: str = PathParam(...),
    body: EventBatch = ...,
    user: UserContext = Depends(require_project_capability('operator')),
    idemp: str = Depends(verify_idempotency_key),
    svc: FlightRecorderService = Depends(_service),
):
    receipt = await svc.ingest_batch(project_id, user.user_id, idemp, body.model_dump())
    return BatchReceipt(
        accepted=receipt['accepted'], duplicates=receipt['duplicates'],
        request_id=receipt['request_id'],
    )


@router.get('/projects/{project_id}/afr/runs', response_model=list[Run])
async def afr_list_runs(
    project_id: str = PathParam(...),
    user: UserContext = Depends(require_project_capability('viewer')),
    svc: FlightRecorderService = Depends(_service),
):
    return await svc.list_runs(project_id)


@router.get('/afr/runs/{run_id}', response_model=Run)
async def afr_get_run(
    run_id: str = PathParam(...),
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('viewer')),
    svc: FlightRecorderService = Depends(_service),
):
    if not x_project_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    return await svc.get_run(run_id, x_project_id)


@router.get('/afr/runs/{run_id}/events', response_model=list[Event])
async def afr_list_events(
    run_id: str = PathParam(...),
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('analyst')),
    svc: FlightRecorderService = Depends(_service),
):
    if not x_project_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    return await svc.list_events(run_id, x_project_id)


@router.post(
    '/projects/{project_id}/afr/cases',
    response_model=Case,
    status_code=status.HTTP_201_CREATED,
)
async def afr_create_case(
    project_id: str = PathParam(...),
    body: CaseCreate = ...,
    user: UserContext = Depends(require_project_capability('analyst')),
    idemp: str = Depends(verify_idempotency_key),
    svc: FlightRecorderService = Depends(_service),
):
    return await svc.create_case(project_id, user.user_id, idemp, body.model_dump())


@router.get('/projects/{project_id}/afr/cases', response_model=list[Case])
async def afr_list_cases(
    project_id: str = PathParam(...),
    user: UserContext = Depends(require_project_capability('analyst')),
    svc: FlightRecorderService = Depends(_service),
):
    return await svc.list_cases(project_id)


@router.get('/afr/cases/{case_id}', response_model=Case)
async def afr_get_case(
    case_id: str = PathParam(...),
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('analyst')),
    svc: FlightRecorderService = Depends(_service),
):
    if not x_project_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    return await svc.get_case(case_id, x_project_id)


@router.post(
    '/projects/{project_id}/afr/replays',
    status_code=status.HTTP_202_ACCEPTED,
)
async def afr_create_replay(
    project_id: str = PathParam(...),
    body: ReplayCreate = ...,
    user: UserContext = Depends(require_project_capability('operator')),
    idemp: str = Depends(verify_idempotency_key),
    svc: FlightRecorderService = Depends(_service),
):
    job = await svc.create_replay(project_id, user.user_id, idemp, body.model_dump())
    return Job(
        id=job['id'], project_id=project_id, kind='afr.replay', state='queued',
        attempt=job['attempt'], revision=job['revision'], created_at=job['created_at'],
        result_id=job['result_id'], error_code=job['error_code'],
    )


@router.get('/afr/replays/{replay_id}')
async def afr_get_replay(
    replay_id: str = PathParam(...),
    x_project_id: str | None = Header(None, alias='X-Project-Id'),
    user: UserContext = Depends(require_object_capability('analyst')),
    svc: FlightRecorderService = Depends(_service),
):
    if not x_project_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'forbidden', 'message': 'project context required'},
        )
    return await svc.get_replay(replay_id, x_project_id)
