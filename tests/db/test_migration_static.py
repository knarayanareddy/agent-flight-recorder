'''Static checks of the baseline migration SQL (no database required).

These verify the migration FILES declare the expected schema, not runtime
behavior. Runtime migration/RLS/FK/concurrency tests live in
test_postgres_gated.py and require a real PostgreSQL 16 instance.
'''

from pathlib import Path
import re

import pytest

from pglast import parse_sql

MIGRATIONS = sorted(Path(__file__).resolve().parents[2].joinpath('database/migrations').glob('*.sql'))

EXPECTED_CORE_TABLES = [
    'organizations', 'users', 'memberships', 'projects', 'project_roles',
    'api_keys', 'artifacts', 'uploads', 'artifact_links', 'jobs', 'job_attempts',
    'idempotency', 'project_creation_idempotency', 'outbox', 'budget_reservations',
    'audit_events', 'deletions',
]
EXPECTED_AFR_TABLES = ['runs', 'events', 'cases', 'replays']


def _sql_text() -> str:
    return ''.join(path.read_text() for path in MIGRATIONS)


def test_migrations_parse_as_postgresql():
    for path in MIGRATIONS:
        parse_sql(path.read_text())


def test_migrations_declare_expected_tables():
    sql = _sql_text()
    for schema, tables in (('core', EXPECTED_CORE_TABLES), ('afr', EXPECTED_AFR_TABLES)):
        for table in tables:
            assert re.search(rf'CREATE TABLE {schema}\.{table}\b', sql), (
                f'missing CREATE TABLE {schema}.{table}'
            )


def test_idempotency_scoped_keys_in_migration():
    sql = _sql_text()
    assert re.search(r'PRIMARY KEY\(project_id,\s*actor_id,\s*route,\s*key\)', sql)
    assert re.search(r'PRIMARY KEY\(organization_id,\s*actor_id,\s*route,\s*key\)', sql)
    assert 'project_creation_idempotency' in sql


def test_project_creation_idempotency_has_no_nullable_project_scope():
    sql = _sql_text()
    block = sql[sql.index('CREATE TABLE core.project_creation_idempotency'):]
    block = block[: block.index(';', block.index('PRIMARY KEY')) + 1]
    assert 'project_id' not in block


def test_rls_policies_declared_for_idempotency_tables():
    sql = _sql_text()
    assert 'project_creation_org_scope' in sql
    assert 'FORCE ROW LEVEL SECURITY' in sql


def test_migration_files_are_baseline_then_roles():
    names = [path.name for path in MIGRATIONS]
    assert names == ['001_baseline.sql', '002_roles.sql']
