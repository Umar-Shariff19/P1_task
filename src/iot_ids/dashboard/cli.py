"""CLI and Process Launcher for IoT IDS Dashboard Platform."""
from __future__ import annotations

import logging
import sys
import time
from typing import Optional

import uvicorn

from iot_ids.dashboard.app import create_app
from iot_ids.dashboard.state import get_platform_state

logger = logging.getLogger("iot_ids.dashboard")


def run_dashboard_server(
    host: str = "127.0.0.1",
    port: int = 8501,
    seed: int = 42,
    traffic_interval: float = 0.25,
    auto_start: bool = False,
    model_mode: str = "synthetic",
    dataset_name: str = "ToN-IoT",
    authorization_provider: Optional[Any] = None,
    policy_document: Optional[Dict[str, Any]] = None,
    log_level: str = "info",
) -> None:
    """Initializes models and launches the Starlette/Uvicorn server with graceful shutdown."""
    print("=" * 76)
    print("  MULTI-LEVEL IOT IDS & ADVERSARIAL ROBUSTNESS PLATFORM")
    print("=" * 76)
    print(f"[INIT] Model Mode: {model_mode.upper()} (Dataset: {dataset_name}, Seed: {seed})...")

    state = get_platform_state(
        seed=seed,
        model_mode=model_mode,
        dataset_name=dataset_name,
        authorization_provider=authorization_provider,
        policy_document=policy_document,
    )
    state.traffic_interval = max(traffic_interval, 0.05)

    health = state.predictor.health_check()
    print(f"[STATUS] Pipeline Health: {health['status']}")
    print(f"[STATUS] Active Model: {state.active_model_name}")
    print(f"[STATUS] IoT Devices Configured: {len(state.simulator.devices)}")
    print(f"[STATUS] Active Scenario: {state.simulator.scenario.scenario_type.value}")

    if auto_start:
        state.start_simulation()
        print(f"[SIMULATOR] Auto-started background traffic generation (Interval: {state.traffic_interval}s)")

    app = create_app(state=state)

    print("-" * 76)
    print(f"  Interactive Dashboard URL: http://{host}:{port}")
    print(f"  WebSocket Telemetry Feed:   ws://{host}:{port}/ws/live")
    print(f"  REST API Documentation:    http://{host}:{port}/api/status")
    print("-" * 76)
    print("  Press Ctrl+C to terminate cleanly.")
    print("=" * 76)

    try:
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level=log_level,
            access_log=False,
        )
        server = uvicorn.Server(config)
        app.state.server = server
        server.run()
    except (KeyboardInterrupt, SystemExit):
        print("\n[SHUTDOWN] Terminating platform gracefully...")
    finally:
        state.stop_simulation()
        print("[SHUTDOWN] Simulator worker terminated. Goodbye.")
