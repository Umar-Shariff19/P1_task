# Canonical Feature Schema

Version: `canonical-features-v1`

The canonical schema is defined in `configs/features/canonical_schema.json`.

## Scientific Decision

A simple intersection of raw column names is invalid. The datasets differ by capture tooling and representation:

- CICIDS2017, Edge-IIoTset and BoT-IoT expose flow/current-record statistics.
- N-BaIoT exposes source-provided damped-window aggregate features used by KitNET-style IoT traffic modeling.

Therefore the frozen strategy is:

- `FLOW_COMPATIBLE_C_E_B`: defensible shared flow-compatible profile for CICIDS2017, Edge-IIoTset and BoT-IoT. Milestone 2.5 reduced this profile from 7 to 4 features after auditing that TCP flag features are not equivalently available in BoT-IoT as decomposed SYN/ACK/RST counts.
- `FLOW_RICH_C_B`: richer flow profile for CICIDS2017 and BoT-IoT.
- `NBAIOT_SOURCE_AGGREGATE`: N-BaIoT source-provided temporal/behavioral aggregate profile.

The strict four-dataset universal raw-flow feature profile is not scientifically defensible at this milestone. N-BaIoT will be handled transparently as a source-aggregate representation rather than pretending raw temporal sequences can be reconstructed.

## Feature Levels

- Instant: current-record measurements such as duration, bytes, packets, ports, rates and TCP flags.
- Temporal: source-provided or causally generated timing/history statistics.
- Behavioral: network behavior descriptors such as traffic asymmetry, source/destination grouping keys for causal feature generation, and N-BaIoT source-provided host/host-pair aggregate behavior over historical decay windows.

Feature group membership is machine-readable and supports later ablation selection.
