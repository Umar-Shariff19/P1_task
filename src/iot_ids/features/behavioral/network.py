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
    prior_history: dict[str, list[str]] | None = None,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    if source_col not in frame or destination_col not in frame:
        result = frame.copy()
        result[output_col] = pd.NA
        return result, prior_history or {}
    result = frame.copy()
    values: list[float] = []
    # Deep-copy prior history to avoid mutating caller's state
    history: dict[str, list[str]] = {}
    if prior_history:
        for k, v in prior_history.items():
            history[k] = list(v)
    for _, row in result.iterrows():
        source = str(row[source_col])
        recent = history.setdefault(source, [])
        values.append(float(len(set(recent[-window:]))))
        recent.append(str(row[destination_col]))
        # Cap history to avoid unbounded memory growth
        if len(recent) > window * 2:
            history[source] = recent[-window:]
    result[output_col] = values
    # Trim histories to window before returning for cross-chunk carry
    trimmed: dict[str, list[str]] = {}
    for k, v in history.items():
        trimmed[k] = v[-window:]
    return result, trimmed

