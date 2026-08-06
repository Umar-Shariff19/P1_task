# Splitting Strategy

Version: `split-strategy-v1`

Splitting logic is defined in `configs/experiments/splits.json` and `src/iot_ids/data/splitting/strategies.py`.

## CICIDS2017

Use source-file/day-aware splitting where possible. Daily files represent collection windows and attack campaigns, so random row splitting can overstate generalization.

## Edge-IIoTset

Use source/time-aware splitting when `frame.time` is valid. The prepared ML CSV is the P1 tabular source; timestamp and IP fields are metadata for ordering and behavior generation, not direct model input.

## BoT-IoT

Use partition/time-aware splitting. Do not concatenate all 74 partitions into memory. `stime`/`ltime` support chronological analysis; source partition is preserved for chunk-aware processing.

## N-BaIoT

Use device-aware grouped splitting for domain analysis. Device identity is not a direct feature. Filename-derived attack family/subtype is label metadata.

## Milestone 2.5 Sanity Evidence

Detailed split sanity evidence is generated at `reports/eda/split_sanity.json`. This includes class-coverage limitations and contamination checks required before final train/validation/test split materialization.
