'''SQLAlchemy ORM models for the Agent Flight Recorder domain (afr schema).

Matches database/migrations/001_baseline.sql: afr.runs, afr.events, afr.cases,
afr.replays. Events and cases are append-only (immutability triggers enforced in
DDL); runs evolve only through the materializer. Composite foreign keys reference
core.projects/afr.runs on (project_id, id).
'''

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from src.core.database import Base


class Run(Base):
    __tablename__ = 'runs'
    __table_args__ = (
        ForeignKeyConstraint(['project_id'], ['core.projects.id']),
        CheckConstraint("state IN ('recording','completed','failed','abandoned')"),
        CheckConstraint("verified_outcome IN ('unscored','pass','fail','error')"),
        {'schema': 'afr'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    state = Column(Text, nullable=False)
    revision = Column(BigInteger, nullable=False, server_default='1')
    event_count = Column(BigInteger, nullable=False, server_default='0')
    completeness = Column(ARRAY(Text), nullable=False, server_default="'{}'")
    verified_outcome = Column(Text, nullable=False, server_default='unscored')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Event(Base):
    __tablename__ = 'events'
    __table_args__ = (
        ForeignKeyConstraint(['project_id', 'run_id'], ['afr.runs.project_id', 'afr.runs.id']),
        CheckConstraint('producer_seq >= 0'),
        {'schema': 'afr'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    project_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    producer_id = Column(Text, nullable=False)
    producer_seq = Column(BigInteger, nullable=False)
    event_type = Column(Text, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    payload_sha256 = Column(Text, nullable=False)
    envelope = Column(JSONB, nullable=False)


class Case(Base):
    __tablename__ = 'cases'
    __table_args__ = (
        ForeignKeyConstraint(['project_id', 'run_id'], ['afr.runs.project_id', 'afr.runs.id']),
        CheckConstraint('version > 0'),
        CheckConstraint("manifest_sha256 ~ '^[a-f0-9]{64}$'"),
        {'schema': 'afr'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    version = Column(BigInteger, nullable=False)
    run_revision = Column(BigInteger, nullable=False)
    manifest_sha256 = Column(Text, nullable=False)
    definition = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Replay(Base):
    __tablename__ = 'replays'
    __table_args__ = (
        ForeignKeyConstraint(['project_id', 'case_id'], ['afr.cases.project_id', 'afr.cases.id']),
        ForeignKeyConstraint(['project_id', 'job_id'], ['core.jobs.project_id', 'core.jobs.id']),
        CheckConstraint("mode IN ('visual','recorded')"),
        {'schema': 'afr'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    case_id = Column(UUID(as_uuid=True), nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    mode = Column(Text, nullable=False)
    result = Column(JSONB)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
