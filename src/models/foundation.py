'''SQLAlchemy ORM models for the shared foundation (core schema).

Matches database/migrations/001_baseline.sql table-by-table: UUID primary keys,
foreign key constraints, check constraints, and column types mirror the
normative PostgreSQL 16 DDL. The runtime role owns none of these tables and is
never superuser/BYPASSRLS; migrations are applied externally as the migration
owner.
'''

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, UUID

from src.core.database import Base


class Organization(Base):
    __tablename__ = 'organizations'
    __table_args__ = {'schema': 'core'}

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'core'}

    id = Column(UUID(as_uuid=True), primary_key=True)
    issuer = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)


class Membership(Base):
    __tablename__ = 'memberships'
    __table_args__ = (
        ForeignKeyConstraint(['organization_id'], ['core.organizations.id']),
        ForeignKeyConstraint(['user_id'], ['core.users.id']),
        CheckConstraint("org_role IN ('member','admin')"),
        {'schema': 'core'},
    )

    organization_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    org_role = Column(Text, nullable=False)


class Project(Base):
    __tablename__ = 'projects'
    __table_args__ = (
        ForeignKeyConstraint(['organization_id'], ['core.organizations.id']),
        CheckConstraint("length(name) BETWEEN 1 AND 120"),
        CheckConstraint("content_capture IN ('metadata_only','redacted')"),
        CheckConstraint('revision > 0'),
        {'schema': 'core'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(Text, nullable=False)
    content_capture = Column(Text, nullable=False, server_default='metadata_only')
    external_transfer = Column(Boolean, nullable=False, server_default='false')
    revision = Column(BigInteger, nullable=False, server_default='1')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProjectRole(Base):
    __tablename__ = 'project_roles'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        ForeignKeyConstraint(['user_id'], ['core.users.id']),
        CheckConstraint("role IN ('viewer','analyst','operator','maintainer')"),
        {'schema': 'core'},
    )

    project_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    role = Column(Text, primary_key=True, nullable=False)


class ApiKey(Base):
    __tablename__ = 'api_keys'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        {'schema': 'core'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    key_digest = Column(BYTEA, nullable=False, unique=True)
    scopes = Column(ARRAY(Text), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))


class Artifact(Base):
    __tablename__ = 'artifacts'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        CheckConstraint("sha256 ~ '^[a-f0-9]{64}$'"),
        CheckConstraint('byte_size > 0 AND byte_size <= 104857600'),
        CheckConstraint("classification IN ('synthetic','public_authorized','sensitive')"),
        CheckConstraint("state IN ('pending','ready','quarantined','deleting','deleted')"),
        {'schema': 'core'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    sha256 = Column(Text, nullable=False)
    byte_size = Column(BigInteger, nullable=False)
    media_type = Column(Text, nullable=False)
    classification = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True))


class Upload(Base):
    __tablename__ = 'uploads'
    __table_args__ = (
        ForeignKeyConstraint(['project_id', 'artifact_id'], ['core.artifacts.project_id', 'core.artifacts.id']),
        CheckConstraint('expected_size > 0'),
        {'schema': 'core'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    artifact_id = Column(UUID(as_uuid=True), nullable=False)
    expected_size = Column(BigInteger, nullable=False)
    expected_sha256 = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    finalized_at = Column(DateTime(timezone=True))


class ArtifactLink(Base):
    __tablename__ = 'artifact_links'
    __table_args__ = (
        CheckConstraint('parent_id <> child_id'),
        ForeignKeyConstraint(['project_id', 'parent_id'], ['core.artifacts.project_id', 'core.artifacts.id']),
        ForeignKeyConstraint(['project_id', 'child_id'], ['core.artifacts.project_id', 'core.artifacts.id']),
        {'schema': 'core'},
    )

    project_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    parent_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    child_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    relation = Column(Text, nullable=False)


class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        CheckConstraint("state IN ('queued','leased','running','cancel_requested','succeeded','failed','timed_out','cancelled','failed_unknown_effect')"),
        CheckConstraint("jsonb_typeof(payload) = 'object'"),
        CheckConstraint('attempt >= 0'),
        {'schema': 'core'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    kind = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    attempt = Column(Integer, nullable=False, server_default='0')
    fence = Column(BigInteger, nullable=False, server_default='0')
    revision = Column(BigInteger, nullable=False, server_default='1')
    lease_until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    result_id = Column(UUID(as_uuid=True))
    error_code = Column(Text)


class JobAttempt(Base):
    __tablename__ = 'job_attempts'
    __table_args__ = (
        CheckConstraint('attempt > 0'),
        ForeignKeyConstraint(['project_id', 'job_id'], ['core.jobs.project_id', 'core.jobs.id']),
        {'schema': 'core'},
    )

    project_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    job_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    attempt = Column(Integer, primary_key=True, nullable=False)
    fence = Column(BigInteger, nullable=False)
    state = Column(Text, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True))


class Idempotency(Base):
    '''Ordinary project-scoped idempotency: key (project_id, actor_id, route, key).'''
    __tablename__ = 'idempotency'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        ForeignKeyConstraint(['actor_id'], ['core.users.id']),
        {'schema': 'core'},
    )

    project_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    actor_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    route = Column(Text, primary_key=True, nullable=False)
    key = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    request_sha256 = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class ProjectCreationIdempotency(Base):
    '''Organization-scoped idempotency for project creation (no project exists yet).'''
    __tablename__ = 'project_creation_idempotency'
    __table_args__ = (
        ForeignKeyConstraint(['organization_id'], ['core.organizations.id']),
        ForeignKeyConstraint(['actor_id'], ['core.users.id']),
        {'schema': 'core'},
    )

    organization_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    actor_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    route = Column(Text, primary_key=True, nullable=False)
    key = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    request_sha256 = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class Outbox(Base):
    __tablename__ = 'outbox'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        {'schema': 'core'},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    kind = Column(Text, nullable=False)
    body = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    delivered_at = Column(DateTime(timezone=True))


class BudgetReservation(Base):
    __tablename__ = 'budget_reservations'
    __table_args__ = (
        ForeignKeyConstraint(['project_id', 'job_id'], ['core.jobs.project_id', 'core.jobs.id']),
        CheckConstraint('token_limit >= 0'),
        CheckConstraint('call_limit >= 0'),
        CheckConstraint('reserved_eur >= 0'),
        CheckConstraint('observed_eur >= 0'),
        CheckConstraint("state IN ('reserved','settled','unknown','released')"),
        {'schema': 'core'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    token_limit = Column(BigInteger, nullable=False)
    call_limit = Column(Integer, nullable=False)
    reserved_eur = Column(Numeric(20, 8))
    observed_eur = Column(Numeric(20, 8))
    state = Column(Text, nullable=False)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        ForeignKeyConstraint(['actor_id'], ['core.users.id']),
        {'schema': 'core'},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(UUID(as_uuid=True))
    actor_id = Column(UUID(as_uuid=True))
    action = Column(Text, nullable=False)
    target_id = Column(UUID(as_uuid=True))
    decision = Column(Text, nullable=False)
    policy_version = Column(Text, nullable=False)
    request_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Deletion(Base):
    __tablename__ = 'deletions'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        CheckConstraint("state IN ('requested','revoked','purging','complete','failed')"),
        {'schema': 'core'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    target_kind = Column(Text, nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    state = Column(Text, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=False)
    purge_deadline = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
