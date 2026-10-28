"""Tests for the generated-only packet-to-alert command."""
from __future__ import annotations

import json

import numpy as np

from iot_ids.runtime import synthetic_packet_demo as demo


def test_demo_command_emits_valid_synthetic_alert_json(capsys):
    assert demo.main(["--seed", "17", "--flows", "3"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["status"] == "SYNTHETIC_ONLY_DIAGNOSTIC"
    assert output["seed"] == 17
    assert output["model"] == {
        "type": "deterministic_duration_rule_test_double",
        "trained": False,
        "artifact_loaded": False,
    }
    assert output["input"] == {
        "type": "generated_packet_records",
        "packet_count": 6,
        "flow_count": 3,
        "feature_profile": "standardized_21",
        "feature_count": 21,
    }
    assert len(output["alerts"]) == 3
    for alert in output["alerts"]:
        assert {
            "flow_id", "prediction_prob", "decision_threshold", "is_anomaly",
            "risk_score", "risk_level", "feature_profile", "selected_features",
        } <= alert.keys()
        assert 0.0 <= alert["prediction_prob"] <= 1.0
        assert 0.0 <= alert["decision_threshold"] <= 1.0
        assert 0.0 <= alert["risk_score"] <= 1.0
        assert alert["feature_profile"] == "synthetic_demo_standardized_21"
        assert len(alert["selected_features"]) == 5


def test_demo_output_is_repeatable_for_fixed_seed():
    first = demo.run_demo(seed=23, flow_count=4)
    second = demo.run_demo(seed=23, flow_count=4)
    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second, sort_keys=True, allow_nan=False
    )


def test_invalid_configuration_fails_with_machine_readable_reason(capsys):
    assert demo.main(["--threshold", "1.5"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "status": "SYNTHETIC_DEMO_FAILED",
        "reason_code": "invalid_threshold",
    }


def test_malformed_model_output_fails_without_emitting_alerts(monkeypatch, capsys):
    def malformed_output(self, features):
        return np.ones((len(features), 1), dtype=float)

    monkeypatch.setattr(demo._SyntheticDurationModel, "predict_proba", malformed_output)
    assert demo.main(["--seed", "5"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "status": "SYNTHETIC_DEMO_FAILED",
        "reason_code": "inference_contract_failed",
    }


def test_demo_requires_no_artifact_and_writes_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = demo.run_demo(seed=31, flow_count=2)
    assert output["model"]["trained"] is False
    assert output["model"]["artifact_loaded"] is False
    assert list(tmp_path.iterdir()) == []
