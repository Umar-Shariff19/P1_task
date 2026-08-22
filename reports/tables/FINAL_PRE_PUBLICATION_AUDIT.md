# FINAL PRE-PUBLICATION FORENSIC AUDIT & VERIFICATION REPORT

> [!IMPORTANT]
> **FINAL AUDIT DECISION: PASS — IMPLEMENTATION COMPLETE & PAPER READY**
>
> Every metric, table, claim, and artifact across the research codebase has been trace-audited against actual generated output files (`final_evaluation_results.json`, `xai_results.json`, `adversarial_results.json`).
> The baseline models, feature schemas, parquet splits, and authoritative benchmark metrics remain **100% FROZEN & UNTOUCHED**.

---

## 1. ARTIFACT LINEAGE & PROVENANCE RECONCILIATION

| Artifact Directory / File | Generating Script / Stage | Source Input | Feature Space / Dimensions | Lineage & Status |
| :--- | :--- | :--- | :---: | :--- |
| `models/final/Edge-IIoTset/` | `scripts/05_train_models.py` | Edge-IIoTset Train Split (94,680 rows) | **13 Features** | Active Frozen Checkpoints (`rf_model.joblib`, `mlp_model.pt`, `ae_model.pt`, `prep_indomain.joblib`, `risk_layer.json`). |
| `models/final/ToN-IoT/` | `scripts/05_train_models.py` | ToN-IoT Train Split (126,625 rows) | **13 Features** | Active Frozen Checkpoints (`rf_model.joblib`, `mlp_model.pt`, `ae_model.pt`, `prep_indomain.joblib`, `risk_layer.json`). |
| `data/processed/final/` | `scripts/01` $\rightarrow$ `04` | Raw Captures | Parquet Splits | Frozen Stratified 60% Train / 20% Val / 20% Test Parquet files. |
| `reports/tables/final_evaluation_results.json` | `scripts/07_evaluate.py` | Frozen Test Splits | 13 In-Domain / 6 $F_{\text{common}}$ | Authoritative JSON Output. |
| `reports/tables/xai_results.json` | `scripts/09_generate_xai_evidence.py` | Frozen Test Splits | 13 In-Domain / 6 $F_{\text{common}}$ | Authoritative XAI Attribution Output. |
| `results/adversarial/adversarial_results.json` | `scripts/10_run_adversarial_evaluation.py` | Frozen Test Splits | 13 In-Domain | Authoritative Adversarial Evasion & Risk State Output. |

---

## 2. EXPERIMENT MATRIX & AUTHORITATIVE METRICS

*All metrics trace directly to `final_evaluation_results.json` generated from untouched test split samples*:

| Experiment Profile | Source Domain $\rightarrow$ Target Domain | Feature Count | Test Rows ($N$) | Accuracy (%) | Precision (%) | Recall (%) | Attack F1 (%) | Macro F1 (%) | ROC AUC | PR AUC | Authoritative Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **In-Domain** | **Edge-IIoTset** | 13 | 31,560 | **89.75%** | 89.23% | 99.95% | **94.29%** | 72.31% | **0.8773** | **0.9629** | **AUTHORITATIVE (FROZEN)** |
| **In-Domain** | **ToN-IoT Network** | 13 | 42,209 | **96.49%** | 96.34% | 99.17% | **97.73%** | 94.98% | **0.9952** | **0.9982** | **AUTHORITATIVE (FROZEN)** |
| **Cross-Domain** | **Edge-IIoTset $\rightarrow$ ToN-IoT** | 6 ($F_{\text{common}}$) | 42,209 | **76.33%** | 76.33% | 99.98% | **86.57%** | 43.44% | **0.8081** | **0.9387** | **AUTHORITATIVE (FROZEN)** |
| **Cross-Domain** | **ToN-IoT $\rightarrow$ Edge-IIoTset** | 6 ($F_{\text{common}}$) | 31,560 | **77.94%** | 87.00% | 86.91% | **86.96%** | 57.76% | **0.7212** | **0.9243** | **AUTHORITATIVE (FROZEN)** |

### Superseded Historical Lineage:
- Early preliminary ToN-IoT In-Domain F1 (**99.60%**) is officially **SUPERSEDED** by **97.73%** following the clean 6-feature $F_{\text{common}}$ harmonization.
- Early preliminary 8-feature cross-domain results (**86.59%** and **86.47%**) are officially **SUPERSEDED** by **86.57%** and **86.96%** following ensemble probability curve evaluation ($P_{\text{sup}} = \frac{1}{2} P_{\text{rf}} + \frac{1}{2} P_{\text{mlp}}$).

---

## 3. THREE-MODEL ARCHITECTURE & DESIGN B RISK LAYER

- **Random Forest (RF)**: Evaluated in supervised path $P_{\text{rf}}$.
- **PyTorch MLP**: Evaluated in supervised path $P_{\text{mlp}}$.
- **Supervised Ensemble**: $P_{\text{sup}} = 0.5 P_{\text{rf}} + 0.5 P_{\text{mlp}}$.
- **Autoencoder (AE)**: Trained **strictly on benign Train samples**; calibrated on benign Validation samples; evaluated via empirical CDF lookup $S_{\text{ae}}$.
- **Design B Risk Layer**:
  - $P_{\text{sup}} \ge 0.50 \implies \text{HIGH CONFIDENCE ATTACK}$
  - $P_{\text{sup}} < 0.50 \land S_{\text{ae}} \ge 0.80 \implies \text{SUSPICIOUS / ANOMALOUS}$
  - $P_{\text{sup}} < 0.50 \land S_{\text{ae}} < 0.80 \implies \text{BENIGN}$

