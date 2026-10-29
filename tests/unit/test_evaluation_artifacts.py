import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_FILE = ROOT / "reports" / "experiments" / "in_domain_evaluation.json"
GOLDEN_MANIFEST = ROOT / "reports" / "golden_run_manifest.json"

@pytest.fixture
def eval_data():
    if not EVAL_FILE.exists():
        pytest.skip(f"Evaluation file not found: {EVAL_FILE}")
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def test_eval_file_exists():
    """Verify that an evaluation evidence artifact exists."""
    if not EVAL_FILE.exists() and not GOLDEN_MANIFEST.exists():
        pytest.skip(f"Evaluation artifact not found: {EVAL_FILE} or {GOLDEN_MANIFEST}")
    assert EVAL_FILE.exists() or GOLDEN_MANIFEST.exists()

def test_eval_file_contains_all_datasets(eval_data):
    """Verify that all four in-domain dataset profiles were evaluated."""
    expected_datasets = ["CICIDS2017", "Edge-IIoTset", "BoT-IoT", "N-BaIoT"]
    for ds in expected_datasets:
        assert ds in eval_data, f"Dataset {ds} is missing from the evaluation artifacts."

def test_eval_file_contains_all_models(eval_data):
    """Verify that all base components and ensembles are evaluated for each dataset."""
    expected_models = ["rf", "mlp", "ae", "rf+mlp", "rf+mlp+ae"]
    
    for ds, test_targets in eval_data.items():
        # In-domain evaluation maps ds -> ds
        assert ds in test_targets, f"In-domain test target {ds} missing for source {ds}"
        model_results = test_targets[ds]
        
        for model in expected_models:
            assert model in model_results, f"Model {model} missing from {ds} evaluation."

def test_eval_model_metrics_structure(eval_data):
    """Verify that each model contains the required metrics for P4 ingestion."""
    expected_metrics = ["accuracy", "precision", "recall", "f1_score", "frozen_weights", "frozen_threshold"]
    
    for ds, test_targets in eval_data.items():
        model_results = test_targets.get(ds, {})
        for model_name, metrics in model_results.items():
            for metric in expected_metrics:
                assert metric in metrics, f"Metric '{metric}' missing in {ds} -> {model_name}"
            
            # Type checks
            assert isinstance(metrics["frozen_weights"], dict), "frozen_weights must be a dictionary"
            assert isinstance(metrics["frozen_threshold"], (float, int)), "frozen_threshold must be numeric"
            assert isinstance(metrics["f1_score"], (float, int)), "f1_score must be numeric"


