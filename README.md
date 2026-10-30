# IoT IDS Implementation Project

This repository contains an implementation and reproducibility record for a multi-level IoT intrusion detection system. Source code, configurations, tests, artifact loaders, and evidence are the project deliverables. Historical metrics and manuscript statements are not treated as newly reproduced findings.

## System

The Python package in `src/iot_ids/` includes dataset adapters and canonical flow handling, feature construction, training and inference, a Random Forest and MLP pipelines, adversarial utilities, privacy-related experimental code, explainability, an artifact registry, CLI commands, and runtime packet/flow processing. The runtime and research pipelines are related but distinct: the golden research pipeline uses 21 standardized features and Option C probability fusion (`0.7 * RF + 0.3 * robust MLP`). Its separate DP-SGD-style experiment is not the fusion model and does not currently substantiate a formal privacy guarantee.

The research pipeline is configured for Edge-IIoTset, ToN-IoT, NF-ToN-IoT-v2, and CICIoT2023. Stage 3 source currently partitions each label class in adapter stream order into 60/20/20 groups and sorts within each group by timestamp. This does not establish globally chronological splits, and existing split artifacts have no linked generation manifest. Temporal generalization is therefore unverified.

## Setup and safe checks

Use Python 3.10 or newer. Install the package and development extras in an isolated environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Optional model and explainability dependencies are in the `models` and `xai` extras in `pyproject.toml`. The current test suite also includes tests that may load local datasets or artifacts. Inspect a test's fixtures and data paths before running it. A focused, synthetic-only check is:

```powershell
python -m pytest tests/unit/data/test_flow_aggregator.py -q
```

To run the deterministic end-to-end synthetic packet demonstration (which exercises packet parsing, flow aggregation, 21-feature extraction, decision thresholding, risk scoring, and JSON alert output without requiring real data authorization or loading model checkpoints):

```powershell
python src/iot_ids/runtime/synthetic_packet_demo.py --seed 2026 --flows 3
```

Do not run dataset-wide scans or pipelines as a substitute for reviewing data access. BoT-IoT file 4 is prohibited. The previously exposed ToN-IoT test split and prohibited BCL evaluator must not be accessed or run.

## Workflows and artifacts

- Data preparation: `scripts/01_*` through `scripts/03_*`; Stage 3 writes under `data/processed/stage3/`.
- Golden training/evaluation: `scripts/run_golden_pipeline.py`; it reads train/validation/test splits and writes model files under `models/golden_run/` and a manifest under `reports/`. Do not run it without an approved, safe data-access plan; it can overwrite official outputs.
- Deployable artifacts: `models/final/deployable_artifact/`, described by `pipeline_metadata.json`.
- CLI: registered as `iot-ids` in `pyproject.toml`; inspect the selected command's artifact and data paths before invocation.

## Evidence and status

[`results/README.md`](results/README.md) is the canonical index for implementation status, validation, provenance, claims, and future experiment records. It replaces in-repository manuscript files as the central research-evidence record. Historical implementation reports remain available at the repository root and under `reports/`, but the canonical ledger controls current evidence status.

The Phase I/Phase J inventory and capture incidents remain unresolved: the earlier recursive inventory may have enumerated protected path metadata, and the earlier Scapy-present test invoked capture code without evidence establishing whether capture started or packets arrived. No zero-access or zero-capture conclusion is supported. Git history confirms `reports/tables/latex_ci_table.tex` was tracked and later deleted; its 2,459-byte historical blob is now preserved at the exact archive path `C:\Users\umari\Documents\IDS_Manuscript_Archive\2026-10-27\original\reports\tables\latex_ci_table.tex`, verified by existence and byte length without reading the contents. It was not restored to the repository. Phase J used only explicit-path checks and static inspection; it did not access protected data, run the prohibited evaluator or test split, or invoke live capture. See `results/validation/safety_and_data_access.md` and `results/implementation/manuscript_cleanup_inventory.md` for the evidence and limits.

The root IEEE submission packages were moved to `C:\Users\umari\Documents\IDS_Manuscript_Archive\2026-10-27\original\`; the colleague's paper package was moved to the corresponding `candidate\` archive. Shared project context documents and research evidence were retained. The candidate repository is a comparison source, not the authoritative implementation.

## Important limitations

Split provenance, exact provenance for historical model artifacts/metrics, the reported privacy guarantee, and confirmatory BCL evidence remain unresolved. A generic lexical dataset-root authorization primitive is available in `src/iot_ids/data/path_policy.py`, but it is not integrated into adapters and cannot authorize real roots without owner-approved roots and a trusted Windows identity verifier. The candidate BCL flow is not integrated. Runtime, adversarial robustness, explainability, and reported benchmark results require appropriately documented experiments before they can be treated as experimentally validated. See `results/claims/claim_evidence_ledger.md`, `results/implementation/known_limitations.md`, and `results/implementation/research_readiness_matrix.md`.
