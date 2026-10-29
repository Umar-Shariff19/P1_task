"""Synthetic Baseline Model Suite and Training Factory for Demonstration and Testing.

Provides fully-functional, calibrated models (Random Forest, Standard MLP,
PGD-Trained Robust MLP, Unsupervised Autoencoder, and Option C Ensemble) trained
on reproducible synthetic reference data matching the canonical 21-feature schema.

Ensures real model inference, adversarial attacks, and explainability work out of the
box without requiring access to restricted or proprietary datasets.
"""
from __future__ import annotations

import json
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.ensemble import RandomForestClassifier

from iot_ids.adaptation.calibration import TargetThresholdCalibrator
from iot_ids.adversarial.adversarial_training import train_mlp_adversarial
from iot_ids.experiments.preprocessing import FeaturePreprocessor
from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.inference.predictor import IDSPredictor
from iot_ids.models.autoencoder import Autoencoder
from iot_ids.models.ensemble.risk_layer import RiskLayer
from iot_ids.models.neural_network import MLPClassifier
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.utils.sinks import DeliveryTarget


class MLPWrapper:
    """Scikit-learn compatible inference wrapper for PyTorch MLPClassifier."""

    def __init__(self, model: nn.Module):
        self.model = model
        self.classes_ = np.array([0, 1])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self.model.eval()
        with torch.no_grad():
            t_X = torch.tensor(np.asarray(X, dtype=np.float32), dtype=torch.float32)
            logits = self.model(t_X).squeeze(-1)
            p_attack = torch.sigmoid(logits).cpu().numpy().reshape(-1)

        p_attack = np.clip(p_attack, 0.0, 1.0)
        p_benign = 1.0 - p_attack
        return np.column_stack([p_benign, p_attack])

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= 0.5).astype(int)


class OptionCEnsemble:
    """Option C Dual-Stream Ensemble (0.7 * RF + 0.3 * Robust MLP)."""

    def __init__(self, rf_model: RandomForestClassifier, robust_mlp: nn.Module):
        self.rf_model = rf_model
        self.robust_mlp = robust_mlp
        self.classes_ = np.array([0, 1])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p_rf = self.rf_model.predict_proba(X)[:, 1]
        self.robust_mlp.eval()
        with torch.no_grad():
            t_X = torch.tensor(np.asarray(X, dtype=np.float32), dtype=torch.float32)
            logits = self.robust_mlp(t_X).squeeze(-1)
            p_mlp = torch.sigmoid(logits).cpu().numpy().reshape(-1)

        p_attack = 0.7 * p_rf + 0.3 * p_mlp
        p_attack = np.clip(p_attack, 0.0, 1.0)
        p_benign = 1.0 - p_attack
        return np.column_stack([p_benign, p_attack])

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= 0.5).astype(int)


