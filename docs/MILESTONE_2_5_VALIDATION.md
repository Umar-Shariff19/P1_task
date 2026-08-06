# Milestone 2.5 Validation

## Pytest Shutdown

Root cause: pytest completed repository tests but hung while creating/writing `.pytest_cache` during session finish under the Codex sandbox. `faulthandler` showed the stack in `_pytest.cacheprovider._ensure_cache_dir_and_supporting_files`. With approved write access to the authoritative repository, pytest returned normally.

Final result: `19 passed, 4 warnings in 4.65s`, exit code `0`.

## C/E/B Semantic Profile Audit

Evidence is stored in:

- `reports/eda/semantic_profile_audit.json`
- `reports/eda/semantic_profile_audit.md`

Final `FLOW_COMPATIBLE_C_E_B` profile:

- `duration_seconds`
- `dst_port`
- `total_bytes`
- `packet_length_mean`

Milestone 2.5 changed this from 7 to 4 features. The previous profile included `syn_flag_count`, `ack_flag_count`, and `rst_flag_count`, but BoT-IoT does not expose audited decomposed SYN/ACK/RST count fields equivalent to CICIDS2017 and Edge-IIoTset.

## N-BaIoT Compatibility

N-BaIoT remains fully included in P1 for same-dataset evaluation and its own source-aggregate feature profile. Direct transfer between N-BaIoT and CICIDS2017/Edge-IIoTset/BoT-IoT is marked `N/A - incompatible representation`.

Reason: N-BaIoT traffic files contain source-provided KitNET-style host/host-pair damped-window aggregate statistics, not raw flow fields. No defensible direct transformation reconstructs the flow-compatible C/E/B feature space.

Compatibility metadata:

- `configs/experiments/cross_dataset_compatibility.json`
- `reports/eda/nbaiot_compatibility.json`

## Feature-Level Audit

Feature-level audit is stored in `reports/eda/feature_level_audit.json`.

Final counts:

- instant: 17
- temporal: 4
- behavioral: 5

Reclassification: `source_agg_*` moved from temporal to behavioral because the N-BaIoT fields describe source-provided host/host-pair behavior over historical decay windows. They are not instant features.

## Split Sanity

Split sanity evidence is stored in `reports/eda/split_sanity.json`.

- CICIDS2017: source daily CSV/day-aware splitting. Binary coverage must be verified because attack families are file/campaign concentrated.
- Edge-IIoTset: single prepared ML CSV; time-aware split if `frame.time` is reliable, otherwise stratified row split with leakage warning.
- BoT-IoT: partition/time-aware split using source partition plus `stime`; normal traffic is extremely rare, so benign coverage must be explicitly guarded.
- N-BaIoT: device-aware grouped split; no raw timestamp field is available in traffic CSVs.

## Bounded Production-Path Benchmark

Benchmark evidence is stored in `reports/eda/materialization_benchmark.json`.

This benchmark used the production materialization path with bounded rows per file. It is not model performance and not full-data materialization.

Rows processed: 2,139,800  
Cache output size: 370,038,370 bytes

Dataset results:

- CICIDS2017: 160,000 rows, 8 partitions, 15.29 s, 10,461.79 rows/s, peak RSS 159,969,280 bytes, output 9,597,545 bytes.
- Edge-IIoTset: 157,800 rows, 4 partitions, 3.47 s, 45,416.39 rows/s, peak RSS 222,154,752 bytes, output 1,336,114 bytes.
- BoT-IoT: 1,110,000 rows, 74 partitions, 64.54 s, 17,199.86 rows/s, peak RSS 171,311,104 bytes, output 28,530,962 bytes.
- N-BaIoT: 712,000 rows, 89 partitions, 174.96 s, 4,069.55 rows/s, peak RSS 206,499,840 bytes, output 330,554,972 bytes.

Approximate full materialization estimates from measured throughput:

- CICIDS2017: ~4.5 minutes, ~170 MB output.
- Edge-IIoTset: ~3.5 seconds, ~1.3 MB output.
- BoT-IoT: ~71.1 minutes, ~1.9 GB output.
- N-BaIoT: ~28.9 minutes, ~3.3 GB output.

These are estimates from bounded samples and may shift with disk cache, row ordering, compression behavior, and full-scale category distributions.

## Cache/Restart Validation

Cache validation is stored in `reports/eda/cache_restart_validation.json`.

Results:

- unchanged cache reuse: passed
- feature-version invalidation: passed
- incomplete-cache rejection: passed
- interrupted/partial output behavior: invalid manifests or partition-count mismatches are not accepted as complete
- raw-data immutability: materializer only reads `data/raw` and writes under configured cache output roots

## Preprocessing Fit Contract

Automated tests verify that a preprocessor fitted on source train data can transform source validation, source test, and compatible target data without changing fitted state. The fit summary/median state remains source-train-only.

