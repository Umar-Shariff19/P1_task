# V3 Temporal Correction Gate Report

**Date:** August 17, 2026  
**Scope:** Mathematical correction and independent validation of `temporal_causal_count` in `src/iot_ids/features/temporal/causal.py`  
**Target Function:** `add_causal_rolling_count()`  

---

## 1. Executive Summary

During the Phase 2 Forensic Audit, `temporal_causal_count` failed verification because the previous implementation computed `.rolling(window=100).count()` on an isolated Parquet chunk. In Pandas, `.rolling().count()` counts non-null rows within the sliding window of the *current chunk's Series*, ignoring cumulative offsets and resetting to `1.0` at every 250,000-row partition boundary.

This document presents the mathematical correction, theoretical proof of chunk-boundary invariance, and exact empirical validation across an 8-test unit suite and synthetic materialization integration tests.

The updated algorithm replaces chunk-local rolling counts with an exact stateful cumulative observation rank:
$$\text{temporal\_causal\_count} = \min(\text{raw\_cumcount} + \text{prior\_offset} + 1, \text{window})$$

All 8 deterministic unit tests and synthetic materializer integration tests passed with 100% exact numerical equality against un-chunked single-pass reference calculations.

**FINAL STATUS:** **`TEMPORAL CORRECTION — PASS`**

---

## 2. Mathematical Diagnosis of Previous Bug vs. Corrected Definition

### A. Previous Mathematical Bug
The previous implementation computed:
```python
raw_cumcount = ordered.groupby(group_col).cumcount()
offsets = ordered[group_col].map(lambda s: prior_counts.get(s, 0))
global_cumcount = raw_cumcount + offsets
values = global_cumcount.groupby(group_col).rolling(window=100, min_periods=1).count()
```
- `global_cumcount` produced correct cumulative values (e.g., `200, 201, 202...`).
- However, `.rolling(window=100).count()` on a Pandas Series counts the number of non-null entries in the sliding window of length 100 on the *chunk Series*.
- `.count()` ignores the numerical values inside `global_cumcount` (whether a value is `0` or `20000`, `.count()` evaluates to `1`).
- Because `.rolling()` was confined to a single Parquet chunk (250,000 rows), the first row of any IP in Chunk $N+1$ had a sliding window of size 1, causing `.count()` to evaluate to `1.0`.

### B. Intended Mathematical Definition
For a given group $g$ and a sequence of observations ordered causally by timestamp $t$:
Let $k_i$ be the 1-based global ordinal rank of observation $i$ within group $g$ across the entire dataset stream ($k_i = 1, 2, 3, \dots$).
The rolling count of observations belonging to group $g$ in a sliding window of size $W$ (where $W=100$) for observation $i$ is:
$$\text{temporal\_causal\_count}(i) = \begin{cases} k_i & \text{if } k_i \le W \\ W & \text{if } k_i > W \end{cases} = \min(k_i, W)$$

### C. Corrected Algorithm Implementation
```python
def add_causal_rolling_count(
    frame: pd.DataFrame,
    group_col: str,
    order_col: str,
    output_col: str,
    window: int,
    prior_counts: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if group_col not in frame or order_col not in frame:
        result = frame.copy()
        result[output_col] = pd.NA
        return result, prior_counts or {}
    if prior_counts is None:
        prior_counts = {}
    
    ordered = frame.sort_values([group_col, order_col], kind="mergesort").copy()
    
    # 0-based rank within group for current chunk
    raw_cumcount = ordered.groupby(group_col, sort=False).cumcount()
    
    # Carry-forward offset from prior chunks
    offsets = ordered[group_col].map(lambda s: prior_counts.get(s, 0))
    
    # 1-based global count of observations seen so far for this group
    global_k = raw_cumcount + offsets + 1
    
    # Bounded rolling count window: min(global_k, window)
    values = np.minimum(global_k, window).astype(float)
    ordered[output_col] = values
    
    # Update prior_counts with total rows seen so far
    updated_counts = dict(prior_counts)
    group_sizes = ordered.groupby(group_col, sort=False).size()
    for grp, size in group_sizes.items():
        updated_counts[grp] = prior_counts.get(grp, 0) + size
        
    return ordered.sort_index(), updated_counts
```

