"""Unit tests for Synthetic Model Suite and Inference Wrappers."""
from __future__ import annotations

import numpy as np
import pytest
import torch

from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.models.synthetic_models import (
    SyntheticModelSuite,
    generate_synthetic_reference_dataset,
    train_synthetic_model_suite,
    get_default_model_suite,
    MLPWrapper,
    OptionCEnsemble,
)


def test_synthetic_reference_dataset_generation():
    df, y = generate_synthetic_reference_dataset(n_samples=100, seed=42, attack_ratio=0.30)
    assert len(df) == 100
    assert len(y) == 100
    assert set(df.columns) == set(CANONICAL_21_FEATURE_NAMES)
    assert df.isnull().sum().sum() == 0

    # Verify binary labels
    assert set(y.unique()).issubset({0, 1})
    assert int((y == 1).sum()) == 30
    assert int((y == 0).sum()) == 70


def test_synthetic_model_suite_training_and_health():
    suite = train_synthetic_model_suite(seed=123, n_train=120, n_val=60)
    assert isinstance(suite, SyntheticModelSuite)
    assert len(suite.feature_names) == 21
    assert suite.metadata["rf_val_acc"] > 0.80
    assert suite.metadata["mlp_val_acc"] > 0.80
    assert suite.metadata["robust_mlp_val_acc"] > 0.80
    assert suite.metadata["option_c_val_acc"] > 0.80

    # Test pipeline and predictor creation
    for model_name in ["rf", "standard_mlp", "robust_mlp", "option_c"]:
        pipeline = suite.create_pipeline(model_name=model_name)
        health = pipeline.health_check()
        assert health["status"] == "HEALTHY", f"Pipeline unhealthy for {model_name}"

        predictor = suite.create_predictor(model_name=model_name)
        p_health = predictor.health_check()
        assert p_health["status"] == "HEALTHY"


def test_mlp_wrapper_interface():
    suite = get_default_model_suite()
    wrapper = suite.standard_mlp_wrapper

    assert np.array_equal(wrapper.classes_, np.array([0, 1]))

    # Test predict_proba
    dummy_X = suite.X_val[:10]
    probs = wrapper.predict_proba(dummy_X)
    assert probs.shape == (10, 2)
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5)

    preds = wrapper.predict(dummy_X)
    assert len(preds) == 10
    assert set(preds).issubset({0, 1})


def test_option_c_ensemble_interface():
    suite = get_default_model_suite()
    ensemble = suite.option_c_ensemble

    assert np.array_equal(ensemble.classes_, np.array([0, 1]))

    dummy_X = suite.X_val[:15]
    probs = ensemble.predict_proba(dummy_X)
    assert probs.shape == (15, 2)
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5)

    preds = ensemble.predict(dummy_X)
    assert len(preds) == 15
    assert set(preds).issubset({0, 1})


def test_invalid_model_name_raises():
    suite = get_default_model_suite()
    with pytest.raises(ValueError, match="Unknown model name"):
        suite.get_model("unsupported_model_family")


def test_synthetic_model_detects_mirai_botnet_flood():
    """Regression test ensuring synthetic reference models detect simulated live Mirai botnet flood flows."""
    from iot_ids.dashboard.state import PlatformStateManager
    from iot_ids.simulator.scenarios import ScenarioType

    manager = PlatformStateManager(seed=42)
    manager.set_scenario(ScenarioType.MIRAI_BOTNET_FLOOD)
    manager.step_simulation(count=25)

    attack_flows = [f for f in manager.recent_flows if f["ground_truth"] == 1]
    assert len(attack_flows) > 0, "No attack flows recorded from Mirai scenario"

    detected_alerts = [f for f in attack_flows if f["is_anomaly"]]
    assert len(detected_alerts) > 0, "Mirai attack flows not detected by active model suite"

    for flow in detected_alerts:
        assert flow["prediction_prob"] >= 0.50
        assert flow["risk_score"] >= 0.50


def test_synthetic_model_detects_slowloris_dos():
    """Regression test ensuring synthetic reference models detect Slowloris DoS flows."""
    from iot_ids.dashboard.state import PlatformStateManager
    from iot_ids.simulator.scenarios import ScenarioType

    manager = PlatformStateManager(seed=42)
    manager.set_scenario(ScenarioType.SLOWLORIS_DOS)
    for _ in range(3):
        manager.step_simulation(count=20)

    attack_flows = [f for f in manager.recent_flows if f["ground_truth"] == 1]
    assert len(attack_flows) > 0, "No attack flows recorded from Slowloris scenario"

    detected_alerts = [f for f in attack_flows if f["is_anomaly"]]
    assert len(detected_alerts) > 0, "Slowloris attack flows not detected by active model suite"

    for flow in detected_alerts:
        assert flow["prediction_prob"] >= 0.50
        assert flow["risk_score"] >= 0.50


