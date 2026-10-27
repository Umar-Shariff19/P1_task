"""Stage 4 Metrics Evaluator & Validation Threshold Optimizer.

Calculates threshold-independent metrics (ROC-AUC, PR-AUC), threshold-dependent metrics
(Accuracy, Macro F1, Attack F1, Benign F1, FPR, FNR, FP/1000), and source-validation threshold optimization.
"""
from __future__ import annotations

from typing import Dict, Any
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    auc,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)


def optimize_threshold_on_val(y_val: np.ndarray, val_probs: np.ndarray) -> float:
    """Finds decision threshold tau* in [0.01, 0.99] maximizing Macro F1 on Source Validation data."""
    y_val = np.asarray(y_val)
    val_probs = np.asarray(val_probs)
    if y_val.ndim != 1 or y_val.size == 0 or not np.issubdtype(y_val.dtype, np.number):
        raise ValueError("Validation labels must be a non-empty one-dimensional numeric array.")
    if np.iscomplexobj(y_val) or not np.isin(y_val, (0, 1)).all():
        raise ValueError("Validation labels must contain only binary labels 0 and 1.")
    if np.unique(y_val).size != 2:
        raise ValueError("Validation threshold optimization requires both label classes.")
    if val_probs.ndim != 1 or val_probs.size != y_val.size:
        raise ValueError("Validation probabilities must be one-dimensional and match label count.")
    if not np.issubdtype(val_probs.dtype, np.number) or np.iscomplexobj(val_probs):
        raise ValueError("Validation probabilities must be real numeric values.")
    val_probs = val_probs.astype(np.float64)
    if not np.isfinite(val_probs).all() or ((val_probs < 0.0) | (val_probs > 1.0)).any():
        raise ValueError("Validation probabilities must be finite values within [0, 1].")

    best_tau = 0.50
    best_f1 = -1.0

    thresholds = np.linspace(0.01, 0.99, 99)
    for tau in thresholds:
        preds = (val_probs >= tau).astype(int)
        macro_f1 = float(f1_score(y_val, preds, average="macro", zero_division=0))
        if macro_f1 > best_f1:
            best_f1 = macro_f1
            best_tau = float(tau)

    return best_tau


def evaluate_predictions(
    y_true: np.ndarray, y_probs: np.ndarray, threshold: float = 0.50
) -> Dict[str, Any]:
    """Computes comprehensive evaluation metrics given true labels and attack probability predictions."""
    raw_y_true = np.asarray(y_true)
    raw_y_probs = np.asarray(y_probs)
    if raw_y_true.ndim != 1 or raw_y_true.size == 0:
        raise ValueError("y_true must be a non-empty one-dimensional binary label array")
    if not np.issubdtype(raw_y_true.dtype, np.number) or np.iscomplexobj(raw_y_true):
        raise ValueError("y_true must contain numeric binary labels 0 and 1")
    if not np.isin(raw_y_true, (0, 1)).all():
        raise ValueError("y_true must contain only binary labels 0 and 1")
    y_true = raw_y_true.astype(int)
    has_both_classes = np.unique(y_true).size == 2

    if raw_y_probs.ndim != 1 or raw_y_probs.size == 0:
        raise ValueError("y_probs must be a non-empty one-dimensional probability array")
    if not np.issubdtype(raw_y_probs.dtype, np.number) or np.iscomplexobj(raw_y_probs):
        raise ValueError("y_probs must contain real numeric probabilities")
    y_probs = raw_y_probs.astype(float)
    if y_probs.size != y_true.size:
        raise ValueError("y_true and y_probs must have the same number of entries")
    if not np.isfinite(y_probs).all():
        raise ValueError("y_probs must contain only finite values")
    if ((y_probs < 0.0) | (y_probs > 1.0)).any():
        raise ValueError("y_probs must be within [0, 1]")
    if isinstance(threshold, (bool, np.bool_)) or not np.isscalar(threshold):
        raise ValueError("threshold must be a finite number within [0, 1]")
    try:
        threshold = float(threshold)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("threshold must be a finite number within [0, 1]") from None
    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be a finite number within [0, 1]")

    # Ranking metrics are explicitly undefined for a single-class evaluation set.
    if has_both_classes:
        roc_auc: float | None = float(roc_auc_score(y_true, y_probs))
        prec_arr, rec_arr, _ = precision_recall_curve(y_true, y_probs)
        pr_auc: float | None = float(auc(rec_arr, prec_arr))
        ranking_status = "DEFINED"
        ranking_reason = None
    else:
        roc_auc = None
        pr_auc = None
        ranking_status = "UNDEFINED"
        ranking_reason = "single_class_labels"

    # Threshold-dependent metrics
    preds = (y_probs >= threshold).astype(int)

    cm = confusion_matrix(y_true, preds, labels=[0, 1])
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    else:
        tn, fp, fn, tp = 0, 0, 0, 0

    acc = float(accuracy_score(y_true, preds))
    macro_f1 = float(f1_score(y_true, preds, average="macro", zero_division=0))
    attack_f1 = float(f1_score(y_true, preds, pos_label=1, zero_division=0))
    benign_f1 = float(f1_score(y_true, preds, pos_label=0, zero_division=0))

    prec = float(precision_score(y_true, preds, zero_division=0))
    rec = float(recall_score(y_true, preds, zero_division=0))

    has_negatives = (fp + tn) > 0
    has_positives = (fn + tp) > 0
    fpr = float(fp / (fp + tn)) if has_negatives else None
    fnr = float(fn / (fn + tp)) if has_positives else None
    fp_per_1000 = float(fpr * 1000.0) if fpr is not None else None

    return {
        "roc_auc": roc_auc,
        "roc_auc_status": ranking_status,
        "roc_auc_reason": ranking_reason,
        "pr_auc": pr_auc,
        "pr_auc_status": ranking_status,
        "pr_auc_reason": ranking_reason,
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "macro_f1": macro_f1,
        "attack_f1": attack_f1,
        "benign_f1": benign_f1,
        "fpr": fpr,
        "fpr_status": "DEFINED" if has_negatives else "UNDEFINED",
        "fpr_reason": None if has_negatives else "no_negative_labels",
        "fnr": fnr,
        "fnr_status": "DEFINED" if has_positives else "UNDEFINED",
        "fnr_reason": None if has_positives else "no_positive_labels",
        "fp_per_1000": fp_per_1000,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "threshold": float(threshold),
        "result_status": "COMPLETE" if has_both_classes else "INCOMPLETE_METRICS",
    }
