"""End-to-End Integration Tests for Multi-Level Operational Pipeline.

Verifies raw telemetry -> FlowAggregator -> 18-feature extraction -> Preprocessor ->
Model inference -> Threshold decision -> Structured alert output, including save/load round-trips.
"""
import json
import tempfile
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from iot_ids.data.flow_object import CanonicalFlow
from iot_ids.features.canonical.flow_builder import CANONICAL_18_FEATURE_NAMES
from iot_ids.experiments.preprocessing import FeaturePreprocessor
from iot_ids.experiments.evaluator import evaluate_predictions
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.runtime import STANDARDIZED_21_FEATURES
from iot_ids.registry.manager import ModelRegistry
from iot_ids.inference.predictor import IDSPredictor


@pytest.fixture
def trained_pipeline():
    """Creates a small, deterministic IDSSystemPipeline fixture."""
    np.random.seed(42)
    n_samples = 50
    df_train = pd.DataFrame(
        np.random.rand(n_samples, len(CANONICAL_18_FEATURE_NAMES)),
        columns=CANONICAL_18_FEATURE_NAMES
    )
    df_train["proto_tcp"] = 1.0
    df_train["proto_udp"] = 0.0
    df_train["proto_icmp"] = 0.0
    df_train["proto_other"] = 0.0

    y_train = np.random.randint(0, 2, size=n_samples)

    preprocessor = FeaturePreprocessor(feature_names=CANONICAL_18_FEATURE_NAMES)
    X_train_proc = preprocessor.fit_transform(df_train)

    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train_proc, y_train)

    pipeline = IDSSystemPipeline(
        model=model,
        preprocessor=preprocessor,
        feature_profile="full_multilevel",
        decision_threshold=0.5,
    )
    return pipeline


def create_sample_flow(timestamp=100.0, dst_host="10.0.0.1", label=0):
    return CanonicalFlow(
        timestamp_start=timestamp,
        timestamp_end=timestamp + 1.5,
        src_host="192.168.1.10",
        dst_host=dst_host,
        src_port=12345,
        dst_port=80,
        protocol="tcp",
        bytes_src=200,
        bytes_dst=400,
        pkts_src=5,
        pkts_dst=4,
        syn_count_src=1,
        ack_count_src=1,
        rst_count_src=0,
        conn_state_code=0,
        label=label,
        attack_category="Normal" if label == 0 else "DDoS",
    )


def test_e2e_normal_flow_inference(trained_pipeline):
    """Verifies flow -> 18 features -> preprocessor -> model -> alert dict."""
    flow = create_sample_flow()
    res = trained_pipeline.process_flow(flow)

    assert "prediction_prob" in res
    assert "is_anomaly" in res
    assert "risk_score" in res
    assert "risk_level" in res
    assert res["feature_profile"] == "full_multilevel"
    assert 0.0 <= res["prediction_prob"] <= 1.0
    assert isinstance(res["is_anomaly"], bool)


def test_e2e_stateful_feature_evolution_and_reset(trained_pipeline):
    """Verifies temporal/behavioral features evolve across flows and reset cleanly."""
    trained_pipeline.reset_state()
    
    flow1 = create_sample_flow(timestamp=10.0, dst_host="10.0.0.1")
    flow2 = create_sample_flow(timestamp=12.0, dst_host="10.0.0.2")

    res1 = trained_pipeline.process_flow(flow1)
    res2 = trained_pipeline.process_flow(flow2)

    # Destination diversity should increase with new destination host
    div1 = res1["raw_features"]["behavioral_dst_diversity"]
    div2 = res2["raw_features"]["behavioral_dst_diversity"]
    assert div2 >= div1

    # Reset state and process flow1 again
    trained_pipeline.reset_state()
    res1_after_reset = trained_pipeline.process_flow(flow1)
    assert res1_after_reset["raw_features"]["behavioral_dst_diversity"] == div1


