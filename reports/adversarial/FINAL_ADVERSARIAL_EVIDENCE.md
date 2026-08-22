# FINAL ADVERSARIAL ROBUSTNESS & DEFENSIVE DIVERSITY REPORT

> [!IMPORTANT]
> **FINAL AUDIT DECISION: C. EXPERIMENT VALID BUT CLAIMS MUST BE WEAKENED**
>
> Evaluation of constrained feature-space gradient perturbations (FGSM and PGD-10 across $\epsilon \in \{0.05, 0.10, 0.20, 0.30\}$ in `RobustScaler` standardized feature space) against frozen model checkpoints (**Edge-IIoTset** and **ToN-IoT Network**). Discrete binary features were 100% masked and unperturbed.

---

## 1. RECONCILED AUTHORITATIVE ADVERSARIAL EVIDENCE TABLE

*Evaluated over all $N$ originally correctly predicted attack samples ($Y=1$)*:

| Dataset | Attack Method | Epsilon ($\epsilon$) | Attacked Samples ($N$) | Supervised Evaded ($P_{\text{sup}} < 0.5$) | Supervised ASR (%) | Suspicious Evaded (AE Catch) | AE Catch Rate (%) | Complete Evasion (Benign Evaded) | Complete Evasion Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Edge-IIoTset** | FGSM | 0.05 | 26,686 | 25 | 0.09% | 25 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | PGD-10 | 0.05 | 26,686 | 25 | 0.09% | 25 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | FGSM | 0.10 | 26,686 | 30 | 0.11% | 30 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | PGD-10 | 0.10 | 26,686 | 817 | 3.06% | 817 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | FGSM | 0.20 | 26,686 | 4 | 0.01% | 4 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | PGD-10 | 0.20 | 26,686 | 1,561 | 5.85% | 1,561 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | FGSM | 0.30 | 26,686 | 493 | 1.85% | 493 | **100.00%** | 0 | **0.00%** |
| **Edge-IIoTset** | PGD-10 | 0.30 | 26,686 | 2,281 | 8.55% | 2,281 | **100.00%** | 0 | **0.00%** |
| **ToN-IoT** | FGSM | 0.05 | 31,941 | 217 | 0.68% | 43 | **19.82%** | 174 | **0.54%** |
| **ToN-IoT** | PGD-10 | 0.05 | 31,941 | 247 | 0.77% | 45 | **18.22%** | 202 | **0.63%** |
| **ToN-IoT** | FGSM | 0.10 | 31,941 | 498 | 1.56% | 76 | **15.26%** | 422 | **1.32%** |
| **ToN-IoT** | PGD-10 | 0.10 | 31,941 | 704 | 2.20% | 82 | **11.65%** | 622 | **1.95%** |
| **ToN-IoT** | FGSM | 0.20 | 31,941 | 646 | 2.02% | 259 | **40.09%** | 387 | **1.21%** |
| **ToN-IoT** | PGD-10 | 0.20 | 31,941 | 3,253 | 10.18% | 264 | **8.12%** | 2,989 | **9.36%** |
| **ToN-IoT** | FGSM | 0.30 | 31,941 | 1,095 | 3.43% | 560 | **51.14%** | 535 | **1.68%** |
| **ToN-IoT** | PGD-10 | 0.30 | 31,941 | 3,339 | 10.45% | 647 | **19.38%** | 2,692 | **8.43%** |

---

## 2. DEFENSIVE DIVERSITY & RISK LAYER ANALYSIS

- **White-Box MLP Attack**: Gradient perturbations are generated against the differentiable `MLPModule` and evaluated for transfer against Random Forest and the Design B Risk Layer.
- **Complementary Anomaly Catching**: The independent anomaly pathway provided complementary defensive coverage for a subset of adversarial evasions, with effectiveness varying substantially across datasets:
  - **Edge-IIoTset**: 100.00% of evasive attack samples ($P_{\text{sup}} < 0.5$) triggered AE reconstruction error spikes ($S_{\text{ae}} \ge 0.8$), reclassifying 100% of evasive attacks as `SUSPICIOUS / ANOMALOUS` (0 complete evasions).
  - **ToN-IoT Network**: AE catch rates range from **8.12% to 51.14%**, leaving complete benign evasion rates between **0.54% and 9.36%**.

---

## 3. METHODOLOGICAL QUALIFICATIONS

1. **Constrained Feature-Space Perturbation**: Perturbations occur in continuous feature space with discrete protocol indicators strictly masked and continuous features clamped to training min/max bounds $[x_{\text{min}}, x_{\text{max}}]$.
2. **Epsilon Space**: Perturbation magnitude $\epsilon$ is specified in `RobustScaler` standardized feature space.
3. **Baseline Integrity**: Baseline model files in `models/final/` and baseline evidence reports in `reports/tables/FINAL_*.md` remained **100% UNTOUCHED**.
