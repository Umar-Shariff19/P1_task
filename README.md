# Multi-Level IoT Intrusion Detection System (IoT-IDS P1)

This repository implements the research pipeline and demonstration system for an **Adversarially Robust, Multi-Level Explainable Intrusion Detection System for IoT and IIoT Environments**.

The system combines supervised classifiers (Random Forest and tabular PyTorch MLP) with an independent, benign-trained Autoencoder anomaly detector managed by a **Design B 2-Stage Risk & Decision Layer**.

---

## 1. PROJECT OVERVIEW

The framework evaluates intrusion detection across two authentic benchmark datasets:
- **Edge-IIoTset**: High-density Industrial IoT testbed traffic.
- **ToN-IoT Network**: Heterogeneous IoT/IIoT network traffic capture.

### Key Architecture Components:
1. **Multi-Level Representation**: Combines static flow features, causal temporal rates/counts, and destination behavioral diversity.
2. **Harmonized Cross-Domain Transfer**: Evaluates zero-adaptation cross-domain transfer over a 6-feature physical network space ($F_{\text{common}}$).
3. **Design B 2-Stage Risk Layer**: Combines supervised ensemble threat probability $P_{\text{sup}} = \frac{1}{2} P_{\text{rf}} + \frac{1}{2} P_{\text{mlp}}$ with an independently calibrated Autoencoder anomaly score $S_{\text{ae}}$.
4. **Explainable AI (XAI)**: Provides global/local feature importances and Autoencoder per-feature reconstruction error decompositions ($e_i = (x_i - \hat{x}_i)^2$).
5. **Constrained Adversarial Evaluation**: Evaluates white-box MLP gradient attacks (FGSM and PGD-10) with discrete feature masking and domain clamping.
6. **Interactive Demonstration**: Streamlit web dashboard and CLI smoke test for real-time sample inspection.

---

## 2. FINAL CANONICAL FEATURE REPRESENTATION

### In-Domain Multi-Level Feature Space:
- **Edge-IIoTset (13 features)**: $6\ F_{\text{common}} + 3\ F_{\text{temporal}} + 2\ F_{\text{behavioral}} + 2\ F_{\text{dataset\_specific}}$ (`mqtt_msgtype`, `mbtcp_unit_id`).
- **ToN-IoT Network (13 features)**: $6\ F_{\text{common}} + 3\ F_{\text{temporal}} + 2\ F_{\text{behavioral}} + 2\ F_{\text{dataset\_specific}}$ (`conn_state_encoded`, `service_encoded`).

### Harmonized Cross-Domain Space ($F_{\text{common}}$ - 6 Features):
1. `duration` (Flow duration in seconds)
2. `src_bytes` (Source payload transfer volume)
3. `proto_tcp` (TCP transport indicator)
4. `proto_udp` (UDP transport indicator)
5. `proto_icmp` (ICMP control indicator)
6. `is_well_known_port` (Target service port indicator $< 1024$)

> [!NOTE]
> `src_pkts` and `dst_pkts` were explicitly excluded from $F_{\text{common}}$ because forensic audits revealed non-equivalent record granularities (frame-level record vs flow summary) and proxy mismatch (`tcp.flags.ack` mapped as packet count).

---

## 3. AUTHORITATIVE FROZEN BENCHMARK RESULTS

All metrics below represent the frozen, reconciled evaluation over untouched test split samples:

| Evaluation Profile | Source Domain $\rightarrow$ Target Domain | Feature Space | Accuracy | Attack F1 | ROC AUC | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **In-Domain** | **Edge-IIoTset** | 13 Features | **89.75%** | **94.29%** | **0.8773** | **AUTHORITATIVE (FROZEN)** |
| **In-Domain** | **ToN-IoT Network** | 13 Features | **96.49%** | **97.73%** | **0.9952** | **AUTHORITATIVE (FROZEN)** |
| **Cross-Domain** | **Edge-IIoTset $\rightarrow$ ToN-IoT** | 6 $F_{\text{common}}$ | **76.33%** | **86.57%** | **0.8081** | **AUTHORITATIVE (FROZEN)** |
| **Cross-Domain** | **ToN-IoT $\rightarrow$ Edge-IIoTset** | 6 $F_{\text{common}}$ | **77.94%** | **86.96%** | **0.7212** | **AUTHORITATIVE (FROZEN)** |

> [!IMPORTANT]
> The early preliminary ToN-IoT Attack F1 result of **99.60%** has been officially **SUPERSEDED** by the reconciled 97.73% result following the clean 6-feature $F_{\text{common}}$ harmonization.

---

## 4. REPRODUCTION PIPELINE

The end-to-end research pipeline is organized sequentially under `scripts/`:

```bash
# 1. Dataset Materialization & Verification
.venv\Scripts\python.exe scripts/01_materialize.py
.venv\Scripts\python.exe scripts/02_validate_materialization.py

# 2. Stratified Temporal Splitting & Verification
.venv\Scripts\python.exe scripts/03_create_splits.py
.venv\Scripts\python.exe scripts/04_validate_splits.py

# 3. Model Training & Risk Layer Calibration
.venv\Scripts\python.exe scripts/05_train_models.py
.venv\Scripts\python.exe scripts/06_calibrate_risk.py

# 4. Evaluation & Paper Evidence Publication
.venv\Scripts\python.exe scripts/07_evaluate.py
.venv\Scripts\python.exe scripts/08_generate_evidence.py

# 5. XAI Attribution & Adversarial Evaluation
.venv\Scripts\python.exe scripts/09_generate_xai_evidence.py
.venv\Scripts\python.exe scripts/10_run_adversarial_evaluation.py
```

