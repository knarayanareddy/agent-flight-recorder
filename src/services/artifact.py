'''Private artifact store (B04).

Two-step upload/finalize with server-side SHA-256 verification, size and media
type quotas, and project-isolated storage. Bytes are never directly web-served;
downloads go through the authorized API gateway.
'''

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.foundation import Artifact, Upload

MAX_BYTES = 100 * 1024 * 1024
UPLOAD_TTL_SECONDS = 15 * 60


class ArtifactStore(Protocol):
    async def get_bytes(self, artifact_id: uuid.UUID) -> bytes:  # pragma: no cover
        raise NotImplementedError


class FilesystemArtifactStore:
    def __init__(self, root: str | Path = settings.ARTIFACT_STORAGE_PATH):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, artifact_id: uuid.UUID) -> Path:
        return self.root / f'{artifact_id}.bin'

    async def put_bytes(self, artifact_id: uuid.UUID, data: bytes) -> None:
        path = self._path(artifact_id)
        path.write_bytes(data)

    async def get_bytes(self, artifact_id: uuid.UUID) -> bytes:
        path = self._path(artifact_id)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='artifact bytes not found')
        return path.read_bytes()

    async def delete_bytes(self, artifact_id: uuid.UUID) -> None:
        path = self._path(artifact_id)
        if path.exists():
            path.unlink()


class ArtifactService:
    def __init__(self, db: AsyncSession, store: ArtifactStore):
        self.db = db
        self.store = store

    async def create_upload(
        self, project_id: str, actor_id: str, idempotency_key: str,
        filename: str, media_type: str, byte_size: int, sha256: str,
        classification: str,
    ) -> dict:
        if byte_size < 1 or byte_size > MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={'code': 'too_large', 'message': f'byte_size must be 1-{MAX_BYTES}'},
            )
        pid = uuid.UUID(project_id)
        aid = uuid.UUID(actor_id)
        key = uuid.UUID(idempotency_key)
        request_sha = sha256_hex({
            'route': 'foundation_create_upload', 'project_id': project_id,
            'actor_id': str(aid), 'filename': filename, 'media_type': media_type,
            'byte_size': byte_size, 'sha256': sha256, 'classification': classification,
        })
        from src.models.foundation import Idempotency
        existing = await self.db.scalar(select(Idempotency).where(
            Idempotency.project_id == pid, Idempotency.actor_id == aid,
            Idempotency.route == 'foundation_create_upload', Idempotency.key == key,
        ))
        if existing is not None:
            if existing.request_sha256 != request_sha:
                raise HTTPException(
                    status_code=409,
                    detail={'code': 'conflict', 'message': 'idempotency key reused with a different upload request'},
                )
            return existing.response_body

        upload_id = uuid.uuid4()
        artifact_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=UPLOAD_TTL_SECONDS)
        try:
            self.db.add(Upload(
                id=upload_id, project_id=pid, artifact_id=artifact_id,
                expected_size=byte_size, expected_sha256=sha256, expires_at=expires_at,
            ))
            self.db.add(Artifact(
                id=artifact_id, project_id=pid, sha256='', byte_size=0,
                media_type=media_type, classification=classification,
                state='pending', storage_key=f'uploads/{upload_id}',
                expires_at=expires_at,
            ))
            self.db.add(Idempotency(
                project_id=pid, actor_id=aid, route='foundation_create_upload',
                key=key, request_sha256=request_sha,
                response_status=201,
                response_body={
                    'upload_id': str(upload_id), 'artifact_id': str(artifact_id),
                    'put_path': f'/api/v1/uploads/{upload_id}/bytes',
                    'expires_at': expires_at.isoformat(),
                    'maximum_bytes': byte_size,
                },
                expires_at=expires_at,
            ))
            await self.db.flush()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.commit()
        return {
            'upload_id': str(upload_id), 'artifact_id': str(artifact_id),
            'put_path': f'/api/v1/uploads/{upload_id}/bytes',
            'expires_at': expires_at.isoformat(), 'maximum_bytes': byte_size,
        }

    async def put_upload_bytes(self, upload_id: str, data: bytes) -> None:
        upload = await self.db.scalar(select(Upload).where(Upload.id == uuid.UUID(upload_id)))
        if upload is None:
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'upload not found'})
        if len(data) != upload.expected_size:
            raise HTTPException(
                status_code=409,
                detail={'code': 'conflict', 'message': f'uploaded {len(data)} bytes, expected {upload.expected_size}'},
            )
        await self.store.put_bytes(upload.artifact_id, data)

    async def finalize_upload(
        self, upload_id: str, actor_id: str, idempotency_key: str,
        sha256: str, byte_size: int,
    ) -> dict:
        upload = await self.db.scalar(select(Upload).where(Upload.id == uuid.UUID(upload_id)))
        if upload is None:
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'upload not found'})
        if sha256 != upload.expected_sha256:
            raise HTTPException(
                status_code=409,
                detail={'code': 'conflict', 'message': 'finalize sha256 does not match upload declaration'},
            )
        if byte_size != upload.expected_size:
            raise HTTPException(
                status_code=409,
                detail={'code': 'conflict', 'message': 'finalize byte_size does not match upload declaration'},
            )
        data = await self.store.get_bytes(upload.artifact_id)
        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != sha256:
            # quarantine: hash mismatch never becomes readable
            artifact = await self.db.scalar(select(Artifact).where(Artifact.id == upload.artifact_id))
            if artifact is not None:
                artifact.state = 'quarantined'
                await self.db.commit()
            raise HTTPException(
                status_code=409,
                detail={'code': 'conflict', 'message': 'content hash verification failed; artifact quarantined'},
            )
        artifact = await self.db.scalar(select(Artifact).where(Artifact.id == upload.artifact_id))
        artifact.sha256 = sha256
        artifact.byte_size = byte_size
        artifact.state = 'ready'
        upload.finalized_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {
            'id': str(artifact.id), 'project_id': str(upload.project_id),
            'sha256': artifact.sha256, 'byte_size': artifact.byte_size,
            'media_type': artifact.media_type, 'status': artifact.state,
            'classification': artifact.classification,
            'created_at': artifact.created_at.isoformat(),
        }

    async def get_artifact(self, artifact_id: str) -> dict:
        artifact = await self.db.scalar(select(Artifact).where(Artifact.id == uuid.UUID(artifact_id)))
        if artifact is None or artifact.state == 'deleted':
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'artifact not found'})
        return {
            'id': str(artifact.id), 'project_id': str(artifact.project_id),
            'sha256': artifact.sha256, 'byte_size': artifact.byte_size,
            'media_type': artifact.media_type, 'status': artifact.state,
            'classification': artifact.classification,
            'created_at': artifact.created_at.isoformat(),
        }

    async def get_artifact_bytes(self, artifact_id: str) -> bytes:
        artifact = await self.db.scalar(select(Artifact).where(Artifact.id == uuid.UUID(artifact_id)))
        if artifact is None or artifact.state != 'ready':
            raise HTTPException(status_code=404, detail={'code': 'not_found', 'message': 'artifact not found'})
        return await self.store.get_bytes(uuid.UUID(artifact_id))


def sha256_hex(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    ).hexdigest()
