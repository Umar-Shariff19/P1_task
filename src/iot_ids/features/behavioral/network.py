from __future__ import annotations

import math

import pandas as pd


def entropy(values: pd.Series) -> float:
    counts = values.dropna().astype(str).value_counts()
    total = counts.sum()
    if total == 0:
        return 0.0
    return float(-sum((count / total) * math.log2(count / total) for count in counts))


def add_historical_destination_diversity(
    frame: pd.DataFrame,
    source_col: str,
    destination_col: str,
    output_col: str,
    window: int,
) -> pd.DataFrame:
    if source_col not in frame or destination_col not in frame:
        result = frame.copy()
        result[output_col] = pd.NA
        return result
    result = frame.copy()
    values: list[float] = []
    history: dict[str, list[str]] = {}
    for _, row in result.iterrows():
        source = str(row[source_col])
        recent = history.setdefault(source, [])
        values.append(float(len(set(recent[-window:]))))
        recent.append(str(row[destination_col]))
    result[output_col] = values
    return result

