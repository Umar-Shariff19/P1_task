# Baseline Snapshot: Multi-Level IoT IDS

**Timestamp**: 2026-10-29T09:23:00+05:30  
**Repository**: `C:\Users\umari\Documents\P1_task_Implementation`  
**Git Branch**: `fix/registry-authorization-tests`  
**Git Commit**: `dc7f6b67fcfe585bc883af61cfb6479855a6b4b2`  
**Execution Environment**: Python 3.12.14 (`.venv\Scripts\python.exe`), Pytest 8.4.2, Scapy 2.7.0, Torch 2.2+, Scikit-Learn 1.4+  

---

## 1. Initial Test Suite Execution

- **Command**: `.\.venv\Scripts\python.exe -m pytest -rs`
- **Exit Code**: `0`
- **Duration**: `46.02s`
- **Total Collected**: `443 items`
- **Passed**: `383`
- **Skipped**: `60`
- **Failed**: `0`
- **Warnings**: `21`

---

## 2. Skipped Test Breakdown (60 Tests)

1. **Requires Authorized Real-Data Credentials (49 Tests)**:
   - Protected by `require_real_data_authorization()` failing closed with `RealDataAuthorizationUnavailable`.
   - `tests/integration/test_audit_cli.py`: 1 test
   - `tests/integration/test_edge_production_hardening_e2e.py`: 1 test
   - `tests/integration/test_end_to_end_runtime.py`: 20 tests
   - `tests/integration/test_operational_cli_e2e.py`: 3 tests
   - `tests/integration/test_pcap_and_live_ingress_e2e.py`: 3 tests
   - `tests/integration/test_runtime_daemon_e2e.py`: 4 tests
   - `tests/integration/test_stateful_behavior.py`: 1 test
   - `tests/integration/test_xai_privacy_runtime_integration.py`: 1 test
   - `tests/unit/data/test_adapters.py`: 1 test
   - `tests/unit/experiments/test_stage4_benchmark.py`: 1 test
   - `tests/unit/test_demo.py`: 1 test
   - `tests/unit/test_package_and_security.py`: 1 test
   - `tests/unit/test_runtime_engine.py`: 11 tests

2. **Requires Elevated Windows Filesystem Privileges (8 Tests)**:
   - Raised `[WinError 1314] A required privilege is not held by the client` or junction unsupported in unprivileged pytest temp storage.
   - `tests/unit/data/test_path_policy.py`: 1 test
   - `tests/unit/experiments/test_experiments.py`: 2 tests
   - `tests/unit/test_artifact_integrity.py`: 1 test
   - `tests/unit/test_windows_access.py`: 3 tests
   - `tests/unit/test_windows_root.py`: 1 test

3. **Missing Historical Evaluation Report (3 Tests)**:
   - `reports/experiments/in_domain_evaluation.json` not found because full real-data evaluation has not run in this checkout.
   - `tests/unit/test_evaluation_artifacts.py`: 3 tests

---

## 3. Warning Categories (21 Warnings)

1. **Internal Deprecation (1)**:
   - `src/iot_ids/data/materialize.py:12`: `from iot_ids.features.canonical.builder import build_canonical_features`. Needs migration to `CanonicalFlowBuilder`.
2. **Python 3.12 Escape Sequence Syntax Warnings (7)**:
   - Unescaped LaTeX/regex backslashes (`\e`, `\g`, `\m`, `\d`, `\s`, `\@`) in scripts (`scripts/10_run_adversarial_evaluation.py`, `scripts/11_run_federated_experiments.py`, `scripts/24_build_authoritative_numerical_ledger.py`, `scripts/build_fixed_overleaf_package.py`, `scripts/generate_paper_figures_v2.py`).
3. **PyTorch JIT Deprecations (6)**:
   - `torch.jit.script` deprecation in `tests/unit/test_mlp_loader.py`.
4. **PyTorch TorchScript Archive UserWarning (1)**:
   - `torch.load` receiving TorchScript archive during scripted model rejection test in `src/iot_ids/runtime/engine.py:328`.
5. **SHAP Colormap Deprecations (3)**:
   - `set_bad`, `set_over`, `set_under` in `shap/plots/colors/_colors.py` called during `test_runtime_synthetic_workflow.py`.
6. **Joblib Loky Physical Cores UserWarning (1)**:
   - Windows physical core detection fallback to logical cores in `test_quality_and_splits.py`.
7. **Pytest Cache Permissions (2)**:
   - Permission denied writing to `.pytest_cache` in repository root due to Windows Administrator ownership.

---

## 4. Tracked and Untracked Working Tree State

- Working tree contains pre-existing modified files from prior sprints (including `sinks.py`, `engine.py`, `predictor.py`, `test_alert_delivery.py`, etc.).
- Untracked files include master audit reports and previous verification tests.
- All pre-existing work will be strictly preserved.
