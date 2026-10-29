from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from iot_ids.data.splitting.strategies import (
    SPLIT_PLANS,
    chronological_split_indices,
    stratified_split_indices,
    verify_split_leakage,
)
from iot_ids.features.behavioral.network import add_historical_destination_diversity, entropy


def test_split_plans_exist_for_active_datasets() -> None:
    assert set(SPLIT_PLANS) == {"Edge-IIoTset", "ToN-IoT"}


def test_stratified_split_indices_proportions() -> None:
    df = pd.DataFrame({
        "label": [0] * 60 + [1] * 40,
        "attack_category": ["Normal"] * 60 + ["DoS"] * 20 + ["Scanning"] * 20
    })
    tr, val, tst = stratified_split_indices(df, label_col="label", category_col="attack_category")
    assert len(tr) == 60
    assert len(val) == 20
    assert len(tst) == 20
    assert len(set(tr).intersection(set(val))) == 0
    assert len(set(tr).intersection(set(tst))) == 0
    assert len(set(val).intersection(set(tst))) == 0


def test_chronological_split_strict_ordering() -> None:
    # 100 samples with increasing timestamps
    timestamps = np.linspace(1000.0, 2000.0, 100)
    df = pd.DataFrame({
        "timestamp": timestamps,
        "feature": np.random.randn(100),
        "label": [0] * 70 + [1] * 30,
    })
    tr, val, tst = chronological_split_indices(df, timestamp_col="timestamp")

    assert len(tr) + len(val) + len(tst) == 100
    assert set(tr).isdisjoint(set(val))
    assert set(tr).isdisjoint(set(tst))
    assert set(val).isdisjoint(set(tst))

    # Strict chronological boundary invariant
    tr_max = df.iloc[tr]["timestamp"].max()
    val_min = df.iloc[val]["timestamp"].min()
    val_max = df.iloc[val]["timestamp"].max()
    tst_min = df.iloc[tst]["timestamp"].min()

    assert tr_max <= val_min
    assert val_max <= tst_min

    # Verify leakage auditor
    audit = verify_split_leakage(tr, val, tst, frame=df, timestamp_col="timestamp")
    assert audit["status"] == "PASS"
    assert audit["has_index_leakage"] is False
    assert audit["temporal_leakage"] is False


def test_chronological_split_handles_boundary_duplicates() -> None:
    # Multiple identical timestamps at the boundary
    timestamps = [100.0] * 50 + [200.0] * 50
    df = pd.DataFrame({"timestamp": timestamps, "val": range(100)})
    tr, val, tst = chronological_split_indices(df, timestamp_col="timestamp")

    assert set(tr).isdisjoint(set(val))
    assert set(tr).isdisjoint(set(tst))
    assert set(val).isdisjoint(set(tst))

    audit = verify_split_leakage(tr, val, tst, frame=df, timestamp_col="timestamp")
    assert audit["status"] == "PASS"
    assert audit["temporal_leakage"] is False


def test_chronological_split_rejects_synthetic_time_without_override() -> None:
    df = pd.DataFrame({"timestamp": [1.0, 2.0, 3.0, 4.0]})
    with pytest.raises(ValueError, match="synthetic_row_order"):
        chronological_split_indices(df, time_semantics="synthetic_row_order", allow_synthetic_time=False)

    # Allowed with explicit override
    tr, val, tst = chronological_split_indices(
        df, time_semantics="synthetic_row_order", allow_synthetic_time=True
    )
    assert len(tr) + len(val) + len(tst) == 4


def test_chronological_split_rejects_nan_and_missing_timestamps() -> None:
    df_missing_col = pd.DataFrame({"time_wrong": [1.0, 2.0, 3.0]})
    with pytest.raises(KeyError, match="not found"):
        chronological_split_indices(df_missing_col, timestamp_col="timestamp")

    df_nan = pd.DataFrame({"timestamp": [1.0, np.nan, 3.0]})
    with pytest.raises(ValueError, match="NaN"):
        chronological_split_indices(df_nan, timestamp_col="timestamp")

    df_inf = pd.DataFrame({"timestamp": [1.0, np.inf, 3.0]})
    with pytest.raises(ValueError, match="non-finite"):
        chronological_split_indices(df_inf, timestamp_col="timestamp")

    df_undersized = pd.DataFrame({"timestamp": [1.0, 2.0]})
    with pytest.raises(ValueError, match="insufficient"):
        chronological_split_indices(df_undersized, timestamp_col="timestamp")

    df_valid = pd.DataFrame({"timestamp": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="must sum to 1.0"):
        chronological_split_indices(df_valid, train_size=0.5, val_size=0.2, test_size=0.2)

    with pytest.raises(ValueError, match="strictly positive"):
        chronological_split_indices(df_valid, train_size=0.0, val_size=0.5, test_size=0.5)


def test_preprocessing_fitted_on_train_only() -> None:
    # Ensure validation and test data NEVER influence fitted preprocessor parameters
    df = pd.DataFrame({
        "timestamp": range(100),
        "feat": [10.0] * 60 + [1000.0] * 40,  # Huge shift in val/test
    })
    tr, val, tst = chronological_split_indices(df, timestamp_col="timestamp")

    scaler = StandardScaler()
    X_tr = scaler.fit_transform(df.iloc[tr][["feat"]])
    X_val = scaler.transform(df.iloc[val][["feat"]])
    X_tst = scaler.transform(df.iloc[tst][["feat"]])

    # Mean must be exactly 10.0 (from train data only, completely untainted by 1000.0)
    assert abs(scaler.mean_[0] - 10.0) < 1e-6
    assert abs(X_tr.mean()) < 1e-6
    # val and test standardized with train mean and scale
    assert (X_val > 0.0).all()


def test_behavioral_destination_diversity_is_historical() -> None:
    frame = pd.DataFrame({"src": ["a", "a", "a"], "dst": ["x", "y", "y"]})
    out_df, _ = add_historical_destination_diversity(frame, "src", "dst", "div", window=10)
    assert out_df["div"].tolist() == [0.0, 1.0, 2.0]
    assert entropy(pd.Series(["x", "x", "y"])) > 0

