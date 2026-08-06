# IoT IDS P1 ML Foundation

This repository implements the P1 foundation for the research project **An Adversarially Robust and Privacy-Preserving AI Framework for Explainable Intrusion Detection in IoT Environments**.

P1 scope is intentionally bounded: multi-level network features plus a hybrid IDS made from Random Forest, tabular Neural Network, and Autoencoder components. Downstream adversarial attack generation, BCL logic, federated learning, dashboards, and XAI research modules are integration consumers, not part of this subsystem.

## Data Layout

Place datasets under:

- `data/raw/CICIDS2017/`
- `data/raw/Edge-IIoTset/`
- `data/raw/BoT-IoT/`
- `data/raw/N-BaIoT/`

`data/raw/**` is immutable and ignored by Git.

## Current Status

First milestone implemented:

- repository foundation
- dataset audit CLI
- initial dataset adapters
- schema/leakage profiling
- initial EDA report generation
- validation tests
- implementation plan and P4 contract skeleton

Run:

```powershell
.\.venv\Scripts\python.exe scripts\audit_datasets.py --data-root data/raw --output reports/eda
.\.venv\Scripts\python.exe scripts\generate_milestone2_reports.py
.\.venv\Scripts\python.exe -m pytest
```

The corrected local repository contains the four raw dataset directories. Regenerate EDA with `scripts/audit_datasets.py` after any source-data placement or schema change.

## Environment

Create the project environment with:

```powershell
C:\Users\umari\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

PyTorch and ONNX dependencies are optional extras for later model/export milestones.

## Milestone 2

Milestone 2 freezes the scientific representation. It documents labels, leakage roles, feature profiles, splitting policy, and cache/materialization behavior. It does not train RF, NN, AE, or ensemble models.

Milestone 2.5 validation is summarized in `docs/MILESTONE_2_5_VALIDATION.md`.
