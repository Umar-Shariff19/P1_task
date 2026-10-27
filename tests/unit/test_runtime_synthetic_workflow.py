"""Synthetic-only runtime and provenance smoke path.

This test creates every sample and model itself in a temporary folder. It uses
the explicit ``InferenceEngine.for_synthetic_components()`` construction path,
which calls the normal constructor without loading files. The fixture is not
an IDS benchmark or evidence of research performance.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import tempfile
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
import torch
from torch import nn

from iot_ids.preprocessing.pipeline import PreprocessingPipeline
from iot_ids.provenance import validate_manifest
from iot_ids.provenance.artifact_integrity import verify_artifact_digest
from iot_ids.provenance.preflight import (
    ArtifactEvidence,
    AuthorizationDecision,
    AuthorizationScope,
    AuthorizationStatus,
    IntegrityStatus,
    PreflightStatus,
    evaluate_preflight,
)
from iot_ids.runtime.engine import InferenceEngine, MLPModule
from iot_ids.runtime.schema import STANDARDIZED_21_FEATURES, validate_input_schema


_EXAMPLE_MANIFEST = (
    Path(__file__).parents[2]
    / "results"
    / "provenance"
    / "experiment_manifest_schema_examples.json"
)


class _SyntheticOnlyPolicy:
    """Test-local policy. It cannot authorize real-data operations."""

    def authorize(self, _manifest: dict) -> AuthorizationDecision:
        return AuthorizationDecision(
            AuthorizationStatus.AUTHORIZED,
            AuthorizationScope.SYNTHETIC_ONLY,
        )


class _RealDataDeniedPolicy:
    """Test-local explicit denial for a real-data request."""

    def authorize(self, _manifest: dict) -> AuthorizationDecision:
        return AuthorizationDecision(
            AuthorizationStatus.AUTHORIZED,
            AuthorizationScope.REAL_DATA,
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_runtime_schema_rejects_non_numeric_features_with_controlled_error() -> None:
    sample = {name: 0.25 for name in STANDARDIZED_21_FEATURES}
    sample[STANDARDIZED_21_FEATURES[3]] = "not-numeric"
    try:
        validate_input_schema(sample)
    except ValueError as error:
        assert "real numeric values" in str(error)
        assert STANDARDIZED_21_FEATURES[3] in str(error)
    else:
        raise AssertionError("non-numeric feature unexpectedly passed validation")


def test_synthetic_runtime_inference_xai_metrics_and_provenance() -> None:
    rng = np.random.default_rng(20261028)
    n_train, n_test = 64, 16
    labels = np.tile(np.array([0, 1], dtype=np.int64), (n_train + n_test) // 2)
    raw = rng.uniform(0.05, 2.0, size=(n_train + n_test, len(STANDARDIZED_21_FEATURES)))
    raw[:, 0] = 0.1 + labels.astype(float) * 0.6
    frame = pd.DataFrame(raw, columns=STANDARDIZED_21_FEATURES)
    train_frame = frame.iloc[:n_train].copy()
    test_frame = frame.iloc[n_train:].copy()
    y_train, y_test = labels[:n_train], labels[n_train:]

    preprocessor = PreprocessingPipeline(STANDARDIZED_21_FEATURES)
    X_train = preprocessor.fit_transform(train_frame)
    rf_model = RandomForestClassifier(n_estimators=12, random_state=17, n_jobs=1)
    rf_model.fit(X_train, y_train)
    torch.manual_seed(19)
    mlp_model = MLPModule(input_dim=len(STANDARDIZED_21_FEATURES))
    mlp_model.eval()  # newly initialized synthetic model; no checkpoint is loaded

    # Use the explicit no-file synthetic construction path and the same predict()
    # method used after production checkpoint loading.
    engine = InferenceEngine.for_synthetic_components(
        preprocessor=preprocessor,
        rf_model=rf_model,
        mlp_model=mlp_model,
    )
    assert engine.dataset == "SYNTHETIC_ONLY"
    assert engine.initialization_mode == "SYNTHETIC_IN_MEMORY_ONLY"
    with pytest.raises(ValueError, match="at least one sample"):
        engine.predict(pd.DataFrame(columns=STANDARDIZED_21_FEATURES))
    with pytest.raises(ValueError, match="top_k must be"):
        engine.predict(test_frame.iloc[:1], explain=True, top_k=0)

    predictions = engine.predict(test_frame, explain=True, top_k=3)
    assert isinstance(predictions, list) and len(predictions) == n_test
    for item in predictions:
        expected = 0.7 * item["rf_probability"] + 0.3 * item["robust_mlp_probability"]
        assert item["probability"] == pytest.approx(expected, abs=1e-7)
        assert item["dataset"] == "SYNTHETIC_ONLY"
        assert len(item["explanation"]["top_k_features"]) == 3

    probabilities = np.asarray([item["probability"] for item in predictions])
    synthetic_auc = float(roc_auc_score(y_test, probabilities))
    result_record = {
        "status": "SYNTHETIC_ONLY_NOT_AN_IDS_BENCHMARK",
        "seed": 20261028,
        "samples": n_test,
        "metric": {
            "name": "synthetic_auc_arithmetic_smoke_check",
            "definition": "ROC-AUC on generated labels and synthetic model outputs only",
            "value": synthetic_auc,
        },
        "predictions": predictions,
    }

    with tempfile.TemporaryDirectory(
        prefix="synthetic-runtime-", dir=Path(__file__).parent
    ) as temporary:
        output_dir = Path(temporary)
        result_path = output_dir / "synthetic_result.json"
        rf_path = output_dir / "synthetic_rf.joblib"
        mlp_path = output_dir / "synthetic_mlp.pt"
        joblib.dump(rf_model, rf_path)
        torch.save(mlp_model.state_dict(), mlp_path)
        result_path.write_text(json.dumps(result_record, indent=2), encoding="utf-8")

        examples = json.loads(_EXAMPLE_MANIFEST.read_text(encoding="utf-8"))
        manifest = copy.deepcopy(examples["positive"])
        manifest.update(
            experiment_id="synthetic-runtime-workflow-only",
            started_at="2026-10-28T00:00:00Z",
            finished_at=datetime.now(timezone.utc).isoformat(),
            source={
                "revision": "0000000000000000000000000000000000000000",
                "working_tree_dirty": False,
                "entrypoint": "tests/unit/test_runtime_synthetic_workflow.py",
                "command": "pytest synthetic runtime workflow test",
            },
            safety_policy_version="synthetic-test-only-no-research-authorization",
            datasets=[
                {
                    "dataset_id": "generated-synthetic-only",
                    "authorization_reference": "NOT_AUTHORIZED_FOR_RESEARCH_DATA",
                    "split_id": "seeded-synthetic-holdout-only",
                    "generator": {
                        "name": "numpy-default-rng",
                        "version": importlib.metadata.version("numpy"),
                        "config": {"seed": 20261028, "train_rows": n_train, "test_rows": n_test},
                    },
                }
            ],
            models=[
                {
                    "model_id": "synthetic-random-forest",
                    "checkpoint_id": "synthetic_rf.joblib",
                    "checkpoint_sha256": _sha256(rf_path),
                    "config": {"estimators": 12, "random_state": 17},
                },
                {
                    "model_id": "synthetic-untrained-mlp-initialization",
                    "checkpoint_id": "synthetic_mlp.pt",
                    "checkpoint_sha256": _sha256(mlp_path),
                    "config": {"input_dim": len(STANDARDIZED_21_FEATURES), "seed": 19, "trained": False},
                },
            ],
            training_config={"scope": "synthetic-only", "rf_fit_rows": n_train, "mlp_fit": False},
            evaluation_config={"scope": "synthetic-only", "holdout_rows": n_test, "fusion_weights": [0.7, 0.3]},
            environment={
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "dependencies": {
                    "numpy": importlib.metadata.version("numpy"),
                    "pandas": importlib.metadata.version("pandas"),
                    "scikit-learn": importlib.metadata.version("scikit-learn"),
                    "torch": importlib.metadata.version("torch"),
                },
                "lockfile_id": None,
            },
            metrics=[
                {
                    **result_record["metric"],
                    "split_id": "seeded-synthetic-holdout-only",
                }
            ],
            outputs=[
                {"artifact_id": "synthetic-result-json", "role": "synthetic-result", "sha256": _sha256(result_path)},
                {"artifact_id": "synthetic-rf-checkpoint", "role": "synthetic-checkpoint", "sha256": _sha256(rf_path)},
                {"artifact_id": "synthetic-mlp-checkpoint", "role": "synthetic-checkpoint", "sha256": _sha256(mlp_path)},
            ],
        )
        manifest_path = output_dir / "experiment_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        validated = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
        assert validated.schema_valid
        assert validated.authorization_verified is False
        assert validated.evidence_truth_verified is False

        evidence = tuple(
            ArtifactEvidence(path.name, "sha256", _sha256(path), str(output_dir))
            for path in (result_path, rf_path, mlp_path)
        )
        preflight = evaluate_preflight(
            manifest,
            authorization_policy=_SyntheticOnlyPolicy(),
            artifact_evidence=evidence,
            require_artifacts=True,
        )
        assert preflight.status is PreflightStatus.READY_SYNTHETIC
        assert preflight.integrity_status is IntegrityStatus.VERIFIED
        assert preflight.evidence_status.value == "UNVERIFIED"

        real_data = evaluate_preflight(
            manifest,
            authorization_policy=_RealDataDeniedPolicy(),
        )
        assert real_data.status is PreflightStatus.BLOCKED
        assert real_data.status is not PreflightStatus.READY_SYNTHETIC

        stored_result = json.loads(result_path.read_text(encoding="utf-8"))
        stored_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert stored_result["status"] == "SYNTHETIC_ONLY_NOT_AN_IDS_BENCHMARK"
        assert stored_manifest["experiment_id"] == "synthetic-runtime-workflow-only"
        for item in evidence:
            assert verify_artifact_digest(
                item.relative_path,
                algorithm=item.algorithm,
                expected_digest=item.expected_digest,
                base_dir=item.base_dir,
            ).status == "MATCH"


def test_synthetic_engine_rejects_malformed_model_outputs_and_inputs() -> None:
    rng = np.random.default_rng(8128)
    labels = np.tile(np.array([0, 1], dtype=np.int64), 16)
    raw = rng.uniform(0.05, 1.0, size=(32, len(STANDARDIZED_21_FEATURES)))
    raw[:, 0] += labels
    frame = pd.DataFrame(raw, columns=STANDARDIZED_21_FEATURES)
    preprocessor = PreprocessingPipeline(STANDARDIZED_21_FEATURES)
    train = preprocessor.fit_transform(frame)
    rf_model = RandomForestClassifier(n_estimators=4, random_state=5, n_jobs=1).fit(train, labels)
    mlp_model = MLPModule(input_dim=len(STANDARDIZED_21_FEATURES)).eval()
    engine = InferenceEngine.for_synthetic_components(
        preprocessor=preprocessor,
        rf_model=rf_model,
        mlp_model=mlp_model,
    )

    invalid = frame.iloc[:1].astype(object).copy()
    invalid.iloc[0, 0] = "invalid"
    with pytest.raises(ValueError, match="real numeric values"):
        engine.predict(invalid)

    class MalformedRF:
        classes_ = np.array([0, 1])

        def predict_proba(self, values):
            return np.ones((len(values), 1), dtype=float)

    original_rf = engine.rf_model
    engine.rf_model = MalformedRF()
    with pytest.raises(ValueError, match=r"\(n_samples, 2\)"):
        engine.predict(frame.iloc[:2])
    engine.rf_model = original_rf

    class MalformedMLP(nn.Module):
        def forward(self, values):
            return torch.full((values.shape[0], 2), float("nan"))

    engine.robust_mlp_model = MalformedMLP()
    with pytest.raises(ValueError, match="one logit per input sample"):
        engine.predict(frame.iloc[:2])

    class NonfiniteMLP(nn.Module):
        def forward(self, values):
            return torch.full((values.shape[0], 1), float("nan"))

    engine.robust_mlp_model = NonfiniteMLP()
    with pytest.raises(ValueError, match="finite values"):
        engine.predict(frame.iloc[:2])


def test_synthetic_constructor_rejects_component_schema_mismatch() -> None:
    class WrongOrderPreprocessor:
        feature_names = list(reversed(STANDARDIZED_21_FEATURES))

        def transform(self, values):
            return values.to_numpy()

    with pytest.raises(ValueError, match="feature order"):
        InferenceEngine.for_synthetic_components(
            preprocessor=WrongOrderPreprocessor(),
            rf_model=object(),
            mlp_model=MLPModule(input_dim=len(STANDARDIZED_21_FEATURES)),
        )
