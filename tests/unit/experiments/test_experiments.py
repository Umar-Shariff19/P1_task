"""Unit tests for Stage 4 experimental framework and leakage safeguards."""

import pytest
import numpy as np
import pandas as pd
import json
import importlib.util
import os
import stat
import subprocess
import tempfile
from types import SimpleNamespace
from pathlib import Path
from io import StringIO

from iot_ids.experiments.preprocessing import FeaturePreprocessor
from iot_ids.experiments.evaluator import optimize_threshold_on_val, evaluate_predictions
from iot_ids.experiments.runner import run_within_domain_experiment, run_cross_domain_experiment
from iot_ids.provenance import (
    AuthorizationDecision,
    AuthorizationScope,
    AuthorizationStatus,
    PreflightOperationBlocked,
    execute_after_preflight,
)
from iot_ids.provenance.windows_access import RealDataAuthorizationUnavailable

_ABLATION_PATH = "scripts/04_analyze_ablations.py"
_ABLATION_SPEC = importlib.util.spec_from_file_location("stage4_ablation_reporting", _ABLATION_PATH)
_ABLATION_MODULE = importlib.util.module_from_spec(_ABLATION_SPEC)
_ABLATION_SPEC.loader.exec_module(_ABLATION_MODULE)
_BENCHMARK_SPEC = importlib.util.spec_from_file_location(
    "stage4_benchmark_reporting", "scripts/04_benchmark_models.py"
)
_BENCHMARK_MODULE = importlib.util.module_from_spec(_BENCHMARK_SPEC)
_BENCHMARK_SPEC.loader.exec_module(_BENCHMARK_MODULE)
_LEGACY_BENCHMARK_SPEC = importlib.util.spec_from_file_location(
    "stage4_legacy_benchmark_runner", "scripts/04_run_benchmarks.py"
)
_LEGACY_BENCHMARK_MODULE = importlib.util.module_from_spec(_LEGACY_BENCHMARK_SPEC)
_LEGACY_BENCHMARK_SPEC.loader.exec_module(_LEGACY_BENCHMARK_MODULE)


def test_preprocessor_train_only_fitting_safeguard():
    feature_names = ["flow_duration", "flow_bytes_per_sec", "payload_byte_ratio"]
    preprocessor = FeaturePreprocessor(feature_names)

    df_dummy = pd.DataFrame({
        "flow_duration": [1.0, 2.0, 3.0],
        "flow_bytes_per_sec": [100.0, 200.0, 300.0],
        "payload_byte_ratio": [0.1, 0.2, 0.3],
    })

    # transform without fit_transform must raise RuntimeError
    with pytest.raises(RuntimeError, match="must be fitted"):
        preprocessor.transform(df_dummy)

    # fit_transform on train
    X_train = preprocessor.fit_transform(df_dummy)
    assert X_train.shape == (3, 3)
    assert preprocessor.is_fitted

    # now transform on val succeeds
    X_val = preprocessor.transform(df_dummy)
    assert X_val.shape == (3, 3)


