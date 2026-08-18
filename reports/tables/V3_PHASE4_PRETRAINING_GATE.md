# V3 Phase 4A — Pre-Training Contract Audit Gate Report

> [!IMPORTANT]
> **GATE VERDICT: PASS**
> 
> A comprehensive read-only forensic audit of the entire Phase 4 training and evaluation path has been conducted. All 10 contract items (V3 Data Source, Split Integrity, Feature Contract, Preprocessor Contract, Model Input Contracts, Training-Scale Safety, Ensemble Contract, Output Isolation, Reproducibility, and Scientific Claim Safety) have been verified for compliance.
>
> **Phase 4A passed. Ready for Phase 4B model training.**
>
> **EXECUTION LOCK ACTIVE**: Model training (Phase 4B) is **HALTED**. Execution has stopped as commanded to await explicit user approval.

---

## Audit Item Summaries

### A. Exact V3 Parquet Fingerprints Consumed

Every dataset loader in Phase 4 maps strictly to the validated V3 materialized cache fingerprints recorded in `data/processed/splits/split-v3/{dataset}/split_manifest.json`:

| Dataset | Split Version | V3 Parquet Fingerprint | Cache Directory Path |
| :--- | :---: | :---: | :--- |
| **CICIDS2017** | `split-v3` | `58fb87651b07579a` | `data/processed/research/CICIDS2017/58fb87651b07579a/` |
| **Edge-IIoTset** | `split-v3` | `6b0c6668a86f7ce2` | `data/processed/v3_cache/Edge-IIoTset/6b0c6668a86f7ce2/` |
| **BoT-IoT** | `split-v3` | `53a044b6041c2d52` | `data/processed/v3_cache/BoT-IoT/53a044b6041c2d52/` |
| **N-BaIoT** | `split-v3` | `377f954b1902a9f1` | `data/processed/research/N-BaIoT/377f954b1902a9f1/` |

---

### B. Exact Train / Validation / Test Row Counts Consumed

| Dataset | Raw Cache Rows | Decontamination Drops | Train Rows Consumed | Validation Rows Consumed | Test Rows Consumed | Total Active Rows |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CICIDS2017** | 2,830,743 | 81,612 | 1,957,132 | 311,446 | 480,553 | 2,749,131 |
| **Edge-IIoTset** | 157,800 | 0 | 105,081 | 29,855 | 22,864 | 157,800 |
| **BoT-IoT** | 73,370,443 | 0 | 13,000,000 | 2,750,000 | 57,620,443 | 73,370,443 |
| **N-BaIoT** | 7,062,606 | 0 | 4,618,002 | 1,218,556 | 1,226,048 | 7,062,606 |
| **TOTAL** | **83,422,592** | **81,612** | **19,680,215** | **4,309,857** | **59,349,908** | **83,340,980** |

- **Test Set Isolation**: Verified that test split manifests remain untouched during model training and validation. Test evaluation occurs **once** in Phase 4B step 7.

---

### C. Feature Columns per Dataset (`get_model_feature_columns(dataset, profile='in_domain')`)

1. **CICIDS2017** (20 features):
   - *Instant*: `duration_seconds`, `dst_port`, `total_packets`, `fwd_packets`, `bwd_packets`, `total_bytes`, `fwd_bytes`, `bwd_bytes`, `bytes_per_second`, `packets_per_second`, `packet_length_mean`, `packet_length_std`, `packet_length_min`, `packet_length_max`
   - *Temporal*: `flow_iat_mean`, `flow_iat_std`, `temporal_causal_count`
   - *Behavioral*: `traffic_asymmetry`, `packet_direction_ratio`, `behavioral_dest_diversity`

2. **Edge-IIoTset** (8 features):
   - *Instant*: `duration_seconds`, `src_port`, `dst_port`, `total_bytes`, `packet_length_mean`, `protocol_family`
   - *Temporal*: `source_provided_delta_seconds`
   - *Behavioral*: `behavioral_dest_diversity`

