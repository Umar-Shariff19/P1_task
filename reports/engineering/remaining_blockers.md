# Remaining Engineering Blockers & Readiness Roadmap

**Date**: 2026-10-29  
**Repository**: `C:\Users\umari\Documents\P1_task_Implementation`  
**Branch**: `fix/registry-authorization-tests`  
**Current Commit**: `dc7f6b67fcfe585bc883af61cfb6479855a6b4b2`  
**Test Suite State**: 402 passed, 60 skipped, 12 warnings, 0 failures (54.88s, 462 collected)  

---

## 1. Summary of Fixed Defects and Verified Hardening

| Area | Defect / Gap Resolved | Resolution | Verification Test |
|---|---|---|---|
| **Webhook SSRF** | Destination validation TOCTOU / DNS rebinding race condition | Implemented connection-time destination validation (`_PinnedHTTPConnection`, `_PinnedHTTPSConnection`) connecting directly to validated IP tuple; kernel getpeername check | `test_webhook_dns_rebinding_connection_time_enforcement`, `test_pinned_http_kernel_peername_check_blocks_prohibited_destination` |
| **TLS & SNI** | Potential SNI / hostname mismatch during IP pinning | Pinned socket receives original domain in `server_hostname` parameter of `wrap_socket`, preserving SNI and SAN/CN validation | `test_webhook_tls_sni_and_cert_verification` |
| **Redirects** | Potential credential leakage / SSRF on redirect | Built `_SafeRedirectHandler` protocol-level interceptor rejecting all 3xx redirects before follow requests are constructed | `test_safe_redirect_handler_blocks_all_redirect_codes` |
| **Proxy Egress** | Ambient environment proxies potentially bypassing local restrictions | Neutralized ambient environment proxy variables (`http_proxy`, `https_proxy`) by default via `ProxyHandler({})` | `test_webhook_proxy_policy` |
| **Address Classification** | IPv4-mapped IPv6, CGNAT, loopback edge cases | Exhaustive classification across 24 address permutations | `test_prohibited_ip_classification` |
| **Socket Cleanup** | Dangling TCP socket if TLS handshake fails | Wrapped TLS handshake in `try...except` to close and clear socket on SSL failure | `test_pinned_https_socket_cleanup_on_tls_failure` |
| **Evaluation Contract** | Unenforced real-data evaluation reporting schema | Integrated `validate_evaluation_report` and `save_validated_evaluation_report` in `src/iot_ids/experiments/evaluator.py` enforcing schema compliance, metric bounds, valid digests, and rejecting synthetic claims | `test_validate_evaluation_report_*`, `test_save_validated_evaluation_report_*` (15 passing unit tests) |
| **Warning Cleanup** | 7 Python 3.12 syntax warnings, 1 legacy builder warning, 2 pytest cache warnings | Converted unescaped regex/LaTeX to raw literals, deferred builder import, and configured `addopts = "-p no:cacheprovider"` | Warnings reduced from 21 down to 12 |
| **Packaging Validation** | Reproducible deterministic wheel build and isolated installation | Built reproducible wheel with `SOURCE_DATE_EPOCH=1700000000` (`147,779 bytes`, SHA-256 `3dfbe2c0ce89...`), verified archive hygiene (95 files, 0 data/models), verified clean venv install, executed CLI `--help` and `synthetic_packet_demo` outside repo | `scripts/build_and_test_clean_wheel.py` exit code `0` |

---

## 2. Categorized Remaining Blockers

### Category A: Code Defects
- **Status**: **ZERO KNOWN DEFECTS**.
- **Evidence**: All 402 automated unit, integration, concurrency, splitting, and readiness tests pass with 0 failures across 462 collected test items.

---

### Category B: Missing Authorization (49 Skipped Tests)
- **Description**: Real datasets (`Edge-IIoTset`, `ToN-IoT`, `NF-ToN-IoT-v2`, `CICIoT2023`) and trained model checkpoints (`rf_model.joblib`, `mlp_model.pt`, `ae_model.pt`) are protected by fail-closed authorization checks (`require_real_data_authorization()`).
- **Impact**: 49 tests intentionally and safely skip to maintain strict confidentiality and regulatory compliance.
- **Prerequisite**: Legitimate authorization code provisioning via sanctioned channels.
- **Exact Next Action**: When credentials are provided, run `pytest tests/integration/` with authorization enabled to execute full checkpoint and real dataset test paths.

