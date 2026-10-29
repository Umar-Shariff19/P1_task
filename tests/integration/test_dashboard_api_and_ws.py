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

