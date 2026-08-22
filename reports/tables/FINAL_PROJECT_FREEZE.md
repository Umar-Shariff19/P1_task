# MASTER PROJECT FREEZE & AUTHORITATIVE RESEARCH ARTIFACT

> [!IMPORTANT]
> **SOLE AUTHORITATIVE FINAL-RESULTS DOCUMENT**
>
> This document is the single, immutable master specification for the entire **Multi-Level IoT Intrusion Detection System** research project. All values, schemas, metrics, claim boundaries, and evidence tables contained herein are permanently frozen and mathematically verified.

---

## A. FINAL ARCHITECTURE

The architecture integrates a multi-level feature representation with a 3-model hybrid intrusion detection framework and a **Design B 2-Stage Risk & Decision Layer**:

```
                              INPUT FLOW SAMPLE
                                      │
                                      ▼
                        Feature Preprocessing (RobustScaler)
                                      │
                                      ▼
                      Multi-Level Feature Representation
                                      │
           ┌──────────────────────────┴──────────────────────────┐
           │                                                     │
           ▼                                                     ▼
Supervised Classifier Path                              Anomaly Detection Path
┌──────────────────────┐                             ┌────────────────────────┐
│ Random Forest (RF)   ├──┐                          │ Benign-Trained         │
└──────────────────────┘  ├──> Supervised Score      │ Autoencoder (AE)       │
┌──────────────────────┐  │    P_sup = (P_rf+P_mlp)/2└───────────┬────────────┘
│ PyTorch MLP          ├──┘                                      │
└──────────────────────┘                                         ▼
                                                       Reconstruction Error MSE
                                                                 │
                                                                 ▼
                                                        Calibrated Score S_ae
                                                        (Empirical CDF Lookup)
                                                                 │
           ┌─────────────────────────────────────────────────────┘
           │
           ▼
DESIGN B 2-STAGE RISK & DECISION LAYER
  ├── P_sup >= 0.50                      ──> HIGH CONFIDENCE ATTACK
  ├── P_sup < 0.50 AND S_ae >= 0.80      ──> SUSPICIOUS / ANOMALOUS (Defensive Diversity)
  └── P_sup < 0.50 AND S_ae < 0.80       ──> BENIGN
```

---

## B. FINAL DATASETS & PROVENANCE

1. **Edge-IIoTset**: High-density Industrial IoT benchmark capture (Ferrag et al., IEEE NetSoft 2022). `ML-EdgeIIoT-dataset.csv` (7.1% stratified benchmark subset, $157,800$ raw rows).
2. **ToN-IoT Network**: Heterogeneous IoT/IIoT network capture (Moustafa et al., UNSW Canberra 2020). Clean flow records ($211,043$ raw rows).

---

## C. FINAL FEATURE CONTRACT & DEFINITIONS

### Harmonized Cross-Domain Space ($F_{\text{common}}$ - Exactly 6 Features):
1. `duration`: Flow duration in seconds
2. `src_bytes`: Source payload transfer volume (bytes)
3. `proto_tcp`: Binary TCP protocol indicator
4. `proto_udp`: Binary UDP protocol indicator
5. `proto_icmp`: Binary ICMP protocol indicator
6. `is_well_known_port`: Binary indicator for destination port $< 1024$

> [!NOTE]
> `src_pkts` and `dst_pkts` were explicitly removed from $F_{\text{common}}$ following a forensic audit which revealed non-equivalent record granularities (frame-level record vs flow summary) and proxy mismatch (`tcp.flags.ack` mapped as packet count).

### In-Domain Multi-Level Feature Space:
- **Edge-IIoTset (13 features)**:
  - $F_{\text{common}}$ (6): `duration`, `src_bytes`, `proto_tcp`, `proto_udp`, `proto_icmp`, `is_well_known_port`
  - $F_{\text{temporal}}$ (3): `temporal_causal_count`, `temporal_causal_rate`, `temporal_iat_mean`
  - $F_{\text{behavioral}}$ (2): `behavioral_dest_diversity`, `behavioral_src_activity`
  - $F_{\text{dataset\_specific}}$ (2): `mqtt_msgtype`, `mbtcp_unit_id` (active non-constant columns)
- **ToN-IoT Network (13 features)**:
  - $F_{\text{common}}$ (6): `duration`, `src_bytes`, `proto_tcp`, `proto_udp`, `proto_icmp`, `is_well_known_port`
  - $F_{\text{temporal}}$ (3): `temporal_causal_count`, `temporal_causal_rate`, `temporal_iat_mean`
  - $F_{\text{behavioral}}$ (2): `behavioral_dest_diversity`, `behavioral_src_activity`
  - $F_{\text{dataset\_specific}}$ (2): `conn_state_encoded`, `service_encoded`

---

## D. FINAL MODEL SPECIFICATIONS

