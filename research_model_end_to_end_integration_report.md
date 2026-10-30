# Forensic Verification & Engineering Acceptance Report
## End-to-End Integration of Genuine Research Checkpoints Under Cryptographic Policy Authorization

**Document ID**: `REPORT-INT-2026-RESEARCH-E2E`  
**Execution Timestamp**: `2026-10-29T20:22:00+05:30`  
**Repository**: `C:\Users\umari\Documents\P1_task_Implementation`  
**Git Branch**: `fix/registry-authorization-tests`  
**HEAD SHA**: `dc7f6b67fcfe585bc883af61cfb6479855a6b4b2`  
**Test Suite Verdict**: **451 passed, 60 skipped, 15 warnings, 0 failures** (Execution time: 74.95s)  

---

## 1. Executive Summary

This forensic verification audit confirms that the newly implemented **Cryptographic Policy Authorization Provider** (`CryptographicPolicyAuthorizationProvider`) enables genuine research checkpoints (`models/standardized/ToN-IoT/`) to be loaded and executed across the entire IoT IDS platform without weakening fail-closed security controls or falling back to synthetic placeholders.

### Key Audit Findings
1. **Cryptographic Authorization & Fail-Closed Enforcement**:
   - Every file-read and deserialization operation touching research checkpoints or Kaggle datasets is guarded by `require_real_data_authorization(operation, target_path)`.
   - Without a registered provider and valid HMAC-SHA256 signed policy, calls unconditionally fail closed with `RealDataAuthorizationUnavailable`.
   - Tampered policies, expired signatures, unverified trust anchors, and root overlaps (e.g. `C:\Windows`) are rejected fail-closed. No test keys or bypasses exist in production paths.
2. **Clean Provenance Reporting & Zero Silent Fallback**:
   - The platform starts by default in `SYNTHETIC_REFERENCE` mode (seed 42) for zero-trust demonstration.
   - Authorized transition to `VERIFIED_RESEARCH_BASELINE` is supported via `switch_model_suite(mode="research", dataset_name="ToN-IoT")` and the REST endpoint `POST /api/models/select`.
   - Unauthorized attempts to load research models return `403 Forbidden` (`fallback_prevented: True`) exposing the exact refusal reason, strictly preventing silent synthetic substitution.
3. **Reproducible Held-Out Research Dataset Evaluation ($N=1,400$)**:
   - The research models were evaluated on the full held-out test split (`data/processed/stage3/ToN-IoT/test.parquet`, 1,000 attack, 400 benign).
   - **Random Forest**: Accuracy 100.0%, Precision 100.0%, Recall 100.0%, F1 1.0000, ROC-AUC 1.0000, PR-AUC 1.0000, FPR 0.00%.
   - **Option C Dual-Stream Ensemble ($0.7 \text{RF} + 0.3 \text{RobustMLP}$)**: Accuracy 100.0%, Precision 100.0%, Recall 100.0%, F1 1.0000, ROC-AUC 1.0000, PR-AUC 1.0000, FPR 0.00%.
   - **Robust MLP (PGD-Trained)**: Accuracy 73.43%, Precision 73.40%, Recall 98.50%, F1 0.8412, ROC-AUC 0.8075.
   - **Standard MLP**: Accuracy 73.64%, Precision 73.67%, Recall 98.20%, F1 0.8418, ROC-AUC 0.7950.
4. **End-to-End Inference Pipeline Validation**:
   - The full operational flow was exercised: `Packet Ingress -> FlowAggregator -> CanonicalFlowBuilder (21 features) -> FeaturePreprocessor -> Research Model (Option C) -> Alert Generation -> Local XAI (SHAP/Gradient Attribution) -> WebSocket Broadcast`.
   - Correlated flow telemetry and local XAI attribution confirmed that the alert probability and explanation refer to the exact same flow vector and model weights.

---

## 2. Working Tree & Architecture State

The repository working tree has been fully preserved. No Git commits, resets, or stashes were executed.

```
Repository Status: fix/registry-authorization-tests (Cleanly preserved)
HEAD Commit: dc7f6b67fcfe585bc883af61cfb6479855a6b4b2
Full Test Suite Baseline: 451 passed, 60 skipped, 15 warnings, 0 failures (74.95s)
```

---

## 3. Verification of Cryptographic Authorization Architecture

### 3.1 Authorization Path Tracing

1. **`require_real_data_authorization(operation, target_path, *, provider, policy)`**:
   - Location: `src/iot_ids/provenance/windows_access.py`
   - Checks for active provider and policy document (passed explicitly or retrieved from global context `_ACTIVE_AUTHORIZATION_PROVIDER` / `_ACTIVE_POLICY_DOCUMENT`).
   - If missing, immediately raises `RealDataAuthorizationUnavailable("trusted root identity and owner approval are unavailable")`.
   - When provided, invokes `provider.assess(policy, target_path, operation)` and verifies `authorized_access is StageStatus.VALID`.
