"""SQLAlchemy ORM models for Agent Flight Recorder."""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.core.database import Base
import uuid
import datetime


class DomainEntity(Base):
    """Domain model matching database/migrations/001_baseline.sql."""
    __tablename__ = "entities"
    __table_args__ = {"schema": "afr"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(120), nullable=False)
    state = Column(String(50), nullable=False, default="pending")
    metadata_payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
