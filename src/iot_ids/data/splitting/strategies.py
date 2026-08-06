from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split


@dataclass(frozen=True, slots=True)
class SplitPlan:
    dataset: str
    strategy: str
    grouping_key: str | None
    temporal_key: str | None
    rationale: str


SPLIT_PLANS = {
    "CICIDS2017": SplitPlan("CICIDS2017", "source-file/day-aware holdout", "source_file", None, "Daily files encode collection windows and should not be randomly interleaved without analysis."),
    "Edge-IIoTset": SplitPlan("Edge-IIoTset", "time/source-aware when frame.time is valid", "source_file", "frame.time", "Prepared CSV has frame.time plus protocol/source fields; timestamps are metadata for splitting/features, not direct model inputs."),
    "BoT-IoT": SplitPlan("BoT-IoT", "partition/time-aware", "source_file", "stime", "Large partitions require chunk-aware handling; stime/ltime allow chronological validation where coverage permits."),
    "N-BaIoT": SplitPlan("N-BaIoT", "device-aware grouped split", "device_id", None, "Device identity must be withheld as direct input but is appropriate for grouped generalization analysis."),
}


def grouped_split_indices(frame: pd.DataFrame, group_col: str, test_size: float = 0.2, random_state: int = 42):
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(splitter.split(frame, groups=frame[group_col]))
    return train_idx, test_idx


def stratified_row_split_indices(frame: pd.DataFrame, label_col: str, test_size: float = 0.2, random_state: int = 42):
    return train_test_split(
        frame.index.to_numpy(),
        test_size=test_size,
        random_state=random_state,
        stratify=frame[label_col] if label_col in frame else None,
    )