def test_threshold_optimization_and_evaluation():
    y_val = np.array([0, 0, 0, 1, 1, 1])
    val_probs = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])

    best_tau = optimize_threshold_on_val(y_val, val_probs)
    assert 0.3 <= best_tau <= 0.7

    metrics = evaluate_predictions(y_val, val_probs, threshold=best_tau)
    assert metrics["roc_auc"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["fpr"] == 0.0
    assert metrics["tn"] == 3
    assert metrics["tp"] == 3


@pytest.mark.parametrize(
    ("labels", "probabilities", "threshold", "message"),
    [
        ([0, 1], [0.1], 0.5, "same number of entries"),
        ([0, 1], [0.1, float("nan")], 0.5, "finite values"),
        ([0, 1], [-0.1, 0.9], 0.5, "within \\[0, 1\\]"),
        ([0, 1], [0.1, 0.9], 1.5, "threshold must be"),
        ([0, 2], [0.1, 0.9], 0.5, "binary labels"),
    ],
)
def test_metric_evaluator_rejects_invalid_inputs_instead_of_fabricating_scores(
    labels, probabilities, threshold, message
):
    with pytest.raises(ValueError, match=message):
        evaluate_predictions(np.asarray(labels), np.asarray(probabilities), threshold=threshold)


@pytest.mark.parametrize(
    ("labels", "probabilities", "defined_rate", "undefined_rate"),
    [
        ([0, 0, 0], [0.1, 0.6, 0.8], "fpr", "fnr"),
        ([1, 1, 1], [0.1, 0.6, 0.8], "fnr", "fpr"),
    ],
)
def test_single_class_metrics_are_explicitly_undefined_and_json_safe(
    labels, probabilities, defined_rate, undefined_rate
):
    metrics = evaluate_predictions(np.asarray(labels), np.asarray(probabilities), threshold=0.5)

    assert metrics["result_status"] == "INCOMPLETE_METRICS"
    assert metrics["roc_auc"] is None
    assert metrics["roc_auc_status"] == "UNDEFINED"
    assert metrics["roc_auc_reason"] == "single_class_labels"
    assert metrics["pr_auc"] is None
    assert metrics["pr_auc_status"] == "UNDEFINED"
    assert metrics["pr_auc_reason"] == "single_class_labels"
    assert metrics[defined_rate] is not None
    assert metrics[undefined_rate] is None
    expected_reason = "no_positive_labels" if undefined_rate == "fnr" else "no_negative_labels"
    assert metrics[f"{undefined_rate}_reason"] == expected_reason

    json_record = json.loads(json.dumps(metrics, allow_nan=False))
    assert json_record["roc_auc"] is None
    csv_text = pd.DataFrame([metrics]).to_csv(index=False)
    csv_record = pd.read_csv(StringIO(csv_text)).iloc[0]
    assert pd.isna(csv_record["roc_auc"])
    assert csv_record["roc_auc_status"] == "UNDEFINED"
    assert csv_record["roc_auc_reason"] == "single_class_labels"
    assert csv_record["result_status"] == "INCOMPLETE_METRICS"


def test_threshold_optimizer_rejects_single_class_validation_labels():
    with pytest.raises(ValueError, match="requires both label classes"):
        optimize_threshold_on_val(np.array([0, 0]), np.array([0.1, 0.2]))


def test_ablation_summary_preserves_undefined_counts_without_zero_fallback():
    summary = _ABLATION_MODULE.summarize_metric(
        pd.DataFrame({"roc_auc": [None, 0.75]}), "roc_auc"
    )
    assert summary == (0.75, 1, 1)
    assert _ABLATION_MODULE.summarize_metric(
        pd.DataFrame({"roc_auc": [None]}), "roc_auc"
    ) == (None, 0, 1)
    assert _ABLATION_MODULE.summarize_metric(
        pd.DataFrame({"roc_auc": pd.Series(dtype=float)}), "roc_auc"
    ) == (None, 0, 0)
    assert _ABLATION_MODULE._difference(None, 0.75) is None


def test_benchmark_summaries_report_incomplete_and_undefined_counts():
    rows = pd.DataFrame({
        "model": ["RF", "RF"],
        "feature_profile": ["synthetic", "synthetic"],
        "result_status": ["COMPLETE", "INCOMPLETE_METRICS"],
        "roc_auc": [0.8, None],
        "pr_auc": [0.7, None],
    })
    summary = rows.groupby(["model", "feature_profile"])[["roc_auc", "pr_auc"]].agg(
        ["mean", "std", "median"]
    ).reset_index()
    recorded = _BENCHMARK_MODULE.attach_result_completeness_counts(
        summary, rows, ["model", "feature_profile"]
    )
    assert recorded.loc[0, ("experiment_count", "")] == 2
    assert recorded.loc[0, ("incomplete_experiment_count", "")] == 1
    assert recorded.loc[0, ("undefined_roc_auc_count", "")] == 1
    assert recorded.loc[0, ("undefined_pr_auc_count", "")] == 1
    assert recorded.loc[0, ("roc_auc", "mean")] == pytest.approx(0.8)


def test_stage4_shared_runner_lifecycle_preserves_partial_metrics_and_aggregation():
    """Exercise the Stage 4 record path with synthetic frames and temporary output only."""
    features = ["flow_duration", "flow_bytes_per_sec", "payload_byte_ratio"]
    train = pd.DataFrame({
        "flow_duration": [1., 2., 3., 4., 5., 6., 7., 8.],
        "flow_bytes_per_sec": [10., 20., 30., 40., 50., 60., 70., 80.],
        "payload_byte_ratio": [.1, .2, .1, .2, .8, .9, .8, .9],
        "label": [0, 0, 0, 0, 1, 1, 1, 1],
    })
    valid_test = train.iloc[[0, 1, 6, 7]].copy()
    incomplete_test = train.iloc[[0, 1, 2]].copy()

    complete = _BENCHMARK_MODULE.run_stage4_within_record(
        "SYNTHETIC_ONLY", "synthetic", features, "LogisticRegression",
        train, train, valid_test,
    )
    incomplete = _BENCHMARK_MODULE.run_stage4_within_record(
        "SYNTHETIC_ONLY", "synthetic", features, "LogisticRegression",
        train, train, incomplete_test,
    )
    cross = _BENCHMARK_MODULE.run_stage4_cross_record(
        "SYNTHETIC_SOURCE", "SYNTHETIC_TARGET", "synthetic", features,
        "LogisticRegression", train, train, valid_test,
    )
    assert complete["eval_type"] == "WITHIN_DOMAIN"
    assert complete["result_status"] == "COMPLETE"
    assert isinstance(complete["roc_auc"], float)
    assert incomplete["result_status"] == "INCOMPLETE_METRICS"
    assert incomplete["roc_auc"] is None
    assert incomplete["roc_auc_status"] == "UNDEFINED"
    assert incomplete["roc_auc_reason"] == "single_class_labels"
    assert incomplete["accuracy"] is not None
    assert cross["eval_type"] == "CROSS_DOMAIN"
    assert cross["source_domain"] == "SYNTHETIC_SOURCE"
    assert cross["target_domain"] == "SYNTHETIC_TARGET"
    assert cross["result_status"] == "COMPLETE"

    # JSON round-trip keeps null distinct from a numeric fallback; aggregation
    # uses the production Stage 4 helper and leaves missing groups absent.
    with tempfile.TemporaryDirectory(prefix=".synthetic-stage4-", dir=Path.cwd()) as temp:
        result_path = Path(temp) / "synthetic_results.json"
        result_path.write_text(json.dumps([complete, incomplete], allow_nan=False), encoding="utf-8")
        restored = json.loads(result_path.read_text(encoding="utf-8"))
        assert restored[1]["roc_auc"] is None
        csv_path = Path(temp) / "synthetic_results.csv"
        pd.DataFrame(restored).to_csv(csv_path, index=False)
        csv_restored = pd.read_csv(csv_path)
        assert pd.isna(csv_restored.loc[1, "roc_auc"])
        assert csv_restored.loc[1, "roc_auc_status"] == "UNDEFINED"
        assert csv_restored.loc[1, "roc_auc_reason"] == "single_class_labels"
        rows = pd.DataFrame(restored)
        grouped = rows.groupby(["model", "feature_profile"])[["roc_auc", "pr_auc"]].agg(
            ["mean", "std", "median"]
        ).reset_index()
        summary = _BENCHMARK_MODULE.attach_result_completeness_counts(
            grouped, rows, ["model", "feature_profile"]
        )
        assert summary.loc[0, ("experiment_count", "")] == 2
        assert summary.loc[0, ("incomplete_experiment_count", "")] == 1
        assert summary.loc[0, ("undefined_roc_auc_count", "")] == 1
        assert summary.loc[0, ("roc_auc", "mean")] == pytest.approx(complete["roc_auc"])

    assert _ABLATION_MODULE.summarize_metric(
        pd.DataFrame(columns=["roc_auc"]), "roc_auc"
    ) == (None, 0, 0)


def test_stage4_record_failure_does_not_return_successful_row():
    features = ["flow_duration", "flow_bytes_per_sec", "payload_byte_ratio"]
    train = pd.DataFrame({
        "flow_duration": [1., 2., 3., 4., 5., 6.],
        "flow_bytes_per_sec": [10., 20., 30., 40., 50., 60.],
        "payload_byte_ratio": [.1, .2, .1, .8, .9, .8],
        "label": [0, 0, 0, 1, 1, 1],
    })
    invalid_validation = train.iloc[:3].copy()
    with pytest.raises(ValueError, match="requires both label classes"):
        _BENCHMARK_MODULE.run_stage4_within_record(
            "SYNTHETIC_ONLY", "synthetic", features, "LogisticRegression",
            train, invalid_validation, train,
        )


def _synthetic_stage4_records(tag: str) -> list[dict]:
    features = ["flow_duration", "flow_bytes_per_sec", "payload_byte_ratio"]
    train = pd.DataFrame({
        "flow_duration": [1., 2., 3., 4., 5., 6., 7., 8.],
        "flow_bytes_per_sec": [10., 20., 30., 40., 50., 60., 70., 80.],
        "payload_byte_ratio": [.1, .2, .1, .2, .8, .9, .8, .9],
        "label": [0, 0, 0, 0, 1, 1, 1, 1],
    })
    offset = float(len(tag)) * 0.01
    train["flow_duration"] += offset
    valid_target = train.iloc[[0, 1, 6, 7]].copy()
    benign_target = train.iloc[[0, 1, 2]].copy()
    benign_target["label"] = 0
    attack_target = train.iloc[[5, 6, 7]].copy()
    attack_target["label"] = 1

    records = [
        _BENCHMARK_MODULE.run_stage4_within_record(
            f"SYNTHETIC_{tag}", "synthetic", features, "LogisticRegression",
            train, train, valid_target,
        ),
        _BENCHMARK_MODULE.run_stage4_cross_record(
            f"SYNTHETIC_{tag}", f"SYNTHETIC_{tag}_VALID", "synthetic", features,
            "LogisticRegression", train, train, valid_target,
        ),
        _BENCHMARK_MODULE.run_stage4_cross_record(
            f"SYNTHETIC_{tag}", f"SYNTHETIC_{tag}_BENIGN_ONLY", "synthetic", features,
            "LogisticRegression", train, train, benign_target,
        ),
        _BENCHMARK_MODULE.run_stage4_cross_record(
            f"SYNTHETIC_{tag}", f"SYNTHETIC_{tag}_ATTACK_ONLY", "synthetic", features,
            "LogisticRegression", train, train, attack_target,
        ),
    ]
    return records


def _published_stage4_snapshot(output: Path) -> dict[str, bytes]:
    snapshot = {}
    for name in _BENCHMARK_MODULE.STAGE4_REPORT_FILES[:-1]:
        snapshot[name] = (output / name).read_bytes()
    cm_dir = output / "stage4_confusion_matrices"
    for path in cm_dir.iterdir():
        snapshot[f"stage4_confusion_matrices/{path.name}"] = path.read_bytes()
    return snapshot


def test_stage4_report_publication_synthetic_success_and_undefined_statuses(tmp_path):
    records = _synthetic_stage4_records("PUB_A")
    output = tmp_path / "reports" / "stage4"
    output.parent.mkdir()
    output.mkdir()
    unrelated_plot = output / "plots" / "keep.txt"
    unrelated_plot.parent.mkdir()
    unrelated_plot.write_text("unrelated synthetic sentinel", encoding="utf-8")

    _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(records, output)

    evidence = json.loads((output / "stage4_evidence_status.json").read_text(encoding="utf-8"))
    assert evidence["manifest_status"] == "NOT_PROVIDED"
    assert evidence["evidence_status"] == "UNVERIFIED"

    assert set(_BENCHMARK_MODULE.STAGE4_REPORT_FILES[:-1]).issubset(
        {path.name for path in output.iterdir()}
    )
    cross = pd.read_csv(output / "stage4_cross_domain_results.csv")
    assert len(cross) == 3
    incomplete = cross[cross["result_status"] == "INCOMPLETE_METRICS"]
    assert len(incomplete) == 2
    assert incomplete["roc_auc"].isna().all()
    assert incomplete["roc_auc_status"].eq("UNDEFINED").all()
    assert incomplete["roc_auc_reason"].eq("single_class_labels").all()
    assert incomplete["pr_auc"].isna().all()

    profile = pd.read_csv(output / "stage4_profile_summary.csv", header=[0, 1])
    assert profile["experiment_count"].iloc[0, 0] == 3
    assert profile["incomplete_experiment_count"].iloc[0, 0] == 2
    assert profile["undefined_roc_auc_count"].iloc[0, 0] == 2
    assert profile["undefined_fpr_count"].iloc[0, 0] == 1
    assert profile["undefined_fnr_count"].iloc[0, 0] == 1
    assert profile["undefined_fp_per_1000_count"].iloc[0, 0] == 1
    assert unrelated_plot.read_text(encoding="utf-8") == "unrelated synthetic sentinel"
    assert len(list((output / "stage4_confusion_matrices").iterdir())) == len(records)


def _synthetic_manifest_for_reporting() -> dict:
    examples = Path("results/provenance/experiment_manifest_schema_examples.json")
    manifest = json.loads(examples.read_text(encoding="utf-8"))["positive"]
    manifest["experiment_id"] = "SYNTHETIC_REPORT_ONLY"
    manifest["metrics"][0].update(
        name="synthetic_fixture_metric",
        definition="artificial fixture value; not IDS performance",
        value=0.25,
    )
    manifest["datasets"][0]["authorization_reference"] = "synthetic-placeholder-not-approval"
    return manifest


def test_stage4_report_records_schema_validity_without_promoting_evidence(tmp_path):
    records = _synthetic_stage4_records("EVIDENCE_STATUS")
    output = tmp_path / "reports" / "stage4"
    output.parent.mkdir()
    _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
        records, output, manifest=_synthetic_manifest_for_reporting()
    )
    evidence = json.loads((output / "stage4_evidence_status.json").read_text(encoding="utf-8"))
    assert evidence["manifest_status"] == "SCHEMA_VALID"
    assert evidence["authorization_status"] == "NOT_ESTABLISHED"
    assert evidence["filesystem_identity_status"] == "NOT_ESTABLISHED"
    assert evidence["artifact_integrity_status"] == "NOT_CHECKED"
    assert evidence["provenance_status"] == "UNVERIFIED"
    assert evidence["scientific_validity_status"] == "UNVERIFIED"
    assert evidence["evidence_status"] == "UNVERIFIED"


