"""Synthetic-only preflight lifecycle tests; no experiment runner is imported."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

import pytest

from iot_ids.provenance import (
    ArtifactEvidence,
    AuthorizationDecision,
    AuthorizationScope,
    AuthorizationStatus,
    EvidenceStatus,
    IntegrityStatus,
    PreflightReason,
    PreflightOperationBlocked,
    PreflightStatus,
    SchemaStatus,
    evaluate_preflight,
    execute_after_preflight,
)


_REPO_ROOT = Path(__file__).parents[2]
_TEST_ROOT = Path(__file__).parent
_EXAMPLES = _REPO_ROOT / "results" / "provenance" / "experiment_manifest_schema_examples.json"


class _SyntheticOnlyPolicy:
    """Test-local policy. This type is not provided by production package code."""

    def __init__(self, decision: object):
        self.decision = decision
        self.calls = 0

    def authorize(self, manifest: dict[str, Any]) -> object:
        # Deliberately independent of the manifest's authorization_reference.
        self.calls += 1
        return self.decision


def _manifest() -> dict[str, Any]:
    value = json.loads(_EXAMPLES.read_text(encoding="utf-8"))["positive"]
    value["experiment_id"] = "SYNTHETIC_PHASE_R_ONLY"
    value["metrics"][0].update(
        name="synthetic_arithmetic_fixture",
        definition="artificial test value; not IDS performance",
        value=0.375,
    )
    value["datasets"][0]["authorization_reference"] = "synthetic-placeholder-not-approval"
    return value


def _authorized_policy() -> _SyntheticOnlyPolicy:
    return _SyntheticOnlyPolicy(
        AuthorizationDecision(
            status=AuthorizationStatus.AUTHORIZED,
            scope=AuthorizationScope.SYNTHETIC_ONLY,
        )
    )


def _tree() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix=".synthetic-preflight-")


def test_valid_synthetic_manifest_and_artifact_allow_only_synthetic_operation() -> None:
    calls: list[str] = []
    with _tree() as temp:
        root = Path(temp)
        artifact = root / "synthetic-result.bin"
        artifact.write_bytes(b"phase R synthetic artifact; not a model or research output")
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        result, operation_result = execute_after_preflight(
            lambda: calls.append("SYNTHETIC_ONLY") or "synthetic-report-published",
            _manifest(),
            authorization_policy=_authorized_policy(),
            artifact_evidence=(ArtifactEvidence("synthetic-result.bin", "sha256", digest, str(root)),),
            require_artifacts=True,
        )
        assert result.status is PreflightStatus.READY_SYNTHETIC
        assert result.schema_status is SchemaStatus.VALID
        assert result.authorization_status is AuthorizationStatus.AUTHORIZED
        assert result.integrity_status is IntegrityStatus.VERIFIED
        assert result.evidence_status is EvidenceStatus.UNVERIFIED
        assert result.artifact_results[0].authorization_verified is False
        assert result.artifact_results[0].scientific_validity_verified is False
        assert operation_result == "synthetic-report-published"
    assert calls == ["SYNTHETIC_ONLY"]


@pytest.mark.parametrize(
    ("policy", "reason"),
    [
        (None, PreflightReason.AUTHORIZATION_MISSING),
        (_SyntheticOnlyPolicy(AuthorizationDecision(AuthorizationStatus.DENIED, AuthorizationScope.SYNTHETIC_ONLY)), PreflightReason.AUTHORIZATION_DENIED),
        (_SyntheticOnlyPolicy(AuthorizationDecision(AuthorizationStatus.INDETERMINATE, AuthorizationScope.SYNTHETIC_ONLY)), PreflightReason.AUTHORIZATION_INDETERMINATE),
        (_SyntheticOnlyPolicy(True), PreflightReason.AUTHORIZATION_MALFORMED),
        (_SyntheticOnlyPolicy(AuthorizationDecision(AuthorizationStatus.AUTHORIZED, AuthorizationScope.REAL_DATA)), PreflightReason.REAL_DATA_AUTHORIZATION_UNAVAILABLE),
    ],
)
def test_authorization_failures_never_call_synthetic_operation(policy, reason) -> None:
    calls: list[str] = []
    with pytest.raises(PreflightOperationBlocked) as blocked:
        execute_after_preflight(
            lambda: calls.append("MUST_NOT_RUN"), _manifest(), authorization_policy=policy
        )
    result = blocked.value.result
    assert result.status is PreflightStatus.BLOCKED
    assert reason in result.reason_codes
    assert calls == []


def test_invalid_manifest_blocks_before_authorization_or_operation() -> None:
    calls: list[str] = []
    manifest = _manifest()
    del manifest["datasets"][0]["split_id"]
    policy = _authorized_policy()
    with pytest.raises(PreflightOperationBlocked) as blocked:
        execute_after_preflight(
            lambda: calls.append("MUST_NOT_RUN"), manifest, authorization_policy=policy
        )
    result = blocked.value.result
    assert result.status is PreflightStatus.BLOCKED
    assert result.schema_status is SchemaStatus.INVALID
    assert result.authorization_status is AuthorizationStatus.NOT_CHECKED
    assert result.integrity_status is IntegrityStatus.NOT_CHECKED
    assert result.reason_codes == (PreflightReason.SCHEMA_INVALID,)
    assert policy.calls == 0
    assert calls == []


def test_policy_exception_becomes_non_sensitive_indeterminate_result() -> None:
    class RaisingPolicy:
        def authorize(self, manifest: dict[str, Any]) -> object:
            raise RuntimeError("synthetic secret path C:\\private\\token")

    result = evaluate_preflight(_manifest(), authorization_policy=RaisingPolicy())
    assert result.status is PreflightStatus.BLOCKED
    assert result.authorization_status is AuthorizationStatus.INDETERMINATE
    assert result.reason_codes == (PreflightReason.AUTHORIZATION_INDETERMINATE,)
    assert "private" not in repr(result)
    assert "token" not in repr(result)


def test_required_artifact_evidence_missing_blocks_operation() -> None:
    calls: list[str] = []
    with pytest.raises(PreflightOperationBlocked) as blocked:
        execute_after_preflight(
            lambda: calls.append("MUST_NOT_RUN"),
            _manifest(), authorization_policy=_authorized_policy(), require_artifacts=True,
        )
    result = blocked.value.result
    assert result.status is PreflightStatus.BLOCKED
    assert result.integrity_status is IntegrityStatus.FAILED
    assert PreflightReason.REQUIRED_ARTIFACT_EVIDENCE_MISSING in result.reason_codes
    assert calls == []


def test_digest_mismatch_and_invalid_declaration_block_operation() -> None:
    calls: list[str] = []
    with _tree() as temp:
        root = Path(temp)
        (root / "result.bin").write_bytes(b"synthetic bytes")
        with pytest.raises(PreflightOperationBlocked) as mismatch_block:
            execute_after_preflight(
                lambda: calls.append("MUST_NOT_RUN"),
                _manifest(),
                authorization_policy=_authorized_policy(),
                artifact_evidence=(ArtifactEvidence("result.bin", "sha256", "0" * 64, str(root)),),
                require_artifacts=True,
            )
        with pytest.raises(PreflightOperationBlocked) as invalid_block:
            execute_after_preflight(
                lambda: calls.append("MUST_NOT_RUN"),
                _manifest(),
                authorization_policy=_authorized_policy(),
                artifact_evidence=(ArtifactEvidence("result.bin", "md5", "0" * 32, str(root)),),
                require_artifacts=True,
            )
        mismatch = mismatch_block.value.result
        invalid = invalid_block.value.result
    for result, reason in (
        (mismatch, PreflightReason.ARTIFACT_MISMATCH),
        (invalid, PreflightReason.ARTIFACT_DECLARATION_INVALID),
    ):
        assert result.status is PreflightStatus.BLOCKED
        assert reason in result.reason_codes
        assert result.schema_status is SchemaStatus.VALID
        assert result.authorization_status is AuthorizationStatus.AUTHORIZED
        assert result.integrity_status is IntegrityStatus.FAILED
    assert calls == []


def test_artifact_path_escape_blocks_operation() -> None:
    calls: list[str] = []
    with _tree() as temp:
        root = Path(temp)
        with pytest.raises(PreflightOperationBlocked) as blocked:
            execute_after_preflight(
                lambda: calls.append("MUST_NOT_RUN"),
                _manifest(),
                authorization_policy=_authorized_policy(),
                artifact_evidence=(ArtifactEvidence("../escape.bin", "sha256", "0" * 64, str(root)),),
                require_artifacts=True,
            )
    result = blocked.value.result
    assert result.status is PreflightStatus.BLOCKED
    assert PreflightReason.ARTIFACT_DECLARATION_INVALID in result.reason_codes
    assert calls == []


def test_schema_and_authorization_are_separate_from_integrity() -> None:
    result = evaluate_preflight(_manifest(), authorization_policy=_authorized_policy())
    assert result.status is PreflightStatus.READY_SYNTHETIC
    assert result.schema_status is SchemaStatus.VALID
    assert result.authorization_status is AuthorizationStatus.AUTHORIZED
    assert result.integrity_status is IntegrityStatus.NOT_REQUIRED
    assert result.evidence_status is EvidenceStatus.UNVERIFIED
    assert result.artifact_results == ()


def test_synthetic_operation_failure_propagates_without_success_result() -> None:
    def failed_operation():
        raise RuntimeError("synthetic report publication failure")

    with pytest.raises(RuntimeError, match="synthetic report publication failure"):
        execute_after_preflight(
            failed_operation, _manifest(), authorization_policy=_authorized_policy()
        )
