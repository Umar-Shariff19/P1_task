# AUTHORITATIVE PAPER CLAIMS MATRIX

> [!IMPORTANT]
> **PAPER CLAIM CONTROL & SAFETY CONTRACT**
>
> This matrix governs all scientific claims made in the research paper, technical reports, and demonstration slides. Only claims in the **SAFE CLAIMS** section are permitted without qualification.

---

## 1. SAFE CLAIMS (FULL EMPIRICAL EVIDENCE SUPPORTED)

| Claim Category | Safe Claim Statement | Supporting Empirical Evidence |
| :--- | :--- | :--- |
| **Feature Representation** | Multi-Level IoT Representation combining static physical flow attributes, causal temporal counts/rates, and behavioral destination diversity. | In-domain ablation studies show consistent F1 improvements across all feature levels. |
| **In-Domain Intrusion Detection** | High-precision intrusion detection on Edge-IIoTset (94.29% Attack F1) and ToN-IoT Network (97.73% Attack F1). | Evaluated on 31,560 and 42,209 untouched test split samples respectively. |
| **Cross-Domain Transferability** | Zero-adaptation cross-domain transfer over 6 harmonized physical network features ($F_{\text{common}}$) achieves ~86.5% Attack F1 ($E \rightarrow T$ and $T \rightarrow E$). | Cross-domain models evaluated directly on target testbed without fine-tuning or target domain labels. |
| **Explainability** | High model rank-correlation consensus between Random Forest and MLP classifiers ($\rho = 0.8632$ on Edge-IIoTset). | Permutation importance and per-feature Autoencoder error decompositions ($e_i = (x_i - \hat{x}_i)^2$). |
| **Constrained Feature Perturbation** | Constrained continuous feature perturbation study demonstrates supervised classifier evasion under FGSM/PGD attacks. | FGSM and PGD-10 evaluations across $\epsilon \in \{0.05, 0.10, 0.20, 0.30\}$ in `RobustScaler` space. |

---

## 2. REQUIRED QUALIFICATIONS (MANDATORY PAPER METHODOLOGY NOTES)

| Domain / Experiment | Required Methodological Qualification | Scientific Rationale |
| :--- | :--- | :--- |
| **Edge-IIoTset Benchmarking** | In-domain evaluation represents **random-sample benchmark pattern generalization** under high-frequency flood traffic (`ML-EdgeIIoT-dataset.csv`). | High-rate DDoS floods generate repeated packet header patterns across random splits. |
| **Cross-Domain Evaluation** | Cross-domain evaluation represents **cross-environment transfer over harmonized physical features ($F_{\text{common}}$)**. | Evaluation occurs across physically separate testbeds with distinct device topologies and IP subnets. |
| **Adversarial Evaluation** | Adversarial study is a **constrained feature-space perturbation experiment**, NOT a physically deployed packet-injection attack. | Continuous features were perturbed directly in feature space with discrete protocol indicators strictly masked. |
| **Defensive Diversity** | Autoencoder anomaly catch rates vary substantially across datasets (100.0% on Edge-IIoTset vs 8.1%--51.1% on ToN-IoT). | AE complementary anomaly coverage is dataset-dependent; complete benign evasions occur in 0.54%--9.36% of cases on ToN-IoT. |
| **Anomaly Pathway** | Autoencoder anomaly flags ($S_{\text{ae}} \ge 0.8$) are **unsupervised anomaly indications**, NOT empirical proof of zero-day attack detection. | Test splits contain known attack categories from benchmark captures. |

---

## 3. FORBIDDEN CLAIMS (DO NOT USE IN PAPER)

| Forbidden Claim | Why It Is Forbidden / Invalid |
| :--- | :--- |
| ❌ *"Zero-day detection proven"* | Unsupervised anomaly flags measure statistical deviation, not empirical proof of unseen zero-day attacks. |
| ❌ *"Zero-day bypass prevented"* | Evasive attack samples on ToN-IoT still achieve complete benign prediction in 0.54%--9.36% of cases. |
| ❌ *"100% adversarial robustness / Universally robust"* | Supervised classifiers are vulnerable to gradient perturbations (ASR up to 10.45%). |
| ❌ *"Real-world physical packet attack prevention"* | Perturbations were performed in feature space, not via live physical network packet injection. |
| ❌ *"XAI proves physical causality"* | XAI metrics measure statistical model feature reliance, not physical causal mechanisms. |
