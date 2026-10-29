"""End-to-End Safe Integration Test: Packet to Multi-Sink Alert.

Validates the full operational pipeline entirely using synthetic data without
accessing restricted datasets or production checkpoints:
1. Synthetic packet generation (Scapy and dictionary frames)
2. Flow aggregation and session state management
3. 21-feature canonical multi-level extraction
4. Feature schema validation and preprocessing
5. Model inference and calibrated thresholding
6. Structured alert generation (IDSAlertOutput contract)
7. Multi-sink delivery (JSONL file sink + secure Webhook sink)
8. Operational metrics and health check reporting
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from iot_ids.adaptation.calibration import TargetThresholdCalibrator
from iot_ids.data.flow_aggregator import FlowAggregator
from iot_ids.data.flow_object import CanonicalFlow
from iot_ids.experiments.preprocessing import FeaturePreprocessor
from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.inference.predictor import IDSPredictor
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.utils.sinks import JSONLFileSink, MultiAlertSink, WebhookAlertSink

try:
    import scapy.all as scapy
    from scapy.layers.inet import IP, TCP
    from scapy.layers.l2 import Ether
    from iot_ids.data.packet_capture import scapy_to_canonical_packet
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False


@pytest.fixture
def synthetic_ids_pipeline():
    """Builds a fully functional, self-contained pipeline using synthetic training data."""
    rng = np.random.default_rng(42)
    n_samples = 80
    feature_names = list(CANONICAL_21_FEATURE_NAMES)

    # Generate synthetic training features
    synthetic_data = rng.uniform(0.0, 10.0, size=(n_samples, len(feature_names)))
    df_train = pd.DataFrame(synthetic_data, columns=feature_names)
    df_train["proto_tcp"] = 1.0
    df_train["proto_udp"] = 0.0
    df_train["proto_icmp"] = 0.0
    df_train["proto_other"] = 0.0
    y_train = rng.choice([0, 1], size=n_samples, p=[0.7, 0.3])

    preprocessor = FeaturePreprocessor(feature_names=feature_names)
    X_proc = preprocessor.fit_transform(df_train)

    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_proc, y_train)

    calibrator = TargetThresholdCalibrator(default_threshold=0.50)
    calibrator.fit(np.asarray(model.predict_proba(X_proc)[:, 1]), y_train)

    pipeline = IDSSystemPipeline(
        model=model,
        preprocessor=preprocessor,
        feature_profile="full_multilevel",
        feature_names=feature_names,
        calibrator=calibrator,
        decision_threshold=0.5,
    )
    return pipeline


def test_safe_packet_to_alert_end_to_end(synthetic_ids_pipeline, tmp_path):
    # Setup temporary file sink
    alert_log_file = tmp_path / "alerts.jsonl"
    jsonl_sink = JSONLFileSink(alert_log_file)

    # Setup mocked Webhook sink
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.code = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        webhook_sink = WebhookAlertSink(
            "http://127.0.0.1:8443/alerts",
            auth_header="Bearer e2e-synthetic-test-token",
            allow_insecure_http=True,
            allow_local=True,
        )

        multi_sink = MultiAlertSink([jsonl_sink, webhook_sink])
        predictor = IDSPredictor(synthetic_ids_pipeline, delivery_target=multi_sink)

        # 1. Health check verification
        health = predictor.health_check()
        assert health["status"] == "HEALTHY"
        assert health["pipeline"]["model_loaded"] is True
        assert health["pipeline"]["preprocessor_loaded"] is True
        assert health["pipeline"]["components"]["model"] == "READY"
        assert health["pipeline"]["components"]["preprocessor"] == "READY"

        # 2. Ingest synthetic packets
        # Ingest packets from multiple synthetic flows
        # Flow 1: 3 packets, normal activity
        packets_flow1 = [
            {
                "timestamp": 100.0,
                "src_ip": "192.168.1.10",
                "dst_ip": "10.0.0.5",
                "src_port": 50001,
                "dst_port": 80,
                "proto": "tcp",
                "length": 60,
                "syn": 1,
                "ack": 0,
                "rst": 0,
            },
            {
                "timestamp": 100.5,
                "src_ip": "10.0.0.5",
                "dst_ip": "192.168.1.10",
                "src_port": 80,
                "dst_port": 50001,
                "proto": "tcp",
                "length": 60,
                "syn": 1,
                "ack": 1,
                "rst": 0,
            },
            {
                "timestamp": 101.0,
                "src_ip": "192.168.1.10",
                "dst_ip": "10.0.0.5",
                "src_port": 50001,
                "dst_port": 80,
                "proto": "tcp",
                "length": 500,
                "syn": 0,
                "ack": 1,
                "rst": 0,
            },
        ]

        # Ingest flow 1 packets (flows remain pending)
        for pkt in packets_flow1:
            res = predictor.ingest_packet(pkt)
            assert res.active_flow_count >= 1

        # Flow 2: Ingested using Scapy if available, else dict
        if HAS_SCAPY:
            scapy_pkt = (
                Ether()
                / IP(src="192.168.1.20", dst="10.0.0.8")
                / TCP(sport=54321, dport=443, flags="S")
            )
            parsed_pkt = scapy_to_canonical_packet(scapy_pkt)
            assert parsed_pkt is not None
            predictor.ingest_packet(parsed_pkt)
        else:
            predictor.ingest_packet({
                "timestamp": 102.0,
                "src_ip": "192.168.1.20",
                "dst_ip": "10.0.0.8",
                "src_port": 54321,
                "dst_port": 443,
                "proto": "tcp",
                "length": 74,
                "syn": 1,
            })

        # 3. Finalize all pending flows
        final_res = predictor.finalize_pending_flows()
        assert len(final_res.alerts) == 2  # Both flows finalized

        # 4. Verify Alert Schema Contract for emitted alerts
        for alert in final_res.alerts:
            assert "flow_id" in alert
            assert "src_ip" in alert
            assert "dst_ip" in alert
            assert "prediction_prob" in alert
            assert 0.0 <= alert["prediction_prob"] <= 1.0
            assert "decision_threshold" in alert
            assert "is_anomaly" in alert
            assert isinstance(alert["is_anomaly"], bool)
            assert "risk_score" in alert
            assert "risk_level" in alert
            assert alert["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            assert "raw_features" in alert
            assert len(alert["raw_features"]) == 21

        # 5. Verify JSONL File Delivery
        assert alert_log_file.exists()
        log_lines = alert_log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(log_lines) == 2
        for line in log_lines:
            record = json.loads(line)
            assert "timestamp_utc" in record
            assert "prediction_prob" in record
            assert "flow_id" in record

        # 6. Verify Webhook Sink Delivery
        assert mock_urlopen.call_count == 2
        for call_args in mock_urlopen.call_args_list:
            req = call_args[0][0]
            assert req.full_url == "http://127.0.0.1:8443/alerts"
            assert req.headers.get("Authorization") == "Bearer e2e-synthetic-test-token"
            body = json.loads(req.data.decode("utf-8"))
            assert "risk_level" in body

        # 7. Verify Operational Metrics
        metrics = predictor.metrics.get_summary()
        expected_pkts = 4
        assert metrics.packets_processed == expected_pkts
        assert metrics.flows_completed == 2
        assert metrics.latency_count == 2
        assert metrics.latency_mean_ms > 0.0
        assert metrics.errors_encountered == 0
        assert metrics.active_flows_in_memory == 0
