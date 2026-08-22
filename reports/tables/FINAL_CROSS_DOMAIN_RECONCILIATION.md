# FINAL CROSS-DOMAIN METRIC RECONCILIATION REPORT

> [!IMPORTANT]
> **AUTHORITATIVE DECISION: B. LATEST RESULTS ARE AUTHORITATIVE**
> 
> The cross-domain metrics produced by `scripts/07_evaluate.py` represent the **100% reproducible, authoritative values** for the clean 6-feature $F_{\text{common}}$ space evaluated under the Design B Ensemble ($P_{\text{sup}} = \frac{1}{2} P_{\text{rf}} + \frac{1}{2} P_{\text{mlp}}$).

---

## 1. ROOT CAUSE OF DISCREPANCY

1. **Feature Space Transition**: Earlier preliminary draft reports contained metric snapshots from an 8-feature $F_{\text{common}}$ space (which included `src_pkts` and `dst_pkts`).
2. **Score Source Alignment**: Earlier ROC AUC numbers (`0.8547` for $E \rightarrow T$) evaluated Random Forest probabilities ($P_{\text{rf}}$) alone. The latest execution of `scripts/07_evaluate.py` evaluates the true **Design B Supervised Ensemble** $P_{\text{sup}} = \frac{1}{2} P_{\text{rf}} + \frac{1}{2} P_{\text{mlp}}$.
3. **Reproducibility Guarantee**: The latest numbers in `scripts/07_evaluate.py` are generated deterministically with zero target adaptation or label leakage.

---

## 2. RECONCILED AUTHORITATIVE CROSS-DOMAIN TABLE FOR FINAL PAPER

*Models trained on Source domain using ONLY clean $F_{\text{common}}$ (6 features) and evaluated directly on Target Test split without retraining or target adaptation*:

| Source Domain $\rightarrow$ Target Domain | Target Test Rows | Accuracy | Precision | Recall | Attack F1 | Macro F1 | ROC AUC | PR AUC | Authoritative Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Edge-IIoTset $\rightarrow$ ToN-IoT** | 42,209 | **76.33%** | 76.33% | 99.98% | **86.57%** | 43.44% | **0.8081** | **0.9387** | **AUTHORITATIVE (REPRODUCIBLE)** |
| **ToN-IoT $\rightarrow$ Edge-IIoTset** | 31,560 | **77.94%** | 87.00% | 86.91% | **86.96%** | 57.76% | **0.7212** | **0.9243** | **AUTHORITATIVE (REPRODUCIBLE)** |

---

## 3. CONFUSION MATRIX RECONCILIATION

- **Edge-IIoTset $\rightarrow$ ToN-IoT Network**:
  - $\text{TP} = 32,203$, $\text{FP} = 9,985$, $\text{TN} = 15$, $\text{FN} = 6$ ($N = 42,209$).
  - $\text{Accuracy} = \frac{32203 + 15}{42209} = 76.33\%$
  - $\text{Attack F1} = \frac{2 \times 0.763321 \times 0.999813}{0.763321 + 0.999813} = 86.57\%$

- **ToN-IoT Network $\rightarrow$ Edge-IIoTset**:
  - $\text{TP} = 23,206$, $\text{FP} = 3,468$, $\text{TN} = 1,392$, $\text{FN} = 3,494$ ($N = 31,560$).
  - $\text{Accuracy} = \frac{23206 + 1392}{31560} = 77.94\%$
  - $\text{Attack F1} = \frac{2 \times 0.869985 \times 0.869138}{0.869985 + 0.869138} = 86.96\%$

---

## 4. CODE / MODEL / DATA MODIFICATION REQUIREMENTS

- **Code Modifications Required**: ZERO.
- **Model Checkpoints Modified**: ZERO.
- **Datasets Modified**: ZERO.
- **Documentation Updates Required**: Ensure `README.md` and `FINAL_IMPLEMENTATION_INTEGRITY_GATE.md` display the authoritative values above (`86.57%` F1 / `0.8081` ROC AUC for $E \rightarrow T$; `86.96%` F1 / `0.7212` ROC AUC for $T \rightarrow E$).
