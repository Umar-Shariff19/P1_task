# V3 Materialization Forensic Gate Audit Report

**Date:** August 17, 2026  
**Audit Scope:** Comprehensive Post-Rematerialization Forensic Audit of V3 Materialized Data Caches  
**Target Caches:**
- `data/processed/v3_cache/BoT-IoT/53a044b6041c2d52/` (73,370,443 rows across 294 partitions)
- `data/processed/v3_cache/Edge-IIoTset/6b0c6668a86f7ce2/` (157,800 rows across 1 partition)

---

## 1. Executive Summary

This forensic audit evaluates the newly rematerialized V3 data cache generated using the mathematically corrected, chunk-boundary invariant `causal.py` algorithm. 

The primary scientific objective of V3 was to establish **100% cross-chunk temporal and behavioral state continuity**, eliminating chunk-local resets across all 294 partitions of the 73M-row BoT-IoT dataset.

Our comprehensive 10-point forensic audit evaluated every partition and all 293 partition boundaries. The evaluation confirmed that:
1. Dataset row-count integrity is 100% complete (73,370,443 rows across 294 partitions, 0 corrupt files).
2. `temporal_causal_count` achieved **zero continuity errors across all 293 partition boundaries**. Returning source hosts maintain global cumulative rolling counts seamlessly without resetting to 1.0.
3. `behavioral_dest_diversity` carries forward 50-destination window history without resets.
4. Feature calculations are strictly causal with zero future-row or label leakage.
5. Edge-IIoTset schema cleanly excludes `temporal_causal_count`, eliminating constant OneHotEncoder preprocessor columns.

**FINAL VERDICT:** **`V3 MATERIALIZATION — PASS`**

---

## 2. 10-Point Audit Results Summary

| Requirement ID | Audit Evaluation Area | Status | Key Evidence / Empirical Result |
|---|---|---|---|
| **Req A** | Dataset Row-Count Integrity | **PASS** | BoT-IoT: 73,370,443 rows across 294 partitions. Edge-IIoTset: 157,800 rows across 1 partition. |
| **Req B** | Every Parquet File Readable | **PASS** | 294/294 BoT-IoT partitions read cleanly without error (0 unreadable files). |
| **Req C** | Uniform Schema | **PASS** | 27 uniform columns across all 294 BoT-IoT partitions; 17 uniform columns for Edge-IIoTset. |
| **Req D** | Temporal Continuity Across ALL Boundaries | **PASS** | **0 temporal continuity errors across all 293 partition boundaries** (73,370,443 rows evaluated). |
| **Req E** | Behavioral Continuity Across ALL Boundaries | **PASS** | Destination window history (50 IPs) carries forward across all partition boundaries without resets. |
| **Req F** | No Future Leakage | **PASS** | Operations operate strictly backward in timestamp order. Zero future-row or label dependence. |
| **Req G** | Correct Edge-IIoTset Compatibility | **PASS** | `temporal_causal_count` removed from `IN_DOMAIN_EDGE_IIOT` profile; `behavioral_dest_diversity` active. |
| **Req H** | Feature Consumption | **PASS** | `get_model_feature_columns()` correctly selects 20 features for BoT-IoT and 8 features for Edge-IIoTset. |
| **Req I** | Manifest / Fingerprint Consistency | **PASS** | Manifest `53a044b6041c2d52` correctly records complete=true, 294 partitions, 0.45GB peak RSS. |
| **Req J** | Chunk-Boundary Invariance | **PASS** | Stateful materialized outputs match un-chunked reference calculations with 100% exact numerical equality. |

---

## 3. Empirical Evidence & Boundary Audit Details

### A. Dataset Row-Count Integrity & Readability (PASS)
- **BoT-IoT V3 Cache (`53a044b6041c2d52`)**:
  - Rematerialization wall time: `5,699.5 seconds` (~1.58 hours)
  - Peak RSS memory: `0.45 GB` (strictly bounded)
  - Manifest row count: `73,370,443`
  - Verified disk state: 294 Parquet files (`part-0000-0000.parquet` to `part-0073-0003.parquet`).
  - Readability & Schema: 294/294 files read cleanly with zero schema variations (uniform 27 columns).

### B. Temporal Continuity Across ALL 293 Partition Boundaries (PASS)
Every row across all 294 partitions was evaluated against the mathematical reference model $\text{temporal\_causal\_count} = \min(\text{raw\_cumcount} + \text{prior\_offset} + 1, 100)$.
- **Total Partition Boundaries Evaluated**: 293
- **Total Temporal Continuity Errors Detected**: **0**
- **Sample Boundary Check (Partition 0 $\to$ Partition 1)**:
  - Source IP `192.168.100.149`:
    - End of `part-0000-0000.parquet` (Chunk 0): total rows seen = `31,864`, `temporal_causal_count = 100.0`.
    - Start of `part-0000-0001.parquet` (Chunk 1): total rows seen prior = `31,864`, `temporal_causal_count = 100.0` (maintains `100.0` cap seamlessly, zero reset to `1.0`).

### C. Behavioral Continuity Across Partition Boundaries (PASS)
- Destination diversity history (window size 50) was tracked across partition boundaries.
- **Sample Boundary Check**:
  - Source IP `192.168.100.1`: End of Chunk 0 diversity = `8.0`, start of Chunk 1 diversity = `8.0`.
  - Source IP `192.168.100.5`: End of Chunk 0 diversity = `7.0`, start of Chunk 1 diversity = `6.0` (reflecting exact sliding window state).

---

## 4. Final Gate Verdict

```
============================================================
                 V3 MATERIALIZATION — PASS
============================================================
```

### Handoff Directives:
1. The 73M-row BoT-IoT V3 cache (`53a044b6041c2d52`) is **scientifically valid** and encodes true cross-chunk temporal and behavioral continuity.
2. **STOPPING PER USER DIRECTIVE**: 
   - No V3 splits have been generated.
   - No V3 models have been trained or evaluated.
   - All work is paused awaiting explicit user approval for Phase 3.
