"""Synthetic-only tests for prospective manifest validation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile

import pytest

from iot_ids.provenance import (
    ManifestValidationError,
    ManifestValidatorUnavailable,
    validate_manifest,
    validate_manifest_json,
)
import iot_ids.provenance.manifest_validation as manifest_validation


_REPO_ROOT = Path(__file__).parents[2]
_EXAMPLES_PATH = _REPO_ROOT / "results" / "provenance" / "experiment_manifest_schema_examples.json"


def _positive_example() -> dict:
    examples = json.loads(_EXAMPLES_PATH.read_text(encoding="utf-8"))
    return examples["positive"]


def _temp_directory() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix=".synthetic-manifest-", dir=_REPO_ROOT)


def test_valid_synthetic_manifest_is_only_structurally_valid() -> None:
    result = validate_manifest(_positive_example())
    assert result.schema_valid is True
    assert result.authorization_verified is False
    assert result.evidence_truth_verified is False


def test_missing_required_provenance_field_is_rejected() -> None:
    manifest = _positive_example()
    del manifest["source"]["revision"]
    with pytest.raises(ManifestValidationError, match="revision"):
        validate_manifest(manifest)


@pytest.mark.parametrize("serialized", ["{bad json", b"\xff\xfe", 42])
def test_malformed_manifest_json_is_rejected_cleanly(serialized: object) -> None:
    with pytest.raises(ManifestValidationError, match="manifest JSON is malformed"):
        validate_manifest_json(serialized)  # type: ignore[arg-type]


def test_non_object_json_root_is_rejected_by_schema() -> None:
    with pytest.raises(ManifestValidationError, match="does not satisfy schema"):
        validate_manifest_json("[]")


def test_unknown_manifest_field_is_rejected_by_canonical_schema() -> None:
    manifest = _positive_example()
    manifest["unrecognized_field"] = "not silently accepted"
    with pytest.raises(ManifestValidationError, match="additionalProperties"):
        validate_manifest(manifest)


def test_all_documented_negative_schema_examples_are_rejected() -> None:
    examples = json.loads(_EXAMPLES_PATH.read_text(encoding="utf-8"))

    def remove_path(document: dict, dotted_path: str) -> None:
        parts = dotted_path.split(".")
        parent = document
        for part in parts[:-1]:
            parent = parent[int(part)] if isinstance(parent, list) else parent[part]
        final = parts[-1]
        if isinstance(parent, list):
            del parent[int(final)]
        else:
            del parent[final]

    for mutation in examples["negative_mutations"]:
        manifest = copy.deepcopy(examples["positive"])
        for path in mutation["remove"]:
            remove_path(manifest, path)
        with pytest.raises(ManifestValidationError):
            validate_manifest(manifest)


def test_populated_authorization_reference_does_not_establish_authorization() -> None:
    manifest = _positive_example()
    manifest["datasets"][0]["authorization_reference"] = "synthetic-not-an-approval"
    result = validate_manifest(manifest)
    assert result.schema_valid is True
    assert result.authorization_verified is False


def test_missing_schema_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with _temp_directory() as temp_dir:
        missing_schema = Path(temp_dir) / "missing-schema.json"
        monkeypatch.setattr(manifest_validation, "MANIFEST_SCHEMA_PATH", missing_schema)
        with pytest.raises(ManifestValidationError, match="schema is unavailable"):
            validate_manifest(_positive_example())


def test_invalid_schema_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with _temp_directory() as temp_dir:
        invalid_schema = Path(temp_dir) / "invalid-schema.json"
        invalid_schema.write_text(
            '{"$schema": "https://json-schema.org/draft/2020-12/schema", '
            '"type": "not-a-json-schema-type"}',
            encoding="utf-8",
        )
        monkeypatch.setattr(manifest_validation, "MANIFEST_SCHEMA_PATH", invalid_schema)
        with pytest.raises(ManifestValidationError, match="could not be applied safely"):
            validate_manifest(_positive_example())


@pytest.mark.parametrize(
    "schema_text",
    [
        '{"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "https://example.invalid/schema.json"}',
        '{"$schema": "https://json-schema.org/draft/2019-09/schema", "type": "object"}',
    ],
)
def test_unsupported_schema_reference_or_dialect_fails_closed(
    monkeypatch: pytest.MonkeyPatch, schema_text: str
) -> None:
    with _temp_directory() as temp_dir:
        custom_schema = Path(temp_dir) / "unsupported-schema.json"
        custom_schema.write_text(schema_text, encoding="utf-8")
        monkeypatch.setattr(manifest_validation, "MANIFEST_SCHEMA_PATH", custom_schema)
        with pytest.raises(ManifestValidationError, match="schema (references|dialect)"):
            validate_manifest(_positive_example())


def test_missing_validator_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import_module = manifest_validation.importlib.import_module

    def unavailable(name: str):
        if name == "jsonschema":
            raise ImportError("synthetic missing validator")
        return original_import_module(name)

    monkeypatch.setattr(manifest_validation.importlib, "import_module", unavailable)
    with pytest.raises(ManifestValidatorUnavailable, match="refusing to skip"):
        validate_manifest(_positive_example())


def test_synthetic_manifest_and_result_are_preserved_together() -> None:
    manifest = copy.deepcopy(_positive_example())
    manifest["experiment_id"] = "synthetic-provenance-fixture-only"
    manifest["source"]["revision"] = "0000000000000000000000000000000000000000"
    manifest["source"]["working_tree_dirty"] = False
    manifest["source"].pop("diff_record_id")
    manifest["datasets"][0]["authorization_reference"] = "synthetic-not-an-approval"
    manifest["metrics"][0].update(
        name="synthetic_arithmetic_check",
        definition="fixed synthetic arithmetic fixture value; not IDS performance",
        value=0.25,
    )
    synthetic_result = {
        "fixture_status": "SYNTHETIC_ONLY_NOT_AN_IDS_EXPERIMENT",
        "metric": {"name": "synthetic_arithmetic_check", "value": 0.25},
    }
    run_assessment = {
        "schema_status": "VALID",
        "authorization_status": "NOT_AUTHORIZED",
        "evidence_truth_status": "UNVERIFIED",
        "reason": "synthetic fixture; the schema does not authenticate approval references",
    }
    incomplete_manifest = copy.deepcopy(manifest)
    del incomplete_manifest["datasets"][0]["split_id"]

    with _temp_directory() as temp_dir:
        output = Path(temp_dir)
        manifest_path = output / "experiment_manifest.json"
        result_path = output / "synthetic_result.json"
        assessment_path = output / "run_assessment.json"
        invalid_path = output / "incomplete_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        result_path.write_text(json.dumps(synthetic_result, indent=2), encoding="utf-8")
        assessment_path.write_text(json.dumps(run_assessment, indent=2), encoding="utf-8")
        invalid_path.write_text(json.dumps(incomplete_manifest, indent=2), encoding="utf-8")

        validated = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
        stored_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        stored_result = json.loads(result_path.read_text(encoding="utf-8"))
        stored_assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        assert validated.schema_valid
        assert stored_result["fixture_status"] == "SYNTHETIC_ONLY_NOT_AN_IDS_EXPERIMENT"
        assert stored_manifest["metrics"][0]["value"] == stored_result["metric"]["value"]
        assert stored_assessment["schema_status"] == "VALID"
        assert stored_assessment["authorization_status"] == "NOT_AUTHORIZED"
        assert stored_assessment["evidence_truth_status"] == "UNVERIFIED"
        assert manifest_path.exists() and result_path.exists()
        with pytest.raises(ManifestValidationError, match="split_id"):
            validate_manifest(json.loads(invalid_path.read_text(encoding="utf-8")))