def test_invalid_manifest_fails_before_report_publication_and_preserves_previous_set(tmp_path):
    output = tmp_path / "reports" / "stage4"
    output.parent.mkdir()
    _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
        _synthetic_stage4_records("MANIFEST_OLD"), output
    )
    before = _published_stage4_snapshot(output)
    invalid = _synthetic_manifest_for_reporting()
    del invalid["datasets"][0]["split_id"]
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as error:
        _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
            _synthetic_stage4_records("MANIFEST_NEW"), output, manifest=invalid
        )
    assert error.value.code == "MANIFEST_INVALID"
    assert _published_stage4_snapshot(output) == before
    assert not list(tmp_path.glob(".stage4-staging-*"))


def test_preflight_failure_cannot_publish_stage4_report_bundle(tmp_path):
    class SyntheticTestPolicy:
        def authorize(self, _manifest):
            return AuthorizationDecision(
                AuthorizationStatus.AUTHORIZED, AuthorizationScope.SYNTHETIC_ONLY
            )

    output = tmp_path / "reports" / "stage4"
    invalid = _synthetic_manifest_for_reporting()
    del invalid["models"][0]["checkpoint_sha256"]
    with pytest.raises(PreflightOperationBlocked):
        execute_after_preflight(
            lambda: _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
                _synthetic_stage4_records("PREFLIGHT_BLOCKED"), output
            ),
            invalid,
            authorization_policy=SyntheticTestPolicy(),
        )
    assert not output.exists()


