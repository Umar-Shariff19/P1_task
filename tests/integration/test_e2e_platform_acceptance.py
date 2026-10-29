"""End-to-End Automated Platform Acceptance Test.

Verifies the complete lifecycle of the IoT IDS & Adversarial Robustness Platform:
1. Multi-device IoT environment simulation
2. Real packet/flow ingestion and 21-feature canonical multi-level extraction
3. Inference using Option C Dual-Stream Ensemble (0.7 RF + 0.3 Robust MLP)
4. Alert generation and severity grading
5. Controlled adversarial attack laboratory (PGD with continuous mask and domain clamping)
6. Comparative detection evaluation (Clean vs Adversarial, ASR, Autoencoder zero-day catch rate)
7. Local explainability (TreeExplainer + Gradient Attribution)
8. Multi-model dynamic switching
9. Experiment ledger audit logging
10. Clean lifecycle reset and shutdown
"""
from __future__ import annotations

import time
import pytest
import numpy as np

from iot_ids.dashboard.state import PlatformStateManager
from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.simulator.scenarios import ScenarioType


def test_full_platform_end_to_end_acceptance():
    # 1. Instantiate platform state manager
    manager = PlatformStateManager(seed=42)
    initial_status = manager.get_status()
    assert initial_status["platform_status"] == "ONLINE"
    assert initial_status["pipeline"]["health"] == "HEALTHY"
    assert initial_status["pipeline"]["active_model"] == "option_c"
    assert len(initial_status["simulator"]["devices"]) == 8

    # 2. Configure threat scenario: Mirai Botnet Flood
    sc_res = manager.set_scenario(ScenarioType.MIRAI_BOTNET_FLOOD)
    assert sc_res["status"] == "SCENARIO_UPDATED"
    assert sc_res["scenario_type"] == "MIRAI_BOTNET_FLOOD"

    # 3. Step simulator to generate and ingest attack traffic
    step_alerts = manager.step_simulation(count=25)
    assert len(step_alerts) > 0

    # 4. Verify telemetry records and alert extraction
    assert len(manager.recent_flows) > 0
    latest_flow = list(manager.recent_flows)[-1]
    assert "flow_id" in latest_flow
    assert "src_ip" in latest_flow
    assert "dst_ip" in latest_flow
    assert "prediction_prob" in latest_flow
    assert "risk_score" in latest_flow
    assert "risk_level" in latest_flow
    assert len(latest_flow["raw_features"]) == len(CANONICAL_21_FEATURE_NAMES)

    # Verify high-severity attack alerts were triggered
    attack_flows = [f for f in manager.recent_flows if f["ground_truth"] == 1]
    assert len(attack_flows) > 0
    anomalous_alerts = [f for f in attack_flows if f["is_anomaly"]]
    assert len(anomalous_alerts) > 0

    # 5. Execute Explainability (XAI) on detected attack flow
    sample_features = anomalous_alerts[0]["raw_features"]
    xai_res = manager.explain_flow(sample_features)
    assert "final_decision" in xai_res
    assert "option_c_probability" in xai_res
    assert "rf_probability" in xai_res
    assert "robust_mlp_probability" in xai_res
    assert "top_k_features" in xai_res
    assert len(xai_res["top_k_features"]) >= 5

    # Verify top features contain relevant network flood indicators
    top_feature_names = [f["feature"] for f in xai_res["top_k_features"]]
    assert any(
        f in top_feature_names
        for f in ["flow_bytes_per_sec", "flow_pkts_per_sec", "tcp_syn_ratio", "temporal_syn_rate_ewma", "behavioral_fanout_ratio"]
    )

    # 6. Execute Adversarial Attack Laboratory Evaluation
    epsilon = 0.15
    steps = 5
    exp_res = manager.run_adversarial_experiment(
        epsilon=epsilon,
        steps=steps,
        attack_method="pgd",
        sample_count=20,
    )
    assert exp_res["experiment_id"].startswith("exp_")
    assert exp_res["attack_method"] == "PGD"
    assert exp_res["epsilon"] == epsilon
    assert exp_res["steps"] == steps
    assert exp_res["samples_attacked"] > 0
    assert exp_res["perturbation_linf"] <= epsilon + 1e-4

    # Verify cross-model comparative robustness
    models_eval = exp_res["models"]
    assert "standard_mlp" in models_eval
    assert "robust_mlp" in models_eval
    assert "random_forest" in models_eval
    assert "option_c_ensemble" in models_eval

    std_clean = models_eval["standard_mlp"]["clean_detection_rate"]
    std_adv = models_eval["standard_mlp"]["adv_detection_rate"]
    rob_adv = models_eval["robust_mlp"]["adv_detection_rate"]
    optc_adv = models_eval["option_c_ensemble"]["adv_detection_rate"]

    assert std_clean >= 0.85
    # Robust MLP and Option C Ensemble retain superior detection over Standard MLP under PGD attack
    assert rob_adv >= std_adv or optc_adv >= std_adv

    # Verify Risk Layer Autoencoder catch rate
    risk_info = exp_res["risk_layer"]
    assert "ae_catch_rate" in risk_info
    assert "attack_success_rate" in risk_info

    # 7. Verify Experiment Ledger Persistence
    assert len(manager.experiment_history) >= 1
    assert manager.experiment_history[-1]["experiment_id"] == exp_res["experiment_id"]

    # 8. Dynamic Model Switching
    switch_res = manager.set_active_model("robust_mlp")
    assert switch_res["status"] == "MODEL_UPDATED"
    assert switch_res["active_model"] == "robust_mlp"
    assert switch_res["health"] == "HEALTHY"

    # Step again with switched model
    alerts_rob = manager.step_simulation(count=10)
    assert len(alerts_rob) > 0

    # 9. Clean Reset and Shutdown
    reset_res = manager.reset_simulation()
    assert reset_res["status"] == "RESET_COMPLETE"
    assert manager.total_packets == 0
    assert len(manager.recent_flows) == 0
    assert len(manager.recent_alerts) == 0

    stop_res = manager.stop_simulation()
    assert stop_res["status"] == "STOPPED"
