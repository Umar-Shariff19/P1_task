"""Integration tests for Dashboard Starlette REST and WebSocket Endpoints."""
from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from iot_ids.dashboard.app import create_app
from iot_ids.dashboard.state import get_platform_state


class MockEndpointRequest:
    """Synchronous test request runner allowing direct endpoint testing without network sockets."""
    __test__ = False

    def __init__(self, json_data: dict | None = None, query_params: dict | None = None):
        self._json_data = json_data or {}
        self.query_params = query_params or {}

    async def json(self) -> dict:
        return self._json_data


def invoke_endpoint(
    app,
    path: str,
    method: str = "GET",
    json_body: dict | None = None,
    query_params: dict | None = None,
):
    """Executes a Starlette route endpoint function synchronously to completion."""
    req = MockEndpointRequest(json_data=json_body, query_params=query_params)
    for route in app.routes:
        if getattr(route, "path", None) == path:
            methods = getattr(route, "methods", ["GET"])
            if method in methods:
                coro = route.endpoint(req)
                try:
                    coro.send(None)
                except StopIteration as e:
                    return e.value
                # If endpoint awaited request.json()
                try:
                    coro.send(json_body or {})
                except StopIteration as e:
                    return e.value
    raise ValueError(f"Route not found: {method} {path}")


@pytest.fixture
def test_app():
    state = get_platform_state()
    return create_app(state=state)


def test_api_health_and_status_endpoints(test_app):
    # Health endpoint
    resp = invoke_endpoint(test_app, "/api/health", method="GET")
    assert resp.status_code == 200
    data = json.loads(resp.body)
    assert data["status"] == "UP"
    assert data["details"]["platform_status"] == "ONLINE"

    # Status endpoint
    resp_status = invoke_endpoint(test_app, "/api/status", method="GET")
    assert resp_status.status_code == 200
    status_data = json.loads(resp_status.body)
    assert "simulator" in status_data
    assert "pipeline" in status_data
    assert status_data["pipeline"]["health"] == "HEALTHY"


def test_api_devices_and_scenarios(test_app):
    # Devices endpoint
    resp_dev = invoke_endpoint(test_app, "/api/devices", method="GET")
    assert resp_dev.status_code == 200
    dev_data = json.loads(resp_dev.body)
    assert dev_data["count"] == 8
    assert len(dev_data["devices"]) == 8

    # Scenarios endpoint
    resp_sc = invoke_endpoint(test_app, "/api/scenarios", method="GET")
    assert resp_sc.status_code == 200
    sc_data = json.loads(resp_sc.body)
    assert len(sc_data["scenarios"]) >= 5
    scenario_types = [s["type"] for s in sc_data["scenarios"]]
    assert "BENIGN_NORMAL" in scenario_types
    assert "MIRAI_BOTNET_FLOOD" in scenario_types


def test_api_simulation_lifecycle_and_stepping(test_app):
    # Start
    resp_start = invoke_endpoint(test_app, "/api/simulation/start", method="POST", json_body={"interval": 0.3})
    assert resp_start.status_code == 200

    # Pause
    resp_pause = invoke_endpoint(test_app, "/api/simulation/pause", method="POST")
    assert resp_pause.status_code == 200
    assert json.loads(resp_pause.body)["status"] == "PAUSED"

    # Resume
    resp_res = invoke_endpoint(test_app, "/api/simulation/resume", method="POST")
    assert resp_res.status_code == 200
    assert json.loads(resp_res.body)["status"] == "RESUMED"

    # Stop
    resp_stop = invoke_endpoint(test_app, "/api/simulation/stop", method="POST")
    assert resp_stop.status_code == 200
    assert json.loads(resp_stop.body)["status"] == "STOPPED"

    # Step
    resp_step = invoke_endpoint(test_app, "/api/simulation/step", method="POST", json_body={"count": 10})
    assert resp_step.status_code == 200
    step_data = json.loads(resp_step.body)
    assert step_data["status"] == "STEP_COMPLETE"
    assert step_data["alerts_generated"] >= 1

    # Scenario Switch
    resp_sc_set = invoke_endpoint(test_app, "/api/simulation/scenario", method="POST", json_body={"scenario": "MIRAI_BOTNET_FLOOD"})
    assert resp_sc_set.status_code == 200
    assert json.loads(resp_sc_set.body)["scenario_type"] == "MIRAI_BOTNET_FLOOD"

    # Model Switch
    resp_mod = invoke_endpoint(test_app, "/api/models/select", method="POST", json_body={"model": "robust_mlp"})
    assert resp_mod.status_code == 200
    assert json.loads(resp_mod.body)["active_model"] == "robust_mlp"


