# FROZEN BASELINE VERIFICATION REPORT

> **Primary Source File**: `reports/tables/final_evaluation_results.json`  
> **Evaluation Pathway**: `scripts/07_evaluate.py` over frozen model checkpoints (`models/final/`) and test split parquets (`data/processed/final/`).

---

## 1. IN-DOMAIN FROZEN BASELINE METRICS

### Edge-IIoTset In-Domain (13 Features, 31,560 Test Rows):
- **Accuracy**: `89.7497%` (Rounded: **89.75%**)
- **Precision**: `89.2299%` (Rounded: **89.23%**)
- **Recall**: `99.9476%` (Rounded: **99.95%**)
- **Attack F1**: `94.2852%` (Rounded: **94.29%**)
- **Macro F1**: `72.3076%` (Rounded: **72.31%**)
- **ROC AUC**: `0.877332` (Rounded: **0.8773**)
- **PR AUC**: `0.962943` (Rounded: **0.9629**)

### ToN-IoT Network In-Domain (13 Features, 42,209 Test Rows):
- **Accuracy**: `96.4889%` (Rounded: **96.49%**)
- **Precision**: `96.3384%` (Rounded: **96.34%**)
- **Recall**: `99.1679%` (Rounded: **99.17%**)
- **Attack F1**: `97.7327%` (Rounded: **97.73%**)
- **Macro F1**: `94.9774%` (Rounded: **94.98%**)
- **ROC AUC**: `0.995196` (Rounded: **0.9952**)
- **PR AUC**: `0.998176` (Rounded: **0.9982**)

---

## 2. CROSS-DOMAIN FROZEN BASELINE METRICS (F_common - 6 Features)

### Edge-IIoTset -> ToN-IoT (6 Features, 42,209 Target Test Rows):
- **Accuracy**: `76.3297%` (Rounded: **76.33%**)
- **Precision**: `76.3321%` (Rounded: **76.33%**)
- **Recall**: `99.9814%` (Rounded: **99.98%**)
- **Attack F1**: `86.5707%` (Rounded: **86.57%**)
- **Macro F1**: `43.4350%` (Rounded: **43.44%**)
- **ROC AUC**: `0.808078` (Rounded: **0.8081**)
- **PR AUC**: `0.938750` (Rounded: **0.9387**)

### ToN-IoT -> Edge-IIoTset (6 Features, 31,560 Target Test Rows):
- **Accuracy**: `77.9404%` (Rounded: **77.94%**)
- **Precision**: `86.9986%` (Rounded: **87.00%**)
- **Recall**: `86.9139%` (Rounded: **86.91%**)
- **Attack F1**: `86.9562%` (Rounded: **86.96%**)
- **Macro F1**: `57.7609%` (Rounded: **57.76%**)
- **ROC AUC**: `0.721250` (Rounded: **0.7212**)
- **PR AUC**: `0.924329` (Rounded: **0.9243**)

---

## 3. EXPECTED VS ACTUAL DISCREPANCY CHECK

- **In-Domain**: All metrics match expected authoritative values 100% exactly.
- **Cross-Domain**: Metrics match the authoritative reconciled values in `FINAL_CROSS_DOMAIN_RECONCILIATION.md` (`86.57%` F1 / `0.8081` ROC AUC for E -> T; `86.96%` F1 / `0.7212` ROC AUC for T -> E).
- **Discrepancy Verdict**: **ZERO DISCREPANCY**. Baseline verification PASSED.
