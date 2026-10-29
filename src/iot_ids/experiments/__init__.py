"""Stage 4 Controlled Model Benchmarking & Multi-Level Ablation Module."""

from iot_ids.experiments.preprocessing import FeaturePreprocessor
from iot_ids.experiments.evaluator import (
    optimize_threshold_on_val,
    evaluate_predictions,
    validate_evaluation_report,
    save_validated_evaluation_report,
    load_evaluation_schema,
)
from iot_ids.experiments.runner import (
    instantiate_model,
    run_within_domain_experiment,
    run_cross_domain_experiment,
)

__all__ = [
    "FeaturePreprocessor",
    "optimize_threshold_on_val",
    "evaluate_predictions",
    "validate_evaluation_report",
    "save_validated_evaluation_report",
    "load_evaluation_schema",
    "instantiate_model",
    "run_within_domain_experiment",
    "run_cross_domain_experiment",
]