def test_synthetic_model_detects_data_exfiltration_mitm():
    """Regression test ensuring synthetic reference models detect bulk data exfiltration flows."""
    from iot_ids.dashboard.state import PlatformStateManager
    from iot_ids.simulator.scenarios import ScenarioType

    manager = PlatformStateManager(seed=42)
    manager.set_scenario(ScenarioType.DATA_EXFILTRATION_MITM)
    for _ in range(4):
        manager.step_simulation(count=20)

    attack_flows = [f for f in manager.recent_flows if f["ground_truth"] == 1]
    assert len(attack_flows) > 0, "No attack flows recorded from Data Exfiltration scenario"

    detected_alerts = [f for f in attack_flows if f["is_anomaly"]]
    assert len(detected_alerts) > 0, "Data exfiltration flows not detected by active model suite"

    for flow in detected_alerts:
        assert flow["prediction_prob"] >= 0.50
        assert flow["risk_score"] >= 0.50


def test_synthetic_model_detects_command_injection():
    """Regression test ensuring synthetic reference models detect Modbus command injection flows."""
    from iot_ids.dashboard.state import PlatformStateManager
    from iot_ids.simulator.scenarios import ScenarioType

    manager = PlatformStateManager(seed=42)
    manager.set_scenario(ScenarioType.COMMAND_INJECTION)
    for _ in range(4):
        manager.step_simulation(count=20)

    attack_flows = [f for f in manager.recent_flows if f["ground_truth"] == 1]
    assert len(attack_flows) > 0, "No attack flows recorded from Command Injection scenario"

    detected_alerts = [f for f in attack_flows if f["is_anomaly"]]
    assert len(detected_alerts) > 0, "Command injection flows not detected by active model suite"

    for flow in detected_alerts:
        assert flow["prediction_prob"] >= 0.50
        assert flow["risk_score"] >= 0.50


def test_synthetic_model_benign_normal_zero_false_positives():
    """Ensures benign operational baseline produces zero high-confidence false positives."""
    from iot_ids.dashboard.state import PlatformStateManager
    from iot_ids.simulator.scenarios import ScenarioType

    manager = PlatformStateManager(seed=42)
    manager.set_scenario(ScenarioType.BENIGN_NORMAL)
    for _ in range(5):
        manager.step_simulation(count=15)

    assert len(manager.recent_flows) > 0
    fp_alerts = [f for f in manager.recent_flows if f["is_anomaly"]]
    assert len(fp_alerts) == 0, f"Expected 0 false positives in benign baseline, got {len(fp_alerts)}"


def test_scenario_name_alone_cannot_force_alert():
    """Verifies that scenario name metadata cannot bypass feature-based inference or force alerts."""
    import pandas as pd
    from iot_ids.models.synthetic_models import get_default_model_suite
    from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES

    suite = get_default_model_suite()
    pipeline = suite.create_pipeline(model_name="option_c")

    # Pure benign telemetry feature vector
    benign_features = {
        "flow_duration": 2.5,
        "flow_bytes_per_sec": 450.0,
        "flow_pkts_per_sec": 3.0,
        "mean_pkt_size": 115.0,
        "payload_byte_ratio": 0.55,
        "pkt_count_ratio": 0.50,
        "tcp_syn_ratio": 0.0,
        "proto_tcp": 1.0,
        "proto_udp": 0.0,
        "proto_icmp": 0.0,
        "proto_other": 0.0,
        "temporal_iat_mean": 0.35,
        "temporal_iat_cv": 0.8,
        "temporal_flow_rate_ewma": 3.0,
        "temporal_byte_rate_ewma": 450.0,
        "temporal_syn_rate_ewma": 0.0,
        "behavioral_dst_diversity": 1.0,
        "behavioral_port_entropy": 0.0,
        "behavioral_fanout_ratio": 0.1,
        "behavioral_unanswered_ratio": 0.0,
        "behavioral_src_activity_ewma": 0.25,
    }
    df = pd.DataFrame([benign_features])

    # Run actual pipeline inference
    results = pipeline.process_dataframe(df)
    assert len(results) == 1
    alert = results[0]

    # Verify benign classification
    assert alert["is_anomaly"] is False
    assert alert["prediction_prob"] < 0.50

