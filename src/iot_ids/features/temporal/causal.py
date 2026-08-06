from __future__ import annotations

import pandas as pd


def add_causal_rolling_count(
    frame: pd.DataFrame,
    group_col: str,
    order_col: str,
    output_col: str,
    window: int,
) -> pd.DataFrame:
    if group_col not in frame or order_col not in frame:
        result = frame.copy()
        result[output_col] = pd.NA
        return result
    ordered = frame.sort_values([group_col, order_col], kind="mergesort").copy()
    values = (
        ordered.groupby(group_col, sort=False)
        .cumcount()
        .groupby(ordered[group_col], sort=False)
        .rolling(window=window, min_periods=1)
        .count()
        .reset_index(level=0, drop=True)
    )
    ordered[output_col] = values
    return ordered.sort_index()


def assert_temporal_causality(
    original: pd.DataFrame,
    transformed: pd.DataFrame,
    feature_col: str,
    order_col: str,
) -> None:
    changed_future = original.copy()
    last_idx = changed_future[order_col].idxmax()
    changed_future.loc[last_idx, order_col] = changed_future[order_col].max() + 10_000
    if not transformed.loc[original[order_col] < original[order_col].max(), feature_col].equals(
        transformed.loc[original[order_col] < original[order_col].max(), feature_col]
    ):
        raise AssertionError("Temporal feature depends on future observations.")

