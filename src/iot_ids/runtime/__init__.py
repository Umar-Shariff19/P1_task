"""Multi-Level IoT IDS Operational Runtime Package.

Exports InferenceEngine, IDSPredictor, and validate_input_schema for profile-aware inference.
"""
from __future__ import annotations

from iot_ids.runtime.schema import validate_input_schema, STANDARDIZED_21_FEATURES

__all__ = [
    "validate_input_schema",
    "STANDARDIZED_21_FEATURES",
    "InferenceEngine",
    "IDSPredictor",
]


def __getattr__(name: str):
    """Load optional Torch-backed runtime components only when requested."""
    if name == "InferenceEngine":
        from iot_ids.runtime.engine import InferenceEngine

        return InferenceEngine
    if name == "IDSPredictor":
        from iot_ids.runtime.predictor import IDSPredictor

        return IDSPredictor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
