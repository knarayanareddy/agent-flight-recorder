'''AFR replay worker: fenced lease execution through the transactional outbox.

Claims queued afr.replay jobs with PostgreSKIP LOCKED, executes recorded replay
fail-closed (zero network calls, no live fallback), and finalizes only while
the lease fence is still active. Stale completions are rejected, never treated
as success. Cancelled jobs stay terminal.
'''

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal
from src.models.foundation import Job
from src.services.afr import FlightRecorderService
from src.services.artifact import FilesystemArtifactStore

logger = logging.getLogger('afr.worker')

LEASE_SQL = '''
WITH candidate AS (
    SELECT id, fence FROM core.jobs
    WHERE project_id = :project_id AND state = 'queued'
    ORDER BY created_at, id FOR UPDATE SKIP LOCKED LIMIT 1
)
UPDATE core.jobs j
SET state = ' leased', attempt = j.attempt + 1, fence = j.fence + 1,
    lease_until = now() + interval '30 seconds',
    revision = j.revision + 1, updated_at = now()
FROM candidate c
WHERE j.id = c.id
RETURNING j.id, j.kind, j.payload, j.attempt, j.fence, j.lease_until;
'''

COMPLETE_SQL = '''
UPDATE core.jobs
SET state = :terminal_state, result_id = :result_id,
    lease_until = NULL, revision = revision + 1, updated_at = now()
WHERE id = :job_id AND project_id = :project_id AND fence = :fence
  AND state IN ('leased', 'running') AND lease_until > now()
  AND :terminal_state IN ('succeeded', 'failed', 'timed_out')
RETURNING *;
'''

ATTEMPT_INSERT = '''
INSERT INTO core.job_attempts (project_id, job_id, attempt, fence, state, started_at, finished_at)
VALUES (:project_id, :job_id, :attempt, :fence, :state, now(), :finished_at);
'''

OUTBOX_MARK_DELIVERED = '''
UPDATE core.outbox
SET delivered_at = now()
WHERE kind = 'afr.replay.requested'
  AND (body->>'job_id')::uuid = :job_id
  AND delivered_at IS NULL;
'''

TERMINAL_FOR = {'pass': 'succeeded', 'fail': 'failed', 'error': 'failed'}


class ReplayWorker:
    def __init__(
        self,
        project_scopes: list[uuid.UUID],
        poll_interval: float = 1.0,
        lease_seconds: int = 30,
    ):
        self.project_scopes = [str(p) for p in project_scopes]
        self.poll_interval = poll_interval
        self.lease_seconds = lease_seconds
        self._store = FilesystemArtifactStore()
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def _claim(self, db: AsyncSession, project_id: str):
        result = await db.execute(text(LEASE_SQL), {'project_id': project_id})
        row = result.mappings().first()
        await db.commit()  # lease claim is its own short transaction
        return dict(row) if row else None

    async def _complete(
        self, db: AsyncSession, project_id: str, job_id: uuid.UUID, fence: int,
        terminal_state: str, result_id: uuid.UUID | None,
    ) -> bool:
        result = await db.execute(
            text(COMPLETE_SQL),
            {
                'job_id': str(job_id), 'project_id': project_id, 'fence': fence,
                'terminal_state': terminal_state,
                'result_id': str(result_id) if result_id else None,
            },
        )
        await db.commit()
        return result.rowcount == 1

    async def _record_attempt(
        self, db: AsyncSession, project_id: str, job_id: uuid.UUID, attempt: int,
        fence: int, state: str,
    ) -> None:
        await db.execute(
            text(ATTEMPT_INSERT),
            {
                'project_id': project_id, 'job_id': str(job_id), 'attempt': attempt,
                'fence': fence, 'state': state,
                'finished_at': None,
            },
        )
        await db.commit()

    async def process_job(self, project_id: str, claimed: dict) -> str:
        job_id = uuid.UUID(claimed['id'])
        replay_id = uuid.UUID(claimed['payload']['replay_id'])
        attempt = int(claimed['attempt'])
        fence = int(claimed['fence'])

        async with AsyncSessionLocal() as db:
            await db.execute(
                text("SELECT set_config('baseline.project_id', :pid, true)"),
                {'pid': project_id},
            )

            job = await db.get(Job, job_id)
            if job is None or job.state not in {'queued', 'leased'}:
                return 'gone'

            await self._record_attempt(db, uuid.UUID(project_id), job_id, attempt, fence, 'running')

            svc = FlightRecorderService(db, artifact_store=self._store)
            try:
                result = await svc.compute_replay_result(replay_id)
            except ValueError as exc:
                logger.warning('Replay %s cannot be computed: %s', replay_id, exc)
                ok = await self._complete(
                    db, project_id, job_id, fence, 'failed', replay_id,
                )
                return 'failed' if ok else 'stale'

            terminal_state = TERMINAL_FOR.get(result['state'], 'failed')
            ok = await self._complete(
                db, project_id, job_id, fence, terminal_state, replay_id,
            )
            if not ok:
                logger.warning('Replay %s fence mismatch; attempt %d abandoned', replay_id, attempt)
                return 'stale'

            await svc.finalize_replay(replay_id, result, job_id, fence)
            await db.execute(text(OUTBOX_MARK_DELIVERED), {'job_id': job_id})
            await db.commit()
            return terminal_state

    async def run_once(self, project_id: str) -> str | None:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("SELECT set_config('baseline.project_id', :pid, true)"),
                {'pid': project_id},
            )
            claimed = await self._claim(db, project_id)
        if not claimed:
            return None
        return await self.process_job(project_id, claimed)

    async def run(self) -> None:
        while not self._stop.is_set():
            for project_id in self.project_scopes:
                if self._stop.is_set():
                    break
                try:
                    outcome = await self.run_once(project_id)
                    if outcome is None:
                        await asyncio.sleep(self.poll_interval)
                except Exception:  # pragma: no cover - defensive worker loop
                    logger.exception('Worker loop error for project %s', project_id)
                    await asyncio.sleep(self.poll_interval)