def test_stage4_entrypoints_refuse_before_dataset_discovery(monkeypatch):
    calls = []
    stage4_loader = _BENCHMARK_MODULE.load_dataset_splits
    legacy_loader = _LEGACY_BENCHMARK_MODULE.load_dataset_splits

    def unexpected_access(*args, **kwargs):
        calls.append("DATA_ACCESS")
        raise AssertionError("dataset access must not occur")

    monkeypatch.setattr(_BENCHMARK_MODULE, "load_dataset_splits", unexpected_access)
    monkeypatch.setattr(_LEGACY_BENCHMARK_MODULE, "load_dataset_splits", unexpected_access)
    monkeypatch.setattr(_BENCHMARK_MODULE.pd, "read_parquet", unexpected_access)

    # Direct calls to the leaf audit/load helpers also stop before touching
    # even a missing synthetic fixture path.
    with tempfile.TemporaryDirectory(prefix=".synthetic-stage4-blocked-", dir=Path.cwd()) as temp:
        synthetic_root = Path(temp)
        with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as audit_error:
            _BENCHMARK_MODULE.perform_preflight_data_integrity_audit(synthetic_root)
        assert audit_error.value.code == "REAL_AUTHORIZATION_DISABLED"
        with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as load_error:
            stage4_loader(synthetic_root, "SYNTHETIC_ONLY")
        assert load_error.value.code == "REAL_AUTHORIZATION_DISABLED"
        with pytest.raises(RealDataAuthorizationUnavailable) as legacy_load_error:
            legacy_loader(synthetic_root, "SYNTHETIC_ONLY")
        assert legacy_load_error.value.code.value == "REAL_AUTHORIZATION_DISABLED"

    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as current_error:
        _BENCHMARK_MODULE.run_stage4_benchmarks(smoke_test=True)
    assert current_error.value.code == "REAL_AUTHORIZATION_DISABLED"
    with pytest.raises(RealDataAuthorizationUnavailable) as legacy_error:
        _LEGACY_BENCHMARK_MODULE.run_benchmarks(smoke_test=True)
    assert legacy_error.value.code.value == "REAL_AUTHORIZATION_DISABLED"
    assert calls == []