### D. Proof of Chunk-Boundary Invariance
Let a dataset contain $N$ rows for group $g$.
For any row $i \in \{0, 1, \dots, N-1\}$ (0-indexed global rank):
- `raw_cumcount` is the 0-based index of row $i$ within its partition.
- `offset` is the number of rows for group $g$ in all partitions preceding the current partition.
- Therefore, `raw_cumcount + offset` is identically equal to $i$ for any arbitrary partition boundary!
- Thus, `global_k = raw_cumcount + offset + 1 = i + 1`, which is strictly independent of partition size or placement.
- `temporal_causal_count = min(i + 1, W)`, which is 100% chunk-boundary invariant.

---

## 3. Empirical Unit Test Results

The test suite in `scratch/test_causal_correction.py` evaluated 8 deterministic scenarios:

| Test ID | Test Description | Condition | Result |
|---|---|---|---|
| **TEST 1** | Continuous 400-row sequence | Compare corrected output against single-pass unchunked reference for 400 rows | **PASS** (100% exact match) |
| **TEST 2** | 200 + 200 Chunk Equivalence | Process 400 rows as 1 chunk vs 2x200 chunks | **PASS** (100% exact match, state = `{'A': 400}`) |
| **TEST 3** | Arbitrary Chunk Boundaries | Test splits: (1,399), (50,350), (99,301), (100,300), (199,201), (200,200), (250,150), (10,20,30,40,50,250) | **PASS** (All 8 split patterns produced identical output to single pass) |
| **TEST 4** | Interleaved Groups | 400 rows with 3 interleaved IPs (`A`, `B`, `C`) processed across 4x100 chunks | **PASS** (100% exact match to reference) |
| **TEST 5** | Window Capping | Verify that feature caps at exactly `100.0` for all observations $k \ge 100$ | **PASS** (Row 99+ all equal `100.0`) |
| **TEST 6** | Zero Future Leakage | Modify timestamp of future row $i=350$; verify rows $0..349$ remain untouched | **PASS** (Rows $0..349$ byte-for-byte identical) |
| **TEST 7** | Empty / Missing Groups | Null `source_host` or missing schema columns handled without state corruption | **PASS** (State preserved, outputs set to `pd.NA`) |
| **TEST 8** | Causal Timestamp Ordering | Out-of-order timestamps within chunk correctly ordered causally by timestamp | **PASS** (Stable mergesort ordering verified) |

---

## 4. Materializer Integration Test Results

Synthetic integration tests were executed via `scratch/test_botiot_materializer_integration.py` and `scratch/test_materializer_integration.py` using `materialize_dataset()`:

1. **BoT-IoT Materializer Test**:
   - Materialized 1,000 rows across 148 partitions (chunksize=250, 500 rows/file).
   - Compared against a single-pass materialization (chunksize=2000).
   - **`temporal_causal_count`**: **100% EQUIVALENT** across chunks vs single pass.
   - **`behavioral_dest_diversity`**: **100% EQUIVALENT** across chunks vs single pass.

2. **Edge-IIoTset Materializer Test**:
   - Materialized 1,000 rows across 4 partitions.
   - **`behavioral_dest_diversity`**: **100% EQUIVALENT** across chunks vs single pass.

---

## 5. Final Gate Verdict

```
============================================================
                TEMPORAL CORRECTION — PASS
============================================================
```

### Current Status & Handoff Directives:
1. `src/iot_ids/features/temporal/causal.py` has been updated with the mathematically correct, chunk-boundary invariant implementation.
2. All 8 unit tests and materializer integration tests have passed with 100% exact equality.
3. The invalid V3 cache (`data/processed/v3_cache/BoT-IoT/53a044b6041c2d52/`) has been identified as invalid and MUST NOT be used for model training.
4. **STOPPING PER USER DIRECTIVE**: Full 73M-row rematerialization of BoT-IoT is paused awaiting user confirmation/approval.
