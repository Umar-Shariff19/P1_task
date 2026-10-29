#!/usr/bin/env python3
"""One-Command Launcher for IoT IDS and Adversarial Robustness Platform.

Usage:
    python scripts/run_platform.py [--host 127.0.0.1] [--port 8501] [--auto-start]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to python path if run directly from repository
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from iot_ids.dashboard.cli import run_dashboard_server


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Interactive Multi-Level IoT IDS & Adversarial Platform"
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind (default: 8501)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed (default: 42)")
    parser.add_argument("--interval", type=float, default=0.25, help="Seconds between generator batches (default: 0.25)")
    parser.add_argument("--auto-start", action="store_true", help="Automatically start simulation on launch")
    parser.add_argument(
        "--model-mode",
        type=str,
        default="synthetic",
        choices=["synthetic", "research"],
        help="Inference model mode: 'synthetic' (default) or 'research' (requires authorized policy)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="ToN-IoT",
        help="Dataset name when using research models (default: ToN-IoT)",
    )

    args = parser.parse_args()

    run_dashboard_server(
        host=args.host,
        port=args.port,
        seed=args.seed,
        traffic_interval=args.interval,
        auto_start=args.auto_start,
        model_mode=args.model_mode,
        dataset_name=args.dataset,
    )


if __name__ == "__main__":
    main()
