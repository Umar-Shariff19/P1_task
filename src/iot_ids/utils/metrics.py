"""Structured Operational Metrics Collector for Multi-Level IoT IDS.

Tracks packets processed, flows completed, alerts emitted, inference latency (mean, min, max, p95),
error counts, and active memory footprints for production observability.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List
import numpy as np


@dataclass
class OperationalMetricsSummary:
    """Snapshot summary of operational pipeline metrics."""

    packets_processed: int = 0
    flows_completed: int = 0
    alerts_emitted: int = 0
    errors_encountered: int = 0
    active_flows_in_memory: int = 0
    latency_count: int = 0
    latency_mean_ms: float = 0.0
    latency_min_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_p95_ms: float = 0.0
    uptime_seconds: float = 0.0


class MetricsCollector:
    """Thread-safe operational metrics tracking collector."""

    def __init__(self, max_latency_samples: int = 10000):
        self._lock = threading.Lock()
        self.start_time: float = time.time()
        self.packets_processed: int = 0
        self.flows_completed: int = 0
        self.alerts_emitted: int = 0
        self.errors_encountered: int = 0
        self.active_flows_in_memory: int = 0
        self.max_latency_samples: int = max_latency_samples
        self.latency_samples_ms: List[float] = []

    def reset(self) -> None:
        """Resets all metrics counters."""
        with self._lock:
            self.start_time = time.time()
            self.packets_processed = 0
            self.flows_completed = 0
            self.alerts_emitted = 0
            self.errors_encountered = 0
            self.active_flows_in_memory = 0
            self.latency_samples_ms.clear()

    def record_packet(self) -> None:
        with self._lock:
            self.packets_processed += 1

    def record_flow(self) -> None:
        with self._lock:
            self.flows_completed += 1

    def record_alert(self) -> None:
        with self._lock:
            self.alerts_emitted += 1

    def record_error(self) -> None:
        with self._lock:
            self.errors_encountered += 1

    def record_latency(self, latency_ms: float) -> None:
        with self._lock:
            if len(self.latency_samples_ms) >= self.max_latency_samples:
                self.latency_samples_ms.pop(0)
            self.latency_samples_ms.append(float(latency_ms))

    def update_active_flows(self, count: int) -> None:
        with self._lock:
            self.active_flows_in_memory = count

    def get_summary(self) -> OperationalMetricsSummary:
        """Returns a snapshot summary of current operational metrics."""
        with self._lock:
            uptime = time.time() - self.start_time
            samples = list(self.latency_samples_ms)
            packets = self.packets_processed
            flows = self.flows_completed
            alerts = self.alerts_emitted
            errors = self.errors_encountered
            active_flows = self.active_flows_in_memory

        if samples:
            arr = np.array(samples)
            l_mean = float(np.mean(arr))
            l_min = float(np.min(arr))
            l_max = float(np.max(arr))
            l_p95 = float(np.percentile(arr, 95))
        else:
            l_mean = l_min = l_max = l_p95 = 0.0

        return OperationalMetricsSummary(
            packets_processed=packets,
            flows_completed=flows,
            alerts_emitted=alerts,
            errors_encountered=errors,
            active_flows_in_memory=active_flows,
            latency_count=len(samples),
            latency_mean_ms=l_mean,
            latency_min_ms=l_min,
            latency_max_ms=l_max,
            latency_p95_ms=l_p95,
            uptime_seconds=uptime,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self.get_summary())