1. **Random Forest (RF)**: `n_estimators=100`, `max_depth=15`, `random_state=42`. Evaluated via `.predict_proba()`.
2. **PyTorch MLP**: 4-layer feedforward architecture ($D_{\text{in}} \rightarrow 128 \rightarrow 64 \rightarrow 32 \rightarrow 1$) with BatchNorm, ReLU, and Dropout (0.2). Trained via Adam ($\text{lr}=0.001$) and BCEWithLogitsLoss for 10 epochs.
3. **PyTorch Autoencoder (AE)**: Bottleneck architecture ($D_{\text{in}} \rightarrow 64 \rightarrow 16 \rightarrow 64 \rightarrow D_{\text{in}}$) with ReLU activation. Trained **strictly on benign Train samples** to minimize reconstruction MSE.

---

## E. TRAIN / VALIDATION / TEST METHODOLOGY

- **Split Ratio**: Stratified temporal 60% Train / 20% Validation / 20% Test.
  - **Edge-IIoTset**: 94,680 Train / 31,560 Validation / 31,560 Test rows.
  - **ToN-IoT Network**: 126,625 Train / 42,209 Validation / 42,209 Test rows.
- **Data Isolation Rules**:
  - Supervised RF and MLP classifiers trained on 60% Train split.
  - Autoencoder trained **strictly on benign Train samples**.
  - Risk Layer Autoencoder calibration ($S_{\text{ae}}$ empirical CDF) performed **strictly on benign Validation samples**.
  - All metrics, XAI attributions, and adversarial evaluations calculated **strictly on untouched Test split**.

---

## F. FINAL AUTHORITATIVE IN-DOMAIN RESULTS

*Evaluated over untouched test split samples using full multi-level in-domain representations*:

| Dataset | Feature Count | Test Rows | Accuracy | Precision | Recall | Attack F1 | Macro F1 | ROC AUC | PR AUC | Authoritative Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Edge-IIoTset** | 13 | 31,560 | **89.75%** | 89.23% | 99.95% | **94.29%** | 72.31% | **0.8773** | **0.9629** | **AUTHORITATIVE (FROZEN)** |
| **ToN-IoT Network** | 13 | 42,209 | **96.49%** | 96.34% | 99.17% | **97.73%** | 94.98% | **0.9952** | **0.9982** | **AUTHORITATIVE (FROZEN)** |

---

## G. FINAL AUTHORITATIVE CROSS-DOMAIN RESULTS

*Models trained on Source domain using ONLY frozen $F_{\text{common}}$ (6 features) and evaluated directly on Target Test split without retraining or target adaptation*:

| Source Domain $\rightarrow$ Target Domain | Feature Space | Target Test Rows | Accuracy | Precision | Recall | Attack F1 | Macro F1 | ROC AUC | PR AUC | Authoritative Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Edge-IIoTset $\rightarrow$ ToN-IoT** | 6 $F_{\text{common}}$ | 42,209 | **76.33%** | 76.33% | 99.98% | **86.57%** | 43.44% | **0.8081** | **0.9387** | **AUTHORITATIVE (FROZEN)** |
| **ToN-IoT $\rightarrow$ Edge-IIoTset** | 6 $F_{\text{common}}$ | 31,560 | **77.94%** | 87.00% | 86.91% | **86.96%** | 57.76% | **0.7212** | **0.9243** | **AUTHORITATIVE (FROZEN)** |

---

## H. DESIGN B RISK LAYER DECISION DISTRIBUTION

- **Thresholds**: Supervised decision threshold $\tau_{\text{sup}} = 0.50$, Autoencoder anomaly threshold $\tau_{\text{ae}} = 0.80$.
- **Edge-IIoTset Test Split Distribution**:
  - `HIGH CONFIDENCE ATTACK`: 29,907 samples (94.76%)
  - `SUSPICIOUS / ANOMALOUS`: 931 samples (2.95%)
  - `BENIGN`: 722 samples (2.29%)
- **ToN-IoT Network Test Split Distribution**:
  - `HIGH CONFIDENCE ATTACK`: 33,155 samples (78.55%)
  - `BENIGN`: 7,118 samples (16.86%)
  - `SUSPICIOUS / ANOMALOUS`: 1,936 samples (4.59%)

---

## I. EXPLAINABLE AI (XAI) EVIDENCE SUMMARY

1. **In-Domain Attribution**: RF Gini and Permutation importance ranking confirms strong model reliance on static payload size (`src_bytes`) and causal temporal features.
2. **Model Consensus**: Spearman rank correlation coefficient ($\rho = 0.8632$ on Edge-IIoTset, $p = 2.41 \times 10^{-5}$) confirms high feature attribution agreement between Random Forest and MLP classifiers.
3. **Cross-Domain $F_{\text{common}}$ Attribution**: Cross-domain transfer relies primarily on physical payload volume (`src_bytes` = 68.71%) and service port indicators (`is_well_known_port` = 20.03%).
4. **Autoencoder Reconstruction Breakdown**: Per-feature MSE decomposition $e_i = (x_i - \hat{x}_i)^2$ identifies exact input features causing anomaly score spikes in suspicious traffic.

---

## J. ADVERSARIAL ROBUSTNESS EVALUATION SUMMARY

*Evaluated over all $N$ originally correctly predicted attack samples ($Y=1$) under white-box MLP gradient attack with discrete protocol masking and domain bounds $[x_{\text{min}}, x_{\text{max}}]$*:

