"""Production Inference Engine for Multi-Level IoT Intrusion Detection.

Provides a clean predictor API for canonical flows, raw packet streams, and batch DataFrames,
delegating pipeline execution to IDSSystemPipeline while tracking operational metrics and health status.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Any, Iterable, List, Optional, Tuple, Union
import pandas as pd

from iot_ids.data.flow_object import CanonicalFlow
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.registry.manager import ModelRegistry
from iot_ids.utils.metrics import MetricsCollector, OperationalMetricsSummary
from iot_ids.utils.sinks import AlertDeliveryError, DeliveryTarget, deliver_alert


@dataclass(frozen=True)
class PacketIngestionResult:
    """Result of ingesting or finalizing packet flows.

    Processing errors are raised to the caller. An empty ``alerts`` tuple with
    ``active_flow_count > 0`` means that flow data is pending, not that
    processing failed.
    """

    alerts: Tuple[Dict[str, Any], ...]
    active_flow_count: int

    @property
    def has_pending_flows(self) -> bool:
        return self.active_flow_count > 0


class IDSPredictor:
    """Deployable inference predictor for multi-level IoT intrusion detection."""

    def __init__(
        self,
        pipeline: IDSSystemPipeline,
        *,
        delivery_target: Optional[DeliveryTarget] = None,
    ):
        self.pipeline = pipeline
        self.metrics = MetricsCollector()
        self.delivery_target = delivery_target
        self._lock = threading.RLock()

    def _deliver_alert(
        self,
        alert: Dict[str, Any],
        delivery_target: Optional[DeliveryTarget] = None,
    ) -> None:
        target = self.delivery_target if delivery_target is None else delivery_target
        if target is None:
            return
        result = deliver_alert(alert, target)
        if not result.successful:
            raise AlertDeliveryError(result)

    @classmethod
    def from_artifact(
        cls,
        artifact_dir: Union[str, Path],
        *,
        authorization_provider: Optional[Any] = None,
        policy_document: Optional[Dict[str, Any]] = None,
    ) -> IDSPredictor:
        """Instantiates an IDSPredictor from a saved ModelRegistry pipeline directory."""
        pipeline = ModelRegistry.load_pipeline(
            Path(artifact_dir),
            authorization_provider=authorization_provider,
            policy_document=policy_document,
        )
        return cls(pipeline=pipeline)

    def health_check(self) -> Dict[str, Any]:
        """Returns health status inspection combining pipeline state and operational metrics."""
        with self._lock:
            pipe_health = self.pipeline.health_check()
            summary = self.metrics.to_dict()
            return {
                "status": pipe_health["status"],
                "readiness_scope": pipe_health["readiness_scope"],
                "pipeline": pipe_health,
                "metrics": summary,
            }

    def reset_state(self) -> None:
        """Resets temporal and behavioral state buffers and operational metrics."""
        with self._lock:
            self.pipeline.reset_state()
            self.metrics.reset()

    def predict_flow(self, flow: CanonicalFlow) -> Dict[str, Any]:
        """Runs end-to-end inference on a single CanonicalFlow object with latency tracking."""
        with self._lock:
            return self._predict_flow(flow, delivery_target=None)

    def _predict_flow(
        self,
        flow: CanonicalFlow,
        *,
        delivery_target: Optional[DeliveryTarget],
    ) -> Dict[str, Any]:
        with self._lock:
            t0 = time.time()
            try:
                alert = self.pipeline.process_flow(flow)
                t_lat = (time.time() - t0) * 1000.0
                self.metrics.record_flow()
                self.metrics.record_latency(t_lat)
                self._deliver_alert(alert, delivery_target)
                if alert.get("is_anomaly", False):
                    self.metrics.record_alert()
                return alert
            except Exception:
                self.metrics.record_error()
                raise

    def predict_dataframe(self, df_flows: pd.DataFrame) -> List[Dict[str, Any]]:
        """Runs batch inference over a DataFrame of canonical flow attributes."""
        with self._lock:
            t0 = time.time()
            try:
                alerts = self.pipeline.process_dataframe(df_flows)
                t_lat = (time.time() - t0) * 1000.0 / max(len(alerts), 1)
                for a in alerts:
                    self.metrics.record_flow()
                    self.metrics.record_latency(t_lat)
                    self._deliver_alert(a)
                    if a.get("is_anomaly", False):
                        self.metrics.record_alert()
                return alerts
            except Exception:
                self.metrics.record_error()
                raise

    def ingest_packet(
        self,
        packet_dict: Dict[str, Any],
        *,
        delivery_target: Optional[DeliveryTarget] = None,
    ) -> PacketIngestionResult:
        """Ingest one packet; raise processing errors instead of reporting them as pending.

        The aggregator may complete one prior flow while retaining the current
        flow. Metrics count packet attempts, successful flow predictions, and
        each failed aggregation or prediction once.
        """
        with self._lock:
            self.metrics.record_packet()
            try:
                completed_flow = self.pipeline.flow_aggregator.add_packet(packet_dict)
            except Exception:
                self.metrics.record_error()
                raise

            active_flow_count = len(self.pipeline.flow_aggregator.active_flows)
            self.metrics.update_active_flows(active_flow_count)
            alerts = () if completed_flow is None else (
                self._predict_flow(completed_flow, delivery_target=delivery_target),
            )
            return PacketIngestionResult(alerts, active_flow_count)

    def process_raw_packet(self, packet_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Backward-compatible packet API; processing failures now propagate.

        Returns an alert when ingestion completes a flow and ``None`` while
        flows remain pending. Call :meth:`ingest_packet` when callers need the
        explicit pending-flow count.
        """
        with self._lock:
            result = self.ingest_packet(packet_dict)
            return result.alerts[0] if result.alerts else None

    def finalize_pending_flows(
        self,
        *,
        delivery_target: Optional[DeliveryTarget] = None,
    ) -> PacketIngestionResult:
        """Flush pending flows through normal inference exactly once."""
        with self._lock:
            try:
                flows = self.pipeline.flow_aggregator.flush()
            except Exception:
                self.metrics.record_error()
                raise

            self.metrics.update_active_flows(len(self.pipeline.flow_aggregator.active_flows))
            alerts = tuple(
                self._predict_flow(flow, delivery_target=delivery_target)
                for flow in flows
            )
            return PacketIngestionResult(alerts, len(self.pipeline.flow_aggregator.active_flows))

    def process_packet_stream(
        self,
        packets: Iterable[Dict[str, Any]],
        *,
        on_alert: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Process a finite packet iterable and flush only after normal exhaustion.

        If iteration, packet processing, or inference raises, finalization is
        skipped and the failure propagates to the caller.
        """
        with self._lock:
            if self.delivery_target is not None and on_alert is not None:
                raise ValueError("Configure either delivery_target or on_alert, not both")
            target = self.delivery_target if on_alert is None else on_alert
            alerts: List[Dict[str, Any]] = []
            for packet in packets:
                packet_alerts = self.ingest_packet(packet, delivery_target=target).alerts
                alerts.extend(packet_alerts)
            final_alerts = self.finalize_pending_flows(delivery_target=target).alerts
            alerts.extend(final_alerts)
            return alerts
