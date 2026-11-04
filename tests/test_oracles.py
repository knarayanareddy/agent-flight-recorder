"""Independent Acceptance Tests against Reference Oracles for AFR."""
from reference.oracles import redact, EventOracle, recorded_match
import pytest
import copy

def test_metadata_redaction_removes_keys():
    bad = {"name": "test_tool", "api_key": "SECRET", "authorization": "Bearer SECRET", "outcome": "pass"}
    cleaned = redact(bad)
    assert "api_key" not in cleaned
    assert "authorization" not in cleaned
    assert cleaned["name"] == "test_tool"

def test_event_oracle_deduplication():
    oracle = EventOracle()
    ev1 = {
        "event_id": "00000000-0000-4000-8000-000000000001",
        "run_id": "00000000-0000-4000-8000-000000000002",
        "producer_id": "producer-1",
        "producer_seq": 1,
        "payload": {"action": "step"}
    }
    res = oracle.batch("proj-1", [ev1])
    assert ev1["event_id"] in res["accepted"]
    
    # Duplicate with same hash should be recognized as duplicate
    res2 = oracle.batch("proj-1", [ev1])
    assert ev1["event_id"] in res2["duplicates"]
    
    # Conflicting payload for same event_id must raise error
    ev_conflict = copy.deepcopy(ev1)
    ev_conflict["payload"] = {"action": "tampered"}
    with pytest.raises(ValueError):
        oracle.batch("proj-1", [ev_conflict])
