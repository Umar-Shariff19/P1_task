"""Concurrency and thread-safety tests for FlowAggregator, MetricsCollector, and IDSPredictor."""
from __future__ import annotations

import concurrent.futures
import threading
import numpy as np
import pytest

from iot_ids.data.flow_aggregator import FlowAggregator
from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.inference.predictor import IDSPredictor
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.utils.metrics import MetricsCollector


class IdentityPreprocessor:
    feature_names = list(CANONICAL_21_FEATURE_NAMES)

    def transform(self, frame):
        return frame.to_numpy(dtype=float)


class SyntheticProbabilityModel:
    classes_ = np.array([0, 1])

    def __init__(self):
        self.lock = threading.Lock()
        self.calls = 0

    def predict_proba(self, features):
        with self.lock:
            self.calls += 1
        positive = np.full(len(features), 0.7, dtype=float)
        return np.column_stack((1.0 - positive, positive))


def make_predictor():
    model = SyntheticProbabilityModel()
    pipeline = IDSSystemPipeline(
        model=model,
        preprocessor=IdentityPreprocessor(),
        feature_profile="synthetic_concurrency_test",
        feature_names=list(CANONICAL_21_FEATURE_NAMES),
    )
    return IDSPredictor(pipeline), model


def test_metrics_collector_concurrency():
    collector = MetricsCollector()
    n_workers = 10
    ops_per_worker = 100

    def worker_tasks():
        for _ in range(ops_per_worker):
            collector.record_packet()
            collector.record_flow()
            collector.record_alert()
            collector.record_latency(1.5)
            collector.update_active_flows(42)

    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [executor.submit(worker_tasks) for _ in range(n_workers)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    summary = collector.get_summary()
    assert summary.packets_processed == n_workers * ops_per_worker
    assert summary.flows_completed == n_workers * ops_per_worker
    assert summary.alerts_emitted == n_workers * ops_per_worker
    assert summary.latency_count == n_workers * ops_per_worker
    assert summary.active_flows_in_memory == 42


def test_flow_aggregator_concurrency():
    aggregator = FlowAggregator(inactivity_timeout=5.0)
    n_threads = 8
    packets_per_thread = 50

    def push_packets(thread_id: int):
        for i in range(packets_per_thread):
            pkt = {
                "timestamp": float(100.0 + i * 0.1),
                "src_ip": f"10.0.0.{thread_id}",
                "dst_ip": "10.0.0.1",
                "src_port": 10000 + thread_id,
                "dst_port": 80,
                "proto": "tcp",
                "length": 64,
                "syn": 1 if i == 0 else 0,
                "ack": 1 if i > 0 else 0,
            }
            aggregator.add_packet(pkt)

    with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
        futures = [executor.submit(push_packets, tid) for tid in range(n_threads)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    flows = aggregator.flush()
    assert len(flows) == n_threads
    assert len(aggregator.active_flows) == 0


def test_ids_predictor_concurrency():
    predictor, model = make_predictor()
    n_threads = 6
    packets_per_thread = 30

    def stream_worker(thread_id: int):
        for i in range(packets_per_thread):
            pkt = {
                "timestamp": float(10.0 + i * 0.1),
                "src_ip": f"192.168.1.{thread_id}",
                "dst_ip": "192.168.1.100",
                "src_port": 20000 + thread_id,
                "dst_port": 443,
                "protocol": "tcp",
                "length": 100,
                "syn": 1 if i == 0 else 0,
            }
            res = predictor.ingest_packet(pkt)
            assert res.active_flow_count >= 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
        futures = [executor.submit(stream_worker, tid) for tid in range(n_threads)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    # Concurrent flush
    final_res = predictor.finalize_pending_flows()
    assert len(final_res.alerts) == n_threads
    summary = predictor.metrics.get_summary()
    assert summary.packets_processed == n_threads * packets_per_thread
    assert summary.flows_completed == n_threads


def test_concurrent_ingest_and_reset_race():
    """Verify that concurrent packet ingestion and state resets do not race or deadlock."""
    predictor, model = make_predictor()
    stop_event = threading.Event()
    exceptions = []

    def ingester(tid: int):
        i = 0
        while not stop_event.is_set() and i < 100:
            pkt = {
                "timestamp": float(50.0 + i * 0.05),
                "src_ip": f"172.16.0.{tid}",
                "dst_ip": "172.16.0.1",
                "src_port": 30000 + tid,
                "dst_port": 80,
                "protocol": "tcp",
                "length": 80,
                "syn": 1 if i == 0 else 0,
            }
            try:
                predictor.ingest_packet(pkt)
            except Exception as e:
                exceptions.append(e)
            i += 1

    def reader():
        while not stop_event.is_set():
            try:
                health = predictor.health_check()
                assert health["status"] == "HEALTHY"
            except Exception as e:
                exceptions.append(e)

    def resetter():
        for _ in range(5):
            try:
                predictor.reset_state()
            except Exception as e:
                exceptions.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        f_ingest = [executor.submit(ingester, i) for i in range(4)]
        f_read = [executor.submit(reader) for _ in range(2)]
        f_reset = executor.submit(resetter)

        # Wait for resetter and ingesters to complete
        f_reset.result()
        for f in f_ingest:
            f.result()
        stop_event.set()
        for f in f_read:
            f.result()

    assert len(exceptions) == 0
