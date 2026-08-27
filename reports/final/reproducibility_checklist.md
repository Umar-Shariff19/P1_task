# Master Reproducibility Checklist & Guide

**Repository**: `IoT-IDS`  
**Guide Version**: Authoritative Final Baseline  
**Verification Date**: August 27, 2026  

---

## 1. Environment Setup & Package Installation

```bash
# 1. Clone repository & create virtual environment
git clone https://github.com/Umar-Shariff19/P1_task.git
cd P1_task_Implementation
python -m venv .venv

# 2. Activate virtual environment (Windows PowerShell / Bash)
# Windows: .venv\Scripts\Activate.ps1
# Linux:   source .venv/bin/activate

# 3. Install iot-ids package in editable production mode
pip install -e .
```

---

## 2. Dataset Materialization & Feature Extraction (Stage 1–3)

```bash
# Materialize canonical datasets (60/20/20 chronological splits across ToN-IoT, Edge-IIoTset, etc.)
python scripts/03_materialize_and_audit_features.py
```
*Output Artifacts*: `data/processed/stage3/<Dataset>/train.parquet`, `val.parquet`, `test.parquet`

---

## 3. Controlled Research Benchmark & Adaptation Reproduction (Stage 4–6)

```bash
# 1. Run controlled within-domain and cross-domain benchmark experiments (160 runs)
python scripts/04_benchmark_models.py

# 2. Run domain adaptation and minimal target label calibration matrix (840 runs)
python scripts/05_domain_adaptation.py

# 3. Run statistical robustness, bootstrap CIs, effect sizes, and shortcut ablations
python scripts/06_statistical_robustness.py
```
*Output Artifacts*: `reports/stage4/`, `reports/stage5/`, `reports/stage6/`

---

## 4. Publication Verification & Submission Packaging (Stage 7–11)

```bash
# 1. Run publication paper integrity audit
python scripts/08_run_publication_audit.py

# 2. Compile LaTeX manuscript & audit citations
python scripts/09_run_submission_compilation.py

# 3. Run adversarial reviewer audit vector suite
python scripts/10_run_adversarial_reviewer_audit.py

# 4. Generate master release submission package & SHA-256 checksums
python scripts/11_run_submission_packaging.py
```
*Output Artifacts*: `reports/stage9/IEEE_paper_final.tex`, `reports/stage11/submission/`

---

## 5. Deployable Artifact Training & Operational Execution (Stage 12)

```bash
# 1. Train and export deployable model artifact independently of training scripts
iot-ids train --source-domain ToN-IoT --target-domain Edge-IIoTset --model-family RandomForest --artifact-dir models/final/deployable_artifact

# 2. Validate deployable artifact on held-out test split
iot-ids validate --artifact-dir models/final/deployable_artifact --test-domain ToN-IoT

# 3. Process batch telemetry CSV/Parquet file
iot-ids predict-batch --artifact-dir models/final/deployable_artifact --input-file data/processed/stage3/ToN-IoT/test.parquet --limit 10 --output-json reports/sample_batch_alerts.json

# 4. Replay offline .pcap network capture file via Scapy
iot-ids replay-pcap --artifact-dir models/final/deployable_artifact --pcap-file data/sample_reproduce_stream.pcap

# 5. Run long-running operational edge runtime daemon
iot-ids run-daemon --artifact-dir models/final/deployable_artifact --pcap-file data/sample_reproduce_stream.pcap --log-file reports/daemon_alerts.jsonl
```

---

## 6. Docker Container Edge Execution

```bash
# Build and run edge sensor container via Docker Compose
docker-compose up --build

# Run container validation directly
docker run --rm -v $(pwd)/models:/app/models iot_ids_edge_sensor validate --artifact-dir models/final/deployable_artifact --test-domain ToN-IoT
```

---

## 7. Master Automated Test Suite

```bash
# Run full 71-test unit and integration suite (0 warnings expected)
python -m pytest tests/unit/data/ tests/unit/features/ tests/unit/experiments/ tests/unit/adaptation/ tests/unit/statistics/ tests/unit/publication/ tests/unit/test_package_and_security.py tests/integration/
```
