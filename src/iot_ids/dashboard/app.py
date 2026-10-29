"""Starlette Application and REST/WebSocket API for IoT IDS Dashboard.

Serves the interactive dashboard interface, handles real-time telemetry streaming over WebSocket,
and provides RESTful controls for simulation, model selection, adversarial testing, and XAI.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from iot_ids.dashboard.state import PlatformStateManager, get_platform_state
from iot_ids.simulator.scenarios import ScenarioType

# Ensure matplotlib and shap don't warn about non-writable cache directories
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())

logger = logging.getLogger(__name__)


def create_app(state: Optional[PlatformStateManager] = None) -> Starlette:
    """Factory creating the complete Starlette application with configured state."""
    app_state = state if state is not None else get_platform_state()

    # -------------------------------------------------------------------------
    # REST API Handlers
    # -------------------------------------------------------------------------

    async def api_health(request) -> JSONResponse:
        status = app_state.get_status()
        return JSONResponse({"status": "UP", "timestamp": time.time(), "details": status})

    async def api_status(request) -> JSONResponse:
        return JSONResponse(app_state.get_status())

    async def api_devices(request) -> JSONResponse:
        devices = [d.to_dict() for d in app_state.simulator.devices]
        return JSONResponse({"count": len(devices), "devices": devices})

    async def api_scenarios(request) -> JSONResponse:
        scenarios = []
        for s_type in ScenarioType:
            sc = app_state.simulator.scenario if app_state.simulator.scenario.scenario_type == s_type else None
            scenarios.append({
                "type": s_type.value,
                "name": s_type.name,
                "active": app_state.simulator.scenario.scenario_type == s_type,
            })
        return JSONResponse({"scenarios": scenarios})

    async def api_simulation_start(request) -> JSONResponse:
        try:
            body = await request.json()
            interval = float(body.get("interval", 0.25))
        except Exception:
            interval = 0.25
        res = app_state.start_simulation(interval=interval)
        return JSONResponse(res)

    async def api_simulation_pause(request) -> JSONResponse:
        return JSONResponse(app_state.pause_simulation())

    async def api_simulation_resume(request) -> JSONResponse:
        return JSONResponse(app_state.resume_simulation())

    async def api_simulation_stop(request) -> JSONResponse:
        return JSONResponse(app_state.stop_simulation())

    async def api_simulation_reset(request) -> JSONResponse:
        return JSONResponse(app_state.reset_simulation())

    async def api_simulation_step(request) -> JSONResponse:
        try:
            body = await request.json()
            count = int(body.get("count", 10))
        except Exception:
            count = 10
        alerts = app_state.step_simulation(count=count)
        return JSONResponse({"alerts_generated": len(alerts), "status": "STEP_COMPLETE"})

    async def api_simulation_scenario(request) -> JSONResponse:
        try:
            body = await request.json()
            scenario_name = str(body.get("scenario", "BENIGN_NORMAL"))
        except Exception:
            return JSONResponse({"error": "Missing scenario in request body"}, status_code=400)
        res = app_state.set_scenario(scenario_name)
        return JSONResponse(res)

    async def api_models_select(request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Missing request body"}, status_code=400)

        # 1. Mode/Suite switching (e.g. synthetic -> research)
        mode = body.get("mode")
        dataset = body.get("dataset", "ToN-IoT")
        if mode is not None:
            from iot_ids.provenance.windows_access import RealDataAuthorizationUnavailable

            try:
                status = app_state.switch_model_suite(mode=str(mode), dataset_name=str(dataset))
                return JSONResponse({"status": "SUITE_UPDATED", "mode": mode, "details": status})
            except RealDataAuthorizationUnavailable as auth_err:
                logger.warning(f"Research model suite switch refused: {auth_err}")
                return JSONResponse(
                    {
                        "error": "RESEARCH_MODEL_AUTHORIZATION_DENIED",
                        "reason": str(auth_err),
                        "status": 403,
                        "fallback_prevented": True,
                    },
                    status_code=403,
                )
            except Exception as e:
                logger.error(f"Error switching model suite: {e}", exc_info=True)
                return JSONResponse({"error": str(e), "status": 500}, status_code=500)

        # 2. Intra-suite model switching (e.g. option_c -> rf -> robust_mlp -> standard_mlp)
        model_name = str(body.get("model", "option_c"))
        try:
            res = app_state.set_active_model(model_name)
            return JSONResponse(res)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def api_flows(request) -> JSONResponse:
        params = request.query_params
        limit = int(params.get("limit", 100))
        only_anomalies = params.get("only_anomalies", "false").lower() == "true"

        with app_state._lock:
            flows = list(app_state.recent_flows)

        if only_anomalies:
            flows = [f for f in flows if f.get("is_anomaly", False)]

        flows = flows[-limit:]
        return JSONResponse({"count": len(flows), "flows": flows})

    async def api_alerts(request) -> JSONResponse:
        params = request.query_params
        limit = int(params.get("limit", 100))
        with app_state._lock:
            alerts = list(app_state.recent_alerts)[-limit:]
        return JSONResponse({"count": len(alerts), "alerts": alerts})

    async def api_adversarial_run(request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}

        epsilon = float(body.get("epsilon", 0.15))
        steps = int(body.get("steps", 7))
        attack_method = str(body.get("attack_method", "pgd"))
        sample_count = int(body.get("sample_count", 25))

        res = app_state.run_adversarial_experiment(
            epsilon=epsilon,
            steps=steps,
            attack_method=attack_method,
            sample_count=sample_count,
        )
        return JSONResponse(res)

    async def api_explain(request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid request body"}, status_code=400)

        # Lookup by flow_id or accept direct raw_features
        features = body.get("features")
        flow_id = body.get("flow_id")

        if features is None and flow_id:
            with app_state._lock:
                for f in reversed(app_state.recent_flows):
                    if f.get("flow_id") == flow_id:
                        features = f.get("raw_features")
                        break

        if features is None:
            # Fallback to the latest flow's raw features
            with app_state._lock:
                if app_state.recent_flows:
                    features = app_state.recent_flows[-1].get("raw_features")

        if features is None:
            return JSONResponse({"error": "No features provided or available for explanation"}, status_code=400)

        res = app_state.explain_flow(features)
        return JSONResponse(res)

    async def api_experiments(request) -> JSONResponse:
        with app_state._lock:
            history = list(app_state.experiment_history)
        return JSONResponse({"count": len(history), "experiments": history})

    async def api_system_shutdown(request) -> JSONResponse:
        def _trigger():
            server = getattr(request.app.state, "server", None) if hasattr(request, "app") else None
            if server is not None:
                server.should_exit = True
            else:
                app_state.stop_simulation()

        try:
            loop = asyncio.get_running_loop()
            loop.call_later(0.1, _trigger)
        except RuntimeError:
            _trigger()
        return JSONResponse({"status": "SHUTDOWN_INITIATED", "message": "Server shutting down cleanly"})

    # -------------------------------------------------------------------------
    # WebSocket Real-Time Stream Handler
    # -------------------------------------------------------------------------

    async def websocket_live_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        event_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        app_state.register_async_queue(event_queue)

        try:
            # Send initial system status
            await websocket.send_json({
                "type": "INITIAL_STATE",
                "status": app_state.get_status(),
            })

            while True:
                # Wait for queue item or incoming ping
                queue_task = asyncio.create_task(event_queue.get())
                recv_task = asyncio.create_task(websocket.receive_text())

                done, pending = await asyncio.wait(
                    [queue_task, recv_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                if queue_task in done:
                    event = queue_task.result()
                    await websocket.send_json({
                        "type": "FLOW_EVENT",
                        "data": event,
                    })

                if recv_task in done:
                    data = recv_task.result()
                    # Respond to client ping or command
                    if data == "ping":
                        await websocket.send_text("pong")

        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        finally:
            app_state.unregister_async_queue(event_queue)

    # -------------------------------------------------------------------------
    # HTML Single Page Dashboard Handler
    # -------------------------------------------------------------------------

    async def root_dashboard(request) -> HTMLResponse:
        from iot_ids.dashboard.views import render_dashboard_html
        html = render_dashboard_html()
        return HTMLResponse(html)

    # -------------------------------------------------------------------------
    # Routes & Middleware Definition
    # -------------------------------------------------------------------------

    routes = [
        Route("/", endpoint=root_dashboard, methods=["GET"]),
        Route("/api/health", endpoint=api_health, methods=["GET"]),
        Route("/api/status", endpoint=api_status, methods=["GET"]),
        Route("/api/devices", endpoint=api_devices, methods=["GET"]),
        Route("/api/scenarios", endpoint=api_scenarios, methods=["GET"]),
        Route("/api/simulation/start", endpoint=api_simulation_start, methods=["POST"]),
        Route("/api/simulation/pause", endpoint=api_simulation_pause, methods=["POST"]),
        Route("/api/simulation/resume", endpoint=api_simulation_resume, methods=["POST"]),
        Route("/api/simulation/stop", endpoint=api_simulation_stop, methods=["POST"]),
        Route("/api/simulation/reset", endpoint=api_simulation_reset, methods=["POST"]),
        Route("/api/simulation/step", endpoint=api_simulation_step, methods=["POST"]),
        Route("/api/simulation/scenario", endpoint=api_simulation_scenario, methods=["POST"]),
        Route("/api/models/select", endpoint=api_models_select, methods=["POST"]),
        Route("/api/flows", endpoint=api_flows, methods=["GET"]),
        Route("/api/alerts", endpoint=api_alerts, methods=["GET"]),
        Route("/api/adversarial/run", endpoint=api_adversarial_run, methods=["POST"]),
        Route("/api/explain", endpoint=api_explain, methods=["POST"]),
        Route("/api/experiments", endpoint=api_experiments, methods=["GET"]),
        Route("/api/system/shutdown", endpoint=api_system_shutdown, methods=["POST"]),
        WebSocketRoute("/ws/live", endpoint=websocket_live_endpoint),
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    app = Starlette(debug=True, routes=routes, middleware=middleware)
    return app
