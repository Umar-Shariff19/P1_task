from __future__ import annotations

from pathlib import Path

from iot_ids.features.schema import load_feature_schema, select_features


def test_feature_schema_levels_and_availability() -> None:
    features = load_feature_schema(Path("configs/features/canonical_schema.json"))
    names = {feature.name for feature in features}
    assert "duration_seconds" in names
    assert "source_agg_*" in names
    instant = select_features(features, levels={"instant"})
    assert instant
    assert all(feature.level == "instant" for feature in instant)

