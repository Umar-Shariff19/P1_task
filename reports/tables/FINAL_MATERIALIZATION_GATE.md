# FINAL MATERIALIZATION FORENSIC GATE REPORT

> [!IMPORTANT]
> **VERDICT: MATERIALIZATION FORENSIC GATE — PASS**
>
> All active datasets (**Edge-IIoTset** and **ToN-IoT Network**) have been successfully materialized into `data/processed/final/` with valid schema definitions and causal state tracking.

---

## Materialization Manifest Evidence

| Dataset | Fingerprint | Total Rows | Parquet Partitions | Schema Columns | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Edge-IIoTset** | `4519e086d92eec3c` | 157,800 | 1 | 21 | **PASS** |
| **ToN-IoT Network** | `a50cbde36eb468bf` | 211,043 | 1 | 21 | **PASS** |

---

## Schema & Feature Inspection
- **F_common (8 Features)**: `duration`, `src_bytes`, `src_pkts`, `dst_pkts`, `proto_tcp`, `proto_udp`, `proto_icmp`, `is_well_known_port` present in both.
- **Causal State Tracking**: Monotonic propagation verified with zero chunk-boundary resets.
- **Verdict**: **MATERIALIZATION FORENSIC GATE PASSED**.
