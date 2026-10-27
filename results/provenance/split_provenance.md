# Split provenance

## Current source behavior

`scripts/03_materialize_and_audit_features.py` consumes each adapter stream, collects up to 2,000 benign and 5,000 attack flows (stopping when both targets are met or 150,000 flows have been scanned), partitions benign and attack lists separately by stream order using integer 60% and 80% cut points, combines the corresponding class pieces, then sorts rows within each completed split by timestamp. It resets feature-builder state at each split boundary and writes train/validation/test parquet files. This is not a global chronological partition. ToN-IoT, NF-ToN-IoT-v2, and CICIoT2023 adapters synthesize timestamps from row order/duration; Edge-IIoTset parses its frame-time field but falls back to an initialized/incremented timestamp if parsing fails. Adapter stream order is therefore not uniformly source event time. The older `scripts/03_create_splits.py` uses seeded stratified splitting for a different processed-data path and does not establish golden Stage 3 provenance.

## Existing artifacts and history

The tracked Stage 3 split files, golden models, and golden manifest were added together in release commit `53efe08` (2026-10-01). The manifest reports timestamp 2026-09-14, seed 42, four dataset names, feature count 21, and metrics, but no split hashes or generator source commit. Co-release does not prove that the current materializer generated the files. No splits were regenerated for this record.

## Conclusion

The current code procedure is identifiable. The exact procedure used to produce the existing official split files is **UNVERIFIED**. Do not describe existing files as globally chronological or attribute them to the current generator without a run-linked manifest. Further work: recover a trustworthy historical run record if one exists; otherwise design a new, separately authorized split experiment without touching protected data.

## Future reproducible split design (proposal only)

Do not apply this proposal to existing files or treat it as a reconstruction of their history. For a future authorized study, first freeze an explicit input-file manifest and label/schema version. Use verified source event-time values only; reject or explicitly classify synthesized timestamps rather than treating them as event time. Establish global per-dataset time boundaries before any class balancing or sampling, assign all rows at a boundary deterministically using a stable source-file/row key, and keep sessions/devices grouped when the source provides reliable grouping identifiers. Fit all learned preprocessing on train only. Keep the final test partition sealed until the protocol and model selection are frozen. Report class support and any exclusions per time window.

If source event time or grouping identity is not trustworthy, use a separately approved seeded stratified/grouped random split and explicitly describe it as non-temporal. A future run manifest should bind the exact generator revision/configuration, input/split identifier, split boundaries or seed, label/schema version, model/checkpoint IDs, evaluation configuration, environment, metric definitions, outputs, and safety-policy version. Owner approval and a new experiment are required; no split generation or evaluation was performed here.
