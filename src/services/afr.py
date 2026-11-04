'''Agent Flight Recorder domain service.

Real, database-backed implementation of the AFR contract:
metadata-first event ingestion (atomic, idempotent, conflict-aware), run
materialization with explicit completeness, immutable regression cases, and
recorded-output replay dispatched through the transactional outbox.

Never imports reference/oracles.py; implements baseline-json/1 canonicalization
and RFC 6901 JSON Pointer resolution locally.
'''

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.afr import Case, Event, Replay, Run
from src.models.foundation import (
    Artifact,
    Idempotency,
    Job,
    Outbox,
    Project,
    ProjectCreationIdempotency,
)
from src.core.security import redact_metadata

CAPTURE_POLICY = 'metadata_only:v1'
ALLOWED_EVENT_TYPES = {
    'run.started', 'run.finished', 'model.requested', 'model.responded',
    'tool.requested', 'tool.responded', 'tool.failed',
    'capture.dropped', 'approval.decided',
}
ALLOWED_CHECK_KINDS = {'json_equals', 'forbidden_tool', 'mock_state_equals'}
IDEM_TTL_SECONDS = 24 * 60 * 60


class ArtifactStore(Protocol):
    '''Load artifact bytes by id. Implemented by the B04 artifact service.'''

    async def get_bytes(self, artifact_id: uuid.UUID) -> bytes:  # pragma: no cover
        raise NotImplementedError


def canonical_json(value: Any) -> bytes:
    '''baseline-json/1: UTF-8 JSON, sorted keys, compact separators, no NaN.'''
    import json

    return json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def deterministic_capture_policy_id(project_id: str) -> str:
    '''UUIDv5(namespace=project, name="metadata_only:v1") -- fixed profile ID.'''
    return str(uuid.uuid5(uuid.UUID(str(project_id)), CAPTURE_POLICY))


def normalize_event_envelope(event: dict) -> dict:
    '''Redact event payload metadata to allowlisted scalar fields.

    Credentials, nested structures and free-text reason are stripped: this is
    the metadata-only capture policy enforced before persistence.
    '''
    payload = event.get('payload') or {}
    if not isinstance(payload, dict):
        raise ValueError('payload must be an object')
    return {
        'schema_version': event.get('schema_version'),
        'event_id': event.get('event_id'),
        'run_id': event.get('run_id'),
        'producer_id': event.get('producer_id'),
        'producer_seq': event.get('producer_seq'),
        'event_type': event.get('event_type'),
        'observed_at': event.get('observed_at'),
        'capture_policy_id': event.get('capture_policy_id'),
        'payload': redact_metadata(payload),
    }


