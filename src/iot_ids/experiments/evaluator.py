"""Stage 4 Metrics Evaluator & Validation Threshold Optimizer.

Calculates threshold-independent metrics (ROC-AUC, PR-AUC), threshold-dependent metrics
(Accuracy, Macro F1, Attack F1, Benign F1, FPR, FNR, FP/1000), and source-validation threshold optimization.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Dict, Any, Union
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

_HEX_64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def load_evaluation_schema() -> Dict[str, Any]:
    """Loads the real-data evaluation JSON schema from configs/real_data_evaluation_schema.json."""
    from iot_ids.utils.paths import REPO_ROOT

    schema_path = REPO_ROOT / "configs" / "real_data_evaluation_schema.json"
    if schema_path.is_file():
        try:
            return json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Embedded fallback to guarantee offline availability and closed failure mode
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "RealDataEvaluationArtifactSchema",
        "type": "object",
        "required": [
            "evaluation_metadata",
            "dataset_provenance",
            "artifact_digests",
            "feature_schema",
            "split_provenance",
            "model_configuration",
            "performance_metrics",
            "system_and_latency",
        ],
        "properties": {
            "evaluation_metadata": {
                "type": "object",
                "required": [
                    "timestamp_iso",
                    "git_commit",
                    "authorization_scope",
                    "evaluation_type",
                    "reproducible_command",
                ],
                "properties": {
                    "timestamp_iso": {"type": "string"},
                    "git_commit": {"type": "string"},
                    "authorization_scope": {"type": "string"},
                    "evaluation_type": {
                        "type": "string",
                        "enum": ["REAL_DATA_OFFICIAL", "SYNTHETIC_BENCHMARK_ONLY"],
                    },
                    "reproducible_command": {"type": "string"},
                },
            },
            "dataset_provenance": {
                "type": "object",
                "required": ["dataset_id", "source_digest_sha256", "record_count", "class_balance"],
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "enum": [
                            "Edge-IIoTset",
                            "ToN-IoT",
                            "NF-ToN-IoT-v2",
                            "CICIoT2023",
                            "CICIDS2017",
                            "BoT-IoT",
                            "N-BaIoT",
                        ],
                    },
                    "source_digest_sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
                    "record_count": {"type": "integer", "minimum": 1},
                    "class_balance": {"type": "object"},
                },
            },
            "artifact_digests": {
                "type": "object",
                "required": ["rf_model_sha256", "preprocessor_sha256"],
                "properties": {
                    "rf_model_sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
                    "mlp_model_sha256": {"type": ["string", "null"]},
                    "ae_model_sha256": {"type": ["string", "null"]},
                    "preprocessor_sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
                },
            },
            "feature_schema": {
                "type": "object",
                "required": ["profile_name", "feature_count", "canonical_feature_names"],
                "properties": {
                    "profile_name": {"type": "string"},
                    "feature_count": {"type": "integer", "enum": [6, 13, 21]},
                    "canonical_feature_names": {"type": "array", "items": {"type": "string"}},
                },
            },
            "split_provenance": {
                "type": "object",
                "required": [
                    "split_strategy",
                    "train_indices_hash",
                    "val_indices_hash",
                    "test_indices_hash",
                    "temporal_non_inversion_verified",
                ],
                "properties": {
                    "split_strategy": {"type": "string", "enum": ["chronological", "stratified"]},
                    "train_indices_hash": {"type": "string"},
                    "val_indices_hash": {"type": "string"},
                    "test_indices_hash": {"type": "string"},
                    "temporal_non_inversion_verified": {"type": "boolean"},
                },
            },
            "model_configuration": {
                "type": "object",
                "required": ["architecture", "fusion_weights", "decision_threshold"],
                "properties": {
                    "architecture": {"type": "string"},
                    "fusion_weights": {"type": "object"},
                    "decision_threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
            },
            "performance_metrics": {
                "type": "object",
                "required": [
                    "accuracy",
                    "precision",
                    "recall",
                    "f1_score",
                    "roc_auc",
                    "pr_auc",
                    "false_positive_rate",
                    "confusion_matrix",
                ],
                "properties": {
                    "accuracy": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "precision": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "recall": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "f1_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "roc_auc": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "pr_auc": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "false_positive_rate": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "confusion_matrix": {"type": "object"},
                },
            },
            "system_and_latency": {
                "type": "object",
                "required": [
                    "latency_p50_ms",
                    "latency_p95_ms",
                    "latency_p99_ms",
                    "throughput_flows_per_sec",
                    "peak_memory_mb",
                    "python_version",
                    "torch_version",
                    "sklearn_version",
                ],
                "properties": {
                    "latency_p50_ms": {"type": "number", "minimum": 0.0},
                    "latency_p95_ms": {"type": "number", "minimum": 0.0},
                    "latency_p99_ms": {"type": "number", "minimum": 0.0},
                    "throughput_flows_per_sec": {"type": "number", "minimum": 0.0},
                    "peak_memory_mb": {"type": "number", "minimum": 0.0},
                    "python_version": {"type": "string"},
                    "torch_version": {"type": "string"},
                    "sklearn_version": {"type": "string"},
                },
            },
        },
    }


def validate_evaluation_report(report: Union[Dict[str, Any], Path, str]) -> Dict[str, Any]:
    """Validates an evaluation report against the real-data evaluation schema and domain rules.

    Enforces:
    1. Structural compliance with configs/real_data_evaluation_schema.json.
    2. Strict bounds on performance metrics ([0.0, 1.0] for rate/score metrics).
    3. Proper 64-character hex digests for models, preprocessor, and source datasets.
    4. Prohibition of synthetic-as-real claims (rejects REAL_DATA_OFFICIAL when synthetic indicators are present).
    5. Non-empty authorization scope when claiming REAL_DATA_OFFICIAL.

    Returns the validated report dictionary or raises ValueError.
    """
    if isinstance(report, (str, Path)):
        p = Path(report)
        if not p.is_file():
            raise ValueError(f"Report file not found: {p}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Failed to parse evaluation report JSON from {p}: {exc}") from exc
    elif isinstance(report, dict):
        data = report
    else:
        raise ValueError("Report must be a dictionary or a path to a valid JSON file.")

    schema = load_evaluation_schema()
    try:
        import jsonschema

        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"Evaluation report schema validation failed: {exc.message}") from exc

    metadata = data.get("evaluation_metadata", {})
    eval_type = metadata.get("evaluation_type")
    auth_scope = str(metadata.get("authorization_scope", "")).strip()

    # Integrity rule: Cannot claim REAL_DATA_OFFICIAL if synthetic indicators are present
    synthetic_indicators = [
        data.get("synthetic_data"),
        metadata.get("synthetic_data"),
        data.get("is_synthetic"),
        metadata.get("is_synthetic"),
        data.get("dataset_provenance", {}).get("synthetic_data"),
        data.get("dataset_provenance", {}).get("is_synthetic"),
    ]
    has_synthetic_flag = any(flag is True for flag in synthetic_indicators)
    auth_scope_lower = auth_scope.lower()
    suspicious_auth = any(
        tok in auth_scope_lower for tok in ("synthetic", "mock", "dummy", "unauthorized", "none")
    )

    if eval_type == "REAL_DATA_OFFICIAL":
        if has_synthetic_flag:
            raise ValueError(
                "Integrity violation: Report specifies evaluation_type='REAL_DATA_OFFICIAL' "
                "but contains synthetic data indicators."
            )
        if not auth_scope or suspicious_auth:
            raise ValueError(
                f"Integrity violation: Report specifies evaluation_type='REAL_DATA_OFFICIAL' "
                f"but has invalid or synthetic authorization_scope: '{auth_scope}'."
            )

    # Check metrics ranges
    metrics = data.get("performance_metrics", {})
    for metric_name in (
        "accuracy",
        "precision",
        "recall",
        "f1_score",
        "roc_auc",
        "pr_auc",
        "false_positive_rate",
    ):
        val = metrics.get(metric_name)
        if val is None or not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueError(f"Metric '{metric_name}' must be a numeric value, got: {type(val)}")
        if not (0.0 <= float(val) <= 1.0):
            raise ValueError(f"Metric '{metric_name}' must be within [0.0, 1.0], got: {val}")

    # Check hex digests
    provenance = data.get("dataset_provenance", {})
    source_digest = provenance.get("source_digest_sha256", "")
    if not _HEX_64_PATTERN.match(source_digest):
        raise ValueError(f"Invalid SHA-256 digest for source dataset: '{source_digest}'")

    digests = data.get("artifact_digests", {})
    for key in ("rf_model_sha256", "preprocessor_sha256"):
        digest_val = digests.get(key, "")
        if not _HEX_64_PATTERN.match(str(digest_val)):
            raise ValueError(f"Invalid SHA-256 digest for {key}: '{digest_val}'")

    for opt_key in ("mlp_model_sha256", "ae_model_sha256"):
        val = digests.get(opt_key)
        if val is not None and not _HEX_64_PATTERN.match(str(val)):
            raise ValueError(f"Invalid optional SHA-256 digest for {opt_key}: '{val}'")

    return data


def save_validated_evaluation_report(
    report: Union[Dict[str, Any], Path, str],
    output_path: Union[Path, str],
) -> Path:
    """Validates an evaluation report against the schema and atomically persists it.

    Fails closed: if validation fails, the output file is NOT created or modified.
    Returns the resolved output Path.
    """
    validated_data = validate_evaluation_report(report)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    temp_file = out.with_suffix(f"{out.suffix}.tmp")
    try:
        temp_file.write_text(json.dumps(validated_data, indent=2), encoding="utf-8")
        temp_file.replace(out)
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
    return out


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
