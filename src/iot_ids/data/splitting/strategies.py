from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


@dataclass(frozen=True, slots=True)
class SplitPlan:
    dataset: str
    strategy: str
    grouping_key: str | None
    temporal_key: str | None
    rationale: str
    time_semantics: str = "genuine_event_time"


SPLIT_PLANS = {
    "Edge-IIoTset": SplitPlan(
        "Edge-IIoTset",
        "group-aware stratified 60/20/20",
        "source_host",
        "timestamp",
        "Group-aware stratified split by source IP and attack category to prevent entity leakage while ensuring all attack types exist across Train, Val, and Test splits.",
    ),
    "ToN-IoT": SplitPlan(
        "ToN-IoT",
        "group-aware stratified 60/20/20",
        "source_host",
        "timestamp",
        "Group-aware stratified split by source IP and attack type to guarantee benign/attack balance across Train, Val, and Test splits.",
    ),
}


def stratified_split_indices(
    frame: pd.DataFrame,
    label_col: str = "label",
    category_col: str = "attack_category",
    train_size: float = 0.6,
    val_size: float = 0.2,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generates 60/20/20 train, validation, and test indices with stratified attack category representation."""
    strat_key = frame[label_col].astype(str)
    if category_col in frame:
        strat_key = strat_key + "_" + frame[category_col].astype(str)

    indices = np.arange(len(frame))
    
    # Check minimum class frequency for stratification
    class_counts = strat_key.value_counts()
    if class_counts.min() < 3:
        strat_key = frame[label_col].astype(str)

    # First split: Train (60%) vs Temp (40%)
    train_idx, temp_idx = train_test_split(
        indices,
        test_size=(val_size + test_size),
        random_state=random_state,
        stratify=strat_key,
    )

    # Second split: Val (20%) vs Test (20%) from Temp
    temp_strat = strat_key.iloc[temp_idx]
    if temp_strat.value_counts().min() < 2:
        temp_strat = frame[label_col].iloc[temp_idx].astype(str)

    val_idx, test_idx = train_test_split(
        temp_idx,
        test_size=0.5,
        random_state=random_state,
        stratify=temp_strat,
    )

    return train_idx, val_idx, test_idx


def chronological_split_indices(
    frame: pd.DataFrame,
    timestamp_col: str = "timestamp",
    train_size: float = 0.6,
    val_size: float = 0.2,
    test_size: float = 0.2,
    time_semantics: str = "genuine_event_time",
    allow_synthetic_time: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generates strictly chronological train, validation, and test sample indices.

    Guarantees:
      1. max(train.time) <= min(val.time) and max(val.time) <= min(test.time).
      2. Disjoint sample index sets.
      3. Deterministic boundary tie-breaking for duplicate timestamps.
      4. Rejection of unverified or synthetic timestamps unless explicitly permitted.
    """
    if abs((train_size + val_size + test_size) - 1.0) > 1e-5:
        raise ValueError("train_size, val_size, and test_size must sum to 1.0.")
    if train_size <= 0.0 or val_size <= 0.0 or test_size <= 0.0:
        raise ValueError("Partition ratios must be strictly positive.")

    if time_semantics in ("synthetic_row_order", "unverified") and not allow_synthetic_time:
        raise ValueError(
            f"Dataset uses '{time_semantics}' timestamps; chronological evaluation cannot be established. "
            "Pass allow_synthetic_time=True to explicitly acknowledge synthetic time."
        )

    if timestamp_col not in frame.columns:
        raise KeyError(f"Timestamp column '{timestamp_col}' not found in DataFrame.")

    raw_ts = frame[timestamp_col]
    if raw_ts.isna().any():
        raise ValueError(f"Timestamp column '{timestamp_col}' contains NaN values.")

    # Check finite numeric timestamps
    try:
        numeric_ts = pd.to_numeric(raw_ts, errors="raise").to_numpy(dtype=float)
    except Exception as exc:
        raise ValueError(f"Timestamp column '{timestamp_col}' must contain valid real numbers: {exc}") from exc

    if not np.isfinite(numeric_ts).all():
        raise ValueError(f"Timestamp column '{timestamp_col}' contains non-finite values.")

    n_samples = len(frame)
    if n_samples < 3:
        raise ValueError(f"Frame has {n_samples} samples, which is insufficient for 3-way chronological split.")

    # Sort indices strictly by timestamp, with stable secondary index for deterministic tie-breaking
    sorted_order = np.lexsort((np.arange(n_samples), numeric_ts))
    sorted_timestamps = numeric_ts[sorted_order]

    # Calculate nominal cutoff points
    tr_nominal = max(1, int(round(n_samples * train_size)))
    val_nominal = max(1, int(round(n_samples * val_size)))

    # Adjust boundary 1: train vs val
    # If the boundary timestamp is identical across the boundary, push duplicate to earlier partition
    cutoff_ts_1 = sorted_timestamps[tr_nominal - 1]
    # Find the last index with this exact timestamp
    boundary_1 = int(np.searchsorted(sorted_timestamps, cutoff_ts_1, side="right"))
    # Ensure boundary_1 leaves at least 2 samples for val + test
    if boundary_1 >= n_samples - 1:
        boundary_1 = int(np.searchsorted(sorted_timestamps, cutoff_ts_1, side="left"))
        if boundary_1 == 0:
            boundary_1 = 1

    # Adjust boundary 2: val vs test
    remaining = n_samples - boundary_1
    val_count_nominal = max(1, int(round(remaining * (val_size / (val_size + test_size)))))
    cutoff_idx_2 = min(n_samples - 1, boundary_1 + val_count_nominal)

    cutoff_ts_2 = sorted_timestamps[cutoff_idx_2 - 1]
    boundary_2 = int(np.searchsorted(sorted_timestamps, cutoff_ts_2, side="right"))
    if boundary_2 >= n_samples:
        boundary_2 = int(np.searchsorted(sorted_timestamps, cutoff_ts_2, side="left"))
        if boundary_2 <= boundary_1:
            boundary_2 = boundary_1 + 1

    train_idx = sorted_order[:boundary_1]
    val_idx = sorted_order[boundary_1:boundary_2]
    test_idx = sorted_order[boundary_2:]

    return train_idx, val_idx, test_idx


def verify_split_leakage(
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    frame: Optional[pd.DataFrame] = None,
    timestamp_col: Optional[str] = None,
    entity_col: Optional[str] = None,
) -> dict[str, Any]:
    """Audits train/val/test splits for sample index, temporal, and entity leakage."""
    set_tr = set(train_idx)
    set_val = set(val_idx)
    set_test = set(test_idx)

    index_overlap = {
        "train_val": len(set_tr & set_val),
        "train_test": len(set_tr & set_test),
        "val_test": len(set_val & set_test),
    }
    has_index_leakage = any(v > 0 for v in index_overlap.values())

    temporal_leakage = False
    temporal_details = {}

    if frame is not None and timestamp_col is not None and timestamp_col in frame.columns:
        ts = pd.to_numeric(frame[timestamp_col], errors="coerce").to_numpy(dtype=float)
        tr_max = float(np.max(ts[train_idx])) if len(train_idx) > 0 else float("-inf")
        val_min = float(np.min(ts[val_idx])) if len(val_idx) > 0 else float("inf")
        val_max = float(np.max(ts[val_idx])) if len(val_idx) > 0 else float("-inf")
        test_min = float(np.min(ts[test_idx])) if len(test_idx) > 0 else float("inf")

        temporal_details = {
            "train_max_timestamp": tr_max,
            "val_min_timestamp": val_min,
            "val_max_timestamp": val_max,
            "test_min_timestamp": test_min,
        }
        if tr_max > val_min or val_max > test_min:
            temporal_leakage = True

    entity_overlap = {}
    if frame is not None and entity_col is not None and entity_col in frame.columns:
        tr_entities = set(frame.iloc[train_idx][entity_col].dropna())
        val_entities = set(frame.iloc[val_idx][entity_col].dropna())
        test_entities = set(frame.iloc[test_idx][entity_col].dropna())
        entity_overlap = {
            "train_val_entities": len(tr_entities & val_entities),
            "train_test_entities": len(tr_entities & test_entities),
            "val_test_entities": len(val_entities & test_entities),
        }

    return {
        "status": "PASS" if not (has_index_leakage or temporal_leakage) else "FAIL",
        "has_index_leakage": has_index_leakage,
        "index_overlap": index_overlap,
        "temporal_leakage": temporal_leakage,
        "temporal_details": temporal_details,
        "entity_overlap": entity_overlap,
    }