class FlightRecorderService:
    '''Core AFR business logic over asyncpg-backed SQLAlchemy sessions.'''

    def __init__(self, db: AsyncSession, artifact_store: ArtifactStore | None = None):
        self.db = db
        self.artifact_store = artifact_store

    # ---------------------------------------------------------------- project

    async def create_project(
        self, organization_id: str, actor_id: str, idempotency_key: str,
        name: str, content_capture: str = 'metadata_only',
        external_transfer: bool = False,
    ) -> dict:
        '''Atomically create a project under organization-scoped idempotency.

        Project creation is an organization-level operation: no project exists
        yet, so the idempotency lock lives in
        core.project_creation_idempotency keyed by (organization_id, actor_id,
        route, key). Project row, idempotency record and audit record commit in
        one transaction: concurrent identical requests create exactly one
        project; rollback strands nothing.
        '''
        oid = uuid.UUID(organization_id)
        aid = uuid.UUID(actor_id)
        key = uuid.UUID(idempotency_key)
        route = 'foundation_create_project'
        request_sha = sha256_hex({
            'route': route, 'organization_id': str(oid), 'actor_id': str(aid),
            'name': name, 'content_capture': content_capture,
            'external_transfer': bool(external_transfer),
        })

        existing = await self._fetch_idempotency(route, oid, aid, key, project_scoped=False)
        if existing is not None:
            if existing.request_sha256 != request_sha:
                raise HTTPException(
                    status_code=409,
                    detail={'code': 'conflict', 'message': 'idempotency key reused with a different project request'},
                )
            return self._project_from_body(existing.response_body)

        project_id = uuid.uuid4()
        try:
            self.db.add(Project(
                id=project_id, organization_id=oid, name=name,
                content_capture=content_capture,
                external_transfer=bool(external_transfer),
            ))
            self.db.add(ProjectCreationIdempotency(
                organization_id=oid, actor_id=aid, route=route, key=key,
                request_sha256=request_sha,
                response_status=201,
                response_body={
                    'project_id': str(project_id), 'name': name,
                    'content_capture': content_capture,
                    'external_transfer': bool(external_transfer),
                },
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=IDEM_TTL_SECONDS),
            ))
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
        existing = await self._fetch_idempotency(route, oid, aid, key, project_scoped=False)
        if existing is None:
            raise
            if existing.request_sha256 != request_sha:
                raise HTTPException(
                    status_code=409,
                    detail={'code': 'conflict', 'message': 'idempotency key reused with a different project request'},
                )
            return self._project_from_body(existing.response_body)
        await self.db.commit()
        return self._project_from_body({
            'project_id': str(project_id), 'name': name,
            'content_capture': content_capture,
            'external_transfer': bool(external_transfer),
        })

    @staticmethod
    def _project_from_body(body: dict) -> dict:
        return {
            'id': body['project_id'], 'name': body['name'],
            'content_capture': body['content_capture'],
            'external_transfer': body['external_transfer'],
            'revision': 1,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

    async def _fetch_idempotency(self, route, scope_id: uuid.UUID, actor_id: uuid.UUID, key: uuid.UUID, project_scoped: bool = True):
        if project_scoped:
            from src.models.foundation import Idempotency as I
            return await self.db.scalar(select(I).where(
                I.project_id == scope_id, I.actor_id == actor_id,
                I.route == route, I.key == key,
            ))
        from src.models.foundation import ProjectCreationIdempotency as PCI
        return await self.db.scalar(select(PCI).where(
            PCI.organization_id == scope_id, PCI.actor_id == actor_id,
            PCI.route == route, PCI.key == key,
        ))

    # ---------------------------------------------------------------- ingest

    async def ingest_batch(
        self, project_id: str, actor_id: str, idempotency_key: str,
        body: dict,
    ) -> dict:
        '''Atomically ingest an event batch.

        All-or-nothing: a schema/semantic error rejects the whole batch with no
        writes; a contradictory duplicate (same id with different content, or
        occupied producer_seq with a different id) rejects the batch with 409
        and no writes; identical duplicates are acknowledged as duplicates;
        valid new events are inserted with the run shell and a receipt
        returned.
        '''
        pid = uuid.UUID(project_id)
        aid = uuid.UUID(actor_id)
        key = uuid.UUID(idempotency_key)
        route = 'afr_ingest_events'
        request_sha = sha256_hex({
            'route': route, 'project_id': project_id, 'actor_id': actor_id,
            'events': [
                {
                    'event_id': e.get('event_id'), 'run_id': e.get('run_id'),
                    'producer_id': e.get('producer_id'),
                    'producer_seq': e.get('producer_seq'),
                } for e in (body.get('events') or [])
            ],
        })

        existing = await self._fetch_idempotency(route, pid, aid, key)
        if existing is not None:
            if existing.request_sha256 != request_sha:
                raise HTTPException(
                    status_code=409,
                    detail={'code': 'conflict', 'message': 'idempotency key reused with a different batch'},
                )
            body_resp = existing.response_body or {}
            return {
                'accepted': list(body_resp.get('accepted', [])),
                'duplicates': list(body_resp.get('duplicates', [])),
                'request_id': str(body_resp.get('request_id', key)),
            }

        events_in = body.get('events') or []
        if not 1 <= len(events_in) <= 500:
            raise HTTPException(
                status_code=422,
                detail={'code': 'invalid', 'message': 'batch must contain 1-500 events'},
            )

        normalized = []
        for event in events_in:
            try:
                normalized.append(normalize_event_envelope(event))
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail={'code': 'invalid', 'message': f'invalid event: {exc}'},
                )

        seen_ids: dict[str, str] = {}
        seen_seqs: dict[tuple, str] = {}
        accepted: list[str] = []
        duplicates: list[str] = []
        accepted_set: set[str] = set()
        run_ids: list[str] = []

        for event in normalized:
            eid = str(event['event_id'])
            digest = sha256_hex(event['payload'])
            if eid in seen_ids:
                if seen_ids[eid] != digest:
                    raise HTTPException(
                        status_code=409,
                        detail={'code': 'conflict', 'message': f'event {eid} repeated with different content'},
                    )
                duplicates.append(eid)
                continue
            seq_key = (str(event['run_id']), str(event['producer_id']), int(event['producer_seq']))
            if seq_key in seen_seqs:
                raise HTTPException(
                    status_code=409,
                    detail={'code': 'conflict', 'message': f'producer sequence {seq_key} occupied by {seen_seqs[seq_key]}'},
                )
            existing_event = await self.db.scalar(select(Event).where(
                Event.project_id == pid, Event.id == uuid.UUID(eid),
            ))
            if existing_event is not None:
                if existing_event.payload_sha256 != digest:
                    raise HTTPException(
                        status_code=409,
                        detail={'code': 'conflict', 'message': f'event {eid} exists with different content'},
                    )
                duplicates.append(eid)
                seen_ids[eid] = digest
                continue
            existing_seq = await self.db.scalar(select(Event.id).where(
                Event.project_id == pid, Event.run_id == uuid.UUID(str(event['run_id'])),
                Event.producer_id == str(event['producer_id']),
                Event.producer_seq == int(event['producer_seq']),
            ))
            if existing_seq is not None:
                raise HTTPException(
                    status_code=409,
                    detail={'code': 'conflict', 'message': f'producer sequence {seq_key} occupied'},
                )
            seen_ids[eid] = digest
            seen_seqs[seq_key] = eid
            accepted.append(eid)
            accepted_set.add(eid)
            run_ids.append(str(event['run_id']))

        try:
            for run_id in dict.fromkeys(run_ids):
                existing_run = await self.db.scalar(select(Run).where(
                    Run.project_id == pid, Run.id == uuid.UUID(run_id),
                ))
                if existing_run is None:
                    self.db.add(Run(
                        id=uuid.UUID(run_id), project_id=pid, state='recording',
                        revision=1, event_count=0,
                    ))
                else:
                    existing_run.revision = (existing_run.revision or 1) + 1

            for event in normalized:
                eid = str(event['event_id'])
                if eid not in accepted_set:
                    continue  # duplicate: acknowledged, not stored again
                self.db.add(Event(
                    id=uuid.UUID(eid), project_id=pid,
                    run_id=uuid.UUID(str(event['run_id'])),
                    producer_id=str(event['producer_id']),
                    producer_seq=int(event['producer_seq']),
                    event_type=str(event['event_type']),
                    observed_at=event['observed_at'],
                    payload_sha256=digest_of(event),
                    envelope=event,
                ))

            for run_id in dict.fromkeys(run_ids):
                run = await self.db.scalar(select(Run).where(
                    Run.project_id == pid, Run.id == uuid.UUID(run_id),
                ))
                run.event_count = await self.db.scalar(
                    select(Event.id).where(
                        Event.project_id == pid, Event.run_id == uuid.UUID(run_id),
                    ).count()
                )
                if any(
                    e['event_type'] == 'run.finished' and str(e['run_id']) == run_id
                    and str(e['event_id']) in accepted_set
                    for e in normalized
                ):
                    run.state = 'completed'

            receipt_request_id = uuid.uuid4()
            self.db.add(Idempotency(
                project_id=pid, actor_id=aid, route=route, key=key,
                request_sha256=request_sha,
                response_status=202,
                response_body={
                    'accepted': accepted, 'duplicates': duplicates,
                    'request_id': str(receipt_request_id),
                },
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=IDEM_TTL_SECONDS),
            ))
            self.db.add(Outbox(
                project_id=pid, kind='afr.events.ingested',
                body={
                    'request_id': str(receipt_request_id), 'project_id': project_id,
                    'accepted': accepted, 'duplicates': duplicates,
                },
            ))
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail={'code': 'conflict', 'message': 'batch conflicts with stored events'},
            )
        await self.db.commit()
        return {
            'accepted': accepted, 'duplicates': duplicates,
            'request_id': str(receipt_request_id),
        }

    # ---------------------------------------------------------------- runs

    async def list_runs(self, project_id: str, limit: int = 50, cursor: str | None = None) -> dict:
        pid = uuid.UUID(project_id)
        q = (select(Run).where(Run.project_id == pid)
             .order_by(Run.created_at.desc(), Run.id.desc())
             .limit(min(int(limit), 100)))
        runs = (await self.db.scalars(q)).all()
        return {
            'items': [self._run_dict(r) for r in runs],
            'next_cursor': None,
        }

    @staticmethod
    def _run_dict(run: Run) -> dict:
        return {
            'id': str(run.id), 'project_id': str(run.project_id),
            'state': run.state, 'revision': run.revision,
            'event_count': run.event_count,
            'completeness': list(run.completeness or []),
            'verified_outcome': run.verified_outcome,
            'created_at': run.created_at.isoformat(),
        }

    async def get_run(self, run_id: str, project_id: str | None = None) -> dict:
        rid = uuid.UUID(run_id)
        q = select(Run).where(Run.id == rid)
        if project_id is not None:
            q = q.where(Run.project_id == uuid.UUID(project_id))
        run = await self.db.scalar(q)
        if run is None:
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'run not found'})
        return self._run_dict(run)

    async def list_events(
        self, run_id: str, project_id: str, limit: int = 50, cursor: str | None = None,
    ) -> dict:
        pid = uuid.UUID(project_id)
        rid = uuid.UUID(run_id)
        run = await self.db.scalar(select(Run).where(Run.id == rid, Run.project_id == pid))
        if run is None:
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'run not found'})
        q = (select(Event).where(Event.project_id == pid, Event.run_id == rid)
             .order_by(Event.received_at.asc(), Event.id.asc()).limit(min(int(limit), 100)))
        events = (await self.db.scalars(q)).all()
        return {
            'items': [self._event_dict(e) for e in events],
            'next_cursor': None,
        }

    @staticmethod
    def _event_dict(event: Event) -> dict:
        envelope = event.envelope or {}
        payload = envelope.get('payload') or {}
        return {
            'schema_version': envelope.get('schema_version', 'afr-event/1'),
            'event_id': str(event.id), 'run_id': str(event.run_id),
            'producer_id': event.producer_id, 'producer_seq': event.producer_seq,
            'event_type': event.event_type,
            'observed_at': event.observed_at.isoformat(),
            'capture_policy_id': envelope.get('capture_policy_id'),
            'payload': payload,
        }

    # ---------------------------------------------------------------- cases

    async def create_case(
        self, project_id: str, actor_id: str, idempotency_key: str, body: dict,
    ) -> dict:
        pid = uuid.UUID(project_id)
        aid = uuid.UUID(actor_id)
        key = uuid.UUID(idempotency_key)
        route = 'afr_create_case'
        request_sha = sha256_hex({
            'route': route, 'project_id': project_id, 'actor_id': actor_id,
            'run_id': body.get('run_id'), 'run_revision': body.get('run_revision'),
            'name': body.get('name'), 'mode': body.get('mode'),
            'checks': body.get('checks'),
            'fixture_artifact_ids': body.get('fixture_artifact_ids', []),
        })

        existing = await self._fetch_idempotency(route, pid, aid, key)
        if existing is not None:
            if existing.request_sha256 != request_sha:
                raise HTTPException(status_code=409, detail={'code': 'conflict'})
            return await self.get_case(str(existing.response_body['case_id']), project_id)

        run_id = uuid.UUID(str(body['run_id']))
        run = await self.db.scalar(select(Run).where(Run.id == run_id, Run.project_id == pid))
        if run is None:
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'run not found'})
        if run.revision != int(body['run_revision']):
            raise HTTPException(status_code=409, detail={
                'code': 'conflict', 'message': 'run revision changed since case snapshot',
            })

        checks = body.get('checks') or []
        if not 1 <= len(checks) <= 100:
            raise HTTPException(
                status_code=422, detail={'code': 'invalid', 'message': 'checks must contain 1-100 items'},
            )
        for index, check in enumerate(checks):
            if check.get('kind') not in ALLOWED_CHECK_KINDS:
                raise HTTPException(status_code=422, detail={
                    'code': 'invalid', 'message': f'unsupported check kind at index {index}',
                })
            path = check.get('path', '')
            if not isinstance(path, str) or not path.startswith('/'):
                raise HTTPException(status_code=422, detail={
                    'code': 'invalid', 'message': f'invalid JSON pointer path at index {index}',
                })
            _validate_json_pointer(path)

        fixture_ids = [uuid.UUID(str(f)) for f in (body.get('fixture_artifact_ids') or [])]
        if len(fixture_ids) > 100:
            raise HTTPException(status_code=422, detail={'code': 'invalid', 'message': 'too many fixture artifacts'})
        for fid in fixture_ids:
            artifact = await self.db.scalar(select(Artifact).where(
                Artifact.id == fid, Artifact.project_id == pid,
            ))
            if artifact is None:
                raise HTTPException(status_code=404, detail={
                    'code': 'not_found', 'message': f'artifact {fid} not found in this project',
                })

        manifest_input = {
            'run_id': str(run_id), 'run_revision': run.revision, 'name': body['name'],
            'mode': body['mode'], 'checks': checks,
            'fixture_artifact_ids': [str(f) for f in fixture_ids],
            'event_count': run.event_count,
        }
        manifest_sha = sha256_hex(manifest_input)
        case_id = uuid.uuid4()
        definition = {
            'run_id': str(run_id), 'run_revision': run.revision, 'name': body['name'],
            'mode': body['mode'], 'checks': checks,
            'fixture_artifact_ids': [str(f) for f in fixture_ids],
        }
        try:
            self.db.add(Case(
                id=case_id, project_id=pid, run_id=run_id, version=1,
                run_revision=run.revision, manifest_sha256=manifest_sha,
                definition=definition,
            ))
            self.db.add(Idempotency(
                project_id=pid, actor_id=aid, route=route, key=key,
                request_sha256=request_sha, response_status=201,
                response_body={'case_id': str(case_id), 'manifest_sha256': manifest_sha},
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=IDEM_TTL_SECONDS),
            ))
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            existing = await self._fetch_idempotency(route, pid, aid, key)
            if existing is None:
                raise
            if existing.request_sha256 != request_sha:
                raise HTTPException(status_code=409, detail={'code': 'conflict'})
            return await self.get_case(str(existing.response_body['case_id']), project_id)
        await self.db.commit()
        return await self.get_case(str(case_id), project_id)

    async def get_case(self, case_id: str, project_id: str | None = None) -> dict:
        cid = uuid.UUID(case_id)
        q = select(Case).where(Case.id == cid)
        if project_id is not None:
            q = q.where(Case.project_id == uuid.UUID(project_id))
        case = await self.db.scalar(q)
        if case is None:
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'case not found'})
        return {
            'id': str(case.id), 'project_id': str(case.project_id),
            'schema_version': 'afr-case/1', 'version': case.version,
            'manifest_sha256': case.manifest_sha256, 'definition': case.definition,
            'created_at': case.created_at.isoformat(),
        }

    async def list_cases(self, project_id: str, limit: int = 50, cursor: str | None = None) -> dict:
        pid = uuid.UUID(project_id)
        q = (select(Case).where(Case.project_id == pid)
             .order_by(Case.created_at.desc(), Case.id.asc())
             .limit(min(int(limit), 100)))
        cases = (await self.db.scalars(q)).all()
        return {
            'items': [
                {
                    'id': str(c.id), 'project_id': str(c.project_id),
                    'schema_version': 'afr-case/1', 'version': c.version,
                    'manifest_sha256': c.manifest_sha256, 'definition': c.definition,
                    'created_at': c.created_at.isoformat(),
                } for c in cases
            ],
            'next_cursor': None,
        }

    # ---------------------------------------------------------------- replays

    async def create_replay(
        self, project_id: str, actor_id: str, idempotency_key: str, body: dict,
    ) -> dict:
        pid = uuid.UUID(project_id)
        aid = uuid.UUID(actor_id)
        key = uuid.UUID(idempotency_key)
        route = 'afr_create_replay'
        request_sha = sha256_hex({
            'route': route, 'project_id': project_id, 'actor_id': actor_id,
            'case_id': body.get('case_id'), 'case_version': body.get('case_version'),
            'mode': body.get('mode'), 'maximum_seconds': body.get('maximum_seconds'),
        })

        existing = await self._fetch_idempotency(route, pid, aid, key)
        if existing is not None:
            if existing.request_sha256 != request_sha:
                raise HTTPException(status_code=409, detail={'code': 'conflict'})
            return self._job_dict(str(existing.response_body['job_id']))

        case_id = uuid.UUID(str(body['case_id']))
        case = await self.db.scalar(select(Case).where(Case.id == case_id, Case.project_id == pid))
        if case is None:
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'case not found'})
        if case.version != int(body['case_version']):
            raise HTTPException(status_code=409, detail={
                'code': 'conflict', 'message': 'case version mismatch',
            })
        mode = str(body.get('mode', 'recorded'))
        if mode not in {'visual', 'recorded'}:
            raise HTTPException(status_code=422, detail={
                'code': 'invalid', 'message': 'mode must be visual or recorded',
            })

        job_id = uuid.uuid4()
        replay_id = uuid.uuid4()
        try:
            self.db.add(Job(
                id=job_id, project_id=pid, kind='afr.replay', state='queued',
                payload={
                    'case_id': str(case_id), 'case_version': case.version,
                    'mode': mode,
                    'maximum_seconds': int(body.get('maximum_seconds', 30)),
                    'replay_id': str(replay_id),
                },
                attempt=0, revision=1,
            ))
            self.db.add(Replay(
                id=replay_id, project_id=pid, case_id=case_id, job_id=job_id,
                mode=mode, result=None,
            ))
            self.db.add(Idempotency(
                project_id=pid, actor_id=aid, route=route, key=key,
                request_sha256=request_sha, response_status=202,
                response_body={'job_id': str(job_id), 'replay_id': str(replay_id)},
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=IDEM_TTL_SECONDS),
            ))
            self.db.add(Outbox(
                project_id=pid, kind='afr.replay.requested',
                body={
                    'job_id': str(job_id), 'replay_id': str(replay_id),
                    'case_id': str(case_id), 'mode': mode,
                },
            ))
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            existing = await self._fetch_idempotency(route, pid, aid, key)
            if existing is None:
                raise
            if existing.request_sha256 != request_sha:
                raise HTTPException(status_code=409, detail={'code': 'conflict'})
            return self._job_dict(str(existing.response_body['job_id']))
        await self.db.commit()
        return self._job_dict(str(job_id))

    async def get_replay(self, replay_id: str, project_id: str | None = None) -> dict:
        rid = uuid.UUID(replay_id)
        q = select(Replay).where(Replay.id == rid)
        if project_id is not None:
            q = q.where(Replay.project_id == uuid.UUID(project_id))
        replay = await self.db.scalar(q)
        if replay is None:
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'replay not found'})
        result = replay.result or {
            'state': 'unscored', 'network_calls': 0,
            'checks': [], 'manifest_sha256': '',
        }
        return {
            'id': str(replay.id), 'job_id': str(replay.job_id),
            'case_id': str(replay.case_id),
            'state': result.get('state', 'unscored'),
            'network_calls': int(result.get('network_calls', 0)),
            'checks': result.get('checks', []),
            'manifest_sha256': result.get('manifest_sha256', ''),
        }

    # ---------------------------------------------------------------- replay execution (worker entry)

    async def compute_replay_result(self, replay_id: uuid.UUID) -> dict:
        '''Compute a recorded replay result fail-closed: zero network calls, no live fallback.

        Pure read+compute: writes nothing. The worker finalizes with a fenced
        job transition. Missing recording fails closed as `error`.
        '''
        replay = await self.db.scalar(select(Replay).where(Replay.id == replay_id))
        if replay is None:
            raise ValueError('replay not found')
        case = await self.db.scalar(select(Case).where(Case.id == replay.case_id))
        if case is None:
            raise ValueError('case not found')

        definition = case.definition or {}
        mode = str(definition.get('mode', 'recorded'))
        checks = definition.get('checks') or []

        checks_out: list[dict] = []
        state = 'pass'

        if mode == 'recorded':
            fixture_ids = definition.get('fixture_artifact_ids') or []
            recordings = [
                fid for fid in fixture_ids
                if await self.db.scalar(select(Artifact.id).where(
                    Artifact.id == uuid.UUID(str(fid)),
                    Artifact.project_id == replay.project_id,
                    Artifact.state == 'ready',
                ))
            ]
            if len(recordings) != 1:
                state = 'error'
                checks_out = [
                    {'index': i, 'outcome': 'error',
                     'reason': f'expected exactly one ready recording artifact, found {len(recordings)}'}
                    for i in range(len(checks))
                ]
            else:
                recording_bytes = await self._load_recording(uuid.UUID(str(recordings[0])))
                recording = _parse_recording(recording_bytes)
                final_output = recording.get('final_output') or {}
                final_state = recording.get('final_state') or {}
                tool_results = recording.get('tool_results') or []
                for index, check in enumerate(checks):
                    outcome, reason = _evaluate_check(
                        check, final_output, final_state, tool_results,
                    )
                    checks_out.append({'index': index, 'outcome': outcome, 'reason': reason})
                    if outcome != 'pass':
                        state = 'fail'
        else:
            checks_out = [
                {'index': i, 'outcome': 'unscored',
                 'reason': 'visual playback presents captured data only; no executable checks'}
                for i in range(len(checks))
            ]
            state = 'unscored'

        return {
            'id': str(replay_id), 'job_id': str(replay.job_id),
            'case_id': str(replay.case_id), 'state': state,
            'network_calls': 0, 'checks': checks_out,
            'manifest_sha256': case.manifest_sha256,
        }

    async def finalize_replay(
        self, replay_id: uuid.UUID, result: dict, job_id: uuid.UUID, fence: int,
    ) -> bool:
        '''Atomically publish the replay result and terminal job state.

        Returns False if the fence no longer matches (stale attempt: caller
        must not treat this as success).
        '''
        from src.models.foundation import Job

        complete = (
            update(Job)
            .where(Job.id == job_id)
            .where(Job.fence == fence)
            .where(Job.state.in_({'leased', 'running'}))
            .values(
                state={'pass': 'succeeded', 'fail': 'failed', 'error': 'failed'}[result['state']],
                revision=Job.revision + 1,
                result_id=replay_id,
            )
        )
        from sqlalchemy import func
        result_proxy = await self.db.execute(complete)
        if result_proxy.rowcount == 0:
            await self.db.rollback()
            return False
        replay = await self.db.scalar(select(Replay).where(Replay.id == replay_id))
        replay.result = result
        await self.db.commit()
        return True

    async def _load_recording(self, artifact_id: uuid.UUID) -> bytes:
        if self.artifact_store is None:
            raise ValueError('recording artifact store is not configured')
        return await self.artifact_store.get_bytes(artifact_id)

    @staticmethod
    def _job_dict(job_id: str) -> dict:
        return {
            'id': job_id, 'kind': 'afr.replay', 'state': 'queued',
            'attempt': 0, 'revision': 1, 'result_id': None, 'error_code': None,
        }