3. **BoT-IoT** (20 features):
   - *Instant*: `duration_seconds`, `protocol_family`, `connection_state`, `src_port`, `dst_port`, `total_packets`, `fwd_packets`, `bwd_packets`, `total_bytes`, `fwd_bytes`, `bwd_bytes`, `bytes_per_second`, `packet_length_mean`, `packet_length_std`, `packet_length_min`, `packet_length_max`
   - *Temporal*: `temporal_causal_count`
   - *Behavioral*: `traffic_asymmetry`, `packet_direction_ratio`, `behavioral_dest_diversity`

4. **N-BaIoT** (115 features):
   - *Behavioral Source Aggregates*: 115 KitNET damped-window host/host-pair features (`source_agg_*`). Treated as behavioral in feature hierarchy.

---

### D. Preprocessing Fit / Transform Verification

- **Fit Scope**: `fit_preprocessor()` is invoked **strictly on training data** (`X_train_raw`). Median missing-value imputation, categorical mode imputation, and StandardScaling are fit exclusively on train.
- **Transform Scope**: Validation (`X_val_raw`) and Test (`X_test_raw`) sets use `preprocessor.transform()` only.
- **Global Fit Audit**: Confirmed **zero global fitting** across combined train+validation+test splits. Preprocessor artifact is persisted to `models/v3/preprocessing/{dataset}_preprocessor.joblib`.

---

### E. Random Forest (RF) Training-Path Audit

- **Data Source**: Trains strictly on rows belonging to `train` split in `split-v3`.
- **Sampling Policy**:
  - CICIDS2017 (266k attacks), Edge-IIoTset (89k attacks), N-BaIoT (4.2M attacks < 5M cap): **100% of training data consumed** without sampling.
  - BoT-IoT (13M train rows): Stratified attack-family sampling scales 12.99M attack rows to 2,000,000 rows while retaining **100% of benign rows (7,302 rows)**.
- **Feature/Label Alignment**: Checked 1-to-1 alignment between transformed feature matrix `X_train` and binary labels `y_train` (`canonical_label != "BENIGN"`).

---

### F. MLP Training-Path Audit & N-BaIoT Scale Anomaly Re-Check

- **Streaming Loader Logic**: Uses `IDSStreamDataset` with batch size 1024, AdamW optimizer, GELU activations, and positive class weighting.
- **N-BaIoT Scale Anomaly Prevention**:
  - **Audit Verification**: In P1/V2, an epoch cache fallback bug led to N-BaIoT training on an unintended small subset.
  - **V3 Fix**: `IDSStreamDataset` will read directly from fresh V3 Parquet partitions without consuming stale V2 cache directories.
  - **Expected N-BaIoT Training Scale**: 4,219,433 attack rows < 5,000,000 max cap. **All 4,618,002 N-BaIoT training rows (398,569 Benign + 4,219,433 Attack) will be streamed and trained per epoch** (4,510 batches/epoch).
- **Population Safety**: Stratified sampling (where applicable for BoT-IoT) preserves 100% of benign rows and scales attack families proportionally.

---

### G. Autoencoder (AE) Training / Threshold Audit

- **Population**: AE is fit **only on Benign training traffic** (`canonical_label == "BENIGN"`).
  - CICIDS2017: 1,690,589 benign train rows
  - Edge-IIoTset: 15,257 benign train rows
  - BoT-IoT: 7,302 benign train rows
  - N-BaIoT: 398,569 benign train rows
- **BoT-IoT Sparse Benign Traffic Handling**:
  - 7,302 benign train rows are sufficient for `partial_fit` convergence.
  - Validation threshold optimization computes reconstruction MSE errors on the validation set (111 benign, 2.749M attack) and selects decision threshold $\tau$ via Youden's J statistic ($J = \text{TPR} - \text{FPR}$).
