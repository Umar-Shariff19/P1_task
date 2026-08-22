# FRESH IN-DOMAIN EVALUATION RESULTS

> **Evaluation Pathway**: Freshly trained models from `reproducibility/fresh_retraining_20260821_010000/run1/` evaluated on untouched Test split parquets (`data/processed/final/`).

---

## 1. EDGE-IIOTSET IN-DOMAIN FRESH RESULTS (13 Features, N=31,560)

- **Random Forest Only**: Accuracy = `89.81%`, F1 = `94.32%`, ROC AUC = `0.8828`
- **MLP Only**: Accuracy = `89.14%`, F1 = `93.93%`, ROC AUC = `0.8749`
- **Supervised Ensemble (P_sup)**:
  - **Accuracy**: `89.7592%` (Rounded: **89.76%**)
  - **Precision**: `89.2232%` (Rounded: **89.22%**)
  - **Recall**: `99.9700%` (Rounded: **99.97%**)
  - **Attack F1**: `94.2914%` (Rounded: **94.29%**)
  - **Macro F1**: `72.2994%` (Rounded: **72.30%**)
  - **ROC AUC**: `0.877398` (Rounded: **0.8774**)
  - **PR AUC**: `0.979030` (Rounded: **0.9790**)
  - **Confusion Matrix**: TP=26692, FP=3224, TN=1636, FN=8

---

## 2. TON-IOT NETWORK IN-DOMAIN FRESH RESULTS (13 Features, N=42,209)

- **Random Forest Only**: Accuracy = `97.39%`, F1 = `98.28%`, ROC AUC = `0.9967`
- **MLP Only**: Accuracy = `95.15%`, F1 = `96.86%`, ROC AUC = `0.9878`
- **Supervised Ensemble (P_sup)**:
  - **Accuracy**: `96.5268%` (Rounded: **96.53%**)
  - **Precision**: `96.4129%` (Rounded: **96.41%**)
  - **Recall**: `99.1369%` (Rounded: **99.14%**)
  - **Attack F1**: `97.7559%` (Rounded: **97.76%**)
  - **Macro F1**: `95.0383%` (Rounded: **95.04%**)
  - **ROC AUC**: `0.995180` (Rounded: **0.9952**)
  - **PR AUC**: `0.998450` (Rounded: **0.9984**)
  - **Confusion Matrix**: TP=31931, FP=1188, TN=8812, FN=278
