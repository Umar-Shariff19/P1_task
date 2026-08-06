# P1 Implementation Plan

## Authority Audit

Authoritative project files are present under `project_context/` in the corrected repository root. Supplementary project references are present under `references/`.

Resolved scope:

- P1 is the ML foundation, not the adversarial/BCL/federated/XAI/dashboard subsystem.
- Primary architecture is Random Forest + tabular Neural Network + Autoencoder.
- Required representation levels are instant, temporal, and behavioral network features.
- P1 must expose component-level outputs for P4 without implementing P4 calculations.

The Objective 4 reference document contains CNN, FGSM, pruning, quantization, synthetic-data, and adversarial-training proof-of-concept material. This is treated as supporting/non-authoritative and does not override the P1 RF + NN + AE boundary.

## Current Repository Audit

- Git repository exists at this root with no commits yet.
- Corrected repository contains `project_context`, `references`, and populated `data/raw` inputs.
- Migrated the implementation scaffold from the accidental workspace into this corrected repository without copying empty raw-data placeholders.
- `data/raw/**` is ignored and treated as immutable source data.

## Environment Audit

- OS/platform observed: Windows 11.
- Python available through bundled Codex runtime: 3.12.13.
- Logical CPUs observed through Python: 12.
- Bundled packages available now: `numpy`, `pandas`, `pypdf`, `python-docx`.
- Missing from bundled runtime and declared as project dependencies: `pyarrow`, `scikit-learn`, `torch`, `onnx`, `onnxruntime`, `joblib`, `psutil`, plotting libraries.
- CUDA/GPU could not be verified because PyTorch is not installed in the active runtime.
- Windows CIM hardware query was denied by the sandbox, so RAM/GPU details remain unverified in this milestone.

## Dataset Audit Status

Expected roots:

- `data/raw/CICIDS2017`
- `data/raw/Edge-IIoTset`
- `data/raw/BoT-IoT`
- `data/raw/N-BaIoT`

The corrected local repository contains populated dataset roots. Regenerated audit outputs under `reports/eda/` are authoritative for Milestone 1; any empty-data reports from the accidental workspace are invalid and ignored.

Real-data audit summary:

- CICIDS2017: 8 candidate/source CSV files, 884,645,759 bytes, 2,830,743 CSV rows, 79 observed columns, `Label` classes detected.
- Edge-IIoTset: 52 source files under root; 1 prepared ML CSV selected for P1 tabular audit, 82,184,390 candidate bytes, 157,800 rows, 63 observed columns, `Attack_label` and `Attack_type` detected.
- BoT-IoT: 75 source files including `data_names.csv`; 74 CSV partitions selected, 14,998,577,525 candidate bytes, 73,370,443 rows, 35 observed columns, `attack`, `category`, and `subcategory` detected.
- N-BaIoT: 93 source files including metadata CSVs; 89 traffic CSVs selected, 8,140,823,834 candidate bytes, 7,062,606 rows, 115 observed columns, labels inferred from filenames.

## Leakage and Splitting Policy

Initial leakage candidates:

- flow IDs
- source/destination IPs
- timestamps when used directly as predictive values
- device IDs and host identifiers
- dataset/source/file metadata
- label-derived attack category/type fields

Permitted uses:

- grouped splitting
- domain analysis
- source-file/day partition tracking
- device-generalization analysis

Default policy is to preserve these as metadata and exclude them from predictive feature matrices unless explicitly justified.

## Computation Strategy

- Use chunked CSV ingestion for BoT-IoT and any large CSV collections.
- Use deterministic fingerprints for raw files and processed caches.
- Prefer Parquet/Arrow caches when `pyarrow` is installed.
- Fit preprocessing on training splits only.
- Use debug mode only for software validation; all reports must record run mode.
- Avoid model training until dataset schemas and label semantics are verified.

## Implementation Roadmap

1. Dataset layer: finalize adapters after raw files are present; validate schemas, labels, missing/Inf values, duplicates, leakage candidates, ordering/entity metadata, and row counts.
2. Canonical representation: document semantic feature mapping across datasets instead of plain name intersection.
3. Feature engineering: instant features first; temporal rolling/causal features where ordering exists; behavioral network features where entity/connection context exists.
4. Preprocessing: split-aware imputation/scaling/encoding, imbalance handling inside training folds only, serialized preprocessors.
5. Models: implement RF, tabular NN, AE with reproducible configs and bounded tuning.
6. Ensemble: weighted RF + NN + AE probability/anomaly fusion with validation-only weight selection.
7. Evaluation: same-dataset, ablations, and compatible 4x4 cross-dataset matrix with mandatory metrics.
8. Export: versioned artifacts, manifest, schemas, native wrappers, ONNX attempts and parity where reliable.
9. P4 handoff: stable `HybridIDS.load`, `predict`, and `predict_batch` component-output API.

## Milestone 2 Representation Freeze

Environment:

- Project venv: `.venv`
- Python: 3.12.13
- CPU: 12 logical / 8 physical cores
- RAM: 16,857,817,088 bytes
- Core installed packages recorded in `reports/eda/environment.json`

Machine-readable outputs:

- `configs/datasets/label_taxonomy.json`
- `configs/features/leakage_metadata.json`
- `configs/features/canonical_schema.json`
- `configs/experiments/splits.json`
- `reports/eda/deep_schema_inventory.json`
- `reports/eda/feature_availability.json`
- `reports/eda/feature_availability.csv`
- `reports/eda/label_mapping.json`
- `reports/eda/leakage_analysis.json`
- `reports/eda/materialization_debug.json`

Canonical profile decision:

- `FLOW_COMPATIBLE_C_E_B`: defensible shared flow-compatible profile for CICIDS2017, Edge-IIoTset and BoT-IoT. Milestone 2.5 semantic audit reduced this from 7 to 4 features because BoT-IoT does not expose decomposed SYN/ACK/RST count fields equivalent to CICIDS2017/Edge-IIoTset.
- `FLOW_RICH_C_B`: richer flow profile for CICIDS2017 and BoT-IoT.
- `NBAIOT_SOURCE_AGGREGATE`: source-provided N-BaIoT aggregate temporal/behavioral profile.

A strict four-dataset raw-flow profile is not frozen because N-BaIoT contains pre-aggregated host/host-pair statistics rather than the raw flow fields available in CICIDS2017, Edge-IIoTset and BoT-IoT. This is a documented scientific limitation, not a missing implementation.

Debug materialization validation:

- CICIDS2017: 8,000 debug rows, 8 Parquet partitions, ~4,292 rows/sec.
- Edge-IIoTset: 1,000 debug rows, 1 Parquet partition, ~5,166 rows/sec.
- BoT-IoT: 74,000 debug rows, 74 Parquet partitions, ~5,584 rows/sec.
- N-BaIoT: 89,000 debug rows, 89 Parquet partitions, ~2,040 rows/sec.
- Debug cache size: 49,603,283 bytes.

These debug caches validate software paths only and are not research results.
