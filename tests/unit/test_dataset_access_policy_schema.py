"""Schema-only tests for the non-authorizing owner policy draft example."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


_IMPLEMENTATION = Path(__file__).parents[2] / "results" / "implementation"
_SCHEMA_PATH = _IMPLEMENTATION / "dataset_access_policy.schema.json"
_EXAMPLE_PATH = _IMPLEMENTATION / "dataset_access_policy.example.json"


def _load_inputs() -> tuple[dict, dict]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    example = json.loads(_EXAMPLE_PATH.read_text(encoding="utf-8"))
    return schema, example


def test_draft_example_is_valid_but_explicitly_non_authorizing() -> None:
    schema, example = _load_inputs()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(example)
    assert example["status"] == "DRAFT"
    assert example["example_only"] is True
    assert example["policy_approval"] is None
    assert all(item["approved_root"] is None for item in example["datasets"].values())
    assert all(item["approval"] is None for item in example["datasets"].values())


def test_draft_example_cannot_become_active_by_changing_status_alone() -> None:
    schema, example = _load_inputs()
    active = copy.deepcopy(example)
    active["status"] = "ACTIVE"
    active["example_only"] = False
    errors = list(Draft202012Validator(schema).iter_errors(active))
    assert errors
    assert any(error.validator in {"type", "minItems", "required"} for error in errors)


def test_unknown_policy_fields_fail_closed() -> None:
    schema, example = _load_inputs()
    example["trust_me"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(example)
