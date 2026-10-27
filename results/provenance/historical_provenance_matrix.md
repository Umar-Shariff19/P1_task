# Historical metric and artifact provenance matrix

This matrix records only metadata already present in `reports/golden_run_manifest.json`, `results/provenance/metric_provenance.md`, and the inspected runner/configuration names. It does not load checkpoints, dataset artifacts, or protected data. No metric was reproduced in this phase.

The synthetic manifest fixture and validator tests use artificial identifiers and a non-IDS arithmetic value. They demonstrate record creation, schema validation, and persistence behavior only; they are not an IDS experiment and provide no performance evidence.

## Metric-level evidence

| Metric | Value reported | Dataset/model identity | Recording artifact | Source revision | Split link | Checkpoint link | Reproduction |
|---|---:|---|---|---|---|---|---|
| Mean ROC-AUC, Random Forest | 0.997568 | Four dataset labels are listed in the manifest; model name is `RF`. | `reports/golden_run_manifest.json` records 0.9975684375; rounded value repeated by `metric_provenance.md`. | Missing. | Missing split ID, generator record, or split digest. | Missing run-bound checkpoint identifier/digest. Filename/code conventions do not bind a checkpoint to this value. | `HISTORICAL_REPORTED` |
| Mean ROC-AUC, Option C | 0.996982 | Four dataset labels are listed; Option C model label is recorded. | Manifest records 0.9969815625; rounded value repeated by `metric_provenance.md`. | Missing. | Missing. | Missing. Current runner's 0.7 RF + 0.3 robust-MLP formula is code evidence, not proof the manifest came from that exact run. | `HISTORICAL_REPORTED` |
| Mean ROC-AUC, standard MLP | 0.859050 | Four dataset labels are listed; `Standard_MLP` aggregate recorded. | Manifest records 0.8590496875; rounded value repeated by `metric_provenance.md`. | Missing. | Missing. | Missing run-bound identifier/digest. | `HISTORICAL_REPORTED` |
| Mean ROC-AUC, robust MLP | 0.856209 | Four dataset labels are listed; `Robust_MLP` aggregate recorded. | Manifest records 0.85620875; rounded value repeated by `metric_provenance.md`. | Missing. | Missing. | Missing run-bound identifier/digest. | `HISTORICAL_REPORTED` |

The manifest directly records the displayed values, dataset labels, timestamp, seed 42, feature count 21, and per-dataset model metrics. These are direct statements in a historical file; they do not independently prove how the measurements were generated. The timestamp does not identify a Git revision or environment.

## Relationships and confidence

| Relationship | Evidence class | Finding |
|---|---|---|
| Four aggregate values to manifest | Directly evidenced as recorded claims | Exact aggregate numbers are in the manifest and round to the four displayed values. |
| Per-dataset values to dataset labels | Directly evidenced as recorded claims | Manifest contains values keyed under the four named datasets. No dataset bytes were opened to verify them. |
| Metrics to feature count 21 and seed 42 | Directly evidenced as co-recorded metadata | Manifest fields exist; no run log proves they governed these metrics. |
| Option C formula to historical aggregate | Inferred from current runner convention | Current source defines a 0.7/0.3 RF/robust-MLP score. No source revision or run record binds that formula to the manifest. |
| Metrics to checkpoint filenames | Inferred from naming/source conventions only | Golden model files exist, but no manifest mapping or digest binds them to each metric. No checkpoint was loaded or hashed. |
| Metrics to current split generator | Missing/conflicting | Source has a class-wise stream partition implementation, while the manifest has no generator version/config or split ID. Co-release/history is not proof of generation. |
| Metrics to source revision | Missing | No source revision is recorded in the manifest. |
| Metrics to environment/dependencies | Missing | A separate environment snapshot exists, but its linkage to this manifest is not established. |
| Manifest's “100% Real Benchmark Data” assertion | Unverified | The string is present, but no independent lineage record substantiates it. |
| Golden artifacts to deployable artifact family | Not established; do not conflate | The deployable pipeline is a separate artifact family and is not evidence for golden metric checkpoint identity. |

## Provenance fields absent from the historical manifest

No source commit/dirty diff identifier, split identity or digest, generator version/configuration, checkpoint identifier/digest mapping, exact train/evaluation configuration, dependency lock/environment binding, metric definition, safety-policy version, or output-artifact mapping is established by the existing manifest. Do not fill these fields retroactively from current filenames or code. Future records use the prospective schema in `experiment_manifest.schema.json`; schema validity alone does not establish authorization, execution, or truth.
