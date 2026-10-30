"""Platform State Manager and Event Store for IoT IDS Dashboard.

Coordinates the real-time IoT traffic simulation engine, multi-level pipeline inference,
adversarial attack evaluation laboratory, explainability queries, and alert distribution.
"""
from __future__ import annotations

import asyncio
import collections
import logging
import threading
import time
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch

from iot_ids.adversarial.attacks import fgsm_attack, pgd_attack
from iot_ids.adversarial.evaluator import evaluate_adversarial_sample
from iot_ids.data.flow_aggregator import normalize_5tuple
from iot_ids.data.flow_object import CanonicalFlow
from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.inference.predictor import IDSPredictor
from iot_ids.models.synthetic_models import SyntheticModelSuite, get_default_model_suite
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.simulator.devices import create_default_iot_network
from iot_ids.simulator.generator import GeneratedPacket, IoTSimulator
from iot_ids.simulator.scenarios import ScenarioType, get_scenario
from iot_ids.xai.local_xai import explain_local_sample

logger = logging.getLogger(__name__)


class PlatformStateManager:
    """Thread-safe orchestrator managing simulator, inference pipeline, and event streams."""

    def __init__(
        self,
        seed: int = 42,
        model_mode: str = "synthetic",
        dataset_name: str = "ToN-IoT",
        authorization_provider: Optional[Any] = None,
        policy_document: Optional[Dict[str, Any]] = None,
    ):
        self._lock = threading.RLock()
        self.seed = seed
        self.model_mode = model_mode.lower()
        self.dataset_name = dataset_name
        self.authorization_provider = authorization_provider
        self.policy_document = policy_document

        # 1. Models & Pipeline
        if self.model_mode == "research":
            # Must raise immediately on authorization failure (fail-closed, no synthetic fallback)
            from iot_ids.models.research_models import load_research_model_suite

            self.model_suite = load_research_model_suite(
                dataset_name=dataset_name,
                authorization_provider=authorization_provider,
                policy_document=policy_document,
            )
        elif self.model_mode == "synthetic":
            self.model_suite: SyntheticModelSuite = get_default_model_suite(seed=seed)
        else:
            raise ValueError(f"Unknown model_mode: '{model_mode}'. Choose 'synthetic' or 'research'.")

        self.active_model_name: str = "option_c"
        self.pipeline: IDSSystemPipeline = self.model_suite.create_pipeline(model_name=self.active_model_name)
        self.predictor: IDSPredictor = IDSPredictor(pipeline=self.pipeline)

        # 2. Simulator
        self.simulator: IoTSimulator = IoTSimulator(seed=seed)
        self.traffic_interval: float = 0.25  # seconds between generator batches

        # 3. Background Generation Thread
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially

        # 4. State Buffers (bounded memory)
        self.recent_flows: collections.deque = collections.deque(maxlen=500)
        self.recent_alerts: collections.deque = collections.deque(maxlen=200)
        self.experiment_history: List[Dict[str, Any]] = []
        self._flow_metadata: Dict[str, Tuple[int, str, str]] = {}

        # 5. Metrics & Counters
        self.total_packets: int = 0
        self.total_flows: int = 0
        self.total_alerts: int = 0
        self.total_attacks_detected: int = 0
        self.start_time: float = time.time()

        # 6. Event Subscribers (sync callbacks and async queues)
        self._sync_listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._async_queues: List[asyncio.Queue] = []

    # -------------------------------------------------------------------------
    # Lifecycle & Simulator Controls
    # -------------------------------------------------------------------------

    def start_simulation(self, interval: Optional[float] = None) -> Dict[str, Any]:
        """Starts the background simulator thread."""
        with self._lock:
            if interval is not None and interval > 0.0:
                self.traffic_interval = interval

            if self._thread is not None and self._thread.is_alive():
                self._pause_event.set()
                return {"status": "ALREADY_RUNNING", "interval": self.traffic_interval}

            self._stop_event.clear()
            self._pause_event.set()
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="IoTSimulatorWorker",
                daemon=True,
            )
            self._thread.start()
            return {"status": "STARTED", "interval": self.traffic_interval}

    def pause_simulation(self) -> Dict[str, Any]:
        """Pauses the simulator loop without terminating the worker thread."""
        with self._lock:
            self._pause_event.clear()
            return {"status": "PAUSED"}

    def resume_simulation(self) -> Dict[str, Any]:
        """Resumes a paused simulation."""
        with self._lock:
            self._pause_event.set()
            return {"status": "RESUMED"}

    def stop_simulation(self) -> Dict[str, Any]:
        """Stops the simulator background thread cleanly."""
        with self._lock:
            self._stop_event.set()
            self._pause_event.set()  # Unblock if paused
            if self._thread is not None and self._thread.is_alive():
                self._thread.join(timeout=3.0)
            self._thread = None
            self.finalize_pending_flows()
            return {"status": "STOPPED"}

    def reset_simulation(self) -> Dict[str, Any]:
        """Resets simulator state, pipeline flow aggregator, and telemetry buffers."""
        with self._lock:
            was_running = self._thread is not None and self._thread.is_alive()
            self.stop_simulation()

            self.simulator.reset()
            self.predictor.reset_state()
            self.recent_flows.clear()
            self.recent_alerts.clear()
            self._flow_metadata.clear()

            self.total_packets = 0
            self.total_flows = 0
            self.total_alerts = 0
            self.total_attacks_detected = 0
            self.start_time = time.time()

            if was_running:
                self.start_simulation()

            return {"status": "RESET_COMPLETE"}

    def set_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Switches the active threat scenario in the simulator."""
        with self._lock:
            self.finalize_pending_flows()
            scenario = self.simulator.set_scenario(scenario_name)
            self.predictor.reset_state()
            self._flow_metadata.clear()
            return {
                "status": "SCENARIO_UPDATED",
                "scenario_name": scenario.name,
                "scenario_type": scenario.scenario_type.value,
                "description": scenario.description,
            }

    def set_active_model(self, model_name: str) -> Dict[str, Any]:
        """Changes the active inference model in the live pipeline."""
        with self._lock:
            new_pipeline = self.model_suite.create_pipeline(model_name=model_name)
            self.pipeline = new_pipeline
            self.predictor = IDSPredictor(pipeline=new_pipeline)
            self.active_model_name = model_name
            return {
                "status": "MODEL_UPDATED",
                "active_model": self.active_model_name,
                "health": self.predictor.health_check()["status"],
            }

    def switch_model_suite(
        self,
        mode: str,
        dataset_name: str = "ToN-IoT",
        authorization_provider: Optional[Any] = None,
        policy_document: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Switches between synthetic reference and authorized research model suites.

        Fails closed with exception if research mode is requested without valid authorization.
        Never falls back to synthetic models when research loading fails.
        """
        with self._lock:
            mode_clean = mode.lower()
            if mode_clean == "research":
                from iot_ids.models.research_models import load_research_model_suite

                prov = authorization_provider if authorization_provider is not None else self.authorization_provider
                pol = policy_document if policy_document is not None else self.policy_document

                new_suite = load_research_model_suite(
                    dataset_name=dataset_name,
                    authorization_provider=prov,
                    policy_document=pol,
                )
                self.model_suite = new_suite
                self.model_mode = "research"
                self.dataset_name = dataset_name
                self.authorization_provider = prov
                self.policy_document = pol
            elif mode_clean == "synthetic":
                self.model_suite = get_default_model_suite(seed=self.seed)
                self.model_mode = "synthetic"
                self.dataset_name = "SYNTHETIC_ONLY"
            else:
                raise ValueError(f"Unknown model_mode: '{mode}'. Choose 'synthetic' or 'research'.")

            self.pipeline = self.model_suite.create_pipeline(model_name=self.active_model_name)
            self.predictor = IDSPredictor(pipeline=self.pipeline)
            return self.get_status()

    # -------------------------------------------------------------------------
    # Packet Ingestion & Event Processing
    # -------------------------------------------------------------------------

    def step_simulation(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generates and processes a discrete batch of packets synchronously."""
        with self._lock:
            packets = self.simulator.generate_batch(count=count)
            return self._process_batch_of_packets(packets, lookahead_buffer=self.simulator._packet_buffer)

    def _worker_loop(self) -> None:
        """Background thread target continuously feeding generated traffic to pipeline."""
        while not self._stop_event.is_set():
            self._pause_event.wait()
            if self._stop_event.is_set():
                break

            try:
                packets = self.simulator.generate_batch(count=12)
                self._process_batch_of_packets(packets, lookahead_buffer=self.simulator._packet_buffer)
            except Exception as e:
                logger.error(f"Error in simulator background loop: {e}", exc_info=True)

            time.sleep(self.traffic_interval)

    def _process_batch_of_packets(
        self,
        packets: List[GeneratedPacket],
        lookahead_buffer: Optional[List[GeneratedPacket]] = None,
    ) -> List[Dict[str, Any]]:
        """Feeds packets into IDSPredictor and updates state records.

        If a simulation-specific lookahead buffer is explicitly provided, active flows
        with upcoming packets within burst proximity (<= 25ms) are preserved across step boundaries.
        Otherwise, generic flow-aggregator inactivity-timeout and duration semantics are used.
        """
        with self._lock:
            alerts_generated: List[Dict[str, Any]] = []
            latest_timestamp = 0.0
            for pkt in packets:
                self.total_packets += 1
                pkt_dict = pkt.to_dict()
                latest_timestamp = max(latest_timestamp, pkt.timestamp)

                # Track flow-level ground truth and metadata
                f_key = f"{pkt.src_ip}:{pkt.src_port}->{pkt.dst_ip}:{pkt.dst_port}"
                r_key = f"{pkt.dst_ip}:{pkt.dst_port}->{pkt.src_ip}:{pkt.src_port}"
                if pkt.ground_truth == 1 or f_key not in self._flow_metadata:
                    self._flow_metadata[f_key] = (pkt.ground_truth, pkt.scenario_name, pkt.source_device_id)
                    self._flow_metadata[r_key] = (pkt.ground_truth, pkt.scenario_name, pkt.source_device_id)

                ingest_res = self.predictor.ingest_packet(pkt_dict)
                for alert in ingest_res.alerts:
                    self._handle_new_alert(alert, pkt)
                    alerts_generated.append(alert)

            fa = self.predictor.pipeline.flow_aggregator

            # 1. Simulator-specific lookahead mode (only when lookahead buffer is explicitly supplied)
            if lookahead_buffer is not None:
                pending_keys = set()
                for p in lookahead_buffer:
                    k, _ = normalize_5tuple(p.src_ip, p.dst_ip, p.src_port, p.dst_port, p.proto)
                    if k in fa.active_flows:
                        flow = fa.active_flows[k]
                        if p.timestamp - flow.timestamp_end <= 0.025:
                            pending_keys.add(k)

                keys_to_pop = [k for k in list(fa.active_flows.keys()) if k not in pending_keys]
                for k in keys_to_pop:
                    fl = fa.active_flows.pop(k).finalize()
                    alert = self.predictor._predict_flow(fl, delivery_target=None)
                    self._handle_new_alert(alert, None)
                    alerts_generated.append(alert)
            else:
                # 2. Generic stream mode: uses flow aggregator's inactivity timeout and max duration
                expired_flows = fa.pop_expired_flows(latest_timestamp)
                for fl in expired_flows:
                    alert = self.predictor._predict_flow(fl, delivery_target=None)
                    self._handle_new_alert(alert, None)
                    alerts_generated.append(alert)

            return alerts_generated

    def finalize_pending_flows(self) -> List[Dict[str, Any]]:
        """Flushes and predicts any remaining pending flows at scenario/simulation completion."""
        with self._lock:
            final_res = self.predictor.finalize_pending_flows()
            alerts_generated = []
            for alert in final_res.alerts:
                self._handle_new_alert(alert, None)
                alerts_generated.append(alert)
            return alerts_generated

    def _handle_new_alert(self, alert: Dict[str, Any], source_packet: Optional[GeneratedPacket] = None) -> None:
        """Processes an alert output dictionary into flow records and event streams."""
        self.total_flows += 1

        meta = self._flow_metadata.get(alert["flow_id"])
        if meta is not None:
            gt, sc_name, dev_id = meta
        elif source_packet is not None:
            gt, sc_name, dev_id = source_packet.ground_truth, source_packet.scenario_name, source_packet.source_device_id
        else:
            gt, sc_name, dev_id = 0, "UNKNOWN", "N/A"

        flow_record = {
            "flow_id": alert["flow_id"],
            "src_ip": alert["src_ip"],
            "dst_ip": alert["dst_ip"],
            "timestamp": alert["timestamp"],
            "prediction_prob": alert["prediction_prob"],
            "decision_threshold": alert["decision_threshold"],
            "is_anomaly": alert["is_anomaly"],
            "risk_score": alert["risk_score"],
            "risk_level": alert["risk_level"],
            "ground_truth": gt,
            "scenario": sc_name,
            "source_device": dev_id,
            "raw_features": alert["raw_features"],
            "features": alert.get("raw_features"),
        }

        self.recent_flows.append(flow_record)

        if alert.get("is_anomaly", False) or alert.get("risk_score", 0.0) >= 0.5:
            self.total_alerts += 1
            if gt == 1:
                self.total_attacks_detected += 1
            self.recent_alerts.append(flow_record)

        # Notify sync listeners
        for listener in list(self._sync_listeners):
            try:
                listener(flow_record)
            except Exception as e:
                logger.warning(f"Error in sync listener: {e}")

        # Broadcast to async WebSocket queues
        for q in list(self._async_queues):
            try:
                q.put_nowait(flow_record)
            except (asyncio.QueueFull, Exception):
                pass

    # -------------------------------------------------------------------------
    # WebSocket Subscription Management
    # -------------------------------------------------------------------------

    def register_async_queue(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._async_queues.append(queue)

    def unregister_async_queue(self, queue: asyncio.Queue) -> None:
        with self._lock:
            if queue in self._async_queues:
                self._async_queues.remove(queue)

    # -------------------------------------------------------------------------
    # Adversarial Attack Laboratory
    # -------------------------------------------------------------------------

    def run_adversarial_experiment(
        self,
        epsilon: float = 0.15,
        steps: int = 7,
        attack_method: str = "pgd",
        sample_count: int = 25,
    ) -> Dict[str, Any]:
        """Executes a controlled laboratory adversarial evaluation using project models."""
        with self._lock:
            suite = self.model_suite
            feature_names = suite.feature_names

            # Filter validation set for true attack samples
            attack_indices = np.where(suite.y_val == 1)[0]
            if len(attack_indices) == 0:
                return {"error": "No attack samples available in validation reference set"}

            selected_idx = attack_indices[: min(sample_count, len(attack_indices))]
            X_clean = suite.X_val[selected_idx]
            y_clean = suite.y_val[selected_idx]

            # Setup discrete feature mask & domain clamping
            discrete_cols = {"proto_tcp", "proto_udp", "proto_icmp", "proto_other"}
            cont_mask = torch.tensor(
                [0.0 if col in discrete_cols else 1.0 for col in feature_names],
                dtype=torch.float32,
            ).unsqueeze(0)

            x_min = torch.tensor(suite.X_train.min(axis=0), dtype=torch.float32).unsqueeze(0)
            x_max = torch.tensor(suite.X_train.max(axis=0), dtype=torch.float32).unsqueeze(0)

            X_tensor = torch.tensor(X_clean, dtype=torch.float32)
            y_tensor = torch.tensor(y_clean, dtype=torch.float32)

            # Generate perturbations against Standard MLP
            if attack_method.lower() == "fgsm":
                X_adv_t = fgsm_attack(
                    model=suite.standard_mlp,
                    X=X_tensor,
                    y=y_tensor,
                    epsilon=epsilon,
                    continuous_mask=cont_mask,
                    x_min=x_min,
                    x_max=x_max,
                )
            else:
                X_adv_t = pgd_attack(
                    model=suite.standard_mlp,
                    X=X_tensor,
                    y=y_tensor,
                    epsilon=epsilon,
                    continuous_mask=cont_mask,
                    x_min=x_min,
                    x_max=x_max,
                    steps=steps,
                )

            X_adv = X_adv_t.numpy()

            # Multi-Model Comparative Evaluation
            # 1. Standard MLP
            p_std_clean = suite.standard_mlp_wrapper.predict_proba(X_clean)[:, 1]
            p_std_adv = suite.standard_mlp_wrapper.predict_proba(X_adv)[:, 1]
            acc_std_clean = float((p_std_clean >= 0.5).mean())
            acc_std_adv = float((p_std_adv >= 0.5).mean())

            # 2. Robust MLP (PGD-trained)
            p_rob_clean = suite.robust_mlp_wrapper.predict_proba(X_clean)[:, 1]
            p_rob_adv = suite.robust_mlp_wrapper.predict_proba(X_adv)[:, 1]
            acc_rob_clean = float((p_rob_clean >= 0.5).mean())
            acc_rob_adv = float((p_rob_adv >= 0.5).mean())

            # 3. Random Forest
            p_rf_clean = suite.rf_model.predict_proba(X_clean)[:, 1]
            p_rf_adv = suite.rf_model.predict_proba(X_adv)[:, 1]
            acc_rf_clean = float((p_rf_clean >= 0.5).mean())
            acc_rf_adv = float((p_rf_adv >= 0.5).mean())

            # 4. Option C Dual-Stream Ensemble
            p_optc_clean = suite.option_c_ensemble.predict_proba(X_clean)[:, 1]
            p_optc_adv = suite.option_c_ensemble.predict_proba(X_adv)[:, 1]
            acc_optc_clean = float((p_optc_clean >= 0.5).mean())
            acc_optc_adv = float((p_optc_adv >= 0.5).mean())

            # 5. Risk Layer & AE Evaluation
            risk_eval = evaluate_adversarial_sample(
                rf_model=suite.rf_model,
                mlp_model=suite.standard_mlp,
                ae_model=suite.autoencoder,
                risk_layer=suite.risk_layer,
                X_clean=X_clean,
                X_adv=X_adv,
                y_true=y_clean,
            )

            # Perturbation statistics
            diff = X_adv - X_clean
            l2_norm = float(np.linalg.norm(diff, axis=1).mean())
            linf_norm = float(np.abs(diff).max(axis=1).mean())

            experiment_record = {
                "experiment_id": f"exp_{int(time.time())}_{len(self.experiment_history) + 1}",
                "timestamp": time.time(),
                "attack_method": attack_method.upper(),
                "epsilon": epsilon,
                "steps": steps,
                "samples_attacked": len(selected_idx),
                "perturbation_l2": l2_norm,
                "perturbation_linf": linf_norm,
                "models": {
                    "standard_mlp": {
                        "clean_detection_rate": acc_std_clean,
                        "adv_detection_rate": acc_std_adv,
                        "degradation": acc_std_clean - acc_std_adv,
                        "mean_clean_prob": float(p_std_clean.mean()),
                        "mean_adv_prob": float(p_std_adv.mean()),
                    },
                    "robust_mlp": {
                        "clean_detection_rate": acc_rob_clean,
                        "adv_detection_rate": acc_rob_adv,
                        "degradation": acc_rob_clean - acc_rob_adv,
                        "mean_clean_prob": float(p_rob_clean.mean()),
                        "mean_adv_prob": float(p_rob_adv.mean()),
                    },
                    "random_forest": {
                        "clean_detection_rate": acc_rf_clean,
                        "adv_detection_rate": acc_rf_adv,
                        "degradation": acc_rf_clean - acc_rf_adv,
                        "mean_clean_prob": float(p_rf_clean.mean()),
                        "mean_adv_prob": float(p_rf_adv.mean()),
                    },
                    "option_c_ensemble": {
                        "clean_detection_rate": acc_optc_clean,
                        "adv_detection_rate": acc_optc_adv,
                        "degradation": acc_optc_clean - acc_optc_adv,
                        "mean_clean_prob": float(p_optc_clean.mean()),
                        "mean_adv_prob": float(p_optc_adv.mean()),
                    },
                },
                "risk_layer": risk_eval,
                "sample_preview": {
                    "clean_sample": [float(v) for v in X_clean[0][:5]],
                    "adv_sample": [float(v) for v in X_adv[0][:5]],
                    "feature_subset": feature_names[:5],
                },
            }

            self.experiment_history.append(experiment_record)
            return experiment_record

    # -------------------------------------------------------------------------
    # Explainability (XAI)
    # -------------------------------------------------------------------------

    def explain_flow(self, flow_features: Dict[str, float] | List[float] | np.ndarray) -> Dict[str, Any]:
        """Computes local SHAP and gradient feature attribution for a network flow vector."""
        with self._lock:
            suite = self.model_suite
            feature_names = suite.feature_names

            if isinstance(flow_features, dict):
                x_vec = np.array([float(flow_features.get(f, 0.0)) for f in feature_names], dtype=np.float32)
                # Preprocess if in raw scale
                df_raw = pd.DataFrame([flow_features])[feature_names].fillna(0.0)
                x_scaled = suite.preprocessor.transform(df_raw)[0]
            elif isinstance(flow_features, list):
                x_scaled = np.array(flow_features, dtype=np.float32)
            else:
                x_scaled = np.asarray(flow_features, dtype=np.float32).flatten()

            explanation = explain_local_sample(
                rf_model=suite.rf_model,
                mlp_model=suite.robust_mlp,
                x_single=x_scaled,
                feature_names=feature_names,
                top_k=7,
                rf_background_X=suite.X_train[:40],
                mlp_background_X=suite.X_train[:40],
            )
            # Ensure attribution alias is populated for frontend compatibility
            for feat in explanation.get("top_k_features", []):
                if "attribution" not in feat and "weighted_attribution" in feat:
                    feat["attribution"] = feat["weighted_attribution"]
            return explanation

    # -------------------------------------------------------------------------
    # State & Health Reporting
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Returns unified platform operational status and counters."""
        with self._lock:
            is_running = self._thread is not None and self._thread.is_alive()
            is_paused = is_running and not self._pause_event.is_set()
            elapsed = max(time.time() - self.start_time, 0.1)

            sim_status = "PAUSED" if is_paused else ("RUNNING" if is_running else "STOPPED")

            devices_info = [d.to_dict() for d in self.simulator.devices]

            if self.model_mode == "research":
                provenance = {
                    "model_suite_type": "VERIFIED_RESEARCH_BASELINE",
                    "model_authorization_status": "AUTHORIZED_CRYPTOGRAPHIC_POLICY",
                    "research_checkpoints_loaded": True,
                    "dataset_name": self.dataset_name,
                    "artifact_path": str(getattr(self.model_suite, "model_dir", "")),
                    "artifact_digests": getattr(self.model_suite, "artifact_digests", {}),
                    "feature_schema": self.model_suite.feature_names,
                    "traffic_source": "SIMULATED_IOT_NETWORK",
                    "traffic_fidelity": "SYNTHETIC_CANONICAL_21",
                    "physical_capture_active": False,
                    "pcap_replay_active": False,
                }
            else:
                provenance = {
                    "model_suite_type": "SYNTHETIC_REFERENCE",
                    "model_authorization_status": "FAIL_CLOSED_ROOT_IDENTITY_REQUIRED",
                    "research_checkpoints_loaded": False,
                    "dataset_name": "SYNTHETIC_ONLY",
                    "artifact_path": "IN_MEMORY_SYNTHETIC_COMPONENTS",
                    "artifact_digests": {},
                    "feature_schema": self.model_suite.feature_names,
                    "traffic_source": "SIMULATED_IOT_NETWORK",
                    "traffic_fidelity": "SYNTHETIC_CANONICAL_21",
                    "physical_capture_active": False,
                    "pcap_replay_active": False,
                }

            return {
                "platform_status": "ONLINE",
                "uptime_seconds": elapsed,
                "simulator": {
                    "status": sim_status,
                    "active_scenario": self.simulator.scenario.scenario_type.value,
                    "scenario_description": self.simulator.scenario.description,
                    "traffic_rate_hz": 1.0 / max(self.traffic_interval, 0.01),
                    "device_count": len(devices_info),
                    "devices": devices_info,
                },
                "pipeline": {
                    "active_model": self.active_model_name,
                    "health": self.predictor.health_check()["status"],
                    "decision_threshold": self.pipeline.effective_decision_threshold,
                    "total_packets": self.total_packets,
                    "total_flows": self.total_flows,
                    "total_alerts": self.total_alerts,
                    "total_attacks_detected": self.total_attacks_detected,
                    "packets_per_second": self.total_packets / elapsed,
                    "flows_per_second": self.total_flows / elapsed,
                    "buffered_flows_count": len(self.recent_flows),
                    "buffered_alerts_count": len(self.recent_alerts),
                },
                "provenance": provenance,
                "experiments_count": len(self.experiment_history),
            }


_GLOBAL_PLATFORM_STATE: Optional[PlatformStateManager] = None
_STATE_LOCK = threading.Lock()


def get_platform_state(
    seed: int = 42,
    model_mode: str = "synthetic",
    dataset_name: str = "ToN-IoT",
    authorization_provider: Optional[Any] = None,
    policy_document: Optional[Dict[str, Any]] = None,
) -> PlatformStateManager:
    """Thread-safe retrieval of the active platform singleton manager."""
    global _GLOBAL_PLATFORM_STATE
    if _GLOBAL_PLATFORM_STATE is None:
        with _STATE_LOCK:
            if _GLOBAL_PLATFORM_STATE is None:
                _GLOBAL_PLATFORM_STATE = PlatformStateManager(
                    seed=seed,
                    model_mode=model_mode,
                    dataset_name=dataset_name,
                    authorization_provider=authorization_provider,
                    policy_document=policy_document,
                )
    return _GLOBAL_PLATFORM_STATE


def reset_platform_state() -> None:
    """Resets global platform singleton instance (for testing)."""
    global _GLOBAL_PLATFORM_STATE
    with _STATE_LOCK:
        if _GLOBAL_PLATFORM_STATE is not None:
            _GLOBAL_PLATFORM_STATE.stop_simulation()
            _GLOBAL_PLATFORM_STATE = None