def test_e2e_save_load_registry_roundtrip(trained_pipeline):
    """Verifies pipeline save -> load -> predictor roundtrip reproducibility."""
    flow = create_sample_flow()
    res_orig = trained_pipeline.process_flow(flow)

    with tempfile.TemporaryDirectory() as tmp_dir:
        save_path = Path(tmp_dir) / "pipeline_artifact"
        ModelRegistry.save_pipeline(trained_pipeline, save_path, metadata={"version": "1.0"})

        # Instantiate predictor from saved artifact
        predictor = IDSPredictor.from_artifact(save_path)
        predictor.reset_state()
        
        res_loaded = predictor.predict_flow(flow)

        assert np.isclose(res_orig["prediction_prob"], res_loaded["prediction_prob"])
        assert res_orig["is_anomaly"] == res_loaded["is_anomaly"]
        assert res_orig["risk_level"] == res_loaded["risk_level"]


def test_e2e_batch_dataframe_inference(trained_pipeline):
    """Verifies batch inference over DataFrame input."""
    df_flows = pd.DataFrame([
        {"timestamp_start": 100.0, "timestamp_end": 101.0, "src_host": "192.168.1.1", "dst_host": "10.0.0.1", "src_port": 1234, "dst_port": 80, "protocol": "tcp", "bytes_src": 100, "bytes_dst": 100, "pkts_src": 2, "pkts_dst": 2, "syn_count_src": 1, "ack_count_src": 1, "rst_count_src": 0, "conn_state_code": 0, "label": 0, "attack_category": "Normal"},
        {"timestamp_start": 102.0, "timestamp_end": 103.0, "src_host": "192.168.1.2", "dst_host": "10.0.0.2", "src_port": 1235, "dst_port": 80, "protocol": "tcp", "bytes_src": 200, "bytes_dst": 200, "pkts_src": 3, "pkts_dst": 3, "syn_count_src": 1, "ack_count_src": 1, "rst_count_src": 0, "conn_state_code": 0, "label": 0, "attack_category": "Normal"},
    ])
    results = trained_pipeline.process_dataframe(df_flows)
    assert len(results) == 2
    assert results[0]["src_ip"] == "192.168.1.1"
    assert results[1]["src_ip"] == "192.168.1.2"


def test_e2e_deterministic_inference(trained_pipeline):
    """Verifies identical inputs yield deterministic probability and risk scores."""
    flow = create_sample_flow()
    
    trained_pipeline.reset_state()
    res1 = trained_pipeline.process_flow(flow)
    
    trained_pipeline.reset_state()
    res2 = trained_pipeline.process_flow(flow)

    assert res1["prediction_prob"] == res2["prediction_prob"]
    assert res1["risk_score"] == res2["risk_score"]


class _IdentityPreprocessor:
    def transform(self, frame):
        return frame.to_numpy(dtype=float)


class _ReverseClassProbabilityModel:
    classes_ = np.array([1, 0])

    def predict_proba(self, features):
        self.last_features = np.asarray(features).copy()
        return np.tile(np.array([[0.8, 0.2]]), (len(features), 1))


class _SyntheticThresholdModel:
    classes_ = np.array([1, 0])

    def predict_proba(self, features):
        values = np.asarray(features, dtype=float)
        self.last_features = values.copy()
        positive_probability = np.where(values[:, 0] > 0.0, 0.9, 0.1)
        return np.column_stack((positive_probability, 1.0 - positive_probability))


def _pipeline_with_test_model(model, feature_names=None):
    return IDSSystemPipeline(
        model=model,
        preprocessor=_IdentityPreprocessor(),
        feature_profile="synthetic_test",
        feature_names=list(feature_names or CANONICAL_18_FEATURE_NAMES),
    )


def test_batch_inference_uses_declared_positive_class_and_canonical_feature_order():
    model = _ReverseClassProbabilityModel()
    pipeline = _pipeline_with_test_model(model)
    values = np.arange(len(CANONICAL_18_FEATURE_NAMES), dtype=float)
    frame = pd.DataFrame(
        [dict(zip(CANONICAL_18_FEATURE_NAMES, values))],
        columns=list(reversed(CANONICAL_18_FEATURE_NAMES)),
    )

    alerts = pipeline.process_dataframe(frame)

    assert model.last_features.tolist() == [values.tolist()]
    assert alerts[0]["prediction_prob"] == pytest.approx(0.8)


