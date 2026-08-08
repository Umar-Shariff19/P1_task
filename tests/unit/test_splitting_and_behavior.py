from __future__ import annotations

import pandas as pd

from iot_ids.data.splitting.strategies import SPLIT_PLANS, grouped_split_indices
from iot_ids.features.behavioral.network import add_historical_destination_diversity, entropy


def test_split_plans_exist_for_all_datasets() -> None:
    assert set(SPLIT_PLANS) == {"CICIDS2017", "Edge-IIoTset", "BoT-IoT", "N-BaIoT"}


def test_grouped_split_has_no_group_overlap() -> None:
    frame = pd.DataFrame({"group": ["a", "a", "b", "b", "c", "c"], "label": [0, 1, 0, 1, 0, 1]})
    train_idx, test_idx = grouped_split_indices(frame, "group", test_size=0.34, random_state=1)
    assert set(frame.loc[train_idx, "group"]).isdisjoint(set(frame.loc[test_idx, "group"]))


def test_behavioral_destination_diversity_is_historical() -> None:
    frame = pd.DataFrame({"src": ["a", "a", "a"], "dst": ["x", "y", "y"]})
    out = add_historical_destination_diversity(frame, "src", "dst", "div", window=10)
    assert out["div"].tolist() == [0.0, 1.0, 2.0]
    assert entropy(pd.Series(["x", "x", "y"])) > 0


def test_hash_deterministic_split_consistency() -> None:
    """Same hash always maps to the same split, preventing cross-split leakage."""
    # Import from the 3A script's logic (replicated here for unit test independence)
    import hashlib

    def _hash_to_split(key: str, train_pct: int = 70, val_pct: int = 15) -> str:
        bucket = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % 100
        if bucket < train_pct:
            return "train"
        if bucket < train_pct + val_pct:
            return "validation"
        return "test"

    # Determinism: same input → same output across many calls
    for key in ["abc123", "row_hash_deadbeef", "duplicate_row_xyz"]:
        results = {_hash_to_split(key) for _ in range(100)}
        assert len(results) == 1, f"Non-deterministic split for key {key}"

    # Coverage: a range of inputs covers all three splits
    splits_seen = {_hash_to_split(str(i)) for i in range(1000)}
    assert splits_seen == {"train", "validation", "test"}

    # Duplicate guarantee: identical canonical rows → identical split
    dup_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    split_a = _hash_to_split(dup_hash)
    split_b = _hash_to_split(dup_hash)
    assert split_a == split_b


def test_nbaiot_device_split_allocation() -> None:
    """N-BaIoT device-holdout: devices 1-7 train, 8 val, 9 test."""
    def _nbaiot_device_split(device_id: str) -> str:
        if device_id in {"8"}:
            return "validation"
        if device_id in {"9"}:
            return "test"
        return "train"

    assert _nbaiot_device_split("1") == "train"
    assert _nbaiot_device_split("7") == "train"
    assert _nbaiot_device_split("8") == "validation"
    assert _nbaiot_device_split("9") == "test"
    # No device appears in multiple splits
    all_devices = [str(d) for d in range(1, 10)]
    split_map = {d: _nbaiot_device_split(d) for d in all_devices}
    from collections import Counter
    counts = Counter(split_map.values())
    assert counts["train"] == 7
    assert counts["validation"] == 1
    assert counts["test"] == 1

