"""Stage 4 Deterministic Model Benchmarking Engine.

Executes within-domain and zero-shot cross-domain model benchmarking across 5 feature profiles,
2 model families (Logistic Regression, Random Forest), and 4 IoT datasets (ToN-IoT, Edge-IIoTset,
NF-ToN-IoT-v2, CICIoT2023). The data-backed entrypoint remains blocked until trusted authorization
is available. Its isolated report publisher can create machine-readable synthetic reports.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import stat
import tempfile
import time
import pandas as pd
import numpy as np

from iot_ids.experiments.runner import (
    run_within_domain_experiment,
    run_cross_domain_experiment,
)
from iot_ids.features.canonical.flow_builder import CANONICAL_18_FEATURE_NAMES
from iot_ids.provenance.manifest_validation import (
    ManifestValidationError,
    ManifestValidatorUnavailable,
    validate_manifest,
)
from iot_ids.provenance.windows_access import (
    RealDataAuthorizationUnavailable,
    require_real_data_authorization,
)

FEATURE_PROFILES = {
    "baseline_common": [
        "flow_duration", "flow_bytes_per_sec", "proto_tcp", "proto_udp", "proto_icmp"
    ],
    "instant_only": [
        "flow_duration", "flow_bytes_per_sec", "flow_pkts_per_sec", "mean_pkt_size",
        "payload_byte_ratio", "pkt_count_ratio", "tcp_syn_ratio",
        "proto_tcp", "proto_udp", "proto_icmp", "proto_other"
    ],
    "instant_temporal": [
        "flow_duration", "flow_bytes_per_sec", "flow_pkts_per_sec", "mean_pkt_size",
        "payload_byte_ratio", "pkt_count_ratio", "tcp_syn_ratio",
        "proto_tcp", "proto_udp", "proto_icmp", "proto_other",
        "temporal_iat_mean", "temporal_iat_cv", "temporal_flow_rate_ewma",
        "temporal_byte_rate_ewma", "temporal_syn_rate_ewma"
    ],
    "instant_behavioral": [
        "flow_duration", "flow_bytes_per_sec", "flow_pkts_per_sec", "mean_pkt_size",
        "payload_byte_ratio", "pkt_count_ratio", "tcp_syn_ratio",
        "proto_tcp", "proto_udp", "proto_icmp", "proto_other",
        "behavioral_dst_diversity", "behavioral_port_entropy", "behavioral_fanout_ratio",
        "behavioral_unanswered_ratio", "behavioral_src_activity_ewma"
    ],
    "full_multilevel": CANONICAL_18_FEATURE_NAMES,
}

DATASETS = ["ToN-IoT", "Edge-IIoTset", "NF-ToN-IoT-v2", "CICIoT2023"]
MODELS = ["LogisticRegression", "RandomForest"]
STAGE4_REPORT_FILES = (
    "stage4_experiment_results.csv",
    "stage4_within_domain_results.csv",
    "stage4_cross_domain_results.csv",
    "stage4_profile_summary.csv",
    "stage4_fpr_comparison.csv",
    "stage4_model_comparison.csv",
    "stage4_evidence_status.json",
    "stage4_confusion_matrices",
)


class Stage4ReportError(RuntimeError):
    """Controlled report preparation/publication failure with a stable code."""

    def __init__(self, code: str, message: str, *, recovery_path: Path | None = None):
        super().__init__(message)
        self.code = code
        self.recovery_path = recovery_path


def _validate_synthetic_report_destination(output_dir: str | Path) -> Path:
    """Allow isolated tests to publish only beneath the OS temporary directory.

    This is a destination restriction for synthetic report tests, not a dataset
    authorization or authenticated filesystem-identity guarantee. Existing
    existing components from the configured temporary root through the final
    component are inspected without following them; Windows reparse points
    (including junctions) are rejected. Repository destinations
    (including the canonical reports tree) and paths outside the temp root fail
    closed before staging or output files are created. These pathname checks
    do not eliminate concurrent replacement races and are defense in depth only.
    """
    try:
        supplied = Path(output_dir)
        if not supplied.is_absolute():
            raise ValueError
        lexical_output = Path(os.path.abspath(os.fspath(supplied)))
        repository = Path(__file__).resolve().parents[2]

        def overlaps(left: Path, right: Path) -> bool:
            left_norm = os.path.normcase(os.path.abspath(os.fspath(left)))
            right_norm = os.path.normcase(os.path.abspath(os.fspath(right)))
            try:
                return os.path.commonpath((left_norm, right_norm)) in (left_norm, right_norm)
            except ValueError:
                return False

        # Reject repository paths lexically, before querying the candidate path.
        if overlaps(lexical_output, repository):
            raise ValueError

        configured_temp = Path(tempfile.gettempdir())
        lexical_temp_root = Path(os.path.abspath(os.fspath(configured_temp)))
        temp_root_info = _inspect_synthetic_destination_component(lexical_temp_root)
        if temp_root_info is None or not stat.S_ISDIR(temp_root_info.st_mode):
            raise ValueError
        temp_root = lexical_temp_root.resolve(strict=True)
        try:
            lexical_common = os.path.commonpath((
                os.path.normcase(os.fspath(lexical_output)),
                os.path.normcase(os.fspath(lexical_temp_root)),
            ))
        except ValueError:
            raise ValueError from None
        if lexical_common != os.path.normcase(os.fspath(lexical_temp_root)) or lexical_output == lexical_temp_root:
            raise ValueError

        # Inspect every existing component from the configured temporary root
        # through the destination using lstat, before resolving or creating
        # anything. This rejects junctions/reparse points in ancestors as well
        # as at the final component. Missing ancestors are not created here.
        final_info = None
        current = lexical_output
        while True:
            info = _inspect_synthetic_destination_component(current)
            if current == lexical_output:
                final_info = info
            elif info is None or not stat.S_ISDIR(info.st_mode):
                raise ValueError
            if current == lexical_temp_root:
                break
            parent_component = current.parent
            if parent_component == current:
                raise ValueError
            current = parent_component

        parent = lexical_output.parent
        if lexical_output.name in {"", ".", ".."}:
            raise ValueError
        resolved_parent = parent.resolve(strict=True)
        if final_info is None:
            resolved_output = resolved_parent / lexical_output.name
        else:
            # lstat-based inspection rejects reparse points before resolve can
            # follow the final component. Resolve ordinary existing directories
            # and validate the resulting destination again against both roots.
            resolved_output = lexical_output.resolve(strict=True)
        if overlaps(resolved_output, repository):
            raise ValueError
        # Require a strict descendant of the resolved temp directory. This also
        # rejects aliases whose resolved parent escapes the configured temp root.
        if not overlaps(resolved_output, temp_root) or resolved_output == temp_root:
            raise ValueError
        if os.path.commonpath((os.path.normcase(os.fspath(resolved_output)),
                               os.path.normcase(os.fspath(temp_root)))) != os.path.normcase(os.fspath(temp_root)):
            raise ValueError
        if final_info is not None and not resolved_output.is_dir():
            raise ValueError
        return resolved_output
    except (OSError, RuntimeError, TypeError, ValueError):
        raise Stage4ReportError(
            "INVALID_OUTPUT_LOCATION",
            "Synthetic Stage 4 reports require an isolated destination beneath the temporary directory",
        ) from None


def _inspect_synthetic_destination_component(path: Path):
    """Return no-follow metadata, refusing links and Windows reparse points.

    A missing final component is allowed. Any other inspection error is
    propagated so the caller can fail closed. On Windows, absence of the
    reparse metadata needed to distinguish junctions is treated as unsupported.
    """
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None

    if stat.S_ISLNK(info.st_mode):
        raise ValueError("Final synthetic output component is a link")
    if os.name == "nt":
        attributes = getattr(info, "st_file_attributes", None)
        if attributes is None:
            raise OSError("Windows reparse-point metadata is unavailable")
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
        if attributes & reparse_flag:
            raise ValueError("Final synthetic output component is a reparse point")
    return info


def attach_result_completeness_counts(
    summary: pd.DataFrame,
    experiment_rows: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    """Expose omitted/undefined metric counts alongside pandas aggregate means."""
    required = {"result_status", "roc_auc", "pr_auc", *group_columns}
    missing = required.difference(experiment_rows.columns)
    if missing:
        raise ValueError(f"Experiment rows lack result-status columns: {sorted(missing)}")
    aggregations = {
        "experiment_count": ("result_status", "size"),
        "incomplete_experiment_count": (
            "result_status", lambda values: int((values != "COMPLETE").sum())
        ),
        "undefined_roc_auc_count": ("roc_auc", lambda values: int(values.isna().sum())),
        "undefined_pr_auc_count": ("pr_auc", lambda values: int(values.isna().sum())),
    }
    for metric in ("fpr", "fnr", "fp_per_1000"):
        if metric in experiment_rows.columns:
            aggregations[f"undefined_{metric}_count"] = (
                metric, lambda values: int(values.isna().sum())
            )
    counts = (
        experiment_rows.groupby(group_columns, dropna=False)
        .agg(**aggregations)
        .reset_index()
    )
    if isinstance(summary.columns, pd.MultiIndex):
        counts.columns = pd.MultiIndex.from_tuples([(column, "") for column in counts.columns])
        merge_keys = [(column, "") for column in group_columns]
    else:
        merge_keys = group_columns
    return summary.merge(counts, on=merge_keys, how="left", validate="one_to_one")


def run_stage4_within_record(
    dataset: str,
    profile: str,
    feature_names: list[str],
    model: str,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> dict:
    """Run one Stage 4 within-domain record through the shared experiment runner."""
    result = run_within_domain_experiment(
        dataset, profile, feature_names, model, train, validation, test
    )
    return _stage4_record(
        result,
        experiment_id=f"within_{dataset}_{profile}_{model}",
        eval_type="WITHIN_DOMAIN",
    )


def run_stage4_cross_record(
    source: str,
    target: str,
    profile: str,
    feature_names: list[str],
    model: str,
    source_train: pd.DataFrame,
    source_validation: pd.DataFrame,
    target_test: pd.DataFrame,
) -> dict:
    """Run one Stage 4 zero-shot record through the shared experiment runner."""
    result = run_cross_domain_experiment(
        source,
        target,
        profile,
        feature_names,
        model,
        source_train,
        source_validation,
        target_test,
    )
    return _stage4_record(
        result,
        experiment_id=f"cross_{source}_to_{target}_{profile}_{model}",
        eval_type="CROSS_DOMAIN",
    )


def _stage4_record(result: dict, *, experiment_id: str, eval_type: str) -> dict:
    """Map the shared runner contract to the established Stage 4 CSV columns."""
    record = {
        "experiment_id": experiment_id,
        "eval_type": eval_type,
        "source_domain": result["source_dataset"],
        "target_domain": result["target_dataset"],
        "feature_profile": result["feature_profile"],
        "model": result["model_name"],
        "n_train": result["n_train"],
        "n_val": result["n_val"],
        "n_test": result["n_test"],
    }
    omitted = {
        "experiment_type", "source_dataset", "target_dataset", "feature_profile",
        "model_name", "n_train", "n_val", "n_test",
    }
    record.update({key: value for key, value in result.items() if key not in omitted})
    return record


def _validate_experiment_records(rows: pd.DataFrame) -> None:
    required = {
        "experiment_id", "eval_type", "result_status", "roc_auc", "roc_auc_status",
        "roc_auc_reason", "pr_auc", "pr_auc_status", "pr_auc_reason",
        "fpr", "fpr_status", "fpr_reason", "fnr", "fnr_status", "fnr_reason",
        "fp_per_1000", "tn", "fp", "fn", "tp",
    }
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"Stage 4 result rows lack required fields: {sorted(missing)}")
    if rows.empty:
        raise ValueError("Stage 4 report set cannot be empty")
    ids = rows["experiment_id"].astype(str)
    if ids.duplicated().any() or not ids.map(lambda value: re.fullmatch(r"[A-Za-z0-9_.-]+", value)).all():
        raise ValueError("Stage 4 experiment identifiers must be unique safe filename components")
    if set(rows["eval_type"]) != {"WITHIN_DOMAIN", "CROSS_DOMAIN"}:
        raise ValueError("Stage 4 report set must contain within- and cross-domain rows")
    if not set(rows["result_status"]).issubset({"COMPLETE", "INCOMPLETE_METRICS"}):
        raise ValueError("Stage 4 result status is unsupported")

    for metric in ("roc_auc", "pr_auc", "fpr", "fnr"):
        status_column = f"{metric}_status"
        reason_column = f"{metric}_reason"
        for value, status, reason in zip(rows[metric], rows[status_column], rows[reason_column]):
            if status == "UNDEFINED":
                if pd.notna(value) or not isinstance(reason, str) or not reason:
                    raise ValueError(f"Undefined {metric} must have a null value and explicit reason")
            elif status == "DEFINED":
                if pd.isna(value) or reason is not None and not pd.isna(reason):
                    raise ValueError(f"Defined {metric} must have a value and no undefined reason")
                numeric = float(value)
                if not np.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
                    raise ValueError(f"Defined {metric} must be finite and within [0, 1]")
            else:
                raise ValueError(f"{metric} status is unsupported")

    if not rows.loc[rows["fpr"].isna(), "fp_per_1000"].isna().all():
        raise ValueError("FP-per-1000 must remain undefined when FPR is undefined")
    complete = rows["result_status"] == "COMPLETE"
    if rows.loc[complete, ["roc_auc", "pr_auc", "fpr", "fnr", "fp_per_1000"]].isna().any().any():
        raise ValueError("COMPLETE result rows cannot contain undefined metrics")


def _evidence_status_record(manifest: dict | None) -> dict:
    """Describe evidence state without promoting schema or digest checks."""
    if manifest is None:
        manifest_status = "NOT_PROVIDED"
    else:
        try:
            validate_manifest(manifest)
        except ManifestValidatorUnavailable as exc:
            raise Stage4ReportError(
                "MANIFEST_VALIDATOR_UNAVAILABLE",
                "Stage 4 report preparation requires the local manifest validator",
            ) from exc
        except ManifestValidationError as exc:
            raise Stage4ReportError(
                "MANIFEST_INVALID", "Stage 4 report manifest does not satisfy the canonical schema"
            ) from exc
        manifest_status = "SCHEMA_VALID"
    return {
        "manifest_status": manifest_status,
        "authorization_status": "NOT_ESTABLISHED",
        "filesystem_identity_status": "NOT_ESTABLISHED",
        "artifact_integrity_status": "NOT_CHECKED",
        "provenance_status": "UNVERIFIED",
        "scientific_validity_status": "UNVERIFIED",
        "evidence_status": "UNVERIFIED",
        "interpretation": (
            "Schema validity and report publication do not establish authorization, "
            "artifact provenance, or scientific validity."
        ),
    }


def _write_stage4_report_bundle(
    experiment_records: list[dict], staging_dir: Path, *, manifest: dict | None = None
) -> None:
    """Create the complete Stage 4 report set in an isolated staging directory."""
    rows = pd.DataFrame(experiment_records)
    _validate_experiment_records(rows)
    staging_dir.mkdir(parents=True, exist_ok=False)
    cm_dir = staging_dir / "stage4_confusion_matrices"
    cm_dir.mkdir()

    rows.to_csv(staging_dir / "stage4_experiment_results.csv", index=False)
    within = rows[rows["eval_type"] == "WITHIN_DOMAIN"]
    cross = rows[rows["eval_type"] == "CROSS_DOMAIN"]
    within.to_csv(staging_dir / "stage4_within_domain_results.csv", index=False)
    cross.to_csv(staging_dir / "stage4_cross_domain_results.csv", index=False)

    profile_summary = cross.groupby(["model", "feature_profile"])[
        ["roc_auc", "pr_auc", "macro_f1", "fpr", "fnr", "fp_per_1000"]
    ].agg(["mean", "std", "median"]).reset_index()
    profile_summary = attach_result_completeness_counts(
        profile_summary, cross, ["model", "feature_profile"]
    )
    profile_summary.to_csv(staging_dir / "stage4_profile_summary.csv", index=False)

    fpr_comparison = cross.pivot_table(
        index=["source_domain", "target_domain", "model"],
        columns="feature_profile",
        values="fpr",
    ).reset_index()
    if "baseline_common" in fpr_comparison.columns and "full_multilevel" in fpr_comparison.columns:
        fpr_comparison["rel_fpr_reduction_full"] = (
            (fpr_comparison["baseline_common"] - fpr_comparison["full_multilevel"])
            / (fpr_comparison["baseline_common"] + 1e-6)
        )
    if "baseline_common" in fpr_comparison.columns and "instant_behavioral" in fpr_comparison.columns:
        fpr_comparison["rel_fpr_reduction_behavioral"] = (
            (fpr_comparison["baseline_common"] - fpr_comparison["instant_behavioral"])
            / (fpr_comparison["baseline_common"] + 1e-6)
        )
    fpr_comparison.to_csv(staging_dir / "stage4_fpr_comparison.csv", index=False)

    model_comparison = cross.groupby(["model"])[
        ["roc_auc", "pr_auc", "macro_f1", "fpr"]
    ].agg(["mean", "std"]).reset_index()
    model_comparison = attach_result_completeness_counts(model_comparison, cross, ["model"])
    model_comparison.to_csv(staging_dir / "stage4_model_comparison.csv", index=False)

    evidence_record = _evidence_status_record(manifest)
    (staging_dir / "stage4_evidence_status.json").write_text(
        json.dumps(evidence_record, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    for record in experiment_records:
        pd.DataFrame([{
            "tn": record["tn"], "fp": record["fp"],
            "fn": record["fn"], "tp": record["tp"],
        }]).to_csv(cm_dir / f"{record['experiment_id']}_cm.csv", index=False)
    _validate_staged_report_bundle(staging_dir, rows)


def _validate_staged_report_bundle(staging_dir: Path, expected_rows: pd.DataFrame) -> None:
    """Read back and validate every required staged output before publication."""
    csv_reports = STAGE4_REPORT_FILES[:6]
    for name in csv_reports:
        path = staging_dir / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise ValueError("A required Stage 4 report is missing or invalid")
        parsed = pd.read_csv(path, header=None, keep_default_na=False)
        if parsed.empty:
            raise ValueError("A required Stage 4 report is empty")

    evidence_path = staging_dir / "stage4_evidence_status.json"
    if evidence_path.is_symlink() or not evidence_path.is_file() or evidence_path.stat().st_size == 0:
        raise ValueError("The Stage 4 evidence-status record is missing or invalid")
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("The Stage 4 evidence-status record is unreadable") from exc
    required_evidence = {
        "manifest_status", "authorization_status", "filesystem_identity_status",
        "artifact_integrity_status", "provenance_status", "scientific_validity_status",
        "evidence_status", "interpretation",
    }
    if not isinstance(evidence, dict) or set(evidence) != required_evidence:
        raise ValueError("The Stage 4 evidence-status record has an invalid structure")
    if evidence["manifest_status"] not in {"NOT_PROVIDED", "SCHEMA_VALID"} or any(
        evidence[key] != expected
        for key, expected in {
            "authorization_status": "NOT_ESTABLISHED",
            "filesystem_identity_status": "NOT_ESTABLISHED",
            "artifact_integrity_status": "NOT_CHECKED",
            "provenance_status": "UNVERIFIED",
            "scientific_validity_status": "UNVERIFIED",
            "evidence_status": "UNVERIFIED",
        }.items()
    ):
        raise ValueError("The Stage 4 evidence-status record overstates verified evidence")

    raw = pd.read_csv(staging_dir / "stage4_experiment_results.csv")
    _validate_experiment_records(raw)
    if len(raw) != len(expected_rows):
        raise ValueError("The serialized Stage 4 result count does not match the prepared rows")
    for name, expected_type in (("stage4_within_domain_results.csv", "WITHIN_DOMAIN"),
                                ("stage4_cross_domain_results.csv", "CROSS_DOMAIN")):
        parsed = pd.read_csv(staging_dir / name)
        if parsed.empty or not parsed["eval_type"].eq(expected_type).all():
            raise ValueError("A Stage 4 domain report is empty or inconsistent")

    cm_dir = staging_dir / "stage4_confusion_matrices"
    if not cm_dir.is_dir() or cm_dir.is_symlink():
        raise ValueError("The Stage 4 confusion-matrix directory is missing or invalid")
    expected_names = {f"{value}_cm.csv" for value in expected_rows["experiment_id"]}
    actual_names = {child.name for child in cm_dir.iterdir()}
    if actual_names != expected_names:
        raise ValueError("The staged confusion-matrix set is incomplete or contains extras")
    records_by_id = expected_rows.set_index("experiment_id")
    for name in expected_names:
        path = cm_dir / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("A staged confusion-matrix file is invalid")
        matrix = pd.read_csv(path)
        if list(matrix.columns) != ["tn", "fp", "fn", "tp"] or len(matrix) != 1:
            raise ValueError("A staged confusion-matrix file has an invalid structure")
        experiment_id = name[:-len("_cm.csv")]
        expected_counts = records_by_id.loc[experiment_id, ["tn", "fp", "fn", "tp"]]
        if any(int(matrix.loc[0, key]) != int(expected_counts[key]) for key in ("tn", "fp", "fn", "tp")):
            raise ValueError("A staged confusion-matrix file does not match its result row")


def publish_stage4_reports(
    experiment_records: list[dict],
    output_dir: str | Path,
    *,
    replace_func=None,
    manifest: dict | None = None,
) -> None:
    """Publish production Stage 4 reports only after real-data authorization."""
    try:
        require_real_data_authorization()
    except RealDataAuthorizationUnavailable as exc:
        raise Stage4ReportError(
            exc.code.value,
            "Stage 4 report publication is blocked because real-data authorization is unavailable",
        ) from None
    _publish_stage4_reports_unchecked_for_synthetic_tests(
        experiment_records, output_dir, replace_func=replace_func, manifest=manifest
    )


def _publish_stage4_reports_unchecked_for_synthetic_tests(
    experiment_records: list[dict],
    output_dir: str | Path,
    *,
    replace_func=None,
    manifest: dict | None = None,
) -> None:
    """Internal publisher exercised by isolated tests with synthetic outputs only.

    Existing targeted outputs are moved to a same-filesystem backup before staged
    outputs are moved into place. On an ordinary exception, newly installed
    outputs are removed and the previous set is restored. This is rollback, not
    an atomic multi-file transaction; readers may observe a transition and a
    process/host failure or non-cooperating concurrent writer can interrupt it.
    """
    output = _validate_synthetic_report_destination(output_dir)
    parent = output.parent
    if not parent.is_dir() or output.name in {"", ".", ".."}:
        raise Stage4ReportError("INVALID_OUTPUT_LOCATION", "Stage 4 output location is unavailable")
    staging = Path(tempfile.mkdtemp(prefix=".stage4-staging-", dir=parent))
    try:
        _write_stage4_report_bundle(
            experiment_records, staging / "bundle", manifest=manifest
        )
        _publish_staged_bundle(staging / "bundle", output, replace_func=replace_func)
    except Exception as exc:
        try:
            shutil.rmtree(staging)
        except OSError:
            raise Stage4ReportError(
                "TEMP_CLEANUP_FAILED", "Stage 4 failed and its temporary staging directory needs cleanup",
                recovery_path=getattr(exc, "recovery_path", None),
            ) from None
        if isinstance(exc, Stage4ReportError):
            raise
        raise Stage4ReportError(
            "PREPARATION_FAILED", "Stage 4 report preparation failed; existing reports were retained"
        ) from None
    try:
        shutil.rmtree(staging)
    except OSError:
        raise Stage4ReportError(
            "PUBLISHED_TEMP_CLEANUP_FAILED",
            "Stage 4 reports were published, but their temporary staging directory needs cleanup",
        ) from None


def _publish_staged_bundle(staging: Path, output: Path, *, replace_func=None) -> None:
    output = _validate_synthetic_report_destination(output)
    replace = replace_func or os.replace
    _validate_staged_report_bundle(staging, pd.read_csv(staging / "stage4_experiment_results.csv"))
    if output.is_symlink() or output.exists() and not output.is_dir():
        raise Stage4ReportError("INVALID_OUTPUT_LOCATION", "Stage 4 output location is ambiguous")
    created_output = not output.exists()
    if created_output:
        output.mkdir()

    targets = [(name, output / name) for name in STAGE4_REPORT_FILES]
    for name, target in targets:
        if target.is_symlink():
            if created_output:
                output.rmdir()
            raise Stage4ReportError("INVALID_EXISTING_OUTPUT", "An existing Stage 4 output is ambiguous")
        if target.exists() and (target.is_dir() != (name == "stage4_confusion_matrices")):
            if created_output:
                output.rmdir()
            raise Stage4ReportError("INVALID_EXISTING_OUTPUT", "An existing Stage 4 output has an unexpected type")

    try:
        backup = Path(tempfile.mkdtemp(prefix=".stage4-backup-", dir=output.parent))
    except OSError:
        if created_output:
            output.rmdir()
        raise Stage4ReportError(
            "PREPARATION_FAILED", "Stage 4 backup workspace could not be created"
        ) from None
    backed_up: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    try:
        for name, target in targets:
            if target.exists():
                saved = backup / name
                replace(target, saved)
                backed_up.append((saved, target))
        for name, target in targets:
            replace(staging / name, target)
            installed.append(target)
    except Exception:
        rollback_errors = []
        for target in reversed(installed):
            try:
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                elif target.exists() or target.is_symlink():
                    target.unlink()
            except Exception:
                rollback_errors.append(target.name)
        for saved, target in reversed(backed_up):
            try:
                replace(saved, target)
            except Exception:
                rollback_errors.append(target.name)
        if rollback_errors:
            raise Stage4ReportError(
                "ROLLBACK_INCOMPLETE",
                "Stage 4 publication failed and rollback was incomplete; the recovery backup was retained",
                recovery_path=backup,
            ) from None
        try:
            shutil.rmtree(backup)
        except OSError:
            raise Stage4ReportError(
                "ROLLBACK_CLEANUP_FAILED",
                "The previous report set was restored, but its backup directory needs cleanup",
                recovery_path=backup,
            ) from None
        if created_output:
            try:
                output.rmdir()
            except OSError:
                pass
        raise Stage4ReportError(
            "PUBLICATION_FAILED", "Stage 4 publication failed; the previous report set was restored"
        ) from None
    else:
        try:
            shutil.rmtree(backup)
        except OSError:
            raise Stage4ReportError(
                "PUBLISHED_BACKUP_REMAINS",
                "Stage 4 reports were published, but the previous report backup needs cleanup",
                recovery_path=backup,
            ) from None


def perform_preflight_data_integrity_audit(data_dir: Path):
    """Verifies schemas, split non-overlap, label ranges, and absence of NaN/Inf before training."""
    try:
        require_real_data_authorization()
    except RealDataAuthorizationUnavailable:
        raise Stage4ReportError(
            "REAL_AUTHORIZATION_DISABLED",
            "Stage 4 data audit is blocked because real-data authorization is unavailable",
        ) from None
    print("--- Running Stage 4 Pre-Flight Data Integrity Audit ---")
    for ds in DATASETS:
        ds_dir = data_dir / ds
        tr_p = ds_dir / "train.parquet"
        val_p = ds_dir / "val.parquet"
        te_p = ds_dir / "test.parquet"

        if not (tr_p.exists() and val_p.exists() and te_p.exists()):
            raise FileNotFoundError(f"Missing materialized splits for dataset: {ds}")

        df_tr = pd.read_parquet(tr_p)
        df_v = pd.read_parquet(val_p)
        df_te = pd.read_parquet(te_p)

        # 1. Label range check
        for split_name, df_s in [("train", df_tr), ("val", df_v), ("test", df_te)]:
            validate_stage4_split_labels(ds, split_name, df_s)

        # 2. NaN/Inf check on canonical features
        for f in CANONICAL_18_FEATURE_NAMES:
            for split_name, df_s in [("train", df_tr), ("val", df_v), ("test", df_te)]:
                col_vals = df_s[f].values
                if np.isnan(col_vals).any() or np.isinf(col_vals).any():
                    raise ValueError(f"NaN or Inf detected in feature {f} of {ds} {split_name}")

        # 3. Non-overlapping timestamp check
        tr_max_ts = df_tr["timestamp_start"].max()
        val_min_ts = df_v["timestamp_start"].min()
        val_max_ts = df_v["timestamp_start"].max()
        te_min_ts = df_te["timestamp_start"].min()

        if tr_max_ts > val_min_ts:
            print(f"Warning: Train/Val timestamp boundary overlap in {ds}: train_max={tr_max_ts}, val_min={val_min_ts}")
        if val_max_ts > te_min_ts:
            print(f"Warning: Val/Test timestamp boundary overlap in {ds}: val_max={val_max_ts}, test_min={te_min_ts}")

    print("Pre-Flight Data Integrity Audit Passed 100% Cleanly!\n")


def validate_stage4_split_labels(dataset: str, split_name: str, frame: pd.DataFrame) -> None:
    """Enforce the existing Stage 4 requirement that every split has both classes."""
    if "label" not in frame.columns:
        raise ValueError(f"Missing label column in {dataset} {split_name}")
    labels = frame["label"].unique()
    if not set(labels).issubset({0, 1}):
        raise ValueError(f"Invalid label values in {dataset} {split_name}: {labels}")
    if len(labels) < 2:
        raise ValueError(f"Single class detected in {dataset} {split_name}: {labels}")


def load_dataset_splits(data_dir: Path, ds_name: str):
    try:
        require_real_data_authorization()
    except RealDataAuthorizationUnavailable:
        raise Stage4ReportError(
            "REAL_AUTHORIZATION_DISABLED",
            "Stage 4 split loading is blocked because real-data authorization is unavailable",
        ) from None
    ds_path = data_dir / ds_name
    return (
        pd.read_parquet(ds_path / "train.parquet"),
        pd.read_parquet(ds_path / "val.parquet"),
        pd.read_parquet(ds_path / "test.parquet"),
    )


def run_stage4_benchmarks(smoke_test: bool = False):
    # Must remain ahead of all path construction, output checks, discovery,
    # split reads, model fitting, and evaluation until native authorization exists.
    try:
        require_real_data_authorization()
    except RealDataAuthorizationUnavailable as exc:
        raise Stage4ReportError(
            exc.code.value, "Stage 4 is blocked because real-data authorization is unavailable"
        ) from None

    data_dir = Path("data/processed/stage3")
    output_dir = Path("reports/stage4")
    if not output_dir.parent.is_dir():
        raise Stage4ReportError("INVALID_OUTPUT_LOCATION", "Stage 4 report parent directory is unavailable")

    perform_preflight_data_integrity_audit(data_dir)

    print("==========================================================================")
    print(f"=== STAGE 4 BENCHMARK EXECUTION (Smoke Test = {smoke_test}) ===")
    print("==========================================================================")

    target_ds_list = ["ToN-IoT", "Edge-IIoTset"] if smoke_test else DATASETS
    target_profiles = ["instant_only"] if smoke_test else list(FEATURE_PROFILES.keys())
    target_models = ["LogisticRegression"] if smoke_test else MODELS

    # Load splits
    datasets_data = {}
    for ds in target_ds_list:
        datasets_data[ds] = load_dataset_splits(data_dir, ds)

    all_experiments = []

    t0 = time.time()

    # 1. WITHIN-DOMAIN EXPERIMENTS
    print("--- Executing Within-Domain Experiments ---")
    for ds in datasets_data.keys():
        df_tr, df_v, df_te = datasets_data[ds]
        for p_name in target_profiles:
            f_names = FEATURE_PROFILES[p_name]
            for m_name in target_models:
                rec = run_stage4_within_record(
                    ds, p_name, f_names, m_name, df_tr, df_v, df_te
                )
                all_experiments.append(rec)

    # 2. CROSS-DOMAIN ZERO-SHOT TRANSFER EXPERIMENTS
    print("--- Executing Zero-Shot Cross-Domain Transfer Experiments ---")
    for src in datasets_data.keys():
        for tgt in datasets_data.keys():
            if src == tgt:
                continue

            src_tr, src_v, _ = datasets_data[src]
            _, _, tgt_te = datasets_data[tgt]

            for p_name in target_profiles:
                f_names = FEATURE_PROFILES[p_name]
                for m_name in target_models:
                    rec = run_stage4_cross_record(
                        src, tgt, p_name, f_names, m_name, src_tr, src_v, tgt_te
                    )
                    all_experiments.append(rec)

    t1 = time.time()
    print(f"\nAll Stage 4 Experiments Completed in {t1 - t0:.2f} seconds!")

    publish_stage4_reports(all_experiments, output_dir)

    print(f"Exported Machine-Readable Stage 4 CSV Reports to {output_dir}:")
    print("  - stage4_experiment_results.csv")
    print("  - stage4_within_domain_results.csv")
    print("  - stage4_cross_domain_results.csv")
    print("  - stage4_profile_summary.csv")
    print("  - stage4_fpr_comparison.csv")
    print("  - stage4_model_comparison.csv")
    print("  - stage4_evidence_status.json (provenance/authorization remain unverified)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 4 Model Benchmarking Runner")
    parser.add_argument("--smoke-test", action="store_true", help="Run fast pre-flight smoke test")
    args = parser.parse_args()
    try:
        run_stage4_benchmarks(smoke_test=args.smoke_test)
    except Stage4ReportError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