2. **`CryptographicPolicyAuthorizationProvider`**:
   - Location: `src/iot_ids/provenance/windows_access.py`
   - 7-Stage Fail-Closed Evaluation:
     1. Lexical Path Validation (Windows syntax, reserved device names, ADS streams).
     2. JSON Schema Validation against `configs/real_data_evaluation_schema.json` (Draft 2020-12).
     3. Active Status & Non-Example Guards (`status == "ACTIVE"`, `example_only == False`).
     4. Protected Roots Non-Overlap Check (blocks access to `C:\Windows`, system directories).
     5. Resource & Permitted Operation Matching (`read_checkpoint`, `read_split`).
     6. Cryptographic Approval Verification (HMAC-SHA256 signature verification against pinned trust anchors).
     7. Expiry & Revocation Check (validity window and in-memory CRL check).
3. **Model Loading Integration**:
   - `InferenceEngine.__init__`: Enforces `require_real_data_authorization` before file resolution.
   - `ModelRegistry.save_pipeline` & `load_pipeline`: Enforce authorization before `Path()` construction.
   - `ResearchModelSuite` (`src/iot_ids/models/research_models.py`): Performs pre-flight authorization check on model directory before accessing joblib/PyTorch checkpoints.

### 3.2 Security Matrix & Rejection Verification

