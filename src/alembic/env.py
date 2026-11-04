'''Alembic environment wrapping the raw baseline SQL migrations.

Migration files in database/migrations/ are applied in filename order as the
migration owner on PostgreSQL 16. Each file runs inside one transaction; SQL
statements are split on semicolons outside $$-dollar-quoted PL/pgSQL blocks so
trigger functions survive intact. Offline mode renders the statements without
connecting.

The sqlalchemy.url must be a synchronous Postgres DSN
(e.g. postgresql+psycopg://...); the async asyncpg URL in src.core.config is
not usable by alembic directly. Migrations may also be applied directly with
psql, which remains the reference application path.
'''

import re
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, text

MIGRATION_DIR = Path(__file__).resolve().parents[2] / 'database' / 'migrations'
config = context.config
target_metadata = None  # baseline SQL is authoritative; no model autogenerate


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


def _run_statements(connection, statements):
    for stmt in statements:
        connection.execute(text(stmt))


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    with context.configure(url=url, literal_binds=True):
        for path in sorted(MIGRATION_DIR.glob('*.sql')):
            for stmt in _split_statements(path.read_text()):
                context.execute(stmt)


def run_migrations_online():
    connectable = create_engine(
        config.get_main_option('sqlalchemy.url'), pool_pre_ping=True
    )
    with connectable.connect() as connection:
        transaction = connection.begin()
        try:
            for path in sorted(MIGRATION_DIR.glob('*.sql')):
                _run_statements(connection, _split_statements(path.read_text()))
            transaction.commit()
        except BaseException:
            transaction.rollback()
            raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