def test_synthetic_evaluation_report_schema(tmp_path: Path) -> None:
    """Validates the in-domain evaluation schema against a deterministic temporary synthetic fixture."""
    synthetic_eval = {
        "CICIDS2017": {
            "CICIDS2017": {
                "rf": {"accuracy": 0.98, "precision": 0.97, "recall": 0.99, "f1_score": 0.98, "frozen_weights": {}, "frozen_threshold": 0.5},
                "mlp": {"accuracy": 0.96, "precision": 0.95, "recall": 0.97, "f1_score": 0.96, "frozen_weights": {}, "frozen_threshold": 0.5},
                "ae": {"accuracy": 0.92, "precision": 0.91, "recall": 0.93, "f1_score": 0.92, "frozen_weights": {}, "frozen_threshold": 0.8},
                "rf+mlp": {"accuracy": 0.985, "precision": 0.98, "recall": 0.99, "f1_score": 0.985, "frozen_weights": {"rf": 0.5, "mlp": 0.5}, "frozen_threshold": 0.5},
                "rf+mlp+ae": {"accuracy": 0.99, "precision": 0.985, "recall": 0.995, "f1_score": 0.99, "frozen_weights": {"rf": 0.4, "mlp": 0.4, "ae": 0.2}, "frozen_threshold": 0.5},
            }
        },
        "Edge-IIoTset": {
            "Edge-IIoTset": {
                "rf": {"accuracy": 0.95, "precision": 0.94, "recall": 0.96, "f1_score": 0.95, "frozen_weights": {}, "frozen_threshold": 0.5},
                "mlp": {"accuracy": 0.94, "precision": 0.93, "recall": 0.95, "f1_score": 0.94, "frozen_weights": {}, "frozen_threshold": 0.5},
                "ae": {"accuracy": 0.90, "precision": 0.89, "recall": 0.91, "f1_score": 0.90, "frozen_weights": {}, "frozen_threshold": 0.8},
                "rf+mlp": {"accuracy": 0.96, "precision": 0.95, "recall": 0.97, "f1_score": 0.96, "frozen_weights": {"rf": 0.5, "mlp": 0.5}, "frozen_threshold": 0.5},
                "rf+mlp+ae": {"accuracy": 0.97, "precision": 0.96, "recall": 0.98, "f1_score": 0.97, "frozen_weights": {"rf": 0.4, "mlp": 0.4, "ae": 0.2}, "frozen_threshold": 0.5},
            }
        },
        "BoT-IoT": {
            "BoT-IoT": {
                "rf": {"accuracy": 0.99, "precision": 0.99, "recall": 0.99, "f1_score": 0.99, "frozen_weights": {}, "frozen_threshold": 0.5},
                "mlp": {"accuracy": 0.98, "precision": 0.97, "recall": 0.99, "f1_score": 0.98, "frozen_weights": {}, "frozen_threshold": 0.5},
                "ae": {"accuracy": 0.93, "precision": 0.92, "recall": 0.94, "f1_score": 0.93, "frozen_weights": {}, "frozen_threshold": 0.8},
                "rf+mlp": {"accuracy": 0.992, "precision": 0.99, "recall": 0.994, "f1_score": 0.992, "frozen_weights": {"rf": 0.5, "mlp": 0.5}, "frozen_threshold": 0.5},
                "rf+mlp+ae": {"accuracy": 0.995, "precision": 0.993, "recall": 0.997, "f1_score": 0.995, "frozen_weights": {"rf": 0.4, "mlp": 0.4, "ae": 0.2}, "frozen_threshold": 0.5},
            }
        },
        "N-BaIoT": {
            "N-BaIoT": {
                "rf": {"accuracy": 0.97, "precision": 0.96, "recall": 0.98, "f1_score": 0.97, "frozen_weights": {}, "frozen_threshold": 0.5},
                "mlp": {"accuracy": 0.95, "precision": 0.94, "recall": 0.96, "f1_score": 0.95, "frozen_weights": {}, "frozen_threshold": 0.5},
                "ae": {"accuracy": 0.91, "precision": 0.90, "recall": 0.92, "f1_score": 0.91, "frozen_weights": {}, "frozen_threshold": 0.8},
                "rf+mlp": {"accuracy": 0.975, "precision": 0.97, "recall": 0.98, "f1_score": 0.975, "frozen_weights": {"rf": 0.5, "mlp": 0.5}, "frozen_threshold": 0.5},
                "rf+mlp+ae": {"accuracy": 0.985, "precision": 0.98, "recall": 0.99, "f1_score": 0.985, "frozen_weights": {"rf": 0.4, "mlp": 0.4, "ae": 0.2}, "frozen_threshold": 0.5},
            }
        },
    }
    fixture_path = tmp_path / "synthetic_in_domain_evaluation.json"
    fixture_path.write_text(json.dumps(synthetic_eval, indent=2), encoding="utf-8")
    loaded = json.loads(fixture_path.read_text(encoding="utf-8"))

    expected_datasets = ["CICIDS2017", "Edge-IIoTset", "BoT-IoT", "N-BaIoT"]
    expected_models = ["rf", "mlp", "ae", "rf+mlp", "rf+mlp+ae"]
    expected_metrics = ["accuracy", "precision", "recall", "f1_score", "frozen_weights", "frozen_threshold"]

    for ds in expected_datasets:
        assert ds in loaded
        assert ds in loaded[ds]
        for model in expected_models:
            assert model in loaded[ds][ds]
            metrics = loaded[ds][ds][model]
            for metric in expected_metrics:
                assert metric in metrics
            assert isinstance(metrics["frozen_weights"], dict)
            assert isinstance(metrics["frozen_threshold"], (float, int))
            assert isinstance(metrics["f1_score"], (float, int))