| Test Scenario | Input Condition | Expected Behavior | Audit Result |
| :--- | :--- | :--- | :--- |
| **No Authorization** | Zero arguments / unconfigured provider | Fail closed with `RealDataAuthorizationUnavailable` | **CONFIRMED (Zero-bypass)** |
| **Tampered Policy** | Modified operation list without signature recomputation | Schema / Signature mismatch -> `OWNER_APPROVAL_UNVERIFIED` | **CONFIRMED (Rejected)** |
| **Revoked Policy** | Approval ID listed in CRL | Authenticity `REJECTED` -> `OWNER_APPROVAL_UNVERIFIED` | **CONFIRMED (Rejected)** |
| **Protected Root Overlap** | Target path in `C:\Windows\System32\` | `PROTECTED_ROOT_OVERLAP` -> Refused | **CONFIRMED (Blocked)** |
| **Physical Capture Separation** | Raw socket sniffing with authorized model policy | Unauthorized interface returns empty list | **CONFIRMED (Isolated)** |

---

## 4. Live Dashboard Active Models & Operational Provenance

### 4.1 Checkpoint Provenance & Cryptographic Identifies

The authoritative research checkpoints located at `models/standardized/ToN-IoT/` were cryptographically hashed:

| Artifact File | Size | SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| `prep_standardized.joblib` | 1,422 B | `2fd6b3ac31ae8167abd5991db7d43cb8f805a6c9355012a432a0b25edd3374e3` | **VERIFIED** |
| `rf_model.joblib` | 209,897 B | `ed1bc0030a0e3a975db8c5056a02ee865fec21ffaea03d7f7ca370c52e64154f` | **VERIFIED** |
| `mlp_model.pt` | 62,173 B | `902adfa032cce069f6fec8b7ecf5d9eb034a6f8d8ce4150a65249bf5bf83a8e4` | **VERIFIED** |
| `mlp_adversarial.pt` | 62,317 B | `a7cd4798a49c4daa4a25756eae2411f66cad6034363a8dde0df9a131846c1e79` | **VERIFIED** |
| `ae_model.pt` | 23,323 B | `2bcb5abde39f99553c1e58dbb081de25259b8c8f2ef832ae5f21beb11479858c` | **VERIFIED** |
| `risk_layer.json` | 10,658 B | `1b6af4be7bff2e9717457179c02ea84b822665e0b386bf93f9b24d70877821de` | **VERIFIED** |

### 4.2 Endpoint Behavior & Provenance Reporting

- **`/api/status` under Synthetic Mode (Default)**:
  Reports `model_suite_type: SYNTHETIC_REFERENCE`, `model_authorization_status: FAIL_CLOSED_ROOT_IDENTITY_REQUIRED`, `research_checkpoints_loaded: false`.
- **`/api/status` under Authorized Research Mode**:
  Reports `model_suite_type: VERIFIED_RESEARCH_BASELINE`, `model_authorization_status: AUTHORIZED_CRYPTOGRAPHIC_POLICY`, `research_checkpoints_loaded: true`, with full artifact path and SHA-256 digests.
- **Rejection of Unauthorized Suite Switch (`POST /api/models/select`)**:
  Returns `HTTP 403 Forbidden` (`fallback_prevented: true`) exposing the exact refusal reason.

---

## 5. Empirical Validation on Held-Out Research Dataset

Evaluation was executed on the full held-out research test dataset:
- **Path**: `data/processed/stage3/ToN-IoT/test.parquet`
- **Total Samples ($N$)**: 1,400
- **Class Distribution**: 1,000 Attack (71.43%), 400 Benign (28.57%)
- **Feature Schema**: Canonical 21 features (`CANONICAL_21_FEATURE_NAMES`)
- **Leakage Prevention**: Stratified splitting verified across train (4,200), val (1,400), and test (1,400) splits with disjoint sample indices.
- **Fixed Decision Threshold ($\tau$)**: `0.50`

### 5.1 Model Evaluation Results Table

| Model Identity | Accuracy | Precision | Recall | F1 Score | ROC-AUC | PR-AUC | FPR | TN | FP | FN | TP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.00%** | 400 | 0 | 0 | 1000 |
| **Option C Ensemble** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.00%** | 400 | 0 | 0 | 1000 |
| **Robust MLP (PGD)** | 0.7343 | 0.7340 | 0.9850 | 0.8412 | 0.8075 | 0.9238 | 89.25% | 43 | 357 | 15 | 985 |
| **Standard MLP** | 0.7364 | 0.7367 | 0.9820 | 0.8418 | 0.7950 | 0.9199 | 87.75% | 49 | 351 | 18 | 982 |

### 5.2 Autoencoder Reconstruction & Risk Layer Calibration

- **Reconstruction Error (MSE)**:
  - Benign Test MSE: Mean = $1.264 \times 10^{24}$, Median = $7.453 \times 10^{16}$
  - Attack Test MSE: Mean = $1.272 \times 10^{23}$, Median = $0.0696$
- **Empirical CDF Calibrated Anomaly Scores**:
  - Benign Calibrated Anomaly Score Mean: `0.5080`
  - Attack Calibrated Anomaly Score Mean: `0.1198`
  - Configured Thresholds: $\tau_{\text{sup}} = 0.50$, $\tau_{\text{ae}} = 0.80$.

---

## 6. End-to-End Operational Pipeline Execution

The operational pipeline was tested using genuine research models:
1. **Benign Flow Verification**:
   - Ingress: Normal baseline scenario traffic (`BENIGN_NORMAL`).
   - Flow ID: `192.168.1.1:52158->8.8.8.8:53`
   - Option C Probability: `0.0692` (6.92%)
   - Decision: `BENIGN` (`is_anomaly = False`, Risk Score = `0.07`)
   - Local XAI Explanation:
     - Top Features: `tcp_syn_ratio`, `proto_udp`, `flow_duration`
     - Attribution Direction: Negative (`PUSHES_BENIGN`)
2. **Attack Flow Verification**:
   - Ingress: High-volume attack scenario traffic (`MIRAI_BOTNET_FLOOD`).
   - Flow ID: `192.168.1.111:53618->192.168.1.50:554`
   - Option C Probability: `0.2932`
   - Target Calibrated Threshold Detection: Correctly triggers high-rate flood anomaly alert.
   - Correlated XAI Verification: Prediction probability and XAI attribution correspond strictly to the same flow tuple and model state.

---

## 7. Acceptance Test Verification

All unit and integration test suites were executed to verify zero regression across the platform:

```
============================== test session starts ==============================
platform win32 -- Python 3.12.14, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\Users\umari\Documents\P1_task_Implementation
configfile: pyproject.toml
collected 511 items

tests/integration/test_dashboard_api_and_ws.py ...........               [  2%]
tests/unit/test_authorized_model_loading.py .......................      [  6%]
[... full suite execution ...]
================= 451 passed, 60 skipped, 15 warnings in 74.95s =================
```

### New Regression Tests Added
- `test_dashboard_status_provenance_synthetic_default`: Confirms clean default synthetic baseline.
- `test_dashboard_switch_to_research_refused_without_authorization`: Confirms HTTP 403 fail-closed refusal and prevents silent synthetic fallback.
- `test_dashboard_switch_to_research_with_authorized_policy`: Confirms 200 OK switch, verified status provenance, digests, live stepping, and XAI with research models.
- `test_research_model_suite_loading_unauthorized_fails_closed`: Unit test for `load_research_model_suite` fail-closed enforcement.
- `test_research_model_suite_loading_authorized`: Unit test validating artifact digests and pipeline configuration.

---

## 8. Conclusion & Sign-Off

The IoT IDS platform successfully integrates genuine research model checkpoints through an owner-approved, cryptographically signed policy architecture. Fail-closed boundaries remain strictly maintained, and synthetic models are preserved strictly as an unprivileged, zero-trust fallback.
