"""Adversarial and functional unit tests for secure model artifact deserialization."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import tempfile
from unittest.mock import patch

import joblib
import pytest
from sklearn.ensemble import RandomForestClassifier

from iot_ids.provenance.artifact_integrity import (
    ArtifactIntegrityError,
    load_verified_joblib,
    verify_and_read_artifact,
)
from iot_ids.registry.manager import ModelRegistry


class DummyPreprocessor:
    def __init__(self, names: list[str]):
        self.feature_names = names

    def transform(self, X):
        return X


@pytest.fixture
def temp_artifact_env():
    with tempfile.TemporaryDirectory(prefix="ids-secure-artifact-test-") as tmp:
        base = Path(tmp).resolve()
        rf = RandomForestClassifier(n_estimators=2, random_state=42)
        rf.fit([[0.1, 0.2], [0.3, 0.4]], [0, 1])

        rf_path = base / "rf_model.joblib"
        joblib.dump(rf, rf_path)

        prep = DummyPreprocessor(["f1", "f2"])
        prep_path = base / "preprocessor.joblib"
        joblib.dump(prep, prep_path)

        rf_bytes = rf_path.read_bytes()
        rf_digest = hashlib.sha256(rf_bytes).hexdigest()

        prep_bytes = prep_path.read_bytes()
        prep_digest = hashlib.sha256(prep_bytes).hexdigest()

        yield {
            "base": base,
            "rf_path": rf_path,
            "rf_digest": rf_digest,
            "prep_path": prep_path,
            "prep_digest": prep_digest,
        }


def test_valid_artifact_loads_with_matching_digest(temp_artifact_env):
    base = temp_artifact_env["base"]
    digest = temp_artifact_env["rf_digest"]

    loaded_rf = load_verified_joblib(
        "rf_model.joblib", expected_digest=digest, base_dir=base
    )
    assert hasattr(loaded_rf, "predict_proba")
    assert callable(loaded_rf.predict_proba)


def test_modified_artifact_rejected_before_deserializer_called(temp_artifact_env):
    base = temp_artifact_env["base"]
    rf_path = temp_artifact_env["rf_path"]
    expected_digest = temp_artifact_env["rf_digest"]

    # Tamper with the artifact content on disk
    rf_path.write_bytes(b"TAMPERED_MALICIOUS_BYTES_NOT_JOBLIB")

    with patch("joblib.load") as mock_load:
        with pytest.raises(ArtifactIntegrityError, match="Digest mismatch"):
            load_verified_joblib(
                "rf_model.joblib", expected_digest=expected_digest, base_dir=base
            )
        # Deserializer MUST NEVER have been called on tampered file
        mock_load.assert_not_called()


def test_malformed_and_unsupported_digest_declarations(temp_artifact_env):
    base = temp_artifact_env["base"]

    # Not 64 hex characters
    with pytest.raises(ArtifactIntegrityError, match="malformed"):
        load_verified_joblib(
            "rf_model.joblib", expected_digest="not-a-valid-sha256", base_dir=base
        )

    # Wrong length
    with pytest.raises(ArtifactIntegrityError, match="malformed"):
        load_verified_joblib(
            "rf_model.joblib", expected_digest="a" * 63, base_dir=base
        )

    with pytest.raises(ArtifactIntegrityError, match="unsupported"):
        verify_and_read_artifact(
            "rf_model.joblib",
            expected_digest="a" * 32,
            base_dir=base,
            algorithm="md5",
        )


def test_missing_artifact_handled_cleanly(temp_artifact_env):
    base = temp_artifact_env["base"]
    dummy_digest = "0" * 64

    with pytest.raises(ArtifactIntegrityError, match="missing"):
        load_verified_joblib(
            "nonexistent_artifact.joblib", expected_digest=dummy_digest, base_dir=base
        )


def test_path_traversal_in_manifest_rejected_without_reading(temp_artifact_env):
    base = temp_artifact_env["base"]
    dummy_digest = "0" * 64

    with pytest.raises(ArtifactIntegrityError, match="escapes"):
        load_verified_joblib(
            "../../escape.joblib", expected_digest=dummy_digest, base_dir=base
        )


def test_toctou_file_swapping_prevented_by_memory_buffer(temp_artifact_env):
    base = temp_artifact_env["base"]
    rf_path = temp_artifact_env["rf_path"]
    expected_digest = temp_artifact_env["rf_digest"]

    # Verify and read into memory
    verified_bytes = verify_and_read_artifact(
        "rf_model.joblib", expected_digest=expected_digest, base_dir=base
    )

    # Immediately tamper with disk file
    rf_path.write_bytes(b"OVERWRITTEN_AFTER_VERIFICATION")

    # Deserializing from the verified in-memory buffer succeeds safely
    loaded = joblib.load(io.BytesIO(verified_bytes))
    assert hasattr(loaded, "predict_proba")


def test_error_message_does_not_leak_absolute_filesystem_path(temp_artifact_env):
    base = temp_artifact_env["base"]
    wrong_digest = "f" * 64

    try:
        load_verified_joblib(
            "rf_model.joblib", expected_digest=wrong_digest, base_dir=base
        )
    except ArtifactIntegrityError as exc:
        msg = str(exc)
        # Should reference the file basename, not full absolute base path
        assert "rf_model.joblib" in msg
        assert str(base) not in msg


def test_model_registry_load_pipeline_refuses_without_authorization(temp_artifact_env):
    from iot_ids.provenance.windows_access import RealDataAuthorizationUnavailable
    base = temp_artifact_env["base"]
    with pytest.raises(RealDataAuthorizationUnavailable):
        ModelRegistry.load_pipeline(base, require_trusted_digests=True)