def test_ablation_report_entrypoint_refuses_before_read_or_write(monkeypatch, tmp_path):
    reads = []
    writes = []
    monkeypatch.setattr(_ABLATION_MODULE.pd, "read_csv", lambda *a, **k: reads.append((a, k)))
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda *a, **k: writes.append((a, k)))
    with pytest.raises(RealDataAuthorizationUnavailable) as error:
        _ABLATION_MODULE.analyze_ablations(reports_dir=tmp_path)
    assert error.value.code.value == "REAL_AUTHORIZATION_DISABLED"
    assert reads == []
    assert writes == []


def test_stage4_preparation_failure_preserves_previous_report_set(monkeypatch, tmp_path):
    root = tmp_path
    output = root / "reports" / "stage4"
    output.parent.mkdir()
    _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
        _synthetic_stage4_records("PREP_OLD"), output
    )
    before = _published_stage4_snapshot(output)

    def fail_during_preparation(_records, staging_dir, **_kwargs):
        staging_dir.mkdir()
        (staging_dir / "partial.csv").write_text("partial", encoding="utf-8")
        raise OSError("injected synthetic preparation failure")

    monkeypatch.setattr(_BENCHMARK_MODULE, "_write_stage4_report_bundle", fail_during_preparation)
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as error:
        _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
            _synthetic_stage4_records("PREP_NEW"), output
        )
    assert error.value.code == "PREPARATION_FAILED"
    assert _published_stage4_snapshot(output) == before
    assert not list(root.glob(".stage4-staging-*"))
    assert not list(root.glob(".stage4-backup-*"))


