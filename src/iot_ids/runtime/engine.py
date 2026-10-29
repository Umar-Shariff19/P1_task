"""Production Profile-Aware Multi-Dataset Inference Engine.

Loads trained model artifact suites for standardized_21 or historical_13 profiles,
validates feature dimensionalities, executes frozen preprocessor transformations (NO refitting),
and evaluates probability fusion ensembles for deployable multi-level IoT intrusion detection.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from iot_ids.runtime.schema import validate_input_schema, STANDARDIZED_21_FEATURES
from iot_ids.utils.paths import REPO_ROOT


class MLPModule(nn.Module):
    """PyTorch MLP Classifier Architecture [input_dim -> 128 -> 64 -> 32 -> 1]."""

    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class InferenceEngine:
    """Production-grade profile-aware inference engine supporting Option C ensemble prediction."""

    SUPPORTED_STANDARDIZED_DATASETS = {"ToN-IoT", "Edge-IIoTset", "NF-ToN-IoT-v2", "CICIoT2023"}
    SUPPORTED_HISTORICAL_DATASETS = {"ToN-IoT", "Edge-IIoTset"}

    def __init__(
        self,
        profile: str = "standardized_21",
        dataset: str = "ToN-IoT",
        models_base_dir: Optional[Union[str, Path]] = None,
        decision_threshold: float = 0.5,
        *,
        expected_digests: Optional[Dict[str, str]] = None,
        require_trusted_digests: bool = False,
        _synthetic_components: Optional[tuple[Any, Any, Any]] = None,
        authorization_provider: Optional[Any] = None,
        policy_document: Optional[Dict[str, Any]] = None,
    ):
        if _synthetic_components is None:
            from iot_ids.provenance.windows_access import require_real_data_authorization
            if authorization_provider is not None or policy_document is not None:
                base_dir = Path(models_base_dir) if models_base_dir else REPO_ROOT / "models" / ("standardized" if profile == "standardized_21" else "final")
                target_path = (base_dir / dataset).resolve() if dataset != "STANDALONE" else base_dir.resolve()
            else:
                target_path = None
            require_real_data_authorization(
                operation="read_checkpoint",
                target_path=target_path,
                provider=authorization_provider,
                policy=policy_document,
            )
        elif (
            profile != "standardized_21"
            or dataset != "SYNTHETIC_ONLY"
            or models_base_dir is not None
        ):
            raise ValueError(
                "Synthetic component injection requires profile='standardized_21', "
                "dataset='SYNTHETIC_ONLY', and no model directory."
            )
        self._validate_threshold(decision_threshold)
        self.profile = profile
        self.dataset = dataset
        self.decision_threshold = float(decision_threshold)
        self.expected_digests = expected_digests
        self.require_trusted_digests = require_trusted_digests

        if _synthetic_components is not None:
            if (
                profile != "standardized_21"
                or dataset != "SYNTHETIC_ONLY"
                or models_base_dir is not None
            ):
                raise ValueError(
                    "Synthetic component injection requires profile='standardized_21', "
                    "dataset='SYNTHETIC_ONLY', and no model directory."
                )
            if not isinstance(_synthetic_components, tuple) or len(_synthetic_components) != 3:
                raise ValueError("Synthetic components must be (preprocessor, RF model, MLP model).")
            self.model_dir = None
            self.expected_dim = len(STANDARDIZED_21_FEATURES)
            self.feature_names = list(STANDARDIZED_21_FEATURES)
            self.preprocessor, self.rf_model, self.robust_mlp_model = _synthetic_components
            self.robust_mlp_model.eval()
            self.historical_model = None
            self._validate_components()
            self.initialization_mode = "SYNTHETIC_IN_MEMORY_ONLY"
            return

        if self.profile == "standardized_21":
            if self.dataset not in self.SUPPORTED_STANDARDIZED_DATASETS:
                raise ValueError(
                    f"InferenceEngine Error: Dataset '{self.dataset}' is not supported for profile 'standardized_21'. "
                    f"Supported datasets: {sorted(list(self.SUPPORTED_STANDARDIZED_DATASETS))}"
                )
            base_dir = Path(models_base_dir) if models_base_dir else REPO_ROOT / "models" / "standardized"
            self.model_dir = base_dir / self.dataset
            self.expected_dim = 21
            self.feature_names = STANDARDIZED_21_FEATURES
        elif self.profile == "historical_13":
            if self.dataset not in self.SUPPORTED_HISTORICAL_DATASETS:
                raise ValueError(
                    f"InferenceEngine Error: Dataset '{self.dataset}' is not supported for profile 'historical_13'. "
                    f"Supported datasets: {sorted(list(self.SUPPORTED_HISTORICAL_DATASETS))}"
                )
            base_dir = Path(models_base_dir) if models_base_dir else REPO_ROOT / "models" / "final"
            self.model_dir = base_dir / self.dataset
            self.expected_dim = 13
            self.feature_names = None
        else:
            raise ValueError(f"InferenceEngine Error: Unsupported profile '{self.profile}'. Must be 'standardized_21' or 'historical_13'.")

        self.preprocessor = None
        self.rf_model = None
        self.robust_mlp_model = None
        self.historical_model = None

        self._load_and_validate_artifacts()
        self.initialization_mode = "CHECKPOINT_BACKED"

    @classmethod
    def for_synthetic_components(
        cls,
        *,
        preprocessor: Any,
        rf_model: Any,
        mlp_model: nn.Module,
        decision_threshold: float = 0.5,
    ) -> "InferenceEngine":
        """Build an inference engine from injected components for synthetic testing only.

        The factory cannot select a research dataset or model directory and never
        loads files. It exercises the same ``predict`` implementation as production.
        """
        return cls(
            profile="standardized_21",
            dataset="SYNTHETIC_ONLY",
            decision_threshold=decision_threshold,
            _synthetic_components=(preprocessor, rf_model, mlp_model),
        )

    @staticmethod
    def _validate_threshold(value: Any) -> None:
        if isinstance(value, (bool, np.bool_)) or not np.isscalar(value):
            raise ValueError("decision_threshold must be a finite number in [0, 1].")
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("decision_threshold must be a finite number in [0, 1].") from None
        if not np.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
            raise ValueError("decision_threshold must be a finite number in [0, 1].")

    def _validate_components(self) -> None:
        if not callable(getattr(self.preprocessor, "transform", None)):
            raise TypeError("Inference preprocessor must provide transform().")
        preprocessor_features = getattr(
            self.preprocessor,
            "feature_names",
            getattr(self.preprocessor, "numeric_cols", None),
        )
        if preprocessor_features is not None and list(preprocessor_features) != self.feature_names:
            raise ValueError("Inference preprocessor feature order does not match the runtime schema.")
        if not callable(getattr(self.rf_model, "predict_proba", None)):
            raise TypeError("Inference Random Forest component must provide predict_proba().")
        rf_dim = getattr(self.rf_model, "n_features_in_", None)
        if rf_dim is not None and int(rf_dim) != self.expected_dim:
            raise ValueError("Inference Random Forest feature dimension does not match the runtime schema.")
        if not isinstance(self.robust_mlp_model, nn.Module):
            raise TypeError("Inference MLP component must be a torch.nn.Module.")
        first_layer = getattr(getattr(self.robust_mlp_model, "net", None), "__getitem__", None)
        if callable(first_layer):
            try:
                input_dim = self.robust_mlp_model.net[0].in_features
            except (AttributeError, IndexError, TypeError):
                input_dim = None
            if input_dim is not None and int(input_dim) != self.expected_dim:
                raise ValueError("Inference MLP input dimension does not match the runtime schema.")

    def health_check(self) -> Dict[str, Any]:
        """Report interface readiness, not training quality or detection validity."""
        preprocessor_present = self.preprocessor is not None
        rf_present = self.rf_model is not None
        mlp_required = self.profile == "standardized_21"
        mlp_present = self.robust_mlp_model is not None

        preprocessor_ok = preprocessor_present and callable(
            getattr(self.preprocessor, "transform", None)
        )
        expected_features = getattr(self, "feature_names", None)
        actual_features = getattr(self.preprocessor, "feature_names", None) if preprocessor_present else None
        if preprocessor_present and actual_features is None:
            actual_features = getattr(self.preprocessor, "numeric_cols", None)
        if actual_features is None:
            preprocessor_ok = False
        else:
            try:
                actual_order = list(actual_features)
                preprocessor_ok = preprocessor_ok and len(actual_order) == self.expected_dim
                if expected_features is not None:
                    preprocessor_ok = preprocessor_ok and actual_order == list(expected_features)
            except (TypeError, ValueError):
                preprocessor_ok = False

        rf_ok = rf_present and callable(getattr(self.rf_model, "predict_proba", None))
        classes = getattr(self.rf_model, "classes_", None) if rf_present else None
        try:
            classes_ok = np.asarray(classes).shape == (2,) and np.array_equal(
                np.asarray(classes), np.array([0, 1])
            )
        except (TypeError, ValueError):
            classes_ok = False
        rf_ok = bool(rf_ok and classes_ok)
        mlp_ok = not mlp_required or (isinstance(self.robust_mlp_model, nn.Module)
                                      and callable(getattr(self.robust_mlp_model, "forward", None)))

        try:
            threshold = float(self.decision_threshold)
            threshold_ok = bool(np.isfinite(threshold) and 0.0 <= threshold <= 1.0)
        except (TypeError, ValueError, OverflowError):
            threshold = None
            threshold_ok = False

        components = {
            "preprocessor": (
                "MISSING" if not preprocessor_present else
                "INVALID" if not callable(getattr(self.preprocessor, "transform", None)) else
                "UNVERIFIED" if actual_features is None else
                "READY" if preprocessor_ok else "INVALID"
            ),
            "rf_model": (
                "MISSING" if not rf_present else
                "INVALID" if not callable(getattr(self.rf_model, "predict_proba", None)) else
                "UNVERIFIED" if classes is None else
                "READY" if rf_ok else "INVALID"
            ),
            "mlp_model": "READY" if mlp_ok else ("MISSING" if mlp_required and not mlp_present else "INVALID"),
            "decision_threshold": "READY" if threshold_ok else "INVALID",
        }
        reasons = [name for name, value in components.items() if value != "READY"]
        return {
            "status": "HEALTHY" if not reasons else "NOT_READY",
            "components": components,
            "not_ready_reasons": reasons,
            "profile": self.profile,
            "dataset": self.dataset,
            "feature_dimension": self.expected_dim,
            "initialization_mode": getattr(self, "initialization_mode", "UNINITIALIZED"),
            "readiness_scope": "component_interface_and_configuration_only",
            "model_training_state": "UNKNOWN",
            "detection_performance_validated": False,
            "decision_threshold": threshold,
        }

    def _transform_preprocessor_frozen(self, df_canonical: pd.DataFrame) -> np.ndarray:
        """Transform once, then enforce the model input shape and finite-value contract."""
        if not callable(getattr(self.preprocessor, "transform", None)):
            raise TypeError("Preprocessor object lacks transform() method.")
        try:
            transformed = np.asarray(self.preprocessor.transform(df_canonical), dtype=np.float64)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Preprocessor output must be a real numeric matrix.") from None
        expected_shape = (len(df_canonical), self.expected_dim)
        if transformed.shape != expected_shape:
            raise ValueError(
                f"Preprocessor output shape {transformed.shape} does not match {expected_shape}."
            )
        if not np.isfinite(transformed).all():
            raise ValueError("Preprocessor output must contain only finite values.")
        return transformed

    def _positive_class_probabilities(self, output: Any, row_count: int) -> np.ndarray:
        """Validate sklearn probability output and select class 1 explicitly."""
        probabilities = np.asarray(output)
        if probabilities.shape != (row_count, 2):
            raise ValueError("Classifier predict_proba() must return an (n_samples, 2) matrix.")
        if not np.issubdtype(probabilities.dtype, np.number) or np.iscomplexobj(probabilities):
            raise ValueError("Classifier probabilities must be real numeric values.")
        probabilities = probabilities.astype(np.float64)
        if not np.isfinite(probabilities).all():
            raise ValueError("Classifier probabilities must be finite.")
        if ((probabilities < 0.0) | (probabilities > 1.0)).any():
            raise ValueError("Classifier probabilities must be within [0, 1].")
        classes = np.asarray(getattr(self.rf_model, "classes_", []))
        if classes.shape != (2,) or not np.array_equal(classes, np.array([0, 1])):
            raise ValueError("Classifier classes must be ordered as binary labels [0, 1].")
        if not np.allclose(probabilities.sum(axis=1), 1.0, rtol=1e-6, atol=1e-7):
            raise ValueError("Classifier probability rows must sum to 1.")
        return probabilities[:, 1]

    @staticmethod
    def _load_mlp_checkpoint(
        mlp_path: Path,
        expected_dim: int,
        expected_digest: Optional[str] = None,
        base_dir: Optional[Path] = None,
    ) -> MLPModule:
        """Safely load and validate an MLP state dictionary artifact.

        Enforces weights_only=True fail-closed deserialization. Rejects full-model pickles,
        unsupported formats, dimension mismatches, and key incompatibilities.
        If expected_digest is provided, verifies SHA-256 before deserializing.
        """
        import io
        if expected_digest is not None:
            from iot_ids.provenance.artifact_integrity import verify_and_read_artifact
            effective_base = base_dir or mlp_path.parent
            content = verify_and_read_artifact(
                mlp_path.name, expected_digest=expected_digest, base_dir=effective_base
            )
            load_target = io.BytesIO(content)
        else:
            load_target = mlp_path

        try:
            mlp_state = torch.load(load_target, weights_only=True)
        except Exception as exc:
            raise TypeError(
                f"InferenceEngine Error: Failed to safely load MLP state dictionary from '{mlp_path.name}': {type(exc).__name__}"
            ) from exc

        if not isinstance(mlp_state, dict):
            raise TypeError(
                f"InferenceEngine Error: MLP artifact at '{mlp_path}' must be a state dictionary, "
                f"got {type(mlp_state).__name__}."
            )

        if "net.0.weight" not in mlp_state:
            raise KeyError(
                f"InferenceEngine Error: MLP state dictionary at '{mlp_path}' missing required key 'net.0.weight'."
            )

        weight_tensor = mlp_state["net.0.weight"]
        if not isinstance(weight_tensor, torch.Tensor) or weight_tensor.ndim != 2:
            raise ValueError(
                f"InferenceEngine Error: 'net.0.weight' must be a 2-D tensor in '{mlp_path}'."
            )

        mlp_in_dim = weight_tensor.shape[1]
        if mlp_in_dim != expected_dim:
            raise ValueError(
                f"InferenceEngine Dimension Mismatch: Robust MLP input_dim={mlp_in_dim}, "
                f"expected {expected_dim}."
            )

        model = MLPModule(input_dim=expected_dim)
        try:
            model.load_state_dict(mlp_state, strict=True)
        except Exception as exc:
            raise ValueError(
                f"InferenceEngine Error: Incompatible state dictionary keys in '{mlp_path}': {exc}"
            ) from exc

        model.eval()
        return model

    def _load_and_validate_artifacts(self) -> None:
        """Loads model artifacts and validates feature input dimensions fail-fast."""
        if not self.model_dir.exists():
            raise FileNotFoundError(f"InferenceEngine Error: Model directory not found: {self.model_dir}")

        if self.profile == "standardized_21":
            prep_path = self.model_dir / "prep_standardized.joblib"
            rf_path = self.model_dir / "rf_model.joblib"
            mlp_path = self.model_dir / "mlp_adversarial.pt"

            if not prep_path.exists():
                raise FileNotFoundError(f"Missing preprocessor artifact: {prep_path}")
            if not rf_path.exists():
                raise FileNotFoundError(f"Missing Random Forest artifact: {rf_path}")
            if not mlp_path.exists():
                raise FileNotFoundError(f"Missing Adversarial MLP artifact: {mlp_path}")

            if self.expected_digests is not None:
                from iot_ids.provenance.artifact_integrity import (
                    ArtifactIntegrityError,
                    load_verified_joblib,
                )
                prep_digest = self.expected_digests.get(prep_path.name)
                rf_digest = self.expected_digests.get(rf_path.name)
                mlp_digest = self.expected_digests.get(mlp_path.name)
                if not prep_digest:
                    raise ArtifactIntegrityError(f"Missing expected digest for '{prep_path.name}'")
                if not rf_digest:
                    raise ArtifactIntegrityError(f"Missing expected digest for '{rf_path.name}'")
                self.preprocessor = load_verified_joblib(
                    prep_path.name, expected_digest=prep_digest, base_dir=self.model_dir
                )
                self.rf_model = load_verified_joblib(
                    rf_path.name, expected_digest=rf_digest, base_dir=self.model_dir
                )
                self.robust_mlp_model = self._load_mlp_checkpoint(
                    mlp_path, self.expected_dim, expected_digest=mlp_digest, base_dir=self.model_dir
                )
            elif self.require_trusted_digests:
                from iot_ids.provenance.artifact_integrity import ArtifactIntegrityError
                raise ArtifactIntegrityError(
                    f"Trusted digest verification required for '{self.model_dir}', but no expected_digests was provided."
                )
            else:
                self.preprocessor = joblib.load(prep_path)
                self.rf_model = joblib.load(rf_path)
                self.robust_mlp_model = self._load_mlp_checkpoint(mlp_path, self.expected_dim)

            # Dimension Validation
            prep_feats = getattr(self.preprocessor, "feature_names", None)
            if prep_feats is not None and len(prep_feats) != self.expected_dim:
                raise ValueError(
                    f"InferenceEngine Dimension Mismatch: Preprocessor has {len(prep_feats)} features, "
                    f"expected {self.expected_dim} for profile '{self.profile}'."
                )

            rf_dim = getattr(self.rf_model, "n_features_in_", None)
            if rf_dim is not None and rf_dim != self.expected_dim:
                raise ValueError(
                    f"InferenceEngine Dimension Mismatch: Random Forest n_features_in_={rf_dim}, "
                    f"expected {self.expected_dim} for profile '{self.profile}'."
                )

        else:
            # Historical 13-feature profile loading
            prep_path = self.model_dir / "prep_indomain.joblib"
            rf_path = self.model_dir / "rf_model.joblib"

            if not prep_path.exists():
                raise FileNotFoundError(f"Missing historical preprocessor artifact: {prep_path}")
            if not rf_path.exists():
                raise FileNotFoundError(f"Missing historical Random Forest artifact: {rf_path}")

            if self.expected_digests is not None:
                from iot_ids.provenance.artifact_integrity import (
                    ArtifactIntegrityError,
                    load_verified_joblib,
                )
                prep_digest = self.expected_digests.get(prep_path.name)
                rf_digest = self.expected_digests.get(rf_path.name)
                if not prep_digest:
                    raise ArtifactIntegrityError(f"Missing expected digest for '{prep_path.name}'")
                if not rf_digest:
                    raise ArtifactIntegrityError(f"Missing expected digest for '{rf_path.name}'")
                self.preprocessor = load_verified_joblib(
                    prep_path.name, expected_digest=prep_digest, base_dir=self.model_dir
                )
                self.rf_model = load_verified_joblib(
                    rf_path.name, expected_digest=rf_digest, base_dir=self.model_dir
                )
            elif self.require_trusted_digests:
                from iot_ids.provenance.artifact_integrity import ArtifactIntegrityError
                raise ArtifactIntegrityError(
                    f"Trusted digest verification required for '{self.model_dir}', but no expected_digests was provided."
                )
            else:
                self.preprocessor = joblib.load(prep_path)
                self.rf_model = joblib.load(rf_path)

            hist_feats = getattr(self.preprocessor, "numeric_cols", getattr(self.preprocessor, "feature_names", None))
            if hist_feats is not None:
                self.feature_names = list(hist_feats)
                if len(self.feature_names) != self.expected_dim:
                    raise ValueError(
                        f"InferenceEngine Dimension Mismatch: Historical preprocessor has {len(self.feature_names)} features, "
                        f"expected {self.expected_dim} for profile '{self.profile}'."
                    )

            rf_dim = getattr(self.rf_model, "n_features_in_", None)
            if rf_dim is not None and rf_dim != self.expected_dim:
                raise ValueError(
                    f"InferenceEngine Dimension Mismatch: Historical RF n_features_in_={rf_dim}, "
                    f"expected {self.expected_dim} for profile '{self.profile}'."
                )

    def predict(
        self,
        inputs: Union[pd.DataFrame, Dict[str, Any], np.ndarray, List[Dict[str, Any]]],
        explain: bool = False,
        top_k: int = 5,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Runs end-to-end inference over input flow samples.

        Args:
            inputs: Sample inputs as DataFrame, Dict, List of Dicts, or Numpy array.
            explain: If True, attaches local XAI explanation dict to each prediction output.
            top_k: Number of top influential features to include when explain=True.

        Returns:
            Structured prediction dictionary (single sample) or list of prediction dicts (batch).
        """
        # 1. Schema Validation & Canonical Ordering
        if explain and (
            isinstance(top_k, (bool, np.bool_))
            or not isinstance(top_k, (int, np.integer))
            or not 1 <= int(top_k) <= self.expected_dim
        ):
            raise ValueError(f"top_k must be an integer in [1, {self.expected_dim}] when explain=True.")
        df_canonical = validate_input_schema(
            inputs,
            profile=self.profile,
            expected_feature_names=self.feature_names,
        )

        is_single = isinstance(inputs, dict) or (isinstance(inputs, np.ndarray) and inputs.ndim == 1)

        # 2. Preprocessing Transformation (FROZEN - NO FIT)
        X_proc = self._transform_preprocessor_frozen(df_canonical)
        row_count = len(df_canonical)

        # 3. Model Inference Execution
        if self.profile == "standardized_21":
            # RF Probabilities
            rf_probs = self._positive_class_probabilities(
                self.rf_model.predict_proba(X_proc), row_count
            )

            # Robust PyTorch MLP Probabilities
            with torch.no_grad():
                mlp_logits = self.robust_mlp_model(
                    torch.tensor(X_proc, dtype=torch.float32)
                )
            if not isinstance(mlp_logits, torch.Tensor):
                raise ValueError("MLP output must be a torch tensor of binary logits.")
            if mlp_logits.shape == (row_count, 1):
                mlp_logits = mlp_logits[:, 0]
            elif mlp_logits.shape != (row_count,):
                raise ValueError("MLP output must have one logit per input sample.")
            if not torch.isfinite(mlp_logits).all():
                raise ValueError("MLP logits must contain only finite values.")
            mlp_probs = torch.sigmoid(mlp_logits).detach().cpu().numpy().astype(np.float64)

            # Option C Probability Fusion: 0.7 * P_RF + 0.3 * P_MLP_Adv
            if rf_probs.shape != (row_count,) or mlp_probs.shape != (row_count,):
                raise ValueError("Model probability outputs must match the input batch length.")
            ensemble_probs = 0.7 * rf_probs + 0.3 * mlp_probs
            if (
                not np.isfinite(ensemble_probs).all()
                or ((ensemble_probs < 0.0) | (ensemble_probs > 1.0)).any()
            ):
                raise ValueError("Fused probabilities must be finite values within [0, 1].")

            results = []
            for i in range(len(ensemble_probs)):
                p_ens = float(ensemble_probs[i])
                p_rf = float(rf_probs[i])
                p_mlp = float(mlp_probs[i])
                is_anom = int(p_ens >= self.decision_threshold)

                res = {
                    "prediction": is_anom,
                    "probability": p_ens,
                    "rf_probability": p_rf,
                    "robust_mlp_probability": p_mlp,
                    "profile": self.profile,
                    "dataset": self.dataset,
                    "feature_dimension": self.expected_dim,
                }

                if explain and self.feature_names:
                    from iot_ids.xai.local_xai import explain_local_sample
                    local_exp = explain_local_sample(
                        rf_model=self.rf_model,
                        mlp_model=self.robust_mlp_model,
                        x_single=X_proc[i],
                        feature_names=self.feature_names,
                        top_k=top_k,
                    )
                    if (
                        not isinstance(local_exp, dict)
                        or not isinstance(local_exp.get("top_k_features"), list)
                        or len(local_exp["top_k_features"]) != min(int(top_k), self.expected_dim)
                    ):
                        raise ValueError("Explainability output does not match the requested top_k contract.")
                    res["explanation"] = local_exp

                results.append(res)

        else:
            # Historical 13-feature profile (RF only)
            rf_probs = self._positive_class_probabilities(
                self.rf_model.predict_proba(X_proc), row_count
            )
            results = []
            for i in range(len(rf_probs)):
                p_rf = float(rf_probs[i])
                is_anom = int(p_rf >= self.decision_threshold)
                results.append({
                    "prediction": is_anom,
                    "probability": p_rf,
                    "rf_probability": p_rf,
                    "profile": self.profile,
                    "dataset": self.dataset,
                    "feature_dimension": self.expected_dim,
                })

        if is_single and len(results) == 1:
            return results[0]
        return results
