# Implementation status

Status reflects inspected source and safe validation recorded on 2026-10-27. File presence alone is not evidence of a complete or scientifically validated component.

| Area | Implemented behavior | Maturity / evidence |
|---|---|---|
| Data adapters | Dataset-specific parsers map inputs into canonical flows; Stage 3 materializer selects bounded class samples and writes feature splits. | Implemented. Split chronology and historical split provenance are unverified. |
| Features | Canonical instant, temporal, and behavioral feature builders; schema profiles include a 21-column standardized profile. | Implemented. Cross-dataset semantic validity and historical feature ordering require run-level evidence. |
| Models | Golden runner defines RF, standard MLP, and adversarially trained MLP. MLP layers are 21→128→64→32→1. | Implemented in source; historical checkpoint-to-run provenance incomplete. |
| Fusion | Golden runner computes Option C as `0.7 * p_rf + 0.3 * p_robust_mlp`. | Source-supported. Its metrics are historical reports, not reproduced here. |
| BCL / risk | Original tree has autoencoder risk calibration/evaluation; candidate tree has separate BCL code. | Original risk layer is implemented. Candidate BCL remains separate and is not validated as confirmatory evidence. |
| Differential privacy | Experimental per-sample clipping/noisy-gradient loop and numeric accountant wrapper exist. | Experimental only; sampling, randomness, normalization, dependency, accounting, and release behavior do not establish a guarantee. |
| Adversarial robustness | PGD utilities and adversarial MLP training are present. | Implemented; robustness claims require a documented, appropriate threat model and experiment provenance. |
| Explainability | RF/MLP/AE explainers and attribution/report utilities are present. | Implemented; existing outputs are historical and provenance-limited. |
| CLI/runtime | CLI, artifact predictor, flow aggregation, sinks, packet capture, and runtime engine are present. Scapy imports are optional for non-capture paths. | Source and focused synthetic flow-aggregator tests support selected behavior; no end-to-end real-data validation in this phase. |
| Tests | Unit, integration, feature, runtime, and experiment tests are present. | Test names alone do not establish safety; inspect data paths before running. Phase H flow tests are synthetic. |
| Configuration/dependencies | `pyproject.toml`, feature schemas, split and dataset configs. Torch/XAI are optional extras; Opacus is not declared. | Present; experiment-specific environment is not bound to historical outputs. |
| Artifacts | Golden-run, standardized, final deployable model files and metadata/manifests are stored under `models/` and `reports/`. | Preserved; source/split/model/environment linkage is incomplete. |

The primary implementation reference is the source tree. Historical status reports at the root are snapshots and must be interpreted through `../claims/claim_evidence_ledger.md`.
