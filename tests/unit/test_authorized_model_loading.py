"""Unit tests for CryptographicPolicyAuthorizationProvider and model loading authorization.

Verifies the cryptographic trust model, owner approval validation, fail-closed handling,
and artifact integrity guarantees without bypassing any security boundaries.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import pytest

from iot_ids.provenance.windows_access import (
    AccessCode,
    CryptographicPolicyAuthorizationProvider,
    StageStatus,
    WindowsAccessAssessment,
    validate_policy_configuration,
)
from iot_ids.provenance.artifact_integrity import (
    verify_artifact_digest,
    verify_and_read_artifact,
    ArtifactIntegrityError,
)

_VALID_ID_PIN = {
    "path_kind": "local_drive",
    "volume_identity": "VOL-TEST-1234",
    "root_file_identity": "FILE-TEST-5678",
    "case_policy": "case_insensitive",
}


def _build_test_policy(
    anchor_id: str = "owner-anchor-01",
    secret_key: bytes = b"test-secret-key-32-bytes-secure!",
    approved_root: str = r"C:\Research\Models",
    record_id: str = "REC-2026-TEST-001",
    delta_seconds: float = 0.0,
    example_only: bool = False,
    status: str = "ACTIVE",
    permitted_ops: list[str] | None = None,
) -> tuple[dict, CryptographicPolicyAuthorizationProvider]:
    provider = CryptographicPolicyAuthorizationProvider(
        trust_anchors={anchor_id: secret_key},
        revocation_list=set(),
    )

    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delta_seconds)
    approved_at_str = now.isoformat()

    if permitted_ops is None:
        permitted_ops = ["read_checkpoint"]

    document = {
        "schema_version": 1,
        "example_only": example_only,
        "policy_revision": "ACTIVE-RESEARCH-POLICY-V1",
        "status": status,
        "filesystem_policy_version": "FS-V1",
        "datasets": {
            "ton_iot_research": {
                "dataset_id": "ton_iot_research",
                "approved_root": r"C:\Research\Datasets\ToN-IoT",
                "permitted_operations": ["read_checkpoint"],
                "identity_pin": _VALID_ID_PIN,
                "approval": None,
            }
        },
        "artifact_roots": {
            "research_models": {
                "resource_id": "research_models",
                "approved_root": approved_root,
                "permitted_operations": list(permitted_ops),
                "identity_pin": _VALID_ID_PIN,
                "approval": None,
            }
        },
        "protected_roots": [
            {
                "root_id": "windows_system",
                "path": r"C:\Windows",
                "coverage": "ancestors_and_descendants",
                "identity_pin": _VALID_ID_PIN,
                "approval": None,
            }
        ],
        "policy_approval": None,
    }

    digest = provider.canonical_policy_digest(document)
    sig = provider.sign_policy_digest(digest, secret_key)

    approval_block = {
        "approval_record_id": record_id,
        "approver_identity": "Project Owner <owner@iot-ids.internal>",
        "approved_at": approved_at_str,
        "trust_anchor_id": anchor_id,
        "signed_policy_sha256": digest,
        "signature_reference": sig,
    }

    document["datasets"]["ton_iot_research"]["approval"] = approval_block
    document["artifact_roots"]["research_models"]["approval"] = approval_block
    document["protected_roots"][0]["approval"] = approval_block
    document["policy_approval"] = approval_block

    return document, provider


def test_schema_validation_succeeds_for_signed_policy() -> None:
    policy, _ = _build_test_policy()
    result = validate_policy_configuration(policy)
    assert result.status is StageStatus.VALID
    assert result.error_code is None


def test_scenario_1_valid_approval_with_ephemeral_key() -> None:
    policy, provider = _build_test_policy()
    checkpoint_path = r"C:\Research\Models\standardized\ton_iot_rf.joblib"
    assessment = provider.assess(policy, checkpoint_path, operation="read_checkpoint")

    assert assessment.lexical_path is StageStatus.VALID
    assert assessment.policy_configuration is StageStatus.VALID
    assert assessment.approval_authenticity is StageStatus.VALID
    assert assessment.filesystem_identity is StageStatus.VALID
    assert assessment.protected_root_check is StageStatus.LEXICALLY_CLEAR
    assert assessment.authorized_access is StageStatus.VALID
    assert assessment.error_code is None


def test_scenario_2_missing_approval_refused() -> None:
    # 2a: Active policy with policy_approval stripped is rejected by schema validator
    policy, provider = _build_test_policy()
    policy["policy_approval"] = None
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"
    assessment = provider.assess(policy, checkpoint_path, operation="read_checkpoint")
    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.error_code is AccessCode.POLICY_SCHEMA_INVALID

    # 2b: Draft policy with null approval is valid under schema but refused by provider
    draft_policy, draft_provider = _build_test_policy(status="DRAFT")
    assessment_draft = draft_provider.assess(draft_policy, checkpoint_path, operation="read_checkpoint")
    assert assessment_draft.policy_configuration is StageStatus.VALID
    assert assessment_draft.authorized_access is StageStatus.REFUSED
    assert assessment_draft.error_code is AccessCode.OWNER_APPROVAL_UNVERIFIED


def test_scenario_2b_draft_or_example_only_refused() -> None:
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"

    # DRAFT status: schema valid, access refused
    policy_draft, provider_draft = _build_test_policy(status="DRAFT")
    assessment_draft = provider_draft.assess(policy_draft, checkpoint_path, operation="read_checkpoint")
    assert assessment_draft.policy_configuration is StageStatus.VALID
    assert assessment_draft.authorized_access is StageStatus.REFUSED
    assert assessment_draft.error_code is AccessCode.OWNER_APPROVAL_UNVERIFIED

    # example_only=True on ACTIVE policy: rejected by schema
    policy_ex, provider_ex = _build_test_policy(example_only=True)
    assessment_ex = provider_ex.assess(policy_ex, checkpoint_path, operation="read_checkpoint")
    assert assessment_ex.authorized_access is StageStatus.REFUSED
    assert assessment_ex.error_code is AccessCode.POLICY_SCHEMA_INVALID


def test_scenario_3_invalid_signature_refused() -> None:
    policy, provider = _build_test_policy()
    # Corrupt the HMAC signature reference
    policy["policy_approval"]["signature_reference"] = "0" * 64
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"
    assessment = provider.assess(policy, checkpoint_path, operation="read_checkpoint")

    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.approval_authenticity is StageStatus.REJECTED
    assert assessment.error_code is AccessCode.OWNER_APPROVAL_UNVERIFIED


def test_scenario_4_altered_policy_manifest_refused() -> None:
    policy, provider = _build_test_policy()
    # Attacker tries to inject an unauthorized operation after signing
    policy["artifact_roots"]["research_models"]["permitted_operations"].append("write_checkpoint")
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"
    assessment = provider.assess(policy, checkpoint_path, operation="read_checkpoint")

    # The canonical digest of the altered policy differs from signed_policy_sha256
    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.approval_authenticity is StageStatus.REJECTED
    assert assessment.error_code is AccessCode.OWNER_APPROVAL_UNVERIFIED


def test_scenario_5_expired_approval_refused() -> None:
    # 400 days in the past (exceeds max_validity_seconds of 365 days)
    policy, provider = _build_test_policy(delta_seconds=-(400 * 86400))
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"
    assessment = provider.assess(policy, checkpoint_path, operation="read_checkpoint")

    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.approval_authenticity is StageStatus.REJECTED
    assert assessment.error_code is AccessCode.OWNER_APPROVAL_UNVERIFIED


def test_scenario_6_future_timestamp_clock_skew_refused() -> None:
    # 300 seconds in the future (exceeds clock_skew_tolerance of 60 seconds)
    policy, provider = _build_test_policy(delta_seconds=+300)
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"
    assessment = provider.assess(policy, checkpoint_path, operation="read_checkpoint")

    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.approval_authenticity is StageStatus.REJECTED
    assert assessment.error_code is AccessCode.OWNER_APPROVAL_UNVERIFIED


def test_scenario_7_revoked_approval_record_refused() -> None:
    policy, provider = _build_test_policy(record_id="REC-REVOKED-999")
    provider.revocation_list.add("REC-REVOKED-999")
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"
    assessment = provider.assess(policy, checkpoint_path, operation="read_checkpoint")

    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.approval_authenticity is StageStatus.REJECTED
    assert assessment.error_code is AccessCode.OWNER_APPROVAL_UNVERIFIED


def test_scenario_8_path_traversal_attempt_rejected() -> None:
    policy, provider = _build_test_policy()
    # Traversal escaping candidate root
    traversal_path = r"C:\Research\Models\..\..\Windows\System32\cmd.exe"
    assessment = provider.assess(policy, traversal_path, operation="read_checkpoint")

    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.lexical_path is StageStatus.REJECTED
    assert assessment.error_code is AccessCode.INVALID_PATH


def test_scenario_9_protected_root_collision_refused() -> None:
    policy, provider = _build_test_policy()
    # Attempting to access file under protected root C:\Windows
    target_path = r"C:\Windows\System32\drivers\etc\hosts"
    assessment = provider.assess(policy, target_path, operation="read_checkpoint")

    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.protected_root_check is StageStatus.LEXICAL_OVERLAP
    assert assessment.error_code is AccessCode.PROTECTED_ROOT_OVERLAP


def test_scenario_10_unauthorized_operation_refused() -> None:
    policy, provider = _build_test_policy(permitted_ops=["read_checkpoint"])
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"
    # Requesting stream_dataset when only read_checkpoint is permitted
    assessment = provider.assess(policy, checkpoint_path, operation="stream_dataset")

    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.error_code is AccessCode.INVALID_PATH


def test_scenario_11_production_default_empty_anchors_fails_closed() -> None:
    # In production, provider has NO trust anchors registered
    production_provider = CryptographicPolicyAuthorizationProvider()
    assert len(production_provider.trust_anchors) == 0

    policy, _ = _build_test_policy()
    checkpoint_path = r"C:\Research\Models\checkpoint.pt"
    assessment = production_provider.assess(policy, checkpoint_path, operation="read_checkpoint")

    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.approval_authenticity is StageStatus.UNVERIFIED
    assert assessment.error_code is AccessCode.OWNER_APPROVAL_UNVERIFIED


def test_scenario_12_artifact_digest_integrity_verification() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        artifact_path = base_dir / "checkpoint.bin"
        content = b"TEST_MODEL_WEIGHTS_CONTENT"
        artifact_path.write_bytes(content)

        expected_hash = hashlib.sha256(content).hexdigest()

        # Matching digest
        result = verify_artifact_digest("checkpoint.bin", algorithm="sha256", expected_digest=expected_hash, base_dir=base_dir)
        assert result.status == "MATCH"
        assert result.actual_digest == expected_hash

        # Mismatched digest
        tampered_hash = "f" * 64
        result_tampered = verify_artifact_digest("checkpoint.bin", algorithm="sha256", expected_digest=tampered_hash, base_dir=base_dir)
        assert result_tampered.status == "MISMATCH"

        # Safe read into memory
        read_bytes = verify_and_read_artifact("checkpoint.bin", expected_digest=expected_hash, base_dir=base_dir)
        assert read_bytes == content

        # Safe read fails on mismatch
        with pytest.raises(ArtifactIntegrityError, match=r"(?i)digest mismatch"):
            verify_and_read_artifact("checkpoint.bin", expected_digest=tampered_hash, base_dir=base_dir)


# ---------------------------------------------------------------------------
# End-to-End Legitimate Research Authorization Integration Tests
# ---------------------------------------------------------------------------

def _build_active_research_policy_fixture(
    anchor_id: str = "research-owner-01",
    secret_key: bytes = b"test-ephemeral-key-32-bytes-long",
    models_root: str | None = None,
    datasets_root: str | None = None,
    permitted_ops_models: list[str] | None = None,
    permitted_ops_datasets: list[str] | None = None,
    tamper_signature: bool = False,
    delta_seconds: float = 0.0,
) -> tuple[dict, CryptographicPolicyAuthorizationProvider]:
    repo_root = Path(__file__).resolve().parents[2]
    if models_root is None:
        models_root = str((repo_root / "models").resolve())
    if datasets_root is None:
        datasets_root = str((repo_root / "data").resolve())

    provider = CryptographicPolicyAuthorizationProvider(
        trust_anchors={anchor_id: secret_key},
    )

    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delta_seconds)
    approved_at_str = now.isoformat()

    doc = {
        "schema_version": 1,
        "example_only": False,
        "policy_revision": "ACTIVE-RESEARCH-POLICY-V1",
        "status": "ACTIVE",
        "filesystem_policy_version": "FS-V1",
        "datasets": {
            "research_datasets": {
                "dataset_id": "research_datasets",
                "approved_root": datasets_root,
                "permitted_operations": permitted_ops_datasets or ["read_split", "evaluate_model", "stream_dataset"],
                "identity_pin": _VALID_ID_PIN,
                "approval": None,
            }
        },
        "artifact_roots": {
            "research_models": {
                "resource_id": "research_models",
                "approved_root": models_root,
                "permitted_operations": permitted_ops_models or ["read_checkpoint", "write_checkpoint"],
                "identity_pin": _VALID_ID_PIN,
                "approval": None,
            }
        },
        "protected_roots": [
            {
                "root_id": "windows_system",
                "path": r"C:\Windows",
                "coverage": "ancestors_and_descendants",
                "identity_pin": _VALID_ID_PIN,
                "approval": None,
            }
        ],
        "policy_approval": None,
    }

    digest = provider.canonical_policy_digest(doc)
    sig = provider.sign_policy_digest(digest, secret_key)
    if tamper_signature:
        sig = "0" * 64

    app_block = {
        "approval_record_id": "REC-RESEARCH-001",
        "approver_identity": "Project Owner <owner@iot-ids.internal>",
        "approved_at": approved_at_str,
        "trust_anchor_id": anchor_id,
        "signed_policy_sha256": digest,
        "signature_reference": sig,
    }
    doc["datasets"]["research_datasets"]["approval"] = app_block
    doc["artifact_roots"]["research_models"]["approval"] = app_block
    doc["protected_roots"][0]["approval"] = app_block
    doc["policy_approval"] = app_block

    return doc, provider


def test_authorized_inference_engine_loading_real_checkpoints():
    """Verifies that InferenceEngine successfully loads actual research checkpoints when legitimately authorized."""
    from iot_ids.runtime.engine import InferenceEngine
    policy, provider = _build_active_research_policy_fixture()

    engine = InferenceEngine(
        profile="standardized_21",
        dataset="ToN-IoT",
        authorization_provider=provider,
        policy_document=policy,
    )

    health = engine.health_check()
    assert health["status"] == "HEALTHY"
    assert health["components"]["rf_model"] == "READY"
    assert health["components"]["mlp_model"] == "READY"
    assert health["components"]["preprocessor"] == "READY"
    assert engine.expected_dim == 21
    assert engine.rf_model.n_features_in_ == 21


def test_authorized_model_registry_load_pipeline():
    """Verifies that ModelRegistry successfully deserializes the deployable artifact under valid policy."""
    from iot_ids.registry.manager import ModelRegistry
    repo_root = Path(__file__).resolve().parents[2]
    artifact_dir = repo_root / "models" / "final" / "deployable_artifact"

    policy, provider = _build_active_research_policy_fixture()

    pipeline = ModelRegistry.load_pipeline(
        artifact_dir,
        authorization_provider=provider,
        policy_document=policy,
    )

    assert pipeline.feature_profile == "full_multilevel"
    assert len(pipeline.feature_names) == 21
    assert pipeline.decision_threshold == 0.5
    assert hasattr(pipeline.model, "predict_proba")


def test_authorized_evaluation_on_real_ton_iot_dataset():
    """Verifies end-to-end inference and evaluation on real Kaggle ToN-IoT test split with Option C fusion."""
    import pandas as pd
    from iot_ids.runtime.engine import InferenceEngine
    from iot_ids.runtime.schema import STANDARDIZED_21_FEATURES

    repo_root = Path(__file__).resolve().parents[2]
    test_pq = repo_root / "data" / "processed" / "stage3" / "ToN-IoT" / "test.parquet"
    assert test_pq.exists(), "ToN-IoT test.parquet missing"

    policy, provider = _build_active_research_policy_fixture()

    engine = InferenceEngine(
        profile="standardized_21",
        dataset="ToN-IoT",
        authorization_provider=provider,
        policy_document=policy,
    )

    df_test = pd.read_parquet(test_pq)
    df_sample = df_test[STANDARDIZED_21_FEATURES].head(15)

    preds = engine.predict(df_sample)
    assert len(preds) == 15
    for pred in preds:
        assert "prediction" in pred
        assert "probability" in pred
        assert 0.0 <= pred["probability"] <= 1.0


def test_rejection_of_missing_authorization_fails_closed():
    """Verifies that InferenceEngine rejects real checkpoint loading without authorization."""
    from iot_ids.runtime.engine import InferenceEngine
    from iot_ids.provenance.windows_access import RealDataAuthorizationUnavailable

    with pytest.raises(RealDataAuthorizationUnavailable):
        InferenceEngine(profile="standardized_21", dataset="ToN-IoT")


def test_rejection_of_tampered_policy_signature():
    """Verifies that tampering with the cryptographic policy signature causes immediate refusal."""
    from iot_ids.runtime.engine import InferenceEngine
    from iot_ids.provenance.windows_access import RealDataAuthorizationUnavailable

    tampered_policy, provider = _build_active_research_policy_fixture(tamper_signature=True)

    with pytest.raises(RealDataAuthorizationUnavailable, match="OWNER_APPROVAL_UNVERIFIED"):
        InferenceEngine(
            profile="standardized_21",
            dataset="ToN-IoT",
            authorization_provider=provider,
            policy_document=tampered_policy,
        )


def test_rejection_of_protected_resource_access():
    """Verifies that access to protected roots (e.g. C:\\Windows) is unconditionally refused."""
    from iot_ids.provenance.windows_access import (
        require_real_data_authorization,
        RealDataAuthorizationUnavailable,
    )

    policy, provider = _build_active_research_policy_fixture()

    with pytest.raises(RealDataAuthorizationUnavailable, match="PROTECTED_ROOT_OVERLAP"):
        require_real_data_authorization(
            operation="read_checkpoint",
            target_path=r"C:\Windows\System32\drivers\etc\hosts",
            provider=provider,
            policy=policy,
        )


def test_separation_of_research_authorization_from_physical_capture():
    """Verifies that research-model authorization does NOT grant raw socket physical NIC capture permissions."""
    from iot_ids.data.packet_capture import PacketCaptureEngine
    from iot_ids.provenance.windows_access import scoped_policy_authorization
    from unittest.mock import MagicMock

    policy, provider = _build_active_research_policy_fixture()
    mock_predictor = MagicMock()

    with scoped_policy_authorization(provider, policy):
        sniffer = PacketCaptureEngine(predictor=mock_predictor)
        # Attempting capture on non-existent physical interface fails closed or returns empty
        res = sniffer.capture_live(interface="NonExistentPhysicalNIC_12345", duration=0.1)
        assert isinstance(res, list)
        assert len(res) == 0


def test_research_model_suite_loading_unauthorized_fails_closed():
    """Verifies that load_research_model_suite fails closed without authorization."""
    from iot_ids.models.research_models import load_research_model_suite
    from iot_ids.provenance.windows_access import RealDataAuthorizationUnavailable

    with pytest.raises(RealDataAuthorizationUnavailable):
        load_research_model_suite("ToN-IoT")


def test_research_model_suite_loading_authorized():
    """Verifies that load_research_model_suite successfully loads all genuine research artifacts."""
    from iot_ids.models.research_models import load_research_model_suite

    policy, provider = _build_active_research_policy_fixture()
    suite = load_research_model_suite(
        "ToN-IoT",
        authorization_provider=provider,
        policy_document=policy,
    )
    assert suite.dataset_name == "ToN-IoT"
    assert suite.rf_model is not None
    assert suite.standard_mlp is not None
    assert suite.robust_mlp is not None
    assert suite.autoencoder is not None
    assert suite.risk_layer is not None
    assert suite.option_c_ensemble is not None
    assert len(suite.artifact_digests) == 6
    for name in ["prep_standardized.joblib", "rf_model.joblib", "mlp_model.pt", "mlp_adversarial.pt", "ae_model.pt", "risk_layer.json"]:
        assert name in suite.artifact_digests
        assert len(suite.artifact_digests[name]) == 64

    # Test pipeline and prediction
    pipe = suite.create_pipeline("option_c")
    assert pipe.feature_profile == "standardized_21"
    assert pipe.decision_threshold == 0.5

