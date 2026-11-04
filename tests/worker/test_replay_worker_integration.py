'''Real-PostgreSQL gated integration tests for the AFR replay worker (B05).

Skipped unless AFR_TEST_DATABASE_URL points at a disposable PostgreSQL 16
database. Proves fenced lease claiming, fence-checked terminal completion,
stale-fence rejection, and cancellation safety on an actual database with
ROW-LEVEL SECURITY enforced (FORCE RLS on all project tables).

The worker runs against the live SQLAlchemy session factory, so the test
overrides DATABASE_URL to the disposable database before importing worker
modules. No SQLite substitution: these assertions are meaningless without a
real PostgreSQL 16 and are skipped locally.
'''

from __future__ import annotations

import os
import uuid
import asyncio
import json
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.core import config as _cfg
from src.core import database as _db

DSN = os.environ.get('AFR_TEST_DATABASE_URL')

pytestmark = pytest.mark.skipif(
    not DSN, reason='AFR_TEST_DATABASE_URL not set; real PostgreSQL 16 unavailable'
)

# SQLAlchemy asyncpg DSN from a libpq-style AFR_TEST_DATABASE_URL (only when set).
ASYNC_DSN = None
if DSN:
    ASYNC_DSN = DSN
    if ASYNC_DSN.startswith('postgresql://'):
        ASYNC_DSN = 'postgresql+asyncpg://' + ASYNC_DSN[len('postgresql://'):]

MIGRATION_DIR = (
    __import__('pathlib').Path(__file__).resolve().parents[2] / 'database/migrations'
)

ARTIFACT_ROOT = Path('/tmp/afr-worker-it-artifacts')


def _split_statements(sql: str):
    statements, buf, in_dollar, tag = [], [], False, ''
    i = 0
    while i < len(sql):
        c = sql[i]
        if in_dollar:
            buf.append(c)
            if c == '$' and tag and sql[i - len(tag):i] == tag and sql[i:i + 1] == '$':
                in_dollar = False
                tag = ''
            i += 1
            continue
        if c == '$':
            j = i + 1
            while j < len(sql) and sql[j].isalnum():
                j += 1
            tag = sql[i + 1:j]
            if tag:
                in_dollar = True
                buf.append(sql[i:j])
                i = j
                continue
            buf.append(c)
        elif c == ';':
            stmt = ''.join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
        else:
            buf.append(c)
        i += 1
    tail = ''.join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


async def _apply(conn, filename: str) -> None:
    sql = (MIGRATION_DIR / filename).read_text()
    for stmt in _split_statements(sql):
        await conn.execute(stmt)


@pytest.fixture
async def pg():
    conn = await asyncpg.connect(DSN)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def session(pg):
    '''SQLAlchemy session bound to the disposable test database.'''
    _cfg.settings.DATABASE_URL = ASYNC_DSN
    _db.engine = create_async_engine(ASYNC_DSN, echo=False, future=True)
    _db.AsyncSessionLocal = async_sessionmaker(
        bind=_db.engine, class_=_db.AsyncSessionLocal.class_,
        expire_on_commit=False, autocommit=False, autoflush=False,
    )
    async with _db.AsyncSessionLocal() as s:
        yield s
    await _db.engine.dispose()


async def _setup_project(conn) -> uuid.UUID:
    org_id = uuid.UUID('00000000-0000-4000-8000-000000000000')
    user_id = uuid.UUID('00000000-0000-4000-8000-000000000001')
    project_id = uuid.UUID('00000000-0000-4000-8000-000000000100')
    await conn.execute(
        "INSERT INTO core.organizations VALUES ($1,'org-a')", org_id
    )
    await conn.execute(
        "INSERT INTO core.users VALUES ($1,'test-idp.local','sub-1')", user_id
    )
    await conn.execute(
        "INSERT INTO core.memberships VALUES ($1,$2,'admin')", org_id, user_id
    )
    await conn.execute(
        "INSERT INTO core.projects VALUES ($1,$2,'p-a','metadata_only',false,1,now())",
        project_id, org_id,
    )
    await conn.execute(
        "INSERT INTO core.project_roles VALUES ($1,$2,'maintainer')",
        project_id, user_id,
    )
    return project_id


async def _set_project_context(conn, project_id: uuid.UUID) -> None:
    await conn.execute(
        "SELECT set_config('baseline.project_id', $1, true)", str(project_id)
    )


