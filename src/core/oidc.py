'''OIDC identity stubs.

Production runtime: fail-closed. Token verification returns ``None`` unless a
verifier is explicitly configured, which never happens in production. Static
test tokens are never accepted by the runtime verifier.

Tests / local development only: :class:`OidcStubProvider` issues signed,
JWT-like stub tokens and verifies them using only the Python standard library
(no PyJWT/cryptography dependency). It is a test double, not a production
identity provider. No default credentials, no production keys, no live models.
'''

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Dict, Optional, Set

from src.core.security import UserContext

# Issuer for the local test IdP. Not a production authority; never used to
# issue tokens accepted outside test/dev override paths.
TEST_ISSUER = 'http://test-idp.local/oidc'

# Module-level verifier. None by default -> production fail-closed (verify_token
# returns None for every token). Configured only by tests via
# configure_oidc_verifier(). Never populated from production configuration.
_oidc_verifier: Optional['OidcStubProvider'] = None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign_payload(secret: str, payload: Dict) -> str:
    header = _b64url(b'{"alg":"HS256","typ":"JWT"}')
    body = _b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{header}.{body}'.encode('utf-8')
    sig = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    return f'{header}.{body}.{_b64url(sig)}'


def _unsign_token(secret: str, token: str) -> Dict:
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError('token must have three segments')
    header_b64, body_b64, sig_b64 = parts
    signing_input = f'{header_b64}.{body_b64}'.encode('utf-8')
    expected = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    provided = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected, provided):
        raise ValueError('signature verification failed')
    payload = json.loads(_b64url_decode(body_b64).decode('utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('token payload must be a JSON object')
    return payload


class OidcStubProvider:
    '''Local test OIDC identity provider.

    Issues signed stub tokens and verifies them. Intended exclusively for test
    and local-development use. Never used by the production runtime.
    '''

    def __init__(
        self,
        issuer: str = TEST_ISSUER,
        secret: Optional[str] = None,
    ):
        self.issuer = issuer
        # Test-only signing secret. Deliberately not a production credential.
        self._secret = secret or 'test-stub-secret-do-not-use-in-production'

    def issue_token(
        self,
        user_id: str,
        organization_id: str,
        org_role: str = 'member',
        project_roles: Optional[Dict[str, Set[str]]] = None,
        ttl_seconds: int = 3600,
    ) -> str:
        '''Issue a signed stub bearer token for a synthetic identity.'''
        now = int(time.time())
        payload: Dict = {
            'iss': self.issuer,
            'sub': str(user_id),
            'org': str(organization_id),
            'org_role': org_role,
            'project_roles': {
                str(k): sorted(v) for k, v in (project_roles or {}).items()
            },
            'iat': now,
            'exp': now + ttl_seconds,
            'jti': str(uuid.uuid4()),
        }
        return _sign_payload(self._secret, payload)

    def verify_token(self, token: str) -> Optional[UserContext]:
        '''Verify a stub token and return a :class:`UserContext`, or ``None``
        if the token is invalid, expired, or issued by a different issuer.'''
        try:
            payload = _unsign_token(self._secret, token)
        except ValueError:
            return None
        if payload.get('iss') != self.issuer:
            return None
        if int(time.time()) > int(payload.get('exp', 0)):
            return None
        return UserContext(
            user_id=str(payload['sub']),
            organization_id=str(payload['org']),
            org_role=str(payload.get('org_role', 'member')),
            project_roles={
                str(k): set(v) for k, v in payload.get('project_roles', {}).items()
            },
        )


def configure_oidc_verifier(provider: Optional[OidcStubProvider]) -> None:
    '''Test-only injection of an OIDC verifier.

    Call this only from test setup. Production never calls it, so the runtime
    verifier remains fail-closed.
    '''
    global _oidc_verifier
    _oidc_verifier = provider


def verify_token_via_oidc(token: str) -> Optional[UserContext]:
    '''Verify a bearer token through the configured OIDC verifier.

    Returns ``None`` when no verifier is configured (production fail-closed).
    '''
    if _oidc_verifier is None:
        return None
    return _oidc_verifier.verify_token(token)
