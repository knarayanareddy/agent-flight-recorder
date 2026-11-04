"""API routes for Agent Flight Recorder (AFR) - Fail-Closed Baseline."""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status, Path as PathParam, HTTPException
from pydantic import BaseModel
from src.api.deps import (
    require_project_capability,
    require_object_capability,
    verify_idempotency_key
)
from src.core.security import UserContext

router = APIRouter()


class Event(BaseModel):
    schema_version: str = "afr-event/1"
    event_id: str
    run_id: str
    producer_id: str
    producer_seq: int
    event_type: str
    observed_at: str
    capture_policy_id: str
    payload: Dict[str, Any]


class EventBatch(BaseModel):
    events: List[Event]


class BatchReceipt(BaseModel):
    accepted: List[str]
    duplicates: List[str]


class Run(BaseModel):
    id: str
    project_id: str
    state: str
    revision: int = 1
    event_count: int = 0
    created_at: str


class ReplayCreate(BaseModel):
    case_id: str
    case_version: int
    mode: str = "recorded"
    maximum_seconds: int = 30


class CaseCreate(BaseModel):
    run_id: str
    run_revision: int
    name: str
    mode: str = "recorded"
    checks: List[Dict[str, Any]]
    fixture_artifact_ids: List[str] = []


@router.post("/projects/{project_id}/afr/events:batch",
             response_model=BatchReceipt,
             status_code=status.HTTP_202_ACCEPTED)
async def afr_ingest_events(
    project_id: str = PathParam(...),
    body: EventBatch = ...,
    user: UserContext = Depends(require_project_capability("operator"))
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="Event ingestion storage unconfigured in B00 baseline.")


@router.get("/projects/{project_id}/afr/runs", response_model=List[Run], status_code=status.HTTP_200_OK)
async def afr_list_runs(
    project_id: str = PathParam(...),
    user: UserContext = Depends(require_project_capability("viewer"))
):
    return []


@router.get("/afr/runs/{run_id}", response_model=Run, status_code=status.HTTP_200_OK)
async def afr_get_run(
    run_id: str = PathParam(...),
    user: UserContext = Depends(require_object_capability("viewer"))
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")


@router.get("/afr/runs/{run_id}/events", response_model=List[Event], status_code=status.HTTP_200_OK)
async def afr_list_events(
    run_id: str = PathParam(...),
    user: UserContext = Depends(require_object_capability("analyst"))
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")


@router.post("/projects/{project_id}/afr/replays", status_code=status.HTTP_202_ACCEPTED)
async def afr_create_replay(
    project_id: str = PathParam(...),
    body: ReplayCreate = ...,
    user: UserContext = Depends(require_project_capability("operator")),
    idemp: str = Depends(verify_idempotency_key)
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="Replay engine unconfigured in B00 baseline.")


@router.get("/afr/replays/{replay_id}", status_code=status.HTTP_200_OK)
async def afr_get_replay(
    replay_id: str = PathParam(...),
    user: UserContext = Depends(require_object_capability("analyst"))
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Replay not found")


@router.post("/projects/{project_id}/afr/cases", status_code=status.HTTP_201_CREATED)
async def afr_create_case(
    project_id: str = PathParam(...),
    body: CaseCreate = ...,
    user: UserContext = Depends(require_project_capability("analyst")),
    idemp: str = Depends(verify_idempotency_key)
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Case store unconfigured in B00 baseline.")


@router.get("/projects/{project_id}/afr/cases", status_code=status.HTTP_200_OK)
async def afr_list_cases(
    project_id: str = PathParam(...),
    user: UserContext = Depends(require_project_capability("analyst"))
):
    return []


@router.get("/afr/cases/{case_id}", status_code=status.HTTP_200_OK)
async def afr_get_case(
    case_id: str = PathParam(...),
    user: UserContext = Depends(require_object_capability("analyst"))
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
