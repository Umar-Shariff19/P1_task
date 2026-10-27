"""Repeatable synthetic-only smoke command for runtime inference.

Run with ``python -m iot_ids.runtime.synthetic_smoke``. This module generates
its own samples and models, never loads files, and is not a benchmark runner.
"""
from __future__ import annotations

import importlib.metadata
import json
import platform
import sys

import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import RandomForestClassifier

from iot_ids.preprocessing.pipeline import PreprocessingPipeline
from iot_ids.runtime.engine import InferenceEngine, MLPModule
from iot_ids.runtime.schema import STANDARDIZED_21_FEATURES


def run_synthetic_smoke() -> dict[str, object]:
    seed = 20261028
    rng = np.random.default_rng(seed)
    row_count = 48
    labels = np.tile(np.array([0, 1], dtype=np.int64), row_count // 2)
    generated = rng.uniform(0.05, 2.0, size=(row_count, len(STANDARDIZED_21_FEATURES)))
    generated[:, 0] += labels.astype(np.float64) * 0.7
    frame = pd.DataFrame(generated, columns=STANDARDIZED_21_FEATURES)

    train_frame, test_frame = frame.iloc[:32], frame.iloc[32:]
    train_labels, test_labels = labels[:32], labels[32:]
    preprocessor = PreprocessingPipeline(STANDARDIZED_21_FEATURES)
    transformed_train = preprocessor.fit_transform(train_frame)
    rf_model = RandomForestClassifier(n_estimators=8, random_state=seed, n_jobs=1)
    rf_model.fit(transformed_train, train_labels)
    torch.manual_seed(seed)
    mlp_model = MLPModule(input_dim=len(STANDARDIZED_21_FEATURES)).eval()

    engine = InferenceEngine.for_synthetic_components(
        preprocessor=preprocessor,
        rf_model=rf_model,
        mlp_model=mlp_model,
    )
    predictions = engine.predict(test_frame, explain=True, top_k=3)
    if not isinstance(predictions, list) or len(predictions) != len(test_frame):
        raise RuntimeError("Synthetic smoke failed: prediction batch length mismatch.")

    probabilities = []
    for result in predictions:
        components = (result["rf_probability"], result["robust_mlp_probability"])
        probability = result["probability"]
        expected = 0.7 * components[0] + 0.3 * components[1]
        if not np.isfinite([*components, probability]).all():
            raise RuntimeError("Synthetic smoke failed: non-finite model output.")
        if not 0.0 <= probability <= 1.0 or not np.isclose(probability, expected):
            raise RuntimeError("Synthetic smoke failed: invalid Option C fusion output.")
        if len(result.get("explanation", {}).get("top_k_features", [])) != 3:
            raise RuntimeError("Synthetic smoke failed: explanation output contract mismatch.")
        probabilities.append(probability)

    # Metric is diagnostic only and intentionally not emitted as research evidence.
    from sklearn.metrics import roc_auc_score

    diagnostic_auc = float(roc_auc_score(test_labels, probabilities))
    return {
        "status": "SYNTHETIC_SMOKE_PASSED_NOT_RESEARCH_EVIDENCE",
        "seed": seed,
        "rows": {"generated": row_count, "train": len(train_frame), "smoke_input": len(test_frame)},
        "features": len(STANDARDIZED_21_FEATURES),
        "components": {
            "preprocessor": "fit on generated training rows only",
            "random_forest": "fitted on generated training rows only",
            "mlp": "freshly initialized, untrained; interface exercised only",
            "inference": "synthetic dependency injection; shared InferenceEngine.predict path",
            "explainability": "SHAP/local explanation requested for synthetic rows",
        },
        "diagnostics": {
            "prediction_count": len(predictions),
            "fusion": "verified probability = 0.7 * RF + 0.3 * MLP",
            "synthetic_auc_arithmetic_check": diagnostic_auc,
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "numpy": importlib.metadata.version("numpy"),
            "pandas": importlib.metadata.version("pandas"),
            "scikit_learn": importlib.metadata.version("scikit-learn"),
            "torch": importlib.metadata.version("torch"),
        },
        "omitted": [
            "research datasets and data adapters",
            "existing checkpoints and production artifact loading",
            "training/evaluation pipelines and benchmark reporting",
            "real-data authorization",
        ],
    }


def main() -> None:
    print(json.dumps(run_synthetic_smoke(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