def test_batch_inference_preserves_configured_feature_subset():
    model = _ReverseClassProbabilityModel()
    selected_features = list(CANONICAL_18_FEATURE_NAMES[:10])
    pipeline = _pipeline_with_test_model(model, feature_names=selected_features)
    values = np.arange(len(CANONICAL_18_FEATURE_NAMES), dtype=float)
    frame = pd.DataFrame(
        [dict(zip(CANONICAL_18_FEATURE_NAMES, values))],
        columns=list(reversed(CANONICAL_18_FEATURE_NAMES)),
    )

    pipeline.process_dataframe(frame)

    expected = [[float(CANONICAL_18_FEATURE_NAMES.index(name)) for name in selected_features]]
    assert model.last_features.tolist() == expected


def test_synthetic_pipeline_to_metrics_record_end_to_end():
    assert tuple(STANDARDIZED_21_FEATURES) == tuple(CANONICAL_18_FEATURE_NAMES)
    selected_features = list(STANDARDIZED_21_FEATURES[:8])
    training_values = np.zeros((8, len(selected_features)), dtype=float)
    training_values[:, 0] = np.tile([0.0, 1.0], 4)
    training_frame = pd.DataFrame(training_values, columns=selected_features)
    preprocessor = FeaturePreprocessor(selected_features)
    preprocessor.fit_transform(training_frame)

    model = _SyntheticThresholdModel()
    pipeline = IDSSystemPipeline(
        model=model,
        preprocessor=preprocessor,
        feature_profile="synthetic_test_subset",
        feature_names=selected_features,
    )
    labels = np.array([0, 1, 0, 1])
    evaluation_values = np.zeros((4, len(STANDARDIZED_21_FEATURES)), dtype=float)
    evaluation_values[:, 0] = [0.2, 0.8, 0.1, 0.9]
    evaluation_frame = pd.DataFrame(
        evaluation_values,
        columns=STANDARDIZED_21_FEATURES,
    )
    evaluation_frame["label"] = labels
    evaluation_frame = evaluation_frame[["label", *reversed(STANDARDIZED_21_FEATURES)]]

    alerts = pipeline.process_dataframe(evaluation_frame)
    probabilities = np.asarray([alert["prediction_prob"] for alert in alerts])
    metrics = evaluate_predictions(labels, probabilities, threshold=0.5)
    report_record = {
        "designation": "SYNTHETIC_ONLY",
        "interpretation": "TEST_FIXTURE_NOT_BENCHMARK_EVIDENCE",
        "sample_count": len(labels),
        "metrics": metrics,
    }

    assert model.last_features.shape == (len(labels), len(selected_features))
    assert all(set(alert["raw_features"]) == set(selected_features) for alert in alerts)
    expected_probabilities = [0.1, 0.9, 0.1, 0.9]
    assert all(
        alert["prediction_prob"] == expected
        for alert, expected in zip(alerts, expected_probabilities)
    )
    assert metrics["result_status"] == "COMPLETE"
    assert metrics["roc_auc"] == pytest.approx(1.0)
    assert json.loads(json.dumps(report_record, allow_nan=False))["designation"] == "SYNTHETIC_ONLY"


def test_materialized_subset_missing_a_configured_feature_fails_before_preprocessing():
    selected_features = list(CANONICAL_18_FEATURE_NAMES[:8])
    pipeline = _pipeline_with_test_model(
        _SyntheticThresholdModel(), feature_names=selected_features
    )
    incomplete_frame = pd.DataFrame(
        np.zeros((1, len(selected_features) - 1)),
        columns=selected_features[:-1],
    )

    with pytest.raises(ValueError, match="missing configured model features"):
        pipeline.process_dataframe(incomplete_frame)