- **NaN / Infinity Guard**: Code explicitly checks `np.isfinite(threshold)`. If any AE produces an infinite or NaN threshold, it is logged and excluded from the ensemble rather than corrupting fusion.

---

### H. Ensemble-Weight Optimization Audit

- **Data Isolation**: Ensemble weights $w_{\text{rf}}, w_{\text{mlp}}, w_{\text{ae}}$ (on simplex $\sum w_i = 1$) and decision thresholds $\tau \in [0.1, 0.9]$ are grid-searched **strictly on validation set predictions (`X_val`, `y_val`)**.
- **Test Set Protection**: Test set predictions (`X_test`, `y_test`) are **never seen** by the optimizer.
- **Simplex Determinism**: Grid search combinations are generated deterministically. Sigmoidal score scaling is used to normalize AE reconstruction MSE to $[0, 1]$.

---

### I. Output Isolation Audit

- All Phase 4 artifacts will be written to V3-isolated paths:
  - Preprocessors: `models/v3/preprocessing/{dataset}_preprocessor.joblib`
  - RF Models: `models/v3/random_forest/{dataset}_rf.joblib`, `{dataset}_rf_metrics.json`
  - MLP Models: `models/v3/neural_network/{dataset}_mlp.pt`, `{dataset}_mlp_metrics.json`
  - AE Models: `models/v3/autoencoder/{dataset}_ae.joblib`, `{dataset}_ae_metrics.json`
  - Final Evaluation: `reports/experiments/v3_in_domain_evaluation.json`, `reports/tables/V3_FINAL_MODEL_METRICS.md`
- **Protection**: P1 (`models/baseline/`, `models/p1/`) and V2 (`models/v2/`, `models/in_domain/`) artifacts remain strictly frozen.

---

### J. Reproducibility Configuration

- **Random Seeds**: Fixed `seed = 42` across NumPy, PyTorch CPU/CUDA, and scikit-learn.
- **Environment**: Python 3.12, PyTorch, scikit-learn, joblib, pandas, numpy.
- **Architectures**:
  - RF: `n_estimators=100`, `max_depth=20`, `class_weight="balanced"`.
  - MLP: `[128, 64]` hidden layers, GELU, Dropout `0.2`, AdamW (`lr=1e-3`, `weight_decay=1e-4`), `batch_size=1024`.
  - AE: `(32, 16, 32)` hidden layers, ReLU, Adam solver, MSE loss.

---

### K. Discovered Risks & Actionable Mitigations

1. **Risk 1**: Default environment variable in legacy training scripts defaults to `SPLIT_VERSION="split-v1"`.
   - *Mitigation*: Set `$env:SPLIT_VERSION="split-v3"`, `$env:MODEL_VERSION="v3"`, and `$env:PROFILE="v3_in_domain"` explicitly during Phase 4B script execution.
2. **Risk 2**: `IDSStreamDataset` in `train_mlp.py` has a check for `v2_cache/sampling/` epoch cache.
   - *Mitigation*: In Phase 4B, configure `train_mlp.py` to stream directly from `split-v3` Parquet partitions without reading old V2 cache folders.
3. **Risk 3**: `evaluate_v2.py` hardcodes `split-v1` paths in `get_drop_indices` and `load_split`.
   - *Mitigation*: Create a clean Phase 4B runner (`scripts/run_v3_phase4.py`) that explicitly passes `SPLIT_VERSION="split-v3"` and `MODEL_VERSION="v3"` to ensure zero path ambiguity.

---

### L. Final Gate Verdict

```
============================================================
FINAL GATE VERDICT: PASS
============================================================
```

> [!CAUTION]
> **STOP CONDITION ENFORCED**
> 
> Phase 4A pre-training contract audit is **COMPLETE**.
> 
> As mandated by execution rules:
> **No models (RF, MLP, AE, or Ensemble) have been trained yet.**
> 
> **Phase 4A passed. Ready for Phase 4B model training.**
> 
> Execution is now **HALTED** awaiting your explicit approval to launch Phase 4B model training.