def test_api_flows_and_alerts_query(test_app):
    # Ensure at least 1 step
    invoke_endpoint(test_app, "/api/simulation/step", method="POST", json_body={"count": 15})

    # Query flows
    resp_flows = invoke_endpoint(test_app, "/api/flows", method="GET", query_params={"limit": 20})
    assert resp_flows.status_code == 200
    flows_data = json.loads(resp_flows.body)
    assert flows_data["count"] > 0
    sample_flow = flows_data["flows"][0]
    assert "flow_id" in sample_flow
    assert "raw_features" in sample_flow

    # Query alerts
    resp_alerts = invoke_endpoint(test_app, "/api/alerts", method="GET", query_params={"limit": 10})
    assert resp_alerts.status_code == 200
    alerts_data = json.loads(resp_alerts.body)
    assert isinstance(alerts_data["alerts"], list)


def test_api_adversarial_and_xai_endpoints(test_app):
    # Adversarial Run
    resp_adv = invoke_endpoint(
        test_app,
        "/api/adversarial/run",
        method="POST",
        json_body={"epsilon": 0.15, "steps": 3, "sample_count": 8, "attack_method": "pgd"},
    )
    assert resp_adv.status_code == 200
    adv_data = json.loads(resp_adv.body)
    assert "experiment_id" in adv_data
    assert "models" in adv_data

    # Explainability
    resp_xai = invoke_endpoint(test_app, "/api/explain", method="POST", json_body={})
    assert resp_xai.status_code == 200
    xai_data = json.loads(resp_xai.body)
    assert "final_decision" in xai_data
    assert "top_k_features" in xai_data
    assert len(xai_data["top_k_features"]) > 0

    # Historical Experiments
    resp_exp = invoke_endpoint(test_app, "/api/experiments", method="GET")
    assert resp_exp.status_code == 200
    exp_data = json.loads(resp_exp.body)
    assert exp_data["count"] >= 1


def test_api_root_html_render(test_app):
    resp = invoke_endpoint(test_app, "/", method="GET")
    assert resp.status_code == 200
    html_content = resp.body.decode("utf-8")
    assert "IoT IDS & Adversarial Platform" in html_content
    assert "Live Telemetry" in html_content
    assert "Adversarial Lab" in html_content
    assert "Explainability (XAI)" in html_content


def test_websocket_event_streaming_queue():
    state = get_platform_state()
    queue = MagicMock()
    queue.put_nowait = MagicMock()

    state.register_async_queue(queue)
    assert queue in state._async_queues

    # Stepping simulation generates and broadcasts events
    state.step_simulation(count=5)
    assert queue.put_nowait.call_count >= 1

    state.unregister_async_queue(queue)
    assert queue not in state._async_queues


def test_api_system_shutdown_endpoint(test_app):
    resp = invoke_endpoint(test_app, "/api/system/shutdown", method="POST")
    assert resp.status_code == 200
    data = json.loads(resp.body)
    assert data["status"] == "SHUTDOWN_INITIATED"


def test_dashboard_status_provenance_synthetic_default(test_app):
    resp = invoke_endpoint(test_app, "/api/status", method="GET")
    assert resp.status_code == 200
    status_data = json.loads(resp.body)
    prov = status_data["provenance"]
    assert prov["model_suite_type"] == "SYNTHETIC_REFERENCE"
    assert prov["model_authorization_status"] == "FAIL_CLOSED_ROOT_IDENTITY_REQUIRED"
    assert prov["research_checkpoints_loaded"] is False
    assert prov["dataset_name"] == "SYNTHETIC_ONLY"


def test_dashboard_switch_to_research_refused_without_authorization(test_app):
    # Attempting to switch to research models without authorized credentials
    resp = invoke_endpoint(
        test_app,
        "/api/models/select",
        method="POST",
        json_body={"mode": "research", "dataset": "ToN-IoT"},
    )
    assert resp.status_code == 403
    data = json.loads(resp.body)
    assert data["error"] == "RESEARCH_MODEL_AUTHORIZATION_DENIED"
    assert data["fallback_prevented"] is True
    assert "Real-data execution is disabled" in data["reason"]

    # Verify platform state remains intact and synthetic (did not silently switch or corrupt)
    status_resp = invoke_endpoint(test_app, "/api/status", method="GET")
    assert json.loads(status_resp.body)["provenance"]["model_suite_type"] == "SYNTHETIC_REFERENCE"