@dataclass
class SyntheticModelSuite:
    """Encapsulates all trained models and pipeline assets for demonstration."""

    rf_model: RandomForestClassifier
    standard_mlp: MLPClassifier
    robust_mlp: MLPClassifier
    autoencoder: Autoencoder
    risk_layer: RiskLayer
    standard_mlp_wrapper: MLPWrapper
    robust_mlp_wrapper: MLPWrapper
    option_c_ensemble: OptionCEnsemble
    preprocessor: FeaturePreprocessor
    calibrator: TargetThresholdCalibrator
    feature_names: List[str]
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    df_train: pd.DataFrame
    df_val: pd.DataFrame
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_model(self, model_name: str) -> Any:
        """Retrieves a model or wrapper by canonical name."""
        name = model_name.lower().replace("-", "_").replace(" ", "_")
        if name in ("rf", "random_forest"):
            return self.rf_model
        if name in ("standard_mlp", "mlp", "standard"):
            return self.standard_mlp_wrapper
        if name in ("robust_mlp", "robust"):
            return self.robust_mlp_wrapper
        if name in ("option_c", "ensemble", "option_c_ensemble"):
            return self.option_c_ensemble
        raise ValueError(f"Unknown model name: {model_name}. Choose from: rf, standard_mlp, robust_mlp, option_c")

    def create_pipeline(
        self,
        model_name: str = "option_c",
        feature_profile: str = "full_multilevel",
        decision_threshold: float = 0.5,
    ) -> IDSSystemPipeline:
        """Builds an operational IDSSystemPipeline using the requested model."""
        selected_model = self.get_model(model_name)
        return IDSSystemPipeline(
            model=selected_model,
            preprocessor=self.preprocessor,
            feature_profile=feature_profile,
            feature_names=self.feature_names,
            calibrator=self.calibrator,
            decision_threshold=decision_threshold,
        )

    def create_predictor(
        self,
        model_name: str = "option_c",
        delivery_target: Optional[DeliveryTarget] = None,
        feature_profile: str = "full_multilevel",
        decision_threshold: float = 0.5,
    ) -> IDSPredictor:
        """Builds a deployable IDSPredictor using the requested model."""
        pipeline = self.create_pipeline(
            model_name=model_name,
            feature_profile=feature_profile,
            decision_threshold=decision_threshold,
        )
        return IDSPredictor(pipeline=pipeline, delivery_target=delivery_target)

    def save(self, cache_dir: Path | str) -> None:
        """Persists trained weights and metadata to disk for rapid instant reload."""
        p = Path(cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.rf_model, p / "rf_model.joblib")
        torch.save(self.standard_mlp.state_dict(), p / "standard_mlp.pt")
        torch.save(self.robust_mlp.state_dict(), p / "robust_mlp.pt")
        torch.save(self.autoencoder.state_dict(), p / "autoencoder.pt")
        joblib.dump(self.preprocessor, p / "preprocessor.joblib")
        joblib.dump(self.calibrator, p / "calibrator.joblib")
        self.risk_layer.save(p / "risk_layer.json")
        np.savez_compressed(
            p / "reference_data.npz",
            X_train=self.X_train,
            y_train=self.y_train,
            X_val=self.X_val,
            y_val=self.y_val,
        )
        (p / "metadata.json").write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, cache_dir: Path | str) -> SyntheticModelSuite:
        """Rapidly instantiates the suite from pre-trained serialized weights."""
        p = Path(cache_dir)
        metadata = json.loads((p / "metadata.json").read_text(encoding="utf-8"))
        feature_names = list(CANONICAL_21_FEATURE_NAMES)

        rf_model = joblib.load(p / "rf_model.joblib")
        preprocessor = joblib.load(p / "preprocessor.joblib")
        calibrator = joblib.load(p / "calibrator.joblib")
        risk_layer = RiskLayer.load(p / "risk_layer.json")

        standard_mlp = MLPClassifier(input_dim=len(feature_names), hidden_layers=[128, 64, 32], dropout=0.1)
        standard_mlp.load_state_dict(torch.load(p / "standard_mlp.pt", weights_only=True))
        standard_mlp.eval()

        robust_mlp = MLPClassifier(input_dim=len(feature_names), hidden_layers=[128, 64, 32], dropout=0.1)
        robust_mlp.load_state_dict(torch.load(p / "robust_mlp.pt", weights_only=True))
        robust_mlp.eval()

        autoencoder = Autoencoder(input_dim=len(feature_names), bottleneck_dim=8)
        autoencoder.load_state_dict(torch.load(p / "autoencoder.pt", weights_only=True))
        autoencoder.eval()

        npz = np.load(p / "reference_data.npz")
        X_train = npz["X_train"]
        y_train = npz["y_train"]
        X_val = npz["X_val"]
        y_val = npz["y_val"]

        df_train = pd.DataFrame(X_train, columns=feature_names)
        df_val = pd.DataFrame(X_val, columns=feature_names)

        standard_mlp_wrapper = MLPWrapper(standard_mlp)
        robust_mlp_wrapper = MLPWrapper(robust_mlp)
        option_c_ensemble = OptionCEnsemble(rf_model=rf_model, robust_mlp=robust_mlp)

        return cls(
            rf_model=rf_model,
            standard_mlp=standard_mlp,
            robust_mlp=robust_mlp,
            autoencoder=autoencoder,
            risk_layer=risk_layer,
            standard_mlp_wrapper=standard_mlp_wrapper,
            robust_mlp_wrapper=robust_mlp_wrapper,
            option_c_ensemble=option_c_ensemble,
            preprocessor=preprocessor,
            calibrator=calibrator,
            feature_names=feature_names,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            df_train=df_train,
            df_val=df_val,
            metadata=metadata,
        )


