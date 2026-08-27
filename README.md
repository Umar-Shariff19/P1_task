# Multi-Level IoT Intrusion Detection System (IoT-IDS)

This repository implements the complete scientific research pipeline and production-grade operational edge software for an **Adversarially Robust Multi-Level IoT Intrusion Detection System**.

---

## 1. Project Overview
Machine learning models for IoT intrusion detection frequently suffer from severe cross-domain generalization degradation when deployed across heterogeneous networks. This project introduces a universal multi-level semantic representation (Instantaneous, Causal Temporal, and Causal Behavioral) paired with unsupervised feature alignment and minimal target domain adaptation to solve cross-domain transfer failure and slash false positive rates.

---

## 2. Research Methodology
The central hypothesis posits that structured multi-level representations obeying read-before-write causality provide superior cross-domain generalization compared to flat, universally available flow features. Grounded in statistical domain adaptation theory, the pipeline evaluates zero-shot transfer, unsupervised CORAL feature covariance alignment, and minimal target-domain threshold calibration.

---

## 3. System Architecture

```text
                               DEPLOYABLE ARTIFACT
                    (model.joblib, preprocessor.joblib, aligner.joblib, calibrator.joblib)
                                       │
                                       ▼
Raw Telemetry ──► Packet Capture ──► Flow Aggregator ──► Multi-Level Builder ──► IDSPredictor ──► Alerts & Metrics
(PCAP / Ingress)    (Scapy Engine)     (5-Tuple LRU)       (18 Features)        (RF Model)     (JSONL & Console)
```

---

## 4. Dataset Preparation
The system evaluates **28,000 canonical flows** across four benchmark IoT datasets (7,000 flows per dataset, split 60% train / 20% validation / 20% test chronologically):
- **ToN-IoT** (Ethernet & Wi-Fi IoT telemetry)
- **Edge-IIoTset** (Industrial IoT protocol telemetry)
- **NF-ToN-IoT-v2** (NetFlow v9 feature representation of ToN-IoT)
- **CICIoT2023** (33-device IoT attack capture)

---

## 5. Feature Architecture
The system defines **18 conceptual semantic features** expanding to **21 numerical model matrix columns**:
- **Level A (Instantaneous)**: 8 conceptual features / 11 numerical columns (flow duration, rates, payload ratio, packet ratio, SYN ratio, 4-way protocol one-hot indicators).
- **Level B (Causal Temporal)**: 5 conceptual/numerical features (EWMA inter-arrival timing mean, CV, flow rate EWMA, byte rate EWMA, SYN rate EWMA).
- **Level C (Causal Behavioral)**: 5 conceptual/numerical features (destination IP diversity, destination port entropy, fanout ratio, unanswered ratio, activity EWMA).

---

## 6. Experimental Methodology
Controlled benchmark experiments (160 runs) evaluate representation profile progressions (`baseline_common`, `instant_only`, `instant_temporal`, `instant_behavioral`, `full_multilevel`) across 4 model families (Random Forest, Logistic Regression, MLP, Autoencoder). Domain adaptation experiments (840 runs) evaluate cross-domain transfer across 12 transfer directions under target label budgets (0%, 1%, 5%, 10%).

---

## 7. Research Results
- **Within-Domain Benchmark**: `full_multilevel` Random Forest reaches **0.986 Macro F1** and slashes FPR to **1.6%**.
- **Minimal Target Adaptation**: 5% target label adaptation (42--210 samples) recovers cross-domain transfer to **0.992 ROC-AUC** (95% CI [0.989, 0.996], Cohen's $d_z = 1.134, p = 0.0024$).
- **Shortcut Independence**: Stripping protocol indicators and raw rates retains **97.2% of performance**.

---

## 8. Installation

```bash
# Clone repository & install package in editable production mode
git clone https://github.com/Umar-Shariff19/P1_task.git
cd P1_task_Implementation
python -m venv .venv
# Activate virtual environment
pip install -e .
```

---

## 9. Training

```bash
iot-ids train --source-domain ToN-IoT --target-domain Edge-IIoTset --model-family RandomForest --artifact-dir models/final/deployable_artifact
```

---

## 10. Validation

```bash
iot-ids validate --artifact-dir models/final/deployable_artifact --test-domain ToN-IoT
```

---

## 11. Batch Inference

```bash
iot-ids predict-batch --artifact-dir models/final/deployable_artifact --input-file data/processed/stage3/ToN-IoT/test.parquet --limit 10 --output-json reports/batch_alerts.json
```

---

## 12. Streaming Inference

```bash
iot-ids predict-stream --artifact-dir models/final/deployable_artifact --input-json data/sample_stream_packets.json
```

---

## 13. PCAP Replay

```bash
iot-ids replay-pcap --artifact-dir models/final/deployable_artifact --pcap-file data/sample_reproduce_stream.pcap
```

---

## 14. Live Capture

```bash
iot-ids predict-live --artifact-dir models/final/deployable_artifact --interface eth0 --bpf-filter "ip"
```

---

## 15. Runtime Daemon

```bash
iot-ids run-daemon --artifact-dir models/final/deployable_artifact --pcap-file data/sample_reproduce_stream.pcap --log-file reports/daemon_alerts.jsonl
```

---

## 16. Docker Deployment

```bash
docker-compose up --build
```

---

## 17. Testing

```bash
python -m pytest tests/unit/data/ tests/unit/features/ tests/unit/experiments/ tests/unit/adaptation/ tests/unit/statistics/ tests/unit/publication/ tests/unit/test_package_and_security.py tests/integration/
```
**Status**: **71 / 71 PASSED (100% Pass Rate, 0 Warnings)**.

---

## 18. Reproducibility
See [reproducibility_checklist.md](file:///C:/Users/umari/Documents/P1_task_Implementation/reports/final/reproducibility_checklist.md) for full step-by-step reproduction instructions.

---

## 19. Limitations
1. Live network sniffing (`predict-live`) requires elevated network interface privileges (`root` / `CAP_NET_RAW` on Linux, Administrator/Npcap on Windows).
2. Enterprise SIEM alert exporters (Kafka, Syslog) are not implemented; alerts persist locally via `JSONLFileSink` and `ConsoleAlertSink`.

---

## 20. Repository Structure
- `src/iot_ids/`: Core operational package (`config`, `data`, `features`, `experiments`, `adaptation`, `pipeline`, `inference`, `registry`, `runtime`, `utils`)
- `scripts/`: Materialization, benchmarking, publication audit, and operational scripts
- `reports/`: Research evidence CSVs, LaTeX publication source (`reports/stage9/IEEE_paper_final.tex`), and final audit matrices (`reports/final/`)
- `tests/`: 71 automated unit and integration tests

---

## 21. Citation

```bibtex
@article{iot_ids_2026,
  title={Cross-Domain IoT Intrusion Detection via Multi-Level Causal Representation and Minimal Target Adaptation},
  author={Anonymized Author(s)},
  journal={IEEE Transactions on Dependable and Secure Computing},
  year={2026}
}
```
