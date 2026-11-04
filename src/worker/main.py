'''AFR replay worker entry point.

Usage: WORKER_PROJECT_SCOPES="<uuid>,<uuid>" python -m src.worker.main
Runs until SIGTERM; intended for container restart on failure (no daemonization).
'''

import asyncio
import logging
import os
import sys
import uuid

from src.worker.replay_worker import ReplayWorker

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format='%(asctime)s %(levelname)s %(name)s: %(message)s')


def _project_scopes() -> list[uuid.UUID]:
    raw = os.getenv('WORKER_PROJECT_SCOPES', '')
    scopes = []
    for token in raw.split(','):
        token = token.strip()
        if not token:
            continue
        scopes.append(uuid.UUID(token))
    return scopes


async def amain() -> None:
    worker = ReplayWorker(project_scopes=_project_scopes())
    loop = asyncio.get_running_loop()
    for sig in ('SIGTERM', 'SIGINT'):
        try:
            loop.add_signal_handler(getattr(__import__('signal'), sig), worker.stop)
        except NotImplementedError:  # pragma: no cover - Windows
            pass
    await worker.run()


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
