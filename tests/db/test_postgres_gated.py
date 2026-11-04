'''Real-PostgreSQL gated tests for B02 foundation behavior.

Skipped unless AFR_TEST_DATABASE_URL points at a disposable PostgreSQL 16
database. These prove migration application, role/RLS separation, FK checks,
append-only immutability, idempotency scoping, and pooled-context reset on an
actual database -- they are not run in the local checkout (no PostgreSQL
available here; see evidence/tickets/B00-start.md).
'''

import os
import re

import asyncpg
import pytest

MIGRATION_DIR = (
    __import__('pathlib').Path(__file__).resolve().parents[2] / 'database/migrations'
)

DSN = os.environ.get('AFR_TEST_DATABASE_URL')

pytestmark = pytest.mark.skipif(
    not DSN, reason='AFR_TEST_DATABASE_URL not set; real PostgreSQL 16 unavailable'
)


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


@pytest.fixture
async def db():
    conn = await asyncpg.connect(DSN)
    try:
        yield conn
    finally:
        await conn.close()


async def _apply(conn, filename):
    sql = (MIGRATION_DIR / filename).read_text()
    for stmt in _split_statements(sql):
        await conn.execute(stmt)


@pytest.mark.asyncio
async def test_migrations_apply_on_real_postgres(db):
    await _apply(db, '001_baseline.sql')
    await _apply(db, '002_roles.sql')
    tables = await db.fetch("""
        SELECT table_schema, table_name FROM information_schema.tables
        WHERE table_schema IN ('core','afr') ORDER BY 1, 2
    """)
    names = {f'{r["table_schema"]}.{r["table_name"]}' for r in tables}
    for expected in [
        'core.organizations', 'core.users', 'core.projects', 'core.idempotency',
        'core.project_creation_idempotency', 'core.outbox', 'afr.runs',
        'afr.events', 'afr.cases', 'afr.replays',
    ]:
        assert expected in names, f'missing {expected}'


@pytest.mark.asyncio
async def test_cross_project_composite_fk_rejected(db):
    await _apply(db, '001_baseline.sql')
    await _apply(db, '002_roles.sql')
    await db.execute("INSERT INTO core.organizations VALUES ('00000000-0000-4000-8000-000000000001','org-a')")
    await db.execute("INSERT INTO core.users VALUES ('00000000-0000-4000-8000-000000000002','issuer','sub')")
    await db.execute("INSERT INTO core.projects VALUES ('00000000-0000-4000-8000-000000000100','00000000-0000-4000-8000-000000000001','p-a','metadata_only',false,1,now())")
    await db.execute("INSERT INTO core.projects VALUES ('00000000-0000-4000-8000-000000000200','00000000-0000-4000-8000-000000000001','p-b','metadata_only',false,1,now())")
    run_a_id = '00000000-0000-4000-8000-000000000300'
    await db.execute(
        "INSERT INTO afr.runs VALUES ($1,'00000000-0000-4000-8000-000000000100','recording',1,0,'{}','unscored',now())",
        run_a_id,
    )
    # Event for run in project p-a but tagged project p-b must be rejected by the composite FK.
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await db.execute(
            "INSERT INTO afr.events VALUES ('00000000-0000-4000-8000-000000000400','00000000-0000-4000-8000-000000000200',$1,'prod',0,'model.requested',now(),'sha','{}')",
            run_a_id,
        )


@pytest.mark.asyncio
async def test_append_only_triggers_deny_update(db):
    await _apply(db, '001_baseline.sql')
    await db.execute("INSERT INTO core.organizations VALUES ('00000000-0000-4000-8000-000000000001','org-a')")
    await db.execute("INSERT INTO core.users VALUES ('00000000-0000-4000-8000-000000000002','issuer','sub')")
    await db.execute("INSERT INTO core.projects VALUES ('00000000-0000-4000-8000-000000000100','00000000-0000-4000-8000-000000000001','p-a','metadata_only',false,1,now())")
    run_id = '00000000-0000-4000-8000-000000000300'
    await db.execute(
        "INSERT INTO afr.runs VALUES ($1,'00000000-0000-4000-8000-000000000100','recording',1,0,'{}','unscored',now())",
        run_id,
    )
    event_id = '00000000-0000-4000-8000-000000000400'
    await db.execute(
        "INSERT INTO afr.events VALUES ($1,'00000000-0000-4000-8000-000000000100',$2,'prod',0,'model.requested',now(),'sha','{}')",
        event_id, run_id,
    )
    # Any UPDATE on afr.events is denied by the append-only immutability trigger.
    with pytest.raises(asyncpg.exceptions.PostgresError):
        await db.execute(
            "UPDATE afr.events SET envelope = '{}' WHERE id = $1", event_id
        )


