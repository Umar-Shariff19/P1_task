from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

FeatureLevel = Literal["common", "instant", "temporal", "behavioral"]
FeatureValidity = Literal["cross_dataset", "in_domain", "both"]


@dataclass(frozen=True, slots=True)
class CanonicalFeature:
    name: str
    dtype: str
    level: FeatureLevel
    semantic_definition: str
    units: str | None
    transformation: str
    availability: dict[str, list[str]]
    missing_behavior: str
    leakage_role: str
    valid_for: FeatureValidity


@dataclass(frozen=True, slots=True)
class RuntimeFeatureMetadata:
    """Code-level metadata for the operational standardized 21-feature profile.

    This deliberately omits dataset availability and scientific-validity labels;
    those are not established by the CanonicalFlow extractor alone.
    """

    name: str
    dtype: str
    level: FeatureLevel
    canonical_inputs: list[str]
    semantic_definition: str
    units: str | None
    transformation: str
    missing_behavior: str


def load_feature_schema(path: str | Path) -> list[CanonicalFeature]:
    """Load the existing shared-feature metadata records.

    This legacy registry is distinct from the named profile arrays and is not
    guaranteed to contain metadata for every feature in those profiles.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [CanonicalFeature(**item) for item in payload["features"]]


def load_standardized_21_metadata(path: str | Path) -> list[RuntimeFeatureMetadata]:
    """Load complete code-level metadata for the standardized runtime profile."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("profile") != "STANDARDIZED_21":
        raise ValueError("Runtime feature metadata must declare profile 'STANDARDIZED_21'.")
    entries = payload.get("features")
    if not isinstance(entries, list) or len(entries) != 21:
        raise ValueError("STANDARDIZED_21 metadata must contain exactly 21 feature records.")
    try:
        features = [RuntimeFeatureMetadata(**item) for item in entries]
    except (TypeError, ValueError) as exc:
        raise ValueError("STANDARDIZED_21 metadata contains an invalid feature record.") from exc
    names = [feature.name for feature in features]
    if any(not isinstance(name, str) or not name.strip() for name in names) or len(set(names)) != 21:
        raise ValueError("STANDARDIZED_21 metadata names must be unique, non-empty strings.")
    for feature in features:
        if (
            feature.dtype != "float64"
            or not isinstance(feature.level, str)
            or feature.level not in ("instant", "temporal", "behavioral")
            or not isinstance(feature.canonical_inputs, list)
            or not feature.canonical_inputs
            or any(
                not isinstance(item, str) or not item.strip()
                for item in feature.canonical_inputs
            )
            or not isinstance(feature.semantic_definition, str)
            or not feature.semantic_definition.strip()
            or (feature.units is not None and not isinstance(feature.units, str))
            or not isinstance(feature.transformation, str)
            or not feature.transformation.strip()
            or not isinstance(feature.missing_behavior, str)
            or not feature.missing_behavior.strip()
        ):
            raise ValueError("STANDARDIZED_21 metadata contains incomplete or unsupported fields.")
    return features


def select_features(
    features: list[CanonicalFeature],
    levels: set[FeatureLevel] | None = None,
    valid_for: FeatureValidity | None = None,
) -> list[CanonicalFeature]:
    selected = features
    if levels is not None:
        selected = [feature for feature in selected if feature.level in levels]
    if valid_for is not None:
        selected = [
            feature
            for feature in selected
            if feature.valid_for == valid_for or feature.valid_for == "both"
        ]
    return selected