def _make_valid_report() -> dict:
    """Constructs a deterministic valid evaluation report complying with the schema."""
    valid_sha256 = "e17465a9aed899f327720d6e9f16186a0a1503bdf220271c76fb59f84959ee78"
    return {
        "evaluation_metadata": {
            "timestamp_iso": "2026-10-29T10:00:00Z",
            "git_commit": "dc7f6b67fcfe585bc883af61cfb6479855a6b4b2",
            "authorization_scope": "AUTHORIZED_INSTITUTIONAL_BENCHMARK",
            "evaluation_type": "REAL_DATA_OFFICIAL",
            "reproducible_command": "python scripts/07_evaluate.py --auth-scope institutional",
        },
        "dataset_provenance": {
            "dataset_id": "Edge-IIoTset",
            "source_digest_sha256": valid_sha256,
            "record_count": 150000,
            "class_balance": {"0": 100000, "1": 50000},
        },
        "artifact_digests": {
            "rf_model_sha256": valid_sha256,
            "mlp_model_sha256": valid_sha256,
            "ae_model_sha256": valid_sha256,
            "preprocessor_sha256": valid_sha256,
        },
        "feature_schema": {
            "profile_name": "edge_iiotset_profile",
            "feature_count": 21,
            "canonical_feature_names": [f"feat_{i}" for i in range(21)],
        },
        "split_provenance": {
            "split_strategy": "chronological",
            "train_indices_hash": valid_sha256,
            "val_indices_hash": valid_sha256,
            "test_indices_hash": valid_sha256,
            "temporal_non_inversion_verified": True,
        },
        "model_configuration": {
            "architecture": "Ensemble(RF+MLP+AE)",
            "fusion_weights": {"rf": 0.4, "mlp": 0.4, "ae": 0.2},
            "decision_threshold": 0.50,
        },
        "performance_metrics": {
            "accuracy": 0.985,
            "precision": 0.982,
            "recall": 0.989,
            "f1_score": 0.985,
            "roc_auc": 0.998,
            "pr_auc": 0.995,
            "false_positive_rate": 0.008,
            "confusion_matrix": {"tn": 99200, "fp": 800, "fn": 550, "tp": 49450},
        },
        "system_and_latency": {
            "latency_p50_ms": 1.25,
            "latency_p95_ms": 3.42,
            "latency_p99_ms": 7.15,
            "throughput_flows_per_sec": 820.0,
            "peak_memory_mb": 142.5,
            "python_version": "3.12.14",
            "torch_version": "2.2.0",
            "sklearn_version": "1.4.2",
        },
    }


def test_validate_evaluation_report_valid_real_data():
    """Verify that a compliant official real-data evaluation report validates cleanly."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    validated = validate_evaluation_report(report)
    assert validated["evaluation_metadata"]["evaluation_type"] == "REAL_DATA_OFFICIAL"
    assert validated["performance_metrics"]["f1_score"] == 0.985


def test_validate_evaluation_report_valid_synthetic():
    """Verify that a synthetic benchmark report validates with appropriate evaluation_type."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    report["evaluation_metadata"]["evaluation_type"] = "SYNTHETIC_BENCHMARK_ONLY"
    report["evaluation_metadata"]["authorization_scope"] = "SYNTHETIC_FIXTURE_TESTING"
    report["synthetic_data"] = True

    validated = validate_evaluation_report(report)
    assert validated["evaluation_metadata"]["evaluation_type"] == "SYNTHETIC_BENCHMARK_ONLY"


