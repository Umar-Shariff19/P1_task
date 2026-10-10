# Authoritative Results Tables — IIoT IDS Paper

## 1. Clean Detection Performance (ROC-AUC)

| Dataset | Random Forest | Standard MLP | Robust MLP | Option C (0.7/0.3) |
| :--- | :---: | :---: | :---: | :---: |
| **Edge-IIoTset** | 0.9995 | 0.8443 | 0.8002 | 0.9988 |
| **NF-ToN-IoT-v2** | 0.9940 | 0.8398 | 0.8299 | 0.9927 |
| **ToN-IoT** | 1.0000 | 0.7745 | 0.8063 | 1.0000 |
| **CICIoT2023** | 0.9968 | 0.9776 | 0.9884 | 0.9965 |
| **Mean** | **0.9976** | **0.8590** | **0.8562** | **0.9970** |

*Key Finding:* Option C does not improve clean mean ROC-AUC over pure RF (0.9970 vs. 0.9976). Option C preserves near-RF clean performance while enabling neural privacy and gradient-level security studies.

---

## 2. Baseline PGD-10 Adversarial Attack Success Rate (ASR %)

| Dataset | Standard MLP | Robust MLP | Option C |
| :--- | :---: | :---: | :---: |
| **Edge-IIoTset** | 0.0% | 0.0% | 3.8% |
| **NF-ToN-IoT-v2** | 53.8% | 48.0% | 4.0% |
| **ToN-IoT** | 2.3% | 2.5% | 0.0% |
| **CICIoT2023** | 2.3% | 1.3% | 1.2% |

*Attack Config:* PGD-10 ($\epsilon=0.10, lpha=0.025, 10$ steps, protocol mask `7:11` frozen). Evaluated as a neural-stream gradient attack evaluated through the deployed ensemble.

---

## 3. Adaptive Surrogate-Gradient Attack Results

| Dataset | Baseline Option C PGD-10 ASR | Adaptive Surrogate Attack ASR | $\Delta$ ASR (pp) | Surrogate Validation $R^2$ |
| :--- | :---: | :---: | :---: | :---: |
| **Edge-IIoTset** | 3.8% | 11.8% | +8.0 pp | -0.5944 |
| **NF-ToN-IoT-v2** | 4.0% | 5.9% | +1.9 pp | +0.9477 |
| **ToN-IoT** | 0.0% | 0.0% | 0.0 pp | +0.0362 |
| **CICIoT2023** | 1.2% | 1.1% | -0.1 pp | +0.5357 |

*Methodology:* Surrogate-based adaptive attack targeting joint objective $0.7 \cdot \mathcal{S}_{	ext{RF}}(x) + 0.3 \cdot 	ext{RobustMLP}(x)$. Final samples evaluated against actual frozen Option C.

---

## 4. Empirical Fusion Weight Ablation Sweep ($w \in [0.0, 1.0]$)

| RF Weight ($w$) | MLP Weight ($1-w$) | Mean Clean ROC-AUC | Mean PGD-10 ASR (%) |
| :---: | :---: | :---: | :---: |
| **0.0 (Pure MLP)** | 1.0 | 0.8562 | 13.0% |
| **0.3** | 0.7 | 0.9914 | 2.3% |
| **0.5** | 0.5 | 0.9956 | 1.7% |
| **0.6** | 0.4 | 0.9958 | 1.5% |
| **0.7 (Option C)** | 0.3 | 0.9970 | 2.2% |
| **1.0 (Pure RF)** | 0.0 | 0.9976 | 8.6% |

*Interpretation:* RF-only ($w=1.0$) maximizes clean AUC. Weight $w=0.6$ achieves lowest mean ASR. Weight $w=0.7$ represents a high-clean-performance operating point with a favorable robustness tradeoff under the evaluated attack protocol.

---

## 5. Non-Parametric Bootstrap 95% Confidence Intervals ($B=1,000$, $	ext{seed}=42$)

| Dataset | Option C Clean ROC-AUC [95% CI] | Option C Clean Macro F1 [95% CI] | Option C PGD-10 ASR [95% CI] |
| :--- | :---: | :---: | :---: |
| **Edge-IIoTset** | 0.9988 [0.9978, 0.9994] | 0.9950 [0.9912, 0.9979] | 0.0380 [0.0270, 0.0500] |
| **NF-ToN-IoT-v2** | 0.9927 [0.9877, 0.9965] | 0.9678 [0.9537, 0.9799] | 0.0400 [0.0280, 0.0530] |
| **ToN-IoT** | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| **CICIoT2023** | 0.9965 [0.9929, 0.9989] | 0.9768 [0.9650, 0.9868] | 0.0120 [0.0060, 0.0190] |

---

## 6. Global Feature Attribution Top 4

| Feature Name | Normalized Attribution ($0.7 	ext{RF} + 0.3 	ext{MLP}$) |
| :--- | :---: |
| `temporal_flow_rate_ewma` | 0.310 |
| `behavioral_port_entropy` | 0.242 |
| `behavioral_unanswered_ratio` | 0.154 |
| `behavioral_dst_diversity` | 0.146 |

---

## 7. Differential Privacy Utility Sweep (NF-ToN-IoT-v2, $\delta=10^{-5}$)

| Noise Multiplier ($\sigma$) | Audited Epsilon ($arepsilon$) | Edge-IIoTset | NF-ToN-IoT-v2 | ToN-IoT | CICIoT2023 |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0.0** | $\infty$ | 0.954 | 0.976 | 1.000 | 0.965 |
| **0.5** | 15.8 | 0.973 | 0.886 | 0.998 | 0.960 |
| **1.0** | **2.4** | 0.978 | **0.854** | 0.997 | 0.964 |
| **2.0** | 0.8 | 0.978 | 0.828 | 0.997 | 0.967 |

---

## 8. Single-CPU Host Inference Throughput

| Batch Size ($N$) | Batch Latency (ms) | Per-Sample Latency (ms) | Throughput (samples/sec) |
| :---: | :---: | :---: | :---: |
| 1 | 69.40 | 69.4000 | 14.4 |
| 32 | 54.86 | 1.7143 | 583.3 |
| 128 | 46.68 | 0.3647 | 2,742.3 |
| **1024** | **62.04** | **0.0606** | **16,504.7** |
