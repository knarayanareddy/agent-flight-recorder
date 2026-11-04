"""Contract and Schema Acceptance Tests.
Validates all JSON schemas in contracts/schemas against Draft 2020-12
and ensures positive fixtures pass and negative fixtures fail.
"""
from pathlib import Path
import json
import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "contracts/schemas"
EXAMPLES_DIR = ROOT / "contracts/examples"

SCHEMAS = {f.stem: json.loads(f.read_text()) for f in SCHEMAS_DIR.glob("*.json")}
REGISTRY = Registry().with_resources((s.get("$id", f"urn:{k}"), Resource.from_contents(s)) for k, s in SCHEMAS.items())


def get_validator(name: str):
    return Draft202012Validator(SCHEMAS[name], registry=REGISTRY, format_checker=FormatChecker())


@pytest.mark.parametrize("schema_name", sorted(SCHEMAS.keys()))
def test_schema_syntax_and_examples(schema_name: str):
    """Test schema validity and positive/negative examples."""
    schema = SCHEMAS[schema_name]
    Draft202012Validator.check_schema(schema)

    val = get_validator(schema_name)
    valid_file = EXAMPLES_DIR / f"{schema_name}.valid.json"
    invalid_file = EXAMPLES_DIR / f"{schema_name}.invalid.json"

    if valid_file.exists():
        data = json.loads(valid_file.read_text())
        val.validate(data)

    if invalid_file.exists():
        data = json.loads(invalid_file.read_text())
        errors = list(val.iter_errors(data))
        assert len(errors) > 0, f"Expected validation errors for negative example: {invalid_file.name}"


def test_endpoint_policy_operations():
    """Verify endpoint policy operations map to valid roles."""
    policy_file = ROOT / "contracts/endpoint-policy.json"
    assert policy_file.exists()
    policies = json.loads(policy_file.read_text())
    assert len(policies) > 0
    valid_roles = {"viewer", "analyst", "operator", "maintainer", "admin"}
    for p in policies:
        assert p["role"] in valid_roles
        assert "operation" in p
        assert "path" in p