---

### Category C: Environment Limitations (8 Skipped Tests)
- **Description**: On Windows, creating directory junctions or symbolic links in temporary directories requires `SeCreateSymbolicLinkPrivilege` or Developer Mode.
- **Impact**: 8 filesystem tests safely detect privilege absence and skip (`[WinError 1314] A required privilege is not held by the client`).
- **Remediation Implemented**: Added deterministic unprivileged tests (`test_reparse_point_rejection_without_elevation`, `test_unprivileged_identity_verifier_rejects_unverified_reparse_semantics`) verifying defense logic via capability testing and lstat mocking.
- **Exact Next Action**: Run these tests in an elevated CI container (e.g., Linux CI runner or Windows Server with Developer Mode enabled) where symlinks are unprivileged.

---

### Category D: Historical Evaluation Artifacts (3 Skipped Tests)
- **Description**: Tests in `tests/unit/test_evaluation_artifacts.py` expect `reports/experiments/in_domain_evaluation.json`. This file is generated only by running full real-data evaluation.
- **Impact**: 3 tests skip because real-data evaluation has not run in this checkout.
- **Remediation Implemented**: Created `configs/real_data_evaluation_schema.json`, integrated `validate_evaluation_report` and `save_validated_evaluation_report`, and added 15 unit tests in `tests/unit/test_evaluation_artifacts.py` validating schema adherence, bounded metrics, and rejection of synthetic-as-real claims.
- **Exact Next Action**: Generate `reports/experiments/in_domain_evaluation.json` during the authorized real-data evaluation milestone and validate via `save_validated_evaluation_report`.

---

### Category E: Hardware & Kernel Driver Limitations
- **Description**: Live physical NIC packet sniffing (`predict-live` CLI command) requires the Npcap OEM/Community driver installed in WinPcap-compatible mode and an Administrator account (or `npcap-users` membership).
- **Impact**: Offline PCAP replay is fully functional, but live capture on physical hardware adapters cannot run in an unprivileged session without Npcap.
- **Exact Next Action**: Install Npcap with WinPcap API compatibility on the target sensor appliance and assign user to `npcap-users`.

---

### Category F: Evidence Gaps (Production Readiness)
- **Description**: While synthetic pipelines, contracts, and security hardening are verified, production claims regarding real detection efficacy (ASR, FPR, AUC) cannot be made without authorized dataset benchmarks.
- **Impact**: Production readiness remains classified as **NOT ESTABLISHED**.
- **Exact Next Action**: Execute post-authorization evaluation using `configs/real_data_evaluation_schema.json` and publish verifiable benchmark artifacts.

---

## 3. Dependency Warnings Status (12 Remaining)

1. **PyTorch JIT Deprecations (6 warnings)**:
   - Triggered by `torch.jit.script` in `tests/unit/test_mlp_loader.py`.
   - *Status*: Expected; test intentionally constructs a scripted TorchScript archive to verify that `InferenceEngine._load_mlp_checkpoint` strictly rejects it under `weights_only=True`.
2. **PyTorch TorchScript Archive UserWarning (1 warning)**:
   - Emitted by PyTorch during the scripted model rejection test.
   - *Status*: Expected byproduct of safe rejection testing.
3. **SHAP Colormap Deprecations (3 warnings)**:
   - Triggered in `shap/plots/colors/_colors.py:47-49` (`set_bad`, `set_over`, `set_under`).
   - *Status*: Upstream issue in third-party `shap` 0.44+ library.
4. **Joblib Loky Physical Cores UserWarning (1 warning)**:
   - Emitted by `joblib/externals/loky` on Windows when physical core lookup falls back to logical cores.
   - *Status*: Harmless third-party library fallback.
5. **Legacy Builder Import Warning (1 warning)**:
   - Emitted in `tests/unit/test_canonical_features.py:4` which tests backward compatibility of `build_canonical_features`.
   - *Status*: Confirms deprecation notice functions as intended.
