"""Trained Multi-Level Pipeline Model Registry & Artifact Serialization Manager.

Saves and loads deployable pipeline artifacts containing model estimators, preprocessors,
aligners, threshold calibrators, and metadata independently of training code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional
import joblib

from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.experiments.preprocessing import FeaturePreprocessor
from iot_ids.adaptation.alignment import UnsupervisedFeatureAligner
from iot_ids.adaptation.calibration import TargetThresholdCalibrator
from iot_ids.provenance.artifact_integrity import (
    ArtifactIntegrityError,
    load_verified_joblib,
)


class ModelRegistry:
    """Registry manager for serializing and deserializing multi-level IDS pipeline artifacts."""

    @staticmethod
    def save_pipeline(
        pipeline: IDSSystemPipeline,
        save_dir: Path,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        authorization_provider: Optional[Any] = None,
        policy_document: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Saves a complete IDSSystemPipeline artifact to a directory."""
        from iot_ids.provenance.windows_access import require_real_data_authorization
        require_real_data_authorization(
            operation="write_checkpoint",
            target_path=save_dir,
            provider=authorization_provider,
            policy=policy_document,
        )
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save component joblibs
        joblib.dump(pipeline.model, save_dir / "model.joblib")
        joblib.dump(pipeline.preprocessor, save_dir / "preprocessor.joblib")

        if pipeline.aligner is not None:
            joblib.dump(pipeline.aligner, save_dir / "aligner.joblib")

        if pipeline.calibrator is not None:
            joblib.dump(pipeline.calibrator, save_dir / "calibrator.joblib")

        # Compute SHA-256 digests over saved components
        artifact_digests: Dict[str, str] = {
            "model.joblib": hashlib.sha256((save_dir / "model.joblib").read_bytes()).hexdigest(),
            "preprocessor.joblib": hashlib.sha256((save_dir / "preprocessor.joblib").read_bytes()).hexdigest(),
        }
        if pipeline.aligner is not None:
            artifact_digests["aligner.joblib"] = hashlib.sha256((save_dir / "aligner.joblib").read_bytes()).hexdigest()
        if pipeline.calibrator is not None:
            artifact_digests["calibrator.joblib"] = hashlib.sha256((save_dir / "calibrator.joblib").read_bytes()).hexdigest()

        # Save metadata configuration JSON
        meta_payload = {
            "feature_profile": pipeline.feature_profile,
            "feature_names": pipeline.feature_names,
            "decision_threshold": pipeline.decision_threshold,
            "has_aligner": pipeline.aligner is not None,
            "has_calibrator": pipeline.calibrator is not None,
            "artifact_digests": artifact_digests,
            "user_metadata": metadata or {},
        }

        with open(save_dir / "pipeline_metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta_payload, f, indent=2)

        return save_dir

    @staticmethod
    def load_pipeline(
        load_dir: Path,
        *,
        expected_digests: Optional[Dict[str, str]] = None,
        require_trusted_digests: bool = False,
        authorization_provider: Optional[Any] = None,
        policy_document: Optional[Dict[str, Any]] = None,
    ) -> IDSSystemPipeline:
        from iot_ids.provenance.windows_access import require_real_data_authorization
        require_real_data_authorization(
            operation="read_checkpoint",
            target_path=load_dir,
            provider=authorization_provider,
            policy=policy_document,
        )
        load_dir = Path(load_dir).resolve()
        """Loads an IDSSystemPipeline artifact from a saved directory with integrity verification."""
        if not load_dir.exists():
            raise FileNotFoundError(f"Pipeline artifact directory not found: {load_dir}")
        if not load_dir.is_dir():
            raise NotADirectoryError(f"Pipeline artifact path is not a directory: {load_dir}")

        meta_path = load_dir / "pipeline_metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Missing pipeline_metadata.json in artifact directory: {load_dir}")

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            raise ValueError(f"Corrupted or invalid pipeline_metadata.json in {load_dir}: {e}") from e

        if not isinstance(meta, dict):
            raise ValueError(f"Invalid pipeline_metadata.json: expected dict, got {type(meta).__name__}")

        model_path = load_dir / "model.joblib"
        preproc_path = load_dir / "preprocessor.joblib"

        if not model_path.exists():
            raise FileNotFoundError(f"Missing required model.joblib in artifact directory: {load_dir}")
        if not preproc_path.exists():
            raise FileNotFoundError(f"Missing required preprocessor.joblib in artifact directory: {load_dir}")

        # Determine effective digests
        manifest_digests = meta.get("artifact_digests")
        if expected_digests is not None:
            active_digests = expected_digests
        elif require_trusted_digests:
            raise ArtifactIntegrityError(
                f"Trusted digest verification required for '{load_dir}', but no external trusted "
                "expected_digests was provided. Digests in pipeline_metadata.json are co-located and unauthenticated."
            )
        elif isinstance(manifest_digests, dict):
            active_digests = manifest_digests
        else:
            active_digests = None

        if active_digests is not None:
            if "model.joblib" not in active_digests:
                raise ArtifactIntegrityError("Missing expected digest for 'model.joblib'")
            if "preprocessor.joblib" not in active_digests:
                raise ArtifactIntegrityError("Missing expected digest for 'preprocessor.joblib'")

            model = load_verified_joblib("model.joblib", expected_digest=active_digests["model.joblib"], base_dir=load_dir)
            preprocessor = load_verified_joblib("preprocessor.joblib", expected_digest=active_digests["preprocessor.joblib"], base_dir=load_dir)

            aligner_path = load_dir / "aligner.joblib"
            calib_path = load_dir / "calibrator.joblib"

            aligner = None
            if meta.get("has_aligner") and aligner_path.exists():
                if "aligner.joblib" not in active_digests:
                    raise ArtifactIntegrityError("Missing expected digest for 'aligner.joblib'")
                aligner = load_verified_joblib("aligner.joblib", expected_digest=active_digests["aligner.joblib"], base_dir=load_dir)

            calibrator = None
            if meta.get("has_calibrator") and calib_path.exists():
                if "calibrator.joblib" not in active_digests:
                    raise ArtifactIntegrityError("Missing expected digest for 'calibrator.joblib'")
                calibrator = load_verified_joblib("calibrator.joblib", expected_digest=active_digests["calibrator.joblib"], base_dir=load_dir)
        else:
            # Fallback path for unchecksummed legacy artifacts when require_trusted_digests=False
            model = joblib.load(model_path)
            preprocessor = joblib.load(preproc_path)

            aligner_path = load_dir / "aligner.joblib"
            calib_path = load_dir / "calibrator.joblib"

            aligner = joblib.load(aligner_path) if meta.get("has_aligner") and aligner_path.exists() else None
            calibrator = joblib.load(calib_path) if meta.get("has_calibrator") and calib_path.exists() else None

        pipeline = IDSSystemPipeline(
            model=model,
            preprocessor=preprocessor,
            feature_profile=meta.get("feature_profile", "full_multilevel"),
            feature_names=meta.get("feature_names"),
            aligner=aligner,
            calibrator=calibrator,
            decision_threshold=meta.get("decision_threshold", 0.5),
        )
        return pipeline