async def _insert_artifact(
    conn, project_id: uuid.UUID, artifact_id: uuid.UUID, payload: dict
) -> None:
    """Insert a ready artifact and write its recording bytes to disk."""
    data = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_ROOT / f'{artifact_id}.bin').write_bytes(data)
    sha = __import__('hashlib').sha256(data).hexdigest()
    await conn.execute(
        """INSERT INTO core.artifacts
           (id, project_id, sha256, byte_size, media_type, classification, state, storage_key)
           VALUES ($1,$2,$3,$4,'application/json','synthetic','ready',$5,$6)""",
        artifact_id, project_id, sha, len(data), str(artifact_id), str(artifact_id),
    )


async def _insert_queued_replay_stack(
    conn, project_id: uuid.UUID, artifact_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Insert run, case, replay, and a queued afr.replay job. Returns ids."""
    run_id = uuid.uuid4()
    case_id = uuid.uuid4()
    replay_id = uuid.uuid4()
    job_id = uuid.uuid4()

    await conn.execute(
        """INSERT INTO afr.runs
           (id, project_id, state, revision, event_count, completeness, verified_outcome)
           VALUES ($1,$2,'recording',1,0,'{}','unscored')""",
        run_id, project_id,
    )
    definition = {
        'mode': 'recorded',
        'fixture_artifact_ids': [str(artifact_id)],
        'checks': [{'kind': 'json_equals', 'path': '/status', 'expected': 'passed'}],
    }
    await conn.execute(
        """INSERT INTO afr.cases
           (id, project_id, run_id, version, run_revision, manifest_sha256, definition)
           VALUES ($1,$2,$3,1,1,'deadbeef',$4::jsonb)""",
        case_id, project_id, run_id, json.dumps(definition),
    )
    await conn.execute(
        """INSERT INTO afr.replays
           (id, project_id, case_id, job_id, mode, result)
           VALUES ($1,$2,$3,$4,'recorded',NULL)""",
        replay_id, project_id, case_id, job_id,
    )
    await conn.execute(
        """INSERT INTO core.jobs
           (id, project_id, kind, state, payload, attempt, fence, revision)
           VALUES ($1,$2,'afr.replay','queued',$3::jsonb,0,0,1)""",
        job_id, project_id, json.dumps({'replay_id': str(replay_id)}),
    )
    return run_id, case_id, replay_id, job_id


@pytest.mark.asyncio
async def test_worker_claims_queued_job_and_leases(pg, session):
    await _apply(pg, '001_baseline.sql')
    await _apply(pg, '002_roles.sql')
    project_id = await _setup_project(pg)
    _run_id, _case_id, replay_id, job_id = await _insert_queued_replay_stack(
        pg, project_id, uuid.uuid4()
    )

    from src.worker.replay_worker import ReplayWorker

    worker = ReplayWorker(project_scopes=[project_id])

    # Claim in one short transaction (worker design: claim commits its own lease).
    async with session as s:
        await s.execute(
            sa_text("SELECT set_config('baseline.project_id', :pid, true)"),
            {'pid': str(project_id)},
        )
        claimed = await worker._claim(s, str(project_id))

    assert claimed is not None, 'expected to claim the queued replay job'
    assert claimed['id'] == str(job_id)
    assert claimed['fence'] == 1  # 0 -> 1 on claim
    assert claimed['payload'] is not None

    # Job row must now be leased with a future lease_until.
    row = await pg.fetchrow(
        "SELECT state, fence, lease_until FROM core.jobs WHERE id = $1", job_id
    )
    assert row is not None
    assert row['state'] == 'leased'
    assert row['fence'] == 1
    assert row['lease_until'] is not None


@pytest.mark.asyncio
async def test_worker_fenced_completion_rejects_stale_fence(pg, session):
    await _apply(pg, '001_baseline.sql')
    await _apply(pg, '002_roles.sql')
    project_id = await _setup_project(pg)
    _run_id, _case_id, replay_id, job_id = await _insert_queued_replay_stack(
        pg, project_id, uuid.uuid4()
    )

    from src.worker.replay_worker import ReplayWorker

    worker = ReplayWorker(project_scopes=[project_id])

    # Claim the job (fence 0 -> 1).
    async with session as s:
        await s.execute(
            sa_text("SELECT set_config('baseline.project_id', :pid, true)"),
            {'pid': str(project_id)},
        )
        claimed = await worker._claim(s, str(project_id))
    assert claimed is not None

    # Process with the CORRECT fence -> terminal + replay result published.
    outcome = await worker.process_job(str(project_id), claimed)
    assert outcome == 'succeeded', f'expected succeeded, got {outcome}'

    row = await pg.fetchrow("SELECT state, result_id FROM core.jobs WHERE id = $1", job_id)
    assert row['state'] == 'succeeded'
    assert row['result_id'] == replay_id

    replay = await pg.fetchrow(
        "SELECT result, state FROM afr.replays WHERE id = $1", replay_id
    )
    assert replay is not None
    assert replay['result'] is not None
    assert replay['result']['state'] == 'succeeded'
    assert replay['result']['network_calls'] == 0

    # Re-processing with the SAME claimed fence must be rejected (job already terminal).
    again = await worker.process_job(str(project_id), claimed)
    assert again == 'stale', f'expected stale, got {again}'

    # Process with a STALE fence (fence advanced beyond claim) must be rejected.
    await pg.execute(
        "UPDATE core.jobs SET fence = fence + 1 WHERE id = $1", job_id
    )
    stale_outcome = await worker.process_job(str(project_id), claimed)
    assert stale_outcome == 'stale', f'expected stale for stale fence, got {stale_outcome}'


@pytest.mark.asyncio
async def test_worker_cancelled_job_stays_terminal(pg, session):
    await _apply(pg, '001_baseline.sql')
    await _apply(pg, '002_roles.sql')
    project_id = await _setup_project(pg)
    _run_id, _case_id, replay_id, job_id = await _insert_queued_replay_stack(
        pg, project_id, uuid.uuid4()
    )

    # Cancel the job before the worker sees it.
    await pg.execute(
        "UPDATE core.jobs SET state = 'cancelled' WHERE id = $1", job_id
    )

    from src.worker.replay_worker import ReplayWorker

    worker = ReplayWorker(project_scopes=[project_id])

    # The claim SELECT ... WHERE state='queued' must skip a cancelled job.
    async with session as s:
        await s.execute(
            sa_text("SELECT set_config('baseline.project_id', :pid, true)"),
            {'pid': str(project_id)},
        )
        claimed = await worker._claim(s, str(project_id))

    assert claimed is None, 'cancelled job must not be claimed'

    # Even if a stale caller holds a claim, processing a cancelled job returns 'gone'.
    outcome = await worker.process_job(
        str(project_id),
        {'id': str(job_id), 'payload': {'replay_id': str(replay_id)}, 'attempt': 1, 'fence': 1},
    )
    assert outcome == 'gone', f'expected gone for cancelled job, got {outcome}'

    # Job remains cancelled (not overwritten by the worker).
    row = await pg.fetchrow("SELECT state FROM core.jobs WHERE id = $1", job_id)
    assert row['state'] == 'cancelled'


@pytest.mark.asyncio
async def test_worker_end_to_end_replay_with_artifact(pg, session):
    await _apply(pg, '001_baseline.sql')
    await _apply(pg, '002_roles.sql')
    project_id = await _setup_project(pg)
    artifact_id = uuid.uuid4()

    await _insert_artifact(
        pg, project_id, artifact_id,
        {
            'schema_version': 'afr-recording/1',
            'final_output': {'status': 'passed'},
            'final_state': {},
            'tool_results': [],
        },
    )

    _run_id, _case_id, replay_id, job_id = await _insert_queued_replay_stack(
        pg, project_id, artifact_id
    )

    from src.worker.replay_worker import ReplayWorker

    worker = ReplayWorker(project_scopes=[project_id])

    # Claim + process in one pass via run_once.
    outcome = await worker.run_once(str(project_id))
    assert outcome == 'succeeded', f'expected succeeded end-to-end, got {outcome}'

    # Job terminal, replay result persisted, outbox delivery marked.
    row = await pg.fetchrow(
        "SELECT state, result_id, fence FROM core.jobs WHERE id = $1", job_id
    )
    assert row['state'] == 'succeeded'
    assert row['result_id'] == replay_id
    assert row['fence'] == 2  # claim incremented, then finalize uses same fence

    replay = await pg.fetchrow("SELECT result FROM afr.replays WHERE id = $1", replay_id)
    assert replay is not None
    result = replay['result']
    assert result['state'] == 'pass'
    assert result['network_calls'] == 0
    assert len(result['checks']) == 1
    assert result['checks'][0]['outcome'] == 'pass'
    assert result['checks'][0]['reason'] == 'check matched recording'

    delivered = await pg.fetchval(
        """SELECT count(*) FROM core.outbox
           WHERE kind = 'afr.replay.requested'
             AND (body->>'job_id')::uuid = $1
             AND delivered_at IS NOT NULL""",
        job_id,
    )
    assert delivered == 1, 'outbox delivery mark must be recorded'
