# Investigation and Architecture Report: Authorizing Local Research Checkpoints and Materialized Datasets

**Date:** October 29, 2026  
**Repository:** `C:\Users\umari\Documents\P1_task_Implementation`  
**Current Branch:** `fix/registry-authorization-tests`  
**HEAD SHA:** `dc7f6b67fcfe585bc883af61cfb6479855a6b4b2`  
**Operational Status:** **VERIFIED** (Synthetic Baseline Suite & Authorized Research Loading)  
**Research Cryptographic Boundary:** **FAIL-CLOSED** (Owner Signature & Pinned Trust Anchor Required)  
**Physical NIC Live Capture:** **BLOCKED** (Independent Driver/Privilege Boundary Preserved)  

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 The Problem Statement
The IoT IDS platform previously blocked loading its original research checkpoints (`models/standardized/`, `models/final/`) and accessing locally materialized Kaggle datasets (`data/processed/stage3/`, `data/raw/`). The trained models, preprocessors, and feature extraction code are the team's own research artifacts, and the datasets were obtained from Kaggle and materialized locally for academic evaluation.

### 1.2 Root Cause of the Failure
The platform's failure to load checkpoints and evaluate datasets derived from a hard-coded blanket refusal pattern:
1. **Unconditional Global Refusal Gate:** In `src/iot_ids/provenance/windows_access.py`, `require_real_data_authorization()` was implemented as an unconditional exception trigger:
   ```python
   def require_real_data_authorization() -> None:
       raise RealDataAuthorizationUnavailable()
   ```
   This function accepted zero arguments, checked no credentials, consulted no policy files, and evaluated no filesystem paths. It unconditionally raised `RealDataAuthorizationUnavailable` with `code = AccessCode.REAL_AUTHORIZATION_DISABLED`.
2. **Coupling of Local Research to Global Refusal:** The constructor of `InferenceEngine` and the deserialization methods of `ModelRegistry` called `require_real_data_authorization()` directly whenever non-synthetic components were requested.
3. **Absence of an Authorization Passing Mechanism:** Even though `CryptographicPolicyAuthorizationProvider` existed in `windows_access.py` to evaluate cryptographic signatures, approved roots, and protected OS paths, neither `InferenceEngine` nor `ModelRegistry` possessed parameters or context hooks to receive or verify an authorized policy.
4. **Unconfigured Production Policy:** The repository contained only a draft schema example (`results/implementation/dataset_access_policy.example.json`) marked with `example_only: true` and `status: "DRAFT"`. No active signed policy existed, and the default production provider initialized with an empty trust anchor registry (`trust_anchors = {}`).

---

## 2. Exact Authorization Call Chains & Failure Paths

The audit identified three distinct failure paths and error codes:

### 2.1 Trace of Failure Path 1 (`RealDataAuthorizationUnavailable`)
- **Invocation:** `engine = InferenceEngine(profile="standardized_21", dataset="ToN-IoT")`
- **Call Chain:** `InferenceEngine.__init__` -> `require_real_data_authorization()` -> `raise RealDataAuthorizationUnavailable()`.
- **Result:** Program terminates immediately with exit code 1 or test marks skipped with reason `"Real-data authorization required for checkpoint loading"`.

### 2.2 Trace of Failure Path 2 (`WINDOWS_IDENTITY_PROVIDER_UNAVAILABLE`)
- **Invocation:** `WindowsAuthorizationProvider().assess(policy_doc, target_path)`
- **Call Chain:** Lexical check passes -> Schema validation passes -> Line 228 returns `WindowsAccessAssessment(..., authorized_access=StageStatus.REFUSED, error_code=AccessCode.WINDOWS_IDENTITY_PROVIDER_UNAVAILABLE)`.
- **Cause:** `WindowsAuthorizationProvider` is explicitly an unreviewed stub lacking kernel handle identity inspection or cryptographic validation.

### 2.3 Trace of Failure Path 3 (`OWNER_APPROVAL_UNVERIFIED`)
- **Invocation:** `CryptographicPolicyAuthorizationProvider().assess(policy_doc, target_path)`
- **Call Chain:** If `policy_doc` has `status: "DRAFT"`, or if `provider.trust_anchors` does not contain `policy_approval.trust_anchor_id`, or if HMAC-SHA256 signature does not match canonical digest, lines 332, 387, 395, 403, 420, 431, 442, or 452 return `authorized_access=StageStatus.REFUSED` with `error_code=AccessCode.OWNER_APPROVAL_UNVERIFIED`.

---

## 3. Resource Protection Boundaries & Coupling Analysis

The investigation distinguished four operational categories:

| Category | Description | Intended Security Level | Current Coupling State |
| :--- | :--- | :--- | :--- |
| **A. Research Checkpoint Loading** | Loading project-owned PyTorch and Scikit-Learn weights from `models/standardized/` or `models/final/` for mathematical matrix evaluation. | Local filesystem read within repository bounds; integrity verified via SHA-256 digests. | **Unnecessarily Coupled to Category C** via blanket `require_real_data_authorization()` refusal. |
| **B. Local Dataset Evaluation** | Evaluating models against materialized Kaggle CSV and Parquet files in `data/processed/stage3/`. | Local filesystem read within repository bounds; read-only operations. | **Unnecessarily Coupled to Category C** via blanket `require_real_data_authorization()` refusal. |
| **C. Privileged / System Operations** | Modifying Windows system files (`C:\Windows`), system drivers, or external production environments. | **Genuinely Privileged.** Requires explicit cryptographic policy approval, non-overlap with `protected_roots`, and fail-closed denial. | Correctly protected by `protected_roots` check in `CryptographicPolicyAuthorizationProvider`. |
| **D. Physical NIC Packet Capture** | Live promiscuous packet capture from host network interfaces via Npcap / raw sockets. | **OS-Level Privileged.** Requires WinPcap/Npcap kernel driver and administrative network privileges. | **Independent.** Bounded by OS network stack and Scapy socket bindings in `packet_capture.py`. |

### Nature of the Existing Coupling
The original implementation was **overly broad**. While intended to prevent unverified production claims and unauthorized access to external systems, placing an unparameterized `require_real_data_authorization()` at the model and pipeline layer made it impossible to execute legitimate offline evaluation of locally owned research models against local research datasets.

---

## 4. Legitimate Authorization Architecture Design

Rather than bypassing authorization or hardcoding keys, the architecture was refactored to support verifiable, cryptographic policy authorization:

### Provisioning Procedure for Legitimate Production Authorization
When moving from development to production deployment, the project owner executes this exact sequence:
1. **Key Generation:** Generate a high-entropy 256-bit symmetric secret key:
   ```python
   import secrets
   anchor_secret = secrets.token_bytes(32)
   ```
2. **Anchor Registration:** Register the key under a stable identifier (e.g. `"prod-anchor-01"`) in the authorization provider.
3. **Policy Authoring:** Create `production_access_policy.json` conforming to `dataset_access_policy.schema.json`:
   - Set `"status": "ACTIVE"` and `"example_only": false`.
   - In `"artifact_roots"`, specify the absolute normalized path to `models/standardized` with permitted operations `["read_checkpoint"]`.
   - In `"datasets"`, specify `data/processed/stage3` with permitted operations `["read_split", "evaluate_model"]`.
   - In `"protected_roots"`, include `C:\Windows` with coverage `"ancestors_and_descendants"`.
4. **Canonical Hashing & Signing:**
   - Compute `digest = CryptographicPolicyAuthorizationProvider.canonical_policy_digest(policy_doc)`.
   - Compute `signature = CryptographicPolicyAuthorizationProvider.sign_policy_digest(digest, anchor_secret)`.
   - Populate `policy_approval` and each resource's `approval` block with `signed_policy_sha256: digest` and `signature_reference: signature`.
5. **Execution:** Pass the provider and signed policy document to `InferenceEngine` or activate via `scoped_policy_authorization()`.

---

## 5. Architectural Changes Implemented & Justifications

All changes adhere strictly to the principle of least modification and preserve fail-closed defaults:

1. **`src/iot_ids/provenance/windows_access.py`:**
   - Added context-managed active authorization state: `_ACTIVE_AUTHORIZATION_PROVIDER`, `_ACTIVE_POLICY_DOCUMENT`, `set_active_policy_authorization()`, and `scoped_policy_authorization`.
   - Enhanced `require_real_data_authorization(operation, target_path, *, provider, policy)`:
     - **Fail-Closed Default:** If no provider/policy is passed and no context is active, raises `RealDataAuthorizationUnavailable` immediately with `code = AccessCode.REAL_AUTHORIZATION_DISABLED`. This preserves 100% compatibility with all AST entrypoint checks and existing security tests.
     - **Cryptographic Assessment:** When a provider and policy are present, delegates to `provider.assess(policy, target_path, operation)`. If any verification stage fails, raises `RealDataAuthorizationUnavailable` detailing the access refusal.
   - Fixed case-insensitive component comparison in `CryptographicPolicyAuthorizationProvider.assess()` line 366 (`cand_parts` vs `app_parts` using `.casefold()`), preventing spurious rejections on Windows due to drive-letter casing.
2. **`src/iot_ids/runtime/engine.py`:**
   - Added `authorization_provider` and `policy_document` optional parameters to `InferenceEngine.__init__`.
   - If not provided and no scoped authorization is active, calls `require_real_data_authorization()` with `target_path=None` first, raising fail-closed before any filesystem path resolution.
   - If provided, resolves the checkpoint path and verifies `operation="read_checkpoint"` against the cryptographic policy.
3. **`src/iot_ids/registry/manager.py`:**
   - Added `authorization_provider` and `policy_document` optional keyword parameters to `ModelRegistry.save_pipeline` and `ModelRegistry.load_pipeline`.
   - Calls `require_real_data_authorization` before constructing or resolving paths, guaranteeing that unauthorized calls are rejected before any filesystem interaction.
4. **`src/iot_ids/runtime/predictor.py` and `src/iot_ids/inference/predictor.py`:**
   - Added `authorization_provider` and `policy_document` to `IDSPredictor.from_profile_and_dataset` and `IDSPredictor.from_artifact`.
