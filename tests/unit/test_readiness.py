"""Synthetic component readiness checks; these do not load or fit models."""
from __future__ import annotations

import numpy as np
import pytest

from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.inference.predictor import IDSPredictor as PipelinePredictor
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.provenance.windows_access import RealDataAuthorizationUnavailable
from iot_ids.runtime.engine import InferenceEngine, MLPModule
from iot_ids.runtime.predictor import IDSPredictor as RuntimePredictor


class IdentityPreprocessor:
    feature_names = list(CANONICAL_21_FEATURE_NAMES)

    def transform(self, frame):
        return frame.to_numpy(dtype=float)


class ProbabilityModel:
    classes_ = np.array([0, 1])
    n_features_in_ = 21

    def predict_proba(self, features):
        return np.tile([0.7, 0.3], (len(features), 1))


class MalformedModel:
    classes_ = np.array([0, "attack"], dtype=object)

    def predict_proba(self, features):
        return np.zeros((len(features), 2))


def make_pipeline(model=None, preprocessor=None, **kwargs):
    return IDSSystemPipeline(
        model=ProbabilityModel() if model is None else model,
        preprocessor=IdentityPreprocessor() if preprocessor is None else preprocessor,
        feature_profile="synthetic_readiness",
        feature_names=list(CANONICAL_21_FEATURE_NAMES),
        **kwargs,
    )


def test_pipeline_healthy_means_component_interfaces_only():
    pipeline = make_pipeline()
    health = pipeline.health_check()

    assert health["status"] == "HEALTHY"
    assert health["components"] == {
        "model": "READY", "preprocessor": "READY", "aligner": "READY", "threshold": "READY"
    }
    assert health["readiness_scope"] == "component_interface_and_configuration_only"
    assert health["model_training_state"] == "UNKNOWN"
    assert health["detection_performance_validated"] is False
    wrapped = PipelinePredictor(pipeline).health_check()
    assert wrapped["status"] == "HEALTHY"
    assert wrapped["readiness_scope"] == health["readiness_scope"]


@pytest.mark.parametrize("missing", ["model", "preprocessor"])
def test_pipeline_missing_required_component_is_not_ready(missing):
    pipeline = make_pipeline()
    setattr(pipeline, missing, None)

    health = pipeline.health_check()

    assert health["status"] == "NOT_READY"
    assert health["components"][missing] == "MISSING"
    assert missing in health["not_ready_reasons"]


def test_malformed_model_interface_and_feature_order_are_not_ready():
    health = make_pipeline(model=MalformedModel()).health_check()
    assert health["status"] == "NOT_READY"
    assert health["components"]["model"] == "INVALID"

    pipeline = make_pipeline()
    pipeline.preprocessor.feature_names = list(reversed(CANONICAL_21_FEATURE_NAMES))
    assert pipeline.health_check()["components"]["preprocessor"] == "INVALID"


def test_preprocessor_without_feature_order_metadata_is_unverified():
    class UnidentifiedPreprocessor:
        def transform(self, frame):
            return frame.to_numpy(dtype=float)

    health = make_pipeline(preprocessor=UnidentifiedPreprocessor()).health_check()
    assert health["status"] == "NOT_READY"
    assert health["components"]["preprocessor"] == "UNVERIFIED"


def test_invalid_threshold_configuration_is_rejected():
    with pytest.raises(ValueError, match="decision_threshold"):
        make_pipeline(decision_threshold=float("nan"))


def test_runtime_synthetic_health_does_not_claim_model_quality():
    engine = InferenceEngine.for_synthetic_components(
        preprocessor=IdentityPreprocessor(),
        rf_model=ProbabilityModel(),
        mlp_model=MLPModule(input_dim=21),
    )
    health = RuntimePredictor(engine).health_check()

    assert health["status"] == "HEALTHY"
    assert health["initialization_mode"] == "SYNTHETIC_IN_MEMORY_ONLY"
    assert health["model_training_state"] == "UNKNOWN"
    assert health["detection_performance_validated"] is False

    engine.rf_model = None
    not_ready = RuntimePredictor(engine).health_check()
    assert not_ready["status"] == "NOT_READY"
    assert not_ready["components"]["rf_model"] == "MISSING"


def test_checkpoint_backed_initialization_is_blocked_before_artifact_loader(monkeypatch):
    loader_called = False

    def forbidden_loader(self):
        nonlocal loader_called
        loader_called = True
        raise AssertionError("artifact loading must not be reached")

    monkeypatch.setattr(InferenceEngine, "_load_and_validate_artifacts", forbidden_loader)
    with pytest.raises(RealDataAuthorizationUnavailable):
        InferenceEngine(profile="standardized_21", dataset="AUTHORIZATION_REQUIRED_FIXTURE")
    assert loader_called is False
