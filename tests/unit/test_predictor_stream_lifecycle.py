"""Synthetic-only tests for packet ingestion and end-of-stream handling."""
from __future__ import annotations

import numpy as np
import pytest

from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.inference.predictor import IDSPredictor
from iot_ids.pipeline.system import IDSSystemPipeline


class IdentityPreprocessor:
    def transform(self, frame):
        return frame.to_numpy(dtype=float)


class SyntheticProbabilityModel:
    classes_ = np.array([0, 1])

    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = 0

    def predict_proba(self, features):
        self.calls += 1
        if self.fail:
            raise RuntimeError("synthetic inference failure")
        positive = np.full(len(features), 0.8, dtype=float)
        return np.column_stack((1.0 - positive, positive))


def make_predictor(*, model=None):
    model = model or SyntheticProbabilityModel()
    pipeline = IDSSystemPipeline(
        model=model,
        preprocessor=IdentityPreprocessor(),
        feature_profile="synthetic_packet_lifecycle",
        feature_names=list(CANONICAL_21_FEATURE_NAMES),
    )
    return IDSPredictor(pipeline), model


def packet(*, flow=1, timestamp=10.0, src_port=None):
    port = 20_000 + flow if src_port is None else src_port
    return {
        "timestamp": timestamp,
        "src_ip": "192.0.2.10",
        "dst_ip": f"198.51.100.{flow}",
        "src_port": port,
        "dst_port": 443,
        "protocol": "tcp",
        "length": 120,
        "syn": 1,
        "label": 0,
        "attack_category": "SYNTHETIC_FIXTURE",
    }


def test_ingestion_exposes_pending_state_without_emitting_premature_alert():
    predictor, model = make_predictor()

    result = predictor.ingest_packet(packet())

    assert result.alerts == ()
    assert result.active_flow_count == 1
    assert result.has_pending_flows is True
    assert model.calls == 0
    assert predictor.metrics.get_summary().errors_encountered == 0


def test_finalization_emits_pending_flow_and_is_idempotent():
    predictor, model = make_predictor()
    predictor.ingest_packet(packet())

    first = predictor.finalize_pending_flows()
    second = predictor.finalize_pending_flows()

    assert len(first.alerts) == 1
    assert first.alerts[0]["prediction_prob"] == pytest.approx(0.8)
    assert first.active_flow_count == 0
    assert first.has_pending_flows is False
    assert second.alerts == ()
    summary = predictor.metrics.get_summary()
    assert summary.flows_completed == 1
    assert summary.errors_encountered == 0
    assert summary.active_flows_in_memory == 0
    assert model.calls == 1


def test_finalization_processes_multiple_flows_once_each():
    predictor, model = make_predictor()
    predictor.ingest_packet(packet(flow=1))
    predictor.ingest_packet(packet(flow=2))

    result = predictor.finalize_pending_flows()

    assert len(result.alerts) == 2
    assert {alert["dst_ip"] for alert in result.alerts} == {
        "198.51.100.1", "198.51.100.2"
    }
    assert predictor.finalize_pending_flows().alerts == ()
    assert model.calls == 2
    assert predictor.metrics.get_summary().flows_completed == 2


def test_flow_completed_during_ingestion_is_not_emitted_twice_on_flush():
    predictor, model = make_predictor()

    pending = predictor.ingest_packet(packet(timestamp=10.0))
    expired = predictor.ingest_packet(packet(timestamp=30.0))
    final = predictor.finalize_pending_flows()

    assert pending.alerts == ()
    assert len(expired.alerts) == 1
    assert len(final.alerts) == 1
    assert model.calls == 2
    assert predictor.metrics.get_summary().flows_completed == 2


def test_empty_finalization_is_safe_and_does_not_change_success_counts():
    predictor, model = make_predictor()

    result = predictor.finalize_pending_flows()

    assert result.alerts == ()
    assert result.active_flow_count == 0
    assert predictor.metrics.get_summary().flows_completed == 0
    assert model.calls == 0


def test_malformed_packet_raises_and_counts_one_error_not_pending_success():
    predictor, _ = make_predictor()

    with pytest.raises(ValueError):
        predictor.ingest_packet(packet(src_port="not-a-port"))

    summary = predictor.metrics.get_summary()
    assert summary.packets_processed == 1
    assert summary.errors_encountered == 1
    assert summary.active_flows_in_memory == 0


def test_inference_failure_during_finalization_propagates_and_counts_once():
    predictor, model = make_predictor(model=SyntheticProbabilityModel(fail=True))
    predictor.ingest_packet(packet())

    with pytest.raises(RuntimeError, match="synthetic inference failure"):
        predictor.finalize_pending_flows()

    summary = predictor.metrics.get_summary()
    assert summary.errors_encountered == 1
    assert summary.flows_completed == 0
    assert summary.active_flows_in_memory == 0
    assert model.calls == 1


def test_inference_failure_on_packet_completion_is_not_reported_as_pending():
    predictor, _ = make_predictor(model=SyntheticProbabilityModel(fail=True))
    predictor.ingest_packet(packet(timestamp=10.0))

    with pytest.raises(RuntimeError, match="synthetic inference failure"):
        predictor.ingest_packet(packet(timestamp=30.0))

    summary = predictor.metrics.get_summary()
    assert summary.packets_processed == 2
    assert summary.errors_encountered == 1
    assert summary.flows_completed == 0
    assert summary.active_flows_in_memory == 1


def test_finite_packet_stream_flushes_after_normal_exhaustion():
    predictor, model = make_predictor()
    delivered = []

    alerts = predictor.process_packet_stream(
        [packet(timestamp=10.0), packet(timestamp=11.0)],
        on_alert=delivered.append,
    )

    assert len(alerts) == 1
    assert delivered == alerts
    assert alerts[0]["prediction_prob"] == pytest.approx(0.8)
    assert predictor.pipeline.flow_aggregator.active_flows == {}
    assert predictor.metrics.get_summary().flows_completed == 1
    assert model.calls == 1


def test_failed_packet_iterable_does_not_finalize_pending_flows():
    predictor, model = make_predictor()

    def failing_stream():
        yield packet()
        raise RuntimeError("synthetic source failure")

    with pytest.raises(RuntimeError, match="synthetic source failure"):
        predictor.process_packet_stream(failing_stream())

    assert len(predictor.pipeline.flow_aggregator.active_flows) == 1
    assert predictor.metrics.get_summary().flows_completed == 0
    assert model.calls == 0


def test_legacy_packet_method_keeps_pending_and_alert_return_shape():
    predictor, _ = make_predictor()

    assert predictor.process_raw_packet(packet(timestamp=10.0)) is None
    emitted = predictor.process_raw_packet(packet(timestamp=30.0))

    assert isinstance(emitted, dict)
    assert emitted["prediction_prob"] == pytest.approx(0.8)
