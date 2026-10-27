# Artifact and experiment provenance

| Evidence item | What is present | Missing linkage / limitation |
|---|---|---|
| Golden manifest | `reports/golden_run_manifest.json`; timestamp field, seed, four dataset labels, feature count, metric summaries, and a `provenance` field claiming “100% Real Benchmark Data”. | No source commit, split identity/hash, model hash, or environment lock reference. Timestamp and the manifest's data-lineage assertion are not independently verified. |
| Golden models | `models/golden_run/` with per-dataset scalers, RF, and MLP state dictionaries. | No authoritative per-file training manifest or mapping to exact split files/environment. Presence is not proof of metric provenance. |
| Deployable artifact | `models/final/deployable_artifact/pipeline_metadata.json` and serialized pipeline components. | Different artifact family/configuration from golden runner; cannot establish golden metrics. |
| Environment | `reports/reproduction_lock_audit/environment.txt` records an environment snapshot including Opacus 1.6.0. | No proven association to the golden manifest; current project dependencies do not pin Opacus. |
| Runtime/benchmark reports | JSON/CSV files remain in `reports/runtime/`, `reports/tables/`, and other report folders. | Provenance varies; no blanket claim that all were produced by current source. |
| Privacy outputs | `reports/privacy/` outputs and manifest entries exist, including numerical epsilon fields. | Mechanism/accounting mismatch; epsilon values are not validated guarantees, and the manifest does not independently substantiate its real-data assertion. |
| BCL | Candidate source and its reports existed in candidate checkout; original has separate risk-layer calibration. | Candidate evaluation was not run; contaminated test history and temporal integrity concerns remain. |
| XAI/adversarial | Source modules and historical reports are present. | Not all outputs are linked to source/data/model/environment hashes or independent validation. |

Do not hash or open prohibited data while enriching provenance. New manifests should record source commit, safe split identifiers, model hashes, config, environment lock, command, and output paths; they must be created only for authorized future experiments, not retroactively fabricated.

`experiment_manifest.schema.json` defines a prospective schema for authorized future runs. It requires revision and dirty-tree status, entrypoint/command, dataset authorization and split IDs, generator version/configuration, checkpoint identifiers/digests, training/evaluation configuration, dependency versions, metric definitions/values, timestamps, output digests, and safety-policy version. It is not a retroactive manifest and does not validate any historical metric or artifact. Do not include raw protected paths or create records from unverified assumptions.

The dataset `authorization_reference` is an opaque string, not proof of approval. The schema validates structure and selected field formats only; it does not verify external references, link a metric's split to a dataset split, validate configuration semantics, or attest to experiment execution. Synthetic-only schema examples and historical metric linkage gaps are recorded in `experiment_manifest_schema_examples.json` and `historical_provenance_matrix.md`.