@pytest.mark.parametrize(
    ("invalid_value", "message"),
    [(np.nan, "contain NaN"), ("not-a-number", "real numeric values")],
)
def test_materialized_feature_schema_rejects_invalid_values(invalid_value, message):
    selected_features = list(CANONICAL_18_FEATURE_NAMES[:8])
    pipeline = _pipeline_with_test_model(
        _SyntheticThresholdModel(), feature_names=selected_features
    )
    if isinstance(invalid_value, str):
        values = np.zeros((1, len(selected_features)), dtype=object)
        values[0, 0] = invalid_value
        frame = pd.DataFrame(values, columns=selected_features)
    else:
        frame = pd.DataFrame(
            np.zeros((1, len(selected_features))), columns=selected_features
        )
        frame.iloc[0, 0] = invalid_value

    with pytest.raises(ValueError, match=message):
        pipeline.process_dataframe(frame)


def test_pipeline_rejects_invalid_feature_and_threshold_configuration():
    with pytest.raises(ValueError, match="unique, non-empty"):
        _pipeline_with_test_model(_SyntheticThresholdModel(), feature_names=["dup", "dup"])

    with pytest.raises(ValueError, match="decision_threshold"):
        IDSSystemPipeline(
            model=_SyntheticThresholdModel(),
            preprocessor=_IdentityPreprocessor(),
            decision_threshold=float("nan"),
        )


def test_preprocessing_failure_propagates_without_model_success():
    class FailingPreprocessor:
        def transform(self, frame):
            raise RuntimeError("synthetic preprocessing failure")

    class MustNotRunModel:
        classes_ = np.array([0, 1])

        def predict_proba(self, features):
            pytest.fail("model must not run after preprocessing fails")

    pipeline = IDSSystemPipeline(
        model=MustNotRunModel(),
        preprocessor=FailingPreprocessor(),
        feature_names=list(CANONICAL_18_FEATURE_NAMES[:8]),
    )
    frame = pd.DataFrame(
        np.zeros((1, len(CANONICAL_18_FEATURE_NAMES[:8]))),
        columns=CANONICAL_18_FEATURE_NAMES[:8],
    )

    with pytest.raises(RuntimeError, match="synthetic preprocessing failure"):
        pipeline.process_dataframe(frame)


def test_batch_inference_rejects_class_labels_masquerading_as_probabilities():
    class LabelOnlyModel:
        classes_ = np.array([0, 1])

        def predict(self, features):
            return np.ones(len(features), dtype=int)

    pipeline = _pipeline_with_test_model(LabelOnlyModel())
    frame = pd.DataFrame(
        [np.zeros(len(CANONICAL_18_FEATURE_NAMES))],
        columns=CANONICAL_18_FEATURE_NAMES,
    )

    with pytest.raises(TypeError, match="must provide predict_proba"):
        pipeline.process_dataframe(frame)


def test_batch_inference_rejects_non_finite_model_probabilities():
    class InvalidProbabilityModel:
        classes_ = np.array([0, 1])

        def predict_proba(self, features):
            return np.tile(np.array([[np.nan, np.nan]]), (len(features), 1))

    pipeline = _pipeline_with_test_model(InvalidProbabilityModel())
    frame = pd.DataFrame(
        [np.zeros(len(CANONICAL_18_FEATURE_NAMES))],
        columns=CANONICAL_18_FEATURE_NAMES,
    )

    with pytest.raises(ValueError, match="finite values within"):
        pipeline.process_dataframe(frame)


@pytest.mark.parametrize(
    ("probabilities", "message"),
    [
        ([[1.1, -0.1]], "finite values within"),
        ([[0.4]], "shape"),
        ([[0.2, 0.2]], "sum to one"),
        ([["0.9", "0.1"]], "real numeric probabilities"),
    ],
)
def test_batch_inference_rejects_malformed_probability_rows(probabilities, message):
    class InvalidProbabilityModel:
        classes_ = np.array([0, 1])

        def predict_proba(self, features):
            return np.tile(np.asarray(probabilities), (len(features), 1))

    pipeline = _pipeline_with_test_model(InvalidProbabilityModel())
    frame = pd.DataFrame(
        [np.zeros(len(CANONICAL_18_FEATURE_NAMES))],
        columns=CANONICAL_18_FEATURE_NAMES,
    )

    with pytest.raises(ValueError, match=message):
        pipeline.process_dataframe(frame)
