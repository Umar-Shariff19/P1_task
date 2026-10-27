"""Synthetic-only regression tests for the real-data refusal boundary.

The tests inspect source placement and invoke a bounded set of blocked entry
points with operation spies. They never supply a research-data path.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pandas as pd
import pytest

from iot_ids.provenance.windows_access import (
    RealDataAuthorizationUnavailable,
    require_real_data_authorization,
)


REPO_ROOT = Path(__file__).resolve().parents[2]

GUARDED_MODULE_ENTRYPOINTS = (
    "scripts/build_final_overleaf_package.py",
    "scripts/build_fixed_overleaf_package.py",
    "scripts/build_manual_editing_overleaf_zip.py",
    "scripts/build_overleaf_package.py",
    "scripts/build_p1_task_implementation_zip.py",
    "scripts/finalize_zip_and_hashes.py",
    "scripts/generate_final_paper_figures.py",
    "scripts/generate_paper_draft_figures.py",
    "scripts/generate_paper_figures_v2.py",
    "scripts/generate_redesigned_paper_figures.py",
)

# These project-owned command paths were identified by static search for data,
# split, checkpoint, training/evaluation, dispatch, and protected-report I/O.
# The listed callable must refuse before its first external side effect.
GUARDED_CALLABLES = {
    "scripts/01_materialize.py": ("main",),
    "scripts/01_materialize_canonical_flows.py": ("run_stage1_validation",),
    "scripts/02_audit_canonical_features.py": ("main", "audit_dataset_features"),
    "scripts/02_validate_materialization.py": ("main",),
    "scripts/03_create_splits.py": ("main",),
    "scripts/03_materialize_and_audit_features.py": ("materialize_dataset", "run_stage3_audit"),
    "scripts/04_analyze_ablations.py": ("analyze_ablations",),
    "scripts/04_generate_stage4_plots.py": ("generate_plots",),
    "scripts/04_validate_splits.py": ("main",),
    "scripts/05_analyze_adaptation.py": ("analyze_adaptation",),
    "scripts/05_domain_adaptation.py": ("load_dataset_splits", "run_stage5_benchmarks"),
    "scripts/05_generate_stage5_plots.py": ("generate_plots",),
    "scripts/05_run_validity_audit.py": ("run_validity_audit",),
    "scripts/05_train_models.py": ("main",),
    "scripts/06_calibrate_risk.py": ("main",),
    "scripts/06_generate_stage6_plots.py": ("generate_plots",),
    "scripts/06_statistical_robustness.py": ("load_dataset_splits", "run_stage6_statistical_robustness"),
    "scripts/07_evaluate.py": ("main",),
    "scripts/07_generate_claim_evidence_matrix.py": ("generate_claim_evidence_matrix",),
    "scripts/08_generate_evidence.py": ("main",),
    "scripts/09_generate_xai_evidence.py": ("main",),
    "scripts/10_run_adversarial_evaluation.py": ("main",),
    "scripts/11_run_federated_experiments.py": ("load_dataset_splits", "main"),
    "scripts/12_run_shap_experiments.py": ("main",),
    "scripts/13_run_adversarial_training.py": ("main",),
    "scripts/14_run_ensemble_experiments.py": ("main",),
    "scripts/15_adaptive_ensemble_attack.py": ("main",),
    "scripts/16_xai_attack_breakdown.py": ("main",),
    "scripts/17_bootstrap_confidence_intervals.py": ("main",),
    "scripts/18_fusion_weight_ablation.py": ("main",),
    "scripts/24_build_authoritative_numerical_ledger.py": ("main",),
    "scripts/04_run_benchmarks.py": ("run_benchmarks", "load_dataset_splits"),
    "scripts/benchmark_runtime_xai_privacy.py": ("main",),
    "scripts/audit_datasets.py": (),
    "scripts/evaluate_cross_domain.py": ("get_parquet_files", "get_drop_indices", "load_split", "get_component_predictions", "run"),
    "scripts/evaluate_v2.py": ("get_parquet_files", "get_drop_indices", "load_split", "get_component_predictions", "run"),
    "scripts/export_deployable_model.py": ("load_dataset_split", "export_deployable_model_artifact"),
    "scripts/generate_milestone2_reports.py": ("main",),
    "scripts/generate_publication_evidence.py": ("run",),
    "scripts/generate_xai_experiments.py": ("load_dataset_samples", "main"),
    "scripts/run_golden_pipeline.py": ("main",),
    "scripts/run_master.py": ("load_registry", "save_registry", "run_script"),
    "scripts/run_milestone3a.py": ("disk_backed_deduplication", "validate_dataset", "run"),
    "scripts/run_privacy_experiments.py": ("load_evaluation_samples", "main"),
    "scripts/train_ae.py": ("get_parquet_files", "get_drop_indices", "load_benign_train", "load_full_split", "train_ae", "run"),
    "scripts/train_mlp.py": ("get_parquet_files", "get_drop_indices", "load_full_split", "train_mlp", "run"),
    "scripts/train_rf.py": ("get_parquet_files", "get_drop_indices", "load_split", "train_rf", "run"),
    "scripts/validate_edge_deployment.py": ("validate_edge_deployment",),
    "scripts/validate_milestone2_5.py": ("run_benchmark", "main"),
    "scripts/validate_real_inference.py": ("validate_real_inference",),
}


def _load_script(relative_path: str, module_name: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_common_real_data_guard_is_typed_stable_and_path_free():
    with pytest.raises(RealDataAuthorizationUnavailable) as exc:
        require_real_data_authorization()
    assert exc.value.code.value == "REAL_AUTHORIZATION_DISABLED"
    assert "path" not in str(exc.value).lower()


@pytest.mark.parametrize("relative_path,names", list(GUARDED_CALLABLES.items()))
def test_identified_entrypoints_call_guard_before_their_body(relative_path, names):
    """AST placement check across the bounded script inventory; no code executes."""
    path = REPO_ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative_path)
    if not names:
        dispatch = next(
            node for node in tree.body
            if isinstance(node, ast.If) and ast.unparse(node.test) == "__name__ == '__main__'"
        )
        body = dispatch.body
        assert len(body) >= 2
        assert isinstance(body[0], ast.ImportFrom)
        assert body[0].module == "iot_ids.provenance.windows_access"
        assert isinstance(body[1], ast.Expr)
        assert isinstance(body[1].value, ast.Call)
        assert ast.unparse(body[1].value.func) == "require_real_data_authorization"
        return

    functions = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in names
    }
    assert set(names) <= set(functions)
    for name in names:
        node = functions[name]
        body = list(node.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body.pop(0)
        if isinstance(body[0], ast.ImportFrom):
            assert body[0].module == "iot_ids.provenance.windows_access", (relative_path, name)
            body.pop(0)
        assert isinstance(body[0], ast.Expr), (relative_path, name)
        assert ast.unparse(body[0].value.func) == "require_real_data_authorization", (relative_path, name)


@pytest.mark.parametrize("relative_path", GUARDED_MODULE_ENTRYPOINTS)
def test_module_level_report_packagers_refuse_before_side_effects(relative_path):
    tree = ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"), filename=relative_path)
    first_operation = next(
        node for node in tree.body
        if not isinstance(node, (ast.Import, ast.ImportFrom))
        and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))
    )
    assert isinstance(first_operation, ast.Expr), relative_path
    assert ast.unparse(first_operation.value.func) == "require_real_data_authorization", relative_path


def test_stage4_runner_refuses_before_reads_or_output_creation(monkeypatch):
    module = _load_script("scripts/04_benchmark_models.py", "_guard_stage4")
    calls = []

    def touched(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("protected operation reached before refusal")

    monkeypatch.setattr(module.pd, "read_parquet", touched)
    monkeypatch.setattr(Path, "mkdir", touched)
    with pytest.raises(module.Stage4ReportError) as exc:
        module.run_stage4_benchmarks()
    assert exc.value.code == "REAL_AUTHORIZATION_DISABLED"
    assert calls == []


def test_stage4_direct_split_loader_refuses_before_parquet_read(monkeypatch, tmp_path):
    module = _load_script("scripts/04_benchmark_models.py", "_guard_stage4_loader")
    calls = []
    monkeypatch.setattr(module.pd, "read_parquet", lambda *a, **k: calls.append((a, k)))
    with pytest.raises(module.Stage4ReportError) as exc:
        module.load_dataset_splits(tmp_path, "synthetic")
    assert exc.value.code == "REAL_AUTHORIZATION_DISABLED"
    assert calls == []


def test_direct_stage4_report_publisher_refuses_before_staging(monkeypatch, tmp_path):
    module = _load_script("scripts/04_benchmark_models.py", "_guard_stage4_publisher")
    calls = []
    monkeypatch.setattr(module.tempfile, "mkdtemp", lambda *a, **k: calls.append("staging"))
    output = tmp_path / "reports" / "stage4"
    with pytest.raises(module.Stage4ReportError) as exc:
        module.publish_stage4_reports([], output)
    assert exc.value.code == "REAL_AUTHORIZATION_DISABLED"
    assert calls == []
    assert not output.exists()


def test_direct_split_loader_refuses_before_parquet_read(monkeypatch, tmp_path):
    module = _load_script("scripts/05_domain_adaptation.py", "_guard_stage5")
    calls = []
    monkeypatch.setattr(module.pd, "read_parquet", lambda *a, **k: calls.append((a, k)))
    with pytest.raises(RealDataAuthorizationUnavailable):
        module.load_dataset_splits(tmp_path, "synthetic")
    assert calls == []


def test_adapter_discovery_refuses_before_directory_enumeration(monkeypatch, tmp_path):
    from iot_ids.data.adapters.ciciot2023 import CICIoT2023Adapter

    calls = []
    monkeypatch.setattr(Path, "rglob", lambda *a, **k: calls.append((a, k)))
    with pytest.raises(RealDataAuthorizationUnavailable):
        CICIoT2023Adapter(tmp_path).get_source_files()
    assert calls == []


def test_materializer_refuses_before_adapter_construction_or_output(monkeypatch, tmp_path):
    from iot_ids.data import materialize

    calls = []
    monkeypatch.setattr(materialize, "build_default_adapters", lambda *a, **k: calls.append("adapter"))
    with pytest.raises(RealDataAuthorizationUnavailable):
        materialize.materialize_dataset("SYNTHETIC", tmp_path, tmp_path / "out")
    assert calls == []
    assert not (tmp_path / "out").exists()


def test_production_inference_constructor_refuses_before_checkpoint_load(monkeypatch):
    from iot_ids.runtime.engine import InferenceEngine
    import iot_ids.runtime.engine as engine_module

    calls = []
    monkeypatch.setattr(engine_module.joblib, "load", lambda *a, **k: calls.append("joblib"))
    monkeypatch.setattr(engine_module.torch, "load", lambda *a, **k: calls.append("torch"))
    with pytest.raises(RealDataAuthorizationUnavailable):
        InferenceEngine()
    assert calls == []


def test_model_registry_refuses_before_artifact_read_or_write(monkeypatch, tmp_path):
    from iot_ids.registry.manager import ModelRegistry

    calls = []
    monkeypatch.setattr(Path, "mkdir", lambda *a, **k: calls.append("mkdir"))
    monkeypatch.setattr(Path, "open", lambda *a, **k: calls.append("open"))
    with pytest.raises(RealDataAuthorizationUnavailable):
        ModelRegistry.save_pipeline(None, tmp_path / "artifact")
    with pytest.raises(RealDataAuthorizationUnavailable):
        ModelRegistry.load_pipeline(tmp_path / "artifact")
    assert calls == []
    assert not (tmp_path / "artifact").exists()


def test_cli_train_refuses_before_training_or_file_reads(monkeypatch):
    import iot_ids.cli as cli

    calls = []
    monkeypatch.setattr(sys, "argv", ["iot-ids", "train"])
    monkeypatch.setattr(cli, "train_and_export_pipeline", lambda *a, **k: calls.append("train"))
    monkeypatch.setattr(cli.pd, "read_parquet", lambda *a, **k: calls.append("read"))
    with pytest.raises(RealDataAuthorizationUnavailable):
        cli.main()
    assert calls == []
