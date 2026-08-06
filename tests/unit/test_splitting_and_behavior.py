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