def test_stage4_publication_failure_rolls_back_previous_report_set(tmp_path):
    root = tmp_path
    output = root / "reports" / "stage4"
    output.parent.mkdir()
    _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
        _synthetic_stage4_records("ROLLBACK_OLD"), output
    )
    before = _published_stage4_snapshot(output)
    calls = 0
    injected = False

    def fail_once_during_install(source, target):
        nonlocal calls, injected
        calls += 1
        # Every bundle member is backed up before the second install move.
        if calls == len(_BENCHMARK_MODULE.STAGE4_REPORT_FILES) + 2 and not injected:
            injected = True
            raise OSError("injected synthetic publication failure")
        os.replace(source, target)

    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as error:
        _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
            _synthetic_stage4_records("ROLLBACK_NEW"), output,
            replace_func=fail_once_during_install,
        )
    assert injected
    assert error.value.code == "PUBLICATION_FAILED"
    assert _published_stage4_snapshot(output) == before
    assert not list(root.glob(".stage4-staging-*"))
    assert not list(root.glob(".stage4-backup-*"))


def test_stage4_repeated_publication_replaces_rows_and_stale_confusion_matrices(tmp_path):
    root = tmp_path
    output = root / "reports" / "stage4"
    output.parent.mkdir()
    first = _synthetic_stage4_records("REPEAT_FIRST")
    second = _synthetic_stage4_records("REPEAT_SECOND")[:2]
    _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(first, output)
    _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(second, output)

    results = pd.read_csv(output / "stage4_experiment_results.csv")
    assert len(results) == len(second)
    assert results["source_domain"].str.contains("REPEAT_SECOND").all()
    assert not results["source_domain"].str.contains("REPEAT_FIRST").any()
    confusion_matrices = list((output / "stage4_confusion_matrices").iterdir())
    assert len(confusion_matrices) == len(second)
    assert all("REPEAT_SECOND" in path.name for path in confusion_matrices)


def test_synthetic_publisher_rejects_repository_destination_before_mutation(monkeypatch):
    calls = []

    def unexpected_mutation(*_args, **_kwargs):
        calls.append("mutation")
        raise AssertionError("protected destination must be rejected before mutation")

    monkeypatch.setattr(_BENCHMARK_MODULE.tempfile, "mkdtemp", unexpected_mutation)
    monkeypatch.setattr(Path, "mkdir", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE.os, "replace", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE, "_write_stage4_report_bundle", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE.pd, "read_csv", unexpected_mutation)
    protected_destination = Path(_BENCHMARK_MODULE.__file__).resolve().parents[2] / "reports" / "stage4"
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as error:
        _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
            _synthetic_stage4_records("PROTECTED_DESTINATION"), protected_destination
        )
    assert error.value.code == "INVALID_OUTPUT_LOCATION"
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as lower_error:
        _BENCHMARK_MODULE._publish_staged_bundle(Path("unused-staging"), protected_destination)
    assert lower_error.value.code == "INVALID_OUTPUT_LOCATION"
    assert calls == []


def _synthetic_output_root(monkeypatch, tmp_path):
    """Give one test an isolated synthetic allowed root without environment flags."""
    allowed_root = tmp_path / "synthetic-allowed-root"
    allowed_root.mkdir()
    monkeypatch.setattr(
        _BENCHMARK_MODULE.tempfile, "gettempdir", lambda: str(allowed_root)
    )
    return allowed_root


def _spy_on_publication_mutations(monkeypatch):
    calls = []

    def unexpected_mutation(*_args, **_kwargs):
        calls.append("mutation")
        raise AssertionError("destination rejection must precede publication mutations")

    monkeypatch.setattr(_BENCHMARK_MODULE.tempfile, "mkdtemp", unexpected_mutation)
    monkeypatch.setattr(Path, "mkdir", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE.os, "replace", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE, "_write_stage4_report_bundle", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE.pd, "read_csv", unexpected_mutation)
    return calls


