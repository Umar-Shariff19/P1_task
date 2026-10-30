"""Unit tests for Flow Lifecycle, Cross-Step Aggregation, and Alert Integrity.

Validates:
1. Multi-packet flow split across simulation steps (preserves pending state, prevents fragmentation).
2. Valid single-packet flow (evaluated and finalized correctly).
3. Flow finalized at explicit termination (clean teardown and flush).
4. Benign traffic across scenario switches (isolated state, zero cross-scenario false positives).
5. Correct alert-to-flow matching for XAI (retains exact flow IDs and canonical feature vectors).
"""
from __future__ import annotations

import json
import pytest

from iot_ids.dashboard.app import create_app
from iot_ids.dashboard.state import PlatformStateManager
from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.simulator.generator import GeneratedPacket
from iot_ids.simulator.scenarios import ScenarioType


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


def test_multi_packet_flow_split_across_simulation_steps():
    """Test 1: Verifies that a multi-packet burst split across simulation steps is preserved

    and aggregated into a unified flow rather than severed into an orphaned tail fragment.
    """
    manager = PlatformStateManager(seed=9999)
    manager.set_scenario(ScenarioType.SLOWLORIS_DOS)

    # Step simulation across multiple small batches that slice bursts
    all_step_alerts = []
    for _ in range(10):
        alerts = manager.step_simulation(count=15)
        all_step_alerts.extend(alerts)

    # Explicit finalization at scenario end
    manager.finalize_pending_flows()

    # Collect attack flows
    attack_flows = [f for f in manager.recent_flows if f["ground_truth"] == 1]
    assert len(attack_flows) > 0, "No attack flows recorded"

    # All attack flows must be successfully detected at threshold 0.50
    missed_flows = [f for f in attack_flows if not f["is_anomaly"]]
    assert len(missed_flows) == 0, f"Found {len(missed_flows)} false negatives in multi-step execution"

    # Verify that multi-packet flows have duration > 0 and packet count > 1
    multi_pkt_flows = [f for f in attack_flows if f["raw_features"]["flow_duration"] > 0]
    assert len(multi_pkt_flows) > 0
    for flow in multi_pkt_flows:
        assert flow["prediction_prob"] >= 0.50
        assert flow["raw_features"]["flow_pkts_per_sec"] > 0


def test_valid_single_packet_flow_handling():
    """Test 2: Verifies that standalone single-packet flows (e.g. Mirai SYN probes)

    are correctly evaluated and finalized within their step without hanging indefinitely.
    """
    manager = PlatformStateManager(seed=42)
    manager.set_scenario(ScenarioType.MIRAI_BOTNET_FLOOD)

    # Step 25 packets - Mirai produces standalone SYN flood probes on ephemeral ports
    step_alerts = manager.step_simulation(count=25)
    assert len(step_alerts) > 0, "Single-packet flows were not finalized in the step"

    # Verify recent flows contain these flows with valid 21-feature representations
    mirai_flows = [f for f in manager.recent_flows if f["ground_truth"] == 1]
    assert len(mirai_flows) > 0

    for flow in mirai_flows:
        assert flow["is_anomaly"] is True
        assert flow["prediction_prob"] >= 0.50
        assert set(flow["raw_features"].keys()) == set(CANONICAL_21_FEATURE_NAMES)
        assert flow["raw_features"]["tcp_syn_ratio"] == pytest.approx(1.0, rel=1e-3)


def test_flow_finalized_at_explicit_termination():
    """Test 3: Verifies that remaining pending flows are cleanly finalized and evaluated

    when explicit scenario termination (stop_simulation or finalize_pending_flows) is triggered.
    """
    manager = PlatformStateManager(seed=777)
    manager.set_scenario(ScenarioType.COMMAND_INJECTION)

    # Manually inject packets where the last packet is at the step boundary
    t_base = 100.0
    packets = [
        GeneratedPacket(
            timestamp=t_base,
            src_ip="192.168.1.102",
            dst_ip="192.168.1.121",
            src_port=50299,
            dst_port=502,
            proto="tcp",
            length=60,
            syn=1,
            ack=0,
            ground_truth=1,
            scenario_name=ScenarioType.COMMAND_INJECTION.value,
            source_device_id="dev_sensor_pressure_02",
        ),
        GeneratedPacket(
            timestamp=t_base + 0.005,
            src_ip="192.168.1.102",
            dst_ip="192.168.1.121",
            src_port=50299,
            dst_port=502,
            proto="tcp",
            length=98,
            syn=0,
            ack=1,
            ground_truth=1,
            scenario_name=ScenarioType.COMMAND_INJECTION.value,
            source_device_id="dev_sensor_pressure_02",
        ),
    ]

    # Queue an upcoming packet in the simulator buffer within burst proximity to keep flow pending
    manager.simulator._packet_buffer = [
        GeneratedPacket(
            timestamp=t_base + 0.010,
            src_ip="192.168.1.102",
            dst_ip="192.168.1.121",
            src_port=50299,
            dst_port=502,
            proto="tcp",
            length=98,
            syn=0,
            ack=1,
            ground_truth=1,
            scenario_name=ScenarioType.COMMAND_INJECTION.value,
            source_device_id="dev_sensor_pressure_02",
        )
    ]

    # Process first 2 packets; flow should remain pending because 3rd packet is in buffer
    manager._process_batch_of_packets(packets)
    assert ("192.168.1.102", "192.168.1.121", 50299, 502, "tcp") in manager.predictor.pipeline.flow_aggregator.active_flows

    # Explicit termination: stop_simulation flushes all pending flows
    res = manager.stop_simulation()
    assert res["status"] == "STOPPED"
    assert len(manager.predictor.pipeline.flow_aggregator.active_flows) == 0

    # Flow must now be in recent_flows
    matching = [f for f in manager.recent_flows if "50299" in f["flow_id"]]
    assert len(matching) == 1
    assert matching[0]["flow_id"] == "192.168.1.102:50299->192.168.1.121:502"