def _create_dashboard_test_policy(
    approved_models_root: str,
    approved_data_root: str,
    anchor_id: str = "owner-anchor-01",
    secret_key: bytes = b"test-secret-key-32-bytes-secure!",
):
    import datetime
    from iot_ids.provenance.windows_access import CryptographicPolicyAuthorizationProvider

    provider = CryptographicPolicyAuthorizationProvider(
        trust_anchors={anchor_id: secret_key},
        revocation_list=set(),
    )
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    id_pin = {
        "path_kind": "local_drive",
        "volume_identity": "VOL-TEST-1234",
        "root_file_identity": "FILE-TEST-5678",
        "case_policy": "case_insensitive",
    }
    document = {
        "schema_version": 1,
        "example_only": False,
        "policy_revision": "ACTIVE-RESEARCH-POLICY-V1",
        "status": "ACTIVE",
        "filesystem_policy_version": "FS-V1",
        "datasets": {
            "ton_iot_research": {
                "dataset_id": "ton_iot_research",
                "approved_root": approved_data_root,
                "permitted_operations": ["read_split", "read_checkpoint", "evaluate_model"],
                "identity_pin": id_pin,
                "approval": None,
            }
        },
        "artifact_roots": {
            "research_models": {
                "resource_id": "research_models",
                "approved_root": approved_models_root,
                "permitted_operations": ["read_checkpoint"],
                "identity_pin": id_pin,
                "approval": None,
            }
        },
        "protected_roots": [
            {
                "root_id": "windows_system",
                "path": r"C:\Windows",
                "coverage": "ancestors_and_descendants",
                "identity_pin": id_pin,
                "approval": None,
            }
        ],
        "policy_approval": None,
    }
    digest = provider.canonical_policy_digest(document)
    sig = provider.sign_policy_digest(digest, secret_key)
    approval_block = {
        "approval_record_id": "REC-2026-DASHBOARD-001",
        "approver_identity": "Project Owner <owner@iot-ids.internal>",
        "approved_at": now,
        "trust_anchor_id": anchor_id,
        "signed_policy_sha256": digest,
        "signature_reference": sig,
    }
    document["datasets"]["ton_iot_research"]["approval"] = approval_block
    document["artifact_roots"]["research_models"]["approval"] = approval_block
    document["protected_roots"][0]["approval"] = approval_block
    document["policy_approval"] = approval_block
    return document, provider


def test_dashboard_switch_to_research_with_authorized_policy():
    from pathlib import Path
    from iot_ids.dashboard.state import PlatformStateManager

    models_root = str(Path("models").resolve())
    data_root = str(Path("data/processed/stage3").resolve())

    policy, provider = _create_dashboard_test_policy(models_root, data_root)

    # Create fresh state manager with authorized policy
    state = PlatformStateManager(
        seed=42,
        model_mode="research",
        dataset_name="ToN-IoT",
        authorization_provider=provider,
        policy_document=policy,
    )
    app = create_app(state=state)

    status_resp = invoke_endpoint(app, "/api/status", method="GET")
    assert status_resp.status_code == 200
    status_data = json.loads(status_resp.body)
    prov = status_data["provenance"]
    assert prov["model_suite_type"] == "VERIFIED_RESEARCH_BASELINE"
    assert prov["model_authorization_status"] == "AUTHORIZED_CRYPTOGRAPHIC_POLICY"
    assert prov["research_checkpoints_loaded"] is True
    assert prov["dataset_name"] == "ToN-IoT"
    assert "models\\standardized\\ToN-IoT" in prov["artifact_path"] or "models/standardized/ToN-IoT" in prov["artifact_path"]
    assert len(prov["artifact_digests"]) >= 6

    # Test stepping traffic with research model
    step_resp = invoke_endpoint(app, "/api/simulation/step", method="POST", json_body={"count": 10})
    assert step_resp.status_code == 200
    assert json.loads(step_resp.body)["status"] == "STEP_COMPLETE"

    # Test XAI endpoint with research model
    xai_resp = invoke_endpoint(app, "/api/explain", method="POST", json_body={})
    assert xai_resp.status_code == 200
    xai_data = json.loads(xai_resp.body)
    assert "final_decision" in xai_data
    assert "top_k_features" in xai_data


# -----------------------------------------------------------------------------
# Regression Tests for XAI & Alert Triage (Phases 1-4 Verification)
# -----------------------------------------------------------------------------