def test_synthetic_publisher_rejects_final_symlink_outside_allowed_root(monkeypatch, tmp_path):
    allowed_root = _synthetic_output_root(monkeypatch, tmp_path)
    outside_target = tmp_path / "synthetic-outside-target"
    outside_target.mkdir()
    sentinel = outside_target / "sentinel.txt"
    sentinel.write_text("synthetic sentinel", encoding="utf-8")
    parent = allowed_root / "reports"
    parent.mkdir()
    destination = parent / "stage4"
    try:
        destination.symlink_to(outside_target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Directory symlink creation is unavailable for this temp fixture: {exc}")

    calls = _spy_on_publication_mutations(monkeypatch)
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as error:
        _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests([], destination)

    assert error.value.code == "INVALID_OUTPUT_LOCATION"
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as lower_error:
        _BENCHMARK_MODULE._publish_staged_bundle(tmp_path / "unused-staging", destination)
    assert lower_error.value.code == "INVALID_OUTPUT_LOCATION"
    assert calls == []
    assert sentinel.read_text(encoding="utf-8") == "synthetic sentinel"
    assert not list(allowed_root.glob(".stage4-staging-*"))
    assert not list(allowed_root.glob(".stage4-backup-*"))


@pytest.mark.skipif(os.name != "nt", reason="Creating a Windows directory junction requires Windows")
def test_synthetic_publisher_rejects_final_junction_outside_allowed_root(monkeypatch, tmp_path):
    allowed_root = _synthetic_output_root(monkeypatch, tmp_path)
    outside_target = tmp_path / "synthetic-junction-target"
    outside_target.mkdir()
    sentinel = outside_target / "sentinel.txt"
    sentinel.write_text("synthetic junction sentinel", encoding="utf-8")
    parent = allowed_root / "reports"
    parent.mkdir()
    destination = parent / "stage4-junction"
    command = f'mklink /J "{destination}" "{outside_target}"'
    created = subprocess.run(
        ["cmd.exe", "/d", "/c", command], capture_output=True, text=True, check=False
    )
    if created.returncode != 0:
        pytest.skip("This Windows filesystem or process cannot create a junction in pytest temp storage")

    try:
        calls = _spy_on_publication_mutations(monkeypatch)
        with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as error:
            _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests(
                [], destination
            )
        assert error.value.code == "INVALID_OUTPUT_LOCATION"
        with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as lower_error:
            _BENCHMARK_MODULE._publish_staged_bundle(tmp_path / "unused-staging", destination)
        assert lower_error.value.code == "INVALID_OUTPUT_LOCATION"
        assert calls == []
        assert sentinel.read_text(encoding="utf-8") == "synthetic junction sentinel"
        assert not list(allowed_root.glob(".stage4-staging-*"))
        assert not list(allowed_root.glob(".stage4-backup-*"))
    finally:
        destination.rmdir()


def test_synthetic_publisher_fails_closed_on_final_component_inspection_error(
    monkeypatch, tmp_path
):
    allowed_root = _synthetic_output_root(monkeypatch, tmp_path)
    parent = allowed_root / "reports"
    parent.mkdir()
    destination = parent / "stage4"

    def inspection_unavailable(_path):
        raise PermissionError("synthetic inspection failure")

    monkeypatch.setattr(
        _BENCHMARK_MODULE, "_inspect_synthetic_destination_component", inspection_unavailable
    )
    calls = _spy_on_publication_mutations(monkeypatch)
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as error:
        _BENCHMARK_MODULE._publish_stage4_reports_unchecked_for_synthetic_tests([], destination)

    assert error.value.code == "INVALID_OUTPUT_LOCATION"
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as lower_error:
        _BENCHMARK_MODULE._publish_staged_bundle(tmp_path / "unused-staging", destination)
    assert lower_error.value.code == "INVALID_OUTPUT_LOCATION"
    assert calls == []
    assert not destination.exists()
    assert not list(allowed_root.glob(".stage4-staging-*"))
    assert not list(allowed_root.glob(".stage4-backup-*"))


def test_windows_reparse_attribute_is_rejected_by_inspection_mock(monkeypatch, tmp_path):
    destination = tmp_path / "synthetic-reparse-point"
    fake_metadata = SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x0400)
    monkeypatch.setattr(_BENCHMARK_MODULE.os, "name", "nt")
    monkeypatch.setattr(Path, "lstat", lambda _path: fake_metadata)

    with pytest.raises(ValueError, match="reparse point"):
        _BENCHMARK_MODULE._inspect_synthetic_destination_component(destination)


