'''FastAPI Application Entrypoint for Agent Flight Recorder.'''
import logging
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import asyncpg

from src.core.config import settings
from src.api.foundation import router as foundation_router
from src.api.afr import router as domain_router

logger = logging.getLogger('afr.api')

app = FastAPI(
    title='Agent Flight Recorder',
    description=(
        'Deterministic black-box recording, run inspection, side-effect sandboxing, '
        'and trace-to-regression test generator for autonomous AI agents.'
    ),
    version='0.2.0',
    docs_url='/docs',
    redoc_url='/redoc',
    openapi_url='/openapi.json',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    return response


def _problem(request: Request, status_code: int, code: str, title: str, detail: str):
    return JSONResponse(
        status_code=status_code,
        content={
            'type': 'https://datatracker.ietf.org/doc/html/rfc7807',
            'title': title,
            'status': status_code,
            'code': code,
            'detail': detail,
            'request_id': getattr(request.state, 'request_id', None),
            'instance': f'/errors/{getattr(request.state, "request_id", uuid.uuid4())}',
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error('Database error [request_id=%s]: %s', request.state.request_id, type(exc).__name__)
    return _problem(
        request, status.HTTP_503_SERVICE_UNAVAILABLE, 'unavailable',
        'Service Unavailable', 'The database is temporarily unavailable.',
    )


@app.exception_handler(OSError)
async def connection_error_handler(request: Request, exc: OSError):
    logger.error('Connection error [request_id=%s]: %s', request.state.request_id, type(exc).__name__)
    return _problem(
        request, status.HTTP_503_SERVICE_UNAVAILABLE, 'unavailable',
        'Service Unavailable', 'A required backend connection is temporarily unavailable.',
    )


@app.exception_handler(asyncpg.PostgresError)
async def postgres_error_handler(request: Request, exc: asyncpg.PostgresError):
    logger.error('Postgres error [request_id=%s]: %s', request.state.request_id, type(exc).__name__)
    return _problem(
        request, status.HTTP_503_SERVICE_UNAVAILABLE, 'unavailable',
        'Service Unavailable', 'The database is temporarily unavailable.',
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    logger.error('Unhandled error [error_id=%s][request_id=%s]', error_id, request.state.request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            'type': 'https://datatracker.ietf.org/doc/html/rfc7807',
            'title': 'Internal Server Error',
            'status': 500,
            'code': 'unavailable',
            'detail': (
                'An unexpected internal error occurred. Reference ID: ' + error_id
            ),
            'instance': f'/errors/{error_id}',
        },
    )


app.include_router(foundation_router, prefix='/api/v1', tags=['Foundation'])
app.include_router(domain_router, prefix='/api/v1', tags=['AFR Domain'])


@app.get('/healthz', tags=['Health'])
async def healthz():
    '''Service liveness probe.'''
    return {
        'status': 'pass',
        'service': 'agent-flight-recorder',
        'version': '0.2.0',
    }


@app.get('/', tags=['Root'])
async def root():
    return {
        'message': 'Welcome to Agent Flight Recorder API',
        'docs': '/docs',
        'health': '/healthz',
    }