def test_xai_explain_by_flow_id(test_app):
    """Criteria 1: Explain by flow_id returns expected keys, feature attributions, and probabilities."""
    invoke_endpoint(test_app, "/api/simulation/step", method="POST", json_body={"count": 10})
    flows_resp = invoke_endpoint(test_app, "/api/flows", method="GET", query_params={"limit": 5})
    target_flow = json.loads(flows_resp.body)["flows"][0]
    target_flow_id = target_flow["flow_id"]

    resp = invoke_endpoint(test_app, "/api/explain", method="POST", json_body={"flow_id": target_flow_id})
    assert resp.status_code == 200
    data = json.loads(resp.body)

    assert data["flow_id"] == target_flow_id
    assert "option_c_probability" in data
    assert "rf_probability" in data
    assert "robust_mlp_probability" in data
    assert "final_decision" in data
    assert data["final_decision"] in ["ATTACK", "BENIGN"]
    assert "top_k_features" in data
    assert len(data["top_k_features"]) == 7
    assert "methodology" in data
    assert data["decision_threshold"] == 0.50

    # Flow provenance metadata
    assert "ground_truth" in data
    assert "scenario" in data
    assert "source_device" in data
    assert "model_suite_type" in data


def test_xai_explain_latest_flow(test_app):
    """Criteria 2: Empty request body returns explanation for most recent network flow."""
    invoke_endpoint(test_app, "/api/simulation/step", method="POST", json_body={"count": 5})
    flows_resp = invoke_endpoint(test_app, "/api/flows", method="GET", query_params={"limit": 1})
    latest_flow_id = json.loads(flows_resp.body)["flows"][0]["flow_id"]

    resp = invoke_endpoint(test_app, "/api/explain", method="POST", json_body={})
    assert resp.status_code == 200
    data = json.loads(resp.body)
    assert data["flow_id"] == latest_flow_id
    assert "final_decision" in data
    assert len(data["top_k_features"]) == 7


def test_xai_explain_flow_not_found_returns_404(test_app):
    """Criteria 3: Unknown flow_id returns 404 with error message (no silent fallback)."""
    invoke_endpoint(test_app, "/api/simulation/step", method="POST", json_body={"count": 5})
    resp = invoke_endpoint(test_app, "/api/explain", method="POST", json_body={"flow_id": "nonexistent_flow_99999"})
    assert resp.status_code == 404
    data = json.loads(resp.body)
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_xai_explain_empty_buffer_returns_404():
    """Criteria 4: Empty buffer returns 404 with error message."""
    from iot_ids.dashboard.state import PlatformStateManager
    fresh_state = PlatformStateManager(seed=42)
    fresh_app = create_app(state=fresh_state)
    assert len(fresh_state.recent_flows) == 0

    resp = invoke_endpoint(fresh_app, "/api/explain", method="POST", json_body={})
    assert resp.status_code == 404
    data = json.loads(resp.body)
    assert "error" in data
    assert "no network flows recorded" in data["error"].lower()


def test_xai_attribution_values_and_features(test_app):
    """Criteria 5: Attribution values are non-zero, normalized, and include top features."""
    invoke_endpoint(test_app, "/api/simulation/step", method="POST", json_body={"count": 10})
    resp = invoke_endpoint(test_app, "/api/explain", method="POST", json_body={})
    assert resp.status_code == 200
    data = json.loads(resp.body)

    feats = data["top_k_features"]
    assert len(feats) == 7

    total_abs_attr = sum(abs(f["attribution"]) for f in feats)
    assert total_abs_attr > 0.001

    for f in feats:
        assert isinstance(f["feature"], str)
        assert isinstance(f["raw_value"], (int, float))
        assert isinstance(f["attribution"], (int, float))
        assert isinstance(f["weighted_attribution"], (int, float))
        assert f["attribution"] == f["weighted_attribution"]
        assert f["direction"] in ["PUSHES_ATTACK", "PUSHES_BENIGN"]
        if f["attribution"] > 0:
            assert f["direction"] == "PUSHES_ATTACK"
        else:
            assert f["direction"] == "PUSHES_BENIGN"


def test_xai_probability_consistency(test_app):
    """Criteria 6: Returned ensemble decision matches probabilities against 0.50 threshold."""
    invoke_endpoint(test_app, "/api/simulation/step", method="POST", json_body={"count": 10})
    resp = invoke_endpoint(test_app, "/api/explain", method="POST", json_body={})
    assert resp.status_code == 200
    data = json.loads(resp.body)

    opt_c = data["option_c_probability"]
    rf = data["rf_probability"]
    mlp = data["robust_mlp_probability"]
    dec = data["final_decision"]

    assert 0.0 <= opt_c <= 1.0
    assert 0.0 <= rf <= 1.0
    assert 0.0 <= mlp <= 1.0

    if opt_c >= 0.50:
        assert dec == "ATTACK"
    else:
        assert dec == "BENIGN"


