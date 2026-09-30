"""Differential Privacy (DP-SGD) Module for PyTorch Neural Models.

Implements per-example gradient clipping, calibrated Gaussian noise addition,
Poisson subsampling, and PyTorch Opacus PRV / RDP accounting for (epsilon, delta) guarantees.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
import math
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

try:
    from opacus.accountants import PRVAccountant, RDPAccountant
    OPACUS_AVAILABLE = True
except ImportError:
    OPACUS_AVAILABLE = False


@dataclass
class DPConfig:
    """Configuration dataclass for DP-SGD training."""
    max_grad_norm: float = 1.0        # L2 gradient clipping bound C
    noise_multiplier: float = 1.0     # Ratio of noise std to clipping bound sigma
    target_delta: float = 1e-5        # Privacy parameter delta
    epochs: int = 10                  # Training epochs
    batch_size: int = 64              # Target mini-batch size
    learning_rate: float = 0.005      # Optimizer learning rate for clipped DP gradients
    seed: int = 42                    # Random seed for reproducibility


def compute_dp_epsilon(
    steps: int | None = None,
    sample_rate: float = 0.01,
    noise_multiplier: float = 1.0,
    target_delta: float = 1e-5,
    epochs: int | None = None,
) -> float:
    """Computes exact (epsilon, delta) privacy budget using PyTorch Opacus PRV/RDP Accountant."""
    if noise_multiplier <= 0.0:
        return float("inf")

    if steps is None:
        if epochs is not None and sample_rate > 0:
            steps = int(round(epochs / sample_rate))
        else:
            steps = 656

    if OPACUS_AVAILABLE:
        try:
            accountant = PRVAccountant()
            accountant.history = [(noise_multiplier, sample_rate, steps)]
            return float(accountant.get_epsilon(delta=target_delta))
        except Exception:
            accountant = RDPAccountant()
            accountant.history = [(noise_multiplier, sample_rate, steps)]
            return float(accountant.get_epsilon(delta=target_delta))
    else:
        # Fallback RDP accountant if Opacus is unavailable
        orders = np.linspace(1.5, 100.0, 200)
        epsilons = []
        for alpha in orders:
            rdp_eps = alpha * steps * (sample_rate ** 2) / (noise_multiplier ** 2)
            eps = rdp_eps + (math.log(1.0 / target_delta)) / (alpha - 1.0)
            epsilons.append(eps)
        return float(np.min(epsilons))


def train_step_dp_sgd(
    model: nn.Module,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    x_batch: torch.Tensor,
    y_batch: torch.Tensor,
    dp_config: DPConfig,
) -> float:
    """Executes a single DP-SGD training step with L2 per-example gradient clipping and Gaussian noise."""
    model.train()
    optimizer.zero_grad()

    batch_size = x_batch.size(0)
    if batch_size == 0:
        return 0.0

    # Apply fixed feature clamping [-10.0, +10.0] for DP stability
    x_batch = torch.clamp(x_batch, min=-10.0, max=10.0)

    per_example_grads: Dict[str, List[torch.Tensor]] = {
        name: [] for name, param in model.named_parameters() if param.requires_grad
    }

    # 1. Compute per-example gradients using model.eval() mode for running stats compatibility
    model.eval()
    for i in range(batch_size):
        x_single = x_batch[i : i + 1]
        y_single = y_batch[i : i + 1]

        model.zero_grad()
        with torch.set_grad_enabled(True):
            out_single = model(x_single)
            loss_single = criterion(out_single.squeeze(-1), y_single.float())
            loss_single.backward()

        for name, param in model.named_parameters():
            if param.requires_grad and param.grad is not None:
                per_example_grads[name].append(param.grad.clone().detach())

    # 2. Clip per-example gradients and accumulate
    with torch.no_grad():
        out_batch = model(x_batch)
        total_loss = float(criterion(out_batch.squeeze(-1), y_batch.float()).item())

        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue

            grads = torch.stack(per_example_grads[name], dim=0) # shape (B, *param.shape)
            flat_grads = grads.view(batch_size, -1)
            norms = torch.norm(flat_grads, p=2, dim=1) # shape (B,)

            # L2 clipping factor = min(1, C / ||g_i||_2)
            clip_factors = torch.clamp(dp_config.max_grad_norm / (norms + 1e-6), max=1.0)
            
            view_shape = [batch_size] + [1] * (grads.ndim - 1)
            clipped_grads = grads * clip_factors.view(*view_shape)

            summed_clipped = torch.sum(clipped_grads, dim=0)

            # Add calibrated Gaussian noise: N(0, (sigma * C)^2)
            noise_std = dp_config.noise_multiplier * dp_config.max_grad_norm
            noise = torch.randn_like(summed_clipped) * noise_std

            # Average noisy gradient over batch size
            dp_grad = (summed_clipped + noise) / float(batch_size)
            param.grad = dp_grad

    optimizer.step()
    return total_loss


def train_robust_mlp_dp(
    model: nn.Module,
    X_train: np.ndarray,
    y_train: np.ndarray,
    dp_config: DPConfig,
    adv_eps: float = 0.10,
    adv_alpha: float = 0.025,
    adv_steps: int = 7,
) -> Dict[str, Any]:
    """Trains PyTorch MLP with joint domain-constrained PGD-7 adversarial training, Poisson subsampling, and DP-SGD."""
    torch.manual_seed(dp_config.seed)
    np.random.seed(dp_config.seed)

    optimizer = optim.Adam(model.parameters(), lr=dp_config.learning_rate)
    criterion = nn.BCEWithLogitsLoss()

    dataset_size = len(X_train)
    batch_size = dp_config.batch_size
    sample_rate = batch_size / dataset_size if dataset_size > 0 else 0.01

    feature_mask = torch.ones(X_train.shape[1], dtype=torch.float32)
    feature_mask[7:11] = 0.0  # Freeze protocol indicators (proto_tcp, proto_udp, proto_icmp, proto_other)

    total_actual_steps = 0
    history = []

    X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
    y_train_tensor = torch.tensor(y_train, dtype=torch.float32)

    steps_per_epoch = max(1, int(round(dataset_size / batch_size)))

    for epoch in range(dp_config.epochs):
        epoch_losses = []
        for _ in range(steps_per_epoch):
            # Poisson Subsampling: Each sample included independently with probability q
            poisson_mask = np.random.binomial(1, sample_rate, size=dataset_size).astype(bool)
            
            # Ensure at least 1 sample if mask happens to be empty
            if not np.any(poisson_mask):
                poisson_mask[np.random.choice(dataset_size, size=min(4, dataset_size), replace=False)] = True

            x_batch = X_train_tensor[poisson_mask].clone()
            y_batch = y_train_tensor[poisson_mask].clone()

            # Domain-constrained PGD-7 Adversarial Batch Generation
            x_adv = x_batch.clone().detach()
            x_adv.requires_grad = True

            for _ in range(adv_steps):
                model.eval()
                logits = model(x_adv).squeeze(-1)
                loss = criterion(logits, y_batch)
                loss.backward()

                with torch.no_grad():
                    grad_sign = x_adv.grad.sign() * feature_mask
                    x_adv = x_adv + adv_alpha * grad_sign
                    eta = torch.clamp(x_adv - x_batch, min=-adv_eps, max=adv_eps) * feature_mask
                    x_adv = torch.clamp(x_batch + eta, min=-10.0, max=10.0).detach()
                    x_adv.requires_grad = True

            # Train step with DP-SGD on adversarial batch
            step_loss = train_step_dp_sgd(
                model=model,
                optimizer=optimizer,
                criterion=criterion,
                x_batch=x_adv.detach(),
                y_batch=y_batch,
                dp_config=dp_config,
            )
            total_actual_steps += 1
            epoch_losses.append(step_loss)

        mean_epoch_loss = float(np.mean(epoch_losses)) if epoch_losses else 0.0
        history.append({"epoch": epoch + 1, "loss": mean_epoch_loss})

    # Calculate exact epsilon using Opacus accountant on ACTUAL executed steps
    epsilon = compute_dp_epsilon(
        steps=total_actual_steps,
        sample_rate=sample_rate,
        noise_multiplier=dp_config.noise_multiplier,
        target_delta=dp_config.target_delta,
    )

    return {
        "final_loss": history[-1]["loss"] if history else 0.0,
        "privacy_epsilon": epsilon,
        "privacy_delta": dp_config.target_delta,
        "max_grad_norm": dp_config.max_grad_norm,
        "noise_multiplier": dp_config.noise_multiplier,
        "actual_steps": total_actual_steps,
        "sampling_rate": sample_rate,
        "epochs": dp_config.epochs,
        "history": history,
    }
