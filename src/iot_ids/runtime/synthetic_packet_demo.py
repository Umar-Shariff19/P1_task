"""Run an isolated synthetic packet-to-alert demonstration.

This module uses the shared operational pipeline with an in-memory deterministic
test double. It does not load or fit a model and does not access project data.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

_src_root = Path(__file__).resolve().parents[2]
if str(_src_root) not in sys.path and (_src_root / "iot_ids").is_dir():
    sys.path.insert(0, str(_src_root))

import numpy as np

from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.pipeline.system import IDSSystemPipeline


DEFAULT_SEED = 2026
DEFAULT_FLOW_COUNT = 3
DEFAULT_THRESHOLD = 0.5
_DISPLAY_FEATURES = (
    "flow_duration",
    "flow_bytes_per_sec",
    "flow_pkts_per_sec",
    "mean_pkt_size",
    "proto_tcp",
)


class SyntheticDemoError(ValueError):
    """Controlled, non-sensitive failure from the synthetic demonstration."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


class _SyntheticIdentityPreprocessor:
    """Identity transform for already numeric synthetic canonical features."""

    def transform(self, frame: Any) -> np.ndarray:
        return frame.to_numpy(dtype=float)


class _SyntheticDurationModel:
    """Untrained test double with a fixed rule over synthetic flow duration."""

    classes_ = np.array([0, 1])

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=float)
        duration_index = CANONICAL_21_FEATURE_NAMES.index("flow_duration")
        positive = np.where(values[:, duration_index] >= 1.0, 0.9, 0.2)
        return np.column_stack((1.0 - positive, positive))


def _validate_configuration(seed: int, flow_count: int, threshold: float) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise SyntheticDemoError("invalid_seed")
    if isinstance(flow_count, bool) or not isinstance(flow_count, int) or not 1 <= flow_count <= 100:
        raise SyntheticDemoError("invalid_flow_count")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise SyntheticDemoError("invalid_threshold")
    if not math.isfinite(float(threshold)) or not 0.0 <= float(threshold) <= 1.0:
        raise SyntheticDemoError("invalid_threshold")


def _generate_packets(seed: int, flow_count: int) -> list[dict[str, Any]]:
    """Generate deterministic packet dictionaries using documentation IP ranges."""
    rng = np.random.default_rng(seed)
    packets: list[dict[str, Any]] = []
    for index in range(flow_count):
        start = 1_000.0 + index * 20.0
        duration = float(rng.choice(np.array([0.25, 0.5, 1.0, 2.0])))
        src = "192.0.2.10"
        dst = f"198.51.100.{index + 1}"
        src_port = 20_000 + index
        dst_port = 443
        category = "SYNTHETIC_FIXTURE"
        common = {
            "src_ip": src,
            "dst_ip": dst,
            "src_port": src_port,
            "dst_port": dst_port,
            "protocol": "tcp",
            "label": 0,
            "attack_category": category,
        }
        packets.append({
            **common,
            "timestamp": start,
            "length": int(rng.integers(64, 1_500)),
            "syn": 1,
        })
        packets.append({
            **common,
            "src_ip": dst,
            "dst_ip": src,
            "src_port": dst_port,
            "dst_port": src_port,
            "timestamp": start + duration,
            "length": int(rng.integers(64, 1_500)),
            "ack": 1,
        })
    return packets


def run_demo(
    *, seed: int = DEFAULT_SEED, flow_count: int = DEFAULT_FLOW_COUNT,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """Run the generated packet -> flow -> canonical features -> alert path."""
    _validate_configuration(seed, flow_count, threshold)
    try:
        pipeline = IDSSystemPipeline(
            model=_SyntheticDurationModel(),
            preprocessor=_SyntheticIdentityPreprocessor(),
            feature_profile="synthetic_demo_standardized_21",
            feature_names=list(CANONICAL_21_FEATURE_NAMES),
            decision_threshold=float(threshold),
        )
        for packet in _generate_packets(seed, flow_count):
            pipeline.flow_aggregator.add_packet(packet)
        flows = pipeline.flow_aggregator.flush()
        if len(flows) != flow_count:
            raise SyntheticDemoError("flow_aggregation_contract_failed")

        alerts = []
        for flow in flows:
            alert = pipeline.process_flow(flow)
            selected = {name: alert["raw_features"][name] for name in _DISPLAY_FEATURES}
            alerts.append({
                key: value for key, value in alert.items() if key != "raw_features"
            } | {"selected_features": selected})
    except SyntheticDemoError:
        raise
    except (TypeError, ValueError, OverflowError, KeyError, IndexError):
        raise SyntheticDemoError("inference_contract_failed") from None

    return {
        "status": "SYNTHETIC_ONLY_DIAGNOSTIC",
        "seed": seed,
        "model": {
            "type": "deterministic_duration_rule_test_double",
            "trained": False,
            "artifact_loaded": False,
        },
        "input": {
            "type": "generated_packet_records",
            "packet_count": flow_count * 2,
            "flow_count": len(flows),
            "feature_profile": "standardized_21",
            "feature_count": len(CANONICAL_21_FEATURE_NAMES),
        },
        "alerts": alerts,
        "limitations": [
            "Synthetic interface demonstration only; not research or benchmark evidence.",
            "The rule-based test double is not a trained IDS model.",
            "No packet capture, datasets, checkpoints, or real-data authorization are used.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--flows", type=int, default=DEFAULT_FLOW_COUNT)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args(argv)
    try:
        result = run_demo(seed=args.seed, flow_count=args.flows, threshold=args.threshold)
        print(json.dumps(result, indent=2, allow_nan=False))
    except SyntheticDemoError as exc:
        print(json.dumps({
            "status": "SYNTHETIC_DEMO_FAILED",
            "reason_code": exc.reason_code,
        }), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
