'''OIDC stub identity tests (B03).

The local test IdP (OidcStubProvider) issues signed stub tokens and verifies
them. Production runtime never configures a verifier, so verify_token() remains
fail-closed (returns None for every token). These tests exercise the stub in
isolation and through verify_token with explicit configure/unconfigure.
'''

import pytest
from src.core.oidc import (
    OidcStubProvider,
    TEST_ISSUER,
    configure_oidc_verifier,
    verify_token_via_oidc,
)
from src.core.security import verify_token


def test_oidc_stub_issues_and_verifies_stub_token(oidc_stub_provider):
    token = oidc_stub_provider.issue_token(
        user_id='user-1',
        organization_id='org-1',
        org_role='admin',
        project_roles={'proj-1': {'maintainer'}},
    )
    assert isinstance(token, str)
    assert token.count('.') == 2

    ctx = oidc_stub_provider.verify_token(token)
    assert ctx is not None
    assert ctx.user_id == 'user-1'
    assert ctx.organization_id == 'org-1'
    assert ctx.org_role == 'admin'
    assert ctx.has_project_capability('proj-1', 'maintainer')


def test_oidc_stub_rejects_tampered_token(oidc_stub_provider):
    token = oidc_stub_provider.issue_token(user_id='user-1', organization_id='org-1')
    tampered = token[:-5] + 'XXXXX'
    assert oidc_stub_provider.verify_token(tampered) is None


def test_oidc_stub_rejects_unknown_issuer_token(oidc_stub_provider):
    other = OidcStubProvider(issuer='http://other-idp.local/oidc')
    token = other.issue_token(user_id='user-1', organization_id='org-1')
    assert oidc_stub_provider.verify_token(token) is None


def test_oidc_stub_rejects_expired_token(oidc_stub_provider):
    token = oidc_stub_provider.issue_token(
        user_id='user-1', organization_id='org-1', ttl_seconds=-1
    )
    assert oidc_stub_provider.verify_token(token) is None


def test_oidc_stub_rejects_malformed_token(oidc_stub_provider):
    assert oidc_stub_provider.verify_token('not-a-token') is None
    assert oidc_stub_provider.verify_token('a.b') is None
    assert oidc_stub_provider.verify_token('') is None


def test_verify_token_production_fail_closed_without_verifier():
    '''With no OIDC verifier configured (production default), every token is
    rejected: static test tokens are never accepted.'''
    assert verify_token('Bearer test-token-admin') is None
    assert verify_token('Bearer test-token-maintainer') is None
    assert verify_token('Bearer nonsense') is None
    assert verify_token('') is None


def test_verify_token_via_oidc_when_configured(oidc_verifier, oidc_stub_provider):
    '''Through the explicitly configured OIDC verifier, a valid stub token
    resolves to a UserContext; the global verifier is reset after the test.'''
    token = oidc_stub_provider.issue_token(
        user_id='user-2', organization_id='org-2', org_role='member',
        project_roles={'proj-2': {'analyst'}},
    )
    ctx = verify_token_via_oidc(token)
    assert ctx is not None
    assert ctx.user_id == 'user-2'
    assert ctx.organization_id == 'org-2'
    assert ctx.has_project_capability('proj-2', 'analyst')


def test_verify_token_delegates_to_configured_verifier(oidc_verifier, oidc_stub_provider):
    '''verify_token() delegates to the configured OIDC verifier.'''
    token = oidc_stub_provider.issue_token(user_id='user-3', organization_id='org-3')
    assert verify_token(token) is not None
    assert verify_token('Bearer invalid.stub.token') is None


def test_verify_token_reset_after_test():
    '''The global OIDC verifier must be None after a test that used it, so
    production fail-closed behavior is preserved for subsequent tests.'''
    import src.core.oidc as oidc_mod

    assert oidc_mod._oidc_verifier is None

    provider = OidcStubProvider()
    configure_oidc_verifier(provider)
    try:
        assert oidc_mod._oidc_verifier is provider
        token = provider.issue_token(user_id='u', organization_id='o')
        assert verify_token(token) is not None
    finally:
        configure_oidc_verifier(None)

    assert oidc_mod._oidc_verifier is None
    assert verify_token('any-token') is None


def test_issuer_constant_is_test_only():
    assert TEST_ISSUER == 'http://test-idp.local/oidc'
    assert 'example.com' not in TEST_ISSUER