def generate_synthetic_reference_dataset(
    n_samples: int = 500,
    seed: int = 42,
    attack_ratio: float = 0.35,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Generates synthetic network flow records following canonical 21-feature schemas.

    Produces realistic feature distributions for benign IoT telemetry and simulated attack traffic
    (Floods, Scans, Malicious Command Injection, and Exfiltration).
    """
    rng = np.random.default_rng(seed)
    n_attacks = int(n_samples * attack_ratio)
    n_benign = n_samples - n_attacks

    features: Dict[str, np.ndarray] = {}

    # 1. Flow Duration
    dur_benign = rng.exponential(scale=3.0, size=n_benign) + 0.1
    dur_attack = np.concatenate([
        rng.exponential(scale=0.2, size=n_attacks // 2) + 0.01,  # Fast flood / probe
        rng.exponential(scale=25.0, size=n_attacks - (n_attacks // 2)) + 10.0,  # Slowloris / exfil
    ])
    features["flow_duration"] = np.concatenate([dur_benign, dur_attack])

    # 2. Flow Rate Metrics
    features["flow_bytes_per_sec"] = np.concatenate([
        rng.normal(loc=1500.0, scale=400.0, size=n_benign).clip(50.0, 50000.0),
        rng.normal(loc=45000.0, scale=12000.0, size=n_attacks).clip(200.0, 500000.0),
    ])

    features["flow_pkts_per_sec"] = np.concatenate([
        rng.normal(loc=10.0, scale=4.0, size=n_benign).clip(0.5, 50.0),
        rng.normal(loc=450.0, scale=100.0, size=n_attacks).clip(2.0, 3000.0),
    ])

    features["mean_pkt_size"] = np.concatenate([
        rng.normal(loc=120.0, scale=30.0, size=n_benign).clip(40.0, 1500.0),
        rng.normal(loc=64.0, scale=15.0, size=n_attacks).clip(40.0, 1500.0),
    ])

    features["payload_byte_ratio"] = np.concatenate([
        rng.uniform(0.5, 0.9, size=n_benign),
        rng.uniform(0.0, 0.3, size=n_attacks),  # floods have tiny payloads
    ])

    features["pkt_count_ratio"] = np.concatenate([
        rng.normal(loc=1.0, scale=0.2, size=n_benign).clip(0.1, 5.0),
        rng.normal(loc=0.05, scale=0.05, size=n_attacks).clip(0.01, 10.0),
    ])

    features["tcp_syn_ratio"] = np.concatenate([
        rng.beta(1.0, 10.0, size=n_benign).clip(0.0, 0.3),  # Benign low syn
        rng.beta(8.0, 1.5, size=n_attacks).clip(0.4, 1.0),   # Attack high syn
    ])

    # Protocol flags (one-hot)
    proto_choices_b = rng.choice(["tcp", "udp"], size=n_benign, p=[0.75, 0.25])
    proto_choices_a = rng.choice(["tcp", "udp"], size=n_attacks, p=[0.85, 0.15])
    all_protos = np.concatenate([proto_choices_b, proto_choices_a])

    features["proto_tcp"] = (all_protos == "tcp").astype(float)
    features["proto_udp"] = (all_protos == "udp").astype(float)
    features["proto_icmp"] = np.zeros(n_samples, dtype=float)
    features["proto_other"] = np.zeros(n_samples, dtype=float)

    # Temporal Metrics
    features["temporal_iat_mean"] = np.concatenate([
        rng.exponential(scale=0.5, size=n_benign) + 0.05,
        rng.exponential(scale=0.01, size=n_attacks) + 0.001,
    ])

    features["temporal_iat_cv"] = np.concatenate([
        rng.uniform(0.1, 0.8, size=n_benign),
        rng.uniform(0.0, 0.2, size=n_attacks),  # Automated bursts are regular
    ])

    features["temporal_flow_rate_ewma"] = np.concatenate([
        rng.normal(loc=5.0, scale=1.5, size=n_benign).clip(0.1, 20.0),
        rng.normal(loc=120.0, scale=30.0, size=n_attacks).clip(5.0, 500.0),
    ])

    features["temporal_byte_rate_ewma"] = np.concatenate([
        rng.normal(loc=2000.0, scale=500.0, size=n_benign).clip(100.0, 20000.0),
        rng.normal(loc=60000.0, scale=15000.0, size=n_attacks).clip(1000.0, 500000.0),
    ])

    features["temporal_syn_rate_ewma"] = np.concatenate([
        rng.normal(loc=0.5, scale=0.2, size=n_benign).clip(0.0, 5.0),
        rng.normal(loc=80.0, scale=20.0, size=n_attacks).clip(1.0, 400.0),
    ])

    # Behavioral Multi-Host Metrics
    features["behavioral_dst_diversity"] = np.concatenate([
        rng.integers(1, 4, size=n_benign).astype(float),
        rng.integers(5, 50, size=n_attacks).astype(float),
    ])

    features["behavioral_port_entropy"] = np.concatenate([
        rng.uniform(0.05, 0.5, size=n_benign),
        rng.uniform(0.8, 2.5, size=n_attacks),
    ])

    features["behavioral_fanout_ratio"] = np.concatenate([
        rng.uniform(0.0, 0.15, size=n_benign),
        rng.uniform(0.4, 0.95, size=n_attacks),
    ])

    features["behavioral_unanswered_ratio"] = np.concatenate([
        rng.uniform(0.0, 0.1, size=n_benign),
        rng.uniform(0.5, 0.99, size=n_attacks),
    ])

    features["behavioral_src_activity_ewma"] = np.concatenate([
        rng.normal(loc=3.0, scale=1.0, size=n_benign).clip(0.5, 10.0),
        rng.normal(loc=50.0, scale=15.0, size=n_attacks).clip(5.0, 200.0),
    ])

    # Construct DataFrame and label Series
    df = pd.DataFrame({col: features[col] for col in CANONICAL_21_FEATURE_NAMES})
    labels = np.concatenate([np.zeros(n_benign, dtype=int), np.ones(n_attacks, dtype=int)])
    y = pd.Series(labels, name="label")

    # Shuffle uniformly
    perm = rng.permutation(n_samples)
    return df.iloc[perm].reset_index(drop=True), y.iloc[perm].reset_index(drop=True)


def train_synthetic_model_suite(
    seed: int = 42,
    n_train: int = 400,
    n_val: int = 150,
) -> SyntheticModelSuite:
    """Trains and calibrates a complete suite of synthetic baseline models deterministically."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    # 1. Generate reference training and validation sets
    df_train, y_train_series = generate_synthetic_reference_dataset(n_samples=n_train, seed=seed)
    df_val, y_val_series = generate_synthetic_reference_dataset(n_samples=n_val, seed=seed + 1)

    y_train = y_train_series.to_numpy()
    y_val = y_val_series.to_numpy()

    # 2. Fit FeaturePreprocessor
    preprocessor = FeaturePreprocessor(feature_names=list(CANONICAL_21_FEATURE_NAMES))
    X_train = preprocessor.fit_transform(df_train)
    X_val = preprocessor.transform(df_val)

    # 3. Train Random Forest Classifier
    rf_model = RandomForestClassifier(
        n_estimators=30,
        max_depth=8,
        min_samples_split=4,
        random_state=seed,
    )
    rf_model.fit(X_train, y_train)

    # 4. Train Standard MLP Classifier
    standard_mlp = MLPClassifier(input_dim=len(CANONICAL_21_FEATURE_NAMES), hidden_layers=[128, 64, 32], dropout=0.1)
    optimizer = optim.Adam(standard_mlp.parameters(), lr=0.005)
    criterion = nn.BCEWithLogitsLoss()

    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(-1)

    standard_mlp.train()
    for _ in range(25):
        optimizer.zero_grad()
        out = standard_mlp(X_train_t)
        loss = criterion(out, y_train_t)
        loss.backward()
        optimizer.step()
    standard_mlp.eval()

    # 5. Train PGD-Adversarially Trained Robust MLP
    robust_mlp = MLPClassifier(input_dim=len(CANONICAL_21_FEATURE_NAMES), hidden_layers=[128, 64, 32], dropout=0.1)
    train_mlp_adversarial(
        model=robust_mlp,
        X_train=X_train,
        y_train=y_train,
        feature_names=list(CANONICAL_21_FEATURE_NAMES),
        epsilon=0.15,
        pgd_steps=5,
        adv_ratio=0.5,
        epochs=15,
        batch_size=64,
        lr=0.004,
        verbose=False,
    )
    robust_mlp.eval()

    # 6. Train Autoencoder on Benign-only Training Data
    autoencoder = Autoencoder(input_dim=len(CANONICAL_21_FEATURE_NAMES), bottleneck_dim=8)
    benign_mask = y_train == 0
    X_train_benign = torch.tensor(X_train[benign_mask], dtype=torch.float32)

    ae_opt = optim.Adam(autoencoder.parameters(), lr=0.005)
    ae_crit = nn.MSELoss()

    autoencoder.train()
    for _ in range(30):
        ae_opt.zero_grad()
        recon = autoencoder(X_train_benign)
        loss = ae_crit(recon, X_train_benign)
        loss.backward()
        ae_opt.step()
    autoencoder.eval()

    # 7. Calibrate Risk Layer on Validation Benign MSE
    val_benign_mask = y_val == 0
    with torch.no_grad():
        val_benign_t = torch.tensor(X_val[val_benign_mask], dtype=torch.float32)
        val_recon = autoencoder(val_benign_t).numpy()
        val_benign_mse = np.mean((X_val[val_benign_mask] - val_recon) ** 2, axis=1)

    risk_layer = RiskLayer(tau_sup=0.50, tau_ae=0.80)
    risk_layer.fit_ae_calibration(val_benign_mse)

    # 8. Wrappers & Option C Ensemble
    standard_mlp_wrapper = MLPWrapper(standard_mlp)
    robust_mlp_wrapper = MLPWrapper(robust_mlp)
    option_c_ensemble = OptionCEnsemble(rf_model=rf_model, robust_mlp=robust_mlp)

    # 9. Fit Calibrator on Validation Probabilities
    calibrator = TargetThresholdCalibrator(default_threshold=0.50)
    val_probs = option_c_ensemble.predict_proba(X_val)[:, 1]
    calibrator.fit(val_probs, y_val)

    metadata = {
        "seed": seed,
        "n_train": n_train,
        "n_val": n_val,
        "feature_count": len(CANONICAL_21_FEATURE_NAMES),
        "created_at": time.time(),
        "rf_val_acc": float((rf_model.predict(X_val) == y_val).mean()),
        "mlp_val_acc": float((standard_mlp_wrapper.predict(X_val) == y_val).mean()),
        "robust_mlp_val_acc": float((robust_mlp_wrapper.predict(X_val) == y_val).mean()),
        "option_c_val_acc": float((option_c_ensemble.predict(X_val) == y_val).mean()),
    }

    return SyntheticModelSuite(
        rf_model=rf_model,
        standard_mlp=standard_mlp,
        robust_mlp=robust_mlp,
        autoencoder=autoencoder,
        risk_layer=risk_layer,
        standard_mlp_wrapper=standard_mlp_wrapper,
        robust_mlp_wrapper=robust_mlp_wrapper,
        option_c_ensemble=option_c_ensemble,
        preprocessor=preprocessor,
        calibrator=calibrator,
        feature_names=list(CANONICAL_21_FEATURE_NAMES),
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        df_train=df_train,
        df_val=df_val,
        metadata=metadata,
    )


DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "iot_ids_synthetic_cache"
_GLOBAL_SUITE_LOCK = threading.Lock()
_GLOBAL_MODEL_SUITE: Optional[SyntheticModelSuite] = None


def get_default_model_suite(seed: int = 42) -> SyntheticModelSuite:
    """Thread-safe retrieval of the cached synthetic model suite with instant disk cache loading."""
    global _GLOBAL_MODEL_SUITE
    if _GLOBAL_MODEL_SUITE is None:
        with _GLOBAL_SUITE_LOCK:
            if _GLOBAL_MODEL_SUITE is None:
                meta_file = DEFAULT_CACHE_DIR / "metadata.json"
                if meta_file.exists():
                    try:
                        _GLOBAL_MODEL_SUITE = SyntheticModelSuite.load(DEFAULT_CACHE_DIR)
                    except Exception:
                        _GLOBAL_MODEL_SUITE = None

                if _GLOBAL_MODEL_SUITE is None:
                    _GLOBAL_MODEL_SUITE = train_synthetic_model_suite(seed=seed)
                    try:
                        _GLOBAL_MODEL_SUITE.save(DEFAULT_CACHE_DIR)
                    except Exception:
                        pass
    return _GLOBAL_MODEL_SUITE
