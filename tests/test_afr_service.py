'''Pure unit tests for AFR service logic (no database required).

Covers baseline-json/1 canonicalization, RFC 6901 pointer resolution, type-aware
equality, check evaluation (json_equals / forbidden_tool / mock_state_equals),
metadata redaction, and deterministic capture policy IDs.
'''
import copy
import pytest

from src.services.afr import (
    ALLOWED_CHECK_KINDS,
    canonical_json,
    digest_of,
    deterministic_capture_policy_id,
    normalize_event_envelope,
    sha256_hex,
    _evaluate_check,
    _json_equal,
    _json_pointer_get,
    _validate_json_pointer,
)


def test_canonical_json_is_deterministic_and_compact():
    value = {'b': 2, 'a': {'z': 1, 'y': [2, 1]}}
    out = canonical_json(value)
    assert out == b'{"a":{"y":[2,1],"z":1},"b":2}'
    assert canonical_json(value) == canonical_json(copy.deepcopy(value))


def test_canonical_json_rejects_nan():
    with pytest.raises(ValueError):
        canonical_json({'x': float('nan')})


def test_sha256_digest_matches_oracle_shape():
    digest = sha256_hex({'name': 'tool', 'outcome': 'success'})
    assert len(digest) == 64
    assert all(c in '0123456789abcdef' for c in digest)


def test_capture_policy_is_deterministic_per_project():
    p1 = deterministic_capture_policy_id('00000000-0000-4000-8000-000000000001')
    p2 = deterministic_capture_policy_id('00000000-0000-4000-8000-000000000002')
    assert p1 == deterministic_capture_policy_id('00000000-0000-4000-8000-000000000001')
    assert p1 != p2
    import uuid
    assert uuid.UUID(p1) == uuid.uuid5(uuid.UUID('00000000-0000-4000-8000-000000000001'), 'metadata_only:v1')


def test_metadata_redaction_drops_credentials_and_free_text():
    meta = {
        'name': 'search_tool',
        'api_key': 'CANARY_KEY',
        'authorization': 'Bearer CANARY',
        'reason': 'CANARY',
        'input_tokens': 120,
        'output_tokens': 45,
        'client': {'api_key': 'CANARY'},
        'redacted': True,
    }
    redacted = normalize_event_envelope({'payload': meta})['payload']
    assert redacted == {'name': 'search_tool', 'input_tokens': 120, 'output_tokens': 45, 'redacted': True}


def test_normalize_event_requires_dict_payload():
    with pytest.raises(ValueError):
        normalize_event_envelope({'payload': 'not-an-object'})


@pytest.mark.parametrize('pointer', ['', '/a', '/a/0/b', '/a~1b/0', '/a~0b'])
def test_json_pointer_valid_escapes(pointer):
    _validate_json_pointer(pointer)


def test_json_pointer_invalid():
    with pytest.raises(ValueError):
        _validate_json_pointer('relative')
    with pytest.raises(ValueError):
        _validate_json_pointer('a/b')


def test_json_pointer_get_resolves_arrays_and_objects():
    doc = {'a': [{'b': 1}, 2], 'c': {'d/e': 3}}
    assert _json_pointer_get(doc, '/a/0/b') == 1
    assert _json_pointer_get(doc, '/a/1') == 2
    assert _json_pointer_get(doc, '/c/d~1e') == 3
    assert _json_pointer_get(doc, '') == doc


def test_json_pointer_get_missing_raises():
    doc = {'a': [1, 2]}
    with pytest.raises(KeyError):
        _json_pointer_get(doc, '/a/5')
    with pytest.raises(KeyError):
        _json_pointer_get(doc, '/missing')


def test_json_equal_is_type_aware():
    assert _json_equal(1, 1)
    assert _json_equal(True, True)
    assert not _json_equal(1, True)
    assert not _json_equal(True, 1)
    assert _json_equal({'x': 1}, {'x': 1})
    assert not _json_equal({'x': 1}, {'x': 2})
    assert _json_equal([1, 'a'], [1, 'a'])
    assert not _json_equal(None, 0)


def test_check_evaluation_json_equals():
    check = {'kind': 'json_equals', 'path': '/ok', 'expected': True}
    outcome, reason = _evaluate_check(check, {'ok': True}, {}, [])
    assert outcome == 'pass'
    outcome, reason = _evaluate_check(check, {'ok': False}, {}, [])
    assert outcome == 'fail'
    outcome, reason = _evaluate_check(check, {}, {}, [])
    assert outcome == 'fail'
    assert 'not present' in reason


def test_check_evaluation_mock_state_equals():
    check = {'kind': 'mock_state_equals', 'path': '/balance', 'expected': 0}
    outcome, reason = _evaluate_check(check, {}, {'balance': 0}, [])
    assert outcome == 'pass'
    outcome, _ = _evaluate_check(check, {}, {'balance': 1}, [])
    assert outcome == 'fail'


def test_check_evaluation_forbidden_tool():
    check = {'kind': 'forbidden_tool', 'path': '', 'expected': 'network.fetch'}
    outcome, reason = _evaluate_check(check, {}, {}, [{'tool': 'fs.read'}])
    assert outcome == 'pass'
    outcome, _ = _evaluate_check(check, {}, {}, [{'tool': 'network.fetch'}])
    assert outcome == 'fail'


def test_check_evaluation_forbidden_tool_requires_empty_path():
    check = {'kind': 'forbidden_tool', 'path': '/x', 'expected': 'tool'}
    outcome, reason = _evaluate_check(check, {}, {}, [])
    assert outcome == 'error'


def test_allowed_check_kinds_frozen():
    assert ALLOWED_CHECK_KINDS == {'json_equals', 'forbidden_tool', 'mock_state_equals'}


def test_event_digest_stable_across_key_order():
    e1 = {'payload': {'b': 2, 'a': 1}}
    e2 = {'payload': {'a': 1, 'b': 2}}
    assert digest_of(e1) == digest_of(e2)
    e3 = {'payload': {'b': 2, 'a': 2}}
    assert digest_of(e1) != digest_of(e3)