def test_benign_traffic_across_scenario_switches():
    """Test 4: Verifies that switching threat scenarios cleanly isolates state and

    benign baseline traffic produces 0 false positives across scenario switches.
    """
    manager = PlatformStateManager(seed=42)

    # 1. Start in Benign Normal
    manager.set_scenario(ScenarioType.BENIGN_NORMAL)
    step1_alerts = []
    for _ in range(5):
        step1_alerts.extend(manager.step_simulation(count=15))

    fp_1 = [a for a in step1_alerts if a["is_anomaly"]]
    assert len(fp_1) == 0, f"Expected 0 FPs in initial benign run, got {len(fp_1)}"

    # 2. Switch to Mirai Botnet Flood
    manager.set_scenario(ScenarioType.MIRAI_BOTNET_FLOOD)
    for _ in range(3):
        manager.step_simulation(count=20)

    # 3. Switch back to Benign Normal: state must be fully reset
    manager.set_scenario(ScenarioType.BENIGN_NORMAL)
    step2_alerts = []
    for _ in range(5):
        step2_alerts.extend(manager.step_simulation(count=15))

    fp_2 = [a for a in step2_alerts if a["is_anomaly"]]
    assert len(fp_2) == 0, f"Expected 0 FPs after scenario switch back to benign, got {len(fp_2)}"


def test_correct_alert_to_flow_matching_for_xai():
    """Test 5: Verifies that alerts and flows retain exact flow IDs and canonical feature vectors,

    allowing /api/explain to look up flows by flow_id and compute valid XAI attributions.
    """
    state = PlatformStateManager(seed=42)
    state.set_scenario(ScenarioType.MIRAI_BOTNET_FLOOD)
    state.step_simulation(count=30)

    # Verify at least one alert was generated
    assert len(state.recent_alerts) > 0
    target_alert = state.recent_alerts[-1]
    flow_id = target_alert["flow_id"]
    raw_features = target_alert["raw_features"]

    assert flow_id.count(":") == 2
    assert "->" in flow_id
    assert len(raw_features) == 21
    for feat_name in CANONICAL_21_FEATURE_NAMES:
        assert feat_name in raw_features

    # Invoke /api/explain with flow_id via invoke_endpoint
    app = create_app(state=state)
    resp = invoke_endpoint(app, "/api/explain", method="POST", json_body={"flow_id": flow_id})
    assert resp.status_code == 200

    xai_data = json.loads(resp.body)
    assert "error" not in xai_data
    assert xai_data["flow_id"] == flow_id
    assert "top_k_features" in xai_data
    assert len(xai_data["top_k_features"]) > 0
    assert xai_data["final_decision"] == "ATTACK"
    assert xai_data["option_c_probability"] >= 0.50