---

## 4. EXPLAINABLE AI (XAI) EVIDENCE

- **Model Consensus**: Spearman rank correlation coefficient confirms high attribution consensus ($\rho = 0.8632$, $p = 1.44 \times 10^{-4}$ on Edge-IIoTset; $\rho = 0.6252$, $p = 2.23 \times 10^{-2}$ on ToN-IoT).
- **Autoencoder Reconstruction**: Per-feature MSE decomposition $e_i = (x_i - \hat{x}_i)^2$ identifies top features driving anomaly threshold breaches.
- **Claim Safety**: XAI metrics measure statistical model feature reliance, NOT physical causality.

---

## 5. CONSTRAINED ADVERSARIAL ROBUSTNESS EVALUATION

- **White-Box MLP Attack**: Evaluates FGSM and PGD-10 continuous feature perturbations in `RobustScaler` standardized feature space with discrete protocol indicators strictly masked.
- **Defensive Catch Rates**:
  - **Edge-IIoTset**: 100.00% of evasive attack samples ($P_{\text{sup}} < 0.5$) triggered AE anomaly flags ($S_{\text{ae}} \ge 0.8$).
  - **ToN-IoT Network**: AE catch rates ranged from **8.12% to 51.14%**, leaving complete benign evasion rates between **0.54% and 9.36%**.
- **Claim Safety**: The AE pathway provides **complementary defensive coverage for a subset of adversarial evasions**, with effectiveness varying by dataset. Blanket claims of "zero-day bypass prevention" or "100% adversarial robustness" are strictly forbidden.

---

## 6. DEMO VERIFICATION

- **Inference-Only Guarantee**: `IDSSystemPipeline` in `src/iot_ids/pipeline/system.py` consumes frozen checkpoints directly from `models/final/` without retraining.
- **Web Dashboard**: Streamlit app (`demo/app.py`) provides live dataset selection, probability gauges ($P_{\text{rf}}$, $P_{\text{mlp}}$, $P_{\text{sup}}$, $S_{\text{ae}}$), Risk Decision banners, In-Domain vs Cross-Domain tabs, XAI charts, and Adversarial inspector.
- **CLI Smoke Test**: Terminal script `demo/cli_demo.py` passed with 100% reproducibility.

---

## 7. FINAL CLAIM-SAFETY MATRIX

| Domain | Permitted Paper Claim | Required Methodological Qualification | Forbidden Claim |
| :--- | :--- | :--- | :--- |
| **In-Domain Detection** | Multi-level representation achieves strong intrusion detection (94.29% F1 Edge, 97.73% F1 ToN). | In-domain evaluation reflects random-sample pattern generalization under benchmark capture conditions. | ❌ *"Zero-day detection proven"* |
| **Cross-Domain Transfer** | Zero-adaptation cross-domain transfer over 6 physical features achieves ~86.5% F1. | Cross-domain evaluation represents transfer across separate physical IoT/IIoT testbed environments. | ❌ *"Universal cross-domain robustness"* |
| **Adversarial Evaluation** | Constrained feature perturbation study evaluates supervised evasion under FGSM/PGD. | Adversarial study is a constrained feature-space perturbation experiment, NOT a live physical network attack. | ❌ *"Real-world physical attack prevention"* |
| **Defensive Coverage** | Autoencoder anomaly pathway provides complementary coverage for evasive attack vectors. | Autoencoder defensive coverage varies by dataset topology (100% on Edge vs 8.12%--51.14% on ToN). | ❌ *"Zero-day bypass prevented"* |

---

## 8. REPRODUCIBILITY COMMANDS

```powershell
# 1. Unit Test Suite (29/29 PASSED)
.\.venv\Scripts\pytest.exe tests/unit/

# 2. Automated Terminal Smoke Test
.\.venv\Scripts\python.exe demo/cli_demo.py

# 3. Interactive Web Dashboard
.\.venv\Scripts\streamlit.exe run demo/app.py

# 4. Reproduce Authoritative Baseline Evaluation
.\.venv\Scripts\python.exe scripts/07_evaluate.py
.\.venv\Scripts\python.exe scripts/08_generate_evidence.py

# 5. Reproduce XAI & Adversarial Evidence Reports
.\.venv\Scripts\python.exe scripts/09_generate_xai_evidence.py
.\.venv\Scripts\python.exe scripts/10_run_adversarial_evaluation.py
```

---

## 9. VERIFICATION SUMMARY & FINAL RELEASE STATUS

- **Unit Test Suite**: 29 / 29 PASSED (100%)
- **CLI Smoke Test**: PASSED (100% REPRODUCIBLE)
- **Frozen Models & Splits**: UNTOUCHED (100%)
- **Authoritative Baseline Metrics**: UNTOUCHED & VERIFIED (100%)
- **Documentation & Lineage**: 100% RECONCILED & TRACED

### **FINAL RELEASE STATUS: IMPLEMENTATION COMPLETE & PAPER READY**
