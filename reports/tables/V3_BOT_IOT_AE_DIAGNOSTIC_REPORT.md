# V3 Phase 4B — BoT-IoT Autoencoder Diagnostic & Forensic Report

> [!CAUTION]
> **PIPELINE HALTED BY STOP CONDITION**: Autoencoder threshold optimization for BoT-IoT produced `best_threshold = inf` (Infinity). As mandated by scientific execution rules, execution has been **STOPPED** to present a formal forensic diagnosis and request explicit user approval before modifying methodology.

---

## 1. The Defect

During Phase 4B-3 Autoencoder training and validation threshold optimization on **BoT-IoT**, the ROC curve Youden's J statistic ($J = \text{TPR} - \text{FPR}$) produced `best_threshold = inf`. 

Because an infinite threshold classifies 100% of samples as non-anomalous (benign), the Autoencoder yields a degenerate all-zero prediction vector, making it impossible to fuse into the ensemble using a standard probability threshold.

---

## 2. Why It Is a Defect / Scientific Cause

1. **Extreme Class Imbalance**:
   The BoT-IoT validation set contains **2,750,000 total rows**, comprising **2,749,889 Attack rows** (99.996%) and only **111 Benign rows** (0.004%).

2. **Reconstruction Error Inversion**:
   Empirical inspection of the reconstruction Mean Squared Error (MSE) across the validation set revealed:
   - **Benign Validation MSE**: Mean = `9.0801`, Std = `13.9965`, Max = `112.5880`
   - **Attack Validation MSE**: Mean = `0.3992`, Std = `0.1325`, Max = `21.0876`

   *Why does this happen?* BoT-IoT attack traffic consists of massive, highly uniform DoS/DDoS packet floods with constant length and rate fields. The Autoencoder easily reconstructs these low-entropy repetitive patterns with near-zero error (`0.3992` mean). Conversely, the 7,302 benign training flows are diverse, causing higher reconstruction errors (`9.0801` mean) on unseen benign validation traffic.

3. **Mathematical ROC Optimization Failure**:
   `roc_curve` assumes higher MSE corresponds to the attack class (`y_true = 1`). Because benign flows have higher MSE than attack flows, lowering the decision threshold increases False Positive Rate (FPR) much faster than True Positive Rate (TPR). Consequently, $J = \text{TPR} - \text{FPR} \le 0$ for all finite thresholds. The global maximum of $J$ occurs at index 0 ($J = 0.0$), where `threshold = inf` and FPR = 0, TPR = 0.

---

## 3. Exact Proposed Correction Options

| Option | Proposed Strategy | Technical Execution | Impact on Scientific Semantics |
| :--- | :--- | :--- | :--- |
| **Option A (Recommended)** | **Exclude AE from BoT-IoT Ensemble ($w_{\text{ae}} = 0$)** | Train RF and MLP normally. Set $w_{\text{ae}} = 0.0$ for BoT-IoT in validation grid search (simplex $w_{\text{rf}} + w_{\text{mlp}} = 1.0$). Keep AE active for CICIDS2017, Edge-IIoTset, and N-BaIoT. | **None**. Preserves standard threshold optimization without inventing artificial rules. Accurately reports that unsupervised AE fails on BoT-IoT DoS traffic. |
| **Option B** | **Benign Percentile Thresholding** | Set AE threshold $\tau$ to the 95th percentile of benign validation MSE ($\tau \approx 15.2$). | Changes threshold selection methodology specifically for BoT-IoT from ROC Youden's J to benign quantile thresholding. |
| **Option C** | **Inverted Anomaly Direction** | Evaluate anomaly score as $-\text{MSE}$ for BoT-IoT AE. | Inverts model anomaly definition specifically for BoT-IoT. |

---

## 4. Status of Completed Component Models

Prior to the halt, the following component models completed training cleanly and are saved in `models/v3/`:

- **Random Forest (4/4 Completed)**:
  - `CICIDS2017`: Val Acc 0.9856, F1 0.0303 (Macro-F1: 0.5115)
  - `Edge-IIoTset`: Val Acc 1.0000, F1 1.0000 (Macro-F1: 0.9999)
  - `BoT-IoT`: Val Acc 1.0000, F1 1.0000 (Macro-F1: 0.9583)
  - `N-BaIoT`: Val Acc 0.9972, F1 0.9985 (Macro-F1: 0.9890)

- **MLP (4/4 Completed)**:
  - `CICIDS2017`: Val Acc 0.9474, F1 0.0039 (Macro-F1: 0.4884)
  - `Edge-IIoTset`: Val Acc 0.6672, F1 0.7595 (Macro-F1: 0.6096)
  - `BoT-IoT`: Val Acc 0.9999, F1 1.0000 (Macro-F1: 0.7723)
  - `N-BaIoT`: **CRITICAL CHECK PASSED** — Full 4,618,002 rows streamed per epoch. Val Acc 0.9889, F1 0.9940 (Macro-F1: 0.9541).

- **Autoencoders (3/4 Completed)**:
  - `CICIDS2017`: Threshold `0.000959`, Val Acc 0.5914, F1 0.0525 (Macro-F1: 0.3960)
  - `Edge-IIoTset`: Threshold `0.011586`, Val Acc 0.8087, F1 0.8754 (Macro-F1: 0.7319)
  - `BoT-IoT`: **HALTED** (`best_threshold = inf`)
  - `N-BaIoT`: Pending resolution of BoT-IoT AE threshold.

---

> [!IMPORTANT]
> **AWAITING USER DECISION**: Please indicate which option (Option A, Option B, or Option C) you approve to resolve the BoT-IoT Autoencoder threshold.