@pytest.mark.asyncio
async def test_rls_project_scope_filters_rows(db):
    await _apply(db, '001_baseline.sql')
    await db.execute("INSERT INTO core.organizations VALUES ('00000000-0000-4000-8000-000000000001','org-a')")
    await db.execute("INSERT INTO core.users VALUES ('00000000-0000-4000-8000-000000000002','issuer','sub')")
    await db.execute("INSERT INTO core.projects VALUES ('00000000-0000-4000-8000-000000000100','00000000-0000-4000-8000-000000000001','p-a','metadata_only',false,1,now())")
    await db.execute("INSERT INTO core.projects VALUES ('00000000-0000-4000-8000-000000000200','00000000-0000-4000-8000-000000000001','p-b','metadata_only',false,1,now())")
    await db.execute("SELECT set_config('baseline.project_id','00000000-0000-4000-8000-000000000100',true)")
    rows = await db.fetch('SELECT id FROM core.projects')
    assert {r['id'] for r in rows} == {
        '00000000-0000-4000-8000-000000000100'
    }, 'RLS must hide rows from other projects'


@pytest.mark.asyncio
async def test_pooled_project_context_resets_after_transaction(db):
    await _apply(db, '001_baseline.sql')
    async with db.transaction():
        await db.execute("SELECT set_config('baseline.project_id','00000000-0000-4000-8000-000000000100',true)")
        assert await db.fetchval("SELECT current_setting('baseline.project_id', true)")
    # session-local config must not leak past transaction end (pooled connection reuse safety)
    assert await db.fetchval("SELECT current_setting('baseline.project_id', true)") is None


@pytest.mark.asyncio
async def test_idempotency_scoped_uniqueness(db):
    await _apply(db, '001_baseline.sql')
    await db.execute("INSERT INTO core.organizations VALUES ('00000000-0000-4000-8000-000000000001','org-a')")
    await db.execute("INSERT INTO core.users VALUES ('00000000-0000-4000-8000-000000000002','issuer','sub')")
    await db.execute("INSERT INTO core.projects VALUES ('00000000-0000-4000-8000-000000000100','00000000-0000-4000-8000-000000000001','p-a','metadata_only',false,1,now())")
    key = '00000000-0000-4000-8000-000000000500'
    await db.execute(
        "INSERT INTO core.idempotency (project_id, actor_id, route, key, request_sha256, response_status, response_body, expires_at) "
        "VALUES ('00000000-0000-4000-8000-000000000100','00000000-0000-4000-8000-000000000002','afr_ingest_events',$1,'sha',201,'{}',now() + interval '24 hours')",
        key,
    )
    # Same scoped key + same key collides: unique PK on (project_id, actor_id, route, key).
    with pytest.raises(asyncpg.UniqueViolationError):
        await db.execute(
            "INSERT INTO core.idempotency (project_id, actor_id, route, key, request_sha256, response_status, response_body, expires_at) "
            "VALUES ('00000000-0000-4000-8000-000000000100','00000000-0000-4000-8000-000000000002','afr_ingest_events',$1,'sha',200,'{}',now() + interval '24 hours')",
            key,
        )
    # Different project reusing the same actor/key is a distinct scope (no cross-project leak).
    await db.execute("INSERT INTO core.projects VALUES ('00000000-0000-4000-8000-000000000200','00000000-0000-4000-8000-000000000001','p-b','metadata_only',false,1,now())")
    await db.execute(
        "INSERT INTO core.idempotency (project_id, actor_id, route, key, request_sha256, response_status, response_body, expires_at) "
        "VALUES ('00000000-0000-4000-8000-000000000200','00000000-0000-4000-8000-000000000002','afr_ingest_events',$1,'sha',201,'{}',now() + interval '24 hours')",
        key,
    )
    # Organization-scoped project-creation table has no project_id and is keyed by organization.
    await db.execute(
        "INSERT INTO core.project_creation_idempotency (organization_id, actor_id, route, key, request_sha256, response_status, response_body, expires_at) "
        "VALUES ('00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002','foundation_create_project',$1,'sha',201,'{}',now() + interval '24 hours')",
        key,
    )
