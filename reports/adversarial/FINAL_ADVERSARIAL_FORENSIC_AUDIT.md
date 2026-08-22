# FINAL ADVERSARIAL VALIDITY & CLAIM SAFETY AUDIT REPORT

> [!IMPORTANT]
> **FINAL AUDIT DECISION: C. EXPERIMENT VALID BUT CLAIMS MUST BE WEAKENED**
> 
> The adversarial experiment is **100% mathematically valid, reproducible, and correctly executed** with discrete feature masking and domain clamping. However, scientific claims in the markdown reports must be **weakened and qualified** to accurately reflect dataset differences (100% AE catch rate on Edge-IIoTset vs 8.1%--51.1% catch rate on ToN-IoT) and to clarify that perturbations occur in **standardized feature space**.

---

## 1. ATTACK OBJECTIVE & METHODOLOGY CLASSIFICATION

- **Loss Function**: `nn.BCEWithLogitsLoss()` evaluated against true binary labels ($Y_{\text{true}}$).
- **Gradient Generation**: White-box backpropagation generated strictly through the differentiable `MLPModule`.
- **Classification**: **White-box MLP gradient attack with transfer evaluation against Random Forest and the Design B Risk Layer**.
- **Discrete Feature Masking**: Gradients for binary protocol indicators (`proto_tcp`, `proto_udp`, `proto_icmp`, `is_well_known_port`, `mqtt_msgtype`, `mbtcp_unit_id`, `conn_state_encoded`, `http_method_encoded`) were 100% masked ($\nabla_x \mathcal{L} \odot M_{\text{cont}}$).

---

## 2. RECONCILED AUTHORITATIVE ADVERSARIAL EVIDENCE TABLE

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

## 3. MANDATORY PAPER CLAIM QUALIFICATIONS

| Previous Strong Claim | Corrected Authoritative Claim | Scientific Rationale |
| :--- | :--- | :--- |
| *"Defensive Diversity Proven"* | **"The AE pathway provided complementary anomaly detection for a subset of adversarial evasions, with effectiveness varying by dataset."** | AE catch rate is 100.00% on Edge-IIoTset but ranges from 8.12% to 51.14% on ToN-IoT. Blanket proof claims are invalid for ToN-IoT. |
| *"Preventing zero-day bypass"* | **"The anomaly pathway reclassifies evasive attack vectors as suspicious anomaly indicators."** | Evasive samples on ToN-IoT still achieve complete benign prediction in 0.54%--9.36% of cases. Zero-day bypass prevention is not 100%. |
| *"Physically realized attack"* | **"Constrained feature-space adversarial perturbation study."** | Continuous derived features were perturbed directly in feature space without recalculating sequence state. |
| *"Epsilon perturbation"* | **"Perturbation magnitude $\epsilon$ in median/IQR standardized feature space."** | $\epsilon$ is specified over `RobustScaler` standardized feature vectors clamped to $[x_{\text{min}}, x_{\text{max}}]$. |

---

## 4. BASELINE & CHECKSUM INTEGRITY

- **Baseline Preservation**: `models/final/`, `data/processed/final/`, and `reports/tables/FINAL_*.md` were **100% UNTOUCHED**.
- **Isolated Adversarial Artifacts**: Stored strictly in `reports/adversarial/` and `results/adversarial/`.

---

## 5. FINAL SCIENTIFIC AUDIT VERDICT

### **VERDICT: C. EXPERIMENT VALID BUT CLAIMS MUST BE WEAKENED**

The adversarial evaluation is scientifically valid, 100% reproducible, and provides strong empirical evidence for the paper. The required claim qualifications above are incorporated into `reports/adversarial/FINAL_ADVERSARIAL_EVIDENCE.md`.
