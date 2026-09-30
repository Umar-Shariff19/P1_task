"""Local Explainability Module for Option C Dual-Stream Ensemble.

Provides local (per-alert / per-sample) explanations for individual network flows:
  - Option C final probability + individual stream probabilities (RF & Robust MLP)
  - Final decision classification
  - Top-k influential features with attribution values and directional signs
  - Weighted model-attribution aggregation (0.7 * RF_attr_norm + 0.3 * MLP_attr_norm)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import torch


def explain_local_sample(
    rf_model: Any,
    mlp_model: Any,
    x_single: np.ndarray,
    feature_names: List[str],
    top_k: int = 5,
    rf_background_X: Optional[np.ndarray] = None,
    mlp_background_X: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Generates a structured local explanation for a single 21-D flow vector.

    Args:
        rf_model: Trained RandomForestClassifier.
        mlp_model: Trained PyTorch MLP (nn.Module).
        x_single: 1D or 2D numpy array of shape (21,) or (1, 21).
        feature_names: List of 21 feature names.
        top_k: Number of top influential features to return.
        rf_background_X: Optional background array for reference baseline.
        mlp_background_X: Optional background array for neural explainer.

    Returns:
        Dict with probabilities, final decision, and top_k_features.
    """
    x_2d = np.atleast_2d(x_single)
    if x_2d.shape[1] != len(feature_names):
        raise ValueError(f"Feature count mismatch: got {x_2d.shape[1]}, expected {len(feature_names)}")

    # 1. Model Probabilities
    rf_prob = float(rf_model.predict_proba(x_2d)[0, 1])

    mlp_model.eval()
    with torch.no_grad():
        t_x = torch.tensor(x_2d, dtype=torch.float32)
        logits = mlp_model(t_x).squeeze(-1)
        mlp_prob = float(torch.sigmoid(logits).item())

    option_c_prob = 0.7 * rf_prob + 0.3 * mlp_prob
    final_decision = "ATTACK" if option_c_prob >= 0.5 else "BENIGN"

    # 2. Compute RF Local Attribution
    # Use TreeExplainer if available, else approximate via decision path feature contributions
    rf_attr = np.zeros(len(feature_names))
    try:
        import shap
        explainer = shap.TreeExplainer(rf_model)
        sv = explainer.shap_values(x_2d)
        if isinstance(sv, list) and len(sv) == 2:
            rf_attr = sv[1][0]
        elif isinstance(sv, np.ndarray) and sv.ndim == 3:
            rf_attr = sv[0, :, 1] if sv.shape[2] == 2 else sv[0, :, 0]
        else:
            rf_attr = sv[0]
    except Exception:
        # Fallback: Tree feature importances weighted by instance values
        rf_attr = rf_model.feature_importances_ * (x_2d[0] - (rf_background_X.mean(axis=0) if rf_background_X is not None else 0))

    # 3. Compute Robust MLP Local Attribution
    mlp_attr = np.zeros(len(feature_names))
    try:
        import shap
        if mlp_background_X is not None:
            bg = torch.tensor(mlp_background_X[:50], dtype=torch.float32)
        else:
            bg = torch.tensor(x_2d, dtype=torch.float32)
        
        explainer = shap.GradientExplainer(mlp_model, bg)
        sv = explainer.shap_values(torch.tensor(x_2d, dtype=torch.float32))
        if isinstance(sv, list):
            mlp_attr = sv[0][0]
        else:
            mlp_attr = sv[0, :, 0] if sv.ndim == 3 else sv[0]
    except Exception:
        # Fallback: Input-gradient attribution (x * grad)
        t_x = torch.tensor(x_2d, dtype=torch.float32, requires_grad=True)
        out = torch.sigmoid(mlp_model(t_x))
        out.backward()
        mlp_attr = (t_x.grad * t_x).detach().numpy()[0]

    # 4. Weighted Model-Attribution Aggregation (Option C Ensemble)
    # Normalize stream attributions by L1 norm to place them on identical scale
    rf_norm_scale = float(np.sum(np.abs(rf_attr))) if np.sum(np.abs(rf_attr)) > 0 else 1.0
    mlp_norm_scale = float(np.sum(np.abs(mlp_attr))) if np.sum(np.abs(mlp_attr)) > 0 else 1.0

    rf_attr_normalized = rf_attr / rf_norm_scale
    mlp_attr_normalized = mlp_attr / mlp_norm_scale

    option_c_attr = 0.7 * rf_attr_normalized + 0.3 * mlp_attr_normalized

    # 5. Extract Top-K Influential Features
    abs_indices = np.argsort(np.abs(option_c_attr))[::-1][:top_k]

    top_k_features = []
    for idx in abs_indices:
        val = float(x_2d[0, idx])
        attr_val = float(option_c_attr[idx])
        direction = "PUSHE_ATTACK" if attr_val > 0 else "PUSHES_BENIGN"
        
        top_k_features.append({
            "feature": feature_names[idx],
            "raw_value": val,
            "weighted_attribution": attr_val,
            "rf_attribution": float(rf_attr[idx]),
            "mlp_attribution": float(mlp_attr[idx]),
            "direction": direction,
        })

    return {
        "option_c_probability": option_c_prob,
        "rf_probability": rf_prob,
        "robust_mlp_probability": mlp_prob,
        "final_decision": final_decision,
        "top_k_features": top_k_features,
        "methodology": "weighted model-attribution aggregation (0.7 * RF_norm + 0.3 * MLP_norm)",
    }
