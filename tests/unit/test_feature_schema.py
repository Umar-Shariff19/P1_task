from __future__ import annotations

from pathlib import Path
import json
import pytest

from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.features.schema import (
    load_feature_schema,
    load_standardized_21_metadata,
    select_features,
)
from iot_ids.preprocessing.pipeline import get_model_feature_columns
from iot_ids.runtime.schema import STANDARDIZED_21_FEATURES


def test_feature_schema_levels_and_availability() -> None:
    features = load_feature_schema(Path("configs/features/canonical_schema.json"))
    names = {feature.name for feature in features}
    assert "duration" in names
    assert "src_bytes" in names
    common = select_features(features, levels={"common"})
    assert len(common) == 6
    assert all(feature.level == "common" for feature in common)
    temporal = select_features(features, levels={"temporal"})
    assert temporal
    assert all(feature.level == "temporal" for feature in temporal)
    cross_dataset = select_features(features, valid_for="cross_dataset")
    assert cross_dataset
    assert all(feature.valid_for in {"cross_dataset", "both"} for feature in cross_dataset)


def test_standardized_21_metadata_matches_extractor_and_runtime_order() -> None:
    features = load_standardized_21_metadata(
        Path("configs/features/standardized_21_metadata.json")
    )
    names = [feature.name for feature in features]

    assert len(features) == 21
    assert names == list(CANONICAL_21_FEATURE_NAMES)
    assert names == STANDARDIZED_21_FEATURES
    assert all(feature.dtype == "float64" for feature in features)
    assert all(feature.canonical_inputs for feature in features)
    assert all(feature.semantic_definition and feature.transformation for feature in features)
    assert sum(feature.level == "instant" for feature in features) == 11
    assert sum(feature.level == "temporal" for feature in features) == 5
    assert sum(feature.level == "behavioral" for feature in features) == 5


def test_legacy_profiles_remain_separate_and_metadata_scope_is_explicit() -> None:
    schema = json.loads(
        Path("configs/features/canonical_schema.json").read_text(encoding="utf-8")
    )
    profiles = schema["profiles"]
    standard_metadata = load_standardized_21_metadata(
        Path("configs/features/standardized_21_metadata.json")
    )

    assert len(profiles["F_COMMON"]) == 6
    assert len(profiles["IN_DOMAIN_EDGE_IIOT"]) == 13
    assert len(profiles["IN_DOMAIN_TON_IOT"]) == 13
    assert (
        get_model_feature_columns("Edge-IIoTset", profile="cross_domain")
        == profiles["F_COMMON"]
    )
    assert (
        get_model_feature_columns("Edge-IIoTset", profile="in_domain")
        == profiles["IN_DOMAIN_EDGE_IIOT"]
    )
    assert (
        get_model_feature_columns("ToN-IoT", profile="in_domain")
        == profiles["IN_DOMAIN_TON_IOT"]
    )
    assert profiles["STANDARDIZED_21_MULTILEVEL"] == [
        feature.name for feature in standard_metadata
    ]
    assert len(load_feature_schema(Path("configs/features/canonical_schema.json"))) == 11
    assert "not a complete metadata inventory" in schema["metadata_scope"]


def test_standardized_21_metadata_loader_rejects_wrong_profile(tmp_path) -> None:
    bad_metadata = tmp_path / "wrong_profile.json"
    bad_metadata.write_text('{"profile":"historical_13","features":[]}', encoding="utf-8")

    with pytest.raises(ValueError, match="STANDARDIZED_21"):
        load_standardized_21_metadata(bad_metadata)