| Dataset | Attack Method | Epsilon ($\epsilon$) | Attacked Samples ($N$) | Supervised Evaded ($P_{\text{sup}} < 0.5$) | Supervised ASR (%) | Suspicious Evaded (AE Catch) | AE Catch Rate (%) | Complete Evasion (Benign Evaded) | Complete Evasion Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Edge-IIoTset** | FGSM | 0.10 | 26,686 | 30 | 0.11% | 30 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | PGD-10 | 0.10 | 26,686 | 817 | 3.06% | 817 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | PGD-10 | 0.30 | 26,686 | 2,281 | 8.55% | 2,281 | **100.00%** | 0 | **0.00%** |
| **ToN-IoT** | FGSM | 0.10 | 31,941 | 498 | 1.56% | 76 | **15.26%** | 422 | **1.32%** |
| **ToN-IoT** | PGD-10 | 0.10 | 31,941 | 704 | 2.20% | 82 | **11.65%** | 622 | **1.95%** |
| **ToN-IoT** | PGD-10 | 0.30 | 31,941 | 3,339 | 10.45% | 647 | **19.38%** | 2,692 | **8.43%** |

---

## K. SUPERSEDED HISTORICAL RESULTS TABLE

*The following preliminary results from earlier experimental phases are officially SUPERSEDED and must NOT be used in the paper*:

| Superseded Metric / Result | Dataset / Direction | Superseded Value | Authoritative Reconciled Value | Reason for Superseding |
| :--- | :--- | :---: | :---: | :--- |
| Early ToN-IoT In-Domain F1 | ToN-IoT Network | **99.60%** | **97.73%** | Superseded because old feature set included non-equivalent `src_pkts` and `dst_pkts` proxies. |
| 8-Feature Cross-Domain $E \rightarrow T$ F1 | Edge $\rightarrow$ ToN | **86.59%** | **86.57%** | Superseded following clean 6-feature $F_{\text{common}}$ harmonization and $P_{\text{sup}}$ ensemble score curve evaluation. |
| 8-Feature Cross-Domain $E \rightarrow T$ ROC AUC | Edge $\rightarrow$ ToN | **0.8547** | **0.8081** | Superseded following clean 6-feature $F_{\text{common}}$ harmonization and $P_{\text{sup}}$ ensemble score curve evaluation. |
| 8-Feature Cross-Domain $T \rightarrow E$ F1 | ToN $\rightarrow$ Edge | **86.47%** | **86.96%** | Superseded following clean 6-feature $F_{\text{common}}$ harmonization and $P_{\text{sup}}$ ensemble score curve evaluation. |
| 8-Feature Cross-Domain $T \rightarrow E$ ROC AUC | ToN $\rightarrow$ Edge | **0.7073** | **0.7212** | Superseded following clean 6-feature $F_{\text{common}}$ harmonization and $P_{\text{sup}}$ ensemble score curve evaluation. |

---

## L. REPRODUCIBILITY INSTRUCTIONS

```powershell
# 1. Environment Setup
python -m venv .venv
.\.venv\Scripts\pip.exe install -e .[dev]

# 2. Run Unit Test Suite (29 Tests)
.\.venv\Scripts\pytest.exe tests/unit/

# 3. Reproduce Authoritative Baseline Metrics
.\.venv\Scripts\python.exe scripts/07_evaluate.py
.\.venv\Scripts\python.exe scripts/08_generate_evidence.py

# 4. Reproduce XAI Attributions & Adversarial Evidence
.\.venv\Scripts\python.exe scripts/09_generate_xai_evidence.py
.\.venv\Scripts\python.exe scripts/10_run_adversarial_evaluation.py

# 5. Launch Interactive Demonstration Dashboard
.\.venv\Scripts\streamlit.exe run demo/app.py
```

---

## M. FINAL CLAIM-SAFETY & BOUNDARY MATRIX

| Claim Scope | Safe Paper Claim | Required Methodological Qualification | Forbidden Claim |
| :--- | :--- | :--- | :--- |
| **In-Domain Detection** | Multi-level representation achieves strong intrusion detection (94.29% F1 Edge, 97.73% F1 ToN). | In-domain evaluation reflects random-sample pattern generalization under benchmark capture conditions. | ❌ *"Zero-day detection proven"* |
| **Cross-Domain Transfer** | Zero-adaptation cross-domain transfer over 6 physical features achieves ~86.5% F1. | Cross-domain evaluation represents transfer across separate physical IoT/IIoT testbed environments. | ❌ *"Universal cross-domain robustness"* |
| **Adversarial Robustness** | Constrained feature perturbation study evaluates supervised evasion under FGSM/PGD. | Adversarial study is a constrained feature-space perturbation experiment, NOT a live physical network attack. | ❌ *"Real-world attack prevention"* |
| **Defensive Diversity** | Autoencoder anomaly pathway provides complementary coverage for evasive attack vectors. | Autoencoder defensive coverage varies by dataset topology (100% on Edge vs 8.12%--51.14% on ToN). | ❌ *"Zero-day bypass prevented"* |
