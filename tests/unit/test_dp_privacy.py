"""Unit tests for Privacy-Aware Data Minimization and DP-SGD modules."""
import numpy as np
import pytest
import torch
import torch.nn as nn

from iot_ids.privacy.data_minimization import DataMinimizationPolicy, extract_minimized_representation
from iot_ids.privacy.dp_sgd import DPConfig, compute_dp_epsilon, train_robust_mlp_dp


class DummyMLP(nn.Module):
    def __init__(self, input_dim: int = 21):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.net(x)


def test_data_minimization_compliance():
    feature_names = list(DataMinimizationPolicy.ALLOWED_FEATURE_CATEGORIES.keys())
    audit = DataMinimizationPolicy.verify_schema_minimization(feature_names)

    assert audit["is_compliant"] is True
    assert audit["total_features"] == 21
    assert len(audit["violations_found"]) == 0

    # Test forbidden type violation
    bad_features = feature_names + ["raw_payload_bytes"]
    bad_audit = DataMinimizationPolicy.verify_schema_minimization(bad_features)
    assert bad_audit["is_compliant"] is False
    assert "raw_payload_bytes" in bad_audit["violations_found"]


def test_minimized_representation_extraction():
    raw_dict = {"flow_duration": 1.25, "proto_tcp": 1.0}
    vec = extract_minimized_representation(raw_dict)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (21,)
    assert vec[0] == 1.25
    assert vec[17] == 1.0


def test_dp_epsilon_accounting():
    eps_low_noise = compute_dp_epsilon(epochs=10, sample_rate=0.05, noise_multiplier=0.5)
    eps_high_noise = compute_dp_epsilon(epochs=10, sample_rate=0.05, noise_multiplier=2.0)

    assert eps_low_noise > eps_high_noise
    assert eps_high_noise > 0.0
    assert compute_dp_epsilon(epochs=10, sample_rate=0.05, noise_multiplier=0.0) == float("inf")


def test_dp_sgd_training_loop():
    rng = np.random.default_rng(42)
    X_tr = rng.normal(0, 1, size=(100, 21))
    y_tr = rng.choice([0, 1], size=100)

    model = DummyMLP(21)
    dp_cfg = DPConfig(max_grad_norm=1.0, noise_multiplier=1.0, epochs=2, batch_size=32, seed=42)

    res = train_robust_mlp_dp(model, X_tr, y_tr, dp_cfg, adv_steps=2)

    assert "privacy_epsilon" in res
    assert res["privacy_epsilon"] > 0.0
    assert res["privacy_delta"] == 1e-5
    assert len(res["history"]) == 2
