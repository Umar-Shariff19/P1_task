# FRESH CROSS-DOMAIN EVALUATION RESULTS

> **Evaluation Pathway**: Zero-adaptation cross-domain evaluation using clean 6-feature F_common space (`duration`, `src_bytes`, `proto_tcp`, `proto_udp`, `proto_icmp`, `is_well_known_port`). No target labels, target retraining, or target adaptation.

---

## 1. EDGE-IIOTSET -> TON-IOT CROSS-DOMAIN FRESH RESULTS (6 Features, N=42,209)

- **Random Forest Only**: Accuracy = 77.82%, F1 = 87.31%, ROC AUC = 0.8547
- **MLP Only**: Accuracy = 74.34%, F1 = 85.26%, ROC AUC = 0.4327
- **Supervised Ensemble (P_sup)**:
  - **Accuracy**: 76.3250% (Rounded: **76.32%**)
  - **Precision**: 76.3323% (Rounded: **76.33%**)
  - **Recall**: 99.9721% (Rounded: **99.97%**)
  - **Attack F1**: 86.5673% (Rounded: **86.57%**)
  - **Macro F1**: 43.4432% (Rounded: **43.44%**)
  - **ROC AUC**: 0.809287 (Rounded: **0.8093**)
  - **PR AUC**: 0.941281 (Rounded: **0.9413**)
  - **Confusion Matrix**: TP=32200, FP=9984, TN=16, FN=9

---

## 2. TON-IOT -> EDGE-IIOTSET CROSS-DOMAIN FRESH RESULTS (6 Features, N=31,560)

- **Random Forest Only**: Accuracy = 77.01%, F1 = 86.48%, ROC AUC = 0.7073
- **MLP Only**: Accuracy = 75.46%, F1 = 85.10%, ROC AUC = 0.6503
- **Supervised Ensemble (P_sup)**:
  - **Accuracy**: 77.9404% (Rounded: **77.94%**)
  - **Precision**: 86.9986% (Rounded: **87.00%**)
  - **Recall**: 86.9139% (Rounded: **86.91%**)
  - **Attack F1**: 86.9562% (Rounded: **86.96%**)
  - **Macro F1**: 57.7609% (Rounded: **57.76%**)
  - **ROC AUC**: 0.721309 (Rounded: **0.7213**)
  - **PR AUC**: 0.949455 (Rounded: **0.9495**)
  - **Confusion Matrix**: TP=23206, FP=3468, TN=1392, FN=3494
