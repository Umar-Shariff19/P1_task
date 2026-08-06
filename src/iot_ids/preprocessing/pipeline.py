from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(slots=True)
class FittedPreprocessor:
    feature_order: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    transformer: ColumnTransformer
    schema_version: str = "canonical-features-v1"
    fit_summary: dict[str, Any] | None = None

    def transform(self, frame: pd.DataFrame):
        self.validate_schema(frame)
        clean = frame[self.feature_order].replace([np.inf, -np.inf], np.nan)
        return self.transformer.transform(clean)

    def validate_schema(self, frame: pd.DataFrame) -> None:
        missing = [column for column in self.feature_order if column not in frame.columns]
        if missing:
            raise ValueError(f"Missing required feature columns: {missing}")

    def save(self, path: str | Path) -> None:
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str | Path) -> "FittedPreprocessor":
        loaded = joblib.load(path)
        if not isinstance(loaded, cls):
            raise TypeError(f"Expected FittedPreprocessor, got {type(loaded)!r}")
        return loaded


def fit_preprocessor(frame: pd.DataFrame, feature_order: list[str]) -> FittedPreprocessor:
    clean = frame[feature_order].replace([np.inf, -np.inf], np.nan)
    numeric_features = [col for col in feature_order if pd.api.types.is_numeric_dtype(clean[col])]
    categorical_features = [col for col in feature_order if col not in numeric_features]
    transformer = ColumnTransformer(
        transformers=[
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric_features),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
                    ]
                ),
                categorical_features,
            ),
        ],
        remainder="drop",
    )
    transformer.fit(clean)
    summary = {
        "fit_rows": int(len(clean)),
        "numeric_medians": {
            col: float(clean[col].replace([np.inf, -np.inf], np.nan).median())
            for col in numeric_features
        },
        "categorical_modes": {
            col: str(clean[col].mode(dropna=True).iloc[0]) if not clean[col].mode(dropna=True).empty else ""
            for col in categorical_features
        },
    }
    return FittedPreprocessor(feature_order, numeric_features, categorical_features, transformer, fit_summary=summary)