def test_alert_triage_data_integrity():
    """Criteria 7: Alerts accurately reflect ground truth, scenario, and model prediction without conflation."""
    from iot_ids.dashboard.state import PlatformStateManager
    state = PlatformStateManager(seed=42)
    app = create_app(state=state)

    # 1. Benign simulation
    state.simulator.set_scenario("BENIGN_NORMAL")
    benign_alerts = state.step_simulation(count=200)

    for alert in benign_alerts:
        flow_meta = state._flow_metadata.get(alert["flow_id"])
        if flow_meta:
            assert flow_meta[0] == 0
            assert flow_meta[1] == "BENIGN_NORMAL"

    for a in state.recent_alerts:
        if a["scenario"] == "BENIGN_NORMAL":
            assert a["ground_truth"] == 0
            assert a["prediction_prob"] >= 0.50 or a["is_anomaly"] is True

    # 2. Attack simulation
    state.simulator.set_scenario("MIRAI_BOTNET_FLOOD")
    state.step_simulation(count=100)

    mirai_alerts = [a for a in state.recent_alerts if a["scenario"] == "MIRAI_BOTNET_FLOOD"]
    assert len(mirai_alerts) > 0
    true_attacks = [a for a in mirai_alerts if a["ground_truth"] == 1]
    assert len(true_attacks) > 0
    for ta in true_attacks:
        assert ta["ground_truth"] == 1
        assert ta["prediction_prob"] >= 0.50
        assert ta["scenario"] == "MIRAI_BOTNET_FLOOD"

    # 3. Query alerts API
    resp = invoke_endpoint(app, "/api/alerts", method="GET")
    assert resp.status_code == 200
    alerts_data = json.loads(resp.body)["alerts"]
    assert len(alerts_data) > 0
    for item in alerts_data:
        assert "ground_truth" in item
        assert "scenario" in item
        assert item["ground_truth"] in (0, 1)


def test_benign_sensor_packet_semantics_and_false_positive_bound():
    """Regression test: Environmental sensors use ephemeral ports, syn=0, and produce 0 high-confidence FPs."""
    from iot_ids.simulator.generator import IoTSimulator
    from iot_ids.simulator.devices import DeviceType
    from iot_ids.dashboard.state import PlatformStateManager

    sim = IoTSimulator(seed=42)
    sensor_devs = [d for d in sim.devices if d.device_type == DeviceType.ENVIRONMENTAL_SENSOR]
    assert len(sensor_devs) == 2

    # Check generated packet semantics directly
    for dev in sensor_devs:
        for _ in range(50):
            pkt = sim._create_benign_packet(dev, timestamp=10.0)
            assert pkt.syn == 0, "Benign sensor telemetry packets must not have syn=1"
            assert pkt.ack == 1, "Benign sensor telemetry packets must have ack=1"
            assert pkt.src_port >= 49152, "Sensor client source port must be ephemeral"
            assert pkt.dst_port in (1883, 8883), "Sensor destination port must be MQTT broker"

    # Verify platform state produces zero high-confidence false positives (prob >= 0.70)
    state = PlatformStateManager(seed=42)
    state.simulator.set_scenario("BENIGN_NORMAL")
    for _ in range(50):
        state.step_simulation(count=10)

    fps = [a for a in state.recent_alerts if a["ground_truth"] == 0]
    high_fps = [a for a in fps if a["prediction_prob"] >= 0.70]
    assert len(high_fps) == 0, f"Expected 0 high-confidence FPs (>=0.70), got {len(high_fps)}"
    total_flows = len(state.recent_flows)
    fpr = len(fps) / max(1, total_flows)
    assert fpr <= 0.01, f"Benign FPR must be <= 1.0%, got {fpr:.4f}"


def test_xai_attribution_direction_consistency(test_app):
    """Regression test: Feature attributions and push directions agree with attribution sign."""
    invoke_endpoint(test_app, "/api/simulation/step", method="POST", json_body={"count": 10})
    resp = invoke_endpoint(test_app, "/api/explain", method="POST", json_body={})
    assert resp.status_code == 200
    data = json.loads(resp.body)

    for feat in data["top_k_features"]:
        attr = feat["attribution"]
        direction = feat["direction"]
        if attr > 0:
            assert direction == "PUSHES_ATTACK", f"Positive attribution {attr} must be PUSHES_ATTACK"
        else:
            assert direction == "PUSHES_BENIGN", f"Non-positive attribution {attr} must be PUSHES_BENIGN"

