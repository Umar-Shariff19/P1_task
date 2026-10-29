"""Synthetic-only tests for lexical dataset-root authorization."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

import pytest

from iot_ids.data.path_policy import (
    DatasetAccessPolicy,
    DatasetRootRejected,
    RootIdentityEvidence,
    authorize_dataset_root,
)


@pytest.fixture
def synthetic_root() -> Iterator[Path]:
    """Create and remove one synthetic tree."""
    with TemporaryDirectory(prefix=".synthetic-path-policy-") as temp_dir:
        yield Path(temp_dir)


def _policy(approved: Path, protected: Path, verifier=None) -> DatasetAccessPolicy:
    def synthetic_verifier(supplied: str, configured: str) -> RootIdentityEvidence:
        return RootIdentityEvidence(
            canonical_path=configured,
            volume_identity="synthetic-volume",
            root_file_identity="synthetic-root-id",
            reparse_points_checked=True,
            case_semantics_checked=True,
        )

    return DatasetAccessPolicy(
        approved_roots={"synthetic": str(approved)},
        protected_roots=(str(protected),),
        identity_verifier=verifier or synthetic_verifier,
    )


def test_missing_policy_and_dataset_authorization_fail_closed(synthetic_root: Path) -> None:
    with pytest.raises(DatasetRootRejected, match="policy is required"):
        authorize_dataset_root("synthetic", str(synthetic_root), None)

    policy = _policy(synthetic_root / "approved", synthetic_root / "protected")
    with pytest.raises(DatasetRootRejected, match="dataset ID"):
        authorize_dataset_root("unknown", str(synthetic_root / "approved"), policy)
    with pytest.raises(DatasetRootRejected, match="dataset ID must"):
        authorize_dataset_root([], str(synthetic_root / "approved"), policy)  # type: ignore[arg-type]

    incomplete = DatasetAccessPolicy({}, (str(synthetic_root / "protected"),), policy.identity_verifier)
    with pytest.raises(DatasetRootRejected, match="approved-root policy"):
        authorize_dataset_root("synthetic", str(synthetic_root / "approved"), incomplete)


def test_ambiguous_approved_root_configuration_is_rejected(synthetic_root: Path) -> None:
    parent = synthetic_root / "dataset"
    child = parent / "nested"
    protected = synthetic_root / "protected"
    policy = DatasetAccessPolicy(
        approved_roots={"one": str(parent), "two": str(child)},
        protected_roots=(str(protected),),
        identity_verifier=_policy(parent, protected).identity_verifier,
    )
    with pytest.raises(DatasetRootRejected, match="overlap"):
        authorize_dataset_root("one", str(parent), policy)

    volume_policy = DatasetAccessPolicy(
        approved_roots={"synthetic": "C:\\"},
        protected_roots=("D:\\Protected",),
        identity_verifier=_policy(parent, protected).identity_verifier,
    )
    with pytest.raises(DatasetRootRejected, match="volume root"):
        authorize_dataset_root("synthetic", "C:\\", volume_policy)


def test_exact_synthetic_root_is_accepted(synthetic_root: Path) -> None:
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    approved.mkdir()
    protected.mkdir()
    result = authorize_dataset_root("synthetic", str(approved), _policy(approved, protected))
    assert result.dataset_id == "synthetic"
    assert str(result.path) == str(approved)


def test_drive_letter_case_is_normalized_but_component_case_alias_is_rejected(
    synthetic_root: Path,
) -> None:
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    approved.mkdir()
    protected.mkdir()
    approved_text = str(approved)
    drive_variant = approved_text[0].lower() + approved_text[1:]
    result = authorize_dataset_root("synthetic", drive_variant, _policy(approved, protected))
    assert str(result.path) == approved_text

    component_variant = str(approved.parent / "APPROVED")
    with pytest.raises(DatasetRootRejected, match="exact authorized root"):
        authorize_dataset_root(
            "synthetic", component_variant, _policy(approved, protected)
        )


def test_dot_component_normalizes_without_filesystem_resolution(synthetic_root: Path) -> None:
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    approved.mkdir()
    protected.mkdir()
    dotted = f"{approved.parent}\\.\\{approved.name}"
    result = authorize_dataset_root("synthetic", dotted, _policy(approved, protected))
    assert str(result.path) == str(approved)


@pytest.mark.parametrize("candidate_kind", ["outside", "protected", "protected_child", "ancestor"])
def test_unapproved_and_protected_roots_fail_before_discovery(
    synthetic_root: Path, candidate_kind: str
) -> None:
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    outside = synthetic_root / "outside"
    for path in (approved, protected, outside):
        path.mkdir()
    candidates = {
        "outside": outside,
        "protected": protected,
        "protected_child": protected / "child",
        "ancestor": synthetic_root,
    }
    discovery_called = False

    def discover(root: Path) -> list[Path]:
        nonlocal discovery_called
        discovery_called = True
        return list(root.rglob("*"))

    with pytest.raises(DatasetRootRejected):
        authorized = authorize_dataset_root(
            "synthetic", str(candidates[candidate_kind]), _policy(approved, protected)
        )
        discover(Path(str(authorized.path)))
    assert not discovery_called


@pytest.mark.parametrize("candidate", ["relative", "..\\escape"])
def test_relative_and_parent_traversal_paths_rejected(
    synthetic_root: Path, candidate: str
) -> None:
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    with pytest.raises(DatasetRootRejected):
        authorize_dataset_root("synthetic", candidate, _policy(approved, protected))


def test_absolute_parent_traversal_is_rejected(synthetic_root: Path) -> None:
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    escaped = f"{approved}\\..\\outside"
    with pytest.raises(DatasetRootRejected, match="parent traversal"):
        authorize_dataset_root("synthetic", escaped, _policy(approved, protected))


def test_identity_verifier_absence_or_ambiguity_fails_closed(synthetic_root: Path) -> None:
    approved, protected = synthetic_root / "approved", synthetic_root / "protected"
    with pytest.raises(DatasetRootRejected, match="verifier is not configured"):
        authorize_dataset_root(
            "synthetic",
            str(approved),
            DatasetAccessPolicy({"synthetic": str(approved)}, (str(protected),), None),
        )

    policy = _policy(approved, protected, verifier=lambda supplied, configured: None)
    with pytest.raises(DatasetRootRejected, match="ambiguous"):
        authorize_dataset_root("synthetic", str(approved), policy)

    bool_policy = _policy(approved, protected, verifier=lambda supplied, configured: True)
    with pytest.raises(DatasetRootRejected, match="ambiguous"):
        authorize_dataset_root("synthetic", str(approved), bool_policy)

    malformed_policy = _policy(
        approved,
        protected,
        verifier=lambda supplied, configured: RootIdentityEvidence(
            configured, None, "root", 1, True  # type: ignore[arg-type]
        ),
    )
    with pytest.raises(DatasetRootRejected, match="ambiguous"):
        authorize_dataset_root("synthetic", str(approved), malformed_policy)


def test_protected_root_is_rejected_before_identity_verifier(synthetic_root: Path) -> None:
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    called = False

    def verifier(supplied: str, configured: str) -> RootIdentityEvidence:
        nonlocal called
        called = True
        return RootIdentityEvidence(configured, "v", "f", True, True)

    with pytest.raises(DatasetRootRejected, match="protected"):
        authorize_dataset_root(
            "synthetic", str(protected), DatasetAccessPolicy(
                {"synthetic": str(approved)}, (str(protected),), verifier
            )
        )
    assert not called


def test_symlink_spelling_is_not_an_authorized_root(synthetic_root: Path) -> None:
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    alias = synthetic_root / "alias"
    approved.mkdir()
    protected.mkdir()
    try:
        alias.symlink_to(approved, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are unavailable in this synthetic environment")

    with pytest.raises(DatasetRootRejected, match="exact authorized root"):
        authorize_dataset_root("synthetic", str(alias), _policy(approved, protected))


def test_unprivileged_identity_verifier_rejects_unverified_reparse_semantics(synthetic_root: Path) -> None:
    """Verifies that authorize_dataset_root strictly rejects unverified reparse semantics without elevation."""
    approved = synthetic_root / "approved"
    protected = synthetic_root / "protected"
    approved.mkdir()
    protected.mkdir()

    bad_identity = RootIdentityEvidence(
        canonical_path=str(approved),
        volume_identity="vol-1",
        root_file_identity="id-1",
        reparse_points_checked=False,  # Fails closed
        case_semantics_checked=True,
    )
    custom_policy = DatasetAccessPolicy(
        approved_roots={"synthetic": str(approved)},
        protected_roots=(str(protected),),
        identity_verifier=lambda s, a: bad_identity,
    )
    with pytest.raises(DatasetRootRejected, match="root identity is ambiguous or could not be verified"):
        authorize_dataset_root("synthetic", str(approved), custom_policy)

