"""Unit tests for Adversarial Attack Laboratory and Evaluation Module."""
from __future__ import annotations

import numpy as np
import pytest
import torch

from iot_ids.adversarial.attacks import fgsm_attack, pgd_attack
from iot_ids.dashboard.state import get_platform_state


def test_adversarial_attacks_discrete_masking_and_bounds():
    state = get_platform_state()
    suite = state.model_suite
    feature_names = suite.feature_names

    discrete_cols = {"proto_tcp", "proto_udp", "proto_icmp", "proto_other"}
    cont_mask = torch.tensor(
        [0.0 if col in discrete_cols else 1.0 for col in feature_names],
        dtype=torch.float32,
    ).unsqueeze(0)

    x_min = torch.tensor(suite.X_train.min(axis=0), dtype=torch.float32).unsqueeze(0)
    x_max = torch.tensor(suite.X_train.max(axis=0), dtype=torch.float32).unsqueeze(0)

    X_clean = torch.tensor(suite.X_val[:10], dtype=torch.float32)
    y_clean = torch.tensor(suite.y_val[:10], dtype=torch.float32)

    epsilon = 0.20

    # 1. Test PGD Attack
    X_pgd = pgd_attack(
        model=suite.standard_mlp,
        X=X_clean,
        y=y_clean,
        epsilon=epsilon,
        continuous_mask=cont_mask,
        x_min=x_min,
        x_max=x_max,
        steps=5,
    )

    # Check that discrete features remain unperturbed
    for idx, name in enumerate(feature_names):
        if name in discrete_cols:
            assert torch.allclose(X_pgd[:, idx], X_clean[:, idx], atol=1e-5), f"Discrete feature {name} was modified!"

    # Check L-infinity perturbation bound on continuous features
    diff = torch.abs(X_pgd - X_clean)
    assert (diff <= epsilon + 1e-5).all(), "Perturbation exceeded epsilon budget!"

    # Check domain clamping
    assert (X_pgd >= x_min - 1e-5).all(), "Perturbation fell below x_min!"
    assert (X_pgd <= x_max + 1e-5).all(), "Perturbation exceeded x_max!"

    # 2. Test FGSM Attack
    X_fgsm = fgsm_attack(
        model=suite.standard_mlp,
        X=X_clean,
        y=y_clean,
        epsilon=epsilon,
        continuous_mask=cont_mask,
        x_min=x_min,
        x_max=x_max,
    )
    for idx, name in enumerate(feature_names):
        if name in discrete_cols:
            assert torch.allclose(X_fgsm[:, idx], X_clean[:, idx], atol=1e-5)
    assert (torch.abs(X_fgsm - X_clean) <= epsilon + 1e-5).all()


def test_adversarial_experiment_execution():
    state = get_platform_state()
    exp = state.run_adversarial_experiment(
        epsilon=0.15,
        steps=5,
        attack_method="pgd",
        sample_count=15,
    )

    assert "experiment_id" in exp
    assert exp["attack_method"] == "PGD"
    assert exp["epsilon"] == 0.15
    assert exp["samples_attacked"] > 0
    assert exp["perturbation_l2"] >= 0.0
    assert exp["perturbation_linf"] <= 0.15 + 1e-4

    # Verify all 4 models are benchmarked
    assert "standard_mlp" in exp["models"]
    assert "robust_mlp" in exp["models"]
    assert "random_forest" in exp["models"]
    assert "option_c_ensemble" in exp["models"]

    # Verify Risk Layer output
    assert "risk_layer" in exp
    assert "attack_success_rate" in exp["risk_layer"]
    assert "ae_catch_rate" in exp["risk_layer"]

    # Check persistence in experiment history
    assert exp in state.experiment_history