---

## 5. DEMONSTRATION & INTERFERENCE

### Interactive Streamlit Web Dashboard:
```bash
.venv\Scripts\streamlit.exe run demo/app.py
```

### Automated Terminal CLI Smoke Test:
```bash
.venv\Scripts\python.exe demo/cli_demo.py
```

The interactive demonstration allows real-time dataset selection, clean flow inspection, pre-computed adversarial evasion inspection, probability gauges ($P_{\text{rf}}$, $P_{\text{mlp}}$, $P_{\text{sup}}$), Autoencoder anomaly score ($S_{\text{ae}}$), Design B Risk Decision state banners, feature tables, and XAI reconstruction error charts.

---

## 6. EXPLAINABLE AI (XAI) EVIDENCE

- **Feature Attributions**: Evaluated via Random Forest Gini/Permutation importances and MLP permutation importances.
- **Model Consensus**: Spearman rank correlation coefficient ($\rho = 0.8632$ on Edge-IIoTset) confirms high feature attribution consensus between RF and MLP classifiers.
- **Autoencoder Error Decomposition**: Measures per-feature squared reconstruction errors $e_i = (x_i - \hat{x}_i)^2$ to identify exact feature dimensions driving anomaly score threshold breaches.

---

## 7. CONSTRAINED ADVERSARIAL EVALUATION

Adversarial evaluation measures the impact of gradient perturbations (FGSM and PGD-10 across $\epsilon \in \{0.05, 0.10, 0.20, 0.30\}$) generated against the differentiable MLP classifier:

- **Methodology**: Evaluated in `RobustScaler` standardized feature space with continuous features clamped to training min/max bounds $[x_{\text{min}}, x_{\text{max}}]$.
- **Discrete Masking**: Discrete protocol indicators (`proto_tcp`, `proto_udp`, `proto_icmp`, `is_well_known_port`, etc.) were 100% masked and unperturbed.
- **Defensive Diversity**: On Edge-IIoTset, 100.00% of evasive attack samples ($P_{\text{sup}} < 0.5$) triggered AE anomaly flags ($S_{\text{ae}} \ge 0.8$). On ToN-IoT, AE catch rates ranged from **8.12% to 51.14%**.

> [!CAUTION]
> This study evaluates **constrained feature-space perturbations**, NOT live physical network packet injection. AE anomaly flags represent statistical deviation indications, NOT empirical proof of zero-day detection.

---

## 8. REPOSITORY STRUCTURE

```
P1_task_Implementation/
├── configs/features/canonical_schema.json   # Canonical feature profiles
├── data/processed/final/                  # Frozen Parquet split datasets
├── models/final/                          # Frozen binary model checkpoints
│   ├── Edge-IIoTset/
│   └── ToN-IoT/
├── src/iot_ids/                           # Production source package
│   ├── models/ensemble/risk_layer.py      # Design B Risk Layer logic
│   ├── xai/                               # XAI explainer modules
│   ├── adversarial/                       # FGSM/PGD attack & evaluation modules
│   └── pipeline/system.py                 # IDSSystemPipeline wrapper
├── scripts/                               # Sequential pipeline scripts (01 to 10)
├── demo/                                  # Interactive Streamlit dashboard & CLI
├── reports/                               # Markdown evidence reports & Claims Matrix
└── tests/unit/                            # Unit test suite (29/29 passing)
```

---

## 9. QUICK START & ENVIRONMENT SETUP

```powershell
# 1. Create Python Virtual Environment
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 2. Install Package Dependencies
.\.venv\Scripts\pip.exe install -e .[dev]

# 3. Run Unit Test Suite
.\.venv\Scripts\pytest.exe tests/unit/

# 4. Launch Interactive Demonstration
.\.venv\Scripts\streamlit.exe run demo/app.py
```

---

## 10. RAW DATASETS & LICENSE NOTE

Raw network captures (`data/raw/`) are excluded from version control under project `.gitignore`. Users must download original captures directly from official dataset providers:
- **Edge-IIoTset**: [IEEE Dataport / Ferrag et al. (2022)]
- **ToN-IoT Network**: [Cyber Range Lab, UNSW Canberra / Moustafa et al. (2020)]

---

## 11. SCIENTIFIC LIMITATIONS

As documented in [CLAIMS_MATRIX.md](file:///C:/Users/umari/Documents/P1_task_Implementation/reports/tables/CLAIMS_MATRIX.md):
1. In-domain evaluation reflects random-sample pattern generalization under benchmark capture conditions.
2. Cross-domain transfer is evaluated across separate physical IoT/IIoT testbeds over physical network attributes.
3. Adversarial perturbations occur in standardized feature space, not live physical network traffic.
4. Autoencoder defensive coverage varies by dataset topology and is not a universal guarantee.