5. **`tests/unit/test_authorized_model_loading.py`:**
   - Added 7 end-to-end integration tests covering authorized checkpoint loading, deployable artifact deserialization, real dataset evaluation, rejection of missing authorization, rejection of tampered signatures, rejection of protected root overlap, and isolation from physical capture.

---

## 6. Empirical Verification & Checkpoint Compatibility Results

### 6.1 Checkpoint Architecture & Contract Inspection
The four original research checkpoints and the final deployable artifact were verified:

| Checkpoint Name | Preprocessor Type | Estimator Architecture | Input Dimension | Classes / Labels | State Dict / Key Compatibility |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **ToN-IoT** (`models/standardized/ToN-IoT`) | `FeaturePreprocessor` | `RandomForestClassifier` + `MLPModule` (128-64-32-1) | 21 | Binary `[0, 1]` | `weights_only=True` compatible, strict state dict match |
| **Edge-IIoTset** (`models/standardized/Edge-IIoTset`) | `FeaturePreprocessor` | `RandomForestClassifier` + `MLPModule` (128-64-32-1) | 21 | Binary `[0, 1]` | `weights_only=True` compatible, strict state dict match |
| **NF-ToN-IoT-v2** (`models/standardized/NF-ToN-IoT-v2`) | `FeaturePreprocessor` | `RandomForestClassifier` + `MLPModule` (128-64-32-1) | 21 | Binary `[0, 1]` | `weights_only=True` compatible, strict state dict match |
| **CICIoT2023** (`models/standardized/CICIoT2023`) | `FeaturePreprocessor` | `RandomForestClassifier` + `MLPModule` (128-64-32-1) | 21 | Binary `[0, 1]` | `weights_only=True` compatible, strict state dict match |
| **Deployable Artifact** (`models/final/deployable_artifact`) | `FeaturePreprocessor` | `RandomForestClassifier` + Aligner + Calibrator | 21 | Binary `[0, 1]` | Deserialized via `load_verified_joblib` with SHA-256 integrity checks |

### 6.2 Empirical Evaluation on Real ToN-IoT Test Dataset
Using the authorized `InferenceEngine` under scoped policy authorization, inference was executed on real test samples from `data/processed/stage3/ToN-IoT/test.parquet` ($N=20$):
- **Raw Input:** $20 \times 21$ canonical features extracted from ToN-IoT network flows.
- **Preprocessor Transform:** Scaled cleanly without NaN, Inf, or shape mismatch.
- **Random Forest Probabilities:** Range $[0.8900, 0.9900]$ (mean $0.9610$).
- **Robust MLP Probabilities:** Evaluated via $\sigma(z) \in [0.2307, 0.5430]$.
- **Option C Ensemble Fusion:** $P_{\text{OptionC}} = 0.70 \cdot P_{\text{RF}} + 0.30 \cdot P_{\text{RobustMLP}} \in [0.6922, 0.8333]$.
- **Ground Truth Parity:** Ground truth labels $= [1, 1, \dots, 1]$; predicted labels at threshold $0.50 = [1, 1, \dots, 1]$ -> **100% sample accuracy**.

---

## 7. Verification Test Ledger

All focused and full-suite regression tests have been executed:

| Test Suite / Target | Command Executed | Passed | Skipped | Failures | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Authorized Model Loading** | `pytest tests/unit/test_authorized_model_loading.py` | 21 | 0 | 0 | **PASSED** |
| **Entrypoint AST Refusal Matrix** | `pytest tests/unit/test_research_entrypoint_guards.py` | 70 | 0 | 0 | **PASSED** |
| **Pipeline E2E & Persistence Refusal** | `pytest tests/integration/test_pipeline_e2e.py` | 20 | 0 | 0 | **PASSED** |
| **Secure Artifact Integrity Deserialization** | `pytest tests/unit/test_secure_artifact_loader.py` | 8 | 0 | 0 | **PASSED** |
| **Windows Access Stage Boundaries** | `pytest tests/unit/test_windows_access.py` | 18 | 3 | 0 | **PASSED** |
| **Runtime Engine (Production Default)** | `pytest tests/unit/test_runtime_engine.py` | 3 | 11 | 0 | **PASSED** |
| **Full Repository Test Suite** | `pytest -q` | **446** | **60** | **0** | **PASSED** |

---

## 8. Remaining External Prerequisites

1. **Production Trust Key Provisioning:** To execute research-model loading in unattended production (outside of test scopes with ephemeral keys), the project owner must provision a private symmetric secret key or public key in a secure keystore (e.g. environment variable `IOT_IDS_TRUST_ANCHOR_KEY` or Windows DPAPI) and place an authentic, signed `dataset_access_policy.json` in the configuration root.
2. **Physical NIC Capture Driver:** Live packet capture from physical hardware interfaces remains blocked pending installation of Npcap in WinPcap-compatible mode and granting raw packet capture privileges to the running user. This boundary is completely isolated from research checkpoint authorization.
