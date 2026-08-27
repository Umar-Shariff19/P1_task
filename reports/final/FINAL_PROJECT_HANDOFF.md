# Master Project Handoff Documentation

**Project**: Adversarially Robust Multi-Level IoT Intrusion Detection System (`iot-ids`)  
**Target Audience**: Researchers, Machine Learning Engineers, Security Engineers, and Reviewers  
**Document Version**: 1.0 (Authoritative Final Baseline)  
**Date**: August 27, 2026  

---

## 1. What This Project Is

This repository contains the complete scientific research pipeline and production-grade operational edge software for an **Adversarially Robust Multi-Level IoT Intrusion Detection System**. It addresses the critical issue of cross-domain generalization failure in IoT ML models when transferred across heterogeneous network environments.

---

## 2. Central Research Objective

> **Central Research Question**: *Can a multi-level network representation combining Instantaneous flow dynamics, Causal Temporal arrival dynamics, and Causal Behavioral host topology provide significantly superior cross-domain generalization and lower false-positive rates than a flat set of universally available flow features?*

---

## 3. The 18-Feature Multi-Level Architecture

The system abstracts raw network telemetry into 18 conceptual semantic features across three distinct abstraction levels:

1. **Level A --- Instantaneous Representation** (8 Conceptual Features / 11 Numerical Matrix Columns):
   - Flow duration, flow bytes/sec, flow pkts/sec, mean packet size, payload byte ratio, packet count ratio, TCP SYN ratio.
   - Nominal protocol field expanded via 4-way one-hot indicators (`proto_tcp`, `proto_udp`, `proto_icmp`, `proto_other`).
2. **Level B --- Causal Temporal Representation** (5 Conceptual / Numerical Features):
   - EWMA inter-arrival timing mean (`temporal_iat_mean`), inter-arrival timing coefficient of variation (`temporal_iat_cv`), flow rate EWMA (`temporal_flow_rate_ewma`), byte rate EWMA (`temporal_byte_rate_ewma`), and SYN rate EWMA (`temporal_syn_rate_ewma`).
   - Calculated obeying **read-before-write causality** ($X_i = f(e_i, H_{<t_i})$).
3. **Level C --- Causal Behavioral Representation** (5 Conceptual / Numerical Features):
   - Destination IP diversity (`behavioral_dst_diversity`), destination port entropy (`behavioral_port_entropy`), fanout ratio (`behavioral_fanout_ratio`), unanswered connection ratio (`behavioral_unanswered_ratio`), and source activity EWMA (`behavioral_src_activity_ewma`).
   - Tracked over sliding 30-second host interaction windows.

---

## 4. Key Experimental Results & Evidence

1. **Within-Domain Monotonic Superiority**:
   - `baseline_common` (5 features): Macro F1 = 0.923, FPR = 15.8%
   - `full_multilevel` (21 columns): Macro F1 = 0.970, **FPR = 1.6%**
   - `instant_behavioral` (16 columns): **Macro F1 = 0.986**, FPR = 2.7%
2. **Cross-Domain Adaptation Recovery**:
   - Zero-shot stateful transfer suffers timing shift ($0.4630$ ROC-AUC).
   - Minimal 5% target adaptation (42--210 samples) recovers performance to **0.992 ROC-AUC** (95% CI [0.989, 0.996]).
3. **Statistical Significance & Effect Sizes**:
   - Paired Cohen's $d_z = 1.134$ ($p = 0.0024$), Hedges' $g = 1.055$.
   - **97.2% performance retention** after stripping protocol and rate shortcut features.

---

## 5. Operational Software Architecture

```text
                               DEPLOYABLE ARTIFACT
                    (model.joblib, preprocessor.joblib, aligner.joblib, calibrator.joblib)
                                       │
                                       ▼
Raw Telemetry ──► Packet Capture ──► Flow Aggregator ──► Multi-Level Builder ──► IDSPredictor ──► Alerts & Metrics
(PCAP / Ingress)    (Scapy Engine)     (5-Tuple LRU)       (18 Features)        (RF Model)     (JSONL & Console)
```

---

## 6. CLI Command Reference (`iot-ids`)

```bash
# 1. Package Installation
pip install -e .

# 2. Train & Export Deployable Artifact
iot-ids train --source-domain ToN-IoT --target-domain Edge-IIoTset --model-family RandomForest --artifact-dir models/final/deployable_artifact

# 3. Validate Artifact on Held-Out Test Set
iot-ids validate --artifact-dir models/final/deployable_artifact --test-domain ToN-IoT

# 4. Batch Telemetry Processing
iot-ids predict-batch --artifact-dir models/final/deployable_artifact --input-file data/processed/stage3/ToN-IoT/test.parquet --limit 10

# 5. Offline PCAP Replay
iot-ids replay-pcap --artifact-dir models/final/deployable_artifact --pcap-file data/sample_reproduce_stream.pcap

# 6. Operational Runtime Daemon
iot-ids run-daemon --artifact-dir models/final/deployable_artifact --pcap-file data/sample_reproduce_stream.pcap --log-file reports/daemon_alerts.jsonl
```

---

## 7. Master Automated Test Suite

```bash
python -m pytest tests/unit/data/ tests/unit/features/ tests/unit/experiments/ tests/unit/adaptation/ tests/unit/statistics/ tests/unit/publication/ tests/unit/test_package_and_security.py tests/integration/
```
**Status**: **71 / 71 PASSED (100% Pass Rate in 4.79s, 0 Warnings)**.

---

## 8. Known Field-Validation Limitations

1. **Physical Live-Wire Interface Testing**: Scapy live capture (`predict-live`) is fully implemented, but has not been field-tested on physical gigabit hardware switches.
2. **Enterprise SIEM Integration**: Alerts are persisted locally via `JSONLFileSink` and `ConsoleAlertSink`; direct syslog / Kafka alert streaming is not implemented.

---

## 9. Master File Navigation Map

- **Core Code**: `src/iot_ids/`
- **Research Benchmarks**: `scripts/03_` to `06_`
- **Publication Audit & LaTeX**: `scripts/08_` to `11_`, `reports/stage9/IEEE_paper_final.tex`
- **Deployable Exporters**: `scripts/export_deployable_model.py`, `scripts/validate_real_inference.py`, `scripts/validate_edge_deployment.py`
- **Traceability Matrices**: `reports/final/`
