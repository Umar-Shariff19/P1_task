# Leakage Analysis

Version: `leakage-metadata-v1`

Roles are stored in `configs/features/leakage_metadata.json`.

## Global Rules

- Labels and label-derived taxonomy columns are never model inputs.
- IPs, MACs, device IDs, file/source names, row IDs and sequence IDs are metadata unless explicitly used to construct causal temporal or behavioral features.
- Timestamps may be used for ordering and leakage-safe splits; they are not direct model features.
- Entity identifiers may be used for grouping/history construction; they are excluded from direct predictive matrices.
- Payload-like fields such as HTTP URI/query/body and MQTT messages are excluded because they can encode attack scripts or collection artifacts.

## Dataset Notes

- CICIDS2017: no Flow ID/IP/Timestamp columns appear in the audited MachineLearningCSV schema. `Destination Port` is conditional because service semantics are useful but can encode scenario setup. `Fwd Header Length.1` is excluded as a duplicate column. Idle timing columns are safe flow statistics, not leakage.
- Edge-IIoTset: `Attack_label` and `Attack_type` are labels. `frame.time`, `ip.src_host`, and `ip.dst_host` are metadata for ordering/behavior construction. HTTP/MQTT payload and URI fields are leakage risks and excluded from model input.
- BoT-IoT: `attack`, `category`, and `subcategory` are labels. `saddr`, `daddr`, `stime`, and `ltime` are metadata for grouping/ordering. `pkSeqID`, MAC/OUI columns are leakage risks.
- N-BaIoT: device identity and filename-derived labels are metadata. Device IDs are valid for grouped/domain splits but not direct model inputs.