def test_multi_packet_flow_split_across_batches_without_lookahead():
    """Test 6: Verifies that multi-packet flows split across generic packet batches

    without any simulator queue lookahead remain pending across batch boundaries
    rather than being severed.
    """
    manager = PlatformStateManager(seed=42)
    t0 = 50.0

    batch1 = [
        GeneratedPacket(
            timestamp=t0,
            src_ip="192.168.1.55",
            dst_ip="192.168.1.1",
            src_port=44444,
            dst_port=80,
            proto="tcp",
            length=60,
            syn=1,
            ack=0,
            ground_truth=1,
            scenario_name="GENERIC_STREAM",
        ),
        GeneratedPacket(
            timestamp=t0 + 0.005,
            src_ip="192.168.1.55",
            dst_ip="192.168.1.1",
            src_port=44444,
            dst_port=80,
            proto="tcp",
            length=100,
            syn=0,
            ack=1,
            ground_truth=1,
            scenario_name="GENERIC_STREAM",
        ),
    ]

    # Ingest batch 1 without lookahead buffer
    alerts1 = manager._process_batch_of_packets(batch1, lookahead_buffer=None)
    assert len(alerts1) == 0, "Active flow was severed prematurely at batch boundary"

    # Flow must remain active in flow aggregator
    flow_key = ("192.168.1.1", "192.168.1.55", 80, 44444, "tcp")
    assert flow_key in manager.predictor.pipeline.flow_aggregator.active_flows

    batch2 = [
        GeneratedPacket(
            timestamp=t0 + 0.010,
            src_ip="192.168.1.55",
            dst_ip="192.168.1.1",
            src_port=44444,
            dst_port=80,
            proto="tcp",
            length=120,
            syn=0,
            ack=1,
            ground_truth=1,
            scenario_name="GENERIC_STREAM",
        ),
    ]

    # Ingest batch 2 without lookahead buffer (inactivity timeout has not elapsed)
    alerts2 = manager._process_batch_of_packets(batch2, lookahead_buffer=None)
    assert len(alerts2) == 0, "Active flow should remain pending during active burst"

    active_flow = manager.predictor.pipeline.flow_aggregator.active_flows[flow_key]
    assert active_flow.pkts_src == 3

    # Explicit finalization at stream end
    final_alerts = manager.finalize_pending_flows()
    assert len(final_alerts) == 1
    final_flow = manager.recent_flows[-1]
    assert final_flow["flow_id"] == "192.168.1.55:44444->192.168.1.1:80"
    assert final_flow["raw_features"]["flow_duration"] == pytest.approx(0.010, rel=1e-3)


def test_flow_expiration_after_inactivity_without_lookahead():
    """Test 7: Verifies that flows in a lookahead-free stream naturally expire and

    finalize when subsequent traffic exceeds the inactivity timeout.
    """
    manager = PlatformStateManager(seed=42)

    # Packet 1 on Flow A at t=10.0
    batch1 = [
        GeneratedPacket(
            timestamp=10.0,
            src_ip="192.168.1.60",
            dst_ip="192.168.1.1",
            src_port=55555,
            dst_port=80,
            proto="tcp",
            length=60,
            syn=1,
            ack=0,
            ground_truth=0,
            scenario_name="BENIGN_STREAM",
        ),
    ]
    manager._process_batch_of_packets(batch1, lookahead_buffer=None)
    flow_key_a = ("192.168.1.1", "192.168.1.60", 80, 55555, "tcp")
    assert flow_key_a in manager.predictor.pipeline.flow_aggregator.active_flows

    # Packet 2 on Flow B at t=30.0 (20.0s later > 15.0s inactivity timeout)
    batch2 = [
        GeneratedPacket(
            timestamp=30.0,
            src_ip="192.168.1.70",
            dst_ip="192.168.1.1",
            src_port=55556,
            dst_port=443,
            proto="tcp",
            length=60,
            syn=1,
            ack=0,
            ground_truth=0,
            scenario_name="BENIGN_STREAM",
        ),
    ]
    alerts2 = manager._process_batch_of_packets(batch2, lookahead_buffer=None)

    # Flow A must have expired and been finalized automatically
    assert any(a["flow_id"] == "192.168.1.60:55555->192.168.1.1:80" for a in alerts2)
    assert flow_key_a not in manager.predictor.pipeline.flow_aggregator.active_flows


def test_genuine_single_packet_rst_traffic():
    """Test 8: Verifies that legitimate single-packet termination frames (e.g. TCP RST)

    finalize immediately without waiting for timeouts or lookahead.
    """
    manager = PlatformStateManager(seed=42)

    rst_pkt = [
        GeneratedPacket(
            timestamp=100.0,
            src_ip="192.168.1.80",
            dst_ip="192.168.1.1",
            src_port=59999,
            dst_port=22,
            proto="tcp",
            length=40,
            syn=0,
            ack=0,
            rst=1,
            ground_truth=1,
            scenario_name="RST_PROBE",
        )
    ]

    alerts = manager._process_batch_of_packets(rst_pkt, lookahead_buffer=None)
    assert len(alerts) == 1, "RST packet was not finalized immediately upon receipt"
    assert alerts[0]["flow_id"] == "192.168.1.80:59999->192.168.1.1:22"
    assert ("192.168.1.1", "192.168.1.80", 22, 59999, "tcp") not in manager.predictor.pipeline.flow_aggregator.active_flows