def digest_of(event: dict) -> str:
    return sha256_hex(event.get('payload') or {})


def _validate_json_pointer(path: str) -> None:
    if path == '':
        return
    if not path.startswith('/'):
        raise ValueError('JSON pointer must start with "/"')
    for token in path[1:].split('/'):
        token.replace('~1', '/').replace('~0', '~')  # syntactic validation only


def _json_pointer_get(document: Any, path: str):
    '''Resolve RFC 6901 pointer. Raises KeyError/IndexError when missing.'''
    if path == '':
        return document
    if not path.startswith('/'):
        raise KeyError(path)
    cur = document
    for token in path[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(cur, list):
            if token == '-' or not token.isdigit() or int(token) >= len(cur):
                raise KeyError(token)
            cur = cur[int(token)]
        elif isinstance(cur, dict):
            if token not in cur:
                raise KeyError(token)
            cur = cur[token]
        else:
            raise KeyError(token)
    return cur


def _json_equal(a: Any, b: Any) -> bool:
    '''Type-aware deep equality (bool != int, int != float).'''
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if set(a) != set(b):
            return False
        return all(_json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(_json_equal(x, y) for x, y in zip(a, b))
    return a == b


def _evaluate_check(check: dict, final_output: dict, final_state: dict,
                    tool_results: list[dict]) -> tuple[str, str]:
    kind = check.get('kind')
    path = check.get('path', '')
    expected = check.get('expected')

    try:
        if kind == 'json_equals':
            actual = _json_pointer_get(final_output, path)
            ok = _json_equal(actual, expected)
        elif kind == 'mock_state_equals':
            actual = _json_pointer_get(final_state, path)
            ok = _json_equal(actual, expected)
        elif kind == 'forbidden_tool':
            if path != '':
                return 'error', 'forbidden_tool path must be empty'
            forbidden = str(expected)
            used = [r.get('tool') for r in tool_results if isinstance(r, dict)]
            ok = forbidden not in used
        else:
            return 'error', f'unsupported check kind {kind}'
    except KeyError:
        return 'fail', 'pointer path not present in recording'
    except Exception as exc:  # pragma: no cover - defensive
        return 'error', f'check evaluation error: {exc}'

    return ('pass', 'check matched recording') if ok else ('fail', 'check did not match recording')


def _parse_recording(raw: bytes) -> dict:
    import json

    try:
        document = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f'recording artifact is not valid JSON: {exc}')
    if not isinstance(document, dict):
        raise ValueError('recording artifact must be a JSON object')
    if document.get('schema_version') != 'afr-recording/1':
        raise ValueError('unsupported recording schema_version')
    return document