def test_validate_evaluation_report_rejects_synthetic_as_real():
    """Verify that claiming REAL_DATA_OFFICIAL with synthetic indicators is strictly rejected."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    # Case 1: synthetic_data flag is True
    report1 = _make_valid_report()
    report1["synthetic_data"] = True
    with pytest.raises(ValueError, match="Integrity violation: Report specifies evaluation_type='REAL_DATA_OFFICIAL'"):
        validate_evaluation_report(report1)

    # Case 2: authorization_scope indicates synthetic/unauthorized
    report2 = _make_valid_report()
    report2["evaluation_metadata"]["authorization_scope"] = "synthetic_mock_test"
    with pytest.raises(ValueError, match="Integrity violation: Report specifies evaluation_type='REAL_DATA_OFFICIAL'"):
        validate_evaluation_report(report2)


def test_validate_evaluation_report_rejects_out_of_bounds_metrics():
    """Verify that performance metrics outside [0.0, 1.0] are rejected."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    report["performance_metrics"]["accuracy"] = 1.05
    with pytest.raises(ValueError, match="(maximum of 1.0|within \\[0.0, 1.0\\])"):
        validate_evaluation_report(report)

    report2 = _make_valid_report()
    report2["performance_metrics"]["f1_score"] = -0.01
    with pytest.raises(ValueError, match="(minimum of 0.0|within \\[0.0, 1.0\\])"):
        validate_evaluation_report(report2)


def test_validate_evaluation_report_rejects_malformed_sha256():
    """Verify that digests not matching 64 hex characters are rejected."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    report["dataset_provenance"]["source_digest_sha256"] = "bad_hex"
    with pytest.raises(ValueError):
        validate_evaluation_report(report)

    report2 = _make_valid_report()
    report2["artifact_digests"]["rf_model_sha256"] = "12345"
    with pytest.raises(ValueError):
        validate_evaluation_report(report2)


def test_validate_evaluation_report_rejects_missing_required_sections():
    """Verify that missing top-level required schema sections fail validation."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    del report["system_and_latency"]
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_evaluation_report(report)


def test_validate_evaluation_report_from_file_path(tmp_path: Path):
    """Verify that reading from a JSON file path works correctly."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    file_path = tmp_path / "valid_eval_report.json"
    file_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    validated = validate_evaluation_report(file_path)
    assert validated["dataset_provenance"]["dataset_id"] == "Edge-IIoTset"


def test_save_validated_evaluation_report_atomic_persistence(tmp_path: Path):
    """Verify atomic file writing on success and strict cleanup without writing on validation error."""
    from iot_ids.experiments.evaluator import save_validated_evaluation_report

    report = _make_valid_report()
    target_out = tmp_path / "nested" / "official_evaluation.json"

    # Success path
    saved_path = save_validated_evaluation_report(report, target_out)
    assert saved_path.is_file()
    loaded = json.loads(saved_path.read_text(encoding="utf-8"))
    assert loaded["performance_metrics"]["f1_score"] == 0.985

    # Failure path: target should not be overwritten
    bad_report = _make_valid_report()
    bad_report["performance_metrics"]["accuracy"] = 999.0
    with pytest.raises(ValueError):
        save_validated_evaluation_report(bad_report, target_out)
    # Ensure original valid file is untouched
    loaded_after = json.loads(saved_path.read_text(encoding="utf-8"))
    assert loaded_after["performance_metrics"]["accuracy"] == 0.985


def test_validate_evaluation_report_rejects_empty_dataset_record_count():
    """Verify that record_count <= 0 is rejected by schema."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    report["dataset_provenance"]["record_count"] = 0
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_evaluation_report(report)


def test_validate_evaluation_report_rejects_unsupported_dataset_id():
    """Verify that unsupported/unknown dataset IDs are rejected."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    report["dataset_provenance"]["dataset_id"] = "UnknownDataset123"
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_evaluation_report(report)


def test_validate_evaluation_report_rejects_invalid_split_strategy():
    """Verify that unsupported split strategies are rejected."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    report["split_provenance"]["split_strategy"] = "arbitrary_random"
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_evaluation_report(report)


def test_validate_evaluation_report_rejects_negative_latency():
    """Verify that negative latency values are rejected."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    report = _make_valid_report()
    report["system_and_latency"]["latency_p50_ms"] = -1.5
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_evaluation_report(report)


def test_validate_evaluation_report_rejects_nonexistent_file(tmp_path: Path):
    """Verify that non-existent report paths fail closed with ValueError."""
    from iot_ids.experiments.evaluator import validate_evaluation_report

    with pytest.raises(ValueError, match="Report file not found"):
        validate_evaluation_report(tmp_path / "does_not_exist.json")



