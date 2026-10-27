"""Fail-closed validation for prospective experiment manifest structure.

Validation checks a JSON document against the repository's declared schema.
It does not authenticate approval references, establish that an experiment
ran, or verify any recorded claim against external evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from pathlib import Path
from typing import Any


_REPOSITORY_ROOT = Path(__file__).parent.parent.parent.parent
MANIFEST_SCHEMA_PATH = (
    _REPOSITORY_ROOT / "results" / "provenance" / "experiment_manifest.schema.json"
)
_DRAFT_2020_12_URI = "https://json-schema.org/draft/2020-12/schema"
_REFERENCE_KEYWORDS = {"$ref", "$dynamicRef", "$recursiveRef"}


class ManifestValidationError(ValueError):
    """Raised when the schema is unavailable/invalid or a manifest is invalid."""


class ManifestValidatorUnavailable(RuntimeError):
    """Raised when the required local JSON Schema validator is unavailable."""


@dataclass(frozen=True)
class ManifestValidationResult:
    """Successful structural validation, explicitly separated from evidence."""

    schema_valid: bool
    authorization_verified: bool = False
    evidence_truth_verified: bool = False


def _contains_reference_keyword(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in _REFERENCE_KEYWORDS or _contains_reference_keyword(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_reference_keyword(child) for child in value)
    return False


def validate_manifest(manifest: Any) -> ManifestValidationResult:
    """Validate a prospective manifest against the declared Draft 2020-12 schema.

    The canonical repository schema is selected internally so ordinary callers
    cannot silently validate against a weaker alternate schema. A valid
    authorization-reference field is treated as opaque text.
    """
    try:
        jsonschema = importlib.import_module("jsonschema")
    except ImportError as exc:
        raise ManifestValidatorUnavailable(
            "jsonschema is required for manifest validation; refusing to skip validation"
        ) from exc

    target = MANIFEST_SCHEMA_PATH
    try:
        with target.open("r", encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(
            "canonical experiment manifest schema is unavailable or invalid"
        ) from exc

    if not isinstance(schema, dict) or schema.get("$schema") != _DRAFT_2020_12_URI:
        raise ManifestValidationError("manifest schema dialect is missing or unsupported")
    if _contains_reference_keyword(schema):
        raise ManifestValidationError(
            "manifest schema references are unsupported; refusing external resolution"
        )

    try:
        validator_type = jsonschema.Draft202012Validator
        validator_type.check_schema(schema)
        validator = validator_type(
            schema, format_checker=jsonschema.FormatChecker()
        )
        errors = sorted(
            validator.iter_errors(manifest),
            key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
        )
    except Exception as exc:
        raise ManifestValidationError("manifest schema could not be applied safely") from exc

    if errors:
        safe_details = []
        for error in errors:
            path = "/".join(str(part) for part in error.absolute_path) or "<root>"
            detail = f"{path}: violates {error.validator or 'schema'} constraint"
            if error.validator == "required" and isinstance(error.instance, dict):
                missing = sorted(set(error.validator_value) - set(error.instance))
                if missing:
                    detail += f" (missing: {', '.join(missing)})"
            safe_details.append(detail)
        details = "; ".join(safe_details)
        raise ManifestValidationError(f"manifest does not satisfy schema: {details}")

    return ManifestValidationResult(schema_valid=True)


def validate_manifest_json(serialized_manifest: str | bytes) -> ManifestValidationResult:
    """Parse and validate JSON text without opening a caller-selected file path."""
    try:
        manifest = json.loads(serialized_manifest)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise ManifestValidationError("manifest JSON is malformed") from exc
    return validate_manifest(manifest)
