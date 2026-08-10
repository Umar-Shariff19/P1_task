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


import json

def get_model_feature_columns(dataset: str, profile: str = "in_domain", levels: list[str] | None = None) -> list[str]:
    """Returns the exact ordered feature column list from the canonical schema.
    
    Args:
        dataset: Dataset name (CICIDS2017, Edge-IIoTset, BoT-IoT, N-BaIoT).
        profile: 'in_domain' for full multi-level features, 'cross_domain' for
                 the strict 4-feature universal profile (FLOW_COMPATIBLE_C_E_B).
        levels: Optional list of semantic levels (e.g., ["instant", "temporal"]).
                If provided, filters the resulting profile to only include features
                from these levels. N-BaIoT source_agg_* is treated as "behavioral".
    """
    schema_path = Path(__file__).resolve().parents[3] / "configs" / "features" / "canonical_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    if dataset == "N-BaIoT":
        # N-BaIoT features are defined as source_agg_* in the schema.
        cols = schema["profiles"]["NBAIOT_SOURCE_AGGREGATE"]
    elif profile == "cross_domain":
        # Strict 4-feature intersection for cross-dataset transfer experiments.
        cols = schema["profiles"]["FLOW_COMPATIBLE_C_E_B"]
    elif profile == "in_domain":
        # In-domain: use the richest available feature set for each dataset.
        in_domain_map = {
            "CICIDS2017": "IN_DOMAIN_CICIDS2017",
            "Edge-IIoTset": "IN_DOMAIN_EDGE_IIOT",
            "BoT-IoT": "IN_DOMAIN_BOT_IOT",
        }
        profile_key = in_domain_map.get(dataset)
        if profile_key and profile_key in schema["profiles"]:
            cols = schema["profiles"][profile_key]
        else:
            raise ValueError(f"No in-domain profile defined for dataset: {dataset}")
    else:
        raise ValueError(f"Invalid profile requested: {profile}. Must be 'in_domain' or 'cross_domain'.")
        
    # Ablation filtering
    if levels is not None:
        if dataset == "N-BaIoT":
            # N-BaIoT features are universally classified as "behavioral" source aggregates.
            if "behavioral" not in levels:
                return []
            return cols
            
        feature_defs = {f["name"]: f["level"] for f in schema.get("features", [])}
        filtered_cols = []
        for c in cols:
            level = feature_defs.get(c)
            if level in levels:
                filtered_cols.append(c)
        return filtered_cols
        
    return cols


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
