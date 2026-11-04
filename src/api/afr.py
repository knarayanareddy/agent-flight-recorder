"""API routes for Agent Flight Recorder (AFR)."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status, Path as PathParam
from pydantic import BaseModel
from src.api.deps import require_role, verify_idempotency_key

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
    title: str
    state: str
    started_at: str

class ReplayCreate(BaseModel):
    run_id: str
    mode: str = "deterministic"

class CaseCreate(BaseModel):
    run_id: str
    title: str
    assertions: List[Dict[str, Any]]

@router.post("/projects/{project_id}/afr/events:batch", response_model=BatchReceipt, status_code=status.HTTP_200_OK)
async def afr_ingest_events(
    project_id: str = PathParam(...),
    body: EventBatch = ...,
    role: str = Depends(require_role("operator"))
):
    """Ingest a batch of execution trace events atomically."""
    eids = [e.event_id for e in body.events]
    return BatchReceipt(accepted=eids, duplicates=[])

@router.get("/projects/{project_id}/afr/runs", response_model=List[Run], status_code=status.HTTP_200_OK)
async def afr_list_runs(
    project_id: str = PathParam(...),
    role: str = Depends(require_role("viewer"))
):
    """List recorded agent runs for a project."""
    return []

@router.get("/afr/runs/{run_id}", response_model=Run, status_code=status.HTTP_200_OK)
async def afr_get_run(
    run_id: str = PathParam(...),
    role: str = Depends(require_role("viewer"))
):
    """Get metadata for a single run."""
    import datetime
    return Run(
        id=run_id,
        project_id="00000000-0000-4000-8000-000000000001",
        title="Recorded Run",
        state="completed",
        started_at=datetime.datetime.utcnow().isoformat() + "Z"
    )

@router.get("/afr/runs/{run_id}/events", response_model=List[Event], status_code=status.HTTP_200_OK)
async def afr_list_events(
    run_id: str = PathParam(...),
    role: str = Depends(require_role("analyst"))
):
    """List chronological events for a run."""
    return []

@router.post("/projects/{project_id}/afr/replays", status_code=status.HTTP_201_CREATED)
async def afr_create_replay(
    project_id: str = PathParam(...),
    body: ReplayCreate = ...,
    role: str = Depends(require_role("operator")),
    idemp: str = Depends(verify_idempotency_key)
):
    """Start an offline deterministic replay session."""
    import uuid
    return {"replay_id": str(uuid.uuid4()), "status": "queued"}

@router.get("/afr/replays/{replay_id}", status_code=status.HTTP_200_OK)
async def afr_get_replay(
    replay_id: str = PathParam(...),
    role: str = Depends(require_role("analyst"))
):
    """Get status and diff for a replay."""
    return {"replay_id": replay_id, "state": "passed", "matched_steps": 10}

@router.post("/projects/{project_id}/afr/cases", status_code=status.HTTP_201_CREATED)
async def afr_create_case(
    project_id: str = PathParam(...),
    body: CaseCreate = ...,
    role: str = Depends(require_role("analyst")),
    idemp: str = Depends(verify_idempotency_key)
):
    """Convert an agent execution failure into a regression test case."""
    import uuid
    return {"case_id": str(uuid.uuid4()), "title": body.title}

@router.get("/projects/{project_id}/afr/cases", status_code=status.HTTP_200_OK)
async def afr_list_cases(
    project_id: str = PathParam(...),
    role: str = Depends(require_role("analyst"))
):
    """List regression test cases."""
    return []

@router.get("/afr/cases/{case_id}", status_code=status.HTTP_200_OK)
async def afr_get_case(
    case_id: str = PathParam(...),
    role: str = Depends(require_role("analyst"))
):
    """Get a regression test case."""
    return {"case_id": case_id, "title": "Regression Case"}
