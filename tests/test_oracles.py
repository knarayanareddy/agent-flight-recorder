"""Independent Acceptance Tests against Reference Oracles for AFR."""
from reference.oracles import redact, EventOracle, recorded_match, archive_entries
import pytest
import copy

def test_metadata_capture_redacts_credentials():
    meta = {
        'name': 'search_tool',
        'api_key': 'CANARY_KEY',
        'authorization': 'Bearer CANARY',
        'reason': 'CANARY',
        'input_tokens': 120,
        'output_tokens': 45,
        'client': {'api_key': 'CANARY'}
    }
    redacted = redact(meta)
    assert 'api_key' not in redacted
    assert 'authorization' not in redacted
    assert 'reason' not in redacted
    assert 'client' not in redacted
    assert redacted['name'] == 'search_tool'
    assert redacted['input_tokens'] == 120

def test_event_oracle_atomic_batch_and_duplicates():
    oracle = EventOracle()
    ev = {
        'event_id': '00000000-0000-4000-8000-000000000001',
        'run_id': '00000000-0000-4000-8000-000000000002',
        'producer_id': 'agent-1',
        'producer_seq': 0,
        'payload': {'step': 'init'}
    }
    b1 = oracle.batch('proj-1', [ev])
    assert len(b1['accepted']) == 1
    assert len(b1['duplicates']) == 0
    
    b2 = oracle.batch('proj-1', [ev])
    assert len(b2['accepted']) == 0
    assert b2['duplicates'] == [ev['event_id']]
    
    tampered = copy.deepcopy(ev)
    tampered['payload'] = {'step': 'tampered'}
    with pytest.raises(ValueError):
        oracle.batch('proj-1', [tampered])

def test_recorded_matching_no_live_fallback():
    records = [{'tool': 'fetch', 'contract_hash': 'a'*64, 'args': {'url': 'https://example.com'}, 'ordinal': 0, 'output': {'status': 200}}]
    res = recorded_match(records, 'fetch', 'a'*64, {'url': 'https://example.com'}, 0)
    assert res == {'status': 200}
    
    with pytest.raises(ValueError):
        recorded_match(records, 'fetch', 'a'*64, {'url': 'https://other.com'}, 0)