def test_public_stage4_publisher_refuses_before_any_mutation(monkeypatch, tmp_path):
    calls = []

    def unexpected_mutation(*_args, **_kwargs):
        calls.append("mutation")
        raise AssertionError("authorization refusal must precede filesystem mutation")

    monkeypatch.setattr(_BENCHMARK_MODULE.tempfile, "mkdtemp", unexpected_mutation)
    monkeypatch.setattr(Path, "mkdir", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE.os, "replace", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE, "_write_stage4_report_bundle", unexpected_mutation)
    monkeypatch.setattr(_BENCHMARK_MODULE.pd, "read_csv", unexpected_mutation)
    with pytest.raises(_BENCHMARK_MODULE.Stage4ReportError) as error:
        _BENCHMARK_MODULE.publish_stage4_reports(
            _synthetic_stage4_records("PUBLIC_REFUSAL"), tmp_path / "reports" / "stage4"
        )
    assert error.value.code == "REAL_AUTHORIZATION_DISABLED"
    assert calls == []


def test_stage4_class_count_preflight_still_rejects_single_class_splits():
    mixed = pd.DataFrame({"label": [0, 1, 0, 1]})
    _BENCHMARK_MODULE.validate_stage4_split_labels("SYNTHETIC", "train", mixed)
    with pytest.raises(ValueError, match="Single class detected"):
        _BENCHMARK_MODULE.validate_stage4_split_labels(
            "SYNTHETIC", "test", pd.DataFrame({"label": [0, 0, 0]})
        )
    undefined = evaluate_predictions(np.array([0, 0]), np.array([0.1, 0.8]))
    assert undefined["result_status"] == "INCOMPLETE_METRICS"
    assert undefined["roc_auc"] is None


def test_within_domain_runner_records_incomplete_single_class_test_result():
    features = ["flow_duration", "flow_bytes_per_sec", "payload_byte_ratio"]
    train = pd.DataFrame({
        "flow_duration": [1., 2., 3., 4., 5., 6., 7., 8.],
        "flow_bytes_per_sec": [10., 20., 30., 40., 50., 60., 70., 80.],
        "payload_byte_ratio": [.1, .2, .1, .2, .8, .9, .8, .9],
        "label": [0, 0, 0, 0, 1, 1, 1, 1],
    })
    validation = train.copy()
    test = pd.DataFrame({
        "flow_duration": [1., 2., 3.],
        "flow_bytes_per_sec": [10., 20., 30.],
        "payload_byte_ratio": [.1, .2, .1],
        "label": [0, 0, 0],
    })
    result = run_within_domain_experiment(
        dataset_name="SYNTHETIC_ONLY",
        feature_profile="synthetic",
        feature_names=features,
        model_name="LogisticRegression",
        train_df=train,
        val_df=validation,
        test_df=test,
    )
    assert result["result_status"] == "INCOMPLETE_METRICS"
    assert result["roc_auc"] is None
    assert result["roc_auc_reason"] == "single_class_labels"
    assert result["accuracy"] is not None


def test_cross_domain_runner_zero_shot():
    feature_names = ["flow_duration", "flow_bytes_per_sec", "payload_byte_ratio"]

    # Source dataset
    src_train = pd.DataFrame({
        "flow_duration": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "flow_bytes_per_sec": [10.0, 20.0, 30.0, 400.0, 500.0, 600.0],
        "payload_byte_ratio": [0.1, 0.1, 0.1, 0.9, 0.9, 0.9],
        "label": [0, 0, 0, 1, 1, 1],
    })
    src_val = src_train.copy()

    # Target dataset
    tgt_test = pd.DataFrame({
        "flow_duration": [1.5, 2.5, 4.5, 5.5],
        "flow_bytes_per_sec": [15.0, 25.0, 450.0, 550.0],
        "payload_byte_ratio": [0.15, 0.15, 0.85, 0.85],
        "label": [0, 0, 1, 1],
    })

    res = run_cross_domain_experiment(
        source_dataset="DomainA",
        target_dataset="DomainB",
        feature_profile="instant_only",
        feature_names=feature_names,
        model_name="LogisticRegression",
        source_train_df=src_train,
        source_val_df=src_val,
        target_test_df=tgt_test,
    )

    assert res["experiment_type"] == "cross_domain"
    assert res["source_dataset"] == "DomainA"
    assert res["target_dataset"] == "DomainB"
    assert res["macro_f1"] > 0.80
    assert res["fpr"] == 0.0
