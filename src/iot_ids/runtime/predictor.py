"""Production IDSPredictor API Wrapper for Runtime Inference Engine.

Delegates single flow and batch predictions to InferenceEngine while tracking
health inspection status and operational state.
"""
from __future__ import annotations

from typing import Dict, Any, List, Union, Optional
import pandas as pd

from iot_ids.runtime.engine import InferenceEngine


class IDSPredictor:
    """Production deployable predictor wrapper for multi-level IoT intrusion detection."""

    def __init__(self, engine: InferenceEngine):
        self.engine = engine

    @classmethod
    def from_profile_and_dataset(
        cls,
        profile: str = "standardized_21",
        dataset: str = "ToN-IoT",
        models_base_dir: Optional[str] = None,
        decision_threshold: float = 0.5,
        *,
        authorization_provider: Optional[Any] = None,
        policy_document: Optional[Dict[str, Any]] = None,
    ) -> IDSPredictor:
        """Instantiates an IDSPredictor from profile and dataset identifiers."""
        engine = InferenceEngine(
            profile=profile,
            dataset=dataset,
            models_base_dir=models_base_dir,
            decision_threshold=decision_threshold,
            authorization_provider=authorization_provider,
            policy_document=policy_document,
        )
        return cls(engine=engine)

    def health_check(self) -> Dict[str, Any]:
        """Returns engine readiness checks without asserting model quality."""
        health = self.engine.health_check()
        health.update({
            "rf_model_loaded": self.engine.rf_model is not None,
            "robust_mlp_loaded": self.engine.robust_mlp_model is not None,
            "preprocessor_loaded": self.engine.preprocessor is not None,
        })
        return health

    def predict_flow(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        """Runs inference on a single flow dictionary."""
        return self.engine.predict(flow)

    def predict_dataframe(self, df_flows: pd.DataFrame) -> List[Dict[str, Any]]:
        """Runs batch inference over a DataFrame of canonical flow features."""
        return self.engine.predict(df_flows)

    def reset_state(self) -> None:
        """Resets predictor state buffers."""
        pass
